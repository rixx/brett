# Brett

Brett is a Kanban board that understands emails and threads.

You can use it without referring to emails and threads as a normal Kanban board, too, but the email workflow is where it
shines:

A card is a topic. When you import (paste, load, etc) an email, you can choose to start a new card or to add it to an
existing card. Add a one-line summary if you want, and … that's it!

## Bulk email review

To triage a Maildir directory against your database:

```bash
python -m brett review_emails ~/.local/share/mail/account/folder/cur/
```

This walks through each email file, skips any already imported (matched by Message-ID), and copies new ones to your clipboard via `wl-copy` so you can paste them into the ingestion UI. Press Enter to advance to the next email, or Ctrl+C to stop.
