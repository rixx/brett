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


class Command(BaseCommand):
    help = "Review a Maildir directory, skipping already-imported emails and copying new ones to clipboard for ingestion"

    def add_arguments(self, parser):
        parser.add_argument(
            "directory",
            type=str,
            help="Path to mail directory (e.g. ~/.local/share/mail/account/folder/cur/)",
        )

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
            headers = header_parser.parsestr(path.read_text(errors="replace"))
            try:
                dt = parsedate_to_datetime(headers["Date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)

        self.stdout.write(f"Sorting {len(unsorted)} emails by date...")
        files = sorted(unsorted, key=_date_key)
        skipped = 0
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
            content = mail_file.read_text(errors="replace")
            headers = header_parser.parsestr(content)

            message_id = headers.get("Message-ID", "").strip()
            if not message_id:
                self.stdout.write(
                    self.style.WARNING(f"  No Message-ID: {mail_file.name}")
                )
                skipped += 1
                if progress is not None:
                    progress.total -= 1
                    progress.refresh()
                continue

            if Entry.objects.filter(message_id=message_id).exists():
                skipped += 1
                if progress is not None:
                    progress.total -= 1
                    progress.refresh()
                continue

            subject = headers.get("Subject", "(no subject)")
            self.stdout.write(f"\n{mail_file.name}")
            self.stdout.write(f"  Subject: {subject}")
            if PGP_BLOCK_RE.search(content):
                content = self.decrypt_pgp_blocks(content)
                self.stdout.write("  Decrypted PGP content.")
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

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {copied} copied, {skipped} skipped.")
        )
