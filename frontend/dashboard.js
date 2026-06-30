/* ===========================================================
   MAGIYA — Live Dashboard
   Fetches the aggregated RSVP payload from the FastAPI backend
   (GET {MAGIYA_API_BASE}/dashboard) and renders it. No hardcoded
   guests — data comes from Supabase via the API.

   Contract (see api/README.md):
   { summary:{invited,confirmed,declined,no_response,expected_headcount},
     status_breakdown:{confirmed,declined,pending},
     dietary_breakdown:{vegetarian,vegan,kosher,celiac,none},
     by_group:[{group,invited,confirmed,expected}],
     recent_updates:[{name,group,status,party_size,responded_at}] }
   =========================================================== */

const $ = (id) => document.getElementById(id);
const API = (typeof MAGIYA_API_BASE !== 'undefined') ? MAGIYA_API_BASE : '';
const WEDDING_ID = localStorage.getItem('magiya_wedding_id') || null;

const STATUS = {
  confirmed: { label: 'Coming',         color: '#6e1423', badge: 'badge--coming' },
  pending:   { label: 'Awaiting reply', color: '#c98a2e', badge: 'badge--pending' },
  declined:  { label: 'Declined',       color: '#2b2b2b', badge: 'badge--declined' },
};

const initials = (n) => (n || '?').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
const groupColor = (g) => (typeof magiyaGroupColor === 'function' ? magiyaGroupColor(g) : '#6e1423');
const escapeHtml = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

const EMPTY = {
  summary: { invited: 0, confirmed: 0, declined: 0, no_response: 0, expected_headcount: 0 },
  status_breakdown: { confirmed: 0, declined: 0, pending: 0 },
  dietary_breakdown: { vegetarian: 0, vegan: 0, kosher: 0, celiac: 0, none: 0 },
  by_group: [],
  recent_updates: [],
};

// Ordered list of meal categories shown on the dashboard, with display labels.
const DIET = [
  { k: 'none', label: 'Regular' },
  { k: 'vegetarian', label: 'Vegetarian' },
  { k: 'vegan', label: 'Vegan' },
  { k: 'kosher', label: 'Glatt kosher' },
  { k: 'celiac', label: 'Celiac / gluten-free' },
];

/* ---------- Load ---------- */
async function load() {
  const btn = $('refreshBtn');
  if (btn) { btn.disabled = true; btn.textContent = '↻ Refreshing…'; }
  try {
    const url = WEDDING_ID
      ? `${API}/dashboard?wedding_id=${encodeURIComponent(WEDDING_ID)}`
      : `${API}/dashboard`;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`API responded ${res.status}`);
    render(await res.json());
  } catch (err) {
    showError(err);
    render(EMPTY);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↻ Refresh'; }
  }
}

function showError(err) {
  $('banner').innerHTML =
    `⚠ Couldn't reach the MAGIYA API at <code>${escapeHtml(API)}/dashboard</code>. ` +
    `Start the backend (<code>uvicorn api.main:app --port 8001</code>) and make sure Supabase has data — ` +
    `then reload. <span class="banner__err">(${escapeHtml(err.message || err)})</span>`;
  $('banner').classList.add('banner--error');
}

/* ---------- Render ---------- */
function render(data) {
  const s = data.summary || EMPTY.summary;
  const sb = data.status_breakdown || EMPTY.status_breakdown;
  const invited = s.invited || 0;

  // Stat cards
  $('stats').innerHTML = [
    { num: s.invited, label: 'Invited', cls: '' },
    { num: s.confirmed, label: 'Attending', cls: 'stat--coming' },
    { num: sb.pending, label: 'Awaiting reply', cls: 'stat--await' },
    { num: s.declined, label: 'Declined', cls: 'stat--declined' },
  ].map((c) => `<div class="stat ${c.cls}"><div class="stat__num">${c.num || 0}</div><div class="stat__label">${c.label}</div></div>`).join('');

  // Progress
  const responded = (s.confirmed || 0) + (s.declined || 0);
  const pct = invited ? Math.round((responded / invited) * 100) : 0;
  $('progPct').textContent = pct + '%';
  $('progFill').style.width = pct + '%';
  $('progNote').textContent =
    `${responded} of ${invited} guests responded · ${s.confirmed || 0} attending` +
    ` · ${s.expected_headcount || 0} expected headcount · ${sb.pending || 0} awaiting.`;

  // Donut
  renderDonut(sb, invited, s.confirmed || 0);

  // Food preferences
  renderDiet(data.dietary_breakdown || EMPTY.dietary_breakdown);

  // By group
  const rows = (data.by_group || []).map((g) =>
    `<tr><td><span class="g-dot" style="background:${groupColor(g.group)}"></span>${escapeHtml(g.group)}</td>` +
    `<td>${g.invited}</td><td>${g.confirmed}</td><td>${g.expected}</td></tr>`).join('');
  $('groupRows').innerHTML = rows || `<tr><td colspan="4" style="color:var(--muted)">No guests yet.</td></tr>`;
  const tot = (data.by_group || []).reduce((a, g) => ({ inv: a.inv + g.invited, con: a.con + g.confirmed, exp: a.exp + g.expected }), { inv: 0, con: 0, exp: 0 });
  $('groupFoot').innerHTML = `<tr><td>Total</td><td>${tot.inv}</td><td>${tot.con}</td><td>${tot.exp}</td></tr>`;

  // Recent updates
  const feed = (data.recent_updates || []).map((u) => {
    const st = STATUS[u.status] || STATUS.pending;
    const party = (u.status === 'confirmed' && u.party_size > 1) ? ` · party of ${u.party_size}` : '';
    return `<div class="feed__row">
      <div class="feed__who">
        <span class="feed__avatar" style="background:${groupColor(u.group)}">${initials(u.name)}</span>
        <div><div class="feed__name">${escapeHtml(u.name)}</div><div class="feed__group">${escapeHtml(u.group)}${party}</div></div>
      </div>
      <span class="feed__time">${fmtTime(u.responded_at)}</span>
      <span class="badge ${st.badge}">${st.label}</span>
    </div>`;
  }).join('');
  $('feed').innerHTML = feed || `<p style="color:var(--muted)">No responses yet.</p>`;
}

function renderDiet(db) {
  const total = DIET.reduce((sum, d) => sum + (db[d.k] || 0), 0);
  $('diet').innerHTML = DIET.map((d) => {
    const v = db[d.k] || 0;
    const pct = total ? Math.round((v / total) * 100) : 0;
    return `<div class="stat"><div class="stat__num">${v}</div>` +
      `<div class="stat__label">${d.label} · ${pct}%</div></div>`;
  }).join('');
}

function renderDonut(sb, invited, centerVal) {
  const donut = $('donut');
  if (!invited) {
    donut.style.background = 'var(--paper-2)';
  } else {
    const segs = [
      { k: 'confirmed', v: sb.confirmed || 0 },
      { k: 'pending', v: sb.pending || 0 },
      { k: 'declined', v: sb.declined || 0 },
    ].filter((x) => x.v > 0);
    let acc = 0;
    const stops = segs.map((x) => {
      const a = (acc / invited) * 360; acc += x.v; const b = (acc / invited) * 360;
      return `${STATUS[x.k].color} ${a}deg ${b}deg`;
    });
    donut.style.background = `conic-gradient(${stops.join(', ')})`;
  }
  $('donutCenter').textContent = centerVal;

  $('legend').innerHTML = ['confirmed', 'pending', 'declined'].map((k) => {
    const v = sb[k] || 0;
    const pct = invited ? Math.round((v / invited) * 100) : 0;
    return `<li><span class="dot" style="background:${STATUS[k].color}"></span>${STATUS[k].label} <b>${v}</b> · ${pct}%</li>`;
  }).join('');
}

/* ---------- Add a guest manually ---------- */
async function loadGroups() {
  const sel = $('agGroup');
  if (!sel || !WEDDING_ID) return;
  try {
    const res = await fetch(`${API}/groups?wedding_id=${encodeURIComponent(WEDDING_ID)}`,
      { headers: { Accept: 'application/json' } });
    const groups = res.ok ? await res.json() : [];
    populateGroupSelect(Array.isArray(groups) ? groups : []);
  } catch {
    populateGroupSelect([]);
  }
}

function populateGroupSelect(groups) {
  const sel = $('agGroup');
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = groups.length
    ? groups.map((g) => `<option value="${escapeHtml(g)}">${escapeHtml(g)}</option>`).join('')
    : `<option value="" disabled selected>No groups yet — build your guestlist first</option>`;
  if (current && groups.includes(current)) sel.value = current;
}

function agSetMsg(text, isError) {
  const el = $('agMsg');
  if (!el) return;
  el.textContent = text || '';
  el.style.color = isError ? '#b3261e' : 'var(--muted)';
}

async function handleAddGuest(e) {
  e.preventDefault();
  const btn = $('agSubmit');
  const result = $('agResult');
  result.hidden = true; result.innerHTML = '';
  agSetMsg('');

  if (!WEDDING_ID) {
    agSetMsg('No wedding selected — open this dashboard from your wedding to add guests.', true);
    return;
  }
  const full_name = $('agName').value.trim();
  const phone = $('agPhone').value.trim();
  const group_name = $('agGroup').value;
  if (!full_name || !phone || !group_name) {
    agSetMsg('Please fill in name, phone and group.', true);
    return;
  }

  btn.disabled = true; btn.textContent = 'Adding…';
  try {
    const res = await fetch(`${API}/guests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ wedding_id: WEDDING_ID, full_name, phone, group_name }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      if (data.invite_link) {
        showInviteResult(`✓ ${escapeHtml(full_name)} added.`, data.invite_link);
      } else {
        agSetMsg(`✓ ${full_name} added — but no invite link was generated here (the bot username isn't configured locally; links work on the live site).`, false);
      }
      $('agName').value = ''; $('agPhone').value = '';
      load(); // refresh counts / by-group
    } else if (res.status === 409) {
      const d = data.detail || {};
      showInviteResult(escapeHtml(d.message || 'This guest is already in your list.'),
        d.guest && d.guest.invite_link, true);
    } else if (res.status === 400) {
      agSetMsg(typeof data.detail === 'string' ? data.detail : 'Invalid input.', true);
    } else {
      agSetMsg(`Couldn't add guest (error ${res.status}).`, true);
    }
  } catch (err) {
    agSetMsg(`Network error: ${err.message || err}`, true);
  } finally {
    btn.disabled = false; btn.textContent = 'Add & create link';
  }
}

function showInviteResult(label, link, isWarning) {
  const result = $('agResult');
  if (!link) { agSetMsg(label, isWarning); return; }
  result.hidden = false;
  result.innerHTML =
    `<div class="addguest__ok">${label}</div>` +
    `<div class="addguest__link"><code id="agLink">${escapeHtml(link)}</code>` +
    `<button type="button" class="btn btn--outline" id="agCopy">Copy link</button></div>`;
  const copyBtn = $('agCopy');
  copyBtn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(link); copyBtn.textContent = 'Copied!'; }
    catch { copyBtn.textContent = 'Copy failed'; }
    setTimeout(() => { copyBtn.textContent = 'Copy link'; }, 1500);
  });
}

/* ---------- Init ---------- */
const refreshBtn = $('refreshBtn');
if (refreshBtn) refreshBtn.addEventListener('click', load);
const addGuestForm = $('addGuestForm');
if (addGuestForm) addGuestForm.addEventListener('submit', handleAddGuest);
loadGroups();
load();
