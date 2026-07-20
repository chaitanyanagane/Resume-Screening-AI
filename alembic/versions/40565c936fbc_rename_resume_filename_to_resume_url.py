"""rename resume_filename to resume_url

Revision ID: 40565c936fbc
Revises: 25972889ea16
Create Date: 2026-07-20 15:28:12.542155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40565c936fbc'
down_revision: Union[str, Sequence[str], None] = '25972889ea16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('candidate_profiles') as batch_op:
        batch_op.add_column(sa.Column('resume_url', sa.Text(), nullable=True))
        batch_op.drop_column('resume_filename')

def downgrade() -> None:
    with op.batch_alter_table('candidate_profiles') as batch_op:
        batch_op.add_column(sa.Column('resume_filename', sa.Text(), nullable=True))
        batch_op.drop_column('resume_url')
