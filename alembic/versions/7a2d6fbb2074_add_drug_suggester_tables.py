"""add_drug_suggester_tables

Revision ID: 7a2d6fbb2074
Revises: 053168080fc3
Create Date: 2025-11-25 15:27:15.597889

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '7a2d6fbb2074'
down_revision = '053168080fc3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create patient_allergies table
    op.create_table('patient_allergies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allergen_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('allergen_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('severity', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('reaction_type', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('reaction_description', sa.Text(), nullable=True),
        sa.Column('diagnosed_date', sa.Date(), nullable=True),
        sa.Column('diagnosed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['diagnosed_by_id'], ['doctors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_allergies_patient_id'), 'patient_allergies', ['patient_id'], unique=False)
    op.create_index(op.f('ix_patient_allergies_allergen_name'), 'patient_allergies', ['allergen_name'], unique=False)
    op.create_index(op.f('ix_patient_allergies_allergen_type'), 'patient_allergies', ['allergen_type'], unique=False)
    op.create_index(op.f('ix_patient_allergies_severity'), 'patient_allergies', ['severity'], unique=False)
    op.create_index(op.f('ix_patient_allergies_is_active'), 'patient_allergies', ['is_active'], unique=False)
    
    # Create drug_interaction_cache table
    op.create_table('drug_interaction_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('drug1_rxcui', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('drug2_rxcui', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('drug1_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('drug2_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('interaction_severity', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column('interaction_description', sa.Text(), nullable=True),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_drug_interaction_cache_drug1_rxcui'), 'drug_interaction_cache', ['drug1_rxcui'], unique=False)
    op.create_index(op.f('ix_drug_interaction_cache_drug2_rxcui'), 'drug_interaction_cache', ['drug2_rxcui'], unique=False)
    op.create_index(op.f('ix_drug_interaction_cache_checked_at'), 'drug_interaction_cache', ['checked_at'], unique=False)
    op.create_index(op.f('ix_drug_interaction_cache_expires_at'), 'drug_interaction_cache', ['expires_at'], unique=False)
    
    # Create drug_suggestions table
    op.create_table('drug_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column('additional_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('primary_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('alternate_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('patient_allergies_checked', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('patient_current_medications', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('interaction_warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('contraindication_alerts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ghana_guideline_notes', sa.Text(), nullable=True),
        sa.Column('ai_rationale', sa.Text(), nullable=True),
        sa.Column('facility_ids_checked', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('was_accepted', sa.Boolean(), nullable=True),
        sa.Column('prescription_created_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('doctor_feedback', sa.Text(), nullable=True),
        sa.Column('processing_time_seconds', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('rxnav_used', sa.Boolean(), nullable=False),
        sa.Column('tavily_searches_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ),
        sa.ForeignKeyConstraint(['prescription_created_id'], ['prescriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_drug_suggestions_patient_id'), 'drug_suggestions', ['patient_id'], unique=False)
    op.create_index(op.f('ix_drug_suggestions_doctor_id'), 'drug_suggestions', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_drug_suggestions_diagnosis'), 'drug_suggestions', ['diagnosis'], unique=False)
    op.create_index(op.f('ix_drug_suggestions_was_accepted'), 'drug_suggestions', ['was_accepted'], unique=False)
    op.create_index(op.f('ix_drug_suggestions_created_at'), 'drug_suggestions', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop drug_suggestions table
    op.drop_index(op.f('ix_drug_suggestions_created_at'), table_name='drug_suggestions')
    op.drop_index(op.f('ix_drug_suggestions_was_accepted'), table_name='drug_suggestions')
    op.drop_index(op.f('ix_drug_suggestions_diagnosis'), table_name='drug_suggestions')
    op.drop_index(op.f('ix_drug_suggestions_doctor_id'), table_name='drug_suggestions')
    op.drop_index(op.f('ix_drug_suggestions_patient_id'), table_name='drug_suggestions')
    op.drop_table('drug_suggestions')
    
    # Drop drug_interaction_cache table
    op.drop_index(op.f('ix_drug_interaction_cache_expires_at'), table_name='drug_interaction_cache')
    op.drop_index(op.f('ix_drug_interaction_cache_checked_at'), table_name='drug_interaction_cache')
    op.drop_index(op.f('ix_drug_interaction_cache_drug2_rxcui'), table_name='drug_interaction_cache')
    op.drop_index(op.f('ix_drug_interaction_cache_drug1_rxcui'), table_name='drug_interaction_cache')
    op.drop_table('drug_interaction_cache')
    
    # Drop patient_allergies table
    op.drop_index(op.f('ix_patient_allergies_is_active'), table_name='patient_allergies')
    op.drop_index(op.f('ix_patient_allergies_severity'), table_name='patient_allergies')
    op.drop_index(op.f('ix_patient_allergies_allergen_type'), table_name='patient_allergies')
    op.drop_index(op.f('ix_patient_allergies_allergen_name'), table_name='patient_allergies')
    op.drop_index(op.f('ix_patient_allergies_patient_id'), table_name='patient_allergies')
    op.drop_table('patient_allergies')

