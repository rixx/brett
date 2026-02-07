from django.db import models

from .base import BrettModel


class Board(BrettModel):
    """Base container."""

    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    core_team = models.ManyToManyField(
        "Correspondent",
        blank=True,
        related_name="core_team_boards",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
