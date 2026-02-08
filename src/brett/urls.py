from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from brett.core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("import/", views.import_email, name="import_email"),
    path("import/suggest/", views.suggest_cards, name="suggest_cards"),
    path("import/search/", views.search_cards, name="search_cards"),
    path(
        "import/confirm/<int:card_id>/",
        views.confirm_import,
        name="confirm_import",
    ),
    path(
        "import/confirm/new/",
        views.confirm_import_new,
        name="confirm_import_new",
    ),
    path("card/<int:card_id>/", views.card_detail, name="card_detail"),
    path(
        "card/<int:card_id>/edit-title/",
        views.card_edit_title,
        name="card_edit_title",
    ),
    path(
        "card/<int:card_id>/edit-description/",
        views.card_edit_description,
        name="card_edit_description",
    ),
    path("card/<int:card_id>/move/", views.move_card, name="move_card"),
    path("column/<int:column_id>/add-card/", views.add_card, name="add_card"),
    path(
        "column/<int:column_id>/cancel-add-card/",
        views.cancel_add_card,
        name="cancel_add_card",
    ),
    path("<slug:slug>/stats/", views.board_stats, name="board_stats"),
    path("<slug:slug>/", views.board_detail, name="board_detail"),
    path("", views.board_list, name="board_list"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
