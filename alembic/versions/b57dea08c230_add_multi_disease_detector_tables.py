"""add_multi_disease_detector_tables

Revision ID: b57dea08c230
Revises: 01d0746e25a3
Create Date: 2025-10-22 22:44:33.662385

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b57dea08c230'
down_revision = '01d0746e25a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table('chat_sessions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', sa.Uuid(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_sessions_patient_id'), 'chat_sessions', ['patient_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_status'), 'chat_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_chat_sessions_created_at'), 'chat_sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_chat_sessions_last_message_at'), 'chat_sessions', ['last_message_at'], unique=False)
    
    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_role'), 'chat_messages', ['role'], unique=False)
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop chat_messages table
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_role'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_session_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    
    # Drop chat_sessions table
    op.drop_index(op.f('ix_chat_sessions_last_message_at'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_created_at'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_status'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_patient_id'), table_name='chat_sessions')
    op.drop_table('chat_sessions')

