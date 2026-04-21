const socket = io();
let myPlayerId = null;
let myName = null;
let myPoints = 0;
let myIsFirst = false;
let turnPlayerId = null;
let currentTemp = null;
let previewSlot = null;
let playerColor = "";
let cols = [];
let rows = [];
let reset_votes = {};
let no_reset_votes = {};

// Additional state
let localPlayerId = null;
let claimed = {};
let usernameInput = null;
let bingoCountdownInterval = null;

// Load saved player info from localStorage
try {
    const savedName = localStorage.getItem('animeBingoPlayerName');
    const savedId = localStorage.getItem('animeBingoPlayerId');
    if (savedName) {
        myName = savedName;
        localPlayerId = savedId;
    }
} catch (e) {}

socket.on('reset_vote_update', (data) => {
    const voteInfo = document.getElementById('resetVoteInfo');
    if (voteInfo) {
        const noVotes = data.no_votes || 0;
        voteInfo.innerHTML = `โหวตรี: <strong style="color:#2ecc71;">${data.votes}/${data.total}</strong> | ไม่รี: <strong style="color:#e74c3c;">${noVotes}</strong>`;
    }
    // Show modal if not shown
    const resetModal = document.getElementById('resetModal');
    if (resetModal && !resetModal.classList.contains('active')) {
        resetModal.classList.add('active');
    }
});

socket.on('show_reset_vote', (data) => {
    // Clear any previous vote counts
    reset_votes = {};
    no_reset_votes = {};
    
    // Show the voting modal
    const resetModal = document.getElementById('resetModal');
    const voteInfo = document.getElementById('resetVoteInfo');
    if (resetModal) {
        resetModal.classList.add('active');
    }
    if (voteInfo) {
        voteInfo.innerHTML = 'รอการโหวต...';
    }
});

socket.on('reset_failed', (data) => {
    const resetModal = document.getElementById('resetModal');
    if (resetModal) {
        resetModal.classList.remove('active');
    }
    // Show notification
    showGameOverPopup(data.message);
});

socket.on('game_reset', (data) => {
    console.log('[client] game_reset:', data.message);
    showResetPopup();
    socket.emit('request_full_state');
});

socket.on('player_skipped', (data) => {
    console.log('[client] player_skipped:', data);
    showSkipPopup(data.player_name, data.hearts);
    socket.emit('request_full_state');
});

function showResetPopup() {
    const modal = document.getElementById('resetModal');
    if (modal) {
        modal.classList.add('active');
        setTimeout(() => {
            modal.classList.remove('active');
        }, 3000);
    }
}

function showSkipPopup(playerName, hearts) {
    const modal = document.getElementById('skipModal');
    const text = document.getElementById('skipText');
    if (modal && text) {
        text.innerHTML = `ผู้เล่น <strong style="color:#f1c40f;">${playerName}</strong> -1 หัวใจ<br>เหลือหัวใจ: ${'❤️'.repeat(hearts)}`;
        modal.classList.add('active');
        setTimeout(() => {
            modal.classList.remove('active');
        }, 3000);
    }
}

function showGameOverPopup(message) {
    const modal = document.getElementById('gameOverModal');
    const text = document.getElementById('gameOverText');
    if (modal && text) {
        text.textContent = message;
        modal.classList.add('active');
        setTimeout(() => {
            modal.classList.remove('active');
        }, 5000);
    }
}

socket.on('connect_error', (error) => {
    console.error('[client] connect_error', error);
});

socket.on('disconnect', (reason) => {
    console.warn('[client] disconnected', reason);
    // Clear any remote preview (current player may have disconnected)
    if (previewSlot) {
        const cell = document.getElementById(`cell-${previewSlot}`);
        if (cell && !cell.classList.contains('locked')) {
            cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            cell.style.borderColor = '#333';
            cell.style.borderStyle = 'solid';
            cell.draggable = false;
        }
        previewSlot = null;
    }
});

// Connection management
socket.on('connect', () => {
    console.log('[client] connected');
    socket.emit('request_full_state');
    // Only auto-join if we have stored credentials
    if (localPlayerId || myName) {
        const payload = { name: myName || 'Player' };
        if (myPlayerId) {
            payload.player_id = myPlayerId;
        } else if (localPlayerId) {
            payload.player_id = localPlayerId;
        }
        socket.emit('join_game', payload);
    }
});

socket.on('session_ready', (data) => {
    console.log('[client] session_ready', data);
    myPlayerId = data.player_id;
    myName = data.player.name;
    playerColor = data.player.color;
    myPoints = data.player.points || 0;
    myIsFirst = data.player.is_first || false;

    // Save for reconnection
    try {
        localStorage.setItem('animeBingoPlayerId', myPlayerId);
        localStorage.setItem('animeBingoPlayerName', myName);
    } catch (e) {}

    localPlayerId = myPlayerId;
    cols = data.col_headers || [];
    rows = data.row_headers || [];
    claimed = data.claimed || {};

    updateGameState(data.state);
    buildGrid(claimed);
    setLoginVisible(false);

    if (data.reconnect) {
        showGameOverPopup('กลับมาได้แล้ว!');
    }

    if (data.turn_start_time) {
        startTimer(data.turn_start_time * 1000, data.turn_duration || 120);
    } else {
        stopTimer();
    }
});

socket.on('update_game_state', updateGameState);

socket.on('slot_locked', (data) => {
    claimed[data.slot_id] = {
        img: data.img,
        name: data.name,
        anime: data.anime || '',
        player_id: data.player_id,
        color: data.color,
        disputes: []
    };
    socket.emit('request_full_state');
});

socket.on('dispute_update', (data) => {
    const slot = claimed[data.slot_id];
    if (slot) {
        slot.disputes = new Array(data.count);
        const cell = document.getElementById(`cell-${data.slot_id}`);
        if (cell) {
            const badge = cell.querySelector('.dispute-badge');
            if (badge) {
                badge.textContent = `ค้าน ${data.count}`;
                badge.style.display = data.count > 0 ? 'block' : 'none';
            } else {
                setLockedCell(cell, slot, data.slot_id);
    }

    // Clear temporary selection if it's no longer our turn
    if (turnPlayerId !== myPlayerId && currentTemp) {
        currentTemp = null;
        const confirmBtn = document.getElementById('confirm');
        if (confirmBtn) confirmBtn.disabled = true;
    }
}
    }
});

socket.on('slot_removed', (data) => {
    delete claimed[data.slot_id];
    buildGrid(claimed);
});

socket.on('game_over', (data) => {
    if (bingoCountdownInterval) {
        clearInterval(bingoCountdownInterval);
        bingoCountdownInterval = null;
    }
    const bingoModal = document.getElementById('bingoModal');
    if (bingoModal) bingoModal.classList.remove('active');
    // Clear any remote preview
    if (previewSlot) {
        const cell = document.getElementById(`cell-${previewSlot}`);
        if (cell && !cell.classList.contains('locked')) {
            cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            cell.style.borderColor = '#333';
            cell.style.borderStyle = 'solid';
            cell.draggable = false;
        }
        previewSlot = null;
    }
    // Hide reset modal if open
    const resetModal = document.getElementById('resetModal');
    if (resetModal) resetModal.classList.remove('active');
    showGameOverPopup(data.message);
});

socket.on('kicked_all', (data) => {
    showGameOverPopup(data.message);
    localStorage.removeItem('animeBingoPlayerId');
    localStorage.removeItem('animeBingoPlayerName');
    myPlayerId = null;
    localPlayerId = null;
    myName = null;
    // Clear any remote preview
    if (previewSlot) {
        const cell = document.getElementById(`cell-${previewSlot}`);
        if (cell && !cell.classList.contains('locked')) {
            cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            cell.style.borderColor = '#333';
            cell.style.borderStyle = 'solid';
            cell.draggable = false;
        }
        previewSlot = null;
    }
    setLoginVisible(true);
});

socket.on('session_error', (data) => {
    alert('Error: ' + data.message);
});

socket.on('full_state', (data) => {
    // Close any open modals
    const resetModal = document.getElementById('resetModal');
    if (resetModal) resetModal.classList.remove('active');
    const bingoModal = document.getElementById('bingoModal');
    if (bingoModal) bingoModal.classList.remove('active');
    
    cols = data.col_headers || cols;
    rows = data.row_headers || rows;
    claimed = data.claimed || claimed;
    updateGameState(data.state);
    if (data.turn_start_time) {
        startTimer(data.turn_start_time * 1000, data.turn_duration || 120);
    } else {
        stopTimer();
    }
    buildGrid(claimed);
});

socket.on('turn_timeout', (data) => {
    console.log('[client] turn_timeout', data);

    socket.emit('request_full_state');
});

socket.on('player_moving', (data) => {
    // Clear any existing preview first
    if (previewSlot) {
        const oldCell = document.getElementById(`cell-${previewSlot}`);
        if (oldCell && !oldCell.classList.contains('locked')) {
            oldCell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            oldCell.style.borderColor = '#333';
            oldCell.style.borderStyle = 'solid';
            oldCell.draggable = false;
        }
        previewSlot = null;
    }
    
    if (!data) {
        // Explicit clear (e.g., player cancelled)
        return;
    }
    
    const slotId = data.slot_id;
    if (!slotId) return;
    
    const cell = document.getElementById(`cell-${slotId}`);
    if (!cell || cell.classList.contains('locked')) return;
    
    // Show preview with dashed border and reduced opacity
    cell.innerHTML = `<img src="${data.img}" style="opacity:0.7; width:100%; height:100%; object-fit:cover;">`;
    cell.style.borderColor = data.color || '#888';
    cell.style.borderStyle = 'dashed';
    cell.style.borderWidth = '4px';
    previewSlot = slotId;
});

socket.on('bingo_detected', (data) => {
    if (bingoCountdownInterval) clearInterval(bingoCountdownInterval);
    const modal = document.getElementById('bingoModal');
    const countdownEl = document.getElementById('bingoCountdown');
    const textEl = document.getElementById('bingoText');
    if (modal && countdownEl) {
        textEl.textContent = 'มีคนทำบิงโกแล้ว! มีเวลา 10 วินาทีในการค้าน';
        modal.classList.add('active');
        let remaining = data.countdown || 10;
        countdownEl.textContent = remaining;
        bingoCountdownInterval = setInterval(() => {
            remaining--;
            countdownEl.textContent = remaining;
            if (remaining <= 0) {
                clearInterval(bingoCountdownInterval);
                bingoCountdownInterval = null;
                modal.classList.remove('active');
                location.reload(); // Auto refresh page after countdown ends
            }
        }, 1000);
    }
});

function buildGrid(claimed) {
    previewSlot = null; // Clear any remote preview when rebuilding grid
    const grid = document.getElementById('bingoGrid');
    grid.innerHTML = '';
    
    console.log('[client] buildGrid - cols:', cols, 'rows:', rows);
    
    // Use default if no headers
    const colHeaders = (cols && cols.length === 5) ? cols : ['X1','X2','X3','X4','X5'];
    const rowHeaders = (rows && rows.length === 5) ? rows : ['Y1','Y2','Y3','Y4','Y5'];

    grid.appendChild(createHeaderCell('', true));
    colHeaders.forEach((col) => grid.appendChild(createHeaderCell(col, false)));

    for (let r = 0; r < 5; r += 1) {
        grid.appendChild(createHeaderCell(rowHeaders[r], true, true));
        for (let c = 0; c < 5; c += 1) {
            const slotId = `${r}-${c}`;
            const cell = document.createElement('div');
            cell.id = `cell-${slotId}`;
            cell.className = 'cell';
            if (claimed?.[slotId]) {
                setLockedCell(cell, claimed[slotId], slotId);
            } else {
                cell.classList.add('drop-zone');
                cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
                cell.ondragover = (e) => e.preventDefault();
                cell.ondrop = (e) => onDrop(e, slotId);
                cell.onclick = () => onQuickCancel(slotId);
                cell.ondragstart = (e) => onInternalDrag(e, slotId);
            }
            grid.appendChild(cell);
        }
    }
}

function createHeaderCell(text, isCorner = false, isRow = false) {
    const node = document.createElement('div');
    node.className = `cell ${isRow ? 'h-row' : 'h-col'}`;
    if (isCorner && !isRow) {
        node.textContent = '';
        node.style.background = 'transparent';
        node.style.border = 'none';
    } else {
        node.textContent = text || '';
        node.style.color = '#fff';
    }
    return node;
}

function onDrop(event, slotId) {
    event.preventDefault();
    if (turnPlayerId !== myPlayerId) {
        return;
    }
    const raw = event.dataTransfer.getData('text');
    if (!raw) {
        return;
    }
    const data = JSON.parse(raw);
    if (!data || !data.img || !data.name) {
        return;
    }
    if (currentTemp && currentTemp.slot_id !== slotId) {
        const previous = document.getElementById(`cell-${currentTemp.slot_id}`);
        if (previous && !previous.classList.contains('locked')) {
            previous.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            previous.style.borderColor = '#333';
            previous.draggable = false;
        }
    }

    const cell = document.getElementById(`cell-${slotId}`);
    if (!cell || cell.classList.contains('locked')) {
        return;
    }
    cell.innerHTML = `<img src="${data.img}">`;
    cell.style.borderColor = playerColor;
    cell.draggable = true;
    currentTemp = { slot_id: slotId, img: data.img, name: data.name };
    socket.emit('sync_temp_move', currentTemp);
    document.getElementById('confirm').disabled = false;
}

function onInternalDrag(event, slotId) {
    if (turnPlayerId !== myPlayerId || !currentTemp || currentTemp.slot_id !== slotId) {
        event.preventDefault();
        return;
    }
    event.dataTransfer.setData('text', JSON.stringify(currentTemp));
}

function onQuickCancel(slotId) {
    if (turnPlayerId !== myPlayerId || !currentTemp || currentTemp.slot_id !== slotId) {
        return;
    }
    const cell = document.getElementById(`cell-${slotId}`);
    if (!cell) {
        return;
    }
    cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
    cell.style.borderColor = '#333';
    cell.draggable = false;
    currentTemp = null;
    socket.emit('sync_temp_move', null);
    document.getElementById('confirm').disabled = true;
}

function setLockedCell(element, data, slotId) {
    element.className = 'cell locked';
    element.onclick = () => showCharDetail(data, slotId);
    element.innerHTML = `
        <img src="${data.img}">
        <button class="vote-btn" onclick="event.stopPropagation(); socket.emit('vote_dispute', { slot_id: '${slotId}' })">ค้าน!</button>
        <div id="dispute-${slotId}" class="dispute-badge" style="display:${data.disputes?.length ? 'block' : 'none'}">ค้าน ${data.disputes?.length || 0}</div>
    `;
    element.style.border = `4px solid ${data.color}`;
    element.style.boxShadow = `0 0 16px ${data.color}44`;
}

let currentDisputeSlot = null;

function showCharDetail(data, slotId) {
    currentDisputeSlot = slotId;
    document.getElementById('charDetailImg').innerHTML = `<img src="${data.img}" style="width:100%;object-fit:cover;">`;
    document.getElementById('charDetailInfo').innerHTML = `
        <p style="font-size:1.3rem;font-weight:700;color:#fff;margin:8px 0;">${data.name || 'ไม่ระบุชื่อ'}</p>
        <p style="font-size:1rem;color:#aaa;margin:4px 0;">${data.anime || 'ไม่ระบุเรื่อง'}</p>
    `;
    document.getElementById('charDetailModal').classList.add('active');
}

function closeCharDetail() {
    document.getElementById('charDetailModal').classList.remove('active');
    currentDisputeSlot = null;
}

let turnStartTime = null;
let turnDuration = 120;
let timerInterval = null;

function disputeSelectedChar() {
    if (currentDisputeSlot) {
        socket.emit('vote_dispute', { slot_id: currentDisputeSlot });
        closeCharDetail();
    }
}

function startTimer(startTime, duration) {
    turnStartTime = startTime;
    turnDuration = duration;
    
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    updateTimerDisplay();
    
    timerInterval = setInterval(() => {
        updateTimerDisplay();
    }, 1000);
}

function updateTimerDisplay() {
    if (!turnStartTime) {
        const timerEl = document.getElementById('timerValue');
        if (timerEl) timerEl.textContent = '2:00';
        return;
    }
    
    const now = Date.now();
    const elapsed = (now - turnStartTime) / 1000;
    const remaining = Math.max(0, turnDuration - elapsed);
    
    const minutes = Math.floor(remaining / 60);
    const seconds = Math.floor(remaining % 60);
    const timerEl = document.getElementById('timerValue');
    if (timerEl) {
        timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (remaining <= 10) {
            timerEl.style.color = '#e74c3c';
            timerEl.style.animation = 'pulse 0.5s infinite';
        } else if (remaining <= 30) {
            timerEl.style.color = '#f39c12';
            timerEl.style.animation = 'none';
        } else {
            timerEl.style.color = '#2ecc71';
            timerEl.style.animation = 'none';
        }
    }

    if (remaining <= 0) {
        socket.emit('request_full_state');
    }
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    turnStartTime = null;
    turnDuration = 120;
    const timerEl = document.getElementById('timerValue');
    if (timerEl) timerEl.textContent = '2:00';
}

function updateGameState(data) {
    claimed = data.claimed || claimed;
    
    const newTurnPlayerId = data.order[data.turn] || null;
    
    // Clear remote preview if turn changed (preview belonged to previous player)
    if (turnPlayerId !== newTurnPlayerId && previewSlot) {
        const oldCell = document.getElementById(`cell-${previewSlot}`);
        if (oldCell && !oldCell.classList.contains('locked')) {
            oldCell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            oldCell.style.borderColor = '#333';
            oldCell.style.borderStyle = 'solid';
            oldCell.draggable = false;
        }
        previewSlot = null;
    }
    turnPlayerId = newTurnPlayerId;
    playerColor = data.players?.[myPlayerId]?.color || playerColor;
    
    // Clear local temp selection if it's no longer our turn
    if (turnPlayerId !== myPlayerId && currentTemp) {
        const slotId = currentTemp.slot_id;
        const cell = document.getElementById(`cell-${slotId}`);
        if (cell && !cell.classList.contains('locked')) {
            cell.innerHTML = '<span style="color:#888; font-size:2rem; font-weight:bold;">?</span>';
            cell.style.borderColor = '#333';
            cell.draggable = false;
        }
        currentTemp = null;
        const confirmBtn = document.getElementById('confirm');
        if (confirmBtn) confirmBtn.disabled = true;
    }
    
    // Update sidebar player list
    const playerListEl = document.getElementById('playerList');
    if (playerListEl) {
        playerListEl.innerHTML = '';
        Object.entries(data.players || {}).forEach(([playerId, player]) => {
            const isActive = playerId === turnPlayerId;
            const isDisconnected = !player.connected;
            const isSkull = player.hearts <= 0;
            const isFirst = player.is_first || false;
            const points = player.points || 0;
            
            const card = document.createElement('div');
            card.className = `player-card${isActive ? ' active' : ''}${isDisconnected ? ' disconnected' : ''}${isSkull ? ' skull' : ''}`;
            card.style.borderLeftColor = player.color;
            card.style.borderLeft = '4px solid';
            
            const firstEmoji = isFirst ? ' 😺' : '';
            card.innerHTML = `
                <div class="player-name">${player.name}${firstEmoji}</div>
                <div class="player-score">★${points}</div>
                <div class="hearts">${'❤️'.repeat(Math.max(0, player.hearts))}</div>
            `;
            playerListEl.appendChild(card);
        });
    }
    
    // Update top player area
    const playerArea = document.getElementById('players');
    playerArea.innerHTML = '';

    Object.entries(data.players || {}).forEach(([playerId, player]) => {
        const isActive = playerId === turnPlayerId;
        const isDisconnected = !player.connected;
        const isSkull = player.hearts <= 0;
        const isFirst = player.is_first || false;
        const points = player.points || 0;
        const card = document.createElement('div');
        card.className = `player-card${isActive ? ' active' : ''}${isDisconnected ? ' disconnected' : ''}${isSkull ? ' skull' : ''}`;
        card.style.color = player.color;
        const firstEmoji = isFirst ? ' 😺' : '';
        card.innerHTML = `
            <div class="p-dot" style="background:${player.color};"></div>
            <div class="player-name">${player.name}${firstEmoji} <span style="color:#f1c40f;">★${points}</span></div>
            <div class="hearts">${'❤️'.repeat(Math.max(0, player.hearts))}</div>
        `;
        playerArea.appendChild(card);
    });

    const indicator = document.getElementById('turnIndicator');
    if (myPlayerId === turnPlayerId) {
        indicator.textContent = '🎮 ตาของคุณแล้ว! เลือกตัวละครมาวางได้เลย';
        indicator.style.color = 'var(--success)';
    } else {
        indicator.textContent = '⌛ รอเพื่อนเล่น...';
        indicator.style.color = 'var(--muted)';
    }
    document.getElementById('skip').disabled = (myPlayerId !== turnPlayerId);

    // Only update timer if server provides turn_start_time
    if (turnPlayerId && data.turn_start_time) {
        startTimer(data.turn_start_time * 1000, data.turn_duration || 120);
    }

    buildGrid(claimed);
}

let searchTimeout = null;
function onSearch() {
    // Show anime section when typing
    document.getElementById('animeSection').style.display = 'block';
    document.getElementById('charSection').style.display = 'none';
    
    clearTimeout(searchTimeout);
    searchTimeout = window.setTimeout(async () => {
        const query = document.getElementById('search').value.trim();
        if (query.length < 3) {
            document.getElementById('animeResultsLabel').style.display = 'none';
            document.getElementById('charResultsLabel').style.display = 'none';
            document.getElementById('animeResults').innerHTML = '';
            document.getElementById('charResults').innerHTML = '';
            return;
        }
        try {
            const response = await fetch(`https://api.jikan.moe/v4/anime?q=${encodeURIComponent(query)}&limit=12`);
            const payload = await response.json();
            renderAnimeResults(payload.data || []);
        } catch (error) {
            console.error('[search] anime lookup failed', error);
        }
    }, 300);
}

function renderAnimeResults(items) {
    const container = document.getElementById('animeResults');
    const label = document.getElementById('animeResultsLabel');
    const count = document.getElementById('animeCount');
    container.innerHTML = '';
    if (!items.length) {
        label.style.display = 'none';
        return;
    }
    label.style.display = 'flex';
    count.textContent = items.length;
    items.forEach((anime) => {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
            <img src="${anime.images?.jpg?.image_url || ''}" alt="${anime.title}">
            <div class="item-name">${anime.title}</div>
        `;
        card.onclick = () => getChars(anime.mal_id, anime.title);
        container.appendChild(card);
    });
}

let currentAnimeTitle = '';
let currentAnimeId = null;
let allCharacters = [];

async function getChars(animeId, animeTitle) {
    currentAnimeTitle = animeTitle;
    currentAnimeId = animeId;
    try {
        const response = await fetch(`https://api.jikan.moe/v4/anime/${animeId}/characters`);
        const payload = await response.json();
        allCharacters = payload.data || [];
        
        // Hide anime section, show character section
        document.getElementById('animeSection').style.display = 'none';
        document.getElementById('charSection').style.display = 'block';
        document.getElementById('charSearch').value = '';
        
        renderCharacterResults(allCharacters, animeTitle);
    } catch (error) {
        console.error('[search] character fetch failed', error);
    }
}

function onCharSearch() {
    const query = document.getElementById('charSearch').value.trim().toLowerCase();
    const container = document.getElementById('charResults');
    const count = document.getElementById('charCount');
    
    if (!query) {
        renderCharacterResults(allCharacters, currentAnimeTitle);
        return;
    }
    
    const filtered = allCharacters.filter(item => 
        item.character.name.toLowerCase().includes(query)
    );
    
    renderCharacterResults(filtered, currentAnimeTitle);
    count.textContent = filtered.length;
}

function renderCharacterResults(characters, animeTitle) {
    const container = document.getElementById('charResults');
    const label = document.getElementById('charResultsLabel');
    const count = document.getElementById('charCount');
    container.innerHTML = '';
    if (!characters.length) {
        label.style.display = 'none';
        return;
    }
    label.style.display = 'flex';
    count.textContent = Math.min(characters.length, 50);
    characters.slice(0, 50).forEach((item) => {
        const character = item.character;
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
            <img src="${character.images?.jpg?.image_url || ''}" alt="${character.name}">
            <div class="item-name">${character.name}</div>
        `;
        card.draggable = true;
        card.ondragstart = (event) => {
            if (turnPlayerId !== myPlayerId) {
                event.preventDefault();
                return;
            }
            event.dataTransfer.setData('text', JSON.stringify({ 
                name: character.name, 
                img: character.images?.jpg?.image_url || '',
                anime: currentAnimeTitle 
            }));
        };
        container.appendChild(card);
    });
}

function showConfirmModal() {
    if (!currentTemp) {
        return;
    }
    document.getElementById('cImg').innerHTML = `<img src="${currentTemp.img}" style="width:150px; height:150px; border-radius:20px; border:4px solid ${playerColor}; object-fit:cover;">`;
    document.getElementById('cText').textContent = `คุณแน่ใจหรือไม่ว่า "${currentTemp.name}" เหมาะสมกับช่องนี้?`;
    document.getElementById('confirmModal').classList.add('active');
}

function submitMove() {
    if (!currentTemp) {
        return;
    }
    socket.emit('confirm_final_claim', currentTemp);
    socket.emit('request_full_state');
    closeConfirm();
}

function closeConfirm() {
    document.getElementById('confirmModal').classList.remove('active');
}

function setLoginVisible(visible) {
    const overlay = document.getElementById('loginOverlay');
    if (overlay) {
        overlay.style.display = visible ? 'flex' : 'none';
    }
}

function enterGame() {
    const input = document.getElementById('username');
    const name = input ? input.value.trim() : '';
    if (!name) {
        alert('กรุณาระบุชื่อ');
        return;
    }
    const payload = { name };
    if (myPlayerId) {
        payload.player_id = myPlayerId;
    } else if (localPlayerId) {
        payload.player_id = localPlayerId;
    }
    socket.emit('join_game', payload);
    myName = name;
    try {
        localStorage.setItem('animeBingoPlayerName', name);
    } catch (e) {}
}

function dismissBingoDispute() {
    if (bingoCountdownInterval) {
        clearInterval(bingoCountdownInterval);
        bingoCountdownInterval = null;
    }
    const modal = document.getElementById('bingoModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

window.enterGame = enterGame;
window.showConfirmModal = showConfirmModal;
window.submitMove = submitMove;
window.closeConfirm = closeConfirm;
window.onSearch = onSearch;
window.onCharSearch = onCharSearch;
window.dismissBingoDispute = dismissBingoDispute;
window.closeSkipModal = closeSkipModal;
window.closeResetModal = closeResetModal;
window.closeCharDetail = closeCharDetail;

function closeSkipModal() {
    document.getElementById('skipModal').classList.remove('active');
}

function closeResetModal() {
    document.getElementById('resetModal').classList.remove('active');
}

window.addEventListener('DOMContentLoaded', () => {
    usernameInput = document.getElementById('username');
    if (!usernameInput) return;
    if (myName) {
        usernameInput.value = myName;
    }
    if (!myName) {
        setLoginVisible(true);
    }
});
