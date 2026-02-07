from brett.core.management.commands.review_emails import Command


def make_pgp_mime_email(octet_stream_body, subject="...", extra_headers=""):
    """Build a multipart/encrypted email with the given octet-stream payload."""
    return (
        f"From: sender@example.com\n"
        f"Subject: {subject}\n"
        f"Date: Mon, 1 Jan 2024 12:00:00 +0000\n"
        f"Message-ID: <test@example.com>\n"
        f"MIME-Version: 1.0\n"
        f"{extra_headers}"
        f"Content-Type: multipart/encrypted;\n"
        f' protocol="application/pgp-encrypted";\n'
        f' boundary="----outer"\n'
        f"\n"
        f"------outer\n"
        f"Content-Type: application/pgp-encrypted\n"
        f"\n"
        f"Version: 1\n"
        f"\n"
        f"------outer\n"
        f'Content-Type: application/octet-stream; name="encrypted.asc"\n'
        f'Content-Disposition: inline; filename="encrypted.asc"\n'
        f"\n"
        f"{octet_stream_body}\n"
        f"------outer--\n"
    )


class TestUnwrapPgpMime:
    def setup_method(self):
        self.cmd = Command()

    def test_non_pgp_email_unchanged(self):
        """Non-PGP/MIME emails are returned unchanged."""
        content = (
            "From: test@example.com\n"
            "Subject: Hello\n"
            "Content-Type: text/plain\n"
            "\n"
            "Body text."
        )
        result, status = self.cmd.unwrap_pgp_mime(content)
        assert status is None
        assert result == content

    def test_encrypted_payload_detected(self):
        """PGP/MIME with encrypted payload (decryption failed) returns 'encrypted'."""
        content = make_pgp_mime_email(
            "-----BEGIN PGP MESSAGE-----\n"
            "wcFMA5dzawO9ZxjOARAA\n"
            "-----END PGP MESSAGE-----"
        )
        result, status = self.cmd.unwrap_pgp_mime(content)
        assert status == "encrypted"
        # Content should be unchanged
        assert "multipart/encrypted" in result

    def test_unwrap_decrypted_mime(self):
        """Decrypted MIME content is unwrapped into a clean email."""
        decrypted_mime = (
            'Content-Type: multipart/mixed; boundary="----inner";\n'
            ' protected-headers="v1"\n'
            "Subject: Re: Actual Subject\n"
            "\n"
            "------inner\n"
            "Content-Type: text/plain; charset=UTF-8\n"
            "\n"
            "Hello, this is the decrypted body.\n"
            "------inner--"
        )
        content = make_pgp_mime_email(decrypted_mime)
        result, status = self.cmd.unwrap_pgp_mime(content)

        assert status == "unwrapped"
        # Should no longer contain multipart/encrypted
        assert "multipart/encrypted" not in result
        assert "application/pgp-encrypted" not in result
        # Should contain the decrypted content directly
        assert "Re: Actual Subject" in result
        assert "Hello, this is the decrypted body." in result
        # Original headers should be preserved
        assert "Message-ID: <test@example.com>" in result
        assert "From: sender@example.com" in result
        assert "Date: Mon, 1 Jan 2024 12:00:00 +0000" in result

    def test_unwrap_decrypted_plain_text(self):
        """Decrypted plain text (not MIME) gets a Content-Type header."""
        content = make_pgp_mime_email("Just a plain text message.\n\nSecond paragraph.")
        result, status = self.cmd.unwrap_pgp_mime(content)

        assert status == "unwrapped"
        assert "multipart/encrypted" not in result
        assert "Content-Type: text/plain; charset=UTF-8" in result
        assert "Just a plain text message." in result

    def test_unwrap_preserves_transport_headers(self):
        """Transport headers like Received are preserved after unwrapping."""
        decrypted_mime = "Content-Type: text/plain; charset=UTF-8\n" "\n" "Body text."
        content = make_pgp_mime_email(
            decrypted_mime,
            extra_headers=(
                "Received: from mail.example.com\n"
                "    by mail.test.com; Mon, 1 Jan 2024 12:00:00 +0000\n"
            ),
        )
        result, status = self.cmd.unwrap_pgp_mime(content)

        assert status == "unwrapped"
        assert "Received: from mail.example.com" in result
        assert "by mail.test.com" in result

    def test_unwrapped_email_parseable(self):
        """An unwrapped email should be correctly parsed by parse_raw_email."""
        from brett.core.email_parser import parse_raw_email

        decrypted_mime = (
            'Content-Type: multipart/mixed; boundary="----inner";\n'
            ' protected-headers="v1"\n'
            "Subject: Re: Project Update\n"
            "\n"
            "------inner\n"
            "Content-Type: text/plain; charset=UTF-8\n"
            "\n"
            "The actual message body.\n"
            "------inner--"
        )
        content = make_pgp_mime_email(decrypted_mime)
        unwrapped, status = self.cmd.unwrap_pgp_mime(content)
        assert status == "unwrapped"

        parsed = parse_raw_email(unwrapped)
        assert parsed["subject"] == "Re: Project Update"
        assert parsed["body"] == "The actual message body."
        assert parsed["from_addr"] == "sender@example.com"
        assert parsed["message_id"] == "<test@example.com>"


class TestStripLargeAttachments:
    def setup_method(self):
        self.cmd = Command()

    def test_encrypted_email_not_stripped(self):
        """multipart/encrypted emails should not have parts stripped."""
        # Build a large PGP/MIME email (over 1.5MB)
        large_payload = "A" * 2_000_000
        content = make_pgp_mime_email(large_payload)
        result = self.cmd.strip_large_attachments(content)
        # The large payload should still be present (not stripped)
        assert large_payload in result
