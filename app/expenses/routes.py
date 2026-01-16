from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.forms import ExpenseForm
from app.models import Expense, Membership, Role

expenses_bp = Blueprint("expenses", __name__, url_prefix="/orgs/<int:org_id>/expenses")


def _require_membership(org_id):
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()
    if not membership:
        abort(403)
    return membership


@expenses_bp.route("/", methods=["GET", "POST"])
@login_required
def list_expenses(org_id):
    membership = _require_membership(org_id)
    org = membership.organization
    
    form = ExpenseForm()
    
    # Handle form submission
    if form.validate_on_submit():
        try:
            # Convert amount string to Decimal
            amount = Decimal(str(form.amount.data).replace(",", ""))
            if amount <= 0:
                flash("Amount must be greater than zero.", "warning")
                return redirect(url_for("expenses.list_expenses", org_id=org_id))
            
            expense = Expense(
                org_id=org_id,
                user_id=current_user.id,
                amount=amount,
                category=form.category.data.strip(),
                date=form.date.data,
                description=form.description.data.strip() if form.description.data else None
            )
            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully.", "success")
            return redirect(url_for("expenses.list_expenses", org_id=org_id))
        except (ValueError, InvalidOperation):
            flash("Invalid amount. Please enter a valid number.", "danger")
            return redirect(url_for("expenses.list_expenses", org_id=org_id))
    
    # Get all expenses for this organization, ordered by date (newest first)
    expenses = Expense.query.filter_by(org_id=org_id).order_by(Expense.date.desc(), Expense.created_at.desc()).all()
    
    # Calculate total amount
    total_result = db.session.query(func.sum(Expense.amount)).filter_by(org_id=org_id).scalar()
    total_amount = total_result if total_result else Decimal("0.00")
    
    return render_template(
        "expenses/list.html",
        org=org,
        membership=membership,
        expenses=expenses,
        form=form,
        total_amount=total_amount,
        Role=Role
    )
