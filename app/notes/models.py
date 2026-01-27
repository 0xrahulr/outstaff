from app.extensions import db
from datetime import datetime

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
