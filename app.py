import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Configuration for database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define your models here
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(100), nullable=True)
    share_regions = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)

@app.route('/')
def index():
    reports = Report.query.all()
    return render_template('index.html', reports=reports)

# Create the uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['IMAGE_UPLOAD_FOLDER']):
    os.makedirs(app.config['IMAGE_UPLOAD_FOLDER'])

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
    if request.method == "POST":
        return redirect(url_for('upload'))

    reports = Report.query.all()
    return render_template("dashboard.html", reports=reports)

@app.route("/upload", methods=["POST"])
def upload():
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

@app.route("/download/<int:report_id>")
def download(report_id):
    report = Report.query.get_or_404(report_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], report.filename)
    if not os.path.exists(file_path):
        return f"Error: The file {report.filename} does not exist."
    return send_file(file_path, as_attachment=True)

@app.route("/edit_report/<int:report_id>", methods=["POST"])
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)
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

# Add a route to perform the schema update
@app.route("/update_db")
def update_db():
    with app.app_context():
        db.session.execute(text('ALTER TABLE report ADD COLUMN image_filename VARCHAR(100)'))
        db.session.execute(text('ALTER TABLE report ADD COLUMN share_regions VARCHAR(100)'))
        db.session.commit()
    return "Database updated!"

if __name__ == "__main__":
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with app.app_context():
        db.create_all()
    app.run(debug=True)
