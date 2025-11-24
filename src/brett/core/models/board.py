from django.db import models

from .base import BrettModel


class Board(BrettModel):
    """Base container."""

    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
