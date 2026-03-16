from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default="citizen")   # citizen | admin
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    reports       = db.relationship("Report", backref="user", lazy=True)

class Report(db.Model):
    __tablename__       = "reports"
    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_path          = db.Column(db.String(256), nullable=False)
    detected_category   = db.Column(db.String(100), nullable=False)
    confidence          = db.Column(db.Float, default=0.0)
    location            = db.Column(db.String(256), default="Unknown")
    description         = db.Column(db.Text, default="")
    status              = db.Column(db.String(50), default="Pending")  # Pending|In Progress|Resolved
    timestamp           = db.Column(db.DateTime, default=datetime.utcnow)

    def status_badge(self):
        return {"Pending": "warning", "In Progress": "info", "Resolved": "success"}.get(self.status, "secondary")

    def category_icon(self):
        icons = {
            "Garbage / Waste": "🗑️", "Pothole": "🕳️",
            "Broken Streetlight": "💡", "Water Leakage": "💧",
            "Illegal Dumping": "⚠️",   "Road Damage": "🚧",
            "Graffiti / Vandalism": "🎨", "Fallen Tree": "🌳",
            "Drainage Blockage": "🚰", "Other": "📍",
        }
        return icons.get(self.detected_category, "📍")