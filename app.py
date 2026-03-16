import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, User, Report
from utils.classifier import classify_image


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "urban_reporter_secret_2024")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///urban_reporter.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
db.init_app(app)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ── AUTH ──────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw    = request.form.get("password", "")
        if not name or not email or not pw:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("register.html")
        db.session.add(User(name=name, email=email,
                            password_hash=generate_password_hash(pw), role="citizen"))
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw    = request.form.get("password", "")
        user  = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, pw):
            session.update({"user_id": user.id, "user_name": user.name, "user_role": user.role})
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("admin_dashboard" if user.role == "admin" else "dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))



# ── CITIZEN ───────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    reports = Report.query.filter_by(user_id=session["user_id"]).order_by(Report.timestamp.desc()).all()
    return render_template("dashboard.html", reports=reports)

@app.route("/report", methods=["GET", "POST"])
def report():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        file     = request.files.get("image")
        location = request.form.get("location", "Unknown").strip()
        desc     = request.form.get("description", "").strip()
        if not file or file.filename == "":
            flash("No image selected.", "error")
            return render_template("report.html")
        if not allowed_file(file.filename):
            flash("Invalid file type.", "error")
            return render_template("report.html")
        ext      = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        category, confidence = classify_image(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        db.session.add(Report(user_id=session["user_id"], image_path=filename,
                              detected_category=category, confidence=confidence,
                              location=location, description=desc,
                              status="Pending", timestamp=datetime.utcnow()))
        db.session.commit()
        flash(f"Reported! AI detected: {category} ({confidence:.0%} confidence).", "success")
        return redirect(url_for("dashboard"))
    return render_template("report.html")

@app.route("/report/<int:report_id>")
def view_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    rpt = Report.query.get_or_404(report_id)
    if rpt.user_id != session["user_id"] and session.get("user_role") != "admin":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))
    return render_template("view_report.html", report=rpt)

@app.route("/report/delete/<int:report_id>", methods=["POST"])
def delete_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    rpt = Report.query.get_or_404(report_id)
    if rpt.user_id != session["user_id"]:
        flash("You can only delete your own reports.", "error")
        return redirect(url_for("dashboard"))
    # Delete image file from disk
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], rpt.image_path)
    if os.path.exists(image_path):
        os.remove(image_path)
    db.session.delete(rpt)
    db.session.commit()
    flash("Report deleted successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route('/sw.js')
def sw():
    return send_from_directory('static', 'sw.js',
                               mimetype='application/javascript')
# ── ADMIN ─────────────────────────────────────
@app.route("/admin")
def admin_dashboard():
    if session.get("user_role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("dashboard"))
    status_filter   = request.args.get("status", "All")
    category_filter = request.args.get("category", "All")
    query = Report.query
    if status_filter   != "All": query = query.filter_by(status=status_filter)
    if category_filter != "All": query = query.filter_by(detected_category=category_filter)
    reports    = query.order_by(Report.timestamp.desc()).all()
    stats      = {"total": Report.query.count(),
                  "pending":     Report.query.filter_by(status="Pending").count(),
                  "in_progress": Report.query.filter_by(status="In Progress").count(),
                  "resolved":    Report.query.filter_by(status="Resolved").count()}
    categories = [c[0] for c in db.session.query(Report.detected_category).distinct().all()]
    return render_template("admin.html", reports=reports, stats=stats, categories=categories,
                           status_filter=status_filter, category_filter=category_filter)

@app.route("/admin/update_status/<int:report_id>", methods=["POST"])
def update_status(report_id):
    if session.get("user_role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    rpt = Report.query.get_or_404(report_id)
    new_status = request.form.get("status")
    if new_status not in ["Pending", "In Progress", "Resolved"]:
        flash("Invalid status.", "error")
        return redirect(url_for("admin_dashboard"))
    rpt.status = new_status
    db.session.commit()
    flash(f"Report #{report_id} updated to '{new_status}'.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/report/<int:report_id>")
def admin_view_report(report_id):
    if session.get("user_role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("dashboard"))
    rpt      = Report.query.get_or_404(report_id)
    reporter = User.query.get(rpt.user_id)
    return render_template("admin_report.html", report=rpt, reporter=reporter)

# ── INIT ──────────────────────────────────────
def create_tables():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email="admin@urbanreporter.com").first():
            db.session.add(User(name="Admin", email="admin@urbanreporter.com",
                                password_hash=generate_password_hash("admin123"), role="admin"))
            db.session.commit()
            print("Default admin created: admin@urbanreporter.com / admin123")

if __name__ == "__main__":
    create_tables()
    app.run(debug=True, port=5000)