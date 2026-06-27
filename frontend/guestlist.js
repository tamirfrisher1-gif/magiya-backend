/* ===========================================================
   MAGIYA — Create Your Guestlist
   Tinder-style sorting: name groups, then swipe to invite/skip.
   Loads real guests from Supabase; falls back to sample data.
   =========================================================== */

const WEDDING_ID = localStorage.getItem('magiya_wedding_id') || null;
const API = (typeof MAGIYA_API_BASE !== 'undefined') ? MAGIYA_API_BASE : '';

/* ---------- Import from Google Contacts ---------- */
document.getElementById('importGoogleBtn').addEventListener('click', () => {
  const params = new URLSearchParams({ wedding_id: WEDDING_ID || '' });
  window.location.href = `${API}/auth/google/start?${params.toString()}`;
});

(function showImportResultFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const banner = document.getElementById('importBanner');
  if (!banner) return;

  if (params.has('imported')) {
    const imported = params.get('imported');
    const skipped = params.get('skipped') || '0';
    banner.textContent = `✓ Imported ${imported} contact${imported === '1' ? '' : 's'} from Google` +
      (skipped !== '0' ? ` (skipped ${skipped} without a usable phone number).` : '.');
    banner.style.display = 'block';
  } else if (params.has('error')) {
    banner.textContent = `⚠ Google import failed: ${params.get('error')}`;
    banner.className = 'importBanner importBanner--error';
    banner.style.display = 'block';
  }

  if (params.has('imported') || params.has('error')) {
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, '', cleanUrl);
  }
})();

/* ---------- Sample contacts (fallback when no Supabase guests yet) ---------- */
const SAMPLE_CONTACTS = [
  { name: 'Maya Cohen',        phone: '054-201-8841' },
  { name: 'Daniel Levi',       phone: '052-774-1190' },
  { name: 'Noa Friedman',      phone: '050-668-3321' },
  { name: 'Itai Bar-On',       phone: '053-992-4410' },
  { name: 'Shira Mizrahi',     phone: '054-118-7763' },
  { name: 'Yonatan Peretz',    phone: '058-330-9921' },
  { name: 'Tamar Goldberg',    phone: '052-447-6650' },
  { name: 'Avi Shapiro',       phone: '050-810-2237' },
  { name: 'Lior Katz',         phone: '054-559-0014' },
  { name: 'Rotem Adler',       phone: '053-221-7788' },
  { name: 'Gal Hertz',         phone: '058-664-1102' },
  { name: 'Hila Ben-David',    phone: '052-903-5567' },
  { name: 'Omer Klein',        phone: '050-145-9923' },
  { name: 'Yael Rosen',        phone: '054-772-3340' },
  { name: 'Ariel Stern',       phone: '053-488-1276' },
  { name: 'Dana Weiss',        phone: '058-219-6604' },
];
let contacts = [...SAMPLE_CONTACTS]; // overwritten by loadContacts()

const AVATAR_COLORS = ['#6e1423', '#4f0d18', '#2b2b2b', '#7a3b2e', '#5a4a38', '#3b3a52'];

/* ---------- State ---------- */
let categories = [];          // group names
let activeCategory = null;    // group right-swipes file into
let index = 0;                // current contact pointer
let history = [];             // for undo: {index, decision, category}
const assignments = {};       // category -> [contact, ...]
let skipped = [];             // skipped contacts

/* ---------- Elements ---------- */
const $ = (id) => document.getElementById(id);
const screens = { setup: $('setup'), swipe: $('swipe'), summary: $('summary') };

/* =========================================================
   SCREEN 1 · SET UP GROUPS
   ========================================================= */
const groupInput = $('groupInput');
const groupList  = $('groupList');
const groupEmpty = $('groupEmpty');
const startBtn   = $('startBtn');

$('addGroupForm').addEventListener('submit', (e) => {
  e.preventDefault();
  addGroup(groupInput.value);
  groupInput.value = '';
  groupInput.focus();
});

document.querySelectorAll('[data-suggest]').forEach((btn) => {
  btn.addEventListener('click', () => addGroup(btn.dataset.suggest));
});

function addGroup(rawName) {
  const name = rawName.trim();
  if (!name) return;
  if (categories.some((c) => c.toLowerCase() === name.toLowerCase())) return; // no dupes
  categories.push(name);
  renderGroups();
}

function removeGroup(name) {
  categories = categories.filter((c) => c !== name);
  renderGroups();
}

function renderGroups() {
  groupList.querySelectorAll('.grouptag').forEach((el) => el.remove());
  groupEmpty.style.display = categories.length ? 'none' : 'block';

  categories.forEach((name) => {
    const tag = document.createElement('span');
    tag.className = 'grouptag';
    tag.textContent = name;
    const x = document.createElement('button');
    x.type = 'button';
    x.setAttribute('aria-label', 'Remove ' + name);
    x.textContent = '✕';
    x.addEventListener('click', () => removeGroup(name));
    tag.appendChild(x);
    groupList.appendChild(tag);
  });

  startBtn.disabled = categories.length === 0;
}

startBtn.addEventListener('click', startSwiping);

/* =========================================================
   SCREEN NAVIGATION
   ========================================================= */
function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.remove('is-active'));
  screens[name].classList.add('is-active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* =========================================================
   SCREEN 2 · SWIPE
   ========================================================= */
const deck         = $('deck');
const progressText = $('progressText');
const progressFill = $('progressFill');
const activeName   = $('activeName');
const filingChips  = $('filingChips');
const undoBtn      = $('undoBtn');

function startSwiping() {
  // reset run state
  index = 0;
  history = [];
  skipped = [];
  categories.forEach((c) => (assignments[c] = []));
  activeCategory = categories[0];

  renderFilingChips();
  renderDeck();
  updateProgress();
  showScreen('swipe');
}

function renderFilingChips() {
  filingChips.innerHTML = '';
  categories.forEach((name) => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.textContent = name;
    chip.setAttribute('aria-pressed', name === activeCategory);
    chip.addEventListener('click', () => {
      activeCategory = name;
      renderFilingChips();
    });
    filingChips.appendChild(chip);
  });
  activeName.textContent = activeCategory || '—';
}

function initials(name) {
  return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
}

function renderDeck() {
  deck.innerHTML = '';
  // render up to 3 cards, top card last so it stacks on top
  const slice = contacts.slice(index, index + 3).reverse();
  slice.forEach((contact, i) => {
    const realIdx = index + (slice.length - 1 - i);
    const card = buildCard(contact, realIdx);
    // slight stacking offset for the cards beneath
    const depth = slice.length - 1 - i;
    card.style.transform = `translateY(${depth * 8}px) scale(${1 - depth * 0.03})`;
    card.style.zIndex = i;
    deck.appendChild(card);
  });
  const top = deck.lastElementChild;
  if (top) enableDrag(top);
}

function buildCard(contact, realIdx) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.idx = realIdx;

  const avatar = document.createElement('div');
  avatar.className = 'card__avatar';
  avatar.style.background = AVATAR_COLORS[realIdx % AVATAR_COLORS.length];
  avatar.textContent = initials(contact.name);

  const name = document.createElement('div');
  name.className = 'card__name';
  name.textContent = contact.name;

  const meta = document.createElement('div');
  meta.className = 'card__meta';
  meta.textContent = contact.phone;

  const invStamp = document.createElement('div');
  invStamp.className = 'card__stamp card__stamp--invite';
  invStamp.textContent = 'INVITE';

  const skipStamp = document.createElement('div');
  skipStamp.className = 'card__stamp card__stamp--skip';
  skipStamp.textContent = 'SKIP';

  card.append(invStamp, skipStamp, avatar, name, meta);
  return card;
}

/* ---------- Drag handling (pointer events) ---------- */
function enableDrag(card) {
  let startX = 0, startY = 0, dx = 0, dragging = false;
  const invStamp = card.querySelector('.card__stamp--invite');
  const skipStamp = card.querySelector('.card__stamp--skip');

  const onDown = (e) => {
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    card.setPointerCapture(e.pointerId);
    card.style.transition = 'none';
  };

  const onMove = (e) => {
    if (!dragging) return;
    dx = e.clientX - startX;
    const dy = e.clientY - startY;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx * 0.05}deg)`;
    const ratio = Math.min(Math.abs(dx) / 120, 1);
    invStamp.style.opacity = dx > 0 ? ratio : 0;
    skipStamp.style.opacity = dx < 0 ? ratio : 0;
  };

  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    card.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
    if (dx > 120) commit('invite', card);
    else if (dx < -120) commit('skip', card);
    else {
      // snap back
      card.style.transform = '';
      invStamp.style.opacity = 0;
      skipStamp.style.opacity = 0;
      dx = 0;
    }
  };

  card.addEventListener('pointerdown', onDown);
  card.addEventListener('pointermove', onMove);
  card.addEventListener('pointerup', onUp);
  card.addEventListener('pointercancel', onUp);
}

/* ---------- Commit a decision ---------- */
function commit(decision, card) {
  const contact = contacts[index];
  if (!contact) return;

  // animate the (top) card off screen
  const topCard = card || deck.lastElementChild;
  if (topCard) {
    topCard.style.transition = 'transform 0.35s ease, opacity 0.35s ease';
    const dir = decision === 'invite' ? 1 : -1;
    topCard.style.transform = `translate(${dir * 600}px, -40px) rotate(${dir * 25}deg)`;
    topCard.style.opacity = '0';
  }

  if (decision === 'invite') {
    assignments[activeCategory].push({ ...contact, group: activeCategory });
    history.push({ index, decision, category: activeCategory });
  } else {
    skipped.push(contact);
    history.push({ index, decision, category: null });
  }

  index++;
  undoBtn.disabled = history.length === 0;

  setTimeout(() => {
    if (index >= contacts.length) {
      buildSummary();
      showScreen('summary');
    } else {
      renderDeck();
      updateProgress();
    }
  }, 220);
}

function updateProgress() {
  progressText.textContent = `${index} / ${contacts.length}`;
  progressFill.style.width = (index / contacts.length) * 100 + '%';
}

/* ---------- Undo ---------- */
function undo() {
  const last = history.pop();
  if (!last) return;
  if (last.decision === 'invite') {
    assignments[last.category].pop();
  } else {
    skipped.pop();
  }
  index = last.index;
  undoBtn.disabled = history.length === 0;
  renderDeck();
  updateProgress();
}

/* ---------- Buttons + keyboard ---------- */
$('skipBtn').addEventListener('click', () => commit('skip'));
$('inviteBtn').addEventListener('click', () => commit('invite'));
undoBtn.addEventListener('click', undo);

document.addEventListener('keydown', (e) => {
  if (!screens.swipe.classList.contains('is-active')) return;
  if (e.key === 'ArrowLeft') commit('skip');
  else if (e.key === 'ArrowRight') commit('invite');
  else if (e.key === 'Backspace') { e.preventDefault(); undo(); }
  else if (/^[1-9]$/.test(e.key)) {
    const i = parseInt(e.key, 10) - 1;
    if (categories[i]) { activeCategory = categories[i]; renderFilingChips(); }
  }
});

/* =========================================================
   SCREEN 3 · SUMMARY
   ========================================================= */
function buildSummary() {
  const grid = $('summaryGrid');
  grid.innerHTML = '';
  const invited = categories.reduce((n, c) => n + assignments[c].length, 0);
  $('summaryLead').textContent =
    `${invited} guests invited across ${categories.length} groups · ${skipped.length} skipped.`;

  categories.forEach((cat) => {
    const people = assignments[cat];
    const box = document.createElement('div');
    box.className = 'summary__group';
    box.innerHTML = `
      <h3>${escapeHtml(cat)}</h3>
      <div class="summary__count">${people.length}</div>
      <div class="summary__names">${people.map((p) => escapeHtml(p.name)).join(', ') || '—'}</div>`;
    grid.appendChild(box);
  });

  if (skipped.length) {
    const box = document.createElement('div');
    box.className = 'summary__group summary__group--skip';
    box.innerHTML = `
      <h3>Skipped</h3>
      <div class="summary__count">${skipped.length}</div>
      <div class="summary__names">${skipped.map((p) => escapeHtml(p.name)).join(', ')}</div>`;
    grid.appendChild(box);
  }
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

$('sendBtn').addEventListener('click', async () => {
  const btn = $('sendBtn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    if (WEDDING_ID && typeof db !== 'undefined') {
      // Save each group name to the groups table
      for (const cat of categories) {
        await db.from('groups').upsert(
          { wedding_id: WEDDING_ID, name: cat },
          { onConflict: 'wedding_id,name' }
        );
      }

      // Update group_name for each invited guest in Supabase
      for (const cat of categories) {
        for (const contact of (assignments[cat] || [])) {
          if (contact.phone) {
            await db.from('guests')
              .update({ group_name: cat, wedding_id: WEDDING_ID })
              .eq('phone', contact.phone.replace(/[-\s]/g, ''));
          }
        }
      }

      btn.textContent = '✅ Saved!';
      setTimeout(() => { window.location.href = 'dashboard.html'; }, 1000);
    } else {
      // No Supabase session — just show success for demo
      btn.textContent = '✅ Saved!';
      alert('🎉 Guestlist saved! (Demo mode — sign up to connect to Supabase)');
      btn.disabled = false;
    }
  } catch (err) {
    btn.textContent = '❌ Error — try again';
    btn.disabled = false;
    console.error(err);
  }
});

$('restartBtn').addEventListener('click', () => {
  index = 0; history = []; skipped = [];
  showScreen('setup');
});

/* ---------- Init — load guests from Supabase or use samples ---------- */
async function loadContacts() {
  if (WEDDING_ID && typeof db !== 'undefined') {
    const { data, error } = await db
      .from('guests')
      .select('full_name, phone')
      .eq('wedding_id', WEDDING_ID);

    if (!error && data && data.length > 0) {
      contacts = data.map((g) => ({ name: g.full_name || 'Unknown', phone: g.phone }));
    }
    // else keep SAMPLE_CONTACTS fallback
  }
  renderGroups();
}

loadContacts();
