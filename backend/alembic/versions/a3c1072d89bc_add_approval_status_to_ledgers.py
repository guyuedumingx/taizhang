"""add_approval_status_to_ledgers

Revision ID: a3c1072d89bc
Revises: 08dd1f31fe88
Create Date: 2025-03-09 02:37:05.355787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic.context import get_context


# revision identifiers, used by Alembic.
revision: str = 'a3c1072d89bc'
down_revision: Union[str, None] = '08dd1f31fe88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加审批状态相关字段
    op.add_column('ledgers', sa.Column('approval_status', sa.String(), nullable=True))
    op.add_column('ledgers', sa.Column('current_approver_id', sa.Integer(), nullable=True))
    op.add_column('ledgers', sa.Column('workflow_id', sa.Integer(), nullable=True))
    op.add_column('ledgers', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ledgers', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    
    # 将现有记录的approval_status设置为默认值
    op.execute("UPDATE ledgers SET approval_status = 'pending' WHERE approval_status IS NULL")
    
    # 将字段设置为非空
    # SQLite不支持直接修改列的nullable属性
    conn = op.get_bind()
    context = get_context()
    if context.dialect.name == 'sqlite':
        # SQLite不支持ALTER COLUMN NOT NULL，所以我们不执行这一步
        pass
    else:
        op.alter_column('ledgers', 'approval_status', nullable=False, server_default='pending')


def downgrade() -> None:
    # SQLite不支持直接删除外键约束，所以在SQLite中我们跳过这一步
    conn = op.get_bind()
    context = get_context()
    if context.dialect.name != 'sqlite':
        op.drop_constraint('fk_ledgers_workflow_id_workflows', 'ledgers', type_='foreignkey')
        op.drop_constraint('fk_ledgers_current_approver_id_users', 'ledgers', type_='foreignkey')
    
    # 删除列
    op.drop_column('ledgers', 'approved_at')
    op.drop_column('ledgers', 'submitted_at')
    op.drop_column('ledgers', 'workflow_id')
    op.drop_column('ledgers', 'current_approver_id')
    op.drop_column('ledgers', 'approval_status')
