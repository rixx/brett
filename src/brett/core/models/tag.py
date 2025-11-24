from django.db import models

from .base import BrettModel


class Tag(BrettModel):
    """Tag for categorizing entries."""

    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, default="#6c757d", help_text="Hex color code, e.g., #ff5733"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
