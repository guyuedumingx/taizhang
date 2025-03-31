"""merge heads

Revision ID: 960bd0ac395b
Revises: 1085f8bfa2c4, b1ae7fb5242a
Create Date: 2025-03-31 10:46:22.903538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '960bd0ac395b'
down_revision: Union[str, None] = ('1085f8bfa2c4', 'b1ae7fb5242a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
