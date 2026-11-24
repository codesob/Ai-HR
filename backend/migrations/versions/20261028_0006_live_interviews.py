"""live interviews: in-app call, recording with consent, transcript, AI notes, scorecard

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 16:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prep_questions', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('recording_consent', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('recording_consent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('recording_on', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('recording', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('transcript', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('transcript_english', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('summary', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('summary_status', sa.String(length=16), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('scorecard', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('interview_signals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('interview_id', sa.Integer(), nullable=False),
    sa.Column('to_role', sa.String(length=16), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('interview_signals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_interview_signals_interview_id'), ['interview_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('interview_signals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_interview_signals_interview_id'))
    op.drop_table('interview_signals')
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        for column in ('ended_at', 'started_at', 'scorecard', 'summary_status', 'summary', 'transcript_english',
                       'transcript', 'recording', 'recording_on', 'recording_consent_at', 'recording_consent',
                       'prep_questions'):
            batch_op.drop_column(column)
