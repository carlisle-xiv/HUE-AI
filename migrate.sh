#!/bin/bash
# Migration helper script for HUE-AI

set -e

case "$1" in
    init)
        echo "🔄 Generating initial migration..."
        alembic revision --autogenerate -m "Initial migration - health sessions and messages"
        echo "✅ Migration generated successfully!"
        echo ""
        echo "Next step: Run './migrate.sh upgrade' to apply the migration"
        ;;
    
    create)
        if [ -z "$2" ]; then
            echo "❌ Error: Please provide a migration message"
            echo "Usage: ./migrate.sh create \"your message here\""
            exit 1
        fi
        echo "🔄 Creating new migration: $2"
        alembic revision --autogenerate -m "$2"
        echo "✅ Migration created successfully!"
        ;;
    
    upgrade)
        echo "🔄 Applying migrations..."
        alembic upgrade head
        echo "✅ Database up to date!"
        ;;
    
    downgrade)
        echo "🔄 Rolling back last migration..."
        alembic downgrade -1
        echo "✅ Rollback complete!"
        ;;
    
    status)
        echo "📊 Current database status:"
        alembic current
        echo ""
        echo "📜 Migration history:"
        alembic history
        ;;
    
    reset)
        echo "⚠️  WARNING: This will reset the database to base state!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            alembic downgrade base
            echo "✅ Database reset complete!"
        else
            echo "❌ Reset cancelled"
        fi
        ;;
    
    *)
        echo "HUE-AI Migration Helper"
        echo ""
        echo "Usage: ./migrate.sh [command]"
        echo ""
        echo "Commands:"
        echo "  init              Generate initial migration"
        echo "  create <msg>      Create new migration with message"
        echo "  upgrade           Apply all pending migrations"
        echo "  downgrade         Rollback last migration"
        echo "  status            Show current migration status"
        echo "  reset             Reset database to base state (DESTRUCTIVE)"
        echo ""
        echo "Examples:"
        echo "  ./migrate.sh init"
        echo "  ./migrate.sh create \"add user preferences table\""
        echo "  ./migrate.sh upgrade"
        ;;
esac

