import csv
import io
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, make_response
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import OrganizationForm
from app.models import Membership, Organization, Role, ActivityLog, Note, Expense, LeaveRequest, User

orgs_bp = Blueprint("orgs", __name__)


def _user_membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


@orgs_bp.route("/")
@login_required
def list_orgs():
    memberships = (
        Membership.query.filter_by(user_id=current_user.id, status="active")
        .order_by(Membership.created_at.desc())
        .all()
    )
    return render_template("orgs/list.html", memberships=memberships)


@orgs_bp.route("/orgs/create", methods=["GET", "POST"])
@login_required
def create_org():
    form = OrganizationForm()
    if form.validate_on_submit():
        slug_exists = Organization.query.filter_by(slug=form.slug.data.strip().lower()).first()
        if slug_exists:
            flash("Slug already taken. Choose another.", "warning")
            return render_template("orgs/create.html", form=form)
        org = Organization(
            name=form.name.data.strip(),
            slug=form.slug.data.strip().lower(),
            timezone=form.timezone.data.strip() or "UTC",
            default_workweek=form.default_workweek.data.strip() or "Mon-Fri",
            created_by_id=current_user.id,
        )
        db.session.add(org)
        db.session.flush()
        membership = Membership(user_id=current_user.id, org_id=org.id, role=Role.ADMIN, status="active", is_default=True)
        db.session.add(membership)
        db.session.commit()
        flash("Organization created and you are set as admin.", "success")
        return redirect(url_for("orgs.view_org", org_id=org.id))
    return render_template("orgs/create.html", form=form)


@orgs_bp.route("/orgs/<int:org_id>")
@login_required
def view_org(org_id):
    membership = _user_membership(org_id)
    if not membership:
        abort(403)
    org = membership.organization
    members = Membership.query.filter_by(org_id=org.id, status="active").all()
    return render_template("orgs/detail.html", org=org, membership=membership, members=members, Role=Role)


@orgs_bp.route("/orgs/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
def edit_org(org_id):
    membership = _user_membership(org_id)
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    org = membership.organization
    form = OrganizationForm(obj=org)
    if form.validate_on_submit():
        org.name = form.name.data.strip()
        org.slug = form.slug.data.strip().lower()
        org.timezone = form.timezone.data.strip() or "UTC"
        org.default_workweek = form.default_workweek.data.strip() or "Mon-Fri"
        db.session.commit()
        flash("Organization updated.", "success")
        return redirect(url_for("orgs.view_org", org_id=org.id))
    return render_template("orgs/edit.html", form=form, org=org)


@orgs_bp.route("/orgs/<int:org_id>/delete", methods=["POST"])
@login_required
def delete_org(org_id):
    membership = _user_membership(org_id)
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    org = membership.organization
    db.session.delete(org)
    db.session.commit()
    flash("Organization removed.", "info")
    return redirect(url_for("orgs.list_orgs"))


@orgs_bp.route("/orgs/<int:org_id>/set-default", methods=["POST"])
@login_required
def set_default_org(org_id):
    membership = _user_membership(org_id)
    if not membership:
        abort(403)
    Membership.query.filter_by(user_id=current_user.id).update({"is_default": False})
    membership.is_default = True
    db.session.commit()
    flash("Default organization updated.", "success")
    db.session.commit()
    flash("Default organization updated.", "success")
    return redirect(request.referrer or url_for("orgs.list_orgs"))


@orgs_bp.route("/orgs/<int:org_id>/members")
@login_required
def directory(org_id):
    membership = _user_membership(org_id)
    if not membership:
        abort(403)
    
    org = membership.organization
    query = request.args.get("q", "").strip()

    members_query = Membership.query.join(Membership.user).filter(
        Membership.org_id == org.id,
        Membership.status == "active"
    )

    if query:
        # Case-insensitive search on User name or Email
        from app.models import User
        members_query = members_query.filter(
            (User.name.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))
        )
    
    # Sort by Role (Admin first) then Name
    # Enum order in Python isn't automatically SQL sortable in a simple way across all DBs without casting,
    # but let's try sorting by role value if compatible, or just fetch and strict sort in python for small orgs.
    # For now, let's sort by name and highlight admins in template. 
    # Or strict sort: Admin < Member usually if A < M.
    # Let's sort by Name for now as it's cleaner for directory.
    members = members_query.order_by(Membership.user.property.mapper.class_.name).all()

    return render_template("orgs/members.html", org=org, members=members, query=query, Role=Role)

@orgs_bp.route("/orgs/<slug>/activity")
@login_required
def activity(slug):
    org = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check membership
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
    if not membership:
        flash("You must be a member of this organization to view activity log.", "error")
        return redirect(url_for("orgs.dashboard", slug=slug))

    activities = ActivityLog.query.filter_by(org_id=org.id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    
    return render_template("orgs/activity.html", org=org, activities=activities)

@orgs_bp.route("/orgs/<slug>/export", methods=["GET", "POST"])
@login_required
def export_data(slug):
    org = Organization.query.filter_by(slug=slug).first_or_404()
    
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
    if not membership:
        flash("You must be a member of this organization to export data.", "error")
        return redirect(url_for("orgs.dashboard", slug=slug))

    if request.method == "POST":
        data_type = request.form.get("data_type")
        
        si = io.StringIO()
        cw = csv.writer(si)
        filename = f"{slug}_{data_type}_{current_user.id}.csv"

        if data_type == "members":
            cw.writerow(["Name", "Email", "Role", "Status", "Joined At"])
            members = Membership.query.filter_by(org_id=org.id).all()
            for m in members:
                cw.writerow([m.user.name, m.user.email, m.role.value, m.status, m.created_at])
        
        elif data_type == "expenses":
            cw.writerow(["Date", "User", "Category", "Description", "Amount"])
            expenses = Expense.query.filter_by(org_id=org.id).all()
            for e in expenses:
                cw.writerow([e.date, e.user.name, e.category, e.description, e.amount])

        elif data_type == "leaves":
            cw.writerow(["Type", "User", "Start Date", "End Date", "Status", "Reason"])
            leaves = LeaveRequest.query.filter_by(org_id=org.id).all()
            for l in leaves:
                cw.writerow([l.type, l.user.name, l.start_date, l.end_date, l.status, l.reason])

        elif data_type == "notes":
            cw.writerow(["Date", "User", "Content"])
            notes = Note.query.filter_by(org_id=org.id).all()
            for n in notes:
                cw.writerow([n.created_at, n.user.name, n.content])

        elif data_type == "activity":
            cw.writerow(["Date", "User", "Action"])
            activities = ActivityLog.query.filter_by(org_id=org.id).order_by(ActivityLog.created_at.desc()).all()
            for a in activities:
                cw.writerow([a.created_at, a.user.name, a.action])

        else:
            flash("Invalid data type selected.", "error")
            return redirect(url_for("orgs.export_data", slug=slug))

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={filename}"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template("orgs/export.html", org=org)
