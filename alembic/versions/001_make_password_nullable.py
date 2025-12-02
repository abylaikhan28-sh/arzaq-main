"""Make hashed_password nullable for Google OAuth

Revision ID: 001
Revises:
Create Date: 2025-12-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make hashed_password nullable for Google OAuth users
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Revert hashed_password to not nullable
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(),
                    nullable=False)
