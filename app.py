import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()  # 從.env文件加載環境變量

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# 使用Heroku提供的DATABASE_URL環境變量
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace("://", "ql://", 1)  # Heroku上的DATABASE_URL需要進行修改
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
    share_regions = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# 用戶的登錄信息
stored_email = "a123456"
stored_password = "a123456"
stored_region = "JP"

# 用於驗證用戶的函數
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
        title = request.form["title"]
        date = request.form["date"]
        category = request.form["category"]
        content = request.form["content"]
        author = request.form["author"]
        share_regions = request.form.getlist("share_regions")
        file = request.files["file"]
        image_file = request.files["image"]
        excel_file = request.files.get("excel")

        filename = None
        file_data = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_data = file.read()  # Read file binary data
        else:
            flash('Invalid file type. Only PDF files are allowed.')
            return redirect(url_for('upload'))

        image_filename = None
        image_data = None
        if image_file and allowed_image_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_data = image_file.read()  # Read image binary data
        elif image_file:
            flash('Invalid image type. Only PNG, JPG, and JPEG files are allowed.')
            return redirect(url_for('upload'))

        # Process Excel file if uploaded
        excel_data = None
        if excel_file and allowed_file(excel_file.filename):
            excel_filename = secure_filename(excel_file.filename)
            excel_data = pd.read_excel(excel_file)  # Read the Excel file into a DataFrame
            # Perform any processing with excel_data if necessary
        elif excel_file:
            flash('Invalid file type. Only Excel files are allowed.')
            return redirect(url_for('upload'))

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
        excel_file = request.files.get("excel")

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

        # Process Excel file if uploaded
        if excel_file and allowed_file(excel_file.filename):
            excel_data = pd.read_excel(excel_file)  # Read the Excel file into a DataFrame
            # Perform any processing with excel_data if necessary
        elif excel_file:
            flash('Invalid file type. Only Excel files are allowed.')
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
    ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
