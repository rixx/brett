"""Email parsing utilities for brett."""

import email
import re
from email.header import decode_header as _decode_header
from email.utils import parseaddr, parsedate_to_datetime


def _is_placeholder_subject(subject):
    """Check if a subject is a PGP encryption placeholder like '...' or 'Re: ...'."""
    stripped = subject.strip()
    if not stripped:
        return True
    return bool(re.match(r"^(Re:\s*)*\.{2,}$", stripped))


def _decode_rfc2047(value):
    """Decode RFC 2047 encoded-words in a header value."""
    parts = _decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _decode_payload(part):
    """Decode the text payload of an email part, handling charset and transfer encoding.

    For quoted-printable/base64, uses get_payload(decode=True) to decode the
    transfer encoding, then decodes the resulting bytes with the part's charset.
    For 8bit/7bit/binary, the string payload from message_from_string already
    contains correct Unicode, so we return it directly.
    """
    cte = part.get("Content-Transfer-Encoding", "").strip().lower()
    if cte in ("quoted-printable", "base64"):
        charset = part.get_content_charset() or "utf-8"
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode(charset, errors="replace")
    payload = part.get_payload(decode=False)
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return ""


def _extract_protected_subject(raw_message):
    """Extract subject from protected-headers block in a PGP-encrypted email."""
    match = re.search(r'protected-headers="?v\d+"?', raw_message)
    if not match:
        return None
    remaining = raw_message[match.end() :]
    # Skip the rest of the line containing the protected-headers marker
    newline_pos = remaining.find("\n")
    if newline_pos == -1:
        return None
    remaining = remaining[newline_pos + 1 :]
    lines = remaining.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith("Subject:"):
            subject_value = stripped[len("Subject:") :].strip()
            # Handle folded headers (continuation lines starting with whitespace)
            for cont_line in lines[i + 1 :]:
                if cont_line and cont_line[0] in (" ", "\t"):
                    subject_value += " " + cont_line.strip()
                else:
                    break
            return _decode_rfc2047(subject_value)
    return None


def _extract_body_from_pgp_payload(msg):
    """Extract body from the decrypted inner MIME structure of a PGP-encrypted email.

    The application/octet-stream part of a multipart/encrypted email contains
    the decrypted MIME message. Parse it to find text/plain content.
    """
    for part in msg.walk():
        if part.get_content_type() == "application/octet-stream":
            # Try string payload first — since the outer message was parsed from
            # a string, the payload preserves Unicode characters (umlauts etc.)
            # Using get_payload(decode=True) would go through raw-unicode-escape
            # encoding which loses non-ASCII chars when later decoded as UTF-8.
            payload_str = part.get_payload(decode=False)
            if isinstance(payload_str, str) and payload_str.strip():
                try:
                    inner_msg = email.message_from_string(payload_str)
                    for inner_part in inner_msg.walk():
                        if inner_part.get_content_type() == "text/plain":
                            inner_body = _decode_payload(inner_part)
                            if inner_body.strip():
                                return inner_body
                except Exception:
                    pass
            # Fall back to bytes path for base64/QP-encoded payloads
            payload = part.get_payload(decode=True)
            if payload:
                try:
                    inner_msg = email.message_from_bytes(payload)
                    for inner_part in inner_msg.walk():
                        if inner_part.get_content_type() == "text/plain":
                            inner_body = _decode_payload(inner_part)
                            if inner_body.strip():
                                return inner_body
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
    from_name = _decode_rfc2047(from_name) if from_name else from_name

    # Parse Subject - handle potential duplicates from encryption
    subjects = msg.get_all("Subject", [])
    if subjects:
        # Use the longer subject if there are multiple
        subject = max(subjects, key=len) if len(subjects) > 1 else subjects[0]
        subject = _decode_rfc2047(subject)
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
                    body = _decode_payload(part)
                    break
                except Exception:
                    continue
        # For PGP-encrypted emails, the text/plain part is inside the
        # application/octet-stream payload which contains the decrypted MIME
        if not body and msg.get_content_type() == "multipart/encrypted":
            body = _extract_body_from_pgp_payload(msg) or ""
    else:
        try:
            body = _decode_payload(msg)
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
