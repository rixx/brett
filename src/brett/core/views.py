import re
from collections import defaultdict

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .email_parser import parse_raw_email
from .models import Board, Card, Column, Correspondent, Entry


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


def _get_related_cards(card, board):
    """Find cards on the same board that share non-core-team correspondents."""
    # Get this card's correspondent IDs from entries
    card_correspondent_ids = set(
        card.entries.filter(sender__isnull=False).values_list("sender_id", flat=True)
    )
    if not card_correspondent_ids:
        return []

    # Subtract core team
    core_team_ids = set(board.core_team.values_list("id", flat=True))
    non_core_ids = card_correspondent_ids - core_team_ids
    if not non_core_ids:
        return []

    # Find other cards on the same board sharing these correspondents
    related_cards = (
        Card.objects.filter(
            column__board=board,
            entries__sender_id__in=non_core_ids,
        )
        .exclude(pk=card.pk)
        .annotate(shared_count=Count("entries__sender_id", distinct=True))
        .order_by("-shared_count")[:10]
    )

    if not related_cards:
        return []

    # Batch-fetch which correspondents are shared per related card
    related_card_ids = [c.pk for c in related_cards]
    shared_entries = (
        Entry.objects.filter(
            card_id__in=related_card_ids,
            sender_id__in=non_core_ids,
        )
        .values_list("card_id", "sender_id")
        .distinct()
    )

    # Map card_id -> set of correspondent IDs
    card_correspondent_map = defaultdict(set)
    for cid, sid in shared_entries:
        card_correspondent_map[cid].add(sid)

    # Fetch correspondent objects for display
    all_shared_ids = set()
    for ids in card_correspondent_map.values():
        all_shared_ids |= ids
    correspondents_by_id = {
        c.pk: c for c in Correspondent.objects.filter(pk__in=all_shared_ids)
    }

    result = []
    for rc in related_cards:
        shared_ids = card_correspondent_map.get(rc.pk, set())
        shared_correspondents = [
            correspondents_by_id[sid]
            for sid in shared_ids
            if sid in correspondents_by_id
        ]
        result.append(
            {
                "card": rc,
                "shared_correspondents": shared_correspondents,
                "shared_count": len(shared_correspondents),
            }
        )

    return result


def card_detail(request, card_id):
    card = get_object_or_404(Card.objects.select_related("column__board"), pk=card_id)
    entries = card.entries.select_related("sender").all()
    board = card.column.board

    related_cards = _get_related_cards(card, board)

    # Check if this is an HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"

    template = "core/card_detail_partial.html" if is_htmx else "core/card_detail.html"

    return render(
        request,
        template,
        {
            "card": card,
            "entries": entries,
            "board": board,
            "related_cards": related_cards,
        },
    )


def card_edit_title(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    if request.method == "POST":
        new_title = request.POST.get("title", "").strip()
        if new_title:
            card.title = new_title
            card.save()
            return render(
                request,
                "core/card_title_display.html",
                {"card": card},
            )

    return render(request, "core/card_title_edit.html", {"card": card})


def card_edit_description(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    if request.method == "POST":
        new_description = request.POST.get("description", "").strip()
        card.description = new_description
        card.save()
        return render(
            request,
            "core/card_description_display.html",
            {"card": card},
        )

    return render(request, "core/card_description_edit.html", {"card": card})


def add_card(request, column_id):
    column = get_object_or_404(Column, pk=column_id)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()

        if title:
            card = Card.objects.create(
                column=column,
                title=title,
                description=description,
            )
            # Return the new card HTML and reset the button using OOB swap
            return render(
                request,
                "core/add_card_success.html",
                {"card": card, "column": column},
            )

    # Show the form
    return render(request, "core/add_card_form.html", {"column": column})


def cancel_add_card(request, column_id):
    column = get_object_or_404(Column, pk=column_id)
    return render(request, "core/new_card_button.html", {"column": column})


def move_card(request, card_id):
    if request.method != "POST":
        return render(
            request, "core/error.html", {"error": "Method not allowed"}, status=405
        )

    card = get_object_or_404(Card, pk=card_id)
    column_id = request.POST.get("column_id")

    if not column_id:
        return render(
            request, "core/error.html", {"error": "column_id required"}, status=400
        )

    new_column = get_object_or_404(Column, pk=column_id)

    # Update the card's column (dates are based on entries, not user actions)
    card.column = new_column
    card.save()

    request.session["last_used_column_id"] = new_column.id

    # Return success response
    return render(request, "core/move_success.html", {"card": card})


def import_email(request):
    """Import an email - step 1: paste raw email."""
    card_id = request.GET.get("card_id")
    new_card = request.GET.get("new_card")

    if request.method == "POST":
        raw_message = request.POST.get("raw_message", "").strip()

        if not raw_message:
            return render(
                request,
                "core/import_email.html",
                {"error": "Please paste an email message"},
            )

        # Parse the email
        try:
            parsed = parse_raw_email(raw_message)
        except Exception as e:
            import traceback

            error_detail = f"Failed to parse email: {str(e)}\n{traceback.format_exc()}"
            return render(
                request,
                "core/import_email.html",
                {"error": error_detail},
            )

        # Convert date to string for session storage
        if parsed.get("date"):
            parsed["date"] = parsed["date"].isoformat()

        # Store parsed data in session for next step
        request.session["parsed_email"] = parsed

        # If card_id or new_card specified, skip suggestion step
        if card_id:
            return redirect("confirm_import", card_id=card_id)
        elif new_card:
            return redirect("confirm_import_new")

        # Otherwise, show card suggestions
        return redirect("suggest_cards")

    return render(
        request,
        "core/import_email.html",
        {"card_id": card_id, "new_card": new_card},
    )


def _clean_subject_for_matching(subject):
    """Strip email prefixes and spam-filter markers from a subject for matching."""
    clean = subject
    # Strip Re:/Fwd: prefixes
    for prefix in ["Re:", "RE:", "re:", "Fwd:", "FWD:", "fwd:", "Fw:", "FW:"]:
        clean = clean.replace(prefix, "").strip()
    # Strip spam-filter markers like ***UNCHECKED***, ***SPAM***, [EXTERNAL], etc.
    clean = re.sub(r"\*{2,3}[A-Z]+\*{2,3}", "", clean)
    clean = re.sub(
        r"\[(?:SPAM|EXTERNAL|BULK|SUSPECT|QUARANTINE|UNCHECKED)\]",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    # Normalize whitespace
    clean = " ".join(clean.split())
    return clean


def _find_cards_by_message_ids(
    message_ids, seen_cards, reason_prefix="Thread reference"
):
    """Look up entries by a list of message IDs and return candidates."""
    if not message_ids:
        return []
    # Build query for all message IDs (with and without angle brackets)
    q = Q()
    for mid in message_ids:
        mid_stripped = mid.strip("<>")
        q |= Q(message_id=mid_stripped) | Q(message_id=f"<{mid_stripped}>")
    matching_entries = Entry.objects.filter(q).select_related("card")
    candidates = []
    for entry in matching_entries:
        if entry.card.id not in seen_cards:
            seen_cards.add(entry.card.id)
            candidates.append(
                {
                    "card": entry.card,
                    "reason": f"{reason_prefix}: {entry.subject[:50]}",
                    "preview": entry.body[:200],
                }
            )
    return candidates


def suggest_cards(request):
    """Import an email - step 2: suggest matching cards."""
    parsed = request.session.get("parsed_email")
    if not parsed:
        return redirect("import_email")

    candidates = []
    seen_cards = set()

    # First, try to find card by in-reply-to message ID
    if parsed.get("in_reply_to"):
        candidates.extend(
            _find_cards_by_message_ids(
                [parsed["in_reply_to"]], seen_cards, reason_prefix="Reply to"
            )
        )

    # Also check References header for thread message IDs
    if parsed.get("references"):
        candidates.extend(
            _find_cards_by_message_ids(
                parsed["references"], seen_cards, reason_prefix="Thread reference"
            )
        )

    # Then, try to find cards by similar subject
    if parsed.get("subject"):
        clean_subject = _clean_subject_for_matching(parsed["subject"])

        if clean_subject:
            # Strategy 1: Exact match on card title (case insensitive)
            exact_matches = Card.objects.filter(title__iexact=clean_subject)
            for card in exact_matches:
                if card.id not in seen_cards:
                    seen_cards.add(card.id)
                    first_entry = card.entries.first()
                    candidates.append(
                        {
                            "card": card,
                            "reason": "Exact subject match",
                            "preview": first_entry.body[:200] if first_entry else "",
                        }
                    )

            # Strategy 2: Card title contains email subject OR email subject contains card title
            all_cards = Card.objects.prefetch_related("entries").all()
            for card in all_cards:
                if card.id in seen_cards:
                    continue

                card_title_clean = _clean_subject_for_matching(card.title).lower()
                clean_subject_lower = clean_subject.lower()

                # Bidirectional matching
                if (
                    card_title_clean in clean_subject_lower
                    or clean_subject_lower in card_title_clean
                ):
                    seen_cards.add(card.id)
                    first_entry = card.entries.first()
                    candidates.append(
                        {
                            "card": card,
                            "reason": "Similar subject",
                            "preview": first_entry.body[:200] if first_entry else "",
                        }
                    )
                    if len(candidates) >= 10:  # Don't check too many
                        break

            # Strategy 3: Match against entry subjects
            matching_entries = Entry.objects.filter(
                Q(subject__icontains=clean_subject)
            ).select_related("card")

            for entry in matching_entries[:10]:  # Limit to 10 entries
                if entry.card.id not in seen_cards:
                    seen_cards.add(entry.card.id)
                    candidates.append(
                        {
                            "card": entry.card,
                            "reason": f"Previous entry: {entry.subject[:50]}",
                            "preview": entry.body[:200],
                        }
                    )

    return render(
        request,
        "core/suggest_cards.html",
        {
            "parsed": parsed,
            "candidates": candidates[:8],  # Limit to 8 suggestions
        },
    )


def search_cards(request):
    """Search cards by title for the import suggest page."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return HttpResponse("")

    cards = Card.objects.filter(title__icontains=q).select_related("column")[:10]
    results = []
    for card in cards:
        first_entry = card.entries.first()
        results.append(
            {
                "card": card,
                "preview": first_entry.body[:200] if first_entry else "",
            }
        )

    return render(request, "core/search_cards_results.html", {"results": results})


def _get_or_create_correspondent(board, email_addr, name=None):
    """Get or create a Correspondent for the given email address."""
    if not email_addr:
        return None

    # First, try to find by primary email
    correspondent = Correspondent.objects.filter(board=board, email=email_addr).first()

    if correspondent:
        # Update name if we have one and correspondent doesn't
        if name and not correspondent.name:
            correspondent.name = name
            correspondent.save()
        return correspondent

    # Check if email exists in aliases (manually since SQLite doesn't support JSON contains)
    for corr in Correspondent.objects.filter(board=board):
        if corr.aliases and email_addr in corr.aliases:
            return corr

    # Create new correspondent
    correspondent = Correspondent.objects.create(
        board=board, email=email_addr, name=name or "", aliases=[]
    )
    return correspondent


def confirm_import(request, card_id):
    """Import an email - step 3: confirm and create entry for existing card."""
    parsed = request.session.get("parsed_email")
    if not parsed:
        return redirect("import_email")

    card = get_object_or_404(Card, pk=card_id)

    if request.method == "POST":
        # Check for duplicate message-ID
        message_id = parsed.get("message_id", "")
        if message_id:
            existing_entry = Entry.objects.filter(message_id=message_id).first()
            if existing_entry:
                return render(
                    request,
                    "core/confirm_import.html",
                    {
                        "card": card,
                        "parsed": parsed,
                        "error": f"This email has already been imported to card '{existing_entry.card.title}'",
                    },
                )

        # Parse date if it's a string
        email_date = parsed.get("date")
        if isinstance(email_date, str):
            email_date = parse_datetime(email_date)
        if not email_date:
            email_date = timezone.now()

        # Get or create correspondent
        board = card.column.board
        correspondent = _get_or_create_correspondent(
            board, parsed.get("from_addr", ""), parsed.get("from_name")
        )

        # Create the entry
        Entry.objects.create(
            card=card,
            sender=correspondent,
            from_addr=parsed.get("from_addr", ""),
            subject=parsed.get("subject", ""),
            message_id=parsed.get("message_id", ""),
            date=email_date,
            body=parsed.get("body", ""),
            raw_message=parsed.get("raw_message", ""),
            summary=request.POST.get("summary", "").strip(),
        )

        # Update card dates based on all entries
        card.update_dates_from_entries()

        # Clear session
        del request.session["parsed_email"]

        return redirect(
            reverse("card_detail", kwargs={"card_id": card.id}) + "?from=import"
        )

    return render(request, "core/confirm_import.html", {"card": card, "parsed": parsed})


def confirm_import_new(request):
    """Import an email - step 3: confirm and create entry for new card."""
    parsed = request.session.get("parsed_email")
    if not parsed:
        return redirect("import_email")

    if request.method == "POST":
        # Check for duplicate message-ID
        message_id = parsed.get("message_id", "")
        if message_id:
            existing_entry = Entry.objects.filter(message_id=message_id).first()
            if existing_entry:
                board = Board.objects.first()
                columns = board.columns.all() if board else Column.objects.none()
                card_title = (
                    _clean_subject_for_matching(parsed.get("subject", "")) or "Untitled"
                )
                return render(
                    request,
                    "core/confirm_import_new.html",
                    {
                        "parsed": parsed,
                        "card_title": card_title,
                        "columns": columns,
                        "error": f"This email has already been imported to card '{existing_entry.card.title}'",
                    },
                )

        # Get the board and column
        board = Board.objects.first()
        if not board:
            return render(
                request,
                "core/error.html",
                {"error": "No board found. Please create a board first."},
            )

        column_id = request.POST.get("column_id")
        if column_id:
            column = get_object_or_404(Column, pk=column_id, board=board)
        else:
            column = board.columns.first()

        if not column:
            return render(
                request,
                "core/error.html",
                {"error": "No column found. Please create a column first."},
            )

        request.session["last_used_column_id"] = column.id

        # Parse date if it's a string
        email_date = parsed.get("date")
        if isinstance(email_date, str):
            email_date = parse_datetime(email_date)
        if not email_date:
            email_date = timezone.now()

        # Get or create correspondent
        correspondent = _get_or_create_correspondent(
            board, parsed.get("from_addr", ""), parsed.get("from_name")
        )

        # Create new card with cleaned subject as title
        card = Card.objects.create(
            column=column,
            title=_clean_subject_for_matching(parsed.get("subject", "")) or "Untitled",
        )

        # Create the entry
        Entry.objects.create(
            card=card,
            sender=correspondent,
            from_addr=parsed.get("from_addr", ""),
            subject=parsed.get("subject", ""),
            message_id=parsed.get("message_id", ""),
            date=email_date,
            body=parsed.get("body", ""),
            raw_message=parsed.get("raw_message", ""),
            summary=request.POST.get("summary", "").strip(),
        )

        # Update card dates based on entries
        card.update_dates_from_entries()

        # Clear session
        del request.session["parsed_email"]

        return redirect(
            reverse("card_detail", kwargs={"card_id": card.id}) + "?from=import"
        )

    board = Board.objects.first()
    columns = board.columns.all() if board else Column.objects.none()
    last_used_column_id = request.session.get("last_used_column_id")
    card_title = _clean_subject_for_matching(parsed.get("subject", "")) or "Untitled"
    return render(
        request,
        "core/confirm_import_new.html",
        {
            "parsed": parsed,
            "card_title": card_title,
            "columns": columns,
            "last_used_column_id": last_used_column_id,
        },
    )
