from django.db import models

from .base import BrettModel


class Entry(BrettModel):
    """An email or note entry within a card."""

    card = models.ForeignKey("Card", on_delete=models.CASCADE, related_name="entries")
    sender = models.ForeignKey(
        "Correspondent",
        on_delete=models.SET_NULL,
        related_name="entries",
        null=True,
        blank=True,
    )
    from_addr = models.CharField(blank=True, max_length=255)
    subject = models.CharField(max_length=500, blank=True)
    message_id = models.CharField(max_length=500, blank=True)
    date = models.DateTimeField()
    body = models.TextField()
    raw_message = models.TextField(
        blank=True, help_text="Full raw email message including headers"
    )
    summary = models.CharField(
        max_length=200, blank=True, help_text="Very short summary, e.g., '+1'"
    )
    tags = models.ManyToManyField("Tag", related_name="entries", blank=True)

    class Meta:
        ordering = ["date"]
        verbose_name_plural = "entries"

    def __str__(self):
        if self.summary:
            return f"{self.from_addr}: {self.summary}"
        return f"{self.from_addr}: {self.subject[:50]}"

    @property
    def parsed_body(self):
        """Extract body from raw_message by splitting on double newline."""
        if self.raw_message:
            parts = self.raw_message.split("\n\n", 1)
            if len(parts) == 2:
                return parts[1].strip()
            return self.raw_message.strip()
        return self.body
