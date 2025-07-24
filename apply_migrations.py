#!/usr/bin/env python3
"""
Apply Supabase migrations to production database
"""
import psycopg2
import os
from pathlib import Path

# Database connection
DATABASE_URL = "postgresql://postgres:UPD_qnj.fda!npe3ghy@db.ehqssdhhekqyzqkvormf.supabase.co:5432/postgres"

def apply_migration(cursor, migration_file):
    """Apply a single migration file"""
    print(f"📄 Applying {migration_file.name}...")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Execute the migration
    try:
        cursor.execute(sql)
        print(f"✅ {migration_file.name} applied successfully")
        return True
    except Exception as e:
        print(f"❌ {migration_file.name} failed: {e}")
        return False

def main():
    print("🔄 Starting database migration process...")
    
    # Connect to database
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Each migration is a transaction
        cursor = conn.cursor()
        print("✅ Connected to production database")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Migration files in order
    base_dir = Path("/Users/mitch/Documents/Projects/mental-model")
    migration_dir = base_dir / "supabase/migrations"
    migration_files = [
        migration_dir / "20250122000001_create_user_profiles.sql",
        migration_dir / "20250122000002_create_chat_tables.sql", 
        migration_dir / "20250723160127_create_business_profile_tables.sql",
        migration_dir / "20250124000001_create_questionnaire_tables.sql"
    ]
    
    # Apply migrations
    success_count = 0
    for migration_file in migration_files:
        if migration_file.exists():
            if apply_migration(cursor, migration_file):
                success_count += 1
        else:
            print(f"⚠️ Migration file not found: {migration_file}")
    
    cursor.close()
    conn.close()
    
    print(f"\n🎉 Migration process complete: {success_count}/{len(migration_files)} successful")

if __name__ == "__main__":
    main()