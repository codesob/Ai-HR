"""hr agent runs and proposed actions

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 20:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('agent_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('trigger', sa.String(length=32), nullable=False),
    sa.Column('instruction', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('reply', sa.Text(), nullable=False),
    sa.Column('steps', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_agent_runs_organization_id'), ['organization_id'], unique=False)

    op.create_table('agent_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('tool', sa.String(length=64), nullable=False),
    sa.Column('args', sa.JSON(), nullable=False),
    sa.Column('summary', sa.String(length=512), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('agent_actions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_agent_actions_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_agent_actions_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('agent_actions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_agent_actions_status'))
        batch_op.drop_index(batch_op.f('ix_agent_actions_organization_id'))
    op.drop_table('agent_actions')
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_agent_runs_organization_id'))
    op.drop_table('agent_runs')
