from django.contrib import admin, messages
from django.db import transaction

from .models import Board, Card, Column, Correspondent, Entry, Tag


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 1
    fields = ["name", "position"]
    ordering = ["position", "name"]


class CardInline(admin.TabularInline):
    model = Card
    extra = 0
    fields = ["title", "last_update_date"]
    readonly_fields = ["last_update_date"]
    show_change_link = True
    ordering = ["-last_update_date"]


class EntryInline(admin.StackedInline):
    model = Entry
    extra = 1
    fields = ["from_addr", "subject", "date", "summary", "body", "tags"]
    filter_horizontal = ["tags"]
    ordering = ["date"]


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "column_count"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["core_team"]
    inlines = [ColumnInline]
    fieldsets = [
        (None, {"fields": ["name", "slug", "description"]}),
        ("Core Team", {"fields": ["core_team"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]

    def column_count(self, obj):
        return obj.columns.count()

    column_count.short_description = "Columns"


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ["name", "board", "position", "card_count"]
    list_filter = ["board"]
    search_fields = ["name", "board__name"]
    inlines = [CardInline]
    fields = ["board", "name", "position", "created_at"]
    readonly_fields = ["created_at"]

    def card_count(self, obj):
        return obj.cards.count()

    card_count.short_description = "Cards"


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "column",
        "start_date",
        "last_update_date",
        "entry_count",
    ]
    list_filter = ["column__board", "column"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [EntryInline]
    fieldsets = [
        (None, {"fields": ["column", "title", "description"]}),
        (
            "Dates",
            {"fields": ["start_date", "last_update_date", "created_at", "updated_at"]},
        ),
    ]

    def entry_count(self, obj):
        return obj.entries.count()

    entry_count.short_description = "Entries"


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["__str__", "card", "from_addr", "date", "tag_list"]
    list_filter = ["tags", "card__column__board"]
    search_fields = ["from_addr", "subject", "body", "summary"]
    filter_horizontal = ["tags"]
    readonly_fields = ["created_at"]
    fieldsets = [
        (None, {"fields": ["card"]}),
        (
            "Email Details",
            {"fields": ["from_addr", "subject", "message_id", "date"]},
        ),
        ("Content", {"fields": ["summary", "body", "tags"]}),
        ("Metadata", {"fields": ["created_at"]}),
    ]

    def tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])

    tag_list.short_description = "Tags"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "entry_count"]
    search_fields = ["name"]
    fields = ["name", "color"]

    def entry_count(self, obj):
        return obj.entries.count()

    entry_count.short_description = "Entries"


@admin.register(Correspondent)
class CorrespondentAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "board", "alias_count"]
    list_filter = ["board"]
    search_fields = ["email", "name"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["merge_correspondents"]
    fieldsets = [
        (None, {"fields": ["board", "email", "name"]}),
        ("Aliases", {"fields": ["aliases"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]

    def alias_count(self, obj):
        return len(obj.aliases) if obj.aliases else 0

    alias_count.short_description = "Aliases"

    @admin.action(description="Merge selected correspondents")
    def merge_correspondents(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(
                request,
                "Select at least 2 correspondents to merge.",
                messages.ERROR,
            )
            return

        boards = set(queryset.values_list("board_id", flat=True))
        if len(boards) > 1:
            self.message_user(
                request,
                "All selected correspondents must belong to the same board.",
                messages.ERROR,
            )
            return

        correspondents = list(queryset.order_by("pk"))
        primary = correspondents[0]
        secondaries = correspondents[1:]

        with transaction.atomic():
            for secondary in secondaries:
                # Collect aliases
                if secondary.email != primary.email and secondary.email not in (
                    primary.aliases or []
                ):
                    primary.aliases = (primary.aliases or []) + [secondary.email]
                for alias in secondary.aliases or []:
                    if alias != primary.email and alias not in primary.aliases:
                        primary.aliases.append(alias)

                # Reassign entries
                Entry.objects.filter(sender=secondary).update(sender=primary)

                # Inherit name if primary has none
                if not primary.name and secondary.name:
                    primary.name = secondary.name

                # Also update core_team references
                for board in secondary.core_team_boards.all():
                    board.core_team.remove(secondary)
                    board.core_team.add(primary)

                secondary.delete()

            primary.save()

        merged_count = len(secondaries)
        self.message_user(
            request,
            f"Merged {merged_count + 1} correspondents into {primary}.",
            messages.SUCCESS,
        )
