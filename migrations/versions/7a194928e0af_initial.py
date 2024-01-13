"""initial

Revision ID: 7a194928e0af
Revises: 515eb1d34b75
Create Date: 2024-01-13 19:21:24.585671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a194928e0af'
down_revision: Union[str, None] = '515eb1d34b75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('employees', 'executor_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('employees', sa.Column('executor_id', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
