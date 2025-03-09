"""add_approver_actions_to_workflow_instance_nodes

Revision ID: 5bd885d93617
Revises: a3c1072d89bc
Create Date: 2025-03-09 17:13:49.076609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bd885d93617'
down_revision: Union[str, None] = 'a3c1072d89bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加approver_actions列
    op.add_column('workflow_instance_nodes', sa.Column('approver_actions', sa.JSON(), nullable=True))
    
    # 更新现有记录，将approver_actions设置为空列表
    op.execute("UPDATE workflow_instance_nodes SET approver_actions = '[]'")


def downgrade() -> None:
    # 删除approver_actions列
    op.drop_column('workflow_instance_nodes', 'approver_actions')
