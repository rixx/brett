**project description**

brett is a lightweight kanban board optimized for tracking email threads and consensus-based decision-making. runs locally, stores everything in sqlite, no external services.

- kanban board with draggable cards across user-defined columns
- cards represent email threads (or other discussion items)
- each card contains multiple emails in chronological order
- manual ingestion: paste raw email text, system suggests matching threads by subject/participants/recency, user selects or creates new card
- card detail view shows full thread history plus user annotations
- supports non-email cards for informal discussions

**data model**
- `Board`: container/project. mostly a name, but will also contain some settings, like e.g. aliases to identify multiple addresses as the same person
- `Column`: belongs to board, has name and position for ordering
- `Card`: belongs to column, has title, timestamps, description, start_date, last_update_date
- `Entry`: belongs to card, stores from_addr, date, subject, message ID, body (text). additionally a summary field, which should be very short (sometimes just "+1")

**ui**
- board view: columns display side-by-side, cards sorted by update time
- drag-and-drop to move cards between columns (htmx)
- card detail: chronological email list, button to add new email or note (link to ingestion with context), option to move to a different column here
- ingestion view: textarea for pasting email → parse → show candidate cards (e.g. from reply-to header and from subject) → select/create
- single-user, runs on localhost:8000, no authentication needed
- no javascript frameworks beyond htmx, plain js otherwise
- no mobile views

**testing**

- never use real names, email addresses, domains, or other actual information in tests — always use generic test data (e.g. test@example.com, Test User)

**project stuff**

check the justfile for commands to run for testing and formatting
