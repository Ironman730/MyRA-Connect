from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///one_to_one_chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  
app.secret_key = 'supersecretkey'

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

# Message Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Pre-registered users
pre_registered_users = [
    {"username": "Adil", "password": "12345"},
    {"username": "Pavan", "password": "11111"},
    {"username": "Bobby", "password": "22222"},
    {"username": "Avinash", "password": "33333"}
]

@app.before_request
def setup():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  
    for user in pre_registered_users:
        if not User.query.filter_by(username=user['username']).first():
            db.session.add(User(username=user['username'], password=user['password']))
    db.session.commit()

# Home Route
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat.html'))
    return render_template('login.html')

# Login Route (Handles both Form and JSON Requests)
@app.route('/login', methods=['POST'])
def login():
    if request.is_json:  # JSON Request (AJAX, Fetch)
        data = request.json
        username = data.get('username')
        password = data.get('password')
    else:  # Form Request (Traditional HTML form)
        username = request.form.get('username')
        password = request.form.get('password')

    print(f"Received login data: username={username}, password={password}")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['username'] = user.username
        return jsonify({"message": "Login successful"}), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

# Logout Route
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Chat Page
@app.route('/chat.html')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    users = User.query.filter(User.username != session['username']).all()
    current_user = User.query.filter_by(username=session['username']).first()
    return render_template('chat.html', users=users, current_user=current_user)

# Get Conversation
@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    sender_username = session['username']
    receiver_username = request.args.get('receiver')

    if not receiver_username:
        return jsonify({"error": "Invalid data"}), 400

    sender = User.query.filter_by(username=sender_username).first()
    receiver = User.query.filter_by(username=receiver_username).first()

    if not sender or not receiver:
        return jsonify({"error": "User not found"}), 404

    messages = Message.query.filter(
        ((Message.sender_id == sender.id) & (Message.receiver_id == receiver.id)) |
        ((Message.sender_id == receiver.id) & (Message.receiver_id == sender.id))
    ).order_by(Message.timestamp).all()

    return jsonify([
        {
            "sender": User.query.get(msg.sender_id).username,
            "receiver": User.query.get(msg.receiver_id).username,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        } for msg in messages
    ])

# Send Message
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    receiver_username = data.get('receiver')
    content = data.get('content')

    if not receiver_username or not content:
        return jsonify({"error": "Invalid data"}), 400

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.filter_by(username=receiver_username).first()

    if not sender or not receiver:
        return jsonify({"error": "User not found"}), 404

    message = Message(sender_id=sender.id, receiver_id=receiver.id, content=content)
    db.session.add(message)
    db.session.commit()

    return jsonify({"message": "Message sent successfully"}), 201

# Signup Route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if User.query.filter_by(username=email).first():
        return jsonify({"message": "Failed to register user"}), 201  # Silent rejection

    new_user = User(username=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
