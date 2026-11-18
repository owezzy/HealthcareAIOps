# Add a database migration

Alembic owns the API's schema. Write migrations by hand, so that each change is reviewed as written.

## 1. Create the revision file

Add `services/api/migrations/versions/<NNNN>_<what>.py`. Use the next number and set `down_revision` to the previous revision:

```python
"""incidents: incident records and their state machine.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(...)


def downgrade() -> None:
    op.drop_table(...)
```

Always write `downgrade()`. Put data rules in the database as constraints where you can, as `0001_llm_usage.py` does with its check constraint.

## 2. Mirror the table in the adapter

Declare the same table with SQLAlchemy Core in the context's `adapters/postgres.py`, on `aiops_api.db.metadata`. Keep the two definitions in step.

## 3. Apply and test

```bash
make migrate                    # apply to your local database
uv run pytest services/api      # adapter tests migrate a throwaway database
```

The adapter tests run every migration from scratch, so a broken migration fails the tests.

## 4. Deploy

Nothing extra. The API's init container runs `alembic upgrade head` before the API starts.

Migrations must be safe to run while the previous release is still serving: add columns as nullable or with defaults, and remove old ones in a later release.
