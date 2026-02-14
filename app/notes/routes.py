from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Note, Organization, Membership
from app.utils import log_activity

notes_bp = Blueprint("notes", __name__)

@notes_bp.route("/orgs/<slug>/notes", methods=["GET", "POST"])
@login_required
def index(slug):
    org = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check membership
    if not current_user.is_org_admin(org.id):
        # Allow members too, so check for generic membership
        membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
        if not membership:
             flash("You must be a member of this organization to view notes.", "error")
             return redirect(url_for("orgs.dashboard", slug=slug))

    if request.method == "POST":
        content = request.form.get("content")
        if not content:
            flash("Note content cannot be empty.", "error")
        else:
            note = Note(content=content, user_id=current_user.id, org_id=org.id)
            db.session.add(note)
            db.session.commit()
            log_activity(org.id, current_user.id, "Added a team note.")
            flash("Note added successfully.", "success")
            return redirect(url_for("notes.index", slug=slug))

    notes = Note.query.filter_by(org_id=org.id).order_by(Note.created_at.desc()).all()
    return render_template("notes/index.html", org=org, notes=notes)

@notes_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete(note_id):
    note = Note.query.get_or_404(note_id)
    
    # Authorization: Only author can delete
    if note.user_id != current_user.id:
        flash("You are not authorized to delete this note.", "error")
        # Redirect back to the org's notes page
        org = Organization.query.get(note.org_id)
        return redirect(url_for("notes.index", slug=org.slug))

    org_slug = note.organization.slug
    db.session.delete(note)
    db.session.commit()
    log_activity(note.org_id, current_user.id, "Deleted a team note.")
    flash("Note deleted successfully.", "success")
    return redirect(url_for("notes.index", slug=org_slug))
