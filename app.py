import logging
import random
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from server.event_bus import EventBus
from server.player_session import PlayerSessionManager

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'anime_bingo_v7_final'
socketio = SocketIO(app, cors_allowed_origins='*', ping_timeout=60, ping_interval=25)

PLAYER_COLORS = [
    '#FF4757', '#2ED573', '#1E90FF', '#ECCC68', '#A55EEA', '#FFA502', '#70A1FF', '#7BED9F'
]

# Conflict topics to prevent overlapping
TOPIC_CONFLICTS = {
    'เป็นฮีโร่': ['เป็นตัวร้าย'],
    'เป็นนักเรียน': ['เป็นครู', 'เป็นอาจารย์'],
    'เป็นทหาร': ['เป็นโจร'],
    'เป็นครึ่งมนุษย์': ['เป็นสัตว์'],
    'ตัวสูง': ['ตัวเตี้ย'],
    'ผอม': ['กล้าม'],
    'ผมดำ': ['ผมขาว', 'ผมทอง', 'ผมชมพู', 'ผมเขียว', 'ผมม่วง', 'ผมฟ้า', 'ผมสีแดง'],
    'อยู่ในโลกอนาคต': ['อยู่ในโลกปัจจุบัน', 'อยู่ในโลกแฟนตาซี', 'อยู่ในโลกยุคน้ำแข็ง'],
    'พูดไม่ได้': ['พูดมาก'],
    'เป็นเทพเจ้า': ['เป็นโจร', 'เป็นนักลอบสังหาร'],
    'ถือดาบใหญ่': ['ใช้มีด', 'ใช้ปืน'],
    'เด็ก': ['เป็นอาจารย์', 'เป็นหัวหน้าแก๊ง']
}

def get_non_conflicting_topics(avoid_top=None, avoid_side=None):
    available_top = list(TOPICS_TOP)
    available_side = list(TOPICS_SIDE)
    
    # ลดโอกาสซ้ำโดยลบ headers ที่เคยใช้ล่าสุดออกก่อน (แต่ยังเหลือให้สุ่มได้)
    if avoid_top:
        for t in avoid_top[:3]:  # หลีกเลี่ยง 3 อันล่าสุด
            if t in available_top and len(available_top) > 3:
                available_top.remove(t)
    if avoid_side:
        for t in avoid_side[:3]:
            if t in available_side and len(available_side) > 3:
                available_side.remove(t)
    
    selected_top = []
    selected_side = []
    
    while len(selected_top) < 5 and available_top:
        topic = random.choice(available_top)
        available_top.remove(topic)
        
        conflicts = TOPIC_CONFLICTS.get(topic, [])
        can_add = True
        for selected in selected_top:
            if selected in conflicts:
                can_add = False
                break
        
        if can_add:
            selected_top.append(topic)
    
    while len(selected_side) < 5 and available_side:
        topic = random.choice(available_side)
        available_side.remove(topic)
        
        can_add = True
        for selected in selected_top:
            if selected in TOPIC_CONFLICTS.get(topic, []):
                can_add = False
                break
        
        if can_add:
            selected_side.append(topic)
    
    return selected_top, selected_side
TOPICS_SIDE = [
    'ผมดำ', 'ผมฟ้า', 'ผม���่วง', 'ผมเขียว', 'ผมชมพู', 'ผมขาว', 'ผมทอง', 'ผมสีแดง',
    'ผมสองสี', 'ผมยาวถึงพื้น', 'ผมสั้นเกรียน',
    'ตาสีแดง', 'ตาสีทอง', 'ตาสองสี', 'ตาปิดข้างเดียว', 'ดวงตาไร้แวว', 'ดวงตาเรืองแสง',
    'ใส่ผ้าปิดตา', 'ใส่หูฟัง', 'ใส่ถุงมือ', 'ใส่รองเท้าบูท',
    'ใส่ชุดเกราะ', 'ใส่สูท', 'ใส่ชุดแฟนตาซี', 'ใส่กิโมโน', 'ใส่ชุดจีน',
    'ใส่ชุดโกธิค', 'ใส่เสื้อคลุมยาว', 'ใส่เกราะครึ่งตัว',
    'ตัวสูง', 'ตัวเตี้ย', 'กล้าม', 'ผอม', 'ผิวสีแทน', 'ผิวซีด',
    'มีเขา', 'มีปีก', 'มีหาง', 'มีเขี้ยว', 'มีหูสัตว์',
    'มีรอยสัก', 'มีแผลเป็น', 'มีแผลเป็นตามตัว', 'มีผ้าพันแผลตามตัว',
    'ใส่แว่น', 'ใส่หมวกคลุม', 'ใส่ฮู้ด', 'ใส่หน้ากาก', 
    'ถือดาบใหญ่', 'ใช้ปืน', 'ถือคทา', 'ถือโล่',
    'ใช้ธนู', 'ใช้มีด', 'ใช้เคียว', 'ใช้กรงเล็บ', 'ใช้โซ่', 'ใช้ขวานยักษ์',
    'มีสัตว์เลี้ยง', 'มีมาสคอต', 'มีหุ่นยนต์คู่หู', 'มีวิญญาณตามติด',
    'ใส่เครื่องแบบทหาร', 'ใส่ชุดนักเรียนหญิง', 'ใส่ชุดนักเรียนชาย',
    'ใส่ชุดแม่บ้าน', 'ใส่ชุดไอดอล', 'ใส่ชุดนักบวช',
    'มีพลังออร่ารอบตัว', 'ลอยตัวบนอากาศ', 'มีแขนขาจักรกล',
    'มีอัญมณีตามตัว', 'ดวงตาเรืองแสง',
    'ร่างกายมีไอเย็น', 'ร่างกายมีเปลวไฟ',
    'มีเสียงพูดแปลก', 'พูดไม่ได้', 'พูดน้อย', 'พูดมาก',
    'ชอบยิ้ม', 'หน้าตาย', 'ดูน่ากลัว','ง่วงนอน',
    'เด็ก', 'วัยรุ่น', 'ผู้ใหญ่',
    'เป็นสัตว์', 'เป็นครึ่งมนุษย์', 'ขับหุ่นยนต์',
    'มีร่างแปลง', 'มีหลายร่าง'
]
TOPICS_TOP = [
    'เป็นฮีโร่', 'เป็นตัวร้าย', 'เป็นแอนตี้ฮีโร่',
    'เป็นทหาร', 'เป็นตำรวจ', 'เป็นสายลับ', 'เป็นบอดี้การ์ด',
    'เป็นนักล่า', 'เป็นนักผจญภัย', 'เป็นผู้รอดชีวิต',
    'เป็นราชา', 'เป็นเจ้าหญิง', 'เป็นขุนนาง', 'เป็นหัวหน้าแก๊ง',
    'เป็นนักบวช', 'เป็นนักเวท', 'เป็นนักดาบ', 'เป็นนักธนู', 'เป็นนักหมัดมวย',
    'เป็นนักพยากรณ์', 'เป็นช่างฝีมือ', 'เป็นเทพเจ้า', 'เป็นผู้พิทักษ์สุสาน',
    'เป็นครู', 'เป็นนักเรียน', 'เป็นอาจารย์',
    'เป็นนักวิจัย', 'เป็นหมอ', 'เป็นนักเล่นแร่แปรถาตุ',
    'เป็นนักฆ่า', 'เป็นโจร', 'เป็นนักลอบสังหาร',
    'อยู่ในโลกอนาคต', 'อยู่ในโลกแฟนตาซี', 'อยู่ในโลกปัจจุบัน',
    'อยู่ในโลกใต้น้ำ', 'อยู่ในโลกยุค Steampunk', 'อยู่ในโลกเกาะลอยฟ้า', 'อยู่ในโลกยุคน้ำแข็ง',
    'มีระบบเกม', 'เลเวลอัปได้', 'มีการใช้การ์ดต่อสู้', 'มีแรงก์ลำดับพลัง',
    'เกิดใหม่', 'ย้อนเวลา', 'ข้ามโลก', 'ความทรงจำเสื่อม',
    'มีสงคราม', 'มีการเมือง', 'มีองค์กรลับ', 'มีพันธสัญญาเลือด',
    'มีโรงเรียนเวทมนตร์', 'มีโรงเรียนต่อสู้', 'มีการสำรวจดันเจี้ยน',
    'ต่อสู้กับปีศาจ', 'ต่อสู้กับเอเลี่ยน', 'ต่อสู้กับมนุษย์', 'ต่อสู้กับเทพเจ้า',
    'มีพลังมืด', 'มีพลังแสง', 'มีพลังน้ำ', 'มีพลังสายฟ้า', 'มีพลังลม', 'มีพลังดิน',
    'ควบคุมเวลา', 'ควบคุมความคิด', 'ควบคุมแรงโน้มถ่วง',
    'มีคำสาป', 'มีพรสวรรค์พิเศษ', 'มีเนตรพิเศษ',
    'มีความลับ', 'มีอดีตมืดมน', 'ต้องปกปิดตัวตนจริง',
    'มีเพื่อนร่วมทีม', 'ทำงานคนเดียว',
    'มีการทรยศ', 'มีการแก้แค้น', 'การไถ่บาป',
    'มีความรัก', 'มีดราม่า', 'มีความตลก',
    'มีการแข่งขัน', 'มีทัวร์นาเมนต์',
    'มีสัตว์อสูร', 'มีมังกร', 'มีซอมบี้',
    'ต้องเอาชีวิตรอด', 'โลกกำลังล่มสลาย', 'เครื่องจักรครองเมือง',
    'มีภารกิจหลัก', 'มีระบบกิลด์'
]
TOPICS_TOP = [
    'เป็นฮีโร่', 'เป็นตัวร้าย', 'เป็นแอนตี้ฮีโร่',
    'เป็นทหาร', 'เป็นตำรวจ', 'เป็นสายลับ',
    'เป็นนักล่า', 'เป็นนักผจญภัย',
    'เป็นราชา', 'เป็นเจ้าหญิง', 'เป็นขุนนาง',
    'เป็นนักเวท', 'เป็นนักดาบ', 'เป็นนักธนู',
    'เป็นนักพยากรณ์', 'เป็นช่างฝีมือ', 'เป็นเทพเจ้า',
    'เป็นครู', 'เป็นนักเรียน', 'เป็นอาจารย์',
    'เป็นนักวิจัย', 'เป็นหมอ', 'เป็นนักเล่นแร่แปรถาตุ',
    'เป็นนักฆ่า', 'เป็นโจร', 'เป็นคลดีย์',
    'อยู่ในโลกอนาคต', 'อยู่ในโลกแฟนตาซี', 'อยู่ในโลกปัจจุบัน',
    'อยู่ในโลกใต้น้ำ', 'อยู่ในโลกยุค Steampunk',
    'มีระบบเกม', 'เลเวลอัปได้', 'มีการใช้การ์ดต่อสู้',
    'เกิดใหม่', 'ย้อนเวลา', 'ข้ามโลก',
    'มีสงคราม', 'มีการเมือง', 'มีองค์กรลับ',
    'มีโรงเรียนเวทมนตร์', 'มีโรงเรียนต่อสู้', 'มีการสำรวจดันเจี้ยน',
    'ต่อสู้กับปีศาจ', 'ต่อสู้กับเอเลี่ยน', 'ต่อสู้กับมนุษย์',
    'มีพลังมืด', 'มีพลังแสง', 'มีพลังน้ำ', 'มีพลังสายฟ้า',
    'ควบคุมเวลา', 'ควบคุมความคิด',
    'มีคำสาป', 'มีพรสวรรค์พิเศษ',
    'มีความลับ', 'มีอดีตมืดมน',
    'มีเพื่อนร่วมทีม', 'ทำงานคนเดียว',
    'มีการทรยศ', 'มีการแก้แค้น',
    'มีความรัก', 'มีดราม่า',
    'มีการแข่งขัน', 'มีทัวร์นาเมนต์',
    'มีสัตว์อสูร', 'มีมังกร',
    'ต้องเอาชีวิตรอด', 'โลกกำลังล่มสลาย',
    'มีภารกิจหลัก', 'มีระบบกิลด์'
]
TOPICS_TOP = [
    'เป็นฮีโร่', 'เป็นตัวร้าย', 'เป็นแอนตี้ฮีโร่',
    'เป็นทหาร', 'เป็นตำรวจ', 'เป็นสายลับ',
    'เป็นนักล่า', 'เป็นนักผจญภัย',
    'เป็นราชา', 'เป็นเจ้าหญิง', 'เป็นขุนนาง',
    'เป็นนักเวท', 'เป็นนักดาบ', 'เป็นนักธนู',
    'เป็นครู', 'เป็นนักเรียน', 'เป็นอาจารย์',
    'เป็นนักวิจัย', 'เป็นหมอ',
    'เป็นนักฆ่า', 'เป็นโจร', 'เป็นนักลอบสังหาร',
    'อยู่ในโลกอนาคต', 'อยู่ในโลกแฟนตาซี', 'อยู่ในโลกปัจจุบัน',
    'มีระบบเกม', 'เลเวลอัปได้',
    'เกิดใหม่', 'ย้อนเวลา', 'ข้ามโลก',
    'มีสงคราม', 'มีการเมือง', 'มีองค์กรลับ',
    'มีโรงเรียนเวทมนตร์', 'มีโรงเรียนต่อสู้',
    'ต่อสู้กับปีศาจ', 'ต่อสู้กับเอเลี่ยน', 'ต่อสู้กับมนุษย์',
    'มีพลังมืด', 'มีพลังแสง', 'มีพลังน้ำ', 'มีพลังสายฟ้า',
    'ควบคุมเวลา', 'ควบคุมความคิด',
    'มีคำสาป', 'มีพรสวรรค์พิเศษ',
    'มีความลับ', 'มีอดีตมืดมน',
    'มีเพื่อนร่วมทีม', 'ทำงานคนเดียว',
    'มีการทรยศ', 'มีการแก้แค้น',
    'มีความรัก', 'มีดราม่า',
    'มีการแข่งขัน', 'มีทัวร์นาเมนต์',
    'มีสัตว์อสูร', 'มีมังกร',
    'ต้องเอาชีวิตรอด', 'โลกกำลังล่มสลาย',
    'มีภารกิจหลัก', 'มีระบบกิลด์'
]
event_bus = EventBus()
session_manager = PlayerSessionManager(disconnect_timeout=120, event_bus=event_bus)

game_state = {
    'col_headers': random.sample(TOPICS_TOP, 5),
    'row_headers': random.sample(TOPICS_SIDE, 5),
    'claimed': {},
    'player_order': [],
    'current_turn_idx': 0,
    'turn_start_time': None,
    'turn_duration': 120,
    'header_history': [],  # เก็บ headers ที่เคยใช้แต่ละรอบ
}

TURN_TIMER = None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    logger.info('Socket connected: %s', request.sid)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    logger.info('Socket disconnected: %s', sid)
    session_manager.detach_session(sid)
    
    # Check if no players left online
    remaining = session_manager.get_all_sessions()
    has_online = any(s['connected'] for s in remaining.values())
    if not has_online and remaining:
        # All players offline - clear game state but keep scores
        game_state['claimed'] = {}
        game_state['current_turn_idx'] = 0
        logger.info('All players offline - game cleared')
    elif not remaining:
        # No players at all - full reset
        game_state['header_history'] = []  # เคลียร์ history
        game_state['col_headers'], game_state['row_headers'] = get_non_conflicting_topics()
        game_state['claimed'] = {}
        game_state['player_order'] = []
        game_state['current_turn_idx'] = 0
        logger.info('No players - full reset')
    
    broadcast_state()

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    player_id = data.get('player_id')
    name = data.get('name', 'Player').strip()[:24] or 'Player'
    session = None
    reconnect = False
    
    existing_sessions = session_manager.get_all_sessions()
    is_first = len(existing_sessions) == 0

    if player_id:
        session = session_manager.get_by_player_id(player_id)
        if session:
            session = session_manager.attach_session(player_id, sid, name)
            reconnect = True
            # This is a reconnect, not a new player - restore first status
            is_first = session.get('is_first', False)

    if session is None:
        assigned_color = PLAYER_COLORS[len(existing_sessions) % len(PLAYER_COLORS)]
        session = session_manager.register_new_player(name, sid, assigned_color)
        if is_first:
            session['is_first'] = True
            session['points'] = 0
        if session['player_id'] not in game_state['player_order']:
            game_state['player_order'].append(session['player_id'])
        logger.info('New player joined: %s %s (first=%s)', session['player_id'], session['name'], is_first)
    else:
        # Reconnecting player - make sure they're in player order
        if session['player_id'] not in game_state['player_order']:
            game_state['player_order'].append(session['player_id'])
            logger.info('Reconnected player added to order: %s', session['player_id'])

    normalize_turn_index()
    
    # Get current timer state for this turn
    current_player_id = get_current_player_id()
    turn_start_time = game_state.get('turn_start_time')
    turn_duration = game_state.get('turn_duration', 120)
    
    # If this player is current turn and there's no timer, start one
    if current_player_id == session['player_id'] and not turn_start_time:
        start_turn_timer()
        turn_start_time = game_state.get('turn_start_time')
    
    emit('session_ready', {
        'player_id': session['player_id'],
        'player': {
            'name': session['name'],
            'color': session['color'],
            'hearts': session['hearts'],
            'points': session.get('points', 0),
            'is_first': session.get('is_first', False),
            'connected': session['connected'],
        },
        'col_headers': game_state['col_headers'],
        'row_headers': game_state['row_headers'],
        'claimed': game_state['claimed'],
        'state': get_state_payload(),
        'reconnect': reconnect,
        'turn_start_time': turn_start_time,
        'turn_duration': turn_duration,
    })
    logger.info('Player %s joined or reconnected: sid=%s reconnect=%s is_first=%s', session['player_id'], sid, reconnect, session.get('is_first', False))
    broadcast_state()

@socketio.on('sync_temp_move')
def handle_temp_move(data):
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    active_id = get_current_player_id()
    if not session or session['player_id'] != active_id:
        return
    payload = {**data, 'color': session['color']} if data else None
    emit('player_moving', payload, broadcast=True, include_self=False)

@socketio.on('confirm_final_claim')
def handle_confirm(data):
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    active_id = get_current_player_id()
    if not session or session['player_id'] != active_id:
        emit('session_error', {'message': 'ไม่ใช่ตาของคุณในตอนนี้'})
        return

    slot_id = data.get('slot_id')
    if not slot_id or slot_id in game_state['claimed']:
        emit('session_error', {'message': 'ช่องนี้ไม่สามารถเลือกได้'})
        return

    game_state['claimed'][slot_id] = {
        'img': data['img'],
        'name': data['name'],
        'anime': data.get('anime', ''),
        'player_id': session['player_id'],
        'color': session['color'],
        'disputes': [],
        'timestamp': datetime.now().timestamp(),
    }

    logger.info('Slot claimed: %s by %s', slot_id, session['player_id'])
    advance_turn()
    emit('slot_locked', {
        **data,
        'player_id': session['player_id'],
        'color': session['color'],
    }, broadcast=True)
    broadcast_state()
    check_win_condition()

@socketio.on('vote_dispute')
def handle_vote(data):
    voter = session_manager.get_by_sid(request.sid)
    slot_id = data.get('slot_id')
    if not voter or not slot_id:
        return
    target = game_state['claimed'].get(slot_id)
    if not target or target['player_id'] == voter['player_id']:
        return
    if voter['player_id'] in target['disputes']:
        return
    target['disputes'].append(voter['player_id'])
    emit('dispute_update', {'slot_id': slot_id, 'count': len(target['disputes'])}, broadcast=True)
    logger.info('Vote dispute: %s by %s', slot_id, voter['player_id'])

    # Check if dispute votes exceed half the room
    total_players = len(session_manager.get_all_sessions())
    if total_players > 1 and len(target['disputes']) > total_players // 2:
        # Find the player who placed this character and deduct 1 heart
        owner_id = target['player_id']
        owner_session = session_manager.get_by_player_id(owner_id)
        if owner_session:
            owner_session['hearts'] = max(0, owner_session['hearts'] - 1)
            logger.info('Disputed: %s lost 1 heart, now has %s', owner_id, owner_session['hearts'])
        
        # Remove the character from this slot only
        del game_state['claimed'][slot_id]
        emit('slot_removed', {'slot_id': slot_id}, broadcast=True)
        broadcast_state()
        logger.info('Character removed due to dispute majority: %s votes out of %s', len(target['disputes']), total_players)


@socketio.on('skip_turn')
def handle_skip():
    session = session_manager.get_by_sid(request.sid)
    active_id = get_current_player_id()
    if not session or session['player_id'] != active_id:
        emit('session_error', {'message': 'ไม่ใช่ตาของคุณในตอนนี้'})
        return
    
    session['hearts'] = max(0, session['hearts'] - 1)
    logger.info('Turn skipped by %s hearts=%s', session['player_id'], session['hearts'])
    emit('player_skipped', {
        'player_id': session['player_id'],
        'player_name': session['name'],
        'hearts': session['hearts']
    }, broadcast=True)
    advance_turn()
    broadcast_state()

@socketio.on('kick_all_except_me')
def handle_kick_all():
    global TURN_TIMER
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    logger.info('DEBUG kick_all: sid=%s, session=%s', sid, session)
    
    if not session:
        logger.info('DEBUG kick_all: no session')
        return
    
    # ตัดทุกคนออกจาก session manager
    all_sessions = session_manager.get_all_sessions()
    logger.info('DEBUG kick_all: all_sessions=%s', all_sessions)
    
    for player_id, s in all_sessions.items():
        try:
            session_manager.remove_session(player_id)
            if s.get('sid'):
                socketio.disconnect(s['sid'])
            logger.info('DEBUG kick_all: removed %s', player_id)
        except Exception as e:
            logger.info('DEBUG kick_all: remove error %s', e)
    
    # รีเซ็ตทุกอย่าง
    game_state['col_headers'], game_state['row_headers'] = get_non_conflicting_topics()
    game_state['claimed'] = {}
    game_state['player_order'] = []
    game_state['current_turn_idx'] = 0
    game_state['turn_start_time'] = None
    game_state['header_history'] = []
    
    if TURN_TIMER:
        TURN_TIMER.cancel()
        TURN_TIMER = None
    
    emit('kicked_all', {'message': 'รีเซ็ตเกม! ทุกคนต้องเข้าใหม่'}, broadcast=True)
    logger.info('Kick all executed - full reset')

@socketio.on('request_reset')
def handle_request_reset():
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    if not session:
        return
    # Clear previous votes
    reset_votes.clear()
    no_reset_votes.clear()
    # Show voting modal to all players
    emit('show_reset_vote', {
        'requester': session['name']
    }, broadcast=True)
    logger.info('Reset vote requested by %s', session['player_id'])


@socketio.on('request_full_state')
def handle_request_full_state():
    emit('full_state', {
        'col_headers': game_state['col_headers'],
        'row_headers': game_state['row_headers'],
        'claimed': game_state['claimed'],
        'state': get_state_payload(),
        'turn_start_time': game_state.get('turn_start_time'),
        'turn_duration': game_state.get('turn_duration', 120),
    })

reset_votes = {}
no_reset_votes = {}

@socketio.on('vote_reset_game')
def handle_vote_reset():
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    if not session:
        return
    
    total_players = len(session_manager.get_all_sessions())
    
    # Check if already voted no, remove if so
    if session['player_id'] in no_reset_votes:
        del no_reset_votes[session['player_id']]
    
    if session['player_id'] not in reset_votes:
        reset_votes[session['player_id']] = True
    
    vote_count = len(reset_votes)
    no_vote_count = len(no_reset_votes)
    emit('reset_vote_update', {
        'votes': vote_count, 
        'total': total_players,
        'no_votes': no_vote_count
    }, broadcast=True)
    
    # Reset passes if more than half vote yes
    if total_players > 1 and vote_count > total_players // 2:
        msg = reset_bingo('ไม่เอาอะรีดีกว่า ;DDDDDDDD')
        emit('game_over', {'message': msg}, broadcast=True)
        reset_votes.clear()
        no_reset_votes.clear()
        broadcast_state()
        start_turn_timer()
        logger.info('Game reset by vote: %s/%s', vote_count, total_players)
    # Reset fails if more than half vote no
    elif total_players > 1 and no_vote_count > total_players // 2:
        emit('reset_failed', {'message': 'ไม่รีแล้ว!'}, broadcast=True)
        reset_votes.clear()
        no_reset_votes.clear()
        logger.info('Reset failed: %s/%s voted no', no_vote_count, total_players)


@socketio.on('vote_no_reset')
def handle_vote_no_reset():
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    if not session:
        return
    
    total_players = len(session_manager.get_all_sessions())
    
    # Check if already voted yes, remove if so
    if session['player_id'] in reset_votes:
        del reset_votes[session['player_id']]
    
    if session['player_id'] not in no_reset_votes:
        no_reset_votes[session['player_id']] = True
    
    vote_count = len(reset_votes)
    no_vote_count = len(no_reset_votes)
    emit('reset_vote_update', {
        'votes': vote_count, 
        'total': total_players,
        'no_votes': no_vote_count
    }, broadcast=True)
    
    # Reset fails if more than half vote no
    if total_players > 1 and no_vote_count > total_players // 2:
        emit('reset_failed', {'message': 'ไม่รีแล้ว!'}, broadcast=True)
        reset_votes.clear()
        no_reset_votes.clear()
        logger.info('Reset rejected: %s/%s voted no', no_vote_count, total_players)


def get_current_player_id():
    if not game_state['player_order']:
        return None
    idx = game_state['current_turn_idx']
    if idx < 0 or idx >= len(game_state['player_order']):
        return None
    return game_state['player_order'][idx]


def start_turn_timer():
    global TURN_TIMER
    if TURN_TIMER:
        TURN_TIMER.cancel()
    
    game_state['turn_start_time'] = time.time()
    
    TURN_TIMER = threading.Timer(game_state['turn_duration'], on_turn_timeout)
    TURN_TIMER.daemon = True
    TURN_TIMER.start()
    logger.info('Turn timer started: %s seconds', game_state['turn_duration'])


def on_turn_timeout():
    global TURN_TIMER
    current_player_id = get_current_player_id()
    if not current_player_id:
        return
    
    session = session_manager.get_by_player_id(current_player_id)
    if session:
        session['hearts'] = max(0, session['hearts'] - 1)
        logger.info('Turn timeout! %s lost 1 heart, now has %s', current_player_id, session['hearts'])
    
    TURN_TIMER = None
    advance_turn()
    # Note: advance_turn already calls start_turn_timer at the end
    # Broadcast the updated state with new timer
    broadcast_state()
    emit('turn_timeout', {'player_id': current_player_id}, broadcast=True)


def advance_turn():
    if not game_state['player_order']:
        game_state['current_turn_idx'] = 0
        return
    
    # Remove players with 0 hearts from the turn order
    remove_dead_players()
    
    if not game_state['player_order']:
        game_state['current_turn_idx'] = 0
        event_bus.publish('turn_changed', turn=0)
        return
    
    game_state['current_turn_idx'] = (game_state['current_turn_idx'] + 1) % len(game_state['player_order'])
    
    # Auto-skip if the new current player has no hearts or is disconnected
    current_player_id = get_current_player_id()
    if current_player_id:
        current_session = session_manager.get_by_player_id(current_player_id)
        if current_session and (current_session['hearts'] <= 0 or not current_session['connected']):
            # Auto-skip dead/disconnected players
            if current_session['hearts'] > 0:
                current_session['hearts'] = 0
            logger.info('Auto-skipping player with no hearts or disconnected: %s', current_player_id)
            advance_turn()
            return
    
    event_bus.publish('turn_changed', turn=game_state['current_turn_idx'])
    logger.info('Turn advanced to index %s', game_state['current_turn_idx'])
    check_tie_condition()
    start_turn_timer()


def remove_dead_players():
    """Remove players with 0 hearts from the player order"""
    all_sessions = session_manager.get_all_sessions()
    dead_players = [pid for pid in game_state['player_order'] 
                   if pid in all_sessions and all_sessions[pid].get('hearts', 0) <= 0]
    
    for player_id in dead_players:
        if player_id in game_state['player_order']:
            game_state['player_order'].remove(player_id)
            logger.info('Removed dead player from order: %s', player_id)
    
    # Normalize turn index if needed
    if game_state['current_turn_idx'] >= len(game_state['player_order']):
        game_state['current_turn_idx'] = 0


def normalize_turn_index():
    if not game_state['player_order']:
        game_state['current_turn_idx'] = 0
        return
    if game_state['current_turn_idx'] >= len(game_state['player_order']):
        game_state['current_turn_idx'] = 0


def get_state_payload():
    current_pid = None
    if game_state['player_order'] and game_state['current_turn_idx'] < len(game_state['player_order']):
        current_pid = game_state['player_order'][game_state['current_turn_idx']]
    
    return {
        'players': session_manager.get_all_sessions(),
        'order': game_state['player_order'],
        'turn': game_state['current_turn_idx'],
        'turn_start_time': game_state.get('turn_start_time'),
        'turn_duration': game_state.get('turn_duration', 120),
        'current_player_id': current_pid,
    }


def broadcast_state():
    payload = get_state_payload()
    socketio.emit('update_game_state', payload, broadcast=True)
    event_bus.publish('state_updated', state=payload)


def reset_bingo(message='ไม่เอาอะรีดีกว่า ;DDDDDDDD'):
    global game_state, TURN_TIMER
    
    # เก็บ headers ปัจจุบันเข้า history (เก็บแค่ 5 รอบล่าสุด)
    old_headers = (game_state['col_headers'], game_state['row_headers'])
    game_state['header_history'].append(old_headers)
    if len(game_state['header_history']) > 5:
        game_state['header_history'].pop(0)
    
    # หลีกเลี่ยง headers จาก 2 รอบล่าสุด
    avoid_top = []
    avoid_side = []
    for hist_top, hist_side in game_state['header_history'][-2:]:
        avoid_top.extend(hist_top)
        avoid_side.extend(hist_side)
    
    game_state['col_headers'], game_state['row_headers'] = get_non_conflicting_topics(avoid_top, avoid_side)
    game_state['claimed'] = {}
    game_state['current_turn_idx'] = 0
    game_state['turn_start_time'] = None
    
    # Cancel existing timer
    if TURN_TIMER:
        TURN_TIMER.cancel()
        TURN_TIMER = None
    
    # Reset hearts: ALL players get 3 hearts
    all_sessions = session_manager.get_all_sessions()
    logger.info('Bingo reset: found %s sessions before reset', len(all_sessions))
    for player_id in list(all_sessions.keys()):
        session = session_manager.get_by_player_id(player_id)
        if session:
            session['hearts'] = 3
            logger.info('Bingo reset: %s hearts set to 3', player_id)
    
    # Shuffle player order randomly
    if game_state['player_order']:
        random.shuffle(game_state['player_order'])
        game_state['current_turn_idx'] = 0
        logger.info('Bingo reset: player order shuffled')
    
    start_turn_timer()
    logger.info('Bingo reset: new headers generated, all players revived with 3 hearts')
    return message


def check_win_condition():
    logger.info('DEBUG: check_win_condition called. claimed=%s', list(game_state['claimed'].keys()))
    # Check if any player has completed a bingo (5 in a row/col/diagonal)
    bingo_lines = []
    
    # Rows
    for r in range(5):
        row = [f"{r}-{c}" for c in range(5)]
        if all(s in game_state['claimed'] for s in row):
            bingo_lines.append(row)
    
    # Columns
    for c in range(5):
        col = [f"{r}-{c}" for r in range(5)]
        if all(s in game_state['claimed'] for s in col):
            bingo_lines.append(col)
    
    # Diagonals
    diag1 = [f"{i}-{i}" for i in range(5)]
    if all(s in game_state['claimed'] for s in diag1):
        bingo_lines.append(diag1)
    diag2 = [f"{i}-{4-i}" for i in range(5)]
    if all(s in game_state['claimed'] for s in diag2):
        bingo_lines.append(diag2)
    
    # If there's a bingo, trigger win with 10 second dispute timer
    if bingo_lines:
        logger.info('Bingo detected! Lines: %s', bingo_lines)
        
        # Find last player who placed in any bingo line
        # Get all slots in bingo lines, find the one with latest timestamp
        all_bingo_slots = set()
        for line in bingo_lines:
            all_bingo_slots.update(line)
        
        last_bingo_slot = max(all_bingo_slots, 
            key=lambda s: game_state['claimed'][s].get('timestamp', 0))
        winner_id = game_state['claimed'][last_bingo_slot]['player_id']
        
        # Emit bingo detected event with countdown
        emit('bingo_detected', {
            'lines': bingo_lines,
            'last_player_id': winner_id,
            'countdown': 10,
        }, broadcast=True)
        
        # Start 10 second countdown
        import threading
        bingo_timer = threading.Timer(10, lambda: finalize_win(bingo_lines))
        bingo_timer.daemon = True
        bingo_timer.start()
        
        # Store bingo timer reference
        game_state['bingo_timer'] = bingo_timer


def finalize_win(bingo_lines, winner_id=None):
    game_state.pop('bingo_timer', None)
    
    if winner_id is None:
        all_slots = set()
        for line in bingo_lines:
            all_slots.update(line)
        last_slot = max(all_slots, key=lambda s: game_state['claimed'][s].get('timestamp', 0))
        winner_id = game_state['claimed'][last_slot]['player_id']
    
    session = session_manager.get_by_player_id(winner_id)
    
    if session:
        session['points'] = session.get('points', 0) + 1
        winner_msg = f'ผู้ชนะคือ {session["name"]}! (Bingo สำเร็จ)'
    else:
        winner_msg = 'ไม่พบผู้ชนะ'
    
    msg = reset_bingo(winner_msg)
    emit('game_over', {'message': winner_msg, 'lines': bingo_lines, 'winner_id': winner_id}, broadcast=True)
    broadcast_state()
    start_turn_timer()
    logger.info('Bingo finalized: %s', winner_msg)


def check_tie_condition():
    active_sessions = [s for s in session_manager.get_all_sessions().values() if s['connected']]
    if not active_sessions:
        logger.info('DEBUG: check_tie_condition - no active sessions')
        return
    
    logger.info('DEBUG: check_tie_condition - active: %s, hearts: %s', 
                len(active_sessions), [s['hearts'] for s in active_sessions])
    
    # เช็คว่ามีผู้เล่นที่มีหัวใจเหลือแค่คนเดียวหรือไม่
    players_with_hearts = [s for s in active_sessions if s['hearts'] > 0]
    players_without_hearts = [s for s in active_sessions if s['hearts'] <= 0]
    
    # ถ้ามีผู้เล่นที่มีหัวใจเหลือแค่คนเดียว และมีคนอื่นที่หมดหัวใจแล้ว
    if len(players_with_hearts) == 1 and len(players_without_hearts) >= 1:
        winner = players_with_hearts[0]
        winner['points'] = winner.get('points', 0) + 1
        winner_msg = f'ผู้ชนะคือ {winner["name"]}! (เหลือคนเดียว)'
        msg = reset_bingo(winner_msg)
        emit('game_over', {'message': winner_msg, 'winner_id': winner['player_id']}, broadcast=True)
        broadcast_state()
        start_turn_timer()
        logger.info('Last survivor wins: %s', winner['player_id'])
    elif all(s['hearts'] <= 0 for s in active_sessions):
        # AUTO RESET เมื่อทุกคนหมดหัวใจ
        msg = reset_bingo('ทุกคนหมดหัวใจ! เริ่มใหม่')
        emit('game_over', {'message': msg}, broadcast=True)
        broadcast_state()
        start_turn_timer()
        logger.info('Bingo auto reset: all hearts empty')


@event_bus.subscribe('player_removed')
def handle_player_removed(player_id, session):
    if player_id not in game_state['player_order']:
        return
    position = game_state['player_order'].index(player_id)
    game_state['player_order'].pop(position)
    if position <= game_state['current_turn_idx']:
        game_state['current_turn_idx'] = max(0, game_state['current_turn_idx'] - 1)
    normalize_turn_index()
    logger.info('Player removed from game order: %s', player_id)
    broadcast_state()


@event_bus.subscribe('player_disconnected')
def handle_player_disconnected(player_id, session):
    logger.info('Player disconnected pending cleanup: %s', player_id)
    broadcast_state()


@event_bus.subscribe('player_created')
def handle_player_created(player_id, session):
    logger.info('Player created: %s %s', player_id, session['name'])


@event_bus.subscribe('player_reconnected')
def handle_player_reconnected(player_id, session):
    logger.info('Player reconnected: %s %s', player_id, session['name'])
    broadcast_state()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
