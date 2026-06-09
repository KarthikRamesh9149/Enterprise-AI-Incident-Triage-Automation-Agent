from app.db.session import SessionLocal, init_db
from app.services.seed import seed_demo_data

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
        print("Demo users, incidents, logs, runbooks, tools, and eval fixtures are loaded.")
    finally:
        db.close()
