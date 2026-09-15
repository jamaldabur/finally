# backend/schema/

PLAN.md §4 describes this directory as holding "schema SQL definitions and
seed data" — the documented contract for FinAlly's database, kept separate
from the top-level `db/` directory (the runtime SQLite volume-mount point).

In practice, the DDL and seed logic live as Python string constants
colocated with each table's access module, following the pattern already
established by `app/db/watchlist.py` before this directory existed. Keeping
each table's schema next to the functions that read/write it (rather than in
standalone `.sql` files this directory would otherwise hold) means there's
one file to open per table, and the lazy-init/seed code that has to stay in
sync with the DDL can't drift out of sync with it.

The schema is defined here:

| Table | Module |
|---|---|
| `users_profile` | `app/db/users.py` |
| `watchlist` | `app/db/watchlist.py` |
| `positions` | `app/db/positions.py` |
| `trades` | `app/db/trades.py` |
| `portfolio_snapshots` | `app/db/portfolio_snapshots.py` |
| `chat_messages` | `app/db/chat_messages.py` |

`app/db/connection.py` holds the shared `DB_PATH` resolution (`FINALLY_DB_PATH`
env var, defaulting to `<repo root>/db/finally.db`) and `connect()` helper
every table module uses. `app/db/__init__.py`'s `init_db()` calls each
module's `init_db()` in turn — the single startup call that creates every
table and seeds default data (PLAN.md §7), idempotently.
