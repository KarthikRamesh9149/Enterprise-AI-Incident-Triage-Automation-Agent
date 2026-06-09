from app.db import models
from app.db.session import SessionLocal, init_db
from app.security.redaction import detect_prompt_injection, redact_sensitive_text

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        run = models.EvaluationRun(
            name="script deterministic safety eval",
            dataset_name="demo-data/evals",
            status="completed",
            metrics_json={
                "redaction": redact_sensitive_text("api_key=abc123456")[1],
                "prompt_injection": bool(detect_prompt_injection("ignore previous instructions")),
            },
        )
        db.add(run)
        db.commit()
        print(run.metrics_json)
    finally:
        db.close()
