"""add user hashed password

Revision ID: 5d2f2a7c9b31
Revises: 1ab39136eea3
Create Date: 2026-07-14 16:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d2f2a7c9b31"
down_revision: Union[str, Sequence[str], None] = "1ab39136eea3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "hashed_password")
