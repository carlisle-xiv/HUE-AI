"""Add clinical data prediction tables

Revision ID: a1b2c3d4e5f6
Revises: 7a2d6fbb2074
Create Date: 2024-12-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7a2d6fbb2074'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create demand_forecasts table
    op.create_table(
        'demand_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('pharmacy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granularity', sa.String(length=30), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('forecast_start_date', sa.Date(), nullable=False),
        sa.Column('forecast_end_date', sa.Date(), nullable=False),
        sa.Column('forecast_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_predicted_demand', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('average_daily_demand', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('trend_direction', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.DECIMAL(precision=4, scale=3), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('training_data_points', sa.Integer(), nullable=False),
        sa.Column('training_period_start', sa.Date(), nullable=True),
        sa.Column('training_period_end', sa.Date(), nullable=True),
        sa.Column('actual_demand', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('forecast_error_mape', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['drug_id'], ['pharmacy_codes.id'], ),
        sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_demand_forecasts_pharmacy_id', 'demand_forecasts', ['pharmacy_id'], unique=False)
    op.create_index('ix_demand_forecasts_drug_id', 'demand_forecasts', ['drug_id'], unique=False)
    op.create_index('ix_demand_forecasts_granularity', 'demand_forecasts', ['granularity'], unique=False)
    op.create_index('ix_demand_forecasts_forecast_start_date', 'demand_forecasts', ['forecast_start_date'], unique=False)
    op.create_index('ix_demand_forecasts_created_at', 'demand_forecasts', ['created_at'], unique=False)
    op.create_index('ix_demand_forecasts_scope', 'demand_forecasts', ['pharmacy_id', 'drug_id', 'granularity'], unique=False)
    op.create_index('ix_demand_forecasts_date_range', 'demand_forecasts', ['forecast_start_date', 'forecast_end_date'], unique=False)

    # Create demand_anomalies table
    op.create_table(
        'demand_anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('pharmacy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('anomaly_type', sa.String(length=30), nullable=False),
        sa.Column('anomaly_date', sa.Date(), nullable=False),
        sa.Column('expected_demand', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('actual_demand', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('deviation_percentage', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('deviation_sigma', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('possible_causes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommended_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, default=False),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['drug_id'], ['pharmacy_codes.id'], ),
        sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_demand_anomalies_pharmacy_id', 'demand_anomalies', ['pharmacy_id'], unique=False)
    op.create_index('ix_demand_anomalies_drug_id', 'demand_anomalies', ['drug_id'], unique=False)
    op.create_index('ix_demand_anomalies_anomaly_type', 'demand_anomalies', ['anomaly_type'], unique=False)
    op.create_index('ix_demand_anomalies_anomaly_date', 'demand_anomalies', ['anomaly_date'], unique=False)
    op.create_index('ix_demand_anomalies_severity', 'demand_anomalies', ['severity'], unique=False)
    op.create_index('ix_demand_anomalies_detected_at', 'demand_anomalies', ['detected_at'], unique=False)
    op.create_index('ix_demand_anomalies_scope', 'demand_anomalies', ['pharmacy_id', 'drug_id'], unique=False)
    op.create_index('ix_demand_anomalies_unack', 'demand_anomalies', ['is_acknowledged', 'detected_at'], unique=False)

    # Create seasonality_patterns table
    op.create_table(
        'seasonality_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pattern_type', sa.String(length=30), nullable=False),
        sa.Column('strength', sa.DECIMAL(precision=4, scale=3), nullable=False),
        sa.Column('pattern_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('analysis_period_days', sa.Integer(), nullable=False),
        sa.Column('analysis_start_date', sa.Date(), nullable=False),
        sa.Column('analysis_end_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['drug_id'], ['pharmacy_codes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_seasonality_patterns_drug_id', 'seasonality_patterns', ['drug_id'], unique=False)
    op.create_index('ix_seasonality_patterns_pattern_type', 'seasonality_patterns', ['pattern_type'], unique=False)
    op.create_index('ix_seasonality_patterns_created_at', 'seasonality_patterns', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('seasonality_patterns')
    op.drop_table('demand_anomalies')
    op.drop_table('demand_forecasts')

