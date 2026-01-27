from flask import Blueprint, render_template, request, redirect
from app import db
from .models import LeaveRequest
from app.activity.services import log_activity

leaves_bp = Blueprint("leaves", __name__, url_prefix="/leaves")

@leaves_bp.route("/", methods=["GET", "POST"])
def apply_leave():
    if request.method == "POST":
        leave = LeaveRequest(
            user_id=1,
            user_name="Current User",
            org_id=1,
            leave_type=request.form["leave_type"],
            reason=request.form["reason"]
        )
        db.session.add(leave)
        log_activity(1, "Current User", "Applied for leave")
        db.session.commit()
        return redirect("/leaves")

    leaves = LeaveRequest.query.all()
    return render_template("leaves/apply.html", leaves=leaves)


@leaves_bp.route("/manage/<int:id>/<status>")
def update_leave(id, status):
    leave = LeaveRequest.query.get_or_404(id)
    leave.status = status
    log_activity(1, "Admin", f"Leave {status}")
    db.session.commit()
    return redirect("/leaves")
