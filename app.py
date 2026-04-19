import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# แยกชุดข้อมูลเพื่อให้เงื่อนไขไม่ซ้ำซ้อนกันเกินไป
TOPICS_COL = ["ผมขาว", "ผมทอง", "ผมดำ", "ผมแดง", "ผมฟ้า", "ใส่หน้ากาก", "ใส่หมวก", "ใส่สูท", "ปิดตาข้างเดียว"]
TOPICS_ROW = ["ค่าย MAPPA", "ค่าย Ufotable", "ต่างโลก", "ใช้ดาบ", "พลังไฟ", "นินจา", "โจรสลัด", "นักเรียน", "ตัวร้าย"]

game_state = {
    "col_headers": [], # สำหรับแนวตั้ง (แกน X)
    "row_headers": [], # สำหรับแนวนอน (แกน Y)
    "claimed": {},
    "players": {},
    "reset_votes": set(),
    "current_turn_idx": 0,
    "player_order": []
}

# ฟังก์ชันสุ่มโจทย์แยกแกน [ตาม Logic ที่คุณต้องการ]
def generate_new_matrix():
    game_state["col_headers"] = random.sample(TOPICS_COL, 5)
    game_state["row_headers"] = random.sample(TOPICS_ROW, 5)
    game_state["claimed"] = {}
    game_state["reset_votes"] = set()

# สุ่มครั้งแรกทันทีที่รันเซิร์ฟเวอร์
generate_new_matrix()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_game')
def handle_join(data):
    name = data.get('name', 'Anonymous')
    game_state["players"][request.sid] = {"name": name, "hearts": 3}
    if name not in game_state["player_order"]:
        game_state["player_order"].append(name)
    
    # ส่งหัวข้อ Col และ Row แยกกันไปให้ Client
    emit('game_started', {
        "col_headers": game_state["col_headers"],
        "row_headers": game_state["row_headers"],
        "claimed": game_state["claimed"]
    })
    emit('update_game_info', {
        "players": list(game_state["players"].values()),
        "player_order": game_state["player_order"],
        "current_turn": game_state["current_turn_idx"]
    }, broadcast=True)

@socketio.on('vote_reset')
def handle_vote():
    game_state["reset_votes"].add(request.sid)
    total = len(game_state["players"])
    if total > 0 and (len(game_state["reset_votes"]) / total) >= 0.75:
        generate_new_matrix()
        for p in game_state["players"].values(): p["hearts"] = 3
        emit('game_started', game_state, broadcast=True)

@socketio.on('claim_slot')
def handle_claim(data):
    # data ประกอบด้วย slot_id (เช่น "0-2"), name, img
    game_state["claimed"][data['slot_id']] = data
    game_state["current_turn_idx"] = (game_state["current_turn_idx"] + 1) % len(game_state["player_order"])
    emit('slot_claimed', {"data": data, "next_turn": game_state["current_turn_idx"]}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)