import sqlite3
import hashlib
import secrets
from pathlib import Path
from getpass import getpass


# =========================================================
# DATABASE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "careerpilot.db"


# =========================================================
# PASSWORD HASH
# =========================================================

def hash_password(password: str) -> str:

    iterations = 310000

    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )

    return (
        f"pbkdf2_sha256$"
        f"{iterations}$"
        f"{salt.hex()}$"
        f"{digest.hex()}"
    )


# =========================================================
# CREATE / UPDATE ADMIN
# =========================================================

print()
print("========================================")
print("CareerPilot AI - Create / Update Admin")
print("========================================")
print()


name = input("Admin name: ").strip()

email = input("Admin email: ").strip().lower()


password = getpass("Admin password: ")

confirm_password = getpass("Confirm password: ")


if not name:

    print("Admin name is required.")
    raise SystemExit


if not email:

    print("Admin email is required.")
    raise SystemExit


if not password:

    print("Password is required.")
    raise SystemExit


if password != confirm_password:

    print("Passwords do not match.")
    raise SystemExit


password_hash = hash_password(password)


# =========================================================
# DATABASE CONNECTION
# =========================================================

connection = sqlite3.connect(DATABASE_PATH)

cursor = connection.cursor()


# Make sure role column exists

columns = [
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(users)"
    ).fetchall()
]


if "role" not in columns:

    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
        """
    )


# =========================================================
# CHECK EXISTING USER
# =========================================================

cursor.execute(
    """
    SELECT id
    FROM users
    WHERE LOWER(email) = ?
    """,
    (email,)
)

existing_user = cursor.fetchone()


if existing_user:

    # IMPORTANT:
    # Update BOTH password and role

    cursor.execute(
        """
        UPDATE users
        SET
            name = ?,
            password_hash = ?,
            role = 'admin'
        WHERE id = ?
        """,
        (
            name,
            password_hash,
            existing_user[0]
        )
    )

    print()
    print("Existing user updated.")
    print("Password has been reset.")
    print("Role: admin")


else:

    cursor.execute(
        """
        INSERT INTO users
        (
            name,
            email,
            password_hash,
            role
        )
        VALUES (?, ?, ?, 'admin')
        """,
        (
            name,
            email,
            password_hash
        )
    )

    print()
    print("New admin created.")
    print("Role: admin")


connection.commit()

connection.close()


print()
print("========================================")
print("Admin account ready.")
print(f"Admin email: {email}")
print("Role: admin")
print("========================================")
print()