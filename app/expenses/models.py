from app import db
from datetime import date

class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    date = db.Column(db.Date, default=date.today)
