from django.core.management.base import BaseCommand

from brett.core.models import Board, Column, Tag


class Command(BaseCommand):
    help = "Create default board with columns and tags"

    def add_arguments(self, parser):
        parser.add_argument(
            "--board-name",
            type=str,
            default="Default Board",
            help="Name of the default board (default: 'Default Board')",
        )

    def handle(self, *args, **options):
        board_name = options["board_name"]

        board, created = Board.objects.get_or_create(
            name=board_name,
            slug=board_name,
            defaults={"description": "Default kanban board for email threads"},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created board: {board.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Board already exists: {board.name}"))

        default_columns = [
            ("Todo", 0),
            ("Waiting", 1),
            ("Voting", 2),
            ("Decided", 3),
            ("Archived", 4),
        ]

        for column_name, position in default_columns:
            column, created = Column.objects.get_or_create(
                board=board,
                name=column_name,
                defaults={"position": position},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  Created column: {column_name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  Column already exists: {column_name}")
                )

        default_tags = [
            ("vote", "#dc3545"),
            ("question", "#0dcaf0"),
        ]

        for tag_name, color in default_tags:
            tag, created = Tag.objects.get_or_create(
                name=tag_name, defaults={"color": color}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created tag: {tag_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Tag already exists: {tag_name}"))

        self.stdout.write(self.style.SUCCESS("\nDefault setup completed successfully!"))
