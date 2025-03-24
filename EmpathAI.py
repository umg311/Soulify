# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from openai import OpenAI
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask and SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///empathai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    conversations = db.relationship('Conversation', backref='user', lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    topic = db.Column(db.String(200))
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(500))  # Store tags as comma-separated string
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Configure OpenAI with environment variable (more secure)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        return jsonify({'message': 'Signup successful'})
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return jsonify({'message': 'Login successful', 'redirect': '/dashboard'})
        
        return jsonify({'error': 'Invalid username or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/conversations', methods=['GET'])
def get_conversations():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
        
    conversations = Conversation.query.filter_by(user_id=session['user_id']).all()
    return jsonify({
        'conversations': [{
            'id': c.id,
            'timestamp': c.timestamp.isoformat(),
            'topic': c.topic,
            'messages': [{
                'role': m.role,
                'content': m.content,
                'timestamp': m.timestamp.isoformat()
            } for m in c.messages]
        } for c in conversations]
    })

@app.route('/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Delete all messages first
        Message.query.filter_by(conversation_id=conversation_id).delete()
        # Then delete the conversation
        db.session.delete(conversation)
        db.session.commit()
        return jsonify({'message': 'Conversation deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete conversation'}), 500

@app.route('/conversations/<int:conversation_id>/topic', methods=['PUT'])
def update_conversation_topic(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    new_topic = request.json.get('topic')
    if not new_topic:
        return jsonify({'error': 'No topic provided'}), 400
    
    try:
        conversation.topic = new_topic
        db.session.commit()
        return jsonify({'message': 'Topic updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update topic'}), 500

# Initialize user sessions
@app.before_request
def before_request():
    # Only initialize conversation history
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    
    # Protect all routes except login, signup, and static files
    if request.endpoint and request.endpoint not in ['login', 'signup', 'static'] and \
       not isinstance(session.get('user_id'), int):
        if request.is_json:
            return jsonify({'error': 'Please login first'}), 401
        return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/chat')
def chat_page():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/facial-detection')
def facial_detection():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return render_template('facial_detection.html')

@app.route('/mental-wellness')
def mental_wellness():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return render_template('mental_wellness.html')

@app.route('/balloon-game')
def balloon_game():
    if 'user_id' not in session or not isinstance(session['user_id'], int):
        return redirect(url_for('login'))
    return render_template('balloon_game.html')

def generate_topic(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a topic generator. Generate a brief, empathetic topic (4-6 words) for a mental health conversation based on the user's first message. The topic should be specific to their situation but respectful and supportive. Respond with ONLY the topic, no other text."},
                {"role": "user", "content": message}
            ],
            max_tokens=20
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating topic: {str(e)}")
        return "General Discussion"

def should_update_topic(conversation, new_message):
    try:
        # Get the last few messages for context
        recent_messages = [msg.content for msg in conversation.messages[-2:]]
        recent_messages.append(new_message)
        
        # If this is the second message and it's different from the greeting, update topic
        if len(conversation.messages) == 1 and "hello" not in new_message.lower():
            return True
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a topic change detector. Your task is to detect ANY significant change in the conversation's emotional tone or subject matter. Be especially sensitive to mentions of mental health issues, personal struggles, or emotional states. Respond with 'YES' if there's ANY meaningful change in the topic or emotional content, 'NO' otherwise. Examples of when to respond YES:
                - User mentions a specific problem or struggle
                - User's emotional state changes
                - User brings up a new aspect of their situation
                - User moves from general greetings to specific issues"""},
                {"role": "user", "content": f"Current topic: {conversation.topic}\nConversation context: {' | '.join(recent_messages)}\nDoes this conversation need a new topic?"}
            ],
            max_tokens=10
        )
        return response.choices[0].message.content.strip().upper() == 'YES'
    except Exception as e:
        print(f"Error checking topic change: {str(e)}")
        return False

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
        
    user_message = request.json.get('message', '')
    conversation_id = request.json.get('conversation_id')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get or create conversation
    if not conversation_id:
        conversation = Conversation(user_id=session['user_id'])
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id
        
        # Generate topic for new conversation
        topic = generate_topic(user_message)
        conversation.topic = topic
        db.session.commit()
    else:
        conversation = Conversation.query.get(conversation_id)
        if not conversation or conversation.user_id != session['user_id']:
            return jsonify({'error': 'Invalid conversation'}), 403
        
        # Check if topic should be updated
        if len(conversation.messages) > 0 and should_update_topic(conversation, user_message):
            new_topic = generate_topic(user_message)
            if new_topic != conversation.topic:  # Only update if topic is different
                conversation.topic = new_topic
                db.session.commit()
    
    # Get previous messages for context
    previous_messages = [{"role": m.role, "content": m.content} for m in conversation.messages]
    
    # Save user message
    message = Message(
        conversation_id=conversation_id,
        role='user',
        content=user_message
    )
    db.session.add(message)
    
    try:
        # Get response from OpenAI using new API format
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a supportive AI health assistant. Respond with empathy and provide helpful mental health advice when appropriate. Always prioritize user safety. Follow these guidelines for all responses:
    1. Use clear paragraph breaks for readability
    2. Use bullet points or numbered lists when providing steps or multiple pieces of advice
    3. Format your responses with appropriate headers when relevant
    4. Keep paragraphs concise and focused
    5. Use empathetic language and maintain a supportive tone
    6. When providing advice (only if the situation requires it), structure it clearly with:
       - Initial validation/acknowledgment
       - Specific suggestions
       - Actionable next steps
       - Supportive closing statement
    7. Always prioritize user safety and well-being
    8. If discussing serious issues, include appropriate resources or professional help recommendations
    9. Never repeat your greeting if you've already greeted the user
    10. If the user mentions a specific issue, address it directly
    11. Avoid using markdown formatting symbols like #, *, or ` in your responses as they won't display correctly."""},
                *previous_messages,
                {"role": "user", "content": user_message}
            ]
        )
        
        ai_message = response.choices[0].message.content
        
        # Save AI message
        message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=ai_message
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'message': ai_message,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to get response from AI', 'details': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    session['conversation_history'] = []
    return jsonify({'status': 'conversation reset'})

# Routes for future features
@app.route('/journal', methods=['GET', 'POST'])
def journal():
    # Placeholder for journal feature
    return jsonify({'status': 'feature not implemented yet'})

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    # Placeholder for computer vision analysis
    return jsonify({'status': 'feature not implemented yet'})

@app.route('/activities', methods=['GET'])
def get_activities():
    # Placeholder for coping activities recommendations
    return jsonify({'status': 'feature not implemented yet'})

@app.route('/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    user = User.query.get(session['user_id'])
    return jsonify({'username': user.username})

@app.route('/journal/entries', methods=['GET'])
def get_journal_entries():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    entries = JournalEntry.query.filter_by(user_id=session['user_id']).order_by(JournalEntry.created_at.desc()).all()
    return jsonify({
        'entries': [{
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'mood': entry.mood,
            'tags': entry.tags.split(',') if entry.tags else [],
            'created_at': entry.created_at.isoformat(),
            'updated_at': entry.updated_at.isoformat()
        } for entry in entries]
    })

@app.route('/journal/entry', methods=['POST'])
def create_journal_entry():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    entry = JournalEntry(
        user_id=session['user_id'],
        title=data.get('title', 'Untitled'),
        content=data.get('content', ''),
        mood=data.get('mood'),
        tags=','.join(data.get('tags', []))
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({
        'message': 'Entry created successfully',
        'entry_id': entry.id
    })

@app.route('/journal/entry/<int:entry_id>', methods=['PUT'])
def update_journal_entry(entry_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    entry = JournalEntry.query.get_or_404(entry_id)
    if entry.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    entry.title = data.get('title', entry.title)
    entry.content = data.get('content', entry.content)
    entry.mood = data.get('mood', entry.mood)
    entry.tags = ','.join(data.get('tags', entry.tags.split(',') if entry.tags else []))
    
    db.session.commit()
    return jsonify({'message': 'Entry updated successfully'})

@app.route('/journal/entry/<int:entry_id>', methods=['DELETE'])
def delete_journal_entry(entry_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    entry = JournalEntry.query.get_or_404(entry_id)
    if entry.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Entry deleted successfully'})

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Check if we're in production mode
    is_production = os.environ.get('PRODUCTION', 'false').lower() == 'true'
    
    if is_production:
        # Production settings
        app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', 'localhost:5000')
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        # Ensure the database is created
        with app.app_context():
            db.create_all()
        # Run with production server
        app.run(
            host='0.0.0.0',  # Listen on all available interfaces
            port=int(os.environ.get('PORT', 5000)),
            debug=False  # Disable debug mode in production
        )
    else:
        # Development settings
        app.run(debug=True)