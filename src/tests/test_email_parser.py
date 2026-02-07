from brett.core.email_parser import parse_raw_email


def test_parse_email_without_subject():
    """Test parsing an email with no subject header."""
    raw_email = """From: test@example.com
To: recipient@example.com
Date: Mon, 1 Jan 2024 12:00:00 +0000

This is the body."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == ""
    assert result["from_addr"] == "test@example.com"
    assert result["body"] == "This is the body."


def test_parse_email_with_malformed_date():
    """Test parsing an email with a date that parsedate_to_datetime can't handle."""
    raw_email = """From: test@example.com
Subject: Test
Date: Invalid Date Format
Message-ID: <test123@example.com>

Body text."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Test"
    assert result["from_addr"] == "test@example.com"
    # Date parsing should fail gracefully and return None
    assert result["date"] is None


def test_parse_email_with_parseable_fallback_date():
    """Test parsing an email with a date that needs fallback parsing."""
    # Some date formats that parsedate can handle but parsedate_to_datetime might not
    raw_email = """From: test@example.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00
Message-ID: <test123@example.com>

Body text."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Test"
    # The fallback parsing should handle this


def test_parse_multipart_email_with_text_plain():
    """Test parsing a multipart email with text/plain content."""
    raw_email = """From: test@example.com
Subject: Multipart Test
Date: Mon, 1 Jan 2024 12:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="utf-8"

This is the plain text body.
--boundary123
Content-Type: text/html; charset="utf-8"

<p>This is the HTML body.</p>
--boundary123--
"""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Multipart Test"
    assert "plain text body" in result["body"]


def test_parse_multipart_email_without_text_plain():
    """Test parsing a multipart email without text/plain parts."""
    raw_email = """From: test@example.com
Subject: Multipart Test
Date: Mon, 1 Jan 2024 12:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/html; charset="utf-8"

<p>Only HTML content.</p>
--boundary123--
"""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Multipart Test"
    # Should have empty body since no text/plain part was found
    assert result["body"] == ""


def test_parse_email_with_multiple_subjects():
    """Test parsing an email with multiple Subject headers (e.g., from encryption)."""
    raw_email = """From: test@example.com
Subject: Short
Subject: This is a much longer subject line
Date: Mon, 1 Jan 2024 12:00:00 +0000

Body text."""

    result = parse_raw_email(raw_email)
    # Should use the longer subject
    assert result["subject"] == "This is a much longer subject line"


def test_parse_email_with_in_reply_to():
    """Test parsing an email with In-Reply-To header."""
    raw_email = """From: test@example.com
Subject: Re: Original
Date: Mon, 1 Jan 2024 12:00:00 +0000
In-Reply-To: <original@example.com>

Reply body."""

    result = parse_raw_email(raw_email)
    assert result["in_reply_to"] == "<original@example.com>"
    assert result["subject"] == "Re: Original"


def test_parse_email_with_display_name():
    """Test parsing an email with a display name in From header."""
    raw_email = """From: John Doe <john@example.com>
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000

Body text."""

    result = parse_raw_email(raw_email)
    assert result["from_addr"] == "john@example.com"
    assert result["from_name"] == "John Doe"


def test_parse_pgp_encrypted_email_with_protected_headers():
    """Test that subject is extracted from protected-headers when envelope subject is a placeholder."""
    raw_email = """From: Alice Sender <alice@example.com>
Subject: ...
Date: Mon, 7 Apr 2025 18:54:55 +0200
Message-ID: <27231b41-43c2-4b75-be57-a28fa0211055@example.com>
In-Reply-To: <993E0ABB-4C67-4695-AB64-08823D203E8D@example.org>
MIME-Version: 1.0
Content-Type: multipart/encrypted;
 protocol="application/pgp-encrypted";
 boundary="------------1cBoy0juGTJNFH2GDTJVwO5m"

This is an OpenPGP/MIME encrypted message (RFC 4880 and 3156)
--------------1cBoy0juGTJNFH2GDTJVwO5m
Content-Type: application/pgp-encrypted
Content-Description: PGP/MIME version identification

Version: 1

--------------1cBoy0juGTJNFH2GDTJVwO5m
Content-Type: application/octet-stream; name="encrypted.asc"
Content-Description: OpenPGP encrypted message
Content-Disposition: inline; filename="encrypted.asc"

Content-Type: multipart/mixed; boundary="------------Eac4tQR5dnhoF0VXUVRE4u3L";
 protected-headers="v1"
Subject: Re: Project Update
From: Alice Sender <alice@example.com>
To: Bob Recipient <bob@example.org>
Cc: "board@example.net" <board@example.net>
Message-ID: <27231b41-43c2-4b75-be57-a28fa0211055@example.com>

--------------Eac4tQR5dnhoF0VXUVRE4u3L
Content-Type: text/plain; charset=UTF-8

This is the decrypted body.
--------------Eac4tQR5dnhoF0VXUVRE4u3L--
--------------1cBoy0juGTJNFH2GDTJVwO5m--
"""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Re: Project Update"
    assert result["from_addr"] == "alice@example.com"
    assert result["body"] == "This is the decrypted body."


def test_parse_pgp_encrypted_email_with_nested_multipart():
    """Test body extraction from PGP email with nested multipart/mixed inside octet-stream."""
    raw_email = """From: sender@example.com
Subject: ...
Date: Mon, 7 Apr 2025 18:54:55 +0200
Message-ID: <test@example.com>
MIME-Version: 1.0
Content-Type: multipart/encrypted;
 protocol="application/pgp-encrypted";
 boundary="----outer"

This is an OpenPGP/MIME encrypted message
------outer
Content-Type: application/pgp-encrypted
Content-Description: PGP/MIME version identification

Version: 1

------outer
Content-Type: application/octet-stream; name="encrypted.asc"
Content-Description: OpenPGP encrypted message
Content-Disposition: inline; filename="encrypted.asc"

Content-Type: multipart/mixed; boundary="----inner";
 protected-headers="v1"
Subject: Re: Actual Subject

------inner
Content-Type: multipart/mixed; boundary="----innermost"

------innermost
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: 8bit

Hallo,

ich habe gehört, dass sich dieser auch mit dem Fall beschäftigt.

Viele Grüße
------innermost
Content-Type: application/pdf; name="document.pdf"
Content-Disposition: attachment; filename="document.pdf"
Content-Transfer-Encoding: base64

JVBER
------innermost--

------inner--
------outer--
"""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Re: Actual Subject"
    assert "gehört" in result["body"]
    assert "beschäftigt" in result["body"]
    assert "Grüße" in result["body"]


def test_parse_pgp_email_placeholder_re_dots():
    """Test that 'Re: ...' is also recognized as a placeholder subject."""
    raw_email = """From: test@example.com
Subject: Re: ...
Date: Mon, 1 Jan 2024 12:00:00 +0000

Content-Type: multipart/mixed; boundary="boundary";
 protected-headers="v1"
Subject: Re: Actual Subject

Body text."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Re: Actual Subject"


def test_parse_pgp_email_unquoted_protected_headers_and_encoded_subject():
    """Test PGP email with unquoted protected-headers value and RFC 2047 encoded folded subject."""
    raw_email = """From: Alice Sender <alice@example.com>
Subject: ...
Date: Tue, 8 Apr 2025 11:53:45 +0200
Message-ID: <test@example.com>
MIME-Version: 1.0
Content-Type: multipart/encrypted; protocol="application/pgp-encrypted";
    boundary="zfdfc6ju2ga26gbs"
Content-Disposition: inline

--zfdfc6ju2ga26gbs
Content-Type: application/pgp-encrypted
Content-Disposition: attachment

Version: 1

--zfdfc6ju2ga26gbs
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="msg.asc"

Content-Type: multipart/mixed; protected-headers=v1;
    boundary="edtvsywf3y23w5sr"
Content-Disposition: inline
Content-Transfer-Encoding: 8bit
Subject: Re: Complaint to the =?utf-8?Q?Aufsichtsbeh=C3=B6rde?=
 =?utf-8?Q?_f=C3=BCr?= Datenschutz
MIME-Version: 1.0

--edtvsywf3y23w5sr
Content-Type: text/plain; charset=UTF-8

Test body.
--edtvsywf3y23w5sr--
--zfdfc6ju2ga26gbs--
"""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Re: Complaint to the Aufsichtsbehörde für Datenschutz"


def test_parse_email_with_rfc2047_encoded_subject():
    """Test that RFC 2047 encoded subjects in regular (non-PGP) emails are decoded."""
    raw_email = """From: Test User <test@example.com>
Subject: =?UTF-8?Q?Re=3A_Einladung_zum_Sommerfest_f=C3=BCr?=
 =?UTF-8?Q?_alle_Mitglieder?=
Date: Tue, 8 Apr 2025 14:38:30 +0200
Message-ID: <test-rfc2047@example.com>
Content-Type: text/plain; charset=UTF-8

Test body."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Re: Einladung zum Sommerfest f\u00fcr alle Mitglieder"
    assert "=?UTF-8?" not in result["subject"]


def test_non_placeholder_subject_not_overridden():
    """Test that a real subject is not replaced by protected-headers subject."""
    raw_email = """From: test@example.com
Subject: Real Subject
Date: Mon, 1 Jan 2024 12:00:00 +0000

Content-Type: multipart/mixed; boundary="boundary";
 protected-headers="v1"
Subject: Different Subject

Body text."""

    result = parse_raw_email(raw_email)
    assert result["subject"] == "Real Subject"


def test_parse_email_with_rfc2047_encoded_sender_name():
    """Test that RFC 2047 encoded sender names are decoded."""
    raw_email = """From: =?UTF-8?B?VGVzdCBVc2VyIHZpYSBUZXN0IE9yZyBEw7xzc2VsZG9yZg==?= =?UTF-8?B?IGUuVi4=?= <test@example.com>
Subject: Test Subject
Date: Tue, 8 Apr 2025 14:38:30 +0200
Message-ID: <test-sender-decode@example.com>
Content-Type: text/plain; charset=UTF-8

Test body."""

    result = parse_raw_email(raw_email)
    assert result["from_name"] == "Test User via Test Org D\u00fcsseldorf e.V."
    assert "=?UTF-8?" not in result["from_name"]


def test_pgp_body_quoted_printable_iso8859():
    """Test that QP-encoded iso-8859-1 bodies in PGP emails are decoded."""
    raw_email = """From: test@example.com
Subject: ...
Date: Fri, 11 Apr 2025 11:47:31 +0200
Message-ID: <test-qp-body@example.com>
MIME-Version: 1.0
Content-Type: multipart/encrypted; protocol="application/pgp-encrypted";
    boundary="testboundary"

--testboundary
Content-Type: application/pgp-encrypted
Content-Disposition: attachment

Version: 1

--testboundary
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="msg.asc"

Content-Type: text/plain; charset=iso-8859-1
Content-Disposition: inline
Content-Transfer-Encoding: quoted-printable

Passt f=FCr mich auch so.

Viele Gr=FC=DFe

--testboundary--"""

    result = parse_raw_email(raw_email)
    assert "f\u00fcr" in result["body"]  # ü
    assert "Gr\u00fc\u00dfe" in result["body"]  # üße
    assert "=FC" not in result["body"]
    assert "=DF" not in result["body"]
