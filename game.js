(() => {
  const $ = selector => document.querySelector(selector);
  const canvas = $('#game');
  const ctx = canvas.getContext('2d');
  const mode = $('#mode');
  const speed = $('#speed');
  const board = $('#board');
  const N = 21;
  const CELL = 20;
  const directions = { up: { x: 0, y: -1 }, down: { x: 0, y: 1 }, left: { x: -1, y: 0 }, right: { x: 1, y: 0 } };
  const tips = { classic: '撞到边缘或自己就结束', wrap: '从一边出去，会从另一边出现', timed: '60 秒内尽量吃到更多点点', walls: '躲开灰色路障和自己的身体' };
  let snake, food, direction, turns, obstacles, tails;
  let score = 0, best = 0, running = false, paused = false, sound = true, audio;
  let gameTime = 0, lastFrame = null, nextStep = 0, animationFrame = null;
  let pointer = null;
  let audioStatus = 'idle', audioRevision = 0;
  try { best = Number(localStorage.getItem('dotSnakeBest')) || 0; } catch {}
  $('#best').textContent = String(best).padStart(2, '0');

  const stepDuration = () => speed.value === 'easy' ? 190 : speed.value === 'fast' ? 90 : 135;
  const sameCell = (a, b) => a.x === b.x && a.y === b.y;
  const radiusAt = (index, length) => index === 0 ? 8 : 7.5 - 3 * index / Math.max(1, length - 1);

  function reset() {
    cancelAnimationFrame(animationFrame);
    animationFrame = null;
    lastFrame = null;
    gameTime = 0;
    nextStep = stepDuration();
    snake = [{ x: 8, y: 10 }, { x: 9, y: 10 }, { x: 10, y: 10 }, { x: 11, y: 10 }];
    direction = directions.left;
    turns = [];
    tails = [];
    obstacles = [];
    pointer = null;
    score = 0;
    if (mode.value === 'walls') {
      for (let x = 5; x < 9; x++) obstacles.push({ x, y: 6 });
      for (let x = 13; x < 17; x++) obstacles.push({ x, y: 14 });
    }
    placeFood();
    updateStats();
    draw();
  }

  function placeFood() {
    const free = [];
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const cell = { x, y };
      if (!snake.some(s => sameCell(s, cell)) && !obstacles.some(o => sameCell(o, cell))) free.push(cell);
    }
    food = free[Math.floor(Math.random() * free.length)] || null;
  }

  function updateStats() {
    $('#score').textContent = String(score).padStart(2, '0');
    $('#time-label').textContent = mode.value === 'timed' ? '剩余' : '长度';
    $('#length').textContent = mode.value === 'timed'
      ? Math.max(0, Math.ceil((60000 - gameTime) / 1000)) + 's'
      : String(snake.length).padStart(2, '0');
  }

  function dot(x, y, radius, color, opacity = 1) {
    if (radius <= 0) return;
    ctx.globalAlpha = opacity;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function draw() {
    ctx.clearRect(0, 0, 420, 420);
    ctx.fillStyle = '#fbfcff';
    ctx.fillRect(0, 0, 420, 420);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) dot(x * CELL + 10, y * CELL + 10, 1.1, '#e7ecf8');
    obstacles.forEach(o => {
      ctx.fillStyle = '#bac6df';
      ctx.beginPath();
      ctx.roundRect(o.x * CELL + 3, o.y * CELL + 3, 14, 14, 5);
      ctx.fill();
    });
    if (food) {
      ctx.save();
      ctx.shadowColor = '#ff7e99';
      ctx.shadowBlur = 12;
      dot(food.x * CELL + 10, food.y * CELL + 10, 5, '#ff7694');
      ctx.restore();
    }
    tails = tails.filter(tail => gameTime - tail.born < tail.duration);
    tails.forEach(tail => {
      const progress = Math.min(1, (gameTime - tail.born) / tail.duration);
      dot(tail.x * CELL + 10, tail.y * CELL + 10, tail.radius * Math.pow(1 - progress, 1.25), '#5b84f0', 1 - progress);
    });
    // Dot centers stay on the grid; only the departing tail shrinks and fades.
    for (let i = snake.length - 1; i >= 0; i--) {
      const s = snake[i];
      const x = s.x * CELL + 10, y = s.y * CELL + 10;
      const radius = radiusAt(i, snake.length);
      dot(x, y, radius, i === 0 ? '#3567e9' : '#5b84f0');
      if (i === 0) {
        const face = turns[0] || direction;
        for (const side of [-1, 1]) {
          dot(x + face.x * 2.8 - face.y * side * 2.1, y + face.y * 2.8 + face.x * side * 2.1, 1.2, '#fff');
        }
      }
    }
  }

  function begin() {
    running = false;
    paused = false;
    reset();
    running = true;
    $('#overlay').classList.add('hidden');
    lastFrame = performance.now();
    animationFrame = requestAnimationFrame(frame);
  }

  function frame(timestamp) {
    if (!running || paused) return;
    const delta = Math.max(0, Math.min(64, timestamp - lastFrame));
    lastFrame = timestamp;
    gameTime += delta;
    if (mode.value === 'timed' && gameTime >= 60000) {
      updateStats();
      finish(true, '时间到！', '你成功撑过了 60 秒', '🏆');
      return;
    }
    if (gameTime >= nextStep) {
      nextStep += stepDuration();
      advance();
    }
    if (!running) return;
    updateStats();
    draw();
    animationFrame = requestAnimationFrame(frame);
  }

  function advance() {
    if (turns.length) direction = turns.shift();
    const head = { x: snake[0].x + direction.x, y: snake[0].y + direction.y };
    if (mode.value === 'wrap') {
      head.x = (head.x + N) % N;
      head.y = (head.y + N) % N;
    } else if (head.x < 0 || head.y < 0 || head.x >= N || head.y >= N) {
      finish(false, '撞到边缘啦', '再试一次，躲开边界吧', '💫');
      return;
    }
    const eating = food && sameCell(head, food);
    const occupied = eating ? snake : snake.slice(0, -1);
    if (occupied.some(s => sameCell(s, head)) || obstacles.some(o => sameCell(o, head))) {
      finish(false, '哎呀，撞上了', '调整方向，再挑战一次', '💥');
      return;
    }
    const oldLength = snake.length;
    snake.unshift(head);
    if (eating) {
      score += 10;
      if (score > best) {
        best = score;
        try { localStorage.setItem('dotSnakeBest', String(best)); } catch {}
        $('#best').textContent = String(best).padStart(2, '0');
      }
      beep();
      placeFood();
      if (!food) {
        updateStats();
        finish(true, '满屏都是你！', '完美通关，太厉害了', '🏆');
      }
    } else {
      const tail = snake.pop();
      tails.push({ ...tail, radius: radiusAt(oldLength - 1, oldLength), born: gameTime, duration: stepDuration() * 0.85 });
    }
  }

  function finish(win, title, detail, emoji) {
    running = false;
    paused = false;
    turns = [];
    pointer = null;
    cancelAnimationFrame(animationFrame);
    draw();
    $('#emoji').textContent = emoji;
    $('#message').textContent = title;
    $('#detail').textContent = detail + ' · 得分 ' + score;
    $('#start').textContent = win ? '再玩一次' : '再试一次';
    $('#overlay').classList.remove('hidden');
  }

  function setDirection(next) {
    if (!running || paused || turns.length >= 2) return;
    const previous = turns[turns.length - 1] || direction;
    // Validate against the queued heading, so quick left → up → right is retained.
    if (sameCell(previous, next) || (next.x === -previous.x && next.y === -previous.y)) return;
    turns.push(next);
    draw();
  }

  function pause() {
    if (!running) return;
    paused = !paused;
    pointer = null;
    turns = [];
    if (paused) {
      cancelAnimationFrame(animationFrame);
      $('#emoji').textContent = '⏸️';
      $('#message').textContent = '暂停一下';
      $('#detail').textContent = '准备好后继续';
      $('#start').textContent = '继续';
    } else {
      unlockAudio();
      lastFrame = performance.now();
      animationFrame = requestAnimationFrame(frame);
    }
    $('#overlay').classList.toggle('hidden', !paused);
  }

  function updateSoundButton() {
    const button = $('#sound');
    const blocked = sound && audioStatus === 'blocked';
    const unavailable = sound && audioStatus === 'unsupported';
    button.textContent = !sound ? '🔇 音效关' : unavailable ? '🔇 音效不可用' : blocked ? '🔈 启用音效' : '🔊 音效开';
    button.setAttribute('aria-pressed', String(sound && !blocked && !unavailable));
    button.setAttribute('aria-label', !sound ? '开启音效并试听' : blocked ? '重新启用音效并试听' : unavailable ? '当前浏览器不支持音效，点击重试' : '关闭音效');
    button.title = unavailable ? '当前浏览器不支持音效' : blocked ? '点击重新启用音效并试听' : '吃到食物时会响一声；开启时可试听';
  }

  // Create and resume synchronously in a click/key/pointer gesture, before awaiting.
  function unlockAudio(preview = false) {
    if (!sound) return Promise.resolve(false);
    const revision = audioRevision;
    let context;
    try {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) {
        audioStatus = 'unsupported';
        updateSoundButton();
        return Promise.resolve(false);
      }
      if (!audio || audio.state === 'closed') audio = new Audio();
      context = audio;
      const resumed = context.state === 'running' ? Promise.resolve() : context.resume();
      return Promise.resolve(resumed).then(() => {
        if (!sound || revision !== audioRevision || context !== audio) return false;
        const ready = context.state === 'running';
        audioStatus = ready ? 'ready' : 'blocked';
        updateSoundButton();
        if (ready && preview) beep();
        return ready;
      }).catch(() => {
        if (sound && revision === audioRevision && context === audio) {
          audioStatus = 'blocked';
          updateSoundButton();
        }
        return false;
      });
    } catch {
      audioStatus = 'blocked';
      updateSoundButton();
      return Promise.resolve(false);
    }
  }

  function beep() {
    if (!sound) return;
    if (!audio || audio.state !== 'running') {
      audioStatus = 'blocked';
      updateSoundButton();
      return;
    }
    try {
      const oscillator = audio.createOscillator(), gain = audio.createGain();
      const now = audio.currentTime;
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(620, now);
      oscillator.frequency.exponentialRampToValueAtTime(880, now + 0.1);
      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(0.12, now + 0.005);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
      oscillator.connect(gain);
      gain.connect(audio.destination);
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
      oscillator.start(now);
      oscillator.stop(now + 0.15);
    } catch {
      audioStatus = 'blocked';
      updateSoundButton();
    }
  }

  $('#start').onclick = () => {
    $('#start').blur();
    unlockAudio(true);
    if (running && paused) pause(); else begin();
  };
  $('#sound').onclick = () => {
    $('#sound').blur();
    const retry = sound && (audioStatus === 'blocked' || audioStatus === 'unsupported');
    if (!retry) sound = !sound;
    audioRevision++;
    updateSoundButton();
    if (sound) unlockAudio(true);
  };
  updateSoundButton();
  const keyDirections = { ArrowUp: 'up', w: 'up', ArrowDown: 'down', s: 'down', ArrowLeft: 'left', a: 'left', ArrowRight: 'right', d: 'right' };
  document.addEventListener('keydown', event => {
    if (event.target.closest('select, input, textarea') || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.code === 'Space') {
      if (event.target.closest('button')) return;
      event.preventDefault();
      if (!event.repeat) pause();
    } else {
      const name = keyDirections[event.key] || keyDirections[event.key.toLowerCase()];
      if (!name) return;
      event.preventDefault();
      if (!event.repeat) {
        if (sound && audio?.state !== 'running') unlockAudio();
        setDirection(directions[name]);
      }
    }
  });
  document.querySelectorAll('.mobile-controls button').forEach(button => {
    button.addEventListener('pointerdown', event => {
      event.preventDefault();
      if (sound && audio?.state !== 'running') unlockAudio();
      setDirection(directions[button.dataset.dir]);
    });
  });

  // Turn as soon as the finger travels 10px, without waiting for it to lift.
  board.addEventListener('pointerdown', event => {
    if (!running || paused || pointer || event.button !== 0) return;
    if (sound && audio?.state !== 'running') unlockAudio();
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
    board.setPointerCapture(event.pointerId);
  });
  function swipe(event) {
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = event.clientX - pointer.x, dy = event.clientY - pointer.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 10) return;
    setDirection(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? directions.right : directions.left) : (dy > 0 ? directions.down : directions.up));
    pointer.x = event.clientX;
    pointer.y = event.clientY;
  }
  board.addEventListener('pointermove', swipe);
  board.addEventListener('pointerup', event => {
    if (pointer?.id !== event.pointerId) return;
    swipe(event);
    pointer = null;
  });
  for (const name of ['pointercancel', 'lostpointercapture']) board.addEventListener(name, event => {
    if (pointer?.id === event.pointerId) pointer = null;
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden && running && !paused) pause(); });
  mode.onchange = () => {
    const resume = running;
    running = false;
    paused = false;
    $('#mode-tip').textContent = tips[mode.value];
    reset();
    if (resume) begin();
  };
  speed.onchange = () => {
    // Preserve progress through the current step without adding another timer.
    nextStep = gameTime + Math.min(stepDuration(), Math.max(0, nextStep - gameTime));
  };
  reset();
})();
