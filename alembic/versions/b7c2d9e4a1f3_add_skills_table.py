"""add skills table

Revision ID: b7c2d9e4a1f3
Revises: a1b2c3d4e5f6
Create Date: 2026-05-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c2d9e4a1f3'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None

    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=schema,
    )
    with op.batch_alter_table('skills', schema=schema) as batch_op:
        batch_op.create_index(batch_op.f('ix_skills_name'), ['name'], unique=True)
        batch_op.create_index(batch_op.f('ix_skills_slug'), ['slug'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None

    with op.batch_alter_table('skills', schema=schema) as batch_op:
        batch_op.drop_index(batch_op.f('ix_skills_slug'))
        batch_op.drop_index(batch_op.f('ix_skills_name'))
    op.drop_table('skills', schema=schema)
