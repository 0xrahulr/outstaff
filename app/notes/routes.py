from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Membership
from .models import Note

notes_bp = Blueprint("notes", __name__, url_prefix="/orgs/<int:org_id>/notes")

@notes_bp.route("/", methods=["GET", "POST"])
@login_required
def notes(org_id):
    membership = Membership.query.filter_by(
        user_id=current_user.id, org_id=org_id, status="active"
    ).first_or_404()

    if request.method == "POST":
        note = Note(
            content=request.form["content"],
            user_id=current_user.id,
            org_id=org_id
        )
        db.session.add(note)
        db.session.commit()

    notes = Note.query.filter_by(org_id=org_id).order_by(Note.created_at.desc())
    return render_template("notes/list.html", notes=notes, membership=membership)
