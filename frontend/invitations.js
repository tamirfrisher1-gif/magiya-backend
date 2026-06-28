/* ===========================================================
   MAGIYA — Send Invitations
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

/* =========================================================
   CUSTOMISE INVITATION MESSAGE
   ========================================================= */
async function loadWeddingCustomisation() {
  if (!WEDDING_ID || !magiyaSupabase) return;
  const { data } = await magiyaSupabase
    .from('weddings')
    .select('bride_name, groom_name, invitation_text, invitation_image_url')
    .eq('id', WEDDING_ID)
    .maybeSingle();
  if (!data) return;

  const defaultText = `שלום! הוזמנת לחתונה של ${data.bride_name} ו${data.groom_name}. אנו שמחים להזמינך לחגוג איתנו את היום המיוחד שלנו 💍`;
  $('invText').value = data.invitation_text || defaultText;
  if (data.invitation_image_url) {
    $('invImageUrl').value = data.invitation_image_url;
    showPreview(data.invitation_image_url);
    $('photoStatus').textContent = '✓ Photo saved';
  }

  // If message was already saved before, skip to step 2
  if (data.invitation_text) {
    showStep(2);
    load();
  }
}

$('pickPhotoBtn').addEventListener('click', () => $('invPhoto').click());

$('invPhoto').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;

  $('photoStatus').textContent = 'Processing…';
  $('pickPhotoBtn').disabled = true;

  const img = new Image();
  const objectUrl = URL.createObjectURL(file);

  img.onload = () => {
    URL.revokeObjectURL(objectUrl);
    const MAX = 800;
    let w = img.width, h = img.height;
    if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d').drawImage(img, 0, 0, w, h);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.75);
    showPreview(dataUrl);
    $('invImageUrl').value = dataUrl;
    $('photoStatus').textContent = '✓ Photo ready';
    $('pickPhotoBtn').disabled = false;
  };

  img.onerror = () => {
    URL.revokeObjectURL(objectUrl);
    $('photoStatus').textContent = '⚠ Could not load image';
    $('pickPhotoBtn').disabled = false;
  };

  img.src = objectUrl;
});

$('removePhotoBtn').addEventListener('click', () => {
  $('invPhoto').value = '';
  $('invImageUrl').value = '';
  $('previewBox').hidden = true;
  $('photoStatus').textContent = '';
});

function showPreview(url) {
  $('previewImg').src = url;
  $('previewBox').hidden = false;
}

$('saveCustomBtn').addEventListener('click', async () => {
  const btn = $('saveCustomBtn');
  const status = $('customStatus');
  if (!WEDDING_ID || !magiyaSupabase) {
    status.textContent = '⚠ Sign up first to save your message.';
    return;
  }
  btn.disabled = true;
  status.textContent = 'Saving…';

  const { error } = await magiyaSupabase
    .from('weddings')
    .update({
      invitation_text: $('invText').value.trim() || null,
      invitation_image_url: $('invImageUrl').value.trim() || null,
    })
    .eq('id', WEDDING_ID);

  btn.disabled = false;
  if (error) {
    status.textContent = '❌ Could not save: ' + error.message;
  } else {
    showStep(2);
    load();
  }
});

$('editMsgBtn').addEventListener('click', () => showStep(1));

function showStep(n) {
  $('step1').hidden = n !== 1;
  $('step2').hidden = n !== 2;
}

/* =========================================================
   GUEST LIST + LINKS
   ========================================================= */
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
    showBanner(`⚠ Couldn't load guests: ${escapeHtml(err.message)}.`, 'warn');
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
  }).catch(() => { prompt('Copy this link:', text); });
}

$('copyAllBtn').addEventListener('click', () => {
  const links = allGuests.filter((g) => g.invite_link).map((g) => `${g.full_name}: ${g.invite_link}`).join('\n');
  if (!links) { alert('No links to copy — set BOT_USERNAME on Render first.'); return; }
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

loadWeddingCustomisation();

/* =========================================================
   AI CHAT WIDGET — Invitation Image Generator
   ========================================================= */
(function initAIChat() {
  const panel   = $('aiChatPanel');
  const msgs    = $('aiChatMessages');
  const quick   = $('aiChatQuick');
  const inputRow = $('aiChatInputRow');
  const input   = $('aiChatInput');

  // Chat state
  let state = 'idle'; // idle → description → style → colors → generating → preview → feedback
  let params = { description: '', style: '', colors: '' };
  let weddingInfo = { bride: '', groom: '', date: '' };

  // Open / close
  $('aiChatBtn').addEventListener('click', () => {
    panel.hidden = false;
    $('aiChatBtn').hidden = true;
    if (state === 'idle') startChat();
  });
  $('aiChatClose').addEventListener('click', () => {
    panel.hidden = true;
    $('aiChatBtn').hidden = false;
  });

  // Send on Enter
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(); });
  $('aiChatSend').addEventListener('click', sendText);

  function sendText() {
    const val = input.value.trim();
    if (!val) return;
    input.value = '';
    addMsg(val, 'user');
    handleUserText(val);
  }

  function handleUserText(text) {
    if (state === 'description') {
      params.description = text;
      hideInput();
      askStyle();
    } else if (state === 'colors_free') {
      params.colors = text;
      hideInput();
      generate();
    } else if (state === 'feedback') {
      params.description = params.description
        ? params.description + '. ' + text
        : text;
      generate();
    }
  }

  // ── Conversation steps ──────────────────────────────────
  function startChat() {
    state = 'description';
    botMsg('Hi! 💍 Describe your wedding in one line — names, location, date.<br><em>e.g. "Eden &amp; Eyal, Paris, July 10th"</em>');
    input.placeholder = 'Eden & Eyal, Paris, July 10th…';
    showInput();
  }

  function askStyle() {
    botMsg('Perfect! What style do you prefer?');
    state = 'style';
    setQuick([
      { label: '🌸 Floral',   value: 'floral' },
      { label: '✨ Élégant',  value: 'elegant' },
      { label: '🌿 Rustique', value: 'rustic' },
      { label: '◼ Moderne',   value: 'modern' },
    ], (val, label) => {
      params.style = val;
      addMsg(label, 'user');
      askColors();
    });
  }

  function askColors() {
    botMsg('Great! What color palette?');
    state = 'colors';
    setQuick([
      { label: '🤍 White & Gold',        value: 'white and gold' },
      { label: '🌸 Blush Pink & Ivory',  value: 'blush pink and ivory' },
      { label: '🍷 Burgundy & Cream',    value: 'burgundy and cream' },
      { label: '🌊 Navy & Silver',       value: 'navy and silver' },
      { label: '✏️ Other…',              value: '__free__' },
    ], (val, label) => {
      if (val === '__free__') {
        state = 'colors_free';
        clearQuick();
        showInput();
        addMsg(label, 'user');
        botMsg('Describe your palette (e.g. "sage green and terracotta"):');
        input.placeholder = 'Your color palette…';
      } else {
        params.colors = val;
        addMsg(label, 'user');
        generate();
      }
    });
  }

  async function generate() {
    state = 'generating';
    hideInput();
    clearQuick();
    const typingEl = addTyping();

    try {
      const res = await fetch(`${API}/invitations/generate-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: params.description,
          style: params.style,
          colors: params.colors,
        }),
      });
      typingEl.remove();
      if (!res.ok) throw new Error(`API ${res.status}`);
      const { image } = await res.json();
      showImagePreview(image);
    } catch (e) {
      typingEl.remove();
      botMsg('⚠️ Generation failed. Make sure the OpenAI API key is set on Render.');
      state = 'idle';
    }
  }

  function showImagePreview(dataUrl) {
    state = 'preview';
    // Image bubble
    const wrap = document.createElement('div');
    wrap.className = 'ai-msg ai-msg--img';
    const img = document.createElement('img');
    img.src = dataUrl;
    img.alt = 'Invitation générée';
    wrap.appendChild(img);

    // "Utiliser" button
    const useBtn = document.createElement('button');
    useBtn.className = 'ai-use-btn';
    useBtn.textContent = '✅ Use this photo';
    useBtn.addEventListener('click', () => {
      showPreview(dataUrl);
      $('invImageUrl').value = dataUrl;
      $('photoStatus').textContent = '✓ AI-generated photo';
      panel.hidden = true;
      $('aiChatBtn').hidden = false;
      botMsg('Photo added! Click <strong>Save & see my links</strong> to continue. 🎉');
    });

    // "Modify" button
    const regenBtn = document.createElement('button');
    regenBtn.className = 'ai-regen-btn';
    regenBtn.textContent = '🔄 Modify';
    regenBtn.addEventListener('click', () => {
      state = 'feedback';
      clearQuick();
      showInput();
      input.placeholder = 'E.g. more flowers, lighter background, add doves…';
      botMsg('What would you like to change?');
    });

    msgs.appendChild(wrap);
    msgs.appendChild(useBtn);
    msgs.appendChild(regenBtn);
    msgs.scrollTop = msgs.scrollHeight;
  }

  // ── Helpers ─────────────────────────────────────────────
  function botMsg(html) {
    const el = document.createElement('div');
    el.className = 'ai-msg ai-msg--bot';
    el.innerHTML = html;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  function addMsg(text, who) {
    const el = document.createElement('div');
    el.className = `ai-msg ai-msg--${who}`;
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function addTyping() {
    const el = document.createElement('div');
    el.className = 'ai-typing';
    el.innerHTML = '<span></span><span></span><span></span>';
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  function setQuick(options, onClick) {
    quick.innerHTML = '';
    inputRow.hidden = true;
    options.forEach(({ label, value }) => {
      const btn = document.createElement('button');
      btn.className = 'ai-quick-btn';
      btn.textContent = label;
      btn.addEventListener('click', () => {
        quick.innerHTML = '';
        onClick(value, label);
      });
      quick.appendChild(btn);
    });
  }

  function clearQuick() { quick.innerHTML = ''; }
  function showInput()  { inputRow.hidden = false; input.focus(); }
  function hideInput()  { inputRow.hidden = true; }
})();
