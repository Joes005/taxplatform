"""phase13_compliance_control_center

Revision ID: c2d3e4f5a6b7
Revises: b1e2c3d4e5f6
Create Date: 2026-09-28 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.utils.types


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1e2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expand status column length on compliance_obligations for new Phase 13 lifecycle statuses
    op.alter_column(
        'compliance_obligations',
        'status',
        existing_type=sa.String(length=15),
        type_=sa.String(length=25),
        existing_nullable=False,
    )

    # 2. Add Phase 13 workflow and readiness columns to compliance_obligations
    op.add_column('compliance_obligations', sa.Column('assigned_to', app.utils.types.GUID(), nullable=True))
    op.add_column('compliance_obligations', sa.Column('reviewer_id', app.utils.types.GUID(), nullable=True))
    op.add_column(
        'compliance_obligations',
        sa.Column('readiness_status', sa.String(length=25), nullable=False, server_default='NOT_APPLICABLE')
    )
    op.add_column('compliance_obligations', sa.Column('readiness_details', sa.JSON(), nullable=True))
    op.add_column('compliance_obligations', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('compliance_obligations', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('compliance_obligations', sa.Column('review_notes', sa.Text(), nullable=True))
    op.add_column('compliance_obligations', sa.Column('prerequisite_config', sa.JSON(), nullable=True))

    op.create_foreign_key(
        'fk_compliance_obligations_assigned_to',
        'compliance_obligations',
        'users',
        ['assigned_to'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_compliance_obligations_reviewer_id',
        'compliance_obligations',
        'users',
        ['reviewer_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'ix_compliance_obligations_assigned',
        'compliance_obligations',
        ['company_id', 'assigned_to'],
        unique=False
    )
    op.create_index(
        op.f('ix_compliance_obligations_assigned_to'),
        'compliance_obligations',
        ['assigned_to'],
        unique=False
    )
    op.create_index(
        op.f('ix_compliance_obligations_reviewer_id'),
        'compliance_obligations',
        ['reviewer_id'],
        unique=False
    )

    # 3. Create compliance_obligation_evidence table
    op.create_table(
        'compliance_obligation_evidence',
        sa.Column('id', app.utils.types.GUID(), nullable=False),
        sa.Column('obligation_id', app.utils.types.GUID(), nullable=False),
        sa.Column('company_id', app.utils.types.GUID(), nullable=False),
        sa.Column('document_id', app.utils.types.GUID(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_by', app.utils.types.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['obligation_id'], ['compliance_obligations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_compliance_obligation_evidence_obligation',
        'compliance_obligation_evidence',
        ['obligation_id'],
        unique=False
    )
    op.create_index(
        'ix_compliance_obligation_evidence_company',
        'compliance_obligation_evidence',
        ['company_id'],
        unique=False
    )
    op.create_index(
        'ix_compliance_obligation_evidence_document',
        'compliance_obligation_evidence',
        ['document_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_compliance_obligation_evidence_document', table_name='compliance_obligation_evidence')
    op.drop_index('ix_compliance_obligation_evidence_company', table_name='compliance_obligation_evidence')
    op.drop_index('ix_compliance_obligation_evidence_obligation', table_name='compliance_obligation_evidence')
    op.drop_table('compliance_obligation_evidence')

    op.drop_index(op.f('ix_compliance_obligations_reviewer_id'), table_name='compliance_obligations')
    op.drop_index(op.f('ix_compliance_obligations_assigned_to'), table_name='compliance_obligations')
    op.drop_index('ix_compliance_obligations_assigned', table_name='compliance_obligations')
    op.drop_constraint('fk_compliance_obligations_reviewer_id', 'compliance_obligations', type_='foreignkey')
    op.drop_constraint('fk_compliance_obligations_assigned_to', 'compliance_obligations', type_='foreignkey')

    op.drop_column('compliance_obligations', 'prerequisite_config')
    op.drop_column('compliance_obligations', 'review_notes')
    op.drop_column('compliance_obligations', 'approved_at')
    op.drop_column('compliance_obligations', 'completed_at')
    op.drop_column('compliance_obligations', 'readiness_details')
    op.drop_column('compliance_obligations', 'readiness_status')
    op.drop_column('compliance_obligations', 'reviewer_id')
    op.drop_column('compliance_obligations', 'assigned_to')

    op.alter_column(
        'compliance_obligations',
        'status',
        existing_type=sa.String(length=25),
        type_=sa.String(length=15),
        existing_nullable=False,
    )
