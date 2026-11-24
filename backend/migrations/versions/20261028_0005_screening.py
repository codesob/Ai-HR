"""take-home tasks and video screens

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28 10:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _review_columns() -> list[sa.Column]:
    return [
        sa.Column('ai_score', sa.Integer(), nullable=True),
        sa.Column('ai_recommendation', sa.String(length=8), nullable=False),
        sa.Column('ai_feedback', sa.Text(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
    ]


def upgrade() -> None:
    op.create_table('assessments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('instructions', sa.Text(), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('submission', sa.Text(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    *_review_columns(),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('video_screens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('questions', sa.JSON(), nullable=False),
    sa.Column('answers', sa.JSON(), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    *_review_columns(),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    for table in ('assessments', 'video_screens'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_index(batch_op.f(f'ix_{table}_organization_id'), ['organization_id'], unique=False)
            batch_op.create_index(batch_op.f(f'ix_{table}_application_id'), ['application_id'], unique=False)


def downgrade() -> None:
    for table in ('video_screens', 'assessments'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f'ix_{table}_application_id'))
            batch_op.drop_index(batch_op.f(f'ix_{table}_organization_id'))
        op.drop_table(table)
