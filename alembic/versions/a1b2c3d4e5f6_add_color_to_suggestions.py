"""add color to suggestions

Revision ID: a1b2c3d4e5f6
Revises: 4f2b327f63c7
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4f2b327f63c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None
    op.add_column('suggestions', sa.Column('color', sa.String(length=32), nullable=True), schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None
    op.drop_column('suggestions', 'color', schema=schema)
