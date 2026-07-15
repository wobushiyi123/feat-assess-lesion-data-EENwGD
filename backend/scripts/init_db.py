import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, SessionLocal
from app.models.database import User, Subject
from app.core.security import get_password_hash
from datetime import datetime, timedelta


def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("OK: Database tables created")


def create_demo_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin",
                role="admin"
            )
            db.add(admin)
            print("OK: Admin user created: admin / admin123")

        doctor = db.query(User).filter(User.username == "doctor").first()
        if not doctor:
            doctor = User(
                username="doctor",
                hashed_password=get_password_hash("doctor123"),
                full_name="Doctor",
                role="doctor"
            )
            db.add(doctor)
            print("OK: Doctor user created: doctor / doctor123")

        db.commit()

        demo_subjects = [
            {"subject_id": "S001", "name": "Subject A", "gender": "Male", "age": 56, "diagnosis": "Lung Cancer"},
            {"subject_id": "S002", "name": "Subject B", "gender": "Female", "age": 48, "diagnosis": "Breast Cancer"},
            {"subject_id": "S003", "name": "Subject C", "gender": "Male", "age": 62, "diagnosis": "Liver Cancer"},
        ]

        for data in demo_subjects:
            existing = db.query(Subject).filter(Subject.subject_id == data["subject_id"]).first()
            if not existing:
                subject = Subject(
                    **data,
                    baseline_date=datetime.now() - timedelta(days=30)
                )
                db.add(subject)
                print(f"OK: Subject created: {data['subject_id']}")

        db.commit()
        print("\nOK: Demo data created successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("RECIST Assessment System - Database Initialization")
    print("=" * 50)
    init_database()
    create_demo_data()
    print("\nInitialization complete!")
    print("Login accounts:")
    print("  Admin: admin / admin123")
    print("  Doctor: doctor / doctor123")