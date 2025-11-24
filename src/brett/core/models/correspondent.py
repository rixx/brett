from django.db import models

from .base import BrettModel


class Correspondent(BrettModel):
    """A person or email address associated with a board."""

    board = models.ForeignKey(
        "Board", on_delete=models.CASCADE, related_name="correspondents"
    )
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True)
    aliases = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative email addresses for this correspondent",
    )

    class Meta:
        ordering = ["email"]
        unique_together = [["board", "email"]]

    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email
