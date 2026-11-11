import sqlite3
from pathlib import Path


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "careerpilot.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # USER PROFILES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            education TEXT,
            experience TEXT,
            interests TEXT,
            target_role TEXT,
            institution TEXT,
            study_year TEXT,
            skills TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # Add missing columns safely to existing databases
    cursor.execute("PRAGMA table_info(profiles)")
    profile_columns = [
        row["name"] for row in cursor.fetchall()
    ]

    for column in ["institution", "study_year", "skills"]:
        if column not in profile_columns:
            cursor.execute(
                f"ALTER TABLE profiles ADD COLUMN {column} TEXT"
            )

    # -----------------------------------------------------
    # RESUMES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT,
            resume_text TEXT,
            resume_score INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # RESUME SKILLS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            skill_score INTEGER DEFAULT 0,
            FOREIGN KEY (resume_id)
                REFERENCES resumes(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # SKILLS MASTER TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT
        )
    """)

    # -----------------------------------------------------
    # JOB ROLES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # -----------------------------------------------------
    # ROLE REQUIRED SKILLS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            importance INTEGER DEFAULT 50,

            UNIQUE(role_id, skill_id),

            FOREIGN KEY (role_id)
                REFERENCES job_roles(id)
                ON DELETE CASCADE,

            FOREIGN KEY (skill_id)
                REFERENCES skills(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # SKILL GAP RESULTS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            match_score INTEGER DEFAULT 0,
            skills_have TEXT,
            skills_missing TEXT,
            analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (role_id)
                REFERENCES job_roles(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # CAREER ROADMAP
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            roadmap_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (role_id)
                REFERENCES job_roles(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # JOBS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            job_type TEXT,
            experience_level TEXT,
            description TEXT,
            skills_required TEXT,
            source_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # JOB MATCHING
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            match_score INTEGER DEFAULT 0,
            matched_skills TEXT,
            missing_skills TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # CAREER REPORTS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS career_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_role TEXT,
            readiness_score INTEGER DEFAULT 0,
            report_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # AI CAREER COACH CHAT MESSAGES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # AI CAREER COACH SUGGESTED QUESTIONS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggested_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================================================
    # ATS RESUME TEMPLATES
    # =========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL UNIQUE,

            full_name TEXT NOT NULL,
            professional_title TEXT,

            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin TEXT,
            github TEXT,

            summary TEXT,

            education TEXT,

            skills TEXT,

            work_experience TEXT,

            internships TEXT,

            projects TEXT,

            certifications TEXT,

            is_fresher INTEGER DEFAULT 1,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# RUN DATABASE INITIALIZATION
# =========================================================

if __name__ == "__main__":

    initialize_database()

    print("========================================")
    print("CareerPilot AI Database")
    print("========================================")
    print("Database created successfully.")
    print(f"Location: {DATABASE_PATH}")
    print("========================================")