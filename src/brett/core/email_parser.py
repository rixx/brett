"""Email parsing utilities for brett."""

import email
import re
from email.utils import parseaddr, parsedate_to_datetime


def _is_placeholder_subject(subject):
    """Check if a subject is a PGP encryption placeholder like '...' or 'Re: ...'."""
    stripped = subject.strip()
    if not stripped:
        return True
    return bool(re.match(r"^(Re:\s*)*\.{2,}$", stripped))


def _extract_protected_subject(raw_message):
    """Extract subject from protected-headers block in a PGP-encrypted email."""
    match = re.search(r'protected-headers="v\d+"', raw_message)
    if not match:
        return None
    remaining = raw_message[match.end() :]
    # Skip the rest of the line containing the protected-headers marker
    newline_pos = remaining.find("\n")
    if newline_pos == -1:
        return None
    remaining = remaining[newline_pos + 1 :]
    for line in remaining.split("\n"):
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith("Subject:"):
            return stripped[len("Subject:") :].strip()
    return None


def _extract_body_from_pgp_payload(msg):
    """Extract body from the decrypted inner MIME structure of a PGP-encrypted email.

    The application/octet-stream part of a multipart/encrypted email contains
    the decrypted MIME message. Parse it to find text/plain content.
    """
    for part in msg.walk():
        if part.get_content_type() == "application/octet-stream":
            # Try decoded payload (bytes)
            payload = part.get_payload(decode=True)
            if payload:
                try:
                    inner_msg = email.message_from_bytes(payload)
                    for inner_part in inner_msg.walk():
                        if inner_part.get_content_type() == "text/plain":
                            inner_body = inner_part.get_payload(decode=True)
                            if inner_body:
                                return inner_body.decode("utf-8", errors="ignore")
                except Exception:
                    pass
            # Try string payload (no transfer encoding)
            payload_str = part.get_payload(decode=False)
            if isinstance(payload_str, str) and payload_str.strip():
                try:
                    inner_msg = email.message_from_string(payload_str)
                    for inner_part in inner_msg.walk():
                        if inner_part.get_content_type() == "text/plain":
                            inner_body = inner_part.get_payload(decode=True)
                            if inner_body:
                                return inner_body.decode("utf-8", errors="ignore")
                except Exception:
                    pass
    return None


def parse_raw_email(raw_message):
    """
    Parse a raw email message and extract headers and body.

    Returns a dictionary with:
    - from_addr: Email address from From header
    - from_name: Display name from From header
    - subject: Email subject (uses longer subject if there are duplicates)
    - message_id: Message-ID header
    - date: Parsed datetime object
    - in_reply_to: In-Reply-To header (if any)
    - body: Email body text
    - raw_message: The original raw message
    """
    msg = email.message_from_string(raw_message)

    # Parse From header
    from_name, from_addr = parseaddr(msg.get("From", ""))

    # Parse Subject - handle potential duplicates from encryption
    subjects = msg.get_all("Subject", [])
    if subjects:
        # Use the longer subject if there are multiple
        subject = max(subjects, key=len) if len(subjects) > 1 else subjects[0]
    else:
        subject = ""

    # PGP-encrypted emails may have a placeholder subject (e.g. "...")
    # with the real subject inside a protected-headers block in the body
    if _is_placeholder_subject(subject):
        protected_subject = _extract_protected_subject(raw_message)
        if protected_subject:
            subject = protected_subject

    # Parse Message-ID
    message_id = msg.get("Message-ID", "")

    # Parse Date
    date_str = msg.get("Date")
    date = None
    if date_str:
        try:
            date = parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            # If parsedate_to_datetime fails, try alternative parsing
            import datetime
            from email.utils import parsedate

            try:
                parsed_tuple = parsedate(date_str)
                if parsed_tuple:
                    # Convert to datetime (parsedate returns struct_time)
                    date = datetime.datetime(*parsed_tuple[:6])
                    # Make timezone-aware (assume UTC if no timezone)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=datetime.timezone.utc)
            except Exception:
                # Last resort: set to None and let caller handle it
                pass

    # Parse In-Reply-To
    in_reply_to = msg.get("In-Reply-To", "")

    # Extract body
    body = ""
    if msg.is_multipart():
        # Get text/plain parts
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )
                    break
                except Exception:
                    continue
        # For PGP-encrypted emails, the text/plain part is inside the
        # application/octet-stream payload which contains the decrypted MIME
        if not body and msg.get_content_type() == "multipart/encrypted":
            body = _extract_body_from_pgp_payload(msg) or ""
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            body = msg.get_payload()

    return {
        "from_addr": from_addr,
        "from_name": from_name,
        "subject": subject,
        "message_id": message_id,
        "date": date,
        "in_reply_to": in_reply_to,
        "body": body.strip() if body else "",
        "raw_message": raw_message,
    }
