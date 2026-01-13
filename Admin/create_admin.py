from auth_utils import hash_password
from database import get_collection
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_admin():
    users_col = get_collection("users")

    admin_data = {
        "username": "admin",
        "email": "admin@gmail.com",
        "password": hash_password("AdminPass123!"),
        "role": "admin"
    }

    if users_col.find_one({"role": "admin"}):
        print("Admin user already exists.")
        return

    users_col.insert_one(admin_data)
    print("Admin user created successfully.")
    print(f"Email: {admin_data['email']}")
    print("Password: AdminPass123!")


if __name__ == "__main__":
    create_admin()

# run with: python create_admin.py