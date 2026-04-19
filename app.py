import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'anime_bingo_v7_final'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# สีประจำตัวผู้เล่นที่แตกต่างกันชัดเจน
PLAYER_COLORS = ["#FF4757", "#2ED573", "#1E90FF", "#ECCC68", "#A55EEA", "#FFA502", "#70A1FF", "#7BED9F"]

TOPICS_SIDE = ["ค่าย MAPPA", "ค่าย Ufotable", "ผมขาว", "ผมแดง", "ใส่หน้ากาก", "ผมทอง", "ตัวเอก", "ต่างโลก"]
TOPICS_TOP = ["เป็นโจรสลัด", "ใช้ดาบ", "พลังไฟ", "ตลก", "ตายตอนจบ", "เก่งเกินไป", "ใส่หมวก", "นินจา"]

game_state = {
    "col_headers": random.sample(TOPICS_TOP, 5),
    "row_headers": random.sample(TOPICS_SIDE, 5),
    "claimed": {}, # { "r-c": { img, name, sid, color, disputes } }
    "players": {}, 
    "player_order": [],
    "current_turn_idx": 0
}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    if sid not in game_state["players"]:
        assigned_color = PLAYER_COLORS[len(game_state["players"]) % len(PLAYER_COLORS)]
        game_state["players"][sid] = {
            "name": data.get('name', 'Player'),
            "color": assigned_color,
            "hearts": 3
        }
        game_state["player_order"].append(sid)
    
    emit('game_started', {
        "col_headers": game_state["col_headers"],
        "row_headers": game_state["row_headers"],
        "claimed": game_state["claimed"]
    })
    update_ui()

@socketio.on('sync_temp_move')
def handle_temp_move(data):
    sid = request.sid
    if sid in game_state["player_order"] and game_state["player_order"][game_state["current_turn_idx"]] == sid:
        color = game_state["players"][sid]["color"]
        emit('player_moving', {**data, "color": color} if data else None, broadcast=True, include_self=False)

@socketio.on('confirm_final_claim')
def handle_confirm(data):
    sid = request.sid
    if game_state["player_order"][game_state["current_turn_idx"]] != sid:
        return
    
    game_state["claimed"][data['slot_id']] = {
        "img": data['img'],
        "name": data['name'],
        "sid": sid,
        "color": game_state["players"][sid]["color"],
        "disputes": []
    }
    
    game_state["current_turn_idx"] = (game_state["current_turn_idx"] + 1) % len(game_state["player_order"])
    emit('slot_locked', {**data, "sid": sid, "color": game_state["players"][sid]["color"]}, broadcast=True)
    update_ui()

@socketio.on('vote_dispute')
def handle_vote(data):
    voter_sid = request.sid
    slot_id = data.get('slot_id')
    if slot_id in game_state["claimed"]:
        target = game_state["claimed"][slot_id]
        if target['sid'] != voter_sid and voter_sid not in target['disputes']:
            target['disputes'].append(voter_sid)
            # แจ้งเตือนเมื่อมีการโหวตค้าน
            emit('dispute_update', {"slot_id": slot_id, "count": len(target['disputes'])}, broadcast=True)

@socketio.on('skip_turn')
def handle_skip():
    sid = request.sid
    if game_state["player_order"][game_state["current_turn_idx"]] == sid:
        game_state["players"][sid]["hearts"] -= 1
        game_state["current_turn_idx"] = (game_state["current_turn_idx"] + 1) % len(game_state["player_order"])
        update_ui()

def update_ui():
    emit('update_game_state', {
        "players": game_state["players"],
        "order": game_state["player_order"],
        "turn": game_state["current_turn_idx"]
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)