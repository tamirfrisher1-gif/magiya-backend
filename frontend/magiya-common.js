/* ===========================================================
   MAGIYA — shared frontend helpers (no hardcoded guest data)
   Deterministic group → colour mapping, shared by the dashboard
   and the seating page so a group keeps the same colour everywhere.
   =========================================================== */
const MAGIYA_GROUP_COLORS = ['#6e1423', '#4f0d18', '#7a3b2e', '#3b3a52', '#5a4a38', '#2b2b2b'];
const _magiyaColorMap = {};
let _magiyaColorIdx = 0;

function magiyaGroupColor(group) {
  const key = group || 'Unassigned';
  if (!(key in _magiyaColorMap)) {
    _magiyaColorMap[key] = MAGIYA_GROUP_COLORS[_magiyaColorIdx % MAGIYA_GROUP_COLORS.length];
    _magiyaColorIdx++;
  }
  return _magiyaColorMap[key];
}
