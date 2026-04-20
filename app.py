import logging
import random
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
socketio = SocketIO(app, cors_allowed_origins='*', ping_timeout=60, ping_interval=25, async_mode='threading')

PLAYER_COLORS = [
    '#FF4757', '#2ED573', '#1E90FF', '#ECCC68', '#A55EEA', '#FFA502', '#70A1FF', '#7BED9F'
]

# Conflict topics to prevent overlapping
TOPIC_CONFLICTS = {
    'เป็นฮีโร่': ['เป็นตัวร้าย'],
    'เป็นนักเรียน': ['เป็นครู'],
    'เป็นทหาร': ['เป็นโจร'],
    'เป็นครึ่งมนุษย์': ['เป็นสัตว์'],
    'มีพลังออร่ารอบตัว': ['มีรอยเรืองแสง'],
}

def get_non_conflicting_topics():
    available_top = list(TOPICS_TOP)
    available_side = list(TOPICS_SIDE)
    
    selected_top = []
    selected_side = []
    
    while len(selected_top) < 5 and available_top:
        topic = random.choice(available_top)
        available_top.remove(topic)
        
        # Check conflicts
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
        
        # Check conflicts with already selected top
        can_add = True
        for selected in selected_top:
            if selected in TOPIC_CONFLICTS.get(topic, []):
                can_add = False
                break
        
        if can_add:
            selected_side.append(topic)
    
    return selected_top, selected_side
TOPICS_SIDE = [
    'ผมดำ', 'ผมฟ้า', 'ผมม่วง', 'ผมเขียว', 'ผมชมพู',
    'ตาสีแดง', 'ตาสีทอง', 'ตาสองสี', 'ตาปิดข้างเดียว',
    'ใส่ผ้าปิดตา', 'ใส่หูฟัง', 'ใส่ถุงมือ', 'ใส่รองเท้าบูท',
    'ใส่ชุดเกราะ', 'ใส่สูท', 'ใส่ชุดแฟนตาซี',
    'ตัวสูง', 'ตัวเตี้ย', 'กล้าม', 'ผอม',
    'มีเขา', 'มีปีก', 'มีหาง', 'มีเขี้ยว',
    'มีรอยสัก', 'มีแผลเป็นบนหน้า', 'มีแผลเป็นตามตัว',
    'ใส่แว่นกันแดด', 'ใส่หมวกคลุม', 'ใส่ฮู้ด',
    'ถือดาบใหญ่', 'ถือปืนคู่', 'ถือคทา', 'ถือโล่',
    'ใช้ธนู', 'ใช้มีด', 'ใช้เคียว',
    'มีสัตว์เลี้ยง', 'มีมาสคอต', 'มีหุ่นยนต์คู่หู',
    'ใส่เครื่องแบบทหาร', 'ใส่ชุดนักเรียนหญิง', 'ใส่ชุดนักเรียนชาย',
    'ใส่ชุดแม่บ้าน', 'ใส่ชุดไอดอล',
    'มีพลังออร่ารอบตัว', 'มีรอยเรืองแสง',
    'มีเสียงพูดแปลก', 'ไม่พูด', 'พูดน้อย',
    'ยิ้มตลอด', 'หน้าตาย', 'ดูน่ากลัว',
    'เด็ก', 'วัยรุ่น', 'ผู้ใหญ่',
    'เป็นสัตว์', 'เป็นครึ่งมนุษย์',
    'มีร่างแปลง', 'มีหลายร่าง'
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
session_manager = PlayerSessionManager(disconnect_timeout=10, event_bus=event_bus)

game_state = {
    'col_headers': random.sample(TOPICS_TOP, 5),
    'row_headers': random.sample(TOPICS_SIDE, 5),
    'claimed': {},
    'player_order': [],
    'current_turn_idx': 0,
}

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
    broadcast_state()

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    player_id = data.get('player_id')
    name = data.get('name', 'Player').strip()[:24] or 'Player'
    session = None
    reconnect = False

    if player_id:
        session = session_manager.get_by_player_id(player_id)
        if session:
            session = session_manager.attach_session(player_id, sid, name)
            reconnect = True

    if session is None:
        assigned_color = PLAYER_COLORS[len(session_manager.get_all_sessions()) % len(PLAYER_COLORS)]
        session = session_manager.register_new_player(name, sid, assigned_color)
        game_state['player_order'].append(session['player_id'])
        logger.info('New player joined: %s %s', session['player_id'], session['name'])

    if session['player_id'] not in game_state['player_order']:
        game_state['player_order'].append(session['player_id'])

    normalize_turn_index()
    emit('session_ready', {
        'player_id': session['player_id'],
        'player': {
            'name': session['name'],
            'color': session['color'],
            'hearts': session['hearts'],
            'connected': session['connected'],
        },
        'col_headers': game_state['col_headers'],
        'row_headers': game_state['row_headers'],
        'claimed': game_state['claimed'],
        'state': get_state_payload(),
        'reconnect': reconnect,
    })
    logger.info('Player %s joined or reconnected: sid=%s reconnect=%s', session['player_id'], sid, reconnect)
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
    }

    logger.info('Slot claimed: %s by %s', slot_id, session['player_id'])
    advance_turn()
    emit('slot_locked', {
        **data,
        'player_id': session['player_id'],
        'color': session['color'],
    }, broadcast=True)
    emit('reload_page', {'action': 'confirm'}, broadcast=True)
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
        emit('reload_page', {'action': 'dispute'}, broadcast=True)
        broadcast_state()
        logger.info('Character removed due to dispute majority: %s votes out of %s', len(target['disputes']), total_players)


@socketio.on('skip_turn')
def handle_skip():
    session = session_manager.get_by_sid(request.sid)
    active_id = get_current_player_id()
    if not session or session['player_id'] != active_id:
        return
    session['hearts'] = max(0, session['hearts'] - 1)
    logger.info('Turn skipped by %s hearts=%s', session['player_id'], session['hearts'])
    advance_turn()
    emit('reload_page', {'action': 'skip'}, broadcast=True)
    broadcast_state()

@socketio.on('request_reset')
def handle_request_reset():
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    if not session:
        return
    total_players = len(session_manager.get_all_sessions())
    if total_players >= 2:
        msg = reset_bingo('ไม่เอาอะรีดีกว่า ;DDDDDDDD')
        emit('game_over', {'message': msg}, broadcast=True)
        broadcast_state()
        logger.info('Game manually reset by %s', session['player_id'])

reset_votes = {}

@socketio.on('vote_reset_game')
def handle_vote_reset():
    sid = request.sid
    session = session_manager.get_by_sid(sid)
    if not session:
        return
    
    total_players = len(session_manager.get_all_sessions())
    if session['player_id'] not in reset_votes:
        reset_votes[session['player_id']] = True
    
    vote_count = len(reset_votes)
    emit('reset_vote_update', {'votes': vote_count, 'total': total_players}, broadcast=True)
    
    if total_players > 1 and vote_count > total_players // 2:
        msg = reset_bingo('ไม่เอาอะรีดีกว่า ;DDDDDDDD')
        emit('game_over', {'message': msg}, broadcast=True)
        reset_votes.clear()
        broadcast_state()
        logger.info('Game reset by vote: %s/%s', vote_count, total_players)


def get_current_player_id():
    if not game_state['player_order']:
        return None
    idx = game_state['current_turn_idx']
    if idx < 0 or idx >= len(game_state['player_order']):
        return None
    return game_state['player_order'][idx]


def advance_turn():
    if not game_state['player_order']:
        game_state['current_turn_idx'] = 0
        return
    game_state['current_turn_idx'] = (game_state['current_turn_idx'] + 1) % len(game_state['player_order'])
    event_bus.publish('turn_changed', turn=game_state['current_turn_idx'])
    logger.info('Turn advanced to index %s', game_state['current_turn_idx'])
    check_tie_condition()


def normalize_turn_index():
    if not game_state['player_order']:
        game_state['current_turn_idx'] = 0
        return
    if game_state['current_turn_idx'] >= len(game_state['player_order']):
        game_state['current_turn_idx'] = 0


def get_state_payload():
    return {
        'players': session_manager.get_all_sessions(),
        'order': game_state['player_order'],
        'turn': game_state['current_turn_idx'],
    }


def broadcast_state():
    payload = get_state_payload()
    socketio.emit('update_game_state', payload, broadcast=True)
    event_bus.publish('state_updated', state=payload)


def reset_bingo(message='ไม่เอาอะรีดีกว่า ;DDDDDDDD'):
    global game_state
    game_state['col_headers'], game_state['row_headers'] = get_non_conflicting_topics()
    game_state['claimed'] = {}
    game_state['current_turn_idx'] = 0
    # Reset hearts: ALL players get 3 hearts
    all_sessions = session_manager.get_all_sessions()
    logger.info('Bingo reset: found %s sessions before reset', len(all_sessions))
    for player_id, session in all_sessions.items():
        session['hearts'] = 3
        logger.info('Bingo reset: %s hearts set to 3', player_id)
    logger.info('Bingo reset: new headers generated, all players revived with 3 hearts')
    return message


def check_win_condition():
    # Check if any player has completed a bingo (5 in a row/col/diagonal)
    # For simplicity, check if all slots are claimed
    if len(game_state['claimed']) >= 25:
        # Find winner
        all_sessions = session_manager.get_all_sessions()
        max_hearts = max([s['hearts'] for s in all_sessions.values()]) if all_sessions else 0
        winners = [s['name'] for s in all_sessions.values() if s['hearts'] == max_hearts]
        
        if len(winners) > 1:
            winner_msg = 'ว่าหาผลสรุปไม่ได้ ;D'
        else:
            winner_msg = f'ผู้ชนะคือ {winners[0]}!'
        
        reset_bingo(winner_msg)
        emit('game_over', {'message': winner_msg}, broadcast=True)
        logger.info('Bingo reset due to game win: %s', winner_msg)


def check_tie_condition():
    # Check if there's a tie (e.g., multiple players with same score)
    # For now, simple check: if all players have 0 hearts
    active_sessions = [s for s in session_manager.get_all_sessions().values() if s['connected']]
    if all(s['hearts'] <= 0 for s in active_sessions):
        reset_bingo()
        emit('bingo_reset', {'reason': 'tie'}, broadcast=True)
        logger.info('Bingo reset due to tie')


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
