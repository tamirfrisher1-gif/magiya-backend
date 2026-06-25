/* ===========================================================
   MAGIYA — Sign-up form → creates wedding in Supabase
   =========================================================== */
document.getElementById('signupForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg    = document.getElementById('signupMsg');
  const btn    = e.target.querySelector('button[type=submit]');
  const bride  = e.target.bride.value.trim();
  const groom  = e.target.groom.value.trim();
  const email  = e.target.email.value.trim();
  const date   = e.target.date.value; // YYYY-MM-DD

  btn.disabled = true;
  msg.textContent = 'Creating your account…';

  // Generate a stable wedding ID from names + date
  const weddingId = `${bride}-${groom}-${date}`
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');

  const { error } = await db.from('weddings').upsert({
    id: weddingId,
    bride_name: bride,
    groom_name: groom,
    contact_email: email,
    wedding_date: date,
    table_capacity: 10,
  }, { onConflict: 'id' });

  if (error) {
    msg.textContent = '❌ Something went wrong: ' + error.message;
    btn.disabled = false;
    return;
  }

  // Save to localStorage so other pages can use it
  localStorage.setItem('magiya_wedding_id', weddingId);
  localStorage.setItem('magiya_bride', bride);
  localStorage.setItem('magiya_groom', groom);
  localStorage.setItem('magiya_date', date);

  msg.textContent = '✅ Account created! Redirecting…';
  setTimeout(() => { window.location.href = 'guestlist.html'; }, 800);
});
