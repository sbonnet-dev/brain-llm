"""drop extra_config from skills

Revision ID: c4f8e6a2d710
Revises: b7c2d9e4a1f3
Create Date: 2026-05-08 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4f8e6a2d710'
down_revision: Union[str, Sequence[str], None] = 'b7c2d9e4a1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None

    # The column may have been auto-created by Base.metadata.create_all() before
    # b7c2d9e4a1f3 was modified to no longer include it. Drop only if present.
    inspector = sa.inspect(bind)
    columns = {c['name'] for c in inspector.get_columns('skills', schema=schema)}
    if 'extra_config' in columns:
        with op.batch_alter_table('skills', schema=schema) as batch_op:
            batch_op.drop_column('extra_config')


def downgrade() -> None:
    bind = op.get_bind()
    schema = 'brain' if bind.dialect.name != 'sqlite' else None
    with op.batch_alter_table('skills', schema=schema) as batch_op:
        batch_op.add_column(sa.Column('extra_config', sa.JSON(), nullable=True))
