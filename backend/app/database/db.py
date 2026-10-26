import os
import sqlite3
import json
from typing import Optional, Dict, Any, List

DB_PATH = os.environ.get("UNLEARNING_DB_PATH", "./experiments/experiments.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema with tables for experiments, jobs, partitions, and metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()

