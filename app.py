from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import requests
from werkzeug.utils import secure_filename
from flask_session import Session

# --- Run once at app startup ---
def send_sms(phone_number, name, ticket_id):
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        'authorization': '0rE2PANavZsQgdnofKOMxJ4Ct8eXbYqmp1wulHS6iWIzkBULVyWIuA2CrMRU4fVZalOyTXbp1SNzYnFP',  # Replace with your Fast2SMS API key
        'sender_id': 'FSTSMS',
        'message': f'Dear {name}, your complaint has been received. Ticket ID: {ticket_id}',
        'language': 'english',
        'route': 'v3',
        'numbers': phone_number
    }

    headers = {
        'cache-control': "no-cache"
    }

    response = requests.get(url, headers=headers, params=payload)
    print(response.text)

# SendGrid email setup
SENDGRID_API_KEY = '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'  # Replace with your SendGrid API Key
sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)


app = Flask(__name__)




app.secret_key = 'kriyahackathon'  # Needed for session and flash messages





# Function to send email using Twilio SendGrid
def send_email(ticket_id, user_email):
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content

    try:
        from_email = Email("nammacityfix@gmail.com")  # Must be verified
        to_email = To(user_email)
        subject = "Complaint Received Successfully"
        content = Content("text/plain",
                          f"Thank you! Your complaint has been submitted.\n\n"
                          f"Your Ticket ID: {ticket_id}\n"
                          f"Use this ID to track your complaint.")

        mail = Mail(from_email, to_email, subject, content)
        mail.reply_to = Email("nammacityfix@gmail.com")

        # ✅ MAKE SURE the SendGrid client is initialized properly
        response = sendgrid_client.send(mail)

        print("✅ Email sent successfully!")
        print("Status Code:", response.status_code)

    except Exception as e:
        print("❌ Error sending email:", e)

def init_db():
    if not os.path.exists('users.db'):
        with sqlite3.connect('users.db') as conn:
            # Create users table
            conn.execute('''CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gov_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                designation TEXT NOT NULL,
                department TEXT NOT NULL,
                password TEXT NOT NULL
            )''')
            # Create extension_requests table
            conn.execute('''CREATE TABLE extension_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT,
                je_id INTEGER,
                reason TEXT,
                new_deadline DATE,
                requested_at DATETIME,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (complaint_id) REFERENCES complaints(ticket_id),
                FOREIGN KEY (je_id) REFERENCES users(user_id)
            )''')
            # Create complaints table
            conn.execute('''CREATE TABLE complaints (
                ticket_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                category TEXT NOT NULL,
                date DATE NOT NULL,
                description TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                expected_date TEXT, 
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to TEXT,
                resolved_image TEXT,
                priority TEXT DEFAULT 'medium'  -- ADDED THIS
            )''')

            print("Database initialized with 'users' and 'complaints' tables.")
    else:
        # If database exists, check if the 'status' column exists in 'complaints'
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            # Check if the 'status' column exists
            c.execute("PRAGMA table_info(complaints)")
            columns = [column[1] for column in c.fetchall()]
            
            # Add priority column if it doesn't exist
            if 'priority' not in columns:
                c.execute("ALTER TABLE complaints ADD COLUMN priority TEXT DEFAULT 'medium'")
                print("Added 'priority' column to 'complaints' table.")
            
            # Check if extension_requests table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_requests'")
            if not c.fetchone():
                conn.execute('''CREATE TABLE extension_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    complaint_id TEXT,
                    je_id INTEGER,
                    reason TEXT,
                    new_deadline DATE,
                    requested_at DATETIME,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (complaint_id) REFERENCES complaints(ticket_id),
                    FOREIGN KEY (je_id) REFERENCES users(user_id)
                )''')
                print("Created 'extension_requests' table.")
            
            # Check if status column exists (your existing check)
            if 'status' not in columns:
                c.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")
                print("Added 'status' column to 'complaints' table.")
            else:
                print("Database structure is up to date.")








import sqlite3

import sqlite3

@app.route('/')
def home():
    conn = sqlite3.connect('users.db')   # ✅ Correct DB file
    cur = conn.cursor()

    cur.execute("""
        SELECT address, COUNT(*) 
        FROM complaints 
        GROUP BY address 
        HAVING COUNT(*) >= 3
    """)
    
    hot_spots = cur.fetchall()
    print("Hot Spots:", hot_spots)  # Debugging line
    conn.close()

    return render_template('landing.html', hot_spots=hot_spots)




@app.route('/complain')
def complain():
    return render_template('raisecomplain.html')


@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/jeweb')
def jeweb():
    if 'user_id' not in session or session.get('user_designation') != 'JE':
        return redirect(url_for('login'))

    je_id = session['user_id']  # assuming you store user_id in session on login

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Get complaints assigned to this JE - FIXED QUERY
    # We need to convert je_id to string since assigned_to is TEXT
    c.execute("SELECT * FROM complaints WHERE assigned_to = ? AND status = 'In Progress'", (str(je_id),))
    pending_complaints = c.fetchall()

    # Get resolved complaints (optional)
    c.execute("SELECT * FROM complaints WHERE assigned_to = ? AND status = 'Resolved'", (str(je_id),))
    resolved_complaints = c.fetchall()

    conn.close()

    return render_template(
        'jeweb.html',
        pending_complaints=pending_complaints,
        resolved_complaints=resolved_complaints
    )



@app.route('/deptweb')
def deptweb():
    department = session.get('user_department')  # Department of the logged-in authority
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Fetch pending complaints that match the department's category - ORDER BY submitted_at DESC for newest first
    c.execute("SELECT * FROM complaints WHERE status = 'Pending' AND category = ? ORDER BY submitted_at DESC", (department,))
    pending_complaints = c.fetchall()

    # Fetch resolved complaints that match the department's category - ORDER BY submitted_at DESC for newest first
    c.execute("SELECT * FROM complaints WHERE status = 'Resolved' AND category = ? ORDER BY submitted_at DESC", (department,))
    resolved_complaints = c.fetchall()

    # Fetch JE users who belong to the same department as the logged-in user
    c.execute("SELECT * FROM users WHERE designation = 'JE' AND department = ?", (department,))
    je_list = c.fetchall()

    # In Progress complaints - ORDER BY submitted_at DESC for newest first
    c.execute("SELECT * FROM complaints WHERE status = 'In Progress' AND category = ? ORDER BY submitted_at DESC", (department,))
    in_progress_complaints = c.fetchall()

    # Fetch pending extension requests for this department
    c.execute("""
        SELECT er.id, er.complaint_id, u.name, er.reason, er.new_deadline, er.requested_at
        FROM extension_requests er
        JOIN complaints c ON er.complaint_id = c.ticket_id
        JOIN users u ON er.je_id = u.user_id
        WHERE er.status = 'pending' AND c.category = ?
        ORDER BY er.requested_at DESC
    """, (department,))
    extension_requests = c.fetchall()

    conn.close()
    
    return render_template('deptweb.html', 
                           pending_complaints=pending_complaints, 
                           resolved_complaints=resolved_complaints, 
                           je_list=je_list,
                           in_progress_complaints=in_progress_complaints,
                           extension_requests=extension_requests,
                           now_date=datetime.now().strftime("%Y-%m-%d"))
@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        gov_id = request.form['id']  # This is the govt-issued ID
        name = request.form['name']
        designation = request.form['designation']
        department = request.form['department']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            try:
                # Insert the new user into the database
                conn.execute("INSERT INTO users (gov_id, name, designation, department, password) VALUES (?, ?, ?, ?, ?)",
                             (gov_id, name, designation, department, password))
                conn.commit()

                # Get the user_id of the newly inserted user
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM users WHERE gov_id = ?", (gov_id,))
                user_id = cur.fetchone()[0]  # Fetch the user_id

                # Set session variables
                session['user_id'] = user_id
                session['user_name'] = name
                session['user_designation'] = designation
                session['user_department'] = department
                session['gov_id'] = gov_id

                flash("Signup successful!")

                # Redirect based on the designation
                if designation == 'Head':
                    return redirect(url_for('deptweb'))  # Redirect to Head dashboard
                elif designation == 'JE':
                    return redirect(url_for('jeweb'))  # Redirect to JE dashboard

            except sqlite3.IntegrityError:
                flash("Gov ID already exists. Please use a different one.")
                return redirect(url_for('auth'))

    return render_template('auth.html', action='signup')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        gov_id = request.form['id']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE gov_id=? AND password=?", (gov_id, password))
            user = cur.fetchone()

            if user:
                session['user_id'] = user[0]  # Add this!
                session['user_name'] = user[2]
                session['user_designation'] = user[3]
                session['user_department'] = user[4]
                session['gov_id'] = user[1]

                flash("Logged in successfully.")

                # Redirect based on the designation
                if user[3] == 'Head':
                    return redirect(url_for('deptweb'))  # Redirect to Head dashboard
                elif user[3] == 'JE':
                    return redirect(url_for('jeweb'))  # Redirect to JE dashboard
            else:
                flash("Invalid ID or password.")
                return redirect(url_for('auth'))

    return render_template('auth.html', action='login')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('auth'))

import random
import string

def generate_ticket_id():
    return 'TCKT' + ''.join(random.choices(string.digits, k=6))




import os
import sqlite3
import torch
from torchvision import transforms
from PIL import Image
from werkzeug.utils import secure_filename
from flask import request, redirect, url_for
from torchvision import models
import torch.nn as nn
import torch

# ----------------------------
# Load AI Model Once at Startup
# ----------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

import json
class_names=['electricity_dataset_pro', 'forest', 'garbage_dataset_pro',
               'infrastructure', 'potholes', 'sewage']


# Recreate the same architecture as in training
model = models.resnet18(pretrained=False)  # pretrained=False since we only load weights
num_features = model.fc.in_features
model.fc = nn.Sequential(
    nn.Linear(num_features, 256),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(256, len(class_names))  # class_names list must be defined
)

# Load trained weights
state_dict = torch.load("classifier_model.pth", map_location=device)
model.load_state_dict(state_dict) 

model = model.to(device)
model.eval()

# class names from your dataset
class_names = [
    'electricity_dataset_pro',
    'forest',
    'garbage_dataset_pro',
    'infrastructure',
    'potholes',
    'sewage'
]

# map predicted classes → actual departments
class_to_department = {
    'electricity_dataset_pro': "KPTCL (Electricity)",
    'forest': "Forest Department (Trees, Lakes, Parks)",
    'garbage_dataset_pro': "Health Department (Hospitals & Sanitation)",
    'infrastructure': "Town Planning Department (City Development)",
    'potholes': "PWD (Roads & Buildings)",
    'sewage': "KUWSDB (Water Supply & Drainage)"
}

# image preprocessing
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # adjust to model input size
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

def predict_department(image_path, threshold=0.6):  # default 60%
    image = Image.open(image_path).convert("RGB")
    
    # ✅ Apply same preprocessing as training
    transform_pipeline = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])
    
    img_tensor = transform_pipeline(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img_tensor)
        probs = torch.softmax(outputs, dim=1)  # convert logits → probabilities
        conf, predicted = torch.max(probs, 1)

    conf = conf.item()
    predicted_class = class_names[predicted.item()]

    # 🔴 Reject if below confidence threshold
    if conf < threshold:
        return f"⚠️ Invalid image. Please upload a valid civic issue picture. (Confidence {conf:.2f})"

    # ✅ Map predicted class → department
    return f"{class_to_department.get(predicted_class, 'Other Department')} (Confidence {conf:.2f})"


# Add jsonify to your imports from flask

from flask import Flask, request, redirect, url_for, render_template, jsonify

# ... keep all your other imports and model setup code ...



# ----------------------------

# 🔹 NEW: AI Analysis Route 🔹

# ----------------------------

@app.route('/analyze-image', methods=['POST'])

def analyze_image():

    """

    Receives an image, predicts the department, and returns it as JSON.

    This is called by JavaScript in the background.

    """

    if 'image' not in request.files:

        return jsonify({'error': 'No image file provided'}), 400



    image_file = request.files['image']



    # We need to save the file temporarily to pass its path to the predictor

    # You can also do this in-memory if you adapt the predict_department function

    temp_filename = secure_filename(image_file.filename)

    temp_path = os.path.join('static/uploads', temp_filename)

    image_file.save(temp_path)
    # Predict the department
    predicted_dept = predict_department(temp_path)
    # Clean up the temporary file
    os.remove(temp_path)
    # Return the prediction as JSON
    return jsonify({'department': predicted_dept})



# -----------------------------------------------------------------

# ✅ Your existing /subcomplaint route does NOT need any changes.

# It will receive the final department choice from the form submission.

# -----------------------------------------------------------------

# @app.route('/subcomplaint', methods=['POST'])

# def submit_complaint():

#    ... (keep this exactly as you have it) ...

# ----------------------------
# Your Route with AI Integration
# ----------------------------




@app.route('/subcomplaint', methods=['POST'])
def submit_complaint():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    category = request.form['category']
    date = request.form['date']
    description = request.form['description']
    latitude = request.form['latitude']
    longitude = request.form['longitude']
    address = request.form['address']

    image = request.files['image']
    image_filename = secure_filename(image.filename)
    image_path = os.path.join('static/uploads', image_filename)
    image.save(image_path)

    ai_department = predict_department(image_path)

    # 🔹 Use AI prediction instead of manual category
    # category = ai_department
    ticket_id = generate_ticket_id()

    # Save to database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT INTO complaints 
                 (ticket_id, name, phone, email, category, date, description, image_filename, latitude, longitude, address) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (ticket_id, name, phone, email, category, date, description, image_filename, latitude, longitude, address))
    conn.commit()
    conn.close()

    # send_sms(phone, name, ticket_id)
    send_email(ticket_id, email)  # Send email

    # Redirect to the thank you page with the ticket_id
    return redirect(url_for('thank_you', ticket_id=ticket_id))


@app.route('/thankyou/<ticket_id>')
def thank_you(ticket_id):
    # Fetch the name of the user (optional)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name FROM complaints WHERE ticket_id = ?', (ticket_id,))
    name = c.fetchone()[0]
    conn.close()

    return render_template("thankyou.html", name=name, ticket_id=ticket_id)


@app.route('/track', methods=['GET'])
def track():
    return render_template('track.html')



@app.route('/trackcomplaint', methods=['POST'])
def trackcomplaint():
    ticket_id = request.json.get('ticket_id')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM complaints WHERE ticket_id = ?", (ticket_id,))
    complaint = c.fetchone()
    conn.close()

    if complaint:
        return jsonify({
            "success": True,
            "ticket_id": complaint[0],
            "name": complaint[1],
            "email": complaint[3],
            "phone": complaint[2],
            "category": complaint[4],
            "description": complaint[6],
            "location": complaint[10],
            "status": complaint[11],
            "expected_resolution": complaint[12],
            "image": complaint[7]
        })
    else:
        return jsonify({"success": False, "message": "Invalid Ticket ID"})


@app.route('/assign_complaint/<string:ticket_id>', methods=['POST'])
def assign_complaint(ticket_id):
    if 'user_id' not in session or session.get('user_designation') != 'Department Head':
        return redirect(url_for('login'))
    
    assigned_to = request.form.get('assigned_to')
    expected_date = request.form.get('expected_date')
    priority = request.form.get('priority', 'medium')  # Get priority from form
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # First, get the JE's name for display purposes
    c.execute("SELECT name FROM users WHERE user_id = ?", (assigned_to,))
    je_info = c.fetchone()
    je_name = je_info[0] if je_info else ""
    
    # Update complaint with priority and assign to JE
    c.execute("""
        UPDATE complaints 
        SET status = 'In Progress', 
            assigned_to = ?, 
            assigned_to_name = ?,
            expected_date = ?,
            priority = ?
        WHERE ticket_id = ? AND status = 'Pending'
    """, (assigned_to, je_name, expected_date, priority, ticket_id))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('deptweb'))

 # Optional if you want to show alerts

@app.route('/request_extension/<string:ticket_id>', methods=['POST'])
def request_extension(ticket_id):
    if 'user_id' not in session or session.get('user_designation') != 'JE':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    reason = data.get('reason')
    new_deadline = data.get('new_deadline')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Create extension request
    c.execute("""
        INSERT INTO extension_requests (complaint_id, je_id, reason, new_deadline, requested_at)
        VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, session['user_id'], reason, new_deadline, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/handle_extension/<int:request_id>/<string:action>', methods=['POST'])
def handle_extension(request_id, action):
    if 'user_id' not in session or session.get('user_designation') != 'Department Head':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    if action == 'approve':
        # Get the extension request
        c.execute("SELECT complaint_id, new_deadline FROM extension_requests WHERE id = ?", (request_id,))
        req = c.fetchone()
        
        if req:
            complaint_id, new_deadline = req
            # Update complaint deadline
            c.execute("UPDATE complaints SET expected_date = ? WHERE ticket_id = ?", (new_deadline, complaint_id))
        
        # Update extension request status
        c.execute("UPDATE extension_requests SET status = 'approved' WHERE id = ?", (request_id,))
    
    elif action == 'reject':
        # Update extension request status
        c.execute("UPDATE extension_requests SET status = 'rejected' WHERE id = ?", (request_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

from flask import Flask, request, redirect, url_for, session, flash

@app.route('/resolve_complaint/<ticket_id>', methods=['POST'])
def resolve_complaint(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get the uploaded file
    resolved_image = request.files.get('resolved_image')
    if resolved_image:
        filename = secure_filename(resolved_image.filename)
        filepath = os.path.join('static', 'uploads', filename)
        resolved_image.save(filepath)

        # Update the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE complaints SET status = 'Resolved', resolved_image = ? WHERE ticket_id = ?", (filename, ticket_id))
        conn.commit()
        conn.close()

        # Redirect back to JE dashboard to refresh data
        return redirect(url_for('jeweb'))

    return "Image not uploaded", 400
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT gov_id, name, designation, department, password FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        return render_template('profile.html',
                               gov_id=user[0],
                               name=user[1],
                               designation=user[2],
                               department=user[3],
                               password=user[4])
    else:
        flash("User not found.")
        return redirect(url_for('login'))


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()

    new_name = data.get("name")
    new_designation = data.get("designation")
    new_department = data.get("department")
    new_password = data.get("password")

    user_id = session['user_id']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    update_fields = []
    update_values = []

    if new_name:
        update_fields.append("name = ?")
        update_values.append(new_name)
    if new_designation:
        update_fields.append("designation = ?")
        update_values.append(new_designation)
    if new_department:
        update_fields.append("department = ?")
        update_values.append(new_department)
    if new_password:
        update_fields.append("password = ?")
        update_values.append(new_password)

    update_values.append(user_id)

    query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
    c.execute(query, tuple(update_values))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Profile updated successfully!"})

@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")

from datetime import datetime, timedelta
from flask import render_template, session, redirect, url_for, jsonify
import sqlite3
@app.route('/dashboard')
def dashboard():
    department = session.get('user_department')
    if not department:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # ---- Top cards
    c.execute("SELECT COUNT(*) FROM complaints WHERE category = ?", (department,))
    total_count = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending' AND category = ?", (department,))
    pending_count = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress' AND category = ?", (department,))
    inprogress_count = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved' AND category = ?", (department,))
    resolved_count = c.fetchone()[0] or 0

    # ---- Time-series: last 30 days (by submitted_at date)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)
    c.execute("""
        SELECT DATE(submitted_at) as d, COUNT(*)
        FROM complaints
        WHERE category = ?
          AND DATE(submitted_at) BETWEEN ? AND ?
        GROUP BY DATE(submitted_at)
        ORDER BY DATE(submitted_at)
    """, (department, start_date.isoformat(), today.isoformat()))
    rows = c.fetchall()
    counts_by_date = {r[0]: r[1] for r in rows}

    dates_30 = [(start_date + timedelta(days=i)).isoformat() for i in range(30)]
    series_30 = [counts_by_date.get(d, 0) for d in dates_30]

    # ---- JE performance (per assigned_to)
    # label = JE name if available, else assigned_to id, else "Unassigned"
    c.execute("""
        SELECT COALESCE(u.name, c.assigned_to, 'Unassigned') AS label,
               SUM(CASE WHEN c.status='Pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN c.status='In Progress' THEN 1 ELSE 0 END) AS inprogress,
               SUM(CASE WHEN c.status='Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints c
        LEFT JOIN users u ON u.gov_id = c.assigned_to
        WHERE c.category = ?
        GROUP BY label
        ORDER BY resolved DESC, pending DESC
    """, (department,))
    je_rows = c.fetchall()
    je_labels = [r[0] for r in je_rows]
    je_pending = [r[1] for r in je_rows]
    je_inprogress = [r[2] for r in je_rows]
    je_resolved = [r[3] for r in je_rows]

    # ---- Map points (limit to 200 newest for performance)
    c.execute("""
        SELECT ticket_id, latitude, longitude, status, address
        FROM complaints
        WHERE category = ?
        ORDER BY submitted_at DESC
        LIMIT 200
    """, (department,))
    map_points = [
        {
            "ticket_id": row[0],
            "lat": row[1],
            "lng": row[2],
            "status": row[3],
            "address": row[4]
        }
        for row in c.fetchall()
    ]

    conn.close()

    return render_template(
        "dashboard.html",
        department=department,
        total_count=total_count,
        pending_count=pending_count,
        inprogress_count=inprogress_count,
        resolved_count=resolved_count,
        dates_30=dates_30,
        series_30=series_30,
        je_labels=je_labels,
        je_pending=je_pending,
        je_inprogress=je_inprogress,
        je_resolved=je_resolved,
        map_points=map_points
    )
    
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    
