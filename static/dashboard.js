// ═══════════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════════
let sensors = {};
let layout  = { preset: '1col', widgets: [] };
let config  = {};
let presets = {};
let dragSrc = null;

// ═══════════════════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════════════════
async function init() {
  await Promise.all([loadSensors(), loadLayout(), loadConfig(), loadPresets()]);
  setInterval(loadSensors, 10000);
}

// ═══════════════════════════════════════════════════════════════════
// Modales — helpers centralisés
// ═══════════════════════════════════════════════════════════════════
function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

// Fermer en cliquant sur le fond sombre
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('open');
  }
});

// ═══════════════════════════════════════════════════════════════════
// Capteurs actifs
// ═══════════════════════════════════════════════════════════════════
async function loadSensors() {
  try {
    const r = await fetch('/sensors');
    sensors = await r.json();
    renderSensors();
    setStatus(true);
  } catch {
    setStatus(false);
  }
}

function renderSensors() {
  const el      = document.getElementById('sensorList');
  const entries = Object.entries(sensors);

  if (!entries.length) {
    el.innerHTML = '<span class="empty-state">Aucun capteur enregistré</span>';
    return;
  }

  el.innerHTML = entries.map(([id, s]) => {
    const val      = s.value != null ? String(s.value) : '—';
    const isStale  = !s.updated_at || (Date.now() - new Date(s.updated_at)) > 60000;
    const timeAgo  = s.updated_at ? timeSince(new Date(s.updated_at)) : 'jamais';
    const onScreen = layout.widgets.some(w => w.sensor_id === id);

    return `
    <div class="sensor-item">
      <div style="flex:1;min-width:0">
        <div class="sensor-name">${escHtml(s.label || id)}</div>
        <div class="sensor-meta">${escHtml(id)} · ${timeAgo}${onScreen ? ' · <em>à l\'écran</em>' : ''}</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        <div class="sensor-val">
          ${val}<span style="font-size:11px;color:var(--muted);margin-left:2px">${escHtml(s.unit || '')}</span>
        </div>
        <div class="sensor-status ${isStale ? 'stale' : 'fresh'}"></div>
        <button class="icon-btn danger" title="Supprimer ce capteur"
          data-sensor-id="${escHtml(id)}" data-action="delete-sensor">×</button>
      </div>
    </div>`;
  }).join('');
}

async function addSensor() {
  const id    = document.getElementById('newSensorId').value.trim();
  const label = document.getElementById('newSensorLabel').value.trim();
  const unit  = document.getElementById('newSensorUnit').value.trim();

  if (!id) {
    toast('L\'ID est obligatoire');
    return;
  }
  if (/\s/.test(id)) {
    toast('L\'ID ne doit pas contenir d\'espaces');
    return;
  }

  // Désactiver le bouton pour éviter double-clic
  const btn = document.getElementById('btnCreateSensor');
  btn.disabled = true;

  try {
    const r = await fetch(`/sensors/${encodeURIComponent(id)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label: label || id, unit: unit || '', value: null, updated_at: null }),
    });

    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    // Fermer la modale et réinitialiser le formulaire
    closeModal('addSensorModal');
    document.getElementById('newSensorId').value    = '';
    document.getElementById('newSensorLabel').value = '';
    document.getElementById('newSensorUnit').value  = '';

    // Recharger les capteurs depuis le serveur (source de vérité)
    await loadSensors();
    toast(`Capteur "${label || id}" créé — utiliser "+ Ajouter" dans Widgets pour l'afficher`);
  } catch (err) {
    toast('Erreur lors de la création du capteur');
    console.error(err);
  } finally {
    btn.disabled = false;
  }
}

function confirmDeleteSensor(id) {
  const label = sensors[id]?.label || id;
  document.getElementById('confirmDeleteMsg').textContent =
    `Supprimer le capteur "${label}" ?`;

  // Attacher l'action au bouton de confirmation
  const btn = document.getElementById('btnConfirmDelete');
  // Cloner pour supprimer les anciens listeners
  const newBtn = btn.cloneNode(true);
  btn.parentNode.replaceChild(newBtn, btn);
  newBtn.addEventListener('click', () => deleteSensor(id));

  openModal('confirmDeleteModal');
}

async function deleteSensor(id) {
  closeModal('confirmDeleteModal');

  try {
    const r = await fetch(`/sensors/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    // Mettre à jour le state local
    delete sensors[id];
    layout.widgets = layout.widgets.filter(w => w.sensor_id !== id);

    renderSensors();
    renderWidgets();
    toast('Capteur supprimé');
  } catch (err) {
    toast('Erreur lors de la suppression');
    console.error(err);
  }
}

// ═══════════════════════════════════════════════════════════════════
// Widgets à l'écran
// ═══════════════════════════════════════════════════════════════════
function openAddWidgetModal() {
  const entries = Object.entries(sensors);

  if (!entries.length) {
    toast('Aucun capteur disponible — créer d\'abord un capteur');
    return;
  }

  const el = document.getElementById('addWidgetList');
  el.innerHTML = entries.map(([id, s]) => {
    const onScreen = layout.widgets.some(w => w.sensor_id === id);
    return `
    <div class="widget-option ${onScreen ? 'on-screen' : ''}">
      <div style="flex:1;min-width:0">
        <div class="widget-option-label">${escHtml(s.label || id)}</div>
        <div class="widget-option-sub">${escHtml(id)}</div>
      </div>
      <button class="btn btn-primary btn-sm"
        ${onScreen ? 'disabled' : `data-sensor-id="${escHtml(id)}" data-action="add-widget"`}>
        ${onScreen ? 'Déjà affiché' : '+ Ajouter'}
      </button>
    </div>`;
  }).join('');

  openModal('addWidgetModal');
}

async function addWidgetToLayout(sensorId) {
  // Si déjà dans le layout (mais invisible), le rendre visible
  const existing = layout.widgets.find(w => w.sensor_id === sensorId);
  if (existing) {
    existing.visible = true;
  } else {
    layout.widgets.push({
      id: `sensor_${sensorId}`,
      type: 'sensor',
      sensor_id: sensorId,
      visible: true,
      order: layout.widgets.length,
      span_col: 1,
      span_row: 1,
    });
    layout.widgets.forEach((w, i) => w.order = i);
  }

  try {
    const r = await fetch('/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layout),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    closeModal('addWidgetModal');
    renderWidgets();
    renderSensors();
    toast('Widget ajouté à l\'écran');
  } catch (err) {
    toast('Erreur lors de l\'ajout du widget');
    console.error(err);
  }
}

async function removeWidget(idx) {
  layout.widgets.splice(idx, 1);
  layout.widgets.forEach((w, i) => w.order = i);

  try {
    await fetch('/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layout),
    });
    renderWidgets();
    renderSensors();
    toast('Widget retiré de l\'écran');
  } catch (err) {
    toast('Erreur lors de la suppression du widget');
  }
}

function renderWidgets() {
  const el = document.getElementById('widgetList');

  if (!layout.widgets.length) {
    el.innerHTML = '<span class="empty-state">Aucun widget — cliquer sur "+ Ajouter"</span>';
    return;
  }

  el.innerHTML = layout.widgets.map((w, i) => {
    const sc        = w.span_col || 1;
    const sr        = w.span_row || 1;
    // Calendrier et horloge : pas de bouton supprimer
    const canRemove = w.type === 'sensor';

    return `
    <div class="widget-row" draggable="true"
      ondragstart="dragStart(event,${i})"
      ondragover="dragOver(event,${i})"
      ondrop="drop(event,${i})">
      <span class="drag-handle">⠿</span>
      <div style="flex:1;min-width:0">
        <div class="widget-label">${escHtml(widgetName(w))}</div>
        <div class="widget-type">${w.type}${w.sensor_id ? ' · ' + escHtml(w.sensor_id) : ''}</div>
      </div>
      <div class="span-controls" title="Colonnes occupées">
        <button class="span-btn" onclick="changeSpan(${i},'col',-1)">−</button>
        <span class="span-val">${sc}c</span>
        <button class="span-btn" onclick="changeSpan(${i},'col',+1)">+</button>
      </div>
      <div class="span-controls" title="Lignes occupées">
        <button class="span-btn" onclick="changeSpan(${i},'row',-1)">−</button>
        <span class="span-val">${sr}r</span>
        <button class="span-btn" onclick="changeSpan(${i},'row',+1)">+</button>
      </div>
      <label class="toggle" title="Visible">
        <input type="checkbox" ${w.visible ? 'checked' : ''} onchange="toggleWidget(${i}, this.checked)">
        <span class="slider"></span>
      </label>
      ${canRemove
        ? `<button class="icon-btn danger" title="Retirer de l'écran" onclick="removeWidget(${i})">×</button>`
        : `<span style="width:22px"></span>`}
    </div>`;
  }).join('');
}

function widgetName(w) {
  if (w.type === 'calendar') return 'Calendrier';
  if (w.type === 'clock')    return 'Horloge';
  if (w.type === 'sensor')   return sensors[w.sensor_id]?.label || w.sensor_id;
  return w.id;
}

function toggleWidget(idx, val) {
  layout.widgets[idx].visible = val;
}

function changeSpan(idx, axis, delta) {
  const w = layout.widgets[idx];
  if (axis === 'col') w.span_col = Math.max(1, (w.span_col || 1) + delta);
  else                w.span_row = Math.max(1, (w.span_row || 1) + delta);
  renderWidgets();
}

function dragStart(e, i) { dragSrc = i; e.dataTransfer.effectAllowed = 'move'; }
function dragOver(e, i)  { e.preventDefault(); }
function drop(e, i) {
  e.preventDefault();
  if (dragSrc === i) return;
  const moved = layout.widgets.splice(dragSrc, 1)[0];
  layout.widgets.splice(i, 0, moved);
  layout.widgets.forEach((w, idx) => w.order = idx);
  dragSrc = null;
  renderWidgets();
}

async function saveLayout(silent = false) {
  try {
    const r = await fetch('/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layout),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    if (!silent) toast('Disposition sauvegardée');
  } catch (err) {
    toast('Erreur lors de la sauvegarde');
    console.error(err);
  }
}

async function loadLayout() {
  const r = await fetch('/layout');
  layout  = await r.json();
  if (!layout.preset) layout.preset = '1col';
  renderWidgets();
}

// ═══════════════════════════════════════════════════════════════════
// Presets de grille
// ═══════════════════════════════════════════════════════════════════
async function loadPresets() {
  const r = await fetch('/layout/presets');
  presets = await r.json();
  renderPresets();
}

function renderPresets() {
  const el = document.getElementById('presetGrid');
  el.innerHTML = Object.entries(presets).map(([id, p]) => `
    <div class="preset-card ${layout.preset === id ? 'active' : ''}" onclick="selectPreset('${id}')">
      <div class="preset-visual">${buildPresetSvg(id)}</div>
      <span class="preset-name">${escHtml(p.label)}</span>
    </div>`).join('');
}

function selectPreset(id) {
  layout.preset = id;
  renderPresets();
  toast(`"${presets[id]?.label}" — cliquer sur Appliquer pour sauvegarder`);
}

function buildPresetSvg(id) {
  const W = 100, H = 60, gap = 2, pad = 2;
  const configs = {
    '1col':         { cols: 1, rows: 3 },
    '2col':         { cols: 2, rows: 2 },
    '2col-sidebar': { cols: [2,1], rows: 2 },
    '3col':         { cols: 3, rows: 2 },
    '2x2':          { cols: 2, rows: 2 },
    '3x2':          { cols: 3, rows: 2 },
    '3x3':          { cols: 3, rows: 3 },
    'hero-bottom':  { special: 'hero-bottom' },
    'sidebar-grid': { special: 'sidebar-grid' },
  };
  const cfg = configs[id] || { cols: 2, rows: 2 };
  let rects = '';

  if (cfg.special === 'hero-bottom') {
    const heroH = (H - pad*2) * 0.6;
    const cellH = (H - pad*2) - heroH - gap;
    const cellW = (W - pad*2 - gap*2) / 3;
    rects += svgRect(pad, pad, W - pad*2, heroH);
    for (let c = 0; c < 3; c++)
      rects += svgRect(pad + c*(cellW+gap), pad + heroH + gap, cellW, cellH);
  } else if (cfg.special === 'sidebar-grid') {
    const sideW = (W - pad*2) * 0.35;
    const mainW = (W - pad*2) - sideW - gap;
    const cellH = (H - pad*2 - gap) / 2;
    const cellW = (mainW - gap) / 2;
    rects += svgRect(pad, pad, sideW, H - pad*2);
    for (let r = 0; r < 2; r++)
      for (let c = 0; c < 2; c++)
        rects += svgRect(pad + sideW + gap + c*(cellW+gap), pad + r*(cellH+gap), cellW, cellH);
  } else {
    const rows  = cfg.rows;
    const cols  = cfg.cols;
    const cellH = (H - pad*2 - gap*(rows-1)) / rows;
    if (Array.isArray(cols)) {
      const total = cols.reduce((a,b) => a+b, 0);
      for (let r = 0; r < rows; r++) {
        let x = pad;
        cols.forEach(span => {
          const cw = (W - pad*2 - gap*(cols.length-1)) * span / total;
          rects += svgRect(x, pad + r*(cellH+gap), cw, cellH);
          x += cw + gap;
        });
      }
    } else {
      const cellW = (W - pad*2 - gap*(cols-1)) / cols;
      for (let r = 0; r < rows; r++)
        for (let c = 0; c < cols; c++)
          rects += svgRect(pad + c*(cellW+gap), pad + r*(cellH+gap), cellW, cellH);
    }
  }
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"
    style="width:100%;height:100%;display:block">${rects}</svg>`;
}

function svgRect(x, y, w, h) {
  return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}"
    width="${Math.max(0,w).toFixed(1)}" height="${Math.max(0,h).toFixed(1)}"
    rx="1" fill="#b8a990"/>`;
}

// ═══════════════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════════════
async function loadConfig() {
  const r = await fetch('/config');
  config  = await r.json();
  renderConfig();
}

function renderConfig() {
  document.getElementById('configPanel').innerHTML = `
    <div class="config-row">
      <label>Rafraîchissement écran (s)</label>
      <input class="config-input" id="cfg_refresh" type="number"
        value="${config.refresh_seconds}" min="60">
    </div>
    <div class="config-row">
      <label>Événements futurs (jours)</label>
      <input class="config-input" id="cfg_days_ahead" type="number"
        value="${config.calendar_days_ahead}" min="1" max="60">
    </div>
    <div class="config-row">
      <label>Événements passés (jours)</label>
      <input class="config-input" id="cfg_days_behind" type="number"
        value="${config.calendar_days_behind ?? 0}" min="0" max="30">
    </div>
    <div class="config-row">
      <label>Fuseau horaire</label>
      <input class="config-input" id="cfg_tz" type="text"
        value="${config.timezone}" style="width:150px;text-align:left">
    </div>`;
}

async function saveConfig() {
  config.refresh_seconds      = parseInt(document.getElementById('cfg_refresh').value);
  config.calendar_days_ahead  = parseInt(document.getElementById('cfg_days_ahead').value);
  config.calendar_days_behind = parseInt(document.getElementById('cfg_days_behind').value);
  config.timezone             = document.getElementById('cfg_tz').value;
  await fetch('/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  toast('Configuration sauvegardée');
}

// ═══════════════════════════════════════════════════════════════════
// Upload ICS
// ═══════════════════════════════════════════════════════════════════
const dropZone = document.getElementById('dropZone');
dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  uploadIcs(e.dataTransfer.files[0]);
});

async function uploadIcs(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  const r    = await fetch('/calendar/upload', { method: 'POST', body: fd });
  const data = await r.json();
  document.getElementById('calendarStatus').textContent =
    `✓ ${data.events_count} événements chargés`;
  toast(`${data.events_count} événements importés`);
}

// ═══════════════════════════════════════════════════════════════════
// Preview
// ═══════════════════════════════════════════════════════════════════
async function refreshPreview() {
  const img         = document.getElementById('previewImg');
  const placeholder = document.getElementById('previewPlaceholder');
  placeholder.textContent   = 'Génération en cours…';
  placeholder.style.display = 'block';
  img.style.display         = 'none';
  img.src = `/display/preview-png?t=${Date.now()}`;
  img.onload  = () => { img.style.display = 'block'; placeholder.style.display = 'none'; };
  img.onerror = () => { placeholder.textContent = '⚠ Erreur de génération'; };
}

// ═══════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════
function setStatus(online) {
  document.getElementById('statusDot').className    = `status-dot ${online ? 'online' : ''}`;
  document.getElementById('statusText').textContent = online ? 'connecté' : 'hors ligne';
}

function timeSince(date) {
  const s = Math.floor((Date.now() - date) / 1000);
  if (s < 60)   return `il y a ${s}s`;
  if (s < 3600) return `il y a ${Math.floor(s/60)}min`;
  return `il y a ${Math.floor(s/3600)}h`;
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Délégation d'événements pour les boutons avec data-action
// Évite les problèmes de guillemets dans les onclick inline générés dynamiquement
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;

  const action   = btn.dataset.action;
  const sensorId = btn.dataset.sensorId;

  if (action === 'delete-sensor' && sensorId) {
    confirmDeleteSensor(sensorId);
  } else if (action === 'add-widget' && sensorId) {
    addWidgetToLayout(sensorId);
  }
});

// ═══════════════════════════════════════════════════════════════════
// Go
// ═══════════════════════════════════════════════════════════════════
init();