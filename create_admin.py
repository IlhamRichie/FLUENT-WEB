import os
import sys
from getpass import getpass # Untuk input password yang lebih aman

# Tambahkan path ke root proyek agar bisa impor 'backend'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Impor create_app, tapi bcrypt akan diakses melalui instance app
from backend import create_app
from backend.database import get_users_collection # Fungsi untuk mendapatkan koleksi
from datetime import datetime, timezone

app = create_app() # Buat instance app untuk mendapatkan context dan akses ke ekstensi

def create_admin_user_script():
    with app.app_context(): # Aktifkan application context
        print("--- Create Admin User ---")
        email = input("Enter admin email: ").strip().lower()
        username = input("Enter admin username: ").strip()
        password = getpass("Enter admin password: ")
        confirm_password = getpass("Confirm admin password: ")

        if not all([email, username, password, confirm_password]):
            print("All fields are required.")
            return

        if password != confirm_password:
            print("Passwords do not match.")
            return
        
        if len(password) < 6:
            print("Password must be at least 6 characters long.")
            return

        users_coll = get_users_collection() # Dapatkan koleksi dalam context

        existing_user_by_email = users_coll.find_one({"email": email})
        existing_user_by_username = users_coll.find_one({"username": username})

        user_to_check = None
        if existing_user_by_email:
            user_to_check = existing_user_by_email
        elif existing_user_by_username:
            # Pastikan username tidak dipakai oleh email lain
            if existing_user_by_username.get("email") != email:
                 print(f"Username '{username}' is already taken by another user.")
                 return
            user_to_check = existing_user_by_username


        if user_to_check:
            if user_to_check.get("is_admin"):
                print(f"Admin user with email '{user_to_check['email']}' or username '{user_to_check['username']}' already exists.")
                choice = input("Do you want to update its password? (y/n): ").lower()
                if choice == 'y':
                    new_password = getpass("Enter new password for existing admin: ")
                    if len(new_password) < 6:
                        print("New password too short.")
                        return
                    # Akses bcrypt melalui app.bcrypt
                    hashed_new_password = app.bcrypt.generate_password_hash(new_password).decode('utf-8')
                    users_coll.update_one({"_id": user_to_check["_id"]}, {"$set": {"password": hashed_new_password}})
                    print(f"Password updated for admin '{user_to_check['username']}'.")
                return
            else:
                print(f"User with email '{user_to_check['email']}' or username '{user_to_check['username']}' already exists but is not an admin.")
                print("You can make this user an admin through the admin panel after they log in,")
                print("or delete the user and recreate as admin if they haven't used the account.")
                return

        # Akses bcrypt melalui app.bcrypt
        hashed_password = app.bcrypt.generate_password_hash(password).decode('utf-8')
        admin_data = {
            "email": email,
            "username": username,
            "password": hashed_password,
            "gender": "Not specified",
            "occupation": "Administrator",
            "is_active": True,
            "last_login": None,
            "created_at": datetime.now(timezone.utc),
            "is_admin": True,
            "auth_provider": "local"
        }
        try:
            users_coll.insert_one(admin_data)
            print(f"Admin user '{username}' ({email}) created successfully.")
        except Exception as e:
            print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin_user_script()