
import getpass
import sqlite3

from backend.main import hash_password

DB_PATH = "careerpilot.db"

email = input("Enter your admin email: ").strip().lower()
new_password = getpass.getpass("Enter your new admin password: ")
confirm_password = getpass.getpass("Confirm your new password: ")

if len(new_password) < 8:
    print("Password must be at least 8 characters.")
    raise SystemExit(1)

if new_password != confirm_password:
    print("Passwords do not match.")
    raise SystemExit(1)

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute(
    "SELECT id, role FROM users WHERE LOWER(email) = ?",
    (email,)
)
admin = cursor.fetchone()

if not admin or admin[1] != "admin":
    connection.close()
    print("No admin account found for that email.")
    raise SystemExit(1)

password_hash = hash_password(new_password)

cursor.execute(
    "UPDATE users SET password_hash = ? WHERE id = ?",
    (password_hash, admin[0])
)

connection.commit()
connection.close()

print("Admin password reset successfully.")
