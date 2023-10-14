"""description_of_changes

Revision ID: 18a563295c7a
Revises: fa7975e153d0
Create Date: 2023-10-14 00:01:10.587771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18a563295c7a'
down_revision: Union[str, None] = 'fa7975e153d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('scene_prompts', sa.Column('max_length', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('scene_prompts', 'max_length')
    # ### end Alembic commands ###
