import pytest
from django.urls import reverse
from django.utils import timezone

from brett.core.models import Board, Card, Column, Entry


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
    response = client.get(
        reverse("board_detail", kwargs={"slug": board.slug})
    )
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
