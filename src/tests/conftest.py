import pytest
from django.utils import timezone

from brett.core.models import Board, Card, Column, Correspondent, Entry, Tag


@pytest.fixture
def board(db):
    return Board.objects.create(
        name="Test Board", slug="test-board", description="Test description"
    )


@pytest.fixture
def column(db, board):
    return Column.objects.create(board=board, name="Todo", position=0)


@pytest.fixture
def columns(db, board):
    return [
        Column.objects.create(board=board, name="Todo", position=0),
        Column.objects.create(board=board, name="In Progress", position=1),
        Column.objects.create(board=board, name="Done", position=2),
    ]


@pytest.fixture
def card(db, column):
    return Card.objects.create(
        column=column,
        title="Test Card",
        description="Test card description",
        start_date=timezone.now(),
        last_update_date=timezone.now(),
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="vote", color="#ff5733")


@pytest.fixture
def tags(db):
    return [
        Tag.objects.create(name="vote", color="#ff5733"),
        Tag.objects.create(name="question", color="#3498db"),
    ]


@pytest.fixture
def entry(db, card):
    return Entry.objects.create(
        card=card,
        from_addr="test@example.com",
        subject="Test Subject",
        message_id="<test@example.com>",
        date=timezone.now(),
        body="Test email body",
        summary="+1",
    )


@pytest.fixture
def correspondent(db, board):
    return Correspondent.objects.create(
        board=board,
        email="john@example.com",
        name="John Doe",
        aliases=["john.doe@example.com", "j.doe@example.com"],
    )


@pytest.fixture
def correspondents(db, board):
    return [
        Correspondent.objects.create(
            board=board, email="alpha@example.com", name="Alpha User"
        ),
        Correspondent.objects.create(
            board=board, email="beta@example.com", name="Beta User"
        ),
        Correspondent.objects.create(
            board=board, email="gamma@example.com", name="Gamma User"
        ),
    ]
