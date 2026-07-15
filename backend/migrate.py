"""Database migration: add user_id, batch_id, import_batches table"""
import sqlite3
import os
import glob

backend_dir = os.path.dirname(os.path.abspath(__file__))
db_files = glob.glob(os.path.join(backend_dir, "*.db"))

for db_path in db_files:
    print(f"Processing: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns in subjects
    cursor.execute("PRAGMA table_info(subjects)")
    cols = [r[1] for r in cursor.fetchall()]
    print(f"  subjects columns: {cols}")

    if "user_id" not in cols:
        cursor.execute("ALTER TABLE subjects ADD COLUMN user_id INTEGER")
        print("  Added user_id to subjects")
    else:
        print("  user_id already exists in subjects")

    # Check existing columns in assessments
    cursor.execute("PRAGMA table_info(assessments)")
    cols = [r[1] for r in cursor.fetchall()]
    print(f"  assessments columns: {cols}")

    if "batch_id" not in cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN batch_id INTEGER")
        print("  Added batch_id to assessments")
    else:
        print("  batch_id already exists in assessments")

    # Check if import_batches table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='import_batches'")
    if not cursor.fetchone():
        cursor.execute("""CREATE TABLE import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename VARCHAR(255) NOT NULL,
            import_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_assessments INTEGER DEFAULT 0,
            subjects_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        print("  Created import_batches table")
    else:
        print("  import_batches table already exists")

    # Set user_id for existing subjects (assign to first user)
    cursor.execute("UPDATE subjects SET user_id = (SELECT MIN(id) FROM users) WHERE user_id IS NULL")
    print(f"  Updated {cursor.rowcount} subjects with default user_id")

    # Drop unique index on subjects.subject_id if it exists
    try:
        cursor.execute("DROP INDEX IF EXISTS ix_subjects_subject_id")
        print("  Dropped unique index on subjects.subject_id")
    except Exception as e:
        print(f"  Index drop: {e}")

    conn.commit()
    conn.close()
    print(f"  Done: {db_path}")

print("\nMigration complete!")
