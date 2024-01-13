"""second

Revision ID: 515eb1d34b75
Revises: ea967d1468b4
Create Date: 2024-01-13 18:21:08.000687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '515eb1d34b75'
down_revision: Union[str, None] = 'ea967d1468b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
