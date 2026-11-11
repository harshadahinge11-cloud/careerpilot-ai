from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

from backend.database import get_connection, initialize_database
from backend import ai_service
from backend.ai_service import ai_coach_reply, ai_resume_feedback, ai_skill_gap_advice, ai_job_insight

import io
import os
import hashlib


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="CareerPilot AI",
    description="AI Career & Job Copilot API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

initialize_database()


def ensure_admin_column():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "role" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'"
        )
        connection.commit()

    connection.close()


ensure_admin_column()


# =========================================================
# ADMIN API KEY
# =========================================================

ADMIN_API_KEY = os.getenv(
    "CAREERPILOT_ADMIN_KEY",
    "careerpilot-admin-2026"
)


def verify_admin(admin_key: str | None):

    if admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )


# =========================================================
# MODELS
# =========================================================

class ChatRequest(BaseModel):
    message: str
    user_id: int
    topic: str | None = None

class ResumeTemplateRequest(BaseModel):
    user_id: int

    full_name: str
    professional_title: str = ""

    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""

    summary: str = ""

    education: str = ""

    skills: str = ""

    work_experience: str = ""

    internships: str = ""

    projects: str = ""

    certifications: str = ""

    is_fresher: bool = True


class RoleCreateRequest(BaseModel):
    name: str
    description: str = ""


class RoleUpdateRequest(BaseModel):
    name: str
    description: str = ""


class RoleSkillRequest(BaseModel):
    skill_id: int
    importance: int = 50


class AdminSkillCreateRequest(BaseModel):
    name: str
    category: str = ""


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    user_id: int
    current_password: str
    new_password: str

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class RoadmapRequest(BaseModel):
    user_id: int

class ProfileUpdateRequest(BaseModel):
    fullName: str = ""
    phone: str = ""
    location: str = ""
    education: str = ""
    institution: str = ""
    studyYear: str = ""
    experience: str = ""
    targetRole: str = ""
    interests: str = ""
    skills: str = ""
    bio: str = ""

# =========================================================
# PASSWORD FUNCTIONS
# =========================================================

def secrets_compare(a: str, b: str) -> bool:

    import hmac

    return hmac.compare_digest(a, b)


def hash_password(password: str) -> str:

    iterations = 120000

    salt = os.urandom(16).hex()

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations
    ).hex()

    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:

    try:

        algorithm, iterations, salt, digest = stored_hash.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations)
        ).hex()

        return secrets_compare(
            calculated,
            digest
        )

    except (ValueError, TypeError):

        return False

# =========================================================
# CHANGE PASSWORD
# =========================================================

class ChangePasswordRequest(BaseModel):
    user_id: int
    current_password: str
    new_password: str


@app.post("/auth/change-password")
def change_password(request: ChangePasswordRequest):

    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must contain at least 6 characters."
        )

    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password."
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (request.user_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        if not verify_password(
            request.current_password,
            user["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Current password is incorrect."
            )

        new_hash = hash_password(request.new_password)

        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, request.user_id)
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Password changed successfully."
        }

    finally:
        connection.close()


# =========================================================
# AUTHENTICATION
# =========================================================

@app.post("/auth/register")
def register_user(request: RegisterRequest):

    name = request.name.strip()
    email = request.email.strip().lower()
    password = request.password

    if not name or not email or not password:

        raise HTTPException(
            status_code=400,
            detail="Name, email and password are required."
        )

    if len(password) < 6:

        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 6 characters."
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE LOWER(email) = ?",
        (email,)
    )

    if cursor.fetchone():

        connection.close()

        raise HTTPException(
            status_code=409,
            detail="Email already registered."
        )

    cursor.execute(
        """
        INSERT INTO users
        (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            email,
            hash_password(password),
            "user"
        )
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return {
        "status": "success",
        "message": "Registration successful.",
        "user_id": user_id,
        "name": name,
        "email": email,
        "role": "user"
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/auth/login")
def login_user(request: LoginRequest):

    email = request.email.strip().lower()

    if not email or not request.password:

        raise HTTPException(
            status_code=400,
            detail="Email and password are required."
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            password_hash,
            role
        FROM users
        WHERE LOWER(email) = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    return {
        "status": "success",
        "message": "Login successful.",
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }


# =========================================================
# USER — GET LOGGED-IN USER
# =========================================================

@app.get("/users/{user_id}")
def get_user(user_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            role
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return {
        "status": "success",
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }

@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                u.id,
                u.name,
                u.email,
                p.education,
                p.experience,
                p.interests,
                p.target_role,
                p.institution,
                p.study_year,
                p.skills
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        return {
            "status": "success",
            "profile": {
                "fullName": user["name"] or "",
                "email": user["email"] or "",
                "education": user["education"] or "",
                "experience": user["experience"] or "",
                "interests": user["interests"] or "",
                "targetRole": user["target_role"] or "",
                "institution": user["institution"] or "",
                "studyYear": user["study_year"] or "",
                "skills": user["skills"] or ""
            }
        }

    finally:
        connection.close()

@app.put("/users/{user_id}")
def update_user_profile(user_id: int, request: ProfileUpdateRequest):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Check whether the user exists
        cursor.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Update the account name
        cursor.execute(
            "UPDATE users SET name = ? WHERE id = ?",
            (request.fullName, user_id)
        )

        # Insert or update the user's profile
        cursor.execute("""
            INSERT INTO profiles (
                user_id,
                education,
                experience,
                interests,
                target_role,
                institution,
                study_year,
                skills,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                education = excluded.education,
                experience = excluded.experience,
                interests = excluded.interests,
                target_role = excluded.target_role,
                institution = excluded.institution,
                study_year = excluded.study_year,
                skills = excluded.skills,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            request.education,
            request.experience,
            request.interests,
            request.targetRole,
            request.institution,
            request.studyYear,
            request.skills
        ))

        connection.commit()

        return {
            "status": "success",
            "message": "Profile updated successfully."
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update profile."
        )

    finally:
        connection.close()


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.post("/admin/login")
def admin_login(request: AdminLoginRequest):

    email = request.email.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            password_hash,
            role
        FROM users
        WHERE LOWER(email) = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user or user["role"] != "admin":

        raise HTTPException(
            status_code=401,
            detail="Admin account not found or access denied."
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    return {
        "status": "success",
        "message": "Admin login successful.",
        "name": user["name"],
        "admin_key": ADMIN_API_KEY
    }


# =========================================================
# HOME
# =========================================================

from fastapi.responses import RedirectResponse

@app.get("/")
def home():
       return RedirectResponse(url="/index.html")


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# =========================================================
# DATABASE — JOB ROLES
# =========================================================

@app.get("/roles")
def get_roles():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            description
        FROM job_roles
        ORDER BY name
        """
    )

    roles = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return {
        "status": "success",
        "roles": roles
    }


# =========================================================
# DATABASE — REQUIRED SKILLS FOR ROLE
# =========================================================

@app.get("/roles/{role_name}/skills")
def get_role_skills(role_name: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.id,
            s.name,
            s.category,
            rs.importance
        FROM role_skills rs
        JOIN skills s
            ON rs.skill_id = s.id
        JOIN job_roles r
            ON rs.role_id = r.id
        WHERE r.name = ?
        ORDER BY rs.importance DESC
        """,
        (role_name,)
    )

    skills = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    if not skills:

        return {
            "status": "error",
            "message": "Job role not found or no skills available."
        }

    return {
        "status": "success",
        "role": role_name,
        "skills": skills
    }


# =========================================================
# ADMIN — ROLE MANAGEMENT
# =========================================================

@app.get("/admin/roles")
def admin_get_roles(
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            r.id,
            r.name,
            r.description,
            COUNT(rs.id) AS skill_count
        FROM job_roles r
        LEFT JOIN role_skills rs
            ON r.id = rs.role_id
        GROUP BY r.id
        ORDER BY r.name
        """
    )

    roles = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return {
        "status": "success",
        "roles": roles
    }


@app.post("/admin/roles")
def admin_create_role(
    request: RoleCreateRequest,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    name = request.name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Role name is required."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO job_roles
            (name, description)
            VALUES (?, ?)
            """,
            (
                name,
                request.description.strip()
            )
        )

        connection.commit()

        role_id = cursor.lastrowid

    except Exception as e:

        connection.close()

        if "UNIQUE" in str(e).upper():

            raise HTTPException(
                status_code=409,
                detail="This job role already exists."
            )

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    connection.close()

    return {
        "status": "success",
        "message": "Job role created successfully.",
        "role_id": role_id
    }


@app.put("/admin/roles/{role_id}")
def admin_update_role(
    role_id: int,
    request: RoleUpdateRequest,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    name = request.name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Role name is required."
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM job_roles
        WHERE id = ?
        """,
        (role_id,)
    )

    if not cursor.fetchone():

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Job role not found."
        )

    try:

        cursor.execute(
            """
            UPDATE job_roles
            SET
                name = ?,
                description = ?
            WHERE id = ?
            """,
            (
                name,
                request.description.strip(),
                role_id
            )
        )

        connection.commit()

    except Exception as e:

        connection.close()

        if "UNIQUE" in str(e).upper():

            raise HTTPException(
                status_code=409,
                detail="Another job role already uses this name."
            )

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    connection.close()

    return {
        "status": "success",
        "message": "Job role updated successfully."
    }


@app.delete("/admin/roles/{role_id}")
def admin_delete_role(
    role_id: int,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM job_roles
        WHERE id = ?
        """,
        (role_id,)
    )

    role = cursor.fetchone()

    if not role:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Job role not found."
        )

    cursor.execute(
        """
        DELETE FROM job_roles
        WHERE id = ?
        """,
        (role_id,)
    )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "message": f"Role '{role['name']}' deleted successfully."
    }


# =========================================================
# ADMIN — SKILL MANAGEMENT
# =========================================================

@app.get("/admin/skills")
def admin_get_skills(
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            category
        FROM skills
        ORDER BY name
        """
    )

    skills = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return {
        "status": "success",
        "skills": skills
    }


@app.post("/admin/skills")
def admin_create_skill(
    request: AdminSkillCreateRequest,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    name = request.name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Skill name is required."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO skills
            (name, category)
            VALUES (?, ?)
            """,
            (
                name,
                request.category.strip()
            )
        )

        connection.commit()

        skill_id = cursor.lastrowid

    except Exception as e:

        connection.close()

        if "UNIQUE" in str(e).upper():

            raise HTTPException(
                status_code=409,
                detail="This skill already exists."
            )

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    connection.close()

    return {
        "status": "success",
        "message": "Skill created successfully.",
        "skill_id": skill_id
    }


@app.get("/admin/roles/{role_id}/skills")
def admin_get_role_skills(
    role_id: int,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.id,
            s.name,
            s.category,
            rs.importance
        FROM role_skills rs
        JOIN skills s
            ON rs.skill_id = s.id
        WHERE rs.role_id = ?
        ORDER BY rs.importance DESC, s.name
        """,
        (role_id,)
    )

    skills = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return {
        "status": "success",
        "role_id": role_id,
        "skills": skills
    }


@app.post("/admin/roles/{role_id}/skills")
def admin_add_role_skill(
    role_id: int,
    request: RoleSkillRequest,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    importance = max(
        0,
        min(100, request.importance)
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM job_roles
        WHERE id = ?
        """,
        (role_id,)
    )

    if not cursor.fetchone():

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Job role not found."
        )

    cursor.execute(
        """
        SELECT id
        FROM skills
        WHERE id = ?
        """,
        (request.skill_id,)
    )

    if not cursor.fetchone():

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Skill not found."
        )

    cursor.execute(
        """
        INSERT INTO role_skills
        (role_id, skill_id, importance)
        VALUES (?, ?, ?)
        ON CONFLICT(role_id, skill_id)
        DO UPDATE SET
            importance = excluded.importance
        """,
        (
            role_id,
            request.skill_id,
            importance
        )
    )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "message": "Required skill added/updated successfully."
    }


@app.delete("/admin/roles/{role_id}/skills/{skill_id}")
def admin_remove_role_skill(
    role_id: int,
    skill_id: int,
    x_admin_key: str | None = Header(default=None)
):

    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM role_skills
        WHERE role_id = ?
        AND skill_id = ?
        """,
        (
            role_id,
            skill_id
        )
    )

    if cursor.rowcount == 0:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Role skill assignment not found."
        )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "message": "Required skill removed from role."
    }


# =========================================================
# AI CAREER COACH
# =========================================================

def generate_career_response(message: str, user_id: int | None = None, topic: str | None = None):
    # Real AI first (Gemini). If key missing / API fails -> old rule-based answers.
    ai_text = ai_coach_reply(message, user_id, topic)
    if ai_text:
        return ai_text
    return generate_rule_based_response(message)


def generate_rule_based_response(message: str):

    message = message.lower().strip()

    # -----------------------------------------------------
    # GREETING
    # -----------------------------------------------------

    if message in [
        "hi",
        "hello",
        "hey",
        "hii",
        "helo",
        "good morning",
        "good afternoon",
        "good evening"
    ]:

        return """
Hello! I'm CareerPilot AI, your AI Career Coach.

I can help you with:

• Career planning
• Job roles
• Skill gap analysis
• Learning roadmaps
• Data Engineering
• Data Analytics
• AWS / Cloud
• AI & Machine Learning
• MCA career planning
• Projects
• Resume improvement
• Interview preparation
• Certifications
• GitHub and portfolio building

Tell me your target career or ask me a career question.
"""


    # -----------------------------------------------------
    # THANK YOU
    # -----------------------------------------------------

    elif (
        "thank you" in message
        or "thanks" in message
        or "thank u" in message
    ):

        return """
You're welcome!

I'm here whenever you need help with your career, skills,
projects, resume, interviews, or job preparation.

Ask me your next question and we'll work on it together.
"""


    # -----------------------------------------------------
    # DATA ENGINEER
    # -----------------------------------------------------

    elif (
        "data engineer" in message
        or "data engineering" in message
    ):

        return """
Data Engineering is a strong career path if you enjoy working
with data, databases, programming and cloud technologies.

CORE SKILLS

1. Python
2. SQL
3. Database fundamentals
4. Linux
5. Git & GitHub
6. AWS / Cloud
7. ETL pipelines
8. Apache Spark
9. Apache Airflow
10. Docker
11. Data Warehousing
12. APIs

RECOMMENDED LEARNING ORDER

Python
↓
SQL
↓
Linux
↓
Git & GitHub
↓
Databases
↓
AWS
↓
ETL
↓
Spark
↓
Airflow
↓
Docker

BEGINNER PROJECTS

• CSV to Database ETL Pipeline
• Sales Data Pipeline
• AWS Data Lake
• Weather Data Pipeline
• Customer Data Processing System

JOB PREPARATION

Build 2–3 projects, upload them to GitHub, create a strong
resume and practice Python + SQL interview questions.

If you're a fresher, focus on strong fundamentals rather than
trying to learn every technology at once.
"""


    # -----------------------------------------------------
    # DATA ANALYST
    # -----------------------------------------------------

    elif (
        "data analyst" in message
        or "data analytics" in message
        or "data analysis" in message
        or "analyst career" in message
    ):

        return """
Data Analyst is a good career choice if you enjoy analyzing
data and finding useful business insights.

CORE SKILLS

1. Excel
2. SQL
3. Statistics
4. Python
5. Pandas
6. Data Visualization
7. Power BI
8. Tableau
9. Business understanding
10. Communication

RECOMMENDED ORDER

Excel
↓
SQL
↓
Statistics
↓
Power BI
↓
Python
↓
Pandas
↓
Projects

PROJECT IDEAS

• Sales Dashboard
• Customer Analysis
• E-commerce Analysis
• Employee Data Analysis
• Financial Dashboard

FOR FRESHERS

Focus on SQL, Excel and Power BI first. Then add Python and
Pandas to make your profile stronger.
"""


    # -----------------------------------------------------
    # AWS / CLOUD
    # -----------------------------------------------------

    elif (
        "aws" in message
        or "cloud engineer" in message
        or "cloud computing" in message
        or "cloud career" in message
        or "cloud" in message
    ):

        return """
For an AWS Cloud career, build your knowledge step by step.

FOUNDATION

1. Linux
2. Networking
3. Operating system basics
4. Git & GitHub

AWS FUNDAMENTALS

5. IAM
6. EC2
7. S3
8. VPC
9. RDS
10. CloudWatch
11. Load Balancer
12. Auto Scaling

NEXT LEVEL

13. Docker
14. Terraform
15. CI/CD
16. AWS Lambda
17. CloudFormation

RECOMMENDED ROADMAP

Linux
↓
Networking
↓
AWS Fundamentals
↓
EC2 + S3 + IAM
↓
VPC
↓
Docker
↓
Terraform
↓
Projects
↓
Interview Preparation

PROJECT IDEAS

• Host a static website on S3
• Deploy a web application on EC2
• Build a monitoring system using CloudWatch
• Create a secure VPC architecture
• Deploy a Docker application on AWS
"""


    # -----------------------------------------------------
    # AI / MACHINE LEARNING
    # -----------------------------------------------------

    elif (
        "machine learning" in message
        or "ml career" in message
        or "artificial intelligence" in message
        or " ai " in f" {message} "
        or message == "ai"
        or "ai engineer" in message
    ):

        return """
For an AI / Machine Learning career, build strong fundamentals
before moving to advanced AI tools.

FOUNDATION

1. Python
2. Mathematics basics
3. Statistics
4. NumPy
5. Pandas
6. Data Visualization

MACHINE LEARNING

7. Regression
8. Classification
9. Clustering
10. Feature Engineering
11. Model Evaluation
12. Scikit-learn

ADVANCED

13. Deep Learning
14. Neural Networks
15. NLP
16. Computer Vision
17. Generative AI
18. LLM fundamentals

PROJECT IDEAS

• House Price Prediction
• Customer Churn Prediction
• Job Skill Trend Detector
• Resume Skill Analyzer
• Recommendation System

Recommended path:

Python → Statistics → Pandas → ML → Projects → Deep Learning → AI
"""


    # -----------------------------------------------------
    # MCA
    # -----------------------------------------------------

    elif (
        "mca" in message
        or "after mca" in message
        or "mca student" in message
    ):

        return """
As an MCA student, you have several technology career options.

POPULAR PATHS

• Cloud / AWS
• Data Engineering
• Data Analytics
• Software Development
• AI / Machine Learning
• Cybersecurity
• DevOps

If you are interested in Cloud + Data:

Linux
↓
Python
↓
SQL
↓
Git & GitHub
↓
AWS
↓
Databases
↓
Data Engineering
↓
Projects

DURING MCA

Year 1:
• Build fundamentals
• Learn one career path
• Build 1–2 projects

Year 2:
• Advanced skills
• Internship
• Major project
• Resume building
• Interview preparation

Before graduation, aim to have:

• 2–4 good projects
• GitHub profile
• LinkedIn profile
• Resume
• Relevant certification
• Interview preparation
"""


    # -----------------------------------------------------
    # SKILLS
    # -----------------------------------------------------

    elif (
        "skills" in message
        or "skill" in message
        or "what should i learn" in message
        or "what should i study" in message
    ):

        return """
The right skills depend on your target role.

FOR DATA ENGINEERING

• Python
• SQL
• Linux
• Git
• AWS
• ETL
• Spark
• Airflow
• Docker

FOR DATA ANALYTICS

• Excel
• SQL
• Power BI
• Statistics
• Python
• Pandas

FOR CLOUD

• Linux
• Networking
• AWS
• Docker
• Terraform
• CI/CD

FOR AI / ML

• Python
• Statistics
• Pandas
• NumPy
• Machine Learning
• Scikit-learn
• Deep Learning

Don't learn everything simultaneously.

Choose one target role and build skills specifically for that
career.
"""


    # -----------------------------------------------------
    # SKILL GAP
    # -----------------------------------------------------

    elif (
        "skill gap" in message
        or "missing skill" in message
        or "skills am i missing" in message
        or "what skills am i missing" in message
    ):

        return """
A skill gap means the difference between the skills you currently
have and the skills required for your target job.

For example, for a Data Engineer:

FOUNDATION

✓ Python
✓ SQL
✓ Linux
✓ Git

CORE DATA

• ETL
• Data Warehousing
• APIs

BIG DATA

• Spark
• Airflow

CLOUD

• AWS
• S3
• EC2
• IAM

DEPLOYMENT

• Docker
• Terraform

For a personalized skill-gap analysis, combine your current
skills with a specific target role.

Example:

"My skills are Python, SQL and Linux. I want to become a Data
Engineer."
"""


    # -----------------------------------------------------
    # ROADMAP
    # -----------------------------------------------------

    elif (
        "roadmap" in message
        or "learning path" in message
        or "learn step by step" in message
        or "how should i learn" in message
    ):

        return """
Here's a practical career roadmap.

PHASE 1 — FOUNDATION

• Programming
• SQL
• Linux
• Git & GitHub

PHASE 2 — CAREER SKILLS

Data Engineering:
Python + SQL + ETL + AWS + Spark

Data Analytics:
SQL + Excel + Power BI + Python

Cloud:
Linux + Networking + AWS + Docker

AI / ML:
Python + Statistics + Pandas + Machine Learning

PHASE 3 — PROJECTS

Build 2–3 practical projects.

PHASE 4 — PORTFOLIO

• GitHub
• LinkedIn
• Resume
• Project documentation

PHASE 5 — JOB PREPARATION

• Technical interview
• HR interview
• Aptitude
• Mock interviews
• Job applications
"""


    # -----------------------------------------------------
    # PROJECTS
    # -----------------------------------------------------

    elif (
        "project" in message
        or "projects" in message
        or "portfolio project" in message
    ):

        return """
Here are strong beginner-friendly projects.

DATA ENGINEERING

1. CSV to SQL ETL Pipeline
2. Sales Data Pipeline
3. AWS Data Lake
4. Customer Data Pipeline
5. Real-time Data Processing

DATA ANALYTICS

1. Sales Dashboard
2. Customer Churn Analysis
3. E-commerce Analysis
4. Employee Analytics
5. Financial Dashboard

CLOUD

1. AWS Static Website
2. EC2 Web Application
3. Cloud Monitoring System
4. AWS VPC Architecture
5. Docker Application Deployment

AI / ML

1. House Price Prediction
2. Customer Churn Prediction
3. Recommendation System
4. Resume Analyzer
5. Job Skill Trend Detector

For a fresher portfolio, 2–3 properly documented projects are
better than many incomplete projects.
"""


    # -----------------------------------------------------
    # RESUME
    # -----------------------------------------------------

    elif (
        "resume" in message
        or "cv" in message
        or "curriculum vitae" in message
    ):

        return """
For a fresher technology resume, keep the structure simple and
job-focused.

RECOMMENDED SECTIONS

1. Name + Contact
2. LinkedIn + GitHub
3. Career Objective / Summary
4. Education
5. Technical Skills
6. Projects
7. Certifications
8. Achievements / Activities

IMPORTANT TIPS

• Keep it around one page when possible.
• Put relevant technical skills near the top.
• Add 2–4 strong projects.
• Explain what you built and what technologies you used.
• Add GitHub links.
• Add relevant certifications.
• Avoid unnecessary personal information.
• Use clear professional formatting.
"""


    # -----------------------------------------------------
    # INTERVIEW
    # -----------------------------------------------------

    elif (
        "interview" in message
        or "interview preparation" in message
        or "prepare for interview" in message
    ):

        return """
For a technology interview, prepare in four areas.

1. TECHNICAL FUNDAMENTALS

Python:
• Data types
• Functions
• OOP
• Lists and dictionaries
• Exception handling
• File handling

SQL:
• SELECT
• WHERE
• JOIN
• GROUP BY
• HAVING
• Subqueries
• Window functions

2. ROLE-SPECIFIC SKILLS

Data Engineer:
• ETL
• Databases
• Data pipelines
• Spark
• Airflow
• AWS

Cloud:
• Linux
• Networking
• IAM
• EC2
• S3
• VPC

Data Analyst:
• SQL
• Excel
• Power BI
• Statistics

3. PROJECT QUESTIONS

Be ready to explain:

• What problem did you solve?
• Why did you choose the technology?
• What was your contribution?
• What challenges did you face?
• How did you solve them?
• What would you improve?

4. HR QUESTIONS

Prepare answers for:

• Tell me about yourself.
• Why should we hire you?
• Why this role?
• What are your strengths?
• Where do you see yourself in five years?
"""


    # -----------------------------------------------------
    # JOBS
    # -----------------------------------------------------

    elif (
        "job" in message
        or "jobs" in message
        or "job role" in message
        or "career opportunity" in message
    ):

        return """
For a fresher, focus on roles that match your current skills.

POSSIBLE ENTRY-LEVEL ROLES

DATA

• Junior Data Analyst
• Data Analyst Intern
• Junior Data Engineer
• Data Engineering Intern

CLOUD

• Cloud Support Associate
• Cloud Intern
• Junior Cloud Engineer
• AWS Support Associate

DEVELOPMENT

• Python Developer
• Backend Developer
• Software Developer

AI / DATA

• ML Intern
• AI Intern
• Data Science Intern

Before applying, make sure your resume, GitHub and LinkedIn
support the role you are targeting.
"""


    # -----------------------------------------------------
    # CERTIFICATIONS
    # -----------------------------------------------------

    elif (
        "certification" in message
        or "certifications" in message
        or "certificate" in message
    ):

        return """
Certifications can strengthen a fresher profile, but they should
support practical skills rather than replace them.

FOR CLOUD

• AWS certifications
• Azure certifications
• Google Cloud certifications

FOR DATA

• SQL certifications
• Power BI certifications
• Data analytics certifications

FOR DEVOPS / CLOUD

• Docker
• Kubernetes
• Terraform-related learning

Best strategy:

Certification
+
Practical project
+
GitHub documentation
+
Interview preparation
"""


    # -----------------------------------------------------
    # GITHUB
    # -----------------------------------------------------

    elif (
        "github" in message
        or "git hub" in message
        or "portfolio" in message
    ):

        return """
Your GitHub should demonstrate what you can actually build.

A good project repository should contain:

• Clear project name
• README.md
• Project description
• Technologies used
• Installation steps
• Screenshots
• Features
• Project structure
• Future improvements

Example:

CareerPilot AI
├── frontend
├── backend
├── README.md
└── requirements.txt

For a fresher, 2–4 quality repositories are a strong starting
point.
"""


    # -----------------------------------------------------
    # FRESHER
    # -----------------------------------------------------

    elif (
        "fresher" in message
        or "fresh graduate" in message
        or "no experience" in message
        or "without experience" in message
    ):

        return """
Being a fresher does not mean you have nothing to show.

Build evidence of your skills through:

1. Academic projects
2. Personal projects
3. Internships
4. Certifications
5. GitHub
6. LinkedIn
7. Technical practice

A strong fresher profile can contain:

• 2–4 practical projects
• Relevant technical skills
• Certifications
• GitHub repositories
• Good communication
• Interview preparation

Focus on explaining what you have built and what you learned.
"""


    # -----------------------------------------------------
    # COMMUNICATION
    # -----------------------------------------------------

    elif (
        "communication" in message
        or "english" in message
        or "spoken english" in message
        or "improve communication" in message
    ):

        return """
Good communication is important in technology roles because you
need to explain your ideas, projects and technical decisions.

A simple daily routine:

10 minutes — Read technical content aloud
10 minutes — Explain one technical topic
10 minutes — Practice interview questions
10 minutes — Learn professional vocabulary

For interviews, practice explaining:

• Your introduction
• Your projects
• Your technical skills
• Your strengths
• Problems you solved

Clear, simple and confident communication is more important than
using difficult words.
"""


    # -----------------------------------------------------
    # CAREER CONFUSION
    # -----------------------------------------------------

    elif (
        "which career" in message
        or "which field" in message
        or "confused" in message
        or "career choice" in message
        or "best career" in message
    ):

        return """
Choosing a career becomes easier when you compare your interests
with the type of work you enjoy.

IF YOU LIKE DATA

→ Data Analyst
→ Data Engineer
→ Data Scientist

IF YOU LIKE CLOUD / INFRASTRUCTURE

→ Cloud Engineer
→ DevOps Engineer
→ Cloud Support

IF YOU LIKE PROGRAMMING

→ Software Developer
→ Backend Developer
→ Full Stack Developer

IF YOU LIKE AI

→ ML Engineer
→ AI Engineer
→ Data Scientist

Don't choose a career only because it is trending.

Choose one path, learn the fundamentals, build projects and
evaluate your progress through practical work.
"""


    # -----------------------------------------------------
    # SALARY
    # -----------------------------------------------------

    elif (
        "salary" in message
        or "package" in message
        or "ctc" in message
        or "pay" in message
    ):

        return """
Salary depends on several factors:

• Role
• Location
• Company
• Technical skills
• Interview performance
• Internship experience
• Projects
• Communication
• Market conditions

Instead of choosing a career only based on salary, build skills
that create long-term opportunities.
"""


    # -----------------------------------------------------
    # DAILY PLAN
    # -----------------------------------------------------

    elif (
        "daily plan" in message
        or "study plan" in message
        or "daily routine" in message
        or "how many hours" in message
    ):

        return """
A simple daily career-learning routine can be:

1 hour — Learn a new concept
1 hour — Practice coding / SQL
1 hour — Work on a project
30 minutes — Interview preparation
30 minutes — Revision

Consistency is more important than studying for a very long time
for only a few days.
"""


    # -----------------------------------------------------
    # GENERAL HELP
    # -----------------------------------------------------

    elif (
        "help me" in message
        or "guide me" in message
        or "what can you do" in message
        or "what do you do" in message
    ):

        return """
I'm CareerPilot AI, your career planning assistant.

I can help you with:

CAREER
• Career selection
• Career planning
• Job roles

SKILLS
• Skill recommendations
• Skill gaps
• Learning priorities

TECHNOLOGY
• Python
• SQL
• AWS
• Cloud
• Data Engineering
• Data Analytics
• AI / ML

JOB PREPARATION
• Resume
• GitHub
• Projects
• Interviews
• Communication

Try asking something specific, such as:

"What should I learn to become a Data Engineer?"

"Give me an AWS Cloud roadmap."

"What projects should I build as an MCA student?"
"""


    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    else:

        return """
I'm CareerPilot AI, your career planning assistant.

I can help you with:

• Career planning
• Data Engineering
• Data Analytics
• AWS / Cloud
• AI / Machine Learning
• MCA career planning
• Skills and skill gaps
• Learning roadmaps
• Projects
• Resume improvement
• Interview preparation
• Certifications
• GitHub and portfolio

Try asking a specific question.

For example:

"What skills do I need for Data Engineering?"

"Give me an AWS roadmap."

"What projects should I build?"

"How can I prepare for a technical interview?"

"How can I improve my resume?"
"""


# =========================================================
# CHAT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    response = generate_career_response(request.message, request.user_id, request.topic)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO chat_messages
            (user_id, message, response)
            VALUES (?, ?, ?)
        """, (
            request.user_id,
            request.message,
            response
        ))

        connection.commit()

    finally:

        connection.close()

    return {
        "response": response,
        "user_id": request.user_id
    }


# =========================================================
# CHAT MESSAGE
# =========================================================

@app.post("/chat/message")
def chat_message(request: ChatRequest):

    response = generate_career_response(request.message, request.user_id, request.topic)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO chat_messages
            (user_id, message, response)
            VALUES (?, ?, ?)
        """, (
            request.user_id,
            request.message,
            response
        ))

        connection.commit()

    finally:

        connection.close()

    return {
        "response": response,
        "user_id": request.user_id
    }


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/chat/history/{user_id}")
def chat_history(user_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                user_id,
                message,
                response,
                created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id ASC
        """, (user_id,))

        messages = [dict(row) for row in cursor.fetchall()]

        return {
            "status": "success",
            "user_id": user_id,
            "messages": messages
        }

    finally:

        connection.close()


 # =========================================================
# RESUME ANALYZER
# =========================================================

@app.post("/resume/analyze")
async def analyze_resume(
    user_id: int,
    file: UploadFile = File(...)
):

    # -----------------------------------------------------
    # CHECK FILE TYPE
    # -----------------------------------------------------

    if file.content_type != "application/pdf":

        return {
            "success": False,
            "message": "Please upload a PDF resume."
        }

    try:

        # -------------------------------------------------
        # VERIFY USER ID
        # -------------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        connection.close()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # READ PDF
        # -------------------------------------------------

        file_bytes = await file.read()

        pdf = PdfReader(
            io.BytesIO(file_bytes)
        )

        # -------------------------------------------------
        # EXTRACT TEXT
        # -------------------------------------------------

        resume_text = ""

        for page in pdf.pages:

            text = page.extract_text()

            if text:

                resume_text += text + "\n"

        text_lower = resume_text.lower()

        # -------------------------------------------------
        # SKILLS
        # -------------------------------------------------

        skills = {

            "Python": "python",
            "SQL": "sql",
            "Java": "java",
            "C++": "c++",
            "JavaScript": "javascript",
            "HTML": "html",
            "CSS": "css",
            "Git": "git",
            "GitHub": "github",
            "AWS": "aws",
            "Azure": "azure",
            "Docker": "docker",
            "Linux": "linux",
            "Power BI": "power bi",
            "Tableau": "tableau",
            "Pandas": "pandas",
            "NumPy": "numpy",
            "Machine Learning": "machine learning",
            "Data Analysis": "data analysis",
            "Data Engineering": "data engineering",
            "Spark": "spark",
            "Airflow": "airflow",
            "Terraform": "terraform"
        }

        detected_skills = []

        for skill_name, keyword in skills.items():

            if keyword in text_lower:

                detected_skills.append(
                    skill_name
                )

        # -------------------------------------------------
        # SECTIONS
        # -------------------------------------------------

        sections = {

            "Education": [
                "education",
                "degree",
                "bachelor",
                "master",
                "mca",
                "bca",
                "b.tech",
                "college",
                "university"
            ],

            "Experience": [
                "experience",
                "work experience",
                "internship",
                "employment"
            ],

            "Projects": [
                "projects",
                "project"
            ],

            "Skills": [
                "skills",
                "technical skills",
                "technologies"
            ],

            "Certifications": [
                "certification",
                "certifications",
                "certificate"
            ],

            "Contact": [
                "@",
                "linkedin",
                "github",
                "phone"
            ]
        }

        section_results = {}

        for section, keywords in sections.items():

            found = False

            for keyword in keywords:

                if keyword in text_lower:

                    found = True
                    break

            section_results[section] = found

        # -------------------------------------------------
        # SCORE
        # -------------------------------------------------

        score = 0

        if len(detected_skills) >= 8:

            score += 25

        elif len(detected_skills) >= 5:

            score += 20

        elif len(detected_skills) >= 3:

            score += 15

        elif len(detected_skills) >= 1:

            score += 10

        if section_results["Education"]:

            score += 15

        if section_results["Projects"]:

            score += 20

        if section_results["Experience"]:

            score += 15

        if section_results["Certifications"]:

            score += 10

        if section_results["Contact"]:

            score += 10

        score = min(score, 100)

        # -------------------------------------------------
        # SUGGESTIONS
        # -------------------------------------------------

        suggestions = []

        if not section_results["Projects"]:

            suggestions.append(
                "Add 2–3 strong technical projects."
            )

        if not section_results["Experience"]:

            suggestions.append(
                "Add internship, freelance, or practical experience if available."
            )

        if not section_results["Certifications"]:

            suggestions.append(
                "Add relevant technical certifications."
            )

        if len(detected_skills) < 5:

            suggestions.append(
                "Add more job-relevant technical skills."
            )

        if not section_results["Contact"]:

            suggestions.append(
                "Add professional LinkedIn and GitHub profiles."
            )

        if not suggestions:

            suggestions.append(
                "Your resume has a strong structure. Focus on measurable achievements."
            )

        # -------------------------------------------------
        # SAVE RESUME TO DATABASE
        # -------------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        resume_id = None

        cursor.execute(
            """
            INSERT INTO resumes
            (
                user_id,
                filename,
                resume_text,
                resume_score
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                file.filename,
                resume_text,
                score
            )
        )

        resume_id = cursor.lastrowid

        # -------------------------------------------------
        # SAVE DETECTED SKILLS
        # -------------------------------------------------

        for skill_name in detected_skills:

            cursor.execute(
                """
                SELECT id
                FROM skills
                WHERE LOWER(name) = LOWER(?)
                """,
                (skill_name,)
            )

            skill = cursor.fetchone()

            if skill:

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO resume_skills
                    (
                        resume_id,
                        skill_name,
                        skill_score
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        resume_id,
                        skill_name,
                        100
                    )
                )

        connection.commit()
        connection.close()

        # -------------------------------------------------
        # AI FEEDBACK (Gemini) - appended to existing suggestions
        # -------------------------------------------------

        try:
            suggestions.extend(ai_resume_feedback(resume_text))
        except Exception:
            pass

        # -------------------------------------------------
        # RETURN RESULT
        # -------------------------------------------------

        return {

            "success": True,

            "resume_id": resume_id,

            "filename": file.filename,

            "pages": len(pdf.pages),

            "score": score,

            "skills": detected_skills,

            "sections": section_results,

            "suggestions": suggestions,

            "text_length": len(resume_text)
        }

    except HTTPException:

        raise

    except Exception as e:

        return {

            "success": False,

            "message": f"Could not analyze resume: {str(e)}"
        }
# =========================================================
# ATS RESUME TEMPLATE
# =========================================================

@app.post("/resume/template")
def save_resume_template(request: ResumeTemplateRequest):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # VERIFY USER
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (request.user_id,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # CHECK EXISTING TEMPLATE
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM resume_templates
            WHERE user_id = ?
        """, (request.user_id,))

        existing = cursor.fetchone()

        if existing:

            # ---------------------------------------------
            # UPDATE EXISTING TEMPLATE
            # ---------------------------------------------

            cursor.execute("""
                UPDATE resume_templates
                SET
                    full_name = ?,
                    professional_title = ?,
                    email = ?,
                    phone = ?,
                    location = ?,
                    linkedin = ?,
                    github = ?,
                    summary = ?,
                    education = ?,
                    skills = ?,
                    work_experience = ?,
                    internships = ?,
                    projects = ?,
                    certifications = ?,
                    is_fresher = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                request.full_name,
                request.professional_title,
                request.email,
                request.phone,
                request.location,
                request.linkedin,
                request.github,
                request.summary,
                request.education,
                request.skills,
                request.work_experience,
                request.internships,
                request.projects,
                request.certifications,
                1 if request.is_fresher else 0,
                request.user_id
            ))

            template_id = existing["id"]

        else:

            # ---------------------------------------------
            # CREATE NEW TEMPLATE
            # ---------------------------------------------

            cursor.execute("""
                INSERT INTO resume_templates
                (
                    user_id,
                    full_name,
                    professional_title,
                    email,
                    phone,
                    location,
                    linkedin,
                    github,
                    summary,
                    education,
                    skills,
                    work_experience,
                    internships,
                    projects,
                    certifications,
                    is_fresher
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.user_id,
                request.full_name,
                request.professional_title,
                request.email,
                request.phone,
                request.location,
                request.linkedin,
                request.github,
                request.summary,
                request.education,
                request.skills,
                request.work_experience,
                request.internships,
                request.projects,
                request.certifications,
                1 if request.is_fresher else 0
            ))

            template_id = cursor.lastrowid

        connection.commit()

        return {
            "success": True,
            "message": "Resume template saved successfully.",
            "template_id": template_id
        }

    finally:

        connection.close()

# =========================================================
# GET ATS RESUME TEMPLATE
# =========================================================

@app.get("/resume/template/{user_id}")
def get_resume_template(user_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                user_id,
                full_name,
                professional_title,
                email,
                phone,
                location,
                linkedin,
                github,
                summary,
                education,
                skills,
                work_experience,
                internships,
                projects,
                certifications,
                is_fresher,
                created_at,
                updated_at
            FROM resume_templates
            WHERE user_id = ?
        """, (user_id,))

        template = cursor.fetchone()

        if not template:

            return {
                "success": True,
                "template": None
            }

        return {
            "success": True,
            "template": dict(template)
        }

    finally:

        connection.close()

 

 # =========================================================
# USER DASHBOARD
# =========================================================

@app.get("/dashboard/{user_id}")
def get_dashboard(user_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # USER INFORMATION
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                role
            FROM users
            WHERE id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # PROFILE
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                education,
                experience,
                interests,
                target_role,
                created_at,
                updated_at
            FROM profiles
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,))

        profile = cursor.fetchone()

        # -------------------------------------------------
        # LATEST RESUME
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                filename,
                resume_score,
                uploaded_at
            FROM resumes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))

        resume = cursor.fetchone()

        resume_skills = []

        if resume:

            cursor.execute("""
                SELECT
                    id,
                    skill_name,
                    skill_score
                FROM resume_skills
                WHERE resume_id = ?
                ORDER BY skill_score DESC, skill_name ASC
            """, (resume["id"],))

            resume_skills = [
                dict(row)
                for row in cursor.fetchall()
            ]

        # -------------------------------------------------
        # SKILL GAP COUNT
        # -------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM skill_gaps
            WHERE user_id = ?
        """, (user_id,))

        skill_gap_count = cursor.fetchone()["total"] or 0

        # -------------------------------------------------
        # LATEST SKILL GAP
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                sg.id,
                sg.role_id,
                r.name AS role_name,
                sg.match_score,
                sg.skills_have,
                sg.skills_missing,
                sg.analyzed_at
            FROM skill_gaps sg
            LEFT JOIN job_roles r
                ON sg.role_id = r.id
            WHERE sg.user_id = ?
            ORDER BY sg.id DESC
            LIMIT 1
        """, (user_id,))

        latest_skill_gap = cursor.fetchone()

        latest_skill_gap_data = (
            dict(latest_skill_gap)
            if latest_skill_gap
            else None
        )

        # -------------------------------------------------
        # JOB MATCH COUNT
        # -------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM job_matches
            WHERE user_id = ?
        """, (user_id,))

        job_match_count = cursor.fetchone()["total"] or 0

        # -------------------------------------------------
        # JOB MATCHES
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                jm.id,
                jm.job_id,
                j.title,
                j.company,
                j.location,
                j.job_type,
                j.experience_level,
                j.source_url,
                jm.match_score,
                jm.matched_skills,
                jm.missing_skills,
                jm.created_at
            FROM job_matches jm
            LEFT JOIN jobs j
                ON jm.job_id = j.id
            WHERE jm.user_id = ?
            ORDER BY jm.match_score DESC, jm.id DESC
            LIMIT 10
        """, (user_id,))

        job_matches = [
            dict(row)
            for row in cursor.fetchall()
        ]

        # -------------------------------------------------
        # LATEST ROADMAP
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                rm.id,
                rm.role_id,
                r.name AS role_name,
                rm.roadmap_data,
                rm.created_at
            FROM roadmaps rm
            LEFT JOIN job_roles r
                ON rm.role_id = r.id
            WHERE rm.user_id = ?
            ORDER BY rm.id DESC
            LIMIT 1
        """, (user_id,))

        roadmap = cursor.fetchone()

        roadmap_data = (
            dict(roadmap)
            if roadmap
            else None
        )

        # -------------------------------------------------
        # LATEST CAREER REPORT
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                target_role,
                readiness_score,
                report_data,
                created_at
            FROM career_reports
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))

        career_report = cursor.fetchone()

        career_report_data = (
            dict(career_report)
            if career_report
            else None
        )

        # -------------------------------------------------
        # DASHBOARD RESPONSE
        # -------------------------------------------------

        return {
            "status": "success",

            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            },

            "profile": (
                dict(profile)
                if profile
                else None
            ),

            "resume": {
                "uploaded": resume is not None,
                "score": (
                    resume["resume_score"] or 0
                    if resume
                    else 0
                ),
                "filename": (
                    resume["filename"]
                    if resume
                    else None
                ),
                "uploaded_at": (
                    resume["uploaded_at"]
                    if resume
                    else None
                )
            },

            "skills": {
                "count": len(resume_skills),
                "list": resume_skills
            },

            "skill_gap": {
                "count": skill_gap_count,
                "latest": latest_skill_gap_data
            },

            "jobs": {
                "matches": job_match_count,
                "list": job_matches
            },

            "roadmap": roadmap_data,

            "career_report": career_report_data
        }

    finally:

        connection.close()


# =========================================================
# SKILL GAP ANALYZER
# =========================================================

class SkillGapRequest(BaseModel):
    user_id: int
    role_name: str


# ---------------------------------------------------------
# GET AVAILABLE ROLES FOR SKILL GAP
# ---------------------------------------------------------

@app.get("/skill-gap/roles")
def get_skill_gap_roles():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                description
            FROM job_roles
            ORDER BY name
        """)

        roles = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "roles": roles
        }

    finally:

        connection.close()


# ---------------------------------------------------------
# GET REQUIRED SKILLS FOR A ROLE
# ---------------------------------------------------------

@app.get("/skill-gap/roles/{role_id}/skills")
def get_skill_gap_role_skills(role_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                r.id,
                r.name,
                r.description
            FROM job_roles r
            WHERE r.id = ?
        """, (role_id,))

        role = cursor.fetchone()

        if not role:

            raise HTTPException(
                status_code=404,
                detail="Job role not found."
            )

        cursor.execute("""
            SELECT
                s.id,
                s.name,
                s.category,
                rs.importance
            FROM role_skills rs
            JOIN skills s
                ON rs.skill_id = s.id
            WHERE rs.role_id = ?
            ORDER BY rs.importance DESC, s.name ASC
        """, (role_id,))

        skills = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "role": {
                "id": role["id"],
                "name": role["name"],
                "description": role["description"]
            },
            "skills": skills
        }

    finally:

        connection.close()


# ---------------------------------------------------------
# ANALYZE SKILL GAP
# ---------------------------------------------------------

@app.post("/skill-gap/analyze")
def analyze_skill_gap(request: SkillGapRequest):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # VERIFY USER
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (request.user_id,))

        user = cursor.fetchone()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # FIND ROLE
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                name,
                description
            FROM job_roles
            WHERE name = ?
        """, (request.role_name,))

        role = cursor.fetchone()

        if not role:

            raise HTTPException(
                status_code=404,
                detail="Job role not found."
            )

        # -------------------------------------------------
        # GET LATEST RESUME
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM resumes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (request.user_id,))

        resume = cursor.fetchone()

        if not resume:

            raise HTTPException(
                status_code=400,
                detail="Please analyze your resume first."
            )

        # -------------------------------------------------
        # GET RESUME SKILLS
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                skill_name,
                skill_score
            FROM resume_skills
            WHERE resume_id = ?
            ORDER BY skill_score DESC, skill_name ASC
        """, (resume["id"],))

        resume_skill_rows = cursor.fetchall()

        current_skills = [
            row["skill_name"]
            for row in resume_skill_rows
        ]

        # -------------------------------------------------
        # GET REQUIRED ROLE SKILLS
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                s.id,
                s.name,
                s.category,
                rs.importance
            FROM role_skills rs
            JOIN skills s
                ON rs.skill_id = s.id
            WHERE rs.role_id = ?
            ORDER BY rs.importance DESC, s.name ASC
        """, (role["id"],))

        required_rows = cursor.fetchall()

        if not required_rows:

            raise HTTPException(
                status_code=400,
                detail="No required skills are configured for this role."
            )

        # -------------------------------------------------
        # COMPARE SKILLS
        # -------------------------------------------------

        current_normalized = {
            str(skill).strip().lower()
            for skill in current_skills
        }

        matched_skills = []
        missing_skills = []
        required_skills = []

        for row in required_rows:

            skill_name = row["name"]
            importance = row["importance"] or 0

            required_skills.append({
                "id": row["id"],
                "name": skill_name,
                "category": row["category"],
                "importance": importance
            })

            if skill_name.strip().lower() in current_normalized:

                matched_skills.append({
                    "id": row["id"],
                    "name": skill_name,
                    "category": row["category"],
                    "importance": importance
                })

            else:

                missing_skills.append({
                    "id": row["id"],
                    "name": skill_name,
                    "category": row["category"],
                    "importance": importance
                })

        # -------------------------------------------------
        # MATCH SCORE
        # -------------------------------------------------

        total_required = len(required_skills)

        matched_count = len(matched_skills)

        match_score = (
            round((matched_count / total_required) * 100)
            if total_required
            else 0
        )

        # -------------------------------------------------
        # SAVE RESULT
        # -------------------------------------------------

        import json

        cursor.execute("""
            INSERT INTO skill_gaps
            (
                user_id,
                role_id,
                match_score,
                skills_have,
                skills_missing
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            request.user_id,
            role["id"],
            match_score,
            json.dumps([
                item["name"]
                for item in matched_skills
            ]),
            json.dumps([
                item["name"]
                for item in missing_skills
            ])
        ))

        skill_gap_id = cursor.lastrowid

        connection.commit()

        # AI advice (Gemini) - extra field, does not affect saved data
        try:
            ai_advice = ai_skill_gap_advice(
                role["name"],
                current_skills,
                [m["name"] for m in missing_skills]
            )
        except Exception as ai_exc:
            ai_advice = []
            ai_service.LAST_ERROR = str(ai_exc)

        if ai_advice:
            ai_error = ""
        elif not missing_skills:
            ai_error = "No missing skills for this role, so no AI tips needed."
        else:
            ai_error = ai_service.LAST_ERROR or "AI tips unavailable."

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return {
            "success": True,

            "skill_gap_id": skill_gap_id,

            "role": {
                "id": role["id"],
                "name": role["name"],
                "description": role["description"]
            },

            "current_skills": current_skills,

            "required_skills": required_skills,

            "matched_skills": matched_skills,

            "missing_skills": missing_skills,

            "match_score": match_score,

            "skills_have_count": len(matched_skills),

            "skills_missing_count": len(missing_skills),

            "total_required": total_required,
            "ai_advice": ai_advice,
            "ai_error": ai_error
        }

    except HTTPException:

        raise

    except Exception as e:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Skill gap analysis failed: {str(e)}"
        )

    finally:

        connection.close()


# ---------------------------------------------------------
# LATEST SKILL GAP RESULT
# ---------------------------------------------------------

@app.get("/skill-gap/latest/{user_id}")
def get_latest_skill_gap(user_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                sg.id,
                sg.role_id,
                r.name AS role_name,
                sg.match_score,
                sg.skills_have,
                sg.skills_missing,
                sg.analyzed_at
            FROM skill_gaps sg
            JOIN job_roles r
                ON sg.role_id = r.id
            WHERE sg.user_id = ?
            ORDER BY sg.id DESC
            LIMIT 1
        """, (user_id,))

        result = cursor.fetchone()

        if not result:

            return {
                "success": True,
                "result": None
            }

        import json

        try:

            skills_have = json.loads(
                result["skills_have"] or "[]"
            )

        except Exception:

            skills_have = []

        try:

            skills_missing = json.loads(
                result["skills_missing"] or "[]"
            )

        except Exception:

            skills_missing = []

        return {
            "success": True,

            "result": {
                "id": result["id"],
                "role_id": result["role_id"],
                "role_name": result["role_name"],
                "match_score": result["match_score"],
                "skills_have": skills_have,
                "skills_missing": skills_missing,
                "analyzed_at": result["analyzed_at"]
            }
        }

    finally:

        connection.close()
# =========================================================
# CAREER ROADMAP
# =========================================================

@app.post("/roadmap/generate")
def generate_roadmap(request: RoadmapRequest):
    import json

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Verify user
        cursor.execute(
            "SELECT id FROM users WHERE id = ?",
            (request.user_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Get latest skill gap analysis
        cursor.execute("""
            SELECT
                sg.id,
                sg.role_id,
                r.name AS role_name,
                r.description AS role_description,
                sg.match_score,
                sg.skills_have,
                sg.skills_missing,
                sg.analyzed_at
            FROM skill_gaps sg
            JOIN job_roles r
                ON sg.role_id = r.id
            WHERE sg.user_id = ?
            ORDER BY sg.id DESC
            LIMIT 1
        """, (request.user_id,))

        skill_gap = cursor.fetchone()

        if not skill_gap:
            raise HTTPException(
                status_code=400,
                detail="Please complete Skill Gap Analysis first."
            )

        # Read skills the user already has
        try:
            skills_have = json.loads(
                skill_gap["skills_have"] or "[]"
            )
        except Exception:
            skills_have = []

        # Read missing skills
        try:
            skills_missing = json.loads(
                skill_gap["skills_missing"] or "[]"
            )
        except Exception:
            skills_missing = []

        # Get latest resume
        cursor.execute("""
            SELECT
                id,
                filename,
                resume_score
            FROM resumes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (request.user_id,))

        resume = cursor.fetchone()

        # Get required skills for selected role
        cursor.execute("""
            SELECT
                s.id,
                s.name,
                s.category,
                rs.importance
            FROM role_skills rs
            JOIN skills s
                ON rs.skill_id = s.id
            WHERE rs.role_id = ?
            ORDER BY rs.importance DESC, s.name ASC
        """, (skill_gap["role_id"],))

        required_rows = cursor.fetchall()

        required_skills = [
            dict(row)
            for row in required_rows
        ]

        # -------------------------------------------------
        # Stage 1
        # -------------------------------------------------

        stage1 = {
            "number": 1,
            "title": "Strengthen Your Current Skills",
            "description": (
                "Strengthen the skills you already have "
                "and improve practical confidence."
            ),
            "skills": skills_have[:]
        }

        # -------------------------------------------------
        # Stage 2
        # -------------------------------------------------

        stage2 = {
            "number": 2,
            "title": "Close Your Skill Gaps",
            "description": (
                "Focus first on the missing skills required "
                "for your selected role."
            ),
            "skills": skills_missing[:]
        }

        # -------------------------------------------------
        # Stage 3
        # -------------------------------------------------

        project_skills = (
            skills_missing[:3]
            if skills_missing
            else skills_have[:3]
        )

        stage3 = {
            "number": 3,
            "title": "Build Practical Projects",
            "description": (
                f"Build practical projects for "
                f"{skill_gap['role_name']} using your current "
                "and newly learned skills."
            ),
            "skills": project_skills
        }

        # -------------------------------------------------
        # Stage 4
        # -------------------------------------------------

        stage4 = {
            "number": 4,
            "title": "Prepare for Interviews",
            "description": (
                f"Prepare for technical and HR interviews "
                f"for {skill_gap['role_name']}."
            ),
            "skills": skills_have[:]
        }

        # -------------------------------------------------
        # Stage 5
        # -------------------------------------------------

        stage5 = {
            "number": 5,
            "title": "Become Job Ready",
            "description": (
                "Finalize your resume, GitHub, LinkedIn, "
                "portfolio and job applications."
            ),
            "skills": required_skills[:]
        }

        # -------------------------------------------------
        # Complete roadmap
        # -------------------------------------------------

        roadmap = {
            "role": {
                "id": skill_gap["role_id"],
                "name": skill_gap["role_name"],
                "description": skill_gap["role_description"]
            },

            "match_score": skill_gap["match_score"],

            "resume_score": (
                resume["resume_score"]
                if resume
                else 0
            ),

            "resume_filename": (
                resume["filename"]
                if resume
                else None
            ),

            "skills_have": skills_have,

            "skills_missing": skills_missing,

            "required_skills": required_skills,

            "stages": [
                stage1,
                stage2,
                stage3,
                stage4,
                stage5
            ]
        }

        # Save roadmap in SQLite
        cursor.execute("""
            INSERT INTO roadmaps
            (
                user_id,
                role_id,
                roadmap_data
            )
            VALUES (?, ?, ?)
        """, (
            request.user_id,
            skill_gap["role_id"],
            json.dumps(roadmap)
        ))

        roadmap_id = cursor.lastrowid

        connection.commit()

        return {
            "success": True,
            "roadmap_id": roadmap_id,
            "roadmap": roadmap
        }

    except HTTPException:
        raise

    except Exception as e:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Roadmap generation failed: {str(e)}"
        )

    finally:
        connection.close()


# =========================================================
# GET LATEST ROADMAP
# =========================================================

@app.get("/roadmap/latest/{user_id}")
def get_latest_roadmap(user_id: int):
    import json

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                rm.id,
                rm.user_id,
                rm.role_id,
                r.name AS role_name,
                rm.roadmap_data,
                rm.created_at
            FROM roadmaps rm
            LEFT JOIN job_roles r
                ON rm.role_id = r.id
            WHERE rm.user_id = ?
            ORDER BY rm.id DESC
            LIMIT 1
        """, (user_id,))

        roadmap = cursor.fetchone()

        if not roadmap:
            return {
                "success": True,
                "roadmap": None
            }

        try:
            roadmap_data = json.loads(
                roadmap["roadmap_data"] or "{}"
            )
        except Exception:
            roadmap_data = {}

        return {
            "success": True,
            "roadmap": {
                "id": roadmap["id"],
                "user_id": roadmap["user_id"],
                "role_id": roadmap["role_id"],
                "role_name": roadmap["role_name"],
                "created_at": roadmap["created_at"],
                "data": roadmap_data
            }
        }

    finally:
        connection.close()

# =========================================================
# ADMIN DASHBOARD — REAL DATABASE DATA
# Add this section at the very bottom of backend/main.py
# =========================================================

@app.get("/admin/dashboard/summary")
def admin_dashboard_summary(
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        def count_rows(table_name):
            # Only call this helper with fixed table names below.
            cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
            return cursor.fetchone()["total"]

        summary = {
            "users": count_rows("users"),
            "career_roles": count_rows("job_roles"),
            "skills": count_rows("skills"),
            "resumes": count_rows("resumes"),
            "chat_messages": count_rows("chat_messages"),
            "skill_gap_analyses": count_rows("skill_gaps"),
            "roadmaps": count_rows("roadmaps"),
        }

        # Get recent activity from tables that actually contain records.
        activity = []

        activity_queries = [
            (
                "resumes",
                """
                SELECT u.name AS user_name, r.filename AS description,
                       r.uploaded_at AS activity_date
                FROM resumes r
                LEFT JOIN users u ON u.id = r.user_id
                ORDER BY r.uploaded_at DESC LIMIT 5
                """,
                "Resume uploaded"
            ),
            (
                "chat_messages",
                """
                SELECT u.name AS user_name, NULL AS description,
                       c.created_at AS activity_date
                FROM chat_messages c
                LEFT JOIN users u ON u.id = c.user_id
                ORDER BY c.created_at DESC LIMIT 5
                """,
                "Career Coach conversation"
            ),
            (
                "skill_gaps",
                """
                SELECT u.name AS user_name, jr.name AS description,
                       sg.analyzed_at AS activity_date
                FROM skill_gaps sg
                LEFT JOIN users u ON u.id = sg.user_id
                LEFT JOIN job_roles jr ON jr.id = sg.role_id
                ORDER BY sg.analyzed_at DESC LIMIT 5
                """,
                "Skill Gap analysis"
            ),
            (
                "roadmaps",
                """
                SELECT u.name AS user_name, jr.name AS description,
                       rm.created_at AS activity_date
                FROM roadmaps rm
                LEFT JOIN users u ON u.id = rm.user_id
                LEFT JOIN job_roles jr ON jr.id = rm.role_id
                ORDER BY rm.created_at DESC LIMIT 5
                """,
                "Career Roadmap created"
            ),
        ]

        for table_name, query, activity_type in activity_queries:
            if count_rows(table_name) > 0:
                cursor.execute(query)
                for row in cursor.fetchall():
                    activity.append({
                        "type": activity_type,
                        "user_name": row["user_name"] or "User",
                        "description": row["description"] or "",
                        "date": row["activity_date"] or ""
                    })

        activity.sort(
            key=lambda item: item["date"],
            reverse=True
        )

        summary["recent_activity"] = activity[:10]

        return {
            "status": "success",
            "summary": summary
        }

    finally:
        connection.close()


@app.get("/admin/dashboard/users")
def admin_dashboard_users(
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                u.id,
                u.name,
                u.email,
                COALESCE(u.role, 'user') AS role,
                u.created_at,
                p.target_role,
                p.education
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            ORDER BY u.id DESC
        """)

        users = [dict(row) for row in cursor.fetchall()]

        return {
            "status": "success",
            "total": len(users),
            "users": users
        }

    finally:
        connection.close()


@app.get("/admin/dashboard/reports")
def admin_dashboard_reports(
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        def count_rows(table_name):
            cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
            return cursor.fetchone()["total"]

        # Only include populated feature tables.
        report_counts = {
            "Registered Users": count_rows("users"),
            "Career Roles": count_rows("job_roles"),
            "Available Skills": count_rows("skills"),
            "Saved Resumes": count_rows("resumes"),
            "Career Coach Messages": count_rows("chat_messages"),
            "Skill Gap Analyses": count_rows("skill_gaps"),
            "Career Roadmaps": count_rows("roadmaps"),
        }

        # Empty tables and zero-count metrics are intentionally omitted.
        populated_reports = {
            label: total
            for label, total in report_counts.items()
            if total > 0
        }

        return {
            "status": "success",
            "reports": populated_reports
        }

    finally:
        connection.close()

# =========================================================
# ADMIN — USER VIEW, EDIT AND DELETE
# =========================================================

from pydantic import EmailStr


class AdminUserUpdateRequest(BaseModel):
    name: str
    email: str
    education: str = ""
    experience: str = ""
    interests: str = ""
    target_role: str = ""
    institution: str = ""
    study_year: str = ""
    skills: str = ""


@app.get("/admin/dashboard/users/{user_id}")
def admin_view_user(
    user_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                u.id,
                u.name,
                u.email,
                u.role,
                u.created_at,
                p.education,
                p.experience,
                p.interests,
                p.target_role,
                p.institution,
                p.study_year,
                p.skills
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Never return password_hash.
        return {
            "status": "success",
            "user": dict(user)
        }

    finally:
        connection.close()

# =========================================================
# ADMIN RESUME MANAGEMENT
# Add near the existing admin dashboard routes
# =========================================================

@app.get("/admin/dashboard/resumes")
def admin_get_resumes(
    x_admin_key: str = Header(default="")
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                r.id,
                r.user_id,
                r.filename,
                r.resume_score,
                r.uploaded_at,
                u.name AS user_name,
                u.email AS user_email
            FROM resumes r
            JOIN users u ON u.id = r.user_id
            ORDER BY r.uploaded_at DESC, r.id DESC
        """).fetchall()

        resumes = []

        for row in rows:
            skills = connection.execute("""
                SELECT skill_name, skill_score
                FROM resume_skills
                WHERE resume_id = ?
                ORDER BY skill_name
            """, (row["id"],)).fetchall()

            resumes.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "user_email": row["user_email"],
                "filename": row["filename"] or "",
                "resume_score": row["resume_score"] or 0,
                "uploaded_at": row["uploaded_at"] or "",
                "skills": [
                    {
                        "name": skill["skill_name"],
                        "score": skill["skill_score"] or 0
                    }
                    for skill in skills
                ]
            })

        return {
            "success": True,
            "total": len(resumes),
            "resumes": resumes
        }

    finally:
        connection.close()


@app.get("/admin/dashboard/resumes/{resume_id}")
def admin_get_resume_details(
    resume_id: int,
    x_admin_key: str = Header(default="")
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT
                r.id,
                r.user_id,
                r.filename,
                r.resume_text,
                r.resume_score,
                r.uploaded_at,
                u.name AS user_name,
                u.email AS user_email
            FROM resumes r
            JOIN users u ON u.id = r.user_id
            WHERE r.id = ?
        """, (resume_id,)).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Resume not found"
            )

        skills = connection.execute("""
            SELECT skill_name, skill_score
            FROM resume_skills
            WHERE resume_id = ?
            ORDER BY skill_name
        """, (resume_id,)).fetchall()

        return {
            "success": True,
            "resume": {
                "id": row["id"],
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "user_email": row["user_email"],
                "filename": row["filename"] or "",
                "resume_score": row["resume_score"] or 0,
                "uploaded_at": row["uploaded_at"] or "",
                "resume_text": row["resume_text"] or "",
                "skills": [
                    {
                        "name": skill["skill_name"],
                        "score": skill["skill_score"] or 0
                    }
                    for skill in skills
                ]
            }
        }

    finally:
        connection.close()


@app.delete("/admin/dashboard/resumes/{resume_id}")
def admin_delete_resume(
    resume_id: int,
    x_admin_key: str = Header(default="")
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM resumes WHERE id = ?",
            (resume_id,)
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Resume not found"
            )

        # Foreign-key cascade removes related resume_skills.
        connection.execute(
            "DELETE FROM resumes WHERE id = ?",
            (resume_id,)
        )
        connection.commit()

        return {
            "success": True,
            "message": "Resume record deleted successfully",
            "resume_id": resume_id
        }

    finally:
        connection.close()

@app.put("/admin/dashboard/users/{user_id}")
def admin_update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    name = request.name.strip()
    email = request.email.strip().lower()

    if not name or not email:
        raise HTTPException(
            status_code=400,
            detail="Name and email are required."
        )

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address."
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id, role FROM users WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Do not allow this endpoint to change admin accounts.
        # Admin privileges must be managed separately.
        if user["role"] == "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin accounts cannot be edited here."
            )

        cursor.execute("""
            UPDATE users
            SET name = ?, email = ?
            WHERE id = ?
        """, (name, email, user_id))

        cursor.execute("""
            INSERT INTO profiles (
                user_id, education, experience, interests,
                target_role, institution, study_year, skills,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                education = excluded.education,
                experience = excluded.experience,
                interests = excluded.interests,
                target_role = excluded.target_role,
                institution = excluded.institution,
                study_year = excluded.study_year,
                skills = excluded.skills,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            request.education.strip(),
            request.experience.strip(),
            request.interests.strip(),
            request.target_role.strip(),
            request.institution.strip(),
            request.study_year.strip(),
            request.skills.strip()
        ))

        connection.commit()

        return {
            "status": "success",
            "message": "User details updated successfully."
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()

        # Handle duplicate email without exposing database details.
        if "UNIQUE constraint failed: users.email" in str(error):
            raise HTTPException(
                status_code=409,
                detail="That email address is already registered."
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to update user details."
        )

    finally:
        connection.close()


@app.delete("/admin/dashboard/users/{user_id}")
def admin_delete_user(
    user_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id, name, role FROM users WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Prevent accidental deletion of an administrator.
        if user["role"] == "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin accounts cannot be deleted here."
            )

        # Foreign-key cascades remove related records where configured.
        cursor.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )

        connection.commit()

        return {
            "status": "success",
            "message": "User account deleted successfully.",
            "user_id": user_id
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to delete this user."
        )

    finally:
        connection.close()

# =========================================================
# ADMIN — AI CAREER COACH MANAGEMENT
# =========================================================

@app.get("/admin/dashboard/chat-messages")
def admin_get_chat_messages(
    x_admin_key: str | None = Header(default=None),
    search: str = ""
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        search_term = f"%{search.strip()}%"

        cursor.execute("""
            SELECT
                c.id,
                c.user_id,
                u.name AS user_name,
                u.email AS user_email,
                c.message,
                c.response,
                c.created_at
            FROM chat_messages c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE
                ? = ''
                OR u.name LIKE ?
                OR u.email LIKE ?
                OR c.message LIKE ?
                OR c.response LIKE ?
            ORDER BY c.id DESC
        """, (
            search.strip(),
            search_term,
            search_term,
            search_term,
            search_term
        ))

        messages = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "total": len(messages),
            "messages": messages
        }

    finally:
        connection.close()


@app.get("/admin/dashboard/chat-messages/{message_id}")
def admin_get_chat_message_details(
    message_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.user_id,
                u.name AS user_name,
                u.email AS user_email,
                c.message,
                c.response,
                c.created_at
            FROM chat_messages c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.id = ?
        """, (message_id,))

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Career Coach message not found."
            )

        return {
            "success": True,
            "message": dict(row)
        }

    finally:
        connection.close()

from pydantic import BaseModel

class AdminChatMessageUpdate(BaseModel):
    message: str
    response: str


@app.put("/admin/dashboard/chat-messages/{message_id}")
def admin_update_chat_message(
    message_id: int,
    payload: AdminChatMessageUpdate,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    message = payload.message.strip()
    response = payload.response.strip()

    if not message or not response:
        raise HTTPException(
            status_code=400,
            detail="Question and response cannot be empty."
        )

    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM chat_messages WHERE id = ?",
            (message_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Career Coach message not found."
            )

        cursor.execute(
            """
            UPDATE chat_messages
            SET message = ?, response = ?
            WHERE id = ?
            """,
            (message, response, message_id)
        )

        connection.commit()

        return {
            "success": True,
            "message": "Career Coach conversation updated successfully."
        }
    finally:
        connection.close()
# =========================================================
# ADMIN — SUGGESTED QUESTIONS MANAGEMENT
# =========================================================

class SuggestedQuestionCreate(BaseModel):
    question: str


class SuggestedQuestionUpdate(BaseModel):
    question: str
    is_active: int = 1


@app.get("/admin/dashboard/suggested-questions")
def admin_list_suggested_questions(
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, question, is_active, created_at
            FROM suggested_questions
            ORDER BY id DESC
        """)

        questions = [dict(row) for row in cursor.fetchall()]

        return {
            "success": True,
            "total": len(questions),
            "questions": questions
        }
    finally:
        connection.close()


@app.post("/admin/dashboard/suggested-questions")
def admin_create_suggested_question(
    payload: SuggestedQuestionCreate,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO suggested_questions (question)
            VALUES (?)
        """, (question,))
        connection.commit()

        return {
            "success": True,
            "id": cursor.lastrowid,
            "message": "Suggested question added successfully."
        }
    finally:
        connection.close()


@app.put("/admin/dashboard/suggested-questions/{question_id}")
def admin_update_suggested_question(
    question_id: int,
    payload: SuggestedQuestionUpdate,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if payload.is_active not in (0, 1):
        raise HTTPException(
            status_code=400,
            detail="is_active must be 0 or 1."
        )

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE suggested_questions
            SET question = ?, is_active = ?
            WHERE id = ?
        """, (question, payload.is_active, question_id))
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Suggested question not found."
            )

        return {
            "success": True,
            "message": "Suggested question updated successfully."
        }
    finally:
        connection.close()


@app.delete("/admin/dashboard/suggested-questions/{question_id}")
def admin_delete_suggested_question(
    question_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM suggested_questions
            WHERE id = ?
        """, (question_id,))
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Suggested question not found."
            )

        return {
            "success": True,
            "message": "Suggested question deleted successfully."
        }
    finally:
        connection.close()

@app.get("/suggested-questions")
def get_public_suggested_questions():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, question
            FROM suggested_questions
            WHERE is_active = 1
            ORDER BY id DESC
        """)

        questions = [
            dict(row) for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "questions": questions
        }

    finally:
        connection.close()

# =========================================================
# CAREER COACH — SHARED CONFIGURATION
# =========================================================

class CoachConfigurationRequest(BaseModel):
    coachName: str = "CareerPilot AI"
    personality: str = "Friendly and professional"
    responseLength: str = "Detailed"
    language: str = "English"
    systemPrompt: str = ""
    topics: str = ""
    welcomeMessage: str = "Hello! How can I help with your career?"
    beginnerMode: bool = True
    roadmapMode: bool = True
    followUpMode: bool = True


def initialize_coach_configuration():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS coach_configuration (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                configuration TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    finally:
        connection.close()


initialize_coach_configuration()


@app.get("/admin/dashboard/coach-configuration")
def admin_get_coach_configuration(
    x_admin_key: str | None = Header(default=None)
):
    import json

    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT configuration
            FROM coach_configuration
            WHERE id = 1
        """).fetchone()

        if row is None:
            config = CoachConfigurationRequest().model_dump()
        else:
            config = json.loads(row["configuration"])

        return {"success": True, "configuration": config}
    finally:
        connection.close()


@app.put("/admin/dashboard/coach-configuration")
def admin_save_coach_configuration(
    payload: CoachConfigurationRequest,
    x_admin_key: str | None = Header(default=None)
):
    import json

    verify_admin(x_admin_key)

    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO coach_configuration
                (id, configuration, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                configuration = excluded.configuration,
                updated_at = CURRENT_TIMESTAMP
        """, (
            json.dumps(payload.model_dump()),
        ))

        connection.commit()

        return {
            "success": True,
            "message": "Coach configuration saved to the database."
        }
    finally:
        connection.close()


@app.get("/coach/configuration")
def get_public_coach_configuration():
    import json

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT configuration
            FROM coach_configuration
            WHERE id = 1
        """).fetchone()

        if row is None:
            config = CoachConfigurationRequest().model_dump()
        else:
            config = json.loads(row["configuration"])

        return {
            "success": True,
            "configuration": config
        }
    finally:
        connection.close()
# =========================================================
# ADMIN — SKILL GAP ANALYSIS RECORDS
# =========================================================

@app.get("/admin/dashboard/skill-gaps")
def admin_skill_gap_analyses(
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                sg.id,
                sg.user_id,
                u.name AS user_name,
                u.email AS user_email,
                jr.name AS role_name,
                sg.match_score,
                sg.skills_have,
                sg.skills_missing,
                sg.analyzed_at
            FROM skill_gaps AS sg
            LEFT JOIN users AS u
                ON sg.user_id = u.id
            LEFT JOIN job_roles AS jr
                ON sg.role_id = jr.id
            ORDER BY sg.analyzed_at DESC, sg.id DESC
        """)

        analyses = [dict(row) for row in cursor.fetchall()]

        return {
            "status": "success",
            "count": len(analyses),
            "analyses": analyses
        }

    finally:
        connection.close()


# =========================================================
# JOB MATCHING - AI INSIGHT (Gemini)
# =========================================================

class JobInsightRequest(BaseModel):
    user_id: int
    skills: list[str] = []
    top_roles: list[dict] = []


@app.post("/jobs/ai-insight")
def jobs_ai_insight(request: JobInsightRequest):
    try:
        tips = ai_job_insight(request.skills, request.top_roles)
    except Exception:
        tips = []
    return {
        "success": True,
        "insight": tips
    }


# =========================================================
# ADMIN - AI STATUS (protected with admin key)
# =========================================================

@app.get("/admin/dashboard/ai-status")
def admin_ai_status(
    test: bool = False,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)

    key_found = bool((os.getenv("GEMINI_API_KEY") or "").strip())
    reply = None

    # Only calls Gemini when the admin presses "Test AI"
    if test:
        reply = ai_service._call_gemini(
            "Reply with one short friendly sentence.",
            [{"role": "user", "parts": [{"text": "Say hello to CareerPilot."}]}],
            max_tokens=100
        )

    return {
        "success": True,
        "key_found": key_found,
        "model": ai_service._WORKING_MODEL,
        "tested": test,
        "working": bool(reply) if test else None,
        "reply": reply,
        "error": ai_service.LAST_ERROR if test else ""
    }


# =========================================================
# ADMIN - ROADMAPS LIST
# =========================================================

@app.get("/admin/dashboard/roadmaps")
def admin_list_roadmaps(
    x_admin_key: str | None = Header(default=None)
):
    import json
    verify_admin(x_admin_key)

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT
                rm.id,
                rm.user_id,
                u.name AS user_name,
                u.email AS user_email,
                jr.name AS role_name,
                rm.roadmap_data,
                rm.created_at
            FROM roadmaps rm
            LEFT JOIN users u ON u.id = rm.user_id
            LEFT JOIN job_roles jr ON jr.id = rm.role_id
            ORDER BY rm.id DESC
        """).fetchall()

        roadmaps = []
        for row in rows:
            try:
                data = json.loads(row["roadmap_data"] or "{}")
            except Exception:
                data = {}

            stages = data.get("stages") or []
            roadmaps.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "user_name": row["user_name"] or "User",
                "user_email": row["user_email"] or "",
                "role_name": row["role_name"] or "",
                "match_score": data.get("match_score") or 0,
                "missing_count": len(data.get("skills_missing") or []),
                "stage_count": len(stages),
                "stages": [
                    {
                        "title": s.get("title", ""),
                        "description": s.get("description", "")
                    }
                    for s in stages if isinstance(s, dict)
                ],
                "created_at": row["created_at"] or ""
            })

        return {
            "status": "success",
            "count": len(roadmaps),
            "roadmaps": roadmaps
        }
    finally:
        connection.close()


# =========================================================
# ADMIN - DELETE RECORDS (chat messages, skill gaps, roadmaps)
# =========================================================

def _admin_delete_row(table: str, row_id: int, label: str):
    connection = get_connection()
    try:
        found = connection.execute(
            f"SELECT id FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()
        if found is None:
            raise HTTPException(status_code=404, detail=f"{label} not found.")
        connection.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        connection.commit()
        return {"success": True, "message": f"{label} deleted successfully."}
    finally:
        connection.close()


@app.delete("/admin/dashboard/chat-messages/{message_id}")
def admin_delete_chat_message(
    message_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)
    return _admin_delete_row("chat_messages", message_id, "Conversation")


@app.delete("/admin/dashboard/skill-gaps/{analysis_id}")
def admin_delete_skill_gap(
    analysis_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)
    return _admin_delete_row("skill_gaps", analysis_id, "Skill gap analysis")


@app.delete("/admin/dashboard/roadmaps/{roadmap_id}")
def admin_delete_roadmap(
    roadmap_id: int,
    x_admin_key: str | None = Header(default=None)
):
    verify_admin(x_admin_key)
    return _admin_delete_row("roadmaps", roadmap_id, "Roadmap")


   # =========================================================
   # SERVE FRONTEND (must stay at the very bottom)
   # =========================================================

from fastapi.staticfiles import StaticFiles
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
       "/",
       StaticFiles(directory=FRONTEND_DIR, html=True),
       name="frontend"
   )