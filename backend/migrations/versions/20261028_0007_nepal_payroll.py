"""nepal payroll: SSF and tax details on salary profiles, BS month and breakdown on payslips

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28 23:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('salary_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('basic_monthly', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('ssf_enrolled', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('married', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('female', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('remote_category', sa.String(length=1), nullable=True))
        batch_op.add_column(sa.Column('cit_monthly', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('life_insurance_annual', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('health_insurance_annual', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('pan', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('ssf_number', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('joined_on', sa.Date(), nullable=True))
    with op.batch_alter_table('payslips', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fiscal_year', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('bs_year', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('bs_month', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ssf_employee', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('ssf_employer', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('breakdown', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.create_index(batch_op.f('ix_payslips_fiscal_year'), ['fiscal_year'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('payslips', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payslips_fiscal_year'))
        for column in ('breakdown', 'ssf_employer', 'ssf_employee', 'bs_month', 'bs_year', 'fiscal_year'):
            batch_op.drop_column(column)
    with op.batch_alter_table('salary_profiles', schema=None) as batch_op:
        for column in ('joined_on', 'ssf_number', 'pan', 'health_insurance_annual', 'life_insurance_annual',
                       'cit_monthly', 'remote_category', 'female', 'married', 'ssf_enrolled', 'basic_monthly'):
            batch_op.drop_column(column)
