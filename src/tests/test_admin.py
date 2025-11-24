from django.contrib.admin.sites import AdminSite

from brett.core.admin import (
    BoardAdmin,
    CardAdmin,
    ColumnAdmin,
    EntryAdmin,
    TagAdmin,
)
from brett.core.models import Board, Card, Column, Entry, Tag


def test_board_admin_column_count(board, columns):
    board_admin = BoardAdmin(Board, AdminSite())
    assert board_admin.column_count(board) == 3


def test_column_admin_card_count(column, card):
    column_admin = ColumnAdmin(Column, AdminSite())
    assert column_admin.card_count(column) == 1


def test_card_admin_entry_count(card, entry):
    card_admin = CardAdmin(Card, AdminSite())
    assert card_admin.entry_count(card) == 1


def test_entry_admin_tag_list_empty(entry):
    entry_admin = EntryAdmin(Entry, AdminSite())
    assert entry_admin.tag_list(entry) == ""


def test_entry_admin_tag_list_with_tags(entry, tags):
    entry.tags.add(tags[0], tags[1])
    entry_admin = EntryAdmin(Entry, AdminSite())
    tag_list = entry_admin.tag_list(entry)
    assert "question" in tag_list
    assert "vote" in tag_list


def test_tag_admin_entry_count(tag, entry):
    entry.tags.add(tag)
    tag_admin = TagAdmin(Tag, AdminSite())
    assert tag_admin.entry_count(tag) == 1
