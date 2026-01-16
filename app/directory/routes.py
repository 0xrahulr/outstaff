from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from app.models import Membership, Role, User

directory_bp = Blueprint("directory", __name__, url_prefix="/orgs/<int:org_id>/directory")


def _require_membership(org_id):
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()
    if not membership:
        abort(403)
    return membership


@directory_bp.route("/")
@login_required
def list_members(org_id):
    membership = _require_membership(org_id)
    org = membership.organization
    
    # Get search query from URL parameters
    search_query = request.args.get("search", "").strip()
    
    # Get all active members for this organization
    all_members = Membership.query.filter_by(org_id=org_id, status="active").all()
    
    # Apply search filter if provided
    if search_query:
        search_lower = search_query.lower()
        filtered_members = []
        for member in all_members:
            # Access user through the backref relationship
            user = member.user
            if not user:
                continue
                
            user_name = (user.name or "").lower()
            user_email = (user.email or "").lower()
            role_value = (member.role.value if member.role else "").lower()
            
            # Check if search term matches name, email, or role
            if (search_lower in user_name or 
                search_lower in user_email or
                search_lower in role_value):
                filtered_members.append(member)
        members = filtered_members
    else:
        members = all_members
    
    # Sort: admins first, then by join date
    members = sorted(
        members,
        key=lambda m: (m.role != Role.ADMIN, m.created_at)  # Admins first (False < True), then by date
    )
    
    return render_template(
        "directory/list.html",
        org=org,
        membership=membership,
        members=members,
        search_query=search_query,
        Role=Role
    )
