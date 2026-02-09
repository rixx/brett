from django.contrib.admin.sites import AdminSite
from django.contrib.messages import constants as message_constants
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.utils import timezone

from brett.core.admin import (
    BoardAdmin,
    CardAdmin,
    ColumnAdmin,
    CorrespondentAdmin,
    EntryAdmin,
    TagAdmin,
)
from brett.core.models import Board, Card, Column, Correspondent, Entry, Tag


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


def test_board_admin_has_core_team_filter_horizontal():
    board_admin = BoardAdmin(Board, AdminSite())
    assert "core_team" in board_admin.filter_horizontal


def _make_request_with_messages():
    factory = RequestFactory()
    request = factory.post("/admin/")
    request.session = "session"
    messages = FallbackStorage(request)
    request._messages = messages
    return request, messages


def test_merge_two_correspondents(board, card):
    c1 = Correspondent.objects.create(board=board, email="a@example.com", name="A User")
    c2 = Correspondent.objects.create(board=board, email="b@example.com", name="B User")
    Entry.objects.create(
        card=card,
        sender=c1,
        from_addr="a@example.com",
        subject="S",
        date=timezone.now(),
        body="body",
    )
    Entry.objects.create(
        card=card,
        sender=c2,
        from_addr="b@example.com",
        subject="S",
        date=timezone.now(),
        body="body",
    )

    admin = CorrespondentAdmin(Correspondent, AdminSite())
    request, msgs = _make_request_with_messages()
    queryset = Correspondent.objects.filter(pk__in=[c1.pk, c2.pk])
    admin.merge_correspondents(request, queryset)

    c1.refresh_from_db()
    assert "b@example.com" in c1.aliases
    assert Entry.objects.filter(sender=c1).count() == 2
    assert not Correspondent.objects.filter(pk=c2.pk).exists()


def test_merge_three_correspondents(board, card):
    c1 = Correspondent.objects.create(board=board, email="a@example.com", name="A User")
    c2 = Correspondent.objects.create(
        board=board, email="b@example.com", name="", aliases=["b2@example.com"]
    )
    c3 = Correspondent.objects.create(board=board, email="c@example.com", name="C User")
    for c in [c1, c2, c3]:
        Entry.objects.create(
            card=card,
            sender=c,
            from_addr=c.email,
            subject="S",
            date=timezone.now(),
            body="body",
        )

    admin = CorrespondentAdmin(Correspondent, AdminSite())
    request, msgs = _make_request_with_messages()
    queryset = Correspondent.objects.filter(pk__in=[c1.pk, c2.pk, c3.pk])
    admin.merge_correspondents(request, queryset)

    c1.refresh_from_db()
    assert set(c1.aliases) == {"b@example.com", "b2@example.com", "c@example.com"}
    assert Entry.objects.filter(sender=c1).count() == 3
    assert Correspondent.objects.filter(board=board).count() == 1


def test_merge_inherits_name(board):
    c1 = Correspondent.objects.create(board=board, email="a@example.com", name="")
    c2 = Correspondent.objects.create(board=board, email="b@example.com", name="B User")

    admin = CorrespondentAdmin(Correspondent, AdminSite())
    request, msgs = _make_request_with_messages()
    queryset = Correspondent.objects.filter(pk__in=[c1.pk, c2.pk])
    admin.merge_correspondents(request, queryset)

    c1.refresh_from_db()
    assert c1.name == "B User"


def test_merge_single_correspondent_errors(board, correspondent):
    admin = CorrespondentAdmin(Correspondent, AdminSite())
    request, msgs = _make_request_with_messages()
    queryset = Correspondent.objects.filter(pk=correspondent.pk)
    admin.merge_correspondents(request, queryset)

    stored = list(msgs)
    assert len(stored) == 1
    assert stored[0].level == message_constants.ERROR
    assert Correspondent.objects.filter(pk=correspondent.pk).exists()


def test_merge_cross_board_errors(board):
    other_board = Board.objects.create(name="Other", slug="other")
    c1 = Correspondent.objects.create(board=board, email="a@example.com")
    c2 = Correspondent.objects.create(board=other_board, email="b@example.com")

    admin = CorrespondentAdmin(Correspondent, AdminSite())
    request, msgs = _make_request_with_messages()
    queryset = Correspondent.objects.filter(pk__in=[c1.pk, c2.pk])
    admin.merge_correspondents(request, queryset)

    stored = list(msgs)
    assert len(stored) == 1
    assert stored[0].level == message_constants.ERROR
    # Both still exist
    assert Correspondent.objects.filter(pk__in=[c1.pk, c2.pk]).count() == 2
