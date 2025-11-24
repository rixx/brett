from django.db import models

from .base import BrettModel


class Column(BrettModel):
    board = models.ForeignKey("Board", on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ["board", "position", "name"]
        unique_together = [["board", "name"]]

    def __str__(self):
        return f"{self.board.name} - {self.name}"
