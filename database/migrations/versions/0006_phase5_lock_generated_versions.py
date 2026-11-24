"""phase5 lock generated versions

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-24 01:19:41.984126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Generated versions are read-only snapshots; edits happen on working copies (Phase 5)."""
    op.execute(sa.text("UPDATE itinerary_versions SET is_locked = :v WHERE label = 'Generated'").bindparams(v=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("UPDATE itinerary_versions SET is_locked = :v WHERE label = 'Generated'").bindparams(v=False))
