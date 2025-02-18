import sqlite3
from project_tracker.config import DATABASE


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DATABASE)


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create projects table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """
    )
    
    # Create project_status table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_status(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            commit_time TEXT NOT NULL,
            projected_end_date TEXT NOT NULL
        );
        """
    )
    
    # Create employees table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """
    )
    
    conn.commit()
    conn.close() 