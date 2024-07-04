import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Database configuration
db_path = os.path.join(os.getenv('DATABASE_DIR', ''), 'reports.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set the upload folder paths
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['IMAGE_UPLOAD_FOLDER'] = os.getenv('IMAGE_UPLOAD_FOLDER', 'uploads/images')
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # Max file size: 16MB

db = SQLAlchemy(app)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(100), nullable=True)
    share_regions = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# Create the uploads directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['IMAGE_UPLOAD_FOLDER'], exist_ok=True)

# User's login details
stored_email = "a123456"
stored_password = "a123456"
stored_region = "JP"

# Function to authenticate user
def authenticate(email, password, region):
    if email == stored_email and password == stored_password and region == stored_region:
        return True
    return False

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        region = request.form["region"]

        if authenticate(email, password, region):
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password. Please try again."
            return render_template("login.html", error=error)

    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    region = request.args.get("region")
    if region:
        reports = Report.query.filter(Report.share_regions.contains(region)).all()
    else:
        reports = Report.query.all()
    return render_template("dashboard.html", reports=reports)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form["title"]
        date = request.form["date"]
        category = request.form["category"]
        content = request.form["content"]
        author = request.form["author"]
        share_regions = request.form.getlist("share_regions")
        file = request.files["file"]
        image_file = request.files["image"]

        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        image_filename = None
        if image_file and allowed_image_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], image_filename))

        report = Report(
            title=title,
            date=date,
            category=category,
            content=content,
            author=author,
            filename=filename,
            image_filename=image_filename,
            share_regions=",".join(share_regions)
        )
        db.session.add(report)
        db.session.commit()
        flash('Report successfully uploaded')
        return redirect(url_for('dashboard'))

    return render_template("upload.html")

@app.route("/download/<int:report_id>")
def download(report_id):
    report = Report.query.get_or_404(report_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], report.filename)
    if not os.path.exists(file_path):
        return f"Error: The file {report.filename} does not exist."
    return send_file(file_path, as_attachment=True)

@app.route("/edit_report/<int:report_id>", methods=["GET", "POST"])
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)
    if request.method == "POST":
        report.title = request.form["title"]
        report.date = request.form["date"]
        report.category = request.form["category"]
        report.content = request.form["content"]
        report.author = request.form["author"]
        share_regions = request.form.getlist("share_regions")
        report.share_regions = ",".join(share_regions)

        file = request.files["file"]
        image_file = request.files["image"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            report.filename = filename

        if image_file and allowed_image_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], image_filename))
            report.image_filename = image_filename

        db.session.commit()
        flash('Report successfully updated')
        return redirect(url_for('dashboard'))
    
    return render_template("edit_report.html", report=report)

@app.route("/uploads/images/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['IMAGE_UPLOAD_FOLDER'], filename)

@app.route("/logout", methods=["POST"])
def logout():
    return redirect(url_for("login"))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def dashboard():
    if request.method == "POST":
        return redirect(url_for('upload'))

    reports = Report.query.all()
    return render_template("dashboard.html", reports=reports)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
