"""create posts table

Revision ID: 118d4c400b3d
Revises:
Create Date: 2026-08-07 19:11:25.638475
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "118d4c400b3d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "posts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("posts")
