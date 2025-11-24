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
