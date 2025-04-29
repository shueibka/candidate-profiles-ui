# backend/audit_log.py

from uuid import uuid4
from datetime import datetime, timedelta
from db_connection import get_session
from models import AuditLog

def get_current_timestamps():
    utc_now = datetime.utcnow()
    swedish_now = utc_now + timedelta(hours=2)
    return utc_now, swedish_now

def log_audit(record_id, operation, status, error_message=None):
    session = get_session()

    try:
        audit_id = str(uuid4())
        utc_timestamp, swedish_timestamp = get_current_timestamps()

        audit_entry = AuditLog(
            audit_id=audit_id,
            record_id=record_id,
            operation=operation,
            status=status,
            error_message=error_message if error_message else "",
            utc_timestamp=utc_timestamp,
            swedish_timestamp=swedish_timestamp
        )

        session.add(audit_entry)
        session.commit()
        print(f"📝 Audit log: {operation} - {status}")

    except Exception as e:
        session.rollback()
        print(f"❌ Audit log failed: {e}")

    finally:
        session.close()
