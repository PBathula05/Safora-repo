import os
from datetime import datetime

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session,
    send_from_directory
)

from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from ultralytics import YOLO
from PIL import Image


# ===============================
# ENVIRONMENT SETUP
# ===============================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change_this_in_render")

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

YOLO_OUTPUT_FOLDER = "yolo_output"


# ===============================
# DIRECTORY SETUP
# ===============================

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(YOLO_OUTPUT_FOLDER, exist_ok=True)


# ===============================
# LOAD YOLO MODEL (ONCE)
# ===============================

try:
    MODEL = YOLO("models/best.pt")

    CLASS_NAMES = [
        "boots", "gloves", "goggles", "helmet",
        "no-boots", "no-gloves", "no-goggles",
        "no-helmet", "no-vest", "vest"
    ]

    print("✅ YOLOv8 Loaded Successfully")

except Exception as e:
    MODEL = None
    print("❌ YOLO Load Failed:", e)


# ===============================
# UTILITIES
# ===============================

def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in app.config["ALLOWED_EXTENSIONS"]
    )


# ===============================
# ROUTES
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ===============================
# LOGIN
# ===============================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if (
            email == os.getenv("APP_EMAIL")
            and password == os.getenv("APP_PASSWORD")
        ):

            session["logged_in"] = True
            session["username"] = email

            flash("Login Successful", "success")

            next_page = request.args.get("next")

            return redirect(next_page or url_for("index"))

        flash("Invalid Credentials", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out", "info")

    return redirect(url_for("index"))


# ===============================
# UPLOAD + DETECTION
# ===============================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if not session.get("logged_in"):
        return redirect(url_for("login", next=request.url))


    if request.method == "POST":

        if "file" not in request.files:
            flash("No file uploaded", "error")
            return redirect(request.url)


        file = request.files["file"]


        if file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)


        if not allowed_file(file.filename):
            flash("Invalid file type", "error")
            return redirect(request.url)


        filename = secure_filename(file.filename)

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(filepath)


        results_data = {
            "filename": filename,
            "image_url": url_for("uploaded_file", filename=filename),
            "detections": [],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }


        # ===============================
        # YOLO INFERENCE
        # ===============================

        if MODEL:

            try:

                results = MODEL.predict(
                    source=filepath,
                    save=True,
                    project=YOLO_OUTPUT_FOLDER,
                    name="exp",
                    exist_ok=True
                )


                r = results[0]


                detected_path = os.path.join(
                    r.save_dir,
                    os.path.basename(r.path)
                )


                if os.path.exists(detected_path):

                    rel = os.path.relpath(
                        detected_path,
                        YOLO_OUTPUT_FOLDER
                    ).replace("\\", "/")

                    results_data["image_url"] = url_for(
                        "yolo_file",
                        filename=rel
                    )


                # Extract boxes
                if r.boxes:

                    for box in r.boxes.data:

                        x1, y1, x2, y2, conf, cls = box

                        results_data["detections"].append({
                            "label": CLASS_NAMES[int(cls)],
                            "confidence": round(conf.item(), 2),
                            "box": [
                                int(x1), int(y1),
                                int(x2), int(y2)
                            ]
                        })


                if not results_data["detections"]:

                    results_data["detections"].append({
                        "label": "No objects",
                        "confidence": 1.0,
                        "box": []
                    })


            except Exception as e:

                results_data["detections"] = [{
                    "label": "Error",
                    "confidence": "N/A",
                    "box": str(e)
                }]


        else:

            results_data["detections"] = [{
                "label": "Model Not Loaded",
                "confidence": "N/A",
                "box": ""
            }]


        session["results"] = results_data

        return redirect(url_for("results"))


    return render_template("upload.html")


# ===============================
# RESULTS
# ===============================

@app.route("/results")
def results():

    data = session.get("results")

    return render_template("result.html", results=data)


# ===============================
# FILE SERVING
# ===============================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


@app.route("/yolo/<path:filename>")
def yolo_file(filename):

    base = os.path.join(app.root_path, YOLO_OUTPUT_FOLDER)

    return send_from_directory(base, filename)


# ===============================
# CONTACT FORM
# ===============================

@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("firstName")
    email = request.form.get("emailAddress")
    msg = request.form.get("message")

    with open("contact_messages.txt", "a") as f:

        f.write(
            f"{datetime.now()} | "
            f"{name} | {email} | {msg}\n"
        )

    flash("Message received", "success")

    return redirect(url_for("home"))


# ===============================
# RUN (RENDER SAFE)
# ===============================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
