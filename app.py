from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'animebingo_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

ANIME_PROMPTS = [
    "ผมขาว", "ผมทอง", "ต่างโลก", "ย้อนเวลา", "ฆ่าตัวตาย",
    "ค่าย MAPPA", "ค่าย Ufotable", "ค่าย Bones", "ค่าย Madhouse", "ค่าย A-1 Pictures",
    "ตายตอนจบ", "Happy Ending", "Sad Ending", "Bitter Ending", "Open Ending",
    "ตัวเอกผมแปลก", "ตัวเอกผมขาว", "ตัวเอกผมดำ", "ตัวเอกผมแดง", "ตัวเอกผมฟ้า",
    "Ninja", "Samurai", "Pirate", "Wizard", "Knight",
    "Isekai", "Mecha", "Shoujo", "Shounen", "Seinen",
    "Otaku", "Chuunibyou", "Tsundere", "Yangire", "Yandere",
    "ศิษย์เก่ง", "ศิษย์ใหม่", "ครู", "ผู้อาวุโส", "เด็กกำพร้า",
    "พี่น้องต่างแม่", "พี่น้องต่างพ่อ", "เพื่อนสนิท", "คู่แข่ง", "คู่กรณี",
    "ลุคหมวก", "ลุคหน้ากาก", "ลุคตาบอด", "ลุคหูหนวก", "ลุคพิการ",
    "พลังเวทย์", "พลังจิต", "พลังกาย", "พลังสติ", "พลังใจ",
    "มังงะ", "ชิโตะบุจิ", "ลายเรน", "บอมเบอร์", "กันดั้ม"
]

claimed_slots = {}

@socketio.on('start_game')
def handle_start_game():
    selected = random.sample(ANIME_PROMPTS, 25)
    global claimed_slots
    claimed_slots = {}
    for i in range(25):
        claimed_slots[i] = None
    emit('game_started', {'prompts': selected, 'claimed': claimed_slots}, broadcast=True)

@socketio.on('claim_slot')
def handle_claim_slot(data):
    index = data.get('index')
    answer = data.get('answer')
    user = data.get('user')
    image_url = data.get('image_url')
    
    if index is None or user is None:
        return
    
    if index in claimed_slots and claimed_slots[index] is not None:
        emit('slot_already_claimed', {'index': index})
        return
    
    claimed_slots[index] = {
        'answer': answer if answer else '',
        'user': user,
        'image_url': image_url if image_url else ''
    }
    emit('slot_claimed', {
        'index': index,
        'answer': answer if answer else '',
        'user': user,
        'image_url': image_url if image_url else ''
    }, broadcast=True)

@socketio.on('reset_game')
def handle_reset_game():
    global claimed_slots
    claimed_slots = {}
    for i in range(25):
        claimed_slots[i] = None
    emit('game_reset', broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)