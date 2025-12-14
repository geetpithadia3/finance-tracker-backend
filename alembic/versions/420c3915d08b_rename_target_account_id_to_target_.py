"""Rename target_account_id to target_category_id

Revision ID: 420c3915d08b
Revises: 5b5685173ba4
Create Date: 2025-12-14 13:34:25.816738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '420c3915d08b'
down_revision: Union[str, None] = '5b5685173ba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column in mapping_rules table
    op.alter_column('mapping_rules', 'target_account_id',
                    new_column_name='target_category_id')


def downgrade() -> None:
    # Revert column name
    op.alter_column('mapping_rules', 'target_category_id',
                    new_column_name='target_account_id')
