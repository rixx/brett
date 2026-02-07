from django.db import models

from .base import BrettModel


class Card(BrettModel):
    """Card representing an email thread or a topic."""

    column = models.ForeignKey("Column", on_delete=models.CASCADE, related_name="cards")
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    last_update_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_update_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def entry_count(self):
        return self.entries.count()

    def update_dates_from_entries(self):
        """Update start_date and last_update_date based on entries."""
        entries = self.entries.all()
        if entries.exists():
            # Get earliest and latest entry dates
            earliest = entries.order_by("date").first()
            latest = entries.order_by("-date").first()
            self.start_date = earliest.date
            self.last_update_date = latest.date
            self.save()
