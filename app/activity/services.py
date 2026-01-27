from datetime import datetime
from app.extensions import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ActivityLog {self.user_name} - {self.action}>"


def log_activity(org_id, user_name, action):
    """
    Centralized activity logger.
    Call this from ANY route after a meaningful action.
    """
    log = ActivityLog(
        org_id=org_id,
        user_name=user_name,
        action=action
    )
    db.session.add(log)
    
def get_recent_activities(org_id, limit=20):
    """
    Returns latest activities in reverse chronological order
    """
    return (
        ActivityLog.query
        .filter_by(org_id=org_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )


def dashboard_stats(org_id):
    """
    Aggregates data for dashboard widgets
    """

    from app.expenses.models import Expense
    from app.leaves.models import LeaveRequest
    from app.models import Membership
    from sqlalchemy import func

    total_expense = (
        db.session.query(func.sum(Expense.amount))
        .filter(Expense.org_id == org_id)
        .scalar()
    ) or 0

    pending_leaves = (
        LeaveRequest.query
        .filter_by(org_id=org_id, status="pending")
        .count()
    )

    total_members = (
        Membership.query
        .filter_by(org_id=org_id, status="active")
        .count()
    )

    return {
        "total_expense": round(total_expense, 2),
        "pending_leaves": pending_leaves,
        "members": total_members
    }
