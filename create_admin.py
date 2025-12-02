# create_admin.py
"""Script to create an admin user for the Arzaq platform"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.db.base import Base


def create_admin_user():
    """Create an admin user"""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@arzaq.kz").first()

        if existing_admin:
            print("❌ Admin user already exists!")
            print(f"Email: {existing_admin.email}")
            return

        # Create admin user
        admin = User(
            email="admin@arzaq.kz",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("✅ Admin user created successfully!")
        print(f"📧 Email: admin@arzaq.kz")
        print(f"🔑 Password: admin123")
        print(f"⚠️  Please change the password after first login!")

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    print("Creating admin user for Arzaq platform...")
    create_admin_user()
