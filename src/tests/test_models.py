from django.utils import timezone

from brett.core.models import Card, Correspondent, Entry


def test_board_str(board):
    assert str(board) == "Test Board"


def test_correspondent_str_with_name(correspondent):
    assert str(correspondent) == "John Doe <john@example.com>"


def test_correspondent_str_without_name(board):
    correspondent = Correspondent.objects.create(board=board, email="test@example.com")
    assert str(correspondent) == "test@example.com"


def test_column_str(column):
    assert str(column) == "Test Board - Todo"


def test_card_str(card):
    assert str(card) == "Test Card"


def test_tag_str(tag):
    assert str(tag) == "vote"


def test_entry_str_with_summary(entry):
    assert str(entry) == "test@example.com: +1"


def test_entry_str_without_summary(card):
    entry = Entry.objects.create(
        card=card,
        from_addr="sender@example.com",
        subject="This is a very long subject line that should be truncated",
        date=timezone.now(),
        body="Email body",
    )
    assert str(entry).startswith("sender@example.com: This is a very long")
    assert len(str(entry).split(": ")[1]) <= 50


def test_card_entry_count_with_no_entries(card):
    assert card.entry_count == 0


def test_card_entry_count_with_entries(card):
    Entry.objects.create(
        card=card,
        from_addr="sender1@example.com",
        subject="Subject 1",
        date=timezone.now(),
        body="Body 1",
    )
    Entry.objects.create(
        card=card,
        from_addr="sender2@example.com",
        subject="Subject 2",
        date=timezone.now(),
        body="Body 2",
    )
    assert card.entry_count == 2


def test_entry_parsed_body_with_raw_message(card):
    """Test that parsed_body extracts body from raw_message."""
    entry = Entry.objects.create(
        card=card,
        from_addr="test@example.com",
        subject="Test",
        message_id="<test@example.com>",
        date=timezone.now(),
        body="Original body",
        raw_message="Subject: Test\nFrom: test@example.com\n\nExtracted body from raw message",
    )
    assert entry.parsed_body == "Extracted body from raw message"


def test_entry_parsed_body_with_raw_message_no_separator(card):
    """Test parsed_body when raw_message has no double newline separator."""
    entry = Entry.objects.create(
        card=card,
        from_addr="test@example.com",
        subject="Test",
        message_id="<test@example.com>",
        date=timezone.now(),
        body="Original body",
        raw_message="No separator in this message",
    )
    assert entry.parsed_body == "No separator in this message"


def test_entry_parsed_body_without_raw_message(card):
    """Test that parsed_body falls back to body when no raw_message."""
    entry = Entry.objects.create(
        card=card,
        from_addr="test@example.com",
        subject="Test",
        message_id="<test@example.com>",
        date=timezone.now(),
        body="Fallback body",
        raw_message="",
    )
    assert entry.parsed_body == "Fallback body"


def test_card_update_dates_from_entries_with_no_entries(column):
    """Test update_dates_from_entries when card has no entries."""
    card = Card.objects.create(
        column=column,
        title="Empty Card",
    )
    # Should not raise an error
    card.update_dates_from_entries()
    # Dates should remain None
    assert card.start_date is None
    assert card.last_update_date is None
