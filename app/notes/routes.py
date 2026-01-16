from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import NoteForm
from app.models import Membership, Note, Role

notes_bp = Blueprint("notes", __name__, url_prefix="/orgs/<int:org_id>/notes")


def _membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


def _require_membership(org_id):
    membership = _membership(org_id)
    if not membership:
        abort(403)
    return membership


@notes_bp.route("/", methods=["GET", "POST"])
@login_required
def list_notes(org_id):
    membership = _require_membership(org_id)
    org = membership.organization
    
    form = NoteForm()
    notes = Note.query.filter_by(org_id=org_id).order_by(Note.created_at.desc()).all()
    
    if form.validate_on_submit():
        note = Note(
            org_id=org_id,
            author_id=current_user.id,
            content=form.content.data.strip(),
        )
        db.session.add(note)
        db.session.commit()
        flash("Note added successfully.", "success")
        return redirect(url_for("notes.list_notes", org_id=org_id))
    
    return render_template("notes/list.html", org=org, membership=membership, notes=notes, form=form, Role=Role)


@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(org_id, note_id):
    membership = _require_membership(org_id)
    note = Note.query.filter_by(id=note_id, org_id=org_id).first_or_404()
    
    # Only the author can delete their own note
    if note.author_id != current_user.id:
        abort(403)
    
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted successfully.", "info")
    return redirect(url_for("notes.list_notes", org_id=org_id))
