from django.utils import timezone

from brett.core.models import Correspondent, Entry


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
