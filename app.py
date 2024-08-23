import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from dotenv import load_dotenv
import io

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Use the Heroku-provided DATABASE_URL environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace("://", "ql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=True)  # Store file binary data
    image_filename = db.Column(db.String(100), nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Store image binary data
    excel_filename = db.Column(db.String(100), nullable=True)
    excel_data = db.Column(db.LargeBinary, nullable=True)  # Store Excel file binary data
    share_regions = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# User login info
stored_email = "a123456"
stored_password = "a123456"
stored_region = "JP"

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
    page = request.args.get('page', 1, type=int)
    region = request.args.get("region")
    if region:
        reports = Report.query.filter(Report.share_regions.contains(region)).order_by(Report.upload_date.desc()).paginate(page=page, per_page=5, error_out=False)
    else:
        reports = Report.query.order_by(Report.upload_date.desc()).paginate(page=page, per_page=5, error_out=False)
    return render_template("dashboard.html", reports=reports)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        # Retrieve form data
        title = request.form["title"]
        date = request.form["date"]
        category = request.form["category"]
        content = request.form["content"]
        author = request.form["author"]
        share_regions = request.form.getlist("share_regions")
        file = request.files["file"]
        image_file = request.files["image"]
        excel_file = request.files["excel"]

        # File handling logic
        filename = None
        file_data = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_data = file.read()
        else:
            flash('Invalid file type. Only PDF files are allowed.')
            return redirect(url_for('upload'))

        image_filename = None
        image_data = None
        if image_file and allowed_image_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_data = image_file.read()
        elif image_file:
            flash('Invalid image type. Only PNG, JPG, and JPEG files are allowed.')
            return redirect(url_for('upload'))

        excel_filename = None
        excel_data = None
        if excel_file and allowed_excel_file(excel_file.filename):
            excel_filename = secure_filename(excel_file.filename)
            excel_data = excel_file.read()
        elif excel_file:
            flash('Invalid excel type. Only XLSX files are allowed.')
            return redirect(url_for('upload'))

        # Create new report entry
        report = Report(
            title=title,
            date=date,
            category=category,
            content=content,
            author=author,
            filename=filename,
            file_data=file_data,
            image_filename=image_filename,
            image_data=image_data,
            excel_filename=excel_filename,
            excel_data=excel_data,
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
    return send_file(
        io.BytesIO(report.file_data),
        as_attachment=True,
        download_name=report.filename
    )

@app.route("/download_excel/<int:report_id>")
def download_excel(report_id):
    report = Report.query.get_or_404(report_id)
    return send_file(
        io.BytesIO(report.excel_data),
        as_attachment=True,
        download_name=report.excel_filename
    )

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
        excel_file = request.files["excel"]

        if file and allowed_file(file.filename):
            report.filename = secure_filename(file.filename)
            report.file_data = file.read()  # Update file binary data
        elif file:
            flash('Invalid file type. Only PDF files are allowed.')
            return redirect(url_for('edit_report', report_id=report_id))

        if image_file and allowed_image_file(image_file.filename):
            report.image_filename = secure_filename(image_file.filename)
            report.image_data = image_file.read()  # Update image binary data
        elif image_file:
            flash('Invalid image type. Only PNG, JPG, and JPEG files are allowed.')
            return redirect(url_for('edit_report', report_id=report_id))

        if excel_file and allowed_excel_file(excel_file.filename):
            report.excel_filename = secure_filename(excel_file.filename)
            report.excel_data = excel_file.read()  # Update Excel binary data
        elif excel_file:
            flash('Invalid Excel file type. Only XLSX files are allowed.')
            return redirect(url_for('edit_report', report_id=report_id))

        db.session.commit()
        flash('Report successfully updated')
        return redirect(url_for('dashboard'))
    
    return render_template("edit_report.html", report=report)

@app.route("/uploads/images/<filename>")
def uploaded_file(filename):
    report = Report.query.filter_by(image_filename=filename).first()
    if report and report.image_data:
        return send_file(
            io.BytesIO(report.image_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=filename
        )
    return "File not found", 404

@app.route("/logout", methods=["POST"])
def logout():
    return redirect(url_for("login"))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_excel_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx, csv, xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
