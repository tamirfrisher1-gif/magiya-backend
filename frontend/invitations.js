/* ===========================================================
   MAGIYA — Send Invitations
   Fetches invited guests from the API and shows each one's
   personal Telegram deep-link so the couple can paste it
   into WhatsApp.
   =========================================================== */

const WEDDING_ID = localStorage.getItem('magiya_wedding_id') || null;
const API = (typeof MAGIYA_API_BASE !== 'undefined') ? MAGIYA_API_BASE : '';

const $ = (id) => document.getElementById(id);
const escapeHtml = (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const GROUP_COLORS = ['#6e1423', '#4f0d18', '#7a3b2e', '#3b3a52', '#5a4a38', '#2b2b2b'];
const colorMap = {};
let colorIdx = 0;
function groupColor(name) {
  const key = name || 'Unassigned';
  if (!(key in colorMap)) colorMap[key] = GROUP_COLORS[colorIdx++ % GROUP_COLORS.length];
  return colorMap[key];
}

let allGuests = [];

async function load() {
  if (!WEDDING_ID) {
    showBanner('⚠ No wedding found. <a href="signup.html">Sign up first</a> to generate your invitation links.', 'warn');
    $('invBody').innerHTML = '<tr><td colspan="5" class="inv__loading">No wedding session — please sign up first.</td></tr>';
    return;
  }

  try {
    const res = await fetch(`${API}/guests/invited?wedding_id=${encodeURIComponent(WEDDING_ID)}`, {
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    allGuests = await res.json();
    render(allGuests);
  } catch (err) {
    showBanner(`⚠ Couldn't load guests: ${escapeHtml(err.message)}. Make sure the API is running.`, 'warn');
    $('invBody').innerHTML = '<tr><td colspan="5" class="inv__loading">Failed to load — try refreshing.</td></tr>';
  }
}

function render(guests) {
  $('invCount').textContent = `${guests.length} guest${guests.length !== 1 ? 's' : ''} invited`;

  if (!guests.length) {
    $('invBody').innerHTML = '<tr><td colspan="5" class="inv__loading">No invited guests yet — go back to the guestlist and swipe!</td></tr>';
    return;
  }

  const rows = guests.map((g) => {
    const hasLink = !!g.invite_link;
    const linkCell = hasLink
      ? `<span class="inv__link">${escapeHtml(g.invite_link)}</span>`
      : `<span class="inv__nolink">Set BOT_USERNAME on Render</span>`;
    const copyBtn = hasLink
      ? `<button class="btn btn--copy" data-link="${escapeHtml(g.invite_link)}" title="Copy link">Copy</button>`
      : '';

    return `<tr>
      <td><span class="inv__name">${escapeHtml(g.full_name || 'Unknown')}</span></td>
      <td><span class="inv__badge" style="background:${groupColor(g.group_name)}">${escapeHtml(g.group_name || 'Unassigned')}</span></td>
      <td class="inv__phone">${escapeHtml(g.phone || '—')}</td>
      <td>${linkCell}</td>
      <td>${copyBtn}</td>
    </tr>`;
  }).join('');

  $('invBody').innerHTML = rows;

  $('invBody').querySelectorAll('.btn--copy').forEach((btn) => {
    btn.addEventListener('click', () => copyToClipboard(btn.dataset.link, btn));
  });
}

function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('btn--copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('btn--copied'); }, 1500);
  }).catch(() => {
    prompt('Copy this link:', text);
  });
}

$('copyAllBtn').addEventListener('click', () => {
  const links = allGuests
    .filter((g) => g.invite_link)
    .map((g) => `${g.full_name}: ${g.invite_link}`)
    .join('\n');

  if (!links) {
    alert('No links to copy — set BOT_USERNAME on Render first.');
    return;
  }
  navigator.clipboard.writeText(links).then(() => {
    const btn = $('copyAllBtn');
    btn.textContent = 'Copied all!';
    setTimeout(() => { btn.textContent = 'Copy all links'; }, 2000);
  });
});

function showBanner(html, kind) {
  const el = $('banner');
  el.innerHTML = html;
  el.className = `banner banner--${kind}`;
  el.hidden = false;
}

load();
