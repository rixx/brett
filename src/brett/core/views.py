from django.shortcuts import get_object_or_404, redirect, render

from .models import Board


def board_list(request):
    boards = Board.objects.all()
    if boards.count() == 1:
        return redirect("board_detail", slug=boards.first().slug)
    return render(request, "core/board_list.html", {"boards": boards})


def board_detail(request, slug):
    board = get_object_or_404(Board, slug=slug)
    columns = board.columns.prefetch_related("cards__entries").all()
    return render(
        request,
        "core/board_detail.html",
        {"board": board, "columns": columns},
    )
