import os
import sqlite3
import json
from typing import Optional, Dict, Any, List

DB_PATH = os.environ.get("UNLEARNING_DB_PATH", "./experiments/experiments.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema with tables for experiments, jobs, partitions, and metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")

    # Experiments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        dataset_name TEXT NOT NULL,
        model_name TEXT NOT NULL,
        status TEXT NOT NULL,
        seed INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        train_config TEXT,
        partition_manifest TEXT,
        unlearn_config TEXT,
        original_checkpoint_path TEXT,
        retrained_checkpoint_path TEXT,
        unlearned_checkpoint_path TEXT,
        metrics TEXT,
        insights TEXT
    )
    """)

    # Jobs table for async tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        progress REAL DEFAULT 0.0,
        current_step TEXT,
        logs TEXT,
        error_message TEXT,
        result TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (experiment_id) REFERENCES experiments (id)
    )
    """)

    # Forgetting requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forgetting_requests (
        id TEXT PRIMARY KEY,
        request_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        scope_description TEXT,
        affected_records_count INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        confirmation_status TEXT NOT NULL,
        job_id TEXT,
        impact_preview TEXT,
        verification_report TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Chat sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        dataset_name TEXT NOT NULL,
        author_id TEXT,
        messages TEXT,
        pending_request TEXT,
        unlearned_records TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Experiments schema migrations
    for col, col_type in [("knowledge_store_version", "TEXT DEFAULT 'v1.0-clean'"), ("model_baseline", "TEXT DEFAULT 'original'")]:
        try:
            cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Forgetting requests migrations
    for col, col_type in [("experiment_id", "TEXT"), ("dataset_version", "TEXT DEFAULT 'v1.0-clean'"), ("knowledge_store_version", "TEXT DEFAULT 'v1.0-clean'")]:
        try:
            cursor.execute(f"ALTER TABLE forgetting_requests ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Chat sessions migrations
    for col, col_type in [("pending_request", "TEXT"), ("unlearned_records", "TEXT"), ("experiment_id", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE chat_sessions ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Global unlearning registry table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_unlearning_registry (
        id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL,
        target_author_id TEXT NOT NULL,
        target_author_name TEXT,
        target_identifier TEXT,
        qa_ids TEXT NOT NULL,
        request_id TEXT,
        experiment_id TEXT,
        dataset_version TEXT DEFAULT 'v1.0-clean',
        knowledge_store_version TEXT DEFAULT 'v1.0-clean',
        status TEXT NOT NULL DEFAULT 'CONFIRMED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_unlearning_registry_author ON global_unlearning_registry(target_author_id)")
    for col, col_type in [("experiment_id", "TEXT"), ("dataset_version", "TEXT DEFAULT 'v1.0-clean'"), ("knowledge_store_version", "TEXT DEFAULT 'v1.0-clean'")]:
        try:
            cursor.execute(f"ALTER TABLE global_unlearning_registry ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_unlearning_registry_exp_author ON global_unlearning_registry(experiment_id, target_author_id)")

    # Legacy Author unlearning status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS author_unlearning_status (
        author_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'ACTIVE_KNOWLEDGE',
        current_step TEXT,
        progress REAL DEFAULT 0.0,
        request_id TEXT,
        job_id TEXT,
        scope_type TEXT,
        data_deleted BOOLEAN DEFAULT 0,
        retrieval_updated BOOLEAN DEFAULT 0,
        unlearning_completed BOOLEAN DEFAULT 0,
        verification_passed BOOLEAN DEFAULT 0,
        error_message TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_author_status_id ON author_unlearning_status(author_id)")

    # Experiment-scoped Author unlearning status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiment_author_unlearning_status (
        id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE_KNOWLEDGE',
        current_step TEXT,
        progress REAL DEFAULT 0.0,
        request_id TEXT,
        job_id TEXT,
        scope_type TEXT,
        data_deleted BOOLEAN DEFAULT 0,
        retrieval_updated BOOLEAN DEFAULT 0,
        unlearning_completed BOOLEAN DEFAULT 0,
        verification_passed BOOLEAN DEFAULT 0,
        error_message TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(experiment_id, author_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_author_status ON experiment_author_unlearning_status(experiment_id, author_id)")

    conn.commit()
    conn.close()

