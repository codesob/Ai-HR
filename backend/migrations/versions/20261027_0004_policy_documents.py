"""company handbook documents

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 22:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('policy_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('chunks', sa.Integer(), nullable=False),
    sa.Column('characters', sa.Integer(), nullable=False),
    sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('policy_documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_policy_documents_organization_id'), ['organization_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('policy_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_policy_documents_organization_id'))
    op.drop_table('policy_documents')
