"""phase12_tally_compatibility

Revision ID: b1e2c3d4e5f6
Revises: 21f14d138a81
Create Date: 2026-09-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.utils.types


# revision identifiers, used by Alembic.
revision: str = 'b1e2c3d4e5f6'
down_revision: Union[str, None] = '21f14d138a81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tally_mapping_templates table
    op.create_table(
        'tally_mapping_templates',
        sa.Column('id', app.utils.types.GUID(), nullable=False),
        sa.Column('company_id', app.utils.types.GUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('created_by', app.utils.types.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tally_mapping_templates_company', 'tally_mapping_templates', ['company_id'], unique=False)
    op.create_index('ix_tally_mapping_templates_id', 'tally_mapping_templates', ['id'], unique=False)

    # 2. Add reconciliation column to import_jobs table
    op.add_column('import_jobs', sa.Column('reconciliation', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('import_jobs', 'reconciliation')
    op.drop_index('ix_tally_mapping_templates_id', table_name='tally_mapping_templates')
    op.drop_index('ix_tally_mapping_templates_company', table_name='tally_mapping_templates')
    op.drop_table('tally_mapping_templates')
