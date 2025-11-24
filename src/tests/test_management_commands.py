from io import StringIO

import pytest
from django.core.management import call_command

from brett.core.models import Board, Tag


@pytest.mark.django_db
def test_setup_defaults_creates_board():

    out = StringIO()
    call_command("setup_defaults", stdout=out)

    assert Board.objects.filter(name="Default Board").exists()
    board = Board.objects.get(name="Default Board")
    assert board.description == "Default kanban board for email threads"
    assert "Created board: Default Board" in out.getvalue()
    assert board.columns.count() == 5

    columns = list(board.columns.all())
    assert columns[0].name == "Todo"
    assert columns[0].position == 0
    assert columns[1].name == "Waiting"
    assert columns[1].position == 1
    assert columns[2].name == "Voting"
    assert columns[2].position == 2
    assert columns[3].name == "Decided"
    assert columns[3].position == 3
    assert columns[4].name == "Archived"
    assert columns[4].position == 4
    assert Tag.objects.filter(name="vote").exists()
    assert Tag.objects.filter(name="question").exists()

    vote_tag = Tag.objects.get(name="vote")
    question_tag = Tag.objects.get(name="question")

    assert vote_tag.color == "#dc3545"
    assert question_tag.color == "#0dcaf0"

    out2 = StringIO()
    call_command("setup_defaults", stdout=out2)
    assert "Board already exists: Default Board" in out2.getvalue()
    assert "Column already exists: Todo" in out2.getvalue()
    assert "Tag already exists: vote" in out2.getvalue()

    assert Board.objects.filter(name="Default Board").count() == 1
    board = Board.objects.get(name="Default Board")
    assert board.columns.count() == 5
    assert Tag.objects.count() == 2
