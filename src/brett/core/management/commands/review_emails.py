import email
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from email.parser import HeaderParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from brett.core.models import Entry

PGP_BLOCK_RE = re.compile(
    r"-----BEGIN PGP MESSAGE-----\n.*?\n-----END PGP MESSAGE-----",
    re.DOTALL,
)


def _read_email_file(path):
    """Read an email file with proper encoding handling.

    Tries UTF-8 first, falls back to latin-1 which maps every byte to the
    same-numbered Unicode code point (preserving raw byte values for charsets
    like windows-1252).
    """
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


class Command(BaseCommand):
    help = "Review a Maildir directory, skipping already-imported emails and copying new ones to clipboard for ingestion"

    def add_arguments(self, parser):
        parser.add_argument(
            "directory",
            type=str,
            help="Path to mail directory (e.g. ~/.local/share/mail/account/folder/cur/)",
        )

    def unwrap_pgp_mime(self, content):
        """If content is a decrypted multipart/encrypted email, unwrap the
        encryption layer to produce a clean MIME message.

        Returns (content, status) where status is:
        - "unwrapped": PGP/MIME was successfully unwrapped
        - "encrypted": PGP/MIME but decryption failed (still encrypted)
        - None: not a PGP/MIME email
        """
        msg = email.message_from_string(content)
        if msg.get_content_type() != "multipart/encrypted":
            return content, None

        # Find the application/octet-stream part with decrypted content
        decrypted_payload = None
        for part in msg.walk():
            if part.get_content_type() == "application/octet-stream":
                payload = part.get_payload(decode=False)
                if isinstance(payload, str) and payload.strip():
                    decrypted_payload = payload
                    break

        if decrypted_payload is None:
            return content, "encrypted"

        # Check if the payload is still encrypted
        stripped_payload = decrypted_payload.strip()
        if stripped_payload.startswith("-----BEGIN PGP"):
            return content, "encrypted"

        # Split original email into headers and body
        header_end = content.find("\n\n")
        if header_end == -1:
            return content, "unwrapped"

        # Filter out MIME content headers from original headers, keeping
        # transport headers (From, Date, Subject, Message-ID, Received, etc.)
        filtered_lines = []
        skip_continuation = False
        for line in content[:header_end].split("\n"):
            if line and line[0] in (" ", "\t"):
                if skip_continuation:
                    continue
                filtered_lines.append(line)
                continue
            skip_continuation = False
            if ":" in line:
                header_name = line.split(":")[0].strip().lower()
                if header_name in (
                    "content-type",
                    "content-transfer-encoding",
                    "content-disposition",
                ):
                    skip_continuation = True
                    continue
            filtered_lines.append(line)

        # Build new email: filtered headers + decrypted MIME content
        if stripped_payload.startswith("Content-Type:") or stripped_payload.startswith(
            "MIME-Version:"
        ):
            # Decrypted content is MIME — join directly as additional headers
            result = "\n".join(filtered_lines) + "\n" + stripped_payload
        else:
            # Decrypted content is plain text — add Content-Type and separator
            result = (
                "\n".join(filtered_lines)
                + "\nContent-Type: text/plain; charset=UTF-8\n\n"
                + stripped_payload
            )

        return result, "unwrapped"

    def strip_large_attachments(self, content, max_size=1_500_000):
        """Strip the largest non-text MIME attachments until content is under max_size."""
        if len(content) <= max_size:
            return content

        msg = email.message_from_string(content)
        if not msg.is_multipart():
            return content
        # Don't strip parts from encrypted emails — the octet-stream part
        # contains the message body (encrypted or decrypted).
        if msg.get_content_type() == "multipart/encrypted":
            return content

        while len(msg.as_string()) > max_size:
            # Find the largest non-text part
            largest_part = None
            largest_size = 0
            for part in msg.walk():
                if part.is_multipart():
                    continue
                content_type = part.get_content_type()
                if content_type in ("text/plain", "text/html"):
                    continue
                part_size = len(part.as_string())
                if part_size > largest_size:
                    largest_size = part_size
                    largest_part = part

            if largest_part is None:
                break

            filename = largest_part.get_filename() or "unnamed"
            size_str = (
                f"{largest_size / 1024 / 1024:.1f}MB"
                if largest_size > 1024 * 1024
                else f"{largest_size / 1024:.0f}KB"
            )
            # Replace the attachment with a placeholder
            for header in (
                "Content-Transfer-Encoding",
                "Content-Disposition",
                "Content-ID",
            ):
                if header in largest_part:
                    del largest_part[header]
            largest_part.set_type("text/plain")
            largest_part.set_payload(f"[attachment stripped: {filename}, {size_str}]\n")

        return msg.as_string()

    def decrypt_pgp(self, block):
        """Decrypt a PGP message block using gpg."""
        result = subprocess.run(
            ["gpg", "--decrypt", "--quiet", "--batch"],
            input=block,
            capture_output=True,
            text=True,
        )
        if result.returncode in (0, 2):
            return result.stdout
        return block

    def decrypt_pgp_blocks(self, content):
        """Replace all PGP message blocks in content with their decrypted text."""
        return PGP_BLOCK_RE.sub(lambda m: self.decrypt_pgp(m.group(0)), content)

    def handle(self, *args, **options):
        directory = Path(options["directory"]).expanduser()
        if not directory.is_dir():
            self.stderr.write(self.style.ERROR(f"Not a directory: {directory}"))
            return

        unsorted = [f for f in directory.iterdir() if f.is_file()]
        if not unsorted:
            self.stdout.write(self.style.WARNING("No files found in directory."))
            return

        header_parser = HeaderParser()

        def _date_key(path):
            headers = header_parser.parsestr(_read_email_file(path))
            try:
                dt = parsedate_to_datetime(headers["Date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)

        self.stdout.write(f"Sorting {len(unsorted)} emails by date...")
        files = sorted(unsorted, key=_date_key)
        already_imported = 0
        no_message_id = 0
        copied = 0

        progress = None
        try:
            from tqdm import tqdm

            progress = tqdm(
                total=len(files),
                desc="Reviewing emails",
                unit="email",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed} elapsed, {remaining} left, {rate_fmt}{postfix}]",
            )
        except ImportError:
            pass

        for mail_file in files:
            content = _read_email_file(mail_file)
            headers = header_parser.parsestr(content)

            message_id = headers.get("Message-ID", "").strip()
            if not message_id:
                self.stdout.write(
                    self.style.WARNING(f"  No Message-ID: {mail_file.name}")
                )
                no_message_id += 1
                if progress is not None:
                    progress.total -= 1
                    progress.refresh()
                continue

            if Entry.objects.filter(message_id=message_id).exists():
                already_imported += 1
                if progress is not None:
                    progress.total -= 1
                    progress.refresh()
                continue

            subject = headers.get("Subject", "(no subject)")
            self.stdout.write(f"\n{mail_file.name}")
            self.stdout.write(f"  Subject: {subject}")
            if PGP_BLOCK_RE.search(content):
                content = self.decrypt_pgp_blocks(content)
                content, pgp_status = self.unwrap_pgp_mime(content)
                if pgp_status == "encrypted":
                    self.stdout.write(
                        self.style.WARNING("  PGP encrypted (could not decrypt).")
                    )
                else:
                    self.stdout.write("  Decrypted PGP content.")
            original_size = len(content)
            content = self.strip_large_attachments(content)
            if len(content) < original_size:
                self.stdout.write(
                    f"  Stripped attachments: {original_size / 1024:.0f}KB → {len(content) / 1024:.0f}KB"
                )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".eml", delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            try:
                with open(tmp_path) as f:
                    subprocess.run(
                        ["wl-copy", "--type", "text/plain"], stdin=f, check=True
                    )
            finally:
                tmp_path.unlink()
            self.stdout.write(self.style.SUCCESS("  Copied to clipboard."))
            copied += 1
            if progress is not None:
                progress.update(1)

            try:
                input("  Press Enter for next email (Ctrl+C to stop)...")
            except (KeyboardInterrupt, EOFError):
                self.stdout.write("")
                break

        total_emails = len(files) - no_message_id
        total_imported = already_imported + copied
        remaining = total_emails - total_imported
        session_pct = (copied / total_emails * 100) if total_emails else 0
        total_pct = (total_imported / total_emails * 100) if total_emails else 0
        self.stdout.write(f"\nSession: {copied} emails imported ({session_pct:.0f}%)")
        self.stdout.write(
            f"Total:   {total_imported}/{total_emails} emails imported ({total_pct:.0f}%), {remaining} remaining"
        )
