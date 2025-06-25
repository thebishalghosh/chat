from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the DATABASE_URL environment variable (from Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Create messages table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    ''')
    # Create user_message_reads table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_message_reads (
            user_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, message_id),
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized or already exists.")

# Initialize DB once immediately on startup
init_db()

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    username = data.get('username')
    message = data.get('message')
    if not username or not message:
        logger.warning("Missing username or message in request")
        return jsonify({'success': False, 'error': 'Username and message required'}), 400
    timestamp = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO messages (username, message, timestamp) VALUES (%s, %s, %s) RETURNING id;',
        (username, message, timestamp)
    )
    msg_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Message inserted with id {msg_id} from user {username}")
    return jsonify({'success': True, 'message': {'id': msg_id, 'username': username, 'message': message, 'timestamp': timestamp}})

@app.route('/messages', methods=['GET'])
def get_messages():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username, message, timestamp FROM messages ORDER BY id ASC')
    messages = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({'messages': messages})

@app.route('/unread')
def unread_count():
    username = request.args.get('user')
    if not username:
        return jsonify({'unread_count': 0})

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM messages m
        WHERE m.username != %s
        AND NOT EXISTS (
            SELECT 1 FROM user_message_reads r
            WHERE r.user_id = %s AND r.message_id = m.id
        )
    ''', (username, username))
    count = cur.fetchone()['count']
    cur.close()
    conn.close()
    return jsonify({'unread_count': count})

@app.route('/mark_read', methods=['POST'])
def mark_read():
    data = request.get_json()
    user = data.get('user')
    message_ids = data.get('message_ids', [])

    if not user or not message_ids:
        return jsonify({'success': False, 'error': 'User and message_ids required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    for msg_id in message_ids:
        cur.execute('''
            INSERT INTO user_message_reads (user_id, message_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        ''', (user, msg_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
