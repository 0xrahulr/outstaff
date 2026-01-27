from flask import Blueprint, render_template, request, make_response
from app import db
from .models import Expense
from app.activity.services import log_activity
import csv, io

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

@expenses_bp.route("/", methods=["GET", "POST"])
def expenses():
    if request.method == "POST":
        expense = Expense(
            org_id=1,
            amount=float(request.form["amount"]),
            category=request.form["category"],
            description=request.form["description"]
        )
        db.session.add(expense)
        log_activity(1, "User", "Added expense")
        db.session.commit()

    expenses = Expense.query.all()
    total = sum(e.amount for e in expenses)
    return render_template("expenses/list.html", expenses=expenses, total=total)


@expenses_bp.route("/export")
def export_csv():
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Amount", "Category", "Date", "Description"])

    for e in Expense.query.all():
        writer.writerow([e.amount, e.category, e.date, e.description])

    response = make_response(si.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=expenses.csv"
    return response
