"""create users table

Revision ID: cdae1ace538f
Revises: 118d4c400b3d
Create Date: 2026-08-13 05:38:03.073220
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cdae1ace538f"
down_revision = "118d4c400b3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clerk_id", sa.String(length=255), nullable=False),
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

    op.create_index(
        op.f("ix_users_clerk_id"),
        "users",
        ["clerk_id"],
        unique=True,
    )

    op.add_column(
        "posts",
        sa.Column("user_id", sa.UUID(), nullable=False),
    )

    op.create_index(
        op.f("ix_posts_user_id"),
        "posts",
        ["user_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_posts_user_id_users",
        "posts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_posts_user_id_users",
        "posts",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_posts_user_id"),
        table_name="posts",
    )

    op.drop_column(
        "posts",
        "user_id",
    )

    op.drop_index(
        op.f("ix_users_clerk_id"),
        table_name="users",
    )

    op.drop_table("users")
