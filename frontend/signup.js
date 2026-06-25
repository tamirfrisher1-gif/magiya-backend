/* ===========================================================
   MAGIYA — Get Started
   Creates a wedding in Supabase (weddings table) from the onboarding
   form, or signs a returning couple in by their Wedding ID.
   Connects directly to Supabase via the browser anon key.
   =========================================================== */

const $ = (id) => document.getElementById(id);

/* ---------- Tabs ---------- */
const tabNew = $('tabNew');
const tabSignin = $('tabSignin');
const panelNew = $('panelNew');
const panelSignin = $('panelSignin');

function switchTab(toNew) {
  tabNew.classList.toggle('is-active', toNew);
  tabSignin.classList.toggle('is-active', !toNew);
  panelNew.classList.toggle('is-active', toNew);
  panelSignin.classList.toggle('is-active', !toNew);
}
tabNew.addEventListener('click', () => switchTab(true));
tabSignin.addEventListener('click', () => switchTab(false));

/* ---------- Wedding ID generation: bride-et-groom-dd-mm-yyyy ---------- */
// Unicode-aware slug: keeps Hebrew/Latin letters & digits, collapses the rest to "-".
function slug(s) {
  return (s || '')
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '');
}

function buildWeddingId(bride, groom, dateStr) {
  let datePart = '';
  if (dateStr) {
    const [yyyy, mm, dd] = dateStr.split('-');
    if (yyyy && mm && dd) datePart = `${dd}-${mm}-${yyyy}`;
  }
  return [slug(bride), 'et', slug(groom), datePart].filter(Boolean).join('-');
}

function refreshIdPreview() {
  const id = buildWeddingId($('brideName').value, $('groomName').value, $('weddingDate').value);
  $('idPreview').textContent = id || '—';
  return id;
}
['brideName', 'groomName', 'weddingDate'].forEach((f) =>
  $(f).addEventListener('input', refreshIdPreview)
);

/* ---------- Helpers ---------- */
function setStatus(el, msg, kind) {
  el.textContent = msg;
  el.className = 'status' + (kind ? ' status--' + kind : '');
}
function busy(btn, on, labelWhenBusy) {
  btn.disabled = on;
  if (on) { btn.dataset.label = btn.textContent; btn.textContent = labelWhenBusy; }
  else if (btn.dataset.label) { btn.textContent = btn.dataset.label; }
}
function noClient() {
  return !magiyaSupabase;
}
function rememberWedding(w) {
  try {
    localStorage.setItem('magiya_wedding_id', w.id);
    localStorage.setItem('magiya_wedding', JSON.stringify(w));
  } catch (e) { /* ignore storage errors */ }
}

/* ---------- Create wedding ---------- */
panelNew.addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = $('createStatus');

  if (noClient()) {
    return setStatus(status, '⚠ Could not load Supabase. Check your connection and refresh.', 'err');
  }

  const bride = $('brideName').value.trim();
  const groom = $('groomName').value.trim();
  const email = $('contactEmail').value.trim();
  const date = $('weddingDate').value;
  const venue = $('venue').value.trim();
  const id = refreshIdPreview();

  if (!bride || !groom || !email || !date || !venue || !id) {
    return setStatus(status, 'Please fill in every field.', 'err');
  }

  const btn = $('createBtn');
  busy(btn, true, 'Creating…');
  setStatus(status, '');

  const record = {
    id,
    bride_name: bride,
    groom_name: groom,
    wedding_date: date, // YYYY-MM-DD (Postgres date)
    venue,
    contact_email: email,
    table_capacity: 10,
  };

  const { data, error } = await magiyaSupabase
    .from('weddings')
    .upsert(record, { onConflict: 'id' })
    .select()
    .single();

  busy(btn, false);

  if (error) {
    setStatus(status, `Couldn't save your wedding: ${error.message}`, 'err');
    return;
  }

  rememberWedding(data || record);
  setStatus(status, '✓ Wedding created! Taking you to your guestlist…', 'ok');
  setTimeout(() => { window.location.href = 'guestlist.html'; }, 900);
});

/* ---------- Sign in (returning couple) ---------- */
panelSignin.addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = $('signinStatus');

  if (noClient()) {
    return setStatus(status, '⚠ Could not load Supabase. Check your connection and refresh.', 'err');
  }

  const id = $('signinId').value.trim().toLowerCase();
  if (!id) return setStatus(status, 'Enter your Wedding ID.', 'err');

  const btn = $('signinBtn');
  busy(btn, true, 'Checking…');
  setStatus(status, '');

  const { data, error } = await magiyaSupabase
    .from('weddings')
    .select('*')
    .eq('id', id)
    .maybeSingle();

  busy(btn, false);

  if (error) {
    setStatus(status, `Something went wrong: ${error.message}`, 'err');
    return;
  }
  if (!data) {
    setStatus(status, "We couldn't find a wedding with that ID. Double-check it, or create a new one.", 'err');
    return;
  }

  rememberWedding(data);
  setStatus(status, `✓ Welcome back, ${data.bride_name} & ${data.groom_name}!`, 'ok');
  setTimeout(() => { window.location.href = 'guestlist.html'; }, 900);
});

/* ---------- Init ---------- */
refreshIdPreview();
