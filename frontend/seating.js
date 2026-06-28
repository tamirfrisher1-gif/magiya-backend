/* ===========================================================
   MAGIYA — Seating Arrangements
   - Define table KINDS (shape + seats); no counts.
   - Auto-seat confirmed guests, keeping each group together,
     adding as many tables of the given kinds as needed.
   - Drag guests between tables (and an Unseated tray) to adjust.
   - "Refresh from Dashboard" re-pulls guests and re-arranges.
   =========================================================== */

/* ---------- Group colours (shared with the dashboard) ---------- */
const colorForGroup = (name) => {
  if (typeof magiyaGroupColor === 'function') return magiyaGroupColor(name);
  return '#6e1423';
};

/* =========================================================
   DATA SOURCE — confirmed guests come from Supabase via the API:
     GET {MAGIYA_API_BASE}/guests/confirmed -> [{name, group, party_size}]
   Each confirmed party is expanded into party_size seats so the whole
   party is seated together. No hardcoded guests.
   ========================================================= */
async function getConfirmedGuests() {
  const base = (typeof MAGIYA_API_BASE !== 'undefined') ? MAGIYA_API_BASE : '';
  const weddingId = localStorage.getItem('magiya_wedding_id');
  const url = weddingId
    ? `${base}/guests/confirmed?wedding_id=${encodeURIComponent(weddingId)}`
    : `${base}/guests/confirmed`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  const data = await res.json(); // [{ name, group, party_size }]
  const out = [];
  data.forEach((g, gi) => {
    const size = (g.party_size && g.party_size > 0) ? g.party_size : 1;
    for (let i = 0; i < size; i++) {
      out.push({
        id: `c${gi}-${i}`,
        name: i === 0 ? g.name : `${g.name} +${i}`,
        group: g.group || 'Unassigned',
      });
    }
  });
  return out;
}

/* ---------- State ---------- */
let kinds = [];            // [{shape, seats}]
let confirmedGuests = [];  // pulled from the dashboard
let tables = [];           // [{id, shape, capacity, seats:[guest|null]}]
let unseated = [];         // guests with no seat
let selectedShape = 'round';

const $ = (id) => document.getElementById(id);
const screens = { setup: $('setup'), plan: $('plan') };
const firstName = (n) => n.split(' ')[0];
const initials = (n) => n.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();

/* =========================================================
   SCREEN 1 · DEFINE TABLE KINDS
   ========================================================= */
$('shapePick').addEventListener('click', (e) => {
  const btn = e.target.closest('.shapebtn');
  if (!btn) return;
  selectedShape = btn.dataset.shape;
  $('shapePick').querySelectorAll('.shapebtn').forEach((b) => b.classList.toggle('is-active', b === btn));
});

$('tableForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const seats = parseInt($('seatsInput').value, 10);
  if (seats >= 2) addKind(selectedShape, seats);
});

document.querySelectorAll('[data-shape][data-seats]').forEach((btn) => {
  btn.addEventListener('click', () => addKind(btn.dataset.shape, parseInt(btn.dataset.seats, 10)));
});

function addKind(shape, seats) {
  if (kinds.some((k) => k.shape === shape && k.seats === seats)) return; // no dupes
  kinds.push({ shape, seats });
  renderKinds();
}
function removeKind(idx) { kinds.splice(idx, 1); renderKinds(); }

function shapeLabel(shape) {
  return { round: 'Round', rectangle: 'Rectangle', square: 'Square' }[shape] || shape;
}

function renderKinds() {
  const list = $('kindList');
  list.querySelectorAll('.kindtag').forEach((el) => el.remove());
  $('kindEmpty').style.display = kinds.length ? 'none' : 'block';

  kinds.forEach((k, idx) => {
    const tag = document.createElement('span');
    tag.className = 'kindtag';
    tag.textContent = `${shapeLabel(k.shape)} · ${k.seats}`;
    const x = document.createElement('button');
    x.type = 'button';
    x.textContent = '✕';
    x.setAttribute('aria-label', 'Remove');
    x.addEventListener('click', () => removeKind(idx));
    tag.appendChild(x);
    list.appendChild(tag);
  });
  $('arrangeBtn').disabled = kinds.length === 0;
}

$('arrangeBtn').addEventListener('click', () => { refreshFromDashboard(); showScreen('plan'); });

/* =========================================================
   SCREEN NAVIGATION
   ========================================================= */
function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.remove('is-active'));
  screens[name].classList.add('is-active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
$('editBtn').addEventListener('click', () => showScreen('setup'));
$('refreshBtn').addEventListener('click', refreshFromDashboard);

/* =========================================================
   AUTO-ARRANGE — keep groups together, add tables as needed
   ========================================================= */
function chooseKind(need) {
  const fitting = kinds.filter((k) => k.seats >= need).sort((a, b) => a.seats - b.seats);
  if (fitting.length) return fitting[0];                 // smallest table the whole run fits in
  return [...kinds].sort((a, b) => b.seats - a.seats)[0]; // run too big — use the largest kind
}

function autoArrange() {
  tables = [];
  unseated = [];
  let tableNo = 0;

  // preserve group order as it appears in the guest list
  const order = [...new Set(confirmedGuests.map((g) => g.group))];
  order.forEach((groupName) => {
    let queue = confirmedGuests.filter((g) => g.group === groupName);
    while (queue.length) {
      const kind = chooseKind(queue.length);
      const seatArr = new Array(kind.seats).fill(null);
      const take = Math.min(kind.seats, queue.length);
      for (let i = 0; i < take; i++) seatArr[i] = queue[i];
      queue = queue.slice(take);
      tables.push({ id: ++tableNo, shape: kind.shape, capacity: kind.seats, seats: seatArr });
    }
  });
}

async function refreshFromDashboard() {
  if (!kinds.length) { showScreen('setup'); return; }
  setPlanLoading();
  try {
    confirmedGuests = await getConfirmedGuests();
  } catch (e) {
    confirmedGuests = [];
    showPlanError(e);
    return;
  }
  autoArrange();
  renderPlan();
}

function setPlanLoading() {
  $('planStats').textContent = 'Loading confirmed guests from the dashboard…';
  $('tables').innerHTML = '';
  $('tray').hidden = true;
}

function showPlanError(e) {
  $('planStats').textContent = '—';
  $('tables').innerHTML =
    `<p style="color:var(--muted);max-width:60ch">⚠ Couldn't load confirmed guests from the API ` +
    `(${escapeHtml(String(e.message || e))}). Start the backend ` +
    `(<code>uvicorn api.main:app --port 8001</code>) and make sure Supabase has data, ` +
    `then hit <em>Refresh from Dashboard</em>.</p>`;
}

/* =========================================================
   SCREEN 2 · RENDER PLAN
   ========================================================= */
function tableGroupName(table) {
  const groups = [...new Set(table.seats.filter(Boolean).map((g) => g.group))];
  if (groups.length === 0) return 'Empty';
  if (groups.length === 1) return groups[0];
  return 'Mixed';
}

function renderPlan() {
  const seated = tables.reduce((n, t) => n + t.seats.filter(Boolean).length, 0);
  $('planStats').textContent =
    `${seated} guests · ${tables.length} tables` + (unseated.length ? ` · ${unseated.length} unseated` : '');

  const wrap = $('tables');
  wrap.innerHTML = '';
  tables.forEach((table) => wrap.appendChild(buildTableCard(table)));

  renderTray();
}

function buildTableCard(table) {
  const card = document.createElement('div');
  card.className = 'table-card';
  card.dataset.tableId = table.id;

  const filled = table.seats.filter(Boolean).length;
  card.innerHTML = `
    <div class="table-card__head">
      <span class="table-card__name">Table ${table.id}</span>
      <span class="table-card__meta">${shapeLabel(table.shape)} · ${filled}/${table.capacity}</span>
    </div>
    <div class="table-card__group">${tableGroupName(table)}</div>`;

  const stage = document.createElement('div');
  stage.className = 'table-stage' + (table.shape === 'rectangle' ? ' table-stage--rect' : '');

  // central shape graphic
  const shape = document.createElement('div');
  const shapeClass = table.shape === 'round' ? 'round' : table.shape === 'square' ? 'square' : 'rect';
  shape.className = `table-shape table-shape--${shapeClass}`;
  shape.innerHTML = `<span class="table-shape__label">${table.id}</span>`;
  stage.appendChild(shape);

  // seats positioned around the shape
  table.seats.forEach((guest, seatIdx) => {
    const seat = document.createElement('div');
    const pos = seatPosition(table.shape, seatIdx, table.capacity);
    seat.style.left = pos.x + '%';
    seat.style.top = pos.y + '%';
    if (guest) {
      seat.className = 'seat seat--filled';
      seat.style.background = colorForGroup(guest.group);
      seat.textContent = guest.name;
      seat.title = `${guest.name} — ${guest.group}`;
      seat.draggable = true;
      seat.dataset.guestId = guest.id;
      seat.dataset.from = 'table:' + table.id + ':' + seatIdx;
      addDragSource(seat);
    } else {
      seat.className = 'seat seat--empty';
      seat.textContent = '+';
      seat.title = 'Empty seat';
    }
    stage.appendChild(seat);
  });

  card.appendChild(stage);

  // hover roster — full names of everyone seated here
  const seatedGuests = table.seats.filter(Boolean);
  const roster = document.createElement('div');
  roster.className = 'roster';
  roster.innerHTML =
    `<h4>Table ${table.id} · ${seatedGuests.length} seated</h4><ul>` +
    (seatedGuests.length
      ? seatedGuests.map((g) =>
          `<li><span class="dot" style="background:${colorForGroup(g.group)}"></span>` +
          `${escapeHtml(g.name)}<em>${escapeHtml(g.group)}</em></li>`).join('')
      : '<li>Empty table</li>') +
    '</ul>';
  card.appendChild(roster);

  addDropTarget(card, () => ({ kind: 'table', tableId: table.id }));
  return card;
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* Seat coordinates (percentages within the stage) */
function seatPosition(shape, i, count) {
  if (shape === 'rectangle') {
    const topCount = Math.ceil(count / 2);
    const botCount = count - topCount;
    if (i < topCount) {
      const x = topCount === 1 ? 50 : 12 + (76 * i) / (topCount - 1);
      return { x, y: 12 };
    }
    const j = i - topCount;
    const x = botCount === 1 ? 50 : 12 + (76 * j) / (botCount - 1);
    return { x, y: 88 };
  }
  // round / square — seats on an ellipse, starting at the top.
  // horizontal radius is tighter so long name pills don't run off the sides.
  const angle = (-90 + (360 * i) / count) * (Math.PI / 180);
  const rx = 34, ry = 44; // % radii
  return { x: 50 + rx * Math.cos(angle), y: 50 + ry * Math.sin(angle) };
}

/* ---------- Unseated tray ---------- */
function renderTray() {
  const tray = $('tray');
  const list = $('trayList');
  list.innerHTML = '';
  tray.hidden = false; // always available as a drop target for manual moves
  if (!unseated.length) {
    const p = document.createElement('span');
    p.className = 'tray__empty';
    p.textContent = 'Everyone is seated. Drag a guest here to set them aside.';
    list.appendChild(p);
  }
  unseated.forEach((guest, idx) => {
    const chip = document.createElement('div');
    chip.className = 'tray__chip';
    chip.style.background = colorForGroup(guest.group);
    chip.textContent = guest.name;
    chip.title = guest.group;
    chip.draggable = true;
    chip.dataset.guestId = guest.id;
    chip.dataset.from = 'tray:' + idx;
    addDragSource(chip);
    list.appendChild(chip);
  });
  addDropTarget(tray, () => ({ kind: 'tray' }));
}

/* =========================================================
   DRAG & DROP
   ========================================================= */
let dragInfo = null; // { guestId, from }

function addDragSource(el) {
  el.addEventListener('dragstart', (e) => {
    dragInfo = { guestId: el.dataset.guestId, from: el.dataset.from };
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', el.dataset.guestId);
    el.classList.add('is-dragging');
  });
  el.addEventListener('dragend', () => el.classList.remove('is-dragging'));
}

function addDropTarget(el, getTarget) {
  el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('is-drop'); });
  el.addEventListener('dragleave', () => el.classList.remove('is-drop'));
  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('is-drop');
    if (!dragInfo) return;
    const target = getTarget();
    // if dropped onto a specific seat, prefer that seat index
    const seatEl = e.target.closest('.seat');
    const seatIdx = seatEl && seatEl.parentElement ? [...seatEl.parentElement.children].indexOf(seatEl) - 1 : null;
    moveGuest(dragInfo, target, seatIdx);
    dragInfo = null;
  });
}

/* Resolve a guest + remove from its source location */
function takeFromSource(from) {
  const [type, a, b] = from.split(':');
  if (type === 'tray') {
    return unseated.splice(parseInt(a, 10), 1)[0];
  }
  const table = tables.find((t) => t.id === parseInt(a, 10));
  const idx = parseInt(b, 10);
  const guest = table.seats[idx];
  table.seats[idx] = null;
  return guest;
}

function moveGuest(info, target, seatIdx) {
  const guest = takeFromSource(info.from);
  if (!guest) { renderPlan(); return; }

  if (target.kind === 'tray') {
    unseated.push(guest);
    renderPlan();
    return;
  }

  // target is a table
  const table = tables.find((t) => t.id === target.tableId);
  let idx = (seatIdx != null && seatIdx >= 0 && seatIdx < table.capacity) ? seatIdx : -1;

  if (idx === -1) idx = table.seats.findIndex((s) => s === null); // first empty

  if (idx === -1) {
    // table full — return guest to where it came from (re-pull) by re-seating into unseated
    unseated.push(guest);
    renderPlan();
    flash(target.tableId);
    return;
  }

  const occupant = table.seats[idx];
  table.seats[idx] = guest;
  if (occupant) {
    // swap: send the displaced guest back to the dragged guest's old seat if possible
    const [type, a, b] = info.from.split(':');
    if (type === 'table') {
      const src = tables.find((t) => t.id === parseInt(a, 10));
      const srcIdx = parseInt(b, 10);
      if (src && src.seats[srcIdx] === null) src.seats[srcIdx] = occupant;
      else unseated.push(occupant);
    } else {
      unseated.push(occupant);
    }
  }
  renderPlan();
}

function flash(tableId) {
  const card = document.querySelector(`.table-card[data-table-id="${tableId}"]`);
  if (!card) return;
  card.classList.add('is-full');
  setTimeout(() => card.classList.remove('is-full'), 300);
}

/* ---------- Init ---------- */
renderKinds();
