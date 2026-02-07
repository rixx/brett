import pytest
from django.urls import reverse
from django.utils import timezone

from brett.core.models import Board, Card, Column, Correspondent, Entry


@pytest.fixture
def multiple_boards(db):
    return [
        Board.objects.create(name="Board 1", slug="board-1", description="First board"),
        Board.objects.create(
            name="Board 2", slug="board-2", description="Second board"
        ),
    ]


@pytest.fixture
def board_with_columns_and_cards(db, board):
    col1 = Column.objects.create(board=board, name="Todo", position=0)
    col2 = Column.objects.create(board=board, name="Done", position=1)

    card1 = Card.objects.create(
        column=col1,
        title="Card 1",
        description="First card",
        last_update_date=timezone.now(),
    )
    Card.objects.create(
        column=col1,
        title="Card 2",
        description="Second card",
        last_update_date=timezone.now(),
    )
    Card.objects.create(
        column=col2,
        title="Card 3",
        description="Third card",
        last_update_date=timezone.now(),
    )

    Entry.objects.create(
        card=card1,
        from_addr="test@example.com",
        subject="Subject 1",
        date=timezone.now(),
        body="Body 1",
    )
    Entry.objects.create(
        card=card1,
        from_addr="test2@example.com",
        subject="Subject 2",
        date=timezone.now(),
        body="Body 2",
    )

    return board


def test_board_list_with_no_boards(client, db):
    response = client.get(reverse("board_list"))
    assert response.status_code == 200
    assert "No boards found" in response.content.decode()


def test_board_list_with_multiple_boards(client, multiple_boards):
    response = client.get(reverse("board_list"))
    assert response.status_code == 200
    assert "Board 1" in response.content.decode()
    assert "Board 2" in response.content.decode()
    assert "First board" in response.content.decode()
    assert "Second board" in response.content.decode()


def test_board_list_with_single_board_redirects(client, board):
    response = client.get(reverse("board_list"))
    assert response.status_code == 302
    assert response.url == reverse("board_detail", kwargs={"slug": "test-board"})


def test_board_detail_renders_board_info(client, board):
    response = client.get(reverse("board_detail", kwargs={"slug": board.slug}))
    assert response.status_code == 200
    assert "Test Board" in response.content.decode()


def test_board_detail_renders_columns(client, board_with_columns_and_cards):
    response = client.get(
        reverse("board_detail", kwargs={"slug": board_with_columns_and_cards.slug})
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Todo" in content
    assert "Done" in content


def test_board_detail_renders_cards(client, board_with_columns_and_cards):
    response = client.get(
        reverse("board_detail", kwargs={"slug": board_with_columns_and_cards.slug})
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Card 1" in content
    assert "Card 2" in content
    assert "Card 3" in content


def test_board_detail_shows_entry_count(client, board_with_columns_and_cards):
    response = client.get(
        reverse("board_detail", kwargs={"slug": board_with_columns_and_cards.slug})
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "2 messages" in content
    assert "0 messages" in content


def test_board_detail_shows_new_card_button(client, board_with_columns_and_cards):
    response = client.get(
        reverse("board_detail", kwargs={"slug": board_with_columns_and_cards.slug})
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "New Card" in content


def test_board_detail_404_for_nonexistent_slug(client, db):
    response = client.get(reverse("board_detail", kwargs={"slug": "nonexistent"}))
    assert response.status_code == 404


# Card detail view tests
def test_card_detail_renders_card_info(client, card):
    response = client.get(reverse("card_detail", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert card.description in content


def test_card_detail_renders_entries(client, card, entry):
    response = client.get(reverse("card_detail", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert entry.subject in content
    assert entry.from_addr in content
    assert entry.summary in content


def test_card_detail_shows_column_info(client, card):
    response = client.get(reverse("card_detail", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.column.name in content


def test_card_detail_shows_back_link(client, card):
    response = client.get(reverse("card_detail", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Back to Board" in content


def test_card_detail_shows_add_entry_link(client, card):
    response = client.get(reverse("card_detail", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Add Entry" in content


def test_card_detail_404_for_nonexistent_card(client, db):
    response = client.get(reverse("card_detail", kwargs={"card_id": 99999}))
    assert response.status_code == 404


def test_card_detail_htmx_request_returns_partial(client, card):
    response = client.get(
        reverse("card_detail", kwargs={"card_id": card.id}),
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    content = response.content.decode()
    # Partial template should not contain base template elements
    assert "<html" not in content
    assert card.title in content


def test_card_edit_title_get_returns_form(client, card):
    response = client.get(reverse("card_edit_title", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert "input" in content
    assert 'name="title"' in content


def test_card_edit_title_post_updates_card(client, card):
    new_title = "Updated Card Title"
    response = client.post(
        reverse("card_edit_title", kwargs={"card_id": card.id}),
        {"title": new_title},
    )
    assert response.status_code == 200
    card.refresh_from_db()
    assert card.title == new_title


def test_card_edit_title_post_empty_title_does_not_update(client, card):
    original_title = card.title
    response = client.post(
        reverse("card_edit_title", kwargs={"card_id": card.id}),
        {"title": ""},
    )
    assert response.status_code == 200
    card.refresh_from_db()
    assert card.title == original_title


def test_card_edit_description_get_returns_form(client, card):
    response = client.get(reverse("card_edit_description", kwargs={"card_id": card.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.description in content
    assert "textarea" in content
    assert 'name="description"' in content


def test_card_edit_description_post_updates_card(client, card):
    new_description = "Updated description for this card"
    response = client.post(
        reverse("card_edit_description", kwargs={"card_id": card.id}),
        {"description": new_description},
    )
    assert response.status_code == 200
    card.refresh_from_db()
    assert card.description == new_description


def test_card_edit_description_post_empty_description_updates(client, card):
    response = client.post(
        reverse("card_edit_description", kwargs={"card_id": card.id}),
        {"description": ""},
    )
    assert response.status_code == 200
    card.refresh_from_db()
    assert card.description == ""


# Add card tests
def test_add_card_get_returns_form(client, column):
    response = client.get(reverse("add_card", kwargs={"column_id": column.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "add-card-form" in content
    assert 'name="title"' in content
    assert 'name="description"' in content


def test_add_card_post_creates_card(client, column):
    initial_count = Card.objects.filter(column=column).count()
    response = client.post(
        reverse("add_card", kwargs={"column_id": column.id}),
        {"title": "New Test Card", "description": "Test description"},
    )
    assert response.status_code == 200
    assert Card.objects.filter(column=column).count() == initial_count + 1
    new_card = Card.objects.filter(column=column).latest("created_at")
    assert new_card.title == "New Test Card"
    assert new_card.description == "Test description"
    # Dates are None until entries are added
    assert new_card.start_date is None
    assert new_card.last_update_date is None


def test_add_card_post_returns_card_html(client, column):
    response = client.post(
        reverse("add_card", kwargs={"column_id": column.id}),
        {"title": "New Test Card", "description": "Test description"},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "New Test Card" in content
    assert "card" in content


def test_add_card_post_empty_title_does_not_create(client, column):
    initial_count = Card.objects.filter(column=column).count()
    response = client.post(
        reverse("add_card", kwargs={"column_id": column.id}),
        {"title": "", "description": "Test description"},
    )
    assert response.status_code == 200
    assert Card.objects.filter(column=column).count() == initial_count


def test_add_card_post_without_description_creates_card(client, column):
    response = client.post(
        reverse("add_card", kwargs={"column_id": column.id}),
        {"title": "Card without description"},
    )
    assert response.status_code == 200
    new_card = Card.objects.filter(column=column).latest("created_at")
    assert new_card.title == "Card without description"
    assert new_card.description == ""


def test_cancel_add_card_returns_button(client, column):
    response = client.get(reverse("cancel_add_card", kwargs={"column_id": column.id}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "new-card-btn" in content
    assert "New Card" in content


# Move card tests
def test_move_card_to_different_column(client, card, board):
    # Create a second column for testing move
    target_column = Column.objects.create(board=board, name="In Progress", position=1)
    original_column = card.column

    response = client.post(
        reverse("move_card", kwargs={"card_id": card.id}),
        {"column_id": target_column.id},
    )
    assert response.status_code == 200

    card.refresh_from_db()
    assert card.column == target_column
    assert card.column != original_column
    assert card.last_update_date is not None


def test_move_card_does_not_update_dates(client, card, column):
    # Dates are based on entries, not user actions
    original_start = card.start_date
    original_last_update = card.last_update_date

    response = client.post(
        reverse("move_card", kwargs={"card_id": card.id}),
        {"column_id": column.id},
    )
    assert response.status_code == 200

    card.refresh_from_db()
    assert card.start_date == original_start
    assert card.last_update_date == original_last_update


def test_move_card_without_column_id_fails(client, card):
    response = client.post(
        reverse("move_card", kwargs={"card_id": card.id}),
        {},
    )
    assert response.status_code == 400


def test_move_card_with_invalid_column_id_fails(client, card):
    response = client.post(
        reverse("move_card", kwargs={"card_id": card.id}),
        {"column_id": 99999},
    )
    assert response.status_code == 404


def test_move_card_get_method_not_allowed(client, card, column):
    response = client.get(
        reverse("move_card", kwargs={"card_id": card.id}),
    )
    assert response.status_code == 405


def test_move_nonexistent_card_fails(client, column):
    response = client.post(
        reverse("move_card", kwargs={"card_id": 99999}),
        {"column_id": column.id},
    )
    assert response.status_code == 404


# Import email tests
def test_import_email_get(client):
    response = client.get(reverse("import_email"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "raw_message" in content
    assert "Paste raw email" in content


def test_import_email_post_parses_email(client, db):
    raw_email = """From: test@example.com
Subject: Test Subject
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>

This is the email body.
"""
    response = client.post(reverse("import_email"), {"raw_message": raw_email})
    assert response.status_code == 302
    assert response.url == reverse("suggest_cards")


def test_import_email_post_empty_fails(client):
    response = client.post(reverse("import_email"), {"raw_message": ""})
    assert response.status_code == 200
    content = response.content.decode()
    assert "Please paste an email" in content


def test_import_email_get_without_params(client):
    # GET request without card_id or new_card params
    response = client.get(reverse("import_email"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "raw_message" in content  # Should show the form


def test_suggest_cards_without_session_redirects(client):
    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 302
    assert response.url == reverse("import_email")


def test_suggest_cards_shows_candidates(client, card):
    # Set up session with parsed email
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": card.title,  # Same subject as existing card
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content


def test_suggest_cards_exact_match_case_insensitive(client, board, column):
    # Create a card with specific title
    card = Card.objects.create(
        column=column,
        title="Important Discussion",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )

    # Test exact match with different case
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Re: IMPORTANT DISCUSSION",  # Different case, with Re: prefix
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert "Exact subject match" in content


def test_suggest_cards_bidirectional_substring_match(client, board, column):
    # Create a card with a title
    card = Card.objects.create(
        column=column,
        title="Project Alpha Update",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )

    # Test: email subject contains card title
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Re: Project Alpha Update - Next Steps",
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert "Similar subject" in content


def test_suggest_cards_reverse_substring_match(client, board, column):
    # Create a card with a longer title
    card = Card.objects.create(
        column=column,
        title="Re: Budget Discussion - Q4 2024",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )

    # Test: card title contains email subject
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Budget Discussion",
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert "Similar subject" in content


def test_suggest_cards_matches_previous_entries(client, board, column):
    # Create a card with entries
    card = Card.objects.create(
        column=column,
        title="Some Card",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )
    Entry.objects.create(
        card=card,
        from_addr="old@example.com",
        subject="Feature Request: Dark Mode",
        message_id="<old123@example.com>",
        date=timezone.now(),
        body="Original request",
    )

    # Test: match against entry subject
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Re: Feature Request: Dark Mode",
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    assert card.title in content
    assert "Previous entry:" in content


def test_suggest_cards_in_reply_to_matching(client, board, column):
    # Create a card with an entry
    card = Card.objects.create(
        column=column,
        title="Unique Thread Title XYZ123",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )
    original_message_id = "<original123@example.com>"
    Entry.objects.create(
        card=card,
        from_addr="original@example.com",
        subject="Some Different Subject",
        message_id=original_message_id,
        date=timezone.now(),
        body="Original message",
    )

    # Test: in-reply-to matching (subject doesn't match, only in-reply-to does)
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Re: Completely Unrelated Subject",
        "in_reply_to": original_message_id,
        "date": "2024-01-01 12:00:00",
        "body": "Reply body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()
    # Card should be found via in-reply-to even though subjects don't match
    assert card.title in content
    assert "Reply to:" in content


def test_suggest_cards_no_duplicate_suggestions(client, board, column):
    # Create a card that would match multiple ways
    card = Card.objects.create(
        column=column,
        title="Meeting Notes",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )
    Entry.objects.create(
        card=card,
        from_addr="original@example.com",
        subject="Meeting Notes",
        message_id="<meeting123@example.com>",
        date=timezone.now(),
        body="Original notes",
    )

    # Email that would match both by title and by entry
    session = client.session
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Re: Meeting Notes",
        "date": "2024-01-01 12:00:00",
        "body": "Test body",
    }
    session.save()

    response = client.get(reverse("suggest_cards"))
    assert response.status_code == 200
    content = response.content.decode()

    # Card should appear only once in the suggestions
    # Count occurrences of candidate-card divs
    candidate_count = content.count('class="candidate-card"')
    assert candidate_count == 1


def test_confirm_import_creates_entry(client, card):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_count = Entry.objects.filter(card=card).count()

    response = client.post(reverse("confirm_import", kwargs={"card_id": card.id}))
    assert response.status_code == 302
    assert response.url == reverse("card_detail", kwargs={"card_id": card.id})

    # Verify entry was created
    assert Entry.objects.filter(card=card).count() == initial_count + 1
    new_entry = Entry.objects.filter(card=card).latest("created_at")
    assert new_entry.from_addr == "test@example.com"
    assert new_entry.subject == "Test Subject"
    assert new_entry.body == "Test body"


def test_confirm_import_saves_summary(client, card):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    # Post with a summary
    response = client.post(
        reverse("confirm_import", kwargs={"card_id": card.id}),
        {"summary": "+1"},
    )
    assert response.status_code == 302

    # Verify entry has summary
    new_entry = Entry.objects.filter(card=card).latest("created_at")
    assert new_entry.summary == "+1"


def test_confirm_import_without_summary(client, card):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    # Post without a summary
    response = client.post(reverse("confirm_import", kwargs={"card_id": card.id}))
    assert response.status_code == 302

    # Verify entry has empty summary
    new_entry = Entry.objects.filter(card=card).latest("created_at")
    assert new_entry.summary == ""


def test_confirm_import_rejects_duplicate_message_id(client, card):
    # Create an existing entry with a specific message-ID
    existing_message_id = "<duplicate123@example.com>"
    Entry.objects.create(
        card=card,
        from_addr="original@example.com",
        subject="Original Email",
        message_id=existing_message_id,
        date=timezone.now(),
        body="Original body",
    )

    # Try to import an email with the same message-ID
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Duplicate Email",
        "message_id": existing_message_id,
        "date": parsed_date.isoformat(),
        "body": "Duplicate body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_count = Entry.objects.filter(card=card).count()

    response = client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Should not create a new entry
    assert Entry.objects.filter(card=card).count() == initial_count

    # Should show error message
    assert response.status_code == 200
    content = response.content.decode()
    assert "already been imported" in content


def test_confirm_import_allows_email_without_message_id(client, card):
    # Import should work if message-ID is empty
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Test Subject",
        "message_id": "",  # Empty message-ID
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_count = Entry.objects.filter(card=card).count()

    response = client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Should create entry even without message-ID
    assert response.status_code == 302
    assert Entry.objects.filter(card=card).count() == initial_count + 1


def test_confirm_import_updates_card_date(client, card):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    original_date = card.last_update_date

    client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    card.refresh_from_db()
    assert card.last_update_date >= original_date


def test_card_dates_reflect_earliest_and_latest_entries(client, card):
    # Card should have dates from entries only
    from datetime import timedelta

    # Add three entries with different dates
    early_date = timezone.now() - timedelta(days=10)
    middle_date = timezone.now() - timedelta(days=5)
    late_date = timezone.now() - timedelta(days=1)

    Entry.objects.create(
        card=card,
        from_addr="test1@example.com",
        subject="First email",
        message_id="<first@example.com>",
        date=middle_date,
        body="Middle entry",
    )
    Entry.objects.create(
        card=card,
        from_addr="test2@example.com",
        subject="Second email",
        message_id="<second@example.com>",
        date=early_date,
        body="Earliest entry",
    )
    Entry.objects.create(
        card=card,
        from_addr="test3@example.com",
        subject="Third email",
        message_id="<third@example.com>",
        date=late_date,
        body="Latest entry",
    )

    # Update card dates
    card.update_dates_from_entries()

    # Verify start_date is earliest entry and last_update_date is latest entry
    assert card.start_date == early_date
    assert card.last_update_date == late_date


def test_confirm_import_new_creates_card_and_entry(client, board, column):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "New Email Subject",
        "message_id": "<test456@example.com>",
        "date": parsed_date.isoformat(),
        "body": "New email body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_card_count = Card.objects.count()
    initial_entry_count = Entry.objects.count()

    response = client.post(reverse("confirm_import_new"))
    assert response.status_code == 302

    # Verify card was created
    assert Card.objects.count() == initial_card_count + 1
    new_card = Card.objects.latest("created_at")
    assert new_card.title == "New Email Subject"

    # Verify entry was created
    assert Entry.objects.count() == initial_entry_count + 1


def test_confirm_import_new_rejects_duplicate_message_id(client, board, column, card):
    # Create an existing entry with a specific message-ID
    existing_message_id = "<duplicate456@example.com>"
    Entry.objects.create(
        card=card,
        from_addr="original@example.com",
        subject="Original Email",
        message_id=existing_message_id,
        date=timezone.now(),
        body="Original body",
    )

    # Try to create a new card with an email that has the same message-ID
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "Duplicate Email",
        "message_id": existing_message_id,
        "date": parsed_date.isoformat(),
        "body": "Duplicate body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_card_count = Card.objects.count()
    initial_entry_count = Entry.objects.count()

    response = client.post(reverse("confirm_import_new"))

    # Should not create a new card or entry
    assert Card.objects.count() == initial_card_count
    assert Entry.objects.count() == initial_entry_count

    # Should show error message
    assert response.status_code == 200
    content = response.content.decode()
    assert "already been imported" in content


def test_confirm_import_new_saves_summary(client, board, column):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "subject": "New Email Subject",
        "message_id": "<test456@example.com>",
        "date": parsed_date.isoformat(),
        "body": "New email body",
        "raw_message": "Full raw message",
    }
    session.save()

    # Post with a summary
    response = client.post(
        reverse("confirm_import_new"),
        {"summary": "questions"},
    )
    assert response.status_code == 302

    # Verify entry has summary
    new_entry = Entry.objects.latest("created_at")
    assert new_entry.summary == "questions"


# Correspondent matching tests
def test_import_creates_correspondent(client, card):
    # Set up session with parsed email
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "john@example.com",
        "from_name": "John Doe",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_correspondent_count = Correspondent.objects.count()

    client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Verify correspondent was created
    assert Correspondent.objects.count() == initial_correspondent_count + 1
    correspondent = Correspondent.objects.latest("created_at")
    assert correspondent.email == "john@example.com"
    assert correspondent.name == "John Doe"
    assert correspondent.board == card.column.board


def test_import_matches_existing_correspondent(client, card, correspondent):
    # correspondent fixture is already created with email "john@example.com"
    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": correspondent.email,
        "from_name": "Different Name",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_correspondent_count = Correspondent.objects.count()

    client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Should not create new correspondent
    assert Correspondent.objects.count() == initial_correspondent_count

    # Verify entry is associated with existing correspondent
    new_entry = Entry.objects.filter(card=card).latest("created_at")
    assert new_entry.sender == correspondent


def test_import_matches_correspondent_alias(client, card, board):
    # Create correspondent with alias
    correspondent = Correspondent.objects.create(
        board=board,
        email="primary@example.com",
        name="John Doe",
        aliases=["alias@example.com", "john@example.com"],
    )

    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "alias@example.com",
        "from_name": "John Doe",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    initial_correspondent_count = Correspondent.objects.count()

    client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Should not create new correspondent
    assert Correspondent.objects.count() == initial_correspondent_count

    # Verify entry is associated with correspondent found via alias
    new_entry = Entry.objects.filter(card=card).latest("created_at")
    assert new_entry.sender == correspondent


def test_import_updates_correspondent_name_if_missing(client, card, board):
    # Create correspondent without name
    correspondent = Correspondent.objects.create(
        board=board, email="test@example.com", name="", aliases=[]
    )

    session = client.session
    parsed_date = timezone.now()
    session["parsed_email"] = {
        "from_addr": "test@example.com",
        "from_name": "Test User",
        "subject": "Test Subject",
        "message_id": "<test123@example.com>",
        "date": parsed_date.isoformat(),
        "body": "Test body",
        "raw_message": "Full raw message",
    }
    session.save()

    client.post(reverse("confirm_import", kwargs={"card_id": card.id}))

    # Verify correspondent name was updated
    correspondent.refresh_from_db()
    assert correspondent.name == "Test User"
