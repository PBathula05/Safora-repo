import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --- ADD THESE IMPORTS FOR YOLOv8 ---
from ultralytics import YOLO
from PIL import Image # For image processing (Pillow library)
import shutil # ADD THIS LINE for file operations
import glob   # ADD THIS LINE for finding latest directories
from datetime import datetime # ADD THIS LINE for timestamps
# No need for numpy directly for simple YOLOv8 use if passing PIL Image
# --- END ADDED IMPORTS ---


# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_default_if_not_set')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Create the uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Create a folder for YOLOv8 output if it doesn't exist ---
YOLO_OUTPUT_FOLDER = 'yolo_output'
if not os.path.exists(YOLO_OUTPUT_FOLDER):
    os.makedirs(YOLO_OUTPUT_FOLDER)
# --- END YOLOv8 folder creation ---

# --- GLOBAL YOLOv8 MODEL LOADING SECTION ---
# This code runs only ONCE when your Flask application starts.
try:
    # 1. Load your YOLOv8 model:
    MODEL = YOLO('models/best.pt') # <--- NOW IT USES YOUR best.pt FILE!
    print("YOLOv8 model loaded successfully!")

    # 2. Define your class names:
    #    This list MUST match the order of classes your YOLO model was trained on.
    #    Adjust if your classes are different (e.g., ['person', 'hat', 'boot'])
    CLASS_NAMES = ['boots', 'gloves', 'goggles', 'helmet', 'no-boots', 'no-gloves', 'no-goggles', 'no-helmet', 'no-vest', 'vest']
    # Alternatively, and often safer: CLASS_NAMES = MODEL.names
    print(f"YOLOv8 Class Names: {CLASS_NAMES}")

except Exception as e:
    MODEL = None
    print(f"Error loading YOLOv8 model: {e}")
    print("YOLOv8 features will be disabled.")
# --- END GLOBAL YOLOv8 MODEL LOADING SECTION ---


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    # As per your provided app.py, /home is no longer protected.
    # If you want to protect it, add the login check back here.
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("DEBUG: Login route function called.")
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == os.getenv('APP_EMAIL') and password == os.getenv('APP_PASSWORD'):
            session['logged_in'] = True
            session['username'] = email
            flash('Logged in successfully!', 'success')
            # --- MODIFIED: Handle 'next' parameter ---
            next_url = request.form.get('next') or request.args.get('next')
            if next_url:
                print(f"DEBUG: Redirecting to next_url: {next_url}")
                return redirect(next_url)
            # --- END MODIFIED ---
            print("DEBUG: No next_url, redirecting to index.")
            return redirect(url_for('index')) # Default redirect if no 'next'
        else:
            flash('Invalid email or password.', 'error')
            print("DEBUG: Invalid credentials.")
    # --- MODIFIED: Pass 'next' parameter to template for GET requests ---
    return render_template('login.html', next=request.args.get('next'))
    # --- END MODIFIED ---


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # Ensure user is logged in before allowing upload
    if not session.get('logged_in'):
        flash('Please log in to upload images.', 'info')
        print(f"DEBUG: Not logged in for upload, redirecting to login with next={request.url}")
        return redirect(url_for('login', next=request.url))

    if request.method == 'POST':
        print("DEBUG: POST request received to /upload")
        if 'file' not in request.files:
            flash('No file part', 'error')
            print("DEBUG: 'file' not in request.files, redirecting.")
            return redirect(request.url)

        file = request.files['file']
        print(f"DEBUG: File object received: {file.filename}")

        if file.filename == '':
            flash('No selected file', 'error')
            print("DEBUG: No file selected (filename empty), redirecting.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            print(f"DEBUG: File '{file.filename}' is allowed. Proceeding with save and detection.")
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            detection_results = {
                'filename': filename,
                'original_image_url': url_for('serve_uploaded_file', filename=filename),
                'image_url': url_for('serve_uploaded_file', filename=filename), # Default to original
                'detections': [],
                'status': 'Processing...',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            if MODEL is None:
                detection_results['status'] = 'Error: YOLOv8 model not loaded.'
                flash('YOLOv8 model not loaded. Cannot perform detection.', 'error')
                print("DEBUG: YOLOv8 model not loaded, handling as error.")
            else:
                # ... (inside upload_file route, within the 'if MODEL is None' else block)
               # ... (inside upload_file route, within the 'if MODEL is None' else block)
                try:
                    yolo_output_subdir = os.path.join(YOLO_OUTPUT_FOLDER, 'exp')
                    if not os.path.exists(yolo_output_subdir):
                        os.makedirs(yolo_output_subdir)
                        print(f"DEBUG: Created YOLO output subdirectory: {yolo_output_subdir}")

                    results_list = MODEL.predict(
                        source=filepath,
                        save=True,
                        project=YOLO_OUTPUT_FOLDER,
                        name='exp',
                        exist_ok=True,
                        save_crop=False,
                        save_conf=False,
                        save_txt=False
                    )

                    full_path_to_detected_image = None
                    if results_list and len(results_list) > 0:
                        yolo_result = results_list[0] # Get the first (and likely only) result object

                        saved_output_dir = yolo_result.save_dir
                        print(f"DEBUG: YOLO result saved_output_dir: {saved_output_dir}") # Add this to confirm

                        original_basename = os.path.basename(filepath)
                        print(f"DEBUG: Original input basename: {original_basename}") # Add this to confirm

                        # --- CRITICAL CHANGE/ADDITION ---
                        # Use yolo_result.path to get the exact filename YOLO *expected* to save.
                        # Then join it with the actual save_dir.
                        # This should be the most reliable way as YOLO itself sets these properties.
                        yolo_saved_filename = os.path.basename(yolo_result.path) # This is the basename of the *input* file
                        full_path_to_detected_image = os.path.join(saved_output_dir, yolo_saved_filename)

                        print(f"DEBUG: Calculated full_path_to_detected_image (from yolo_result.path): {full_path_to_detected_image}")

                        # If YOLO indeed converts to .jpg, then the filename might change from .jpeg to .jpg
                        # Let's add a check for the .jpg version as well if the first one doesn't exist
                        if not os.path.exists(full_path_to_detected_image):
                            name_without_ext = os.path.splitext(yolo_saved_filename)[0]
                            jpg_candidate_path = os.path.join(saved_output_dir, f"{name_without_ext}.jpg")
                            print(f"DEBUG: Checking JPG candidate path: {jpg_candidate_path}")
                            if os.path.exists(jpg_candidate_path):
                                full_path_to_detected_image = jpg_candidate_path
                                print(f"DEBUG: Found processed image with .jpg extension: {full_path_to_detected_image}")

                        # --- END CRITICAL CHANGE/ADDITION ---

                        if full_path_to_detected_image and os.path.exists(full_path_to_detected_image):
                            relative_path_for_url = os.path.relpath(full_path_to_detected_image, YOLO_OUTPUT_FOLDER)
                            relative_path_for_url = relative_path_for_url.replace(os.sep, '/')

                            detection_results['image_url'] = url_for('serve_yolo_output', filename=relative_path_for_url)
                            print(f"DEBUG: Final YOLO processed image URL used: {detection_results['image_url']}")
                        else:
                            print(f"WARNING: Processed image NOT FOUND after all checks. Falling back to original.")
                            # List content of the save_dir to debug what's actually there
                            print(f"DEBUG: Contents of '{saved_output_dir}': {os.listdir(saved_output_dir) if os.path.exists(saved_output_dir) else 'Directory not found.'}")
                            detection_results['image_url'] = detection_results['original_image_url']
                            flash('Failed to find processed image. Displaying original.', 'warning')
                    else:
                        print(f"DEBUG: YOLO model.predict() returned no results for image: {filename}. Falling back to original.")
                        detection_results['image_url'] = detection_results['original_image_url']
                        flash('YOLO detection did not produce results. Displaying original.', 'warning')

                    # Process detection results (boxes, labels, confidence) - this part is mostly fine
                    detections = []
                    if results_list and len(results_list) > 0 and results_list[0].boxes and len(results_list[0].boxes.data) > 0:
                        for *xyxy, conf, cls in results_list[0].boxes.data:
                            label = CLASS_NAMES[int(cls)]
                            detections.append({
                                'label': label,
                                'confidence': round(conf.item(), 2),
                                'box': [int(x.item()) for x in xyxy]
                            })
                        print(f"DEBUG: Detections found: {detections}")
                    else:
                        print(f"DEBUG: No objects detected in image: {filename}")
                        detections.append({'label': 'No objects detected', 'confidence': 1.0, 'box': []})

                    detection_results['detections'] = detections
                    detection_results['status'] = 'Detection Complete'
                    detection_results['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print("DEBUG: YOLO inference completed successfully and results processed.")

                except Exception as e:
                    print(f"DEBUG: Error during YOLOv8 inference: {e}")
                    detection_results['image_url'] = detection_results['original_image_url']
                    detection_results['detections'] = [{'label': 'Error', 'confidence': 'N/A', 'box': str(e)}]
                    detection_results['status'] = f'Processing Failed: {e}'
                    detection_results['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            session['detection_results'] = detection_results
            flash(f'File {filename} uploaded and processed!', 'success')
            print("DEBUG: Redirecting to /results after processing.")
            return redirect(url_for('results'))
        else: # This 'else' belongs to 'if file and allowed_file(file.filename):'
            flash('Allowed image types are png, jpg, jpeg, gif', 'error')
            print(f"DEBUG: File '{file.filename}' not allowed, redirecting to {request.url}.")
            return redirect(request.url)
    
    # This block handles GET requests for the /upload page
    print("DEBUG: GET request to /upload, rendering upload.html.")
    return render_template('upload.html')

@app.route('/results')
def results():
    # This is where you would retrieve the detection results from your session
    # or a temporary storage, as they are not passed directly in the URL.
    # Assuming you're storing them in Flask's session or a global/cache:
    detection_results = session.get('detection_results', None)
    if detection_results:
        app.logger.debug(f"Displaying result.html with image_url: {detection_results.get('image_url')}")
    else:
        app.logger.debug("No detection results found in session for /results page.")

    return render_template('result.html', results=detection_results)

# Route to serve files from the uploads folder (for original images)
@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to serve files from the yolo_output folder (for processed images)
@app.route('/yolo_output_files/<path:filename>')
def serve_yolo_output(filename):
    safe_path = os.path.join(app.root_path, YOLO_OUTPUT_FOLDER)
    print(f"DEBUG: Serving YOLO output file from: {safe_path}, filename: {filename}")
    return send_from_directory(safe_path, filename)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def result():
    return render_template('result.html')

@app.route('/contact', methods=['POST'])
def contact():
    # Get form data
    first_name = request.form.get('firstName')
    email = request.form.get('emailAddress')
    message = request.form.get('message')

    # Save to a local text file
    with open('contact_messages.txt', 'a') as f:
        f.write(f"{datetime.now()} | Name: {first_name} | Email: {email} | Message: {message}\n")

    flash("Thanks for contacting us!", "success")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)