"""auth sessions, emailed tokens, email verification

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27 16:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    # Accounts created before verification existed are treated as verified.
    op.execute("UPDATE users SET email_verified_at = created_at")

    op.create_table('auth_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_agent', sa.String(length=255), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_sessions_refresh_token_hash'), ['refresh_token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_auth_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('user_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('purpose', sa.String(length=32), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_tokens_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_user_tokens_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('user_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_user_tokens_token_hash'))
    op.drop_table('user_tokens')
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_sessions_user_id'))
        batch_op.drop_index(batch_op.f('ix_auth_sessions_refresh_token_hash'))
    op.drop_table('auth_sessions')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('email_verified_at')
