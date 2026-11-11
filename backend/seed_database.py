from database import get_connection, initialize_database


# =========================================================
# CAREERPILOT AI - INITIAL DATABASE DATA
# =========================================================

initialize_database()

connection = get_connection()
cursor = connection.cursor()


# =========================================================
# SKILLS
# =========================================================

skills = [

    ("Python", "Programming"),
    ("SQL", "Database"),
    ("Java", "Programming"),
    ("JavaScript", "Web Development"),
    ("HTML", "Web Development"),
    ("CSS", "Web Development"),

    ("Excel", "Data"),
    ("Data Analysis", "Data"),
    ("Data Visualization", "Data"),
    ("Power BI", "Data"),
    ("Tableau", "Data"),
    ("Statistics", "Data"),

    ("Machine Learning", "AI"),
    ("Machine Learning Basics", "AI"),
    ("Deep Learning", "AI"),
    ("Pandas", "Python"),
    ("NumPy", "Python"),
    ("Scikit-learn", "AI"),

    ("Big Data", "Data Engineering"),
    ("Hadoop", "Data Engineering"),
    ("Spark", "Data Engineering"),

    ("Linux", "Cloud & DevOps"),
    ("AWS", "Cloud"),
    ("Azure", "Cloud"),
    ("Docker", "DevOps"),
    ("Kubernetes", "DevOps"),
    ("Terraform", "DevOps"),
    ("Git", "DevOps"),
    ("CI/CD", "DevOps"),

    ("Networking", "Cloud"),
    ("Cloud Security", "Cloud"),

    ("Data Cleaning", "Data"),
    ("Data Structures", "Programming"),
    ("Algorithms", "Programming"),
    ("REST API", "Backend"),
    ("Testing", "Software Development"),
    ("OOP", "Programming"),

    ("Problem Solving", "Professional"),
    ("Communication", "Professional"),
    ("Teamwork", "Professional"),
    ("Documentation", "Professional"),
    ("Presentation", "Professional"),
    ("Requirements Analysis", "Business")
]


# =========================================================
# JOB ROLES
# =========================================================

roles = [

    (
        "Data Analyst",
        "Analyze data, create reports and dashboards, and generate business insights."
    ),

    (
        "Cloud Engineer",
        "Design, deploy and maintain cloud infrastructure and services."
    ),

    (
        "Software Engineer",
        "Design, develop, test and maintain software applications."
    ),

    (
        "Data Scientist",
        "Use statistics, machine learning and data analysis to solve business problems."
    ),

    (
        "DevOps Engineer",
        "Automate software delivery, infrastructure and deployment processes."
    ),

    (
        "Business Analyst",
        "Analyze business requirements and translate them into technology solutions."
    )
]


# =========================================================
# ROLE → REQUIRED SKILLS
# =========================================================

role_skill_map = {

    "Data Analyst": [
        ("Python", 90),
        ("SQL", 95),
        ("Excel", 90),
        ("Data Analysis", 95),
        ("Data Visualization", 90),
        ("Power BI", 85),
        ("Tableau", 80),
        ("Statistics", 85),
        ("Pandas", 80),
        ("Data Cleaning", 85)
    ],

    "Cloud Engineer": [
        ("Linux", 90),
        ("AWS", 95),
        ("Azure", 75),
        ("Networking", 90),
        ("Docker", 85),
        ("Kubernetes", 80),
        ("Terraform", 80),
        ("Git", 85),
        ("Cloud Security", 80),
        ("Python", 65)
    ],

    "Software Engineer": [
        ("Python", 80),
        ("Java", 85),
        ("JavaScript", 80),
        ("Data Structures", 95),
        ("Algorithms", 95),
        ("OOP", 90),
        ("Git", 85),
        ("REST API", 80),
        ("Testing", 85),
        ("Problem Solving", 95)
    ],

    "Data Scientist": [
        ("Python", 95),
        ("SQL", 85),
        ("Statistics", 95),
        ("Machine Learning", 95),
        ("Machine Learning Basics", 90),
        ("Pandas", 90),
        ("NumPy", 90),
        ("Scikit-learn", 90),
        ("Data Visualization", 80),
        ("Data Cleaning", 85)
    ],

    "DevOps Engineer": [
        ("Linux", 95),
        ("Git", 90),
        ("Docker", 95),
        ("Kubernetes", 90),
        ("AWS", 85),
        ("Terraform", 90),
        ("CI/CD", 95),
        ("Networking", 85),
        ("Python", 70),
        ("Cloud Security", 75)
    ],

    "Business Analyst": [
        ("Excel", 90),
        ("Data Analysis", 85),
        ("SQL", 75),
        ("Power BI", 80),
        ("Statistics", 70),
        ("Requirements Analysis", 95),
        ("Communication", 95),
        ("Presentation", 90),
        ("Documentation", 90),
        ("Problem Solving", 90)
    ]
}


# =========================================================
# INSERT SKILLS
# =========================================================

for name, category in skills:

    cursor.execute("""
        INSERT OR IGNORE INTO skills
        (name, category)
        VALUES (?, ?)
    """, (name, category))


# =========================================================
# INSERT JOB ROLES
# =========================================================

for name, description in roles:

    cursor.execute("""
        INSERT OR IGNORE INTO job_roles
        (name, description)
        VALUES (?, ?)
    """, (name, description))


# =========================================================
# CONNECT ROLES WITH REQUIRED SKILLS
# =========================================================

for role_name, required_skills in role_skill_map.items():

    cursor.execute("""
        SELECT id
        FROM job_roles
        WHERE name = ?
    """, (role_name,))

    role = cursor.fetchone()

    if not role:
        continue

    role_id = role["id"]

    for skill_name, importance in required_skills:

        cursor.execute("""
            SELECT id
            FROM skills
            WHERE name = ?
        """, (skill_name,))

        skill = cursor.fetchone()

        if not skill:
            continue

        skill_id = skill["id"]

        cursor.execute("""
            INSERT OR IGNORE INTO role_skills
            (role_id, skill_id, importance)
            VALUES (?, ?, ?)
        """, (
            role_id,
            skill_id,
            importance
        ))


# =========================================================
# SAVE
# =========================================================

connection.commit()


# =========================================================
# VERIFY
# =========================================================

cursor.execute("SELECT COUNT(*) AS count FROM skills")
skill_count = cursor.fetchone()["count"]

cursor.execute("SELECT COUNT(*) AS count FROM job_roles")
role_count = cursor.fetchone()["count"]

cursor.execute("SELECT COUNT(*) AS count FROM role_skills")
role_skill_count = cursor.fetchone()["count"]


connection.close()


print()
print("========================================")
print("CareerPilot AI Database Seeded")
print("========================================")
print(f"Skills added       : {skill_count}")
print(f"Job roles added    : {role_count}")
print(f"Role-skill links   : {role_skill_count}")
print("========================================")
print("Database is ready.")
print("========================================")