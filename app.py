from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.before_first_request
def setup():
    init_db()

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    username = data.get('username')
    message = data.get('message')
    if not username or not message:
        return jsonify({'success': False, 'error': 'Username and message required'}), 400
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)', (username, message, timestamp))
        conn.commit()
        msg_id = c.lastrowid
    return jsonify({'success': True, 'message': {'id': msg_id, 'username': username, 'message': message, 'timestamp': timestamp}})

@app.route('/messages', methods=['GET'])
def get_messages():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, message, timestamp FROM messages ORDER BY id ASC')
        rows = c.fetchall()
        messages = [{'id': row[0], 'username': row[1], 'message': row[2], 'timestamp': row[3]} for row in rows]
    return jsonify({'messages': messages})

if __name__ == '__main__':
    app.run(debug=True) 