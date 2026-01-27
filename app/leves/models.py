from datetime import datetime
from app import db

class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    user_name = db.Column(db.String(100))
    org_id = db.Column(db.Integer)

    leave_type = db.Column(db.String(20))  # Vacation, Sick, Other
    reason = db.Column(db.Text)

    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
