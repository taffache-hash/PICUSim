const $ = (id) => document.getElementById(id);
let sessionId = null;
let currentScenario = null;
let scenarioCatalogMap = new Map();
let bedsideWS = null;
let waveformWS = null;
let lastWaveform = {};
let lastBedsideState = {};
let lastExtendedMonitorState = {};
let extendedMonitorSnapshotTimer = null;
let fullProfileFetchInFlight = false;
let lastFullProfileFetchMs = 0;
let labsStripRotationIndex = 0;
let labsStripLastRotateMs = 0;
let labsStripLastFullRequestMs = 0;
const extendedSnapshotBuffer = [];
const waveformTrendBuffer = [];
let waveformLoopVolumeMl = 0;
let renderers = [];
let lastFrame = performance.now();
let emergencyScenarioMap = new Map();
let instructorPresets = [];
let diagnosisHidden = false;
let authoringTemplates = [];
let authoringLastSavedScenario = null;
const SESSION_UI_STATE = { loaded: false, running: false, lastAction: null, simTimeS: 0, wallStartMs: 0, wallAccumMs: 0, speed: 1 };

function readSessionSpeed() {
  const raw = Number($('speedInput')?.value);
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

function syncSessionTiming(st={}, envelope={}) {
  const t = Number(envelope.time_s ?? st.time_s ?? st.t);
  if (Number.isFinite(t)) SESSION_UI_STATE.simTimeS = t;
  const speed = Number(envelope.speed);
  if (Number.isFinite(speed) && speed > 0) SESSION_UI_STATE.speed = speed;
  const status = String(envelope.status || '').toLowerCase();
  if (status === 'running') SESSION_UI_STATE.running = true;
  if (status === 'paused' || status === 'stopped') SESSION_UI_STATE.running = false;
}

function setStatus(text, online=false) {
  const el = $('connectionStatus');
  el.textContent = text;
  el.classList.toggle('online', online);
}

function clampNumber(x, lo, hi, fallback) {
  const n = Number(x);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(lo, Math.min(hi, n));
}

function saturationToneHz(spo2Fraction) {
  const spo2 = clampNumber(spo2Fraction, 0.55, 1.0, 0.98);
  const pct = spo2 * 100;
  return Math.round(420 + ((pct - 55) / 45) * 620);
}

function setAudioMonitorButton() {
  const btn = $('audioMonitorBtn');
  if (!btn) return;
  btn.classList.toggle('audio-monitor-on', AUDIO_MONITOR.enabled);
  btn.classList.toggle('audio-monitor-off', !AUDIO_MONITOR.enabled);
  btn.setAttribute('aria-pressed', AUDIO_MONITOR.enabled ? 'true' : 'false');
  btn.textContent = AUDIO_MONITOR.enabled ? 'Audio ON' : 'Audio OFF';
  btn.title = 'Monitor audio: pulsossimetro pitch-variabile, click ECG e cue UI. Disattivato di default.';
}

async function ensureAudioContext() {
  const AudioCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtor) throw new Error('Web Audio non supportato da questo browser.');
  if (!AUDIO_MONITOR.ctx) AUDIO_MONITOR.ctx = new AudioCtor();
  if (AUDIO_MONITOR.ctx.state === 'suspended') await AUDIO_MONITOR.ctx.resume();
  return AUDIO_MONITOR.ctx;
}

function playMonitorTone(freqHz, durationSec, gainValue, type='sine') {
  const ctx = AUDIO_MONITOR.ctx;
  if (!ctx || ctx.state !== 'running') return;
  const t0 = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freqHz, t0);
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, gainValue), t0 + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + durationSec);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + durationSec + 0.015);
}

async function toggleAudioMonitor() {
  if (!AUDIO_MONITOR.enabled) {
    await ensureAudioContext();
    AUDIO_MONITOR.enabled = true;
    const now = performance.now();
    AUDIO_MONITOR.nextPulseAt = now;
    AUDIO_MONITOR.nextEcgAt = now + 25;
  } else {
    AUDIO_MONITOR.enabled = false;
  }
  setAudioMonitorButton();
  if (AUDIO_MONITOR.enabled) playUiCue('confirm');
}

function driveMonitorAudio(nowMs) {
  if (!AUDIO_MONITOR.enabled || !AUDIO_MONITOR.ctx || !lastBedsideState) return;
  const hr = clampNumber(lastBedsideState.HR, 25, 260, 120);
  const intervalMs = 60000 / hr;
  if (!Number.isFinite(AUDIO_MONITOR.nextPulseAt) || AUDIO_MONITOR.nextPulseAt <= 0 || nowMs - AUDIO_MONITOR.nextPulseAt > intervalMs * 3) {
    AUDIO_MONITOR.nextPulseAt = nowMs;
  }
  if (!Number.isFinite(AUDIO_MONITOR.nextEcgAt) || AUDIO_MONITOR.nextEcgAt <= 0 || nowMs - AUDIO_MONITOR.nextEcgAt > intervalMs * 3) {
    AUDIO_MONITOR.nextEcgAt = nowMs + 25;
  }
  const spo2 = clampNumber(lastBedsideState.SaO2 ?? (Number(lastBedsideState.SpO2_percent) / 100), 0.55, 1.0, 0.98);
  if (AUDIO_MONITOR.pulseOx && nowMs >= AUDIO_MONITOR.nextPulseAt) {
    const freq = saturationToneHz(spo2);
    const gain = spo2 < 0.90 ? 0.075 : 0.055;
    playMonitorTone(freq, 0.075, gain, 'sine');
    AUDIO_MONITOR.nextPulseAt += intervalMs;
  }
  if (AUDIO_MONITOR.ecg && nowMs >= AUDIO_MONITOR.nextEcgAt) {
    playMonitorTone(1150, 0.026, 0.030, 'square');
    AUDIO_MONITOR.nextEcgAt += intervalMs;
  }
}


function playUiCue(kind='confirm') {
  if (!AUDIO_MONITOR.enabled || !AUDIO_MONITOR.uiCues || !AUDIO_MONITOR.ctx || AUDIO_MONITOR.ctx.state !== 'running') return;
  if (kind === 'error') {
    playMonitorTone(260, 0.12, 0.045, 'sawtooth');
    return;
  }
  if (kind === 'pending') {
    playMonitorTone(720, 0.035, 0.020, 'triangle');
    return;
  }
  playMonitorTone(940, 0.045, 0.026, 'triangle');
}

function setButtonVisualState(btn, state='idle', label='') {
  if (!btn) return;
  btn.classList.remove('button-active', 'button-pending', 'button-confirmed', 'button-error');
  btn.dataset.stateLabel = label || '';
  if (state && state !== 'idle') btn.classList.add(`button-${state}`);
  btn.setAttribute('aria-pressed', state === 'active' ? 'true' : 'false');
}

function markButtonMomentary(id, state='confirmed', label='done', timeoutMs=900) {
  const btn = $(id);
  if (!btn) return;
  setButtonVisualState(btn, state, label);
  window.setTimeout(() => updateSessionButtonStates(), timeoutMs);
}

function showActionFeedback(label, detail='', state='confirmed') {
  const el = $('actionFeedbackBar');
  if (!el) return;
  el.classList.remove('idle', 'pending', 'confirmed', 'error');
  el.classList.add(state || 'confirmed');
  const t = Number(SESSION_UI_STATE.simTimeS || 0);
  const detailText = detail ? ` - ${detail}` : '';
  el.textContent = `t ${formatDuration(t)} · ${label}${detailText}`;
}



function formatDuration(seconds) {
  const n = Math.max(0, Number(seconds) || 0);
  const h = Math.floor(n / 3600);
  const m = Math.floor((n % 3600) / 60);
  const s = Math.floor(n % 60);
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`;
}

function currentWallElapsedMs(nowMs=performance.now()) {
  return SESSION_UI_STATE.wallAccumMs + (SESSION_UI_STATE.running && SESSION_UI_STATE.wallStartMs ? nowMs - SESSION_UI_STATE.wallStartMs : 0);
}

function updateTimeTelemetry(nowMs=performance.now()) {
  const el = $('timeTelemetry');
  if (!el) return;
  if (!SESSION_UI_STATE.loaded) {
    el.textContent = 'sim -- · wall -- · speed ×--';
    el.classList.remove('running');
    return;
  }
  const sim = SESSION_UI_STATE.simTimeS;
  const wallS = currentWallElapsedMs(nowMs) / 1000;
  const speed = SESSION_UI_STATE.running ? Number(SESSION_UI_STATE.speed || readSessionSpeed()) : 0;
  el.textContent = `sim ${formatDuration(sim)} · wall ${formatDuration(wallS)} · speed ×${fmt(speed, 1)}`;
  el.classList.toggle('running', SESSION_UI_STATE.running);
}

function startWallClock() {
  SESSION_UI_STATE.wallStartMs = performance.now();
}

function pauseWallClock() {
  if (SESSION_UI_STATE.wallStartMs) SESSION_UI_STATE.wallAccumMs = currentWallElapsedMs();
  SESSION_UI_STATE.wallStartMs = 0;
}

function resetWallClock() {
  SESSION_UI_STATE.wallStartMs = 0;
  SESSION_UI_STATE.wallAccumMs = 0;
}
function setSessionRunState(state='idle') {
  const el = $('sessionRunState');
  if (!el) return;
  el.classList.remove('idle', 'paused', 'running', 'pending', 'error');
  el.classList.add(state);
  const labels = {
    idle: 'not loaded',
    paused: 'paused',
    running: 'running',
    pending: 'working',
    error: 'error',
  };
  el.textContent = labels[state] || state;
}
function updateSessionButtonStates() {
  setButtonVisualState($('loadBtn'), SESSION_UI_STATE.loaded ? 'confirmed' : 'idle', SESSION_UI_STATE.loaded ? 'loaded' : '');
  setButtonVisualState($('startBtn'), SESSION_UI_STATE.running ? 'active' : 'idle', SESSION_UI_STATE.running ? 'running' : '');
  setButtonVisualState($('pauseBtn'), SESSION_UI_STATE.loaded && !SESSION_UI_STATE.running ? 'active' : 'idle', SESSION_UI_STATE.loaded && !SESSION_UI_STATE.running ? 'paused' : '');
  setSessionRunState(!SESSION_UI_STATE.loaded ? 'idle' : (SESSION_UI_STATE.running ? 'running' : 'paused'));
  if (!$('stepBtn')?.classList.contains('button-pending') && !$('stepBtn')?.classList.contains('button-confirmed')) setButtonVisualState($('stepBtn'), 'idle');
  if (!$('resetBtn')?.classList.contains('button-pending') && !$('resetBtn')?.classList.contains('button-confirmed')) setButtonVisualState($('resetBtn'), 'idle');
}

async function runSessionButtonAction(buttonId, action) {
  const btn = $(buttonId);
  setButtonVisualState(btn, 'pending', 'pending');
  setSessionRunState('pending');
  showActionFeedback(btn?.textContent?.trim() || 'Session action', 'in corso', 'pending');
  playUiCue('pending');
  try {
    const result = await action();
    playUiCue('confirm');
    updateSessionButtonStates();
    return result;
  } catch (e) {
    if (handleUnknownSession(e)) throw e;
    setButtonVisualState(btn, 'error', 'error');
    setSessionRunState('error');
    showActionFeedback(btn?.textContent?.trim() || 'Session action', e.message, 'error');
    playUiCue('error');
    window.setTimeout(() => updateSessionButtonStates(), 1200);
    throw e;
  }
}
function fmt(x, digits=0) {
  const n = Number(x);
  return Number.isFinite(n) ? n.toFixed(digits) : '--';
}
async function api(path, options={}) {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const parsed = JSON.parse(detail);
      detail = parsed.detail || parsed.message || detail;
    } catch (_) {}
    const err = new Error(String(detail || `HTTP ${res.status}`));
    err.status = res.status;
    err.path = path;
    throw err;
  }
  return await res.json();
}

function isUnknownSessionError(err) {
  return err?.status === 404 && String(err.message || '').includes('Unknown session');
}

function handleUnknownSession(err) {
  if (!isUnknownSessionError(err)) return false;
  err.handled = true;
  const stale = sessionId;
  sessionId = null;
  SESSION_UI_STATE.loaded = false;
  SESSION_UI_STATE.running = false;
  pauseWallClock();
  disconnectStreams();
  updateSessionButtonStates();
  updateAirwayActionButtons({});
  if ($('sessionMeta')) $('sessionMeta').textContent = 'Sessione non più attiva: ricarica lo scenario.';
  showActionFeedback('Sessione scaduta', stale ? `ID ${stale.slice(0, 8)} non presente sul server; premi Load` : 'premi Load', 'error');
  playUiCue('error');
  return true;
}

function reportUiError(err) {
  if (handleUnknownSession(err) || err?.handled) return;
  alert(err?.message || String(err));
}

const LIVE_CONTROL_DEBOUNCE_MS = 120;
const liveControlTimers = new Map();
const liveControlLastTouched = new Map();
const controlPendingValues = new Map();
const controlStatusTimers = new Map();

const RANGE_CONTROL_BINDINGS = {
  fio2Range: { key: 'FiO2', outputId: 'fio2Out', formatter: (v) => Number(v).toFixed(2) },
  peepRange: { key: 'PEEP', outputId: 'peepOut', formatter: (v) => String(Number(v)) },
  rrRange: { key: 'RR', outputId: 'rrOut', formatter: (v) => String(Number(v)) },
};
const DRUG_CONTROL_BINDINGS = {
  set_adrenaline: 'adrenaline_mcg_kg_min',
  set_norad: 'norad_mcg_kg_min',
  set_dopamine: 'dopamine_mcg_kg_min',
  set_vasopressin: 'vasopressin_mU_kg_min',
  set_milrinone: 'milrinone_mcg_kg_min',
  set_ketamine: 'ketamine_mg_kg_h',
  set_fentanyl: 'fentanyl_mcg_kg_h',
  set_remifentanil: 'remifentanil_mcg_kg_min',
  set_morphine: 'morphine_mcg_kg_h',
  set_midazolam: 'midazolam_mcg_kg_h',
  set_propofol: 'propofol_mg_kg_h',
  set_dexmedetomidine: 'dexmedetomidine_mcg_kg_h',
  set_clonidine: 'clonidine_mcg_kg_h',
  set_rocuronium: 'rocuronium_mg_kg_h',
  set_salbutamol: 'salbutamol_mcg_kg_min',
  set_ipratropium: 'ipratropium_mcg_kg_h',
  set_magnesium: 'magnesium_mg_kg_h',
  set_nebulized_epinephrine: 'nebulized_epinephrine_mcg_kg_min',
  set_ino_ppm: 'ino_ppm',
  set_hydrocortisone: 'hydrocortisone_mg_kg_h',
  set_dexamethasone: 'dexamethasone_mcg_kg_h',
  set_insulin: 'insulin_UI_h',
  set_furosemide: 'furosemide_mg_kg',
  set_furosemide_infusion: 'furosemide_mg_kg_h',
  set_vancomycin: 'vancomycin_mg_kg_h',
  set_piperacillin: 'piperacillin_mg_kg_h',
  set_crystalloid_rate: 'crystalloid_rate_mL_h',
};
const CONTROL_SYNC_GRACE_MS = 350;

const AIRWAY_EVENT_DEFAULT_SEVERITIES = {
  failed_intubation_attempt: 'moderate',
  start_bag_mask_ventilation: 'adequate',
  perform_intubation: 'emergency',
  accidental_extubation: 'moderate',
  planned_extubation: 'to_hfnc',
  laryngospasm: 'severe',
  aspiration_event: 'moderate',
  airway_obstruction_event: 'moderate',
};

const AUDIO_MONITOR = {
  enabled: false,
  pulseOx: true,
  ecg: true,
  uiCues: true,
  ctx: null,
  nextPulseAt: 0,
  nextEcgAt: 0,
};


const LABS_STRIP_ITEMS = [
  { label: 'Lactate', keys: ['lactate'], unit: 'mmol/L', digits: 1 },
  { label: 'Glucose', keys: ['glucose_mmol_L', 'glucose'], unit: 'mmol/L', digits: 1 },
  { label: 'K+', keys: ['K_mmol_L', 'K'], unit: 'mmol/L', digits: 1 },
  { label: 'Na+', keys: ['Na_mmol_L', 'Na'], unit: 'mmol/L', digits: 0 },
  { label: 'Hb', keys: ['Hb'], unit: 'g/dL', digits: 1 },
  { label: 'Creatinine', keys: ['creatinine_mg_dL'], unit: 'mg/dL', digits: 2 },
  { label: 'Bilirubin', keys: ['bilirubin_total_mg_dL', 'bilirubin_mg_dL', 'total_bilirubin'], unit: 'mg/dL', digits: 1 },
  { label: 'GCS', keys: ['GCS_proxy', 'GCS'], unit: '', digits: 0 },
  { label: 'RASS', keys: ['RASS_proxy', 'RASS'], unit: '', digits: 0 },
  { label: 'ICP', keys: ['ICP_mmHg', 'ICP'], unit: 'mmHg', digits: 1 },
  { label: 'CVP', keys: ['CVP'], unit: 'mmHg', digits: 1 },
  { label: 'DO2', keys: ['DO2'], unit: 'mL/min', digits: 0 },
  { label: 'Urine', keys: ['urine_rate_mL_h'], unit: 'mL/h', digits: 0 },
];
const BOLUS_DRUG_DEFS = [
  { id: 'bolus_adrenaline', label: 'Adrenaline push', unit: 'mcg/kg', defaultValue: 1, step: 0.1, durationSec: 60, action: 'set_adrenaline', rateUnit: 'mcg/kg/min', rateFactor: dose => dose / 1.0 },
  { id: 'bolus_ketamine', label: 'Ketamine', unit: 'mg/kg', defaultValue: 1, step: 0.1, durationSec: 60, action: 'set_ketamine', rateUnit: 'mg/kg/h', rateFactor: dose => dose * 60.0 },
  { id: 'bolus_fentanyl', label: 'Fentanyl', unit: 'mcg/kg', defaultValue: 1, step: 0.5, durationSec: 60, action: 'set_fentanyl', rateUnit: 'mcg/kg/h', rateFactor: dose => dose * 60.0 },
  { id: 'bolus_morphine', label: 'Morphine', unit: 'mcg/kg', defaultValue: 50, step: 5, durationSec: 300, action: 'set_morphine', rateUnit: 'mcg/kg/h', rateFactor: dose => dose * 12.0 },
  { id: 'bolus_midazolam', label: 'Midazolam', unit: 'mcg/kg', defaultValue: 100, step: 10, durationSec: 60, action: 'set_midazolam', rateUnit: 'mcg/kg/h', rateFactor: dose => dose * 60.0 },
  { id: 'bolus_propofol', label: 'Propofol', unit: 'mg/kg', defaultValue: 1, step: 0.1, durationSec: 60, action: 'set_propofol', rateUnit: 'mg/kg/h', rateFactor: dose => dose * 60.0 },
  { id: 'bolus_rocuronium', label: 'Rocuronium', unit: 'mg/kg', defaultValue: 1, step: 0.1, durationSec: 60, action: 'set_rocuronium', rateUnit: 'mg/kg/h', rateFactor: dose => dose * 60.0 },
  { id: 'bolus_furosemide', label: 'Furosemide', unit: 'mg/kg', defaultValue: 1, step: 0.1, durationSec: 0, action: 'set_furosemide', rateUnit: 'native bolus', nativeBolus: true },
  { id: 'bolus_hydrocortisone', label: 'Hydrocortisone', unit: 'mg/kg', defaultValue: 2, step: 0.5, durationSec: 300, action: 'set_hydrocortisone', rateUnit: 'mg/kg/h', rateFactor: dose => dose * 12.0 },
];
const activeBolusTimers = new Map();
const activeBolusRecords = new Map();

const DRUG_AUDIT_GROUPS = [
  { name: 'Adrenaline', dose: 'adrenaline_mcg_kg_min', unit: 'mcg/kg/min', concentration: ['C_adrenaline_ng_mL'], effects: ['drug_HR_mod', 'vasoactive_SVR_mod', 'vasoactive_CO_mod'] },
  { name: 'Noradrenaline', dose: 'norad_mcg_kg_min', unit: 'mcg/kg/min', concentration: ['C_norad_ng_mL', 'C_noradrenaline_ng_mL'], effects: ['vasoactive_SVR_mod', 'drug_HR_mod'] },
  { name: 'Dopamine', dose: 'dopamine_mcg_kg_min', unit: 'mcg/kg/min', concentration: ['C_dopamine_ng_mL'], effects: ['drug_HR_mod', 'vasoactive_CO_mod'] },
  { name: 'Vasopressin', dose: 'vasopressin_mU_kg_min', unit: 'mU/kg/min', effects: ['vasoactive_SVR_mod'] },
  { name: 'Milrinone', dose: 'milrinone_mcg_kg_min', unit: 'mcg/kg/min', effects: ['vasoactive_CO_mod'] },
  { name: 'Ketamine', dose: 'ketamine_mg_kg_h', unit: 'mg/kg/h', concentration: ['C_ketamine_mg_L'], effects: ['ketamine_analgesia_signal', 'ketamine_dissociation_signal', 'ketamine_hemodynamic_support_signal'] },
  { name: 'Fentanyl', dose: 'fentanyl_mcg_kg_h', unit: 'mcg/kg/h', concentration: ['C_fentanyl_ng_mL'], effects: ['fentanyl_analgesia_signal', 'fentanyl_resp_depression_signal'] },
  { name: 'Remifentanil', dose: 'remifentanil_mcg_kg_min', unit: 'mcg/kg/min', concentration: ['C_remifentanil_ng_mL'], effects: ['remifentanil_analgesia_signal', 'remifentanil_resp_depression_signal'] },
  { name: 'Morphine', dose: 'morphine_mcg_kg_h', unit: 'mcg/kg/h', concentration: ['C_morphine_ng_mL'], effects: ['morphine_analgesia_signal', 'morphine_resp_depression_signal'], risks: ['morphine_renal_accumulation_risk', 'M6G_accumulation_proxy'] },
  { name: 'Midazolam', dose: 'midazolam_mcg_kg_h', unit: 'mcg/kg/h', concentration: ['C_midazolam_ng_mL'], effects: ['midazolam_sedation_signal', 'midazolam_vasodilation_signal', 'gaba_sedation_signal'] },
  { name: 'Propofol', dose: 'propofol_mg_kg_h', unit: 'mg/kg/h', concentration: ['C_propofol_mg_L', 'C_propofol_mcg_mL'], effects: ['propofol_sedation_signal', 'propofol_vasodilation_signal', 'gaba_sedation_signal'] },
  { name: 'Dexmedetomidine', dose: 'dexmedetomidine_mcg_kg_h', unit: 'mcg/kg/h', concentration: ['C_dexmedetomidine_ng_mL'], effects: ['dexmedetomidine_sedation_signal', 'dexmedetomidine_sympatholysis_signal'] },
  { name: 'Clonidine', dose: 'clonidine_mcg_kg_h', unit: 'mcg/kg/h', concentration: ['C_clonidine_ng_mL'], effects: ['clonidine_sedation_signal', 'clonidine_sympatholysis_signal'], risks: ['clonidine_bradycardia_risk', 'clonidine_hypotension_risk'] },
  { name: 'Rocuronium', dose: 'rocuronium_mg_kg_h', unit: 'mg/kg/h', concentration: ['C_rocuronium_ng_mL'], effects: ['drug_NMB_frac', 'spontaneous_effort_available'], risks: ['nmb_trigger_block_active'] },
  { name: 'Salbutamol', dose: 'salbutamol_mcg_kg_min', unit: 'mcg/kg/min', effects: ['salbutamol_bronchodilation_signal', 'salbutamol_tachycardia_signal'] },
  { name: 'Ipratropium', dose: 'ipratropium_mcg_kg_h', unit: 'mcg/kg/h', effects: ['ipratropium_bronchodilation_signal'] },
  { name: 'Magnesium', dose: 'magnesium_mg_kg_h', unit: 'mg/kg/h', effects: ['magnesium_bronchodilation_signal'] },
  { name: 'Nebulized epinephrine', dose: 'nebulized_epinephrine_mcg_kg_min', unit: 'mcg/kg/min', effects: ['nebulized_epinephrine_bronchodilation_signal', 'nebulized_epinephrine_upper_airway_relief_signal'] },
  { name: 'iNO', dose: 'ino_ppm', unit: 'ppm', effects: ['ino_pulmonary_vasodilation_signal', 'ino_oxygenation_signal'], risks: ['ino_rebound_risk_signal'] },
  { name: 'Hydrocortisone', dose: 'hydrocortisone_mg_kg_h', unit: 'mg/kg/h', effects: ['hydrocortisone_adrenal_support_signal', 'hydrocortisone_vasopressor_sensitization_signal', 'hydrocortisone_antiinflammatory_signal'] },
  { name: 'Dexamethasone', dose: 'dexamethasone_mcg_kg_h', unit: 'mcg/kg/h', effects: ['dexamethasone_antiinflammatory_signal', 'dexamethasone_ICP_edema_signal'] },
  { name: 'Insulin', dose: 'insulin_UI_h', unit: 'UI/h', concentration: ['C_insulin_mU_L'], effects: ['insulin_action_signal', 'insulin_effective_clearance_mmol_L_h', 'insulin_effective_potassium_shift_mmol_L_h'], risks: ['insulin_hypoglycemia_risk'] },
  { name: 'Furosemide', dose: 'furosemide_mg_kg_h', alternateDose: 'furosemide_mg_kg', unit: 'mg/kg/h', concentration: ['C_furosemide_mg_L'], effects: ['furosemide_diuresis_signal', 'furosemide_effective_diuretic_signal', 'furosemide_additional_urine_mL_h'], risks: ['diuretic_hypovolemia_risk'] },
  { name: 'Vancomycin', dose: 'vancomycin_mg_kg_h', unit: 'mg/kg/h', concentration: ['C_vancomycin_mg_L'], effects: ['vancomycin_target_attainment', 'vancomycin_coverage_mod'], risks: ['vancomycin_renal_clearance_factor'] },
  { name: 'Piperacillin-tazobactam', dose: 'piperacillin_mg_kg_h', unit: 'mg/kg/h', concentration: ['C_piperacillin_mg_L'], effects: ['piperacillin_target_attainment', 'piperacillin_kill_signal', 'piperacillin_ft_above_MIC'], risks: ['piperacillin_renal_clearance_factor'] },
];

const EXTENDED_MONITOR_REFRESH_MODE = 'snapshot-only';

// v3.1 step4.2/4.13-clean: bedside numeric trend buffers for miniature sparklines.
// UI-only feature: the physiological model and backend profiles are unchanged.
// The clean package keeps 10 minutes of simulated bedside trend history.
const TREND_WINDOW_S = 600;
const TREND_MAX_SAMPLES = 2400;
const bedsideTrendBuffer = [];
const SPARKLINE_DEFS = [
  { canvasId: 'trendHR', primary: 'HR' },
  { canvasId: 'trendSpO2', primary: 'SpO2_percent' },
  { canvasId: 'trendMAP', primary: 'MAP' },
  { canvasId: 'trendCO2', primary: 'PaCO2', secondary: 'EtCO2' },
  { canvasId: 'trendPaw', primary: 'Paw' },
  { canvasId: 'trendFiO2', primary: 'FiO2' },
];


// v3.1 step4.4: visual-only threshold alarms for bedside vitals.
// No audio and no backend changes: this only annotates the existing vital cards.
const VITAL_ALARM_RULES = {
  HR: [
    { level: 'critical', test: v => v < 60 || v > 220, label: 'HR critical' },
    { level: 'warning', test: v => v < 80 || v > 180, label: 'HR warning' },
  ],
  SpO2: [
    { level: 'critical', test: v => v < 85, label: 'SpO₂ critical' },
    { level: 'warning', test: v => v < 92, label: 'SpO₂ warning' },
  ],
  MAP: [
    { level: 'critical', test: v => v < 45 || v > 120, label: 'MAP critical' },
    { level: 'warning', test: v => v < 55 || v > 100, label: 'MAP warning' },
  ],
  CO2: [
    { level: 'critical', test: v => v < 25 || v > 75, label: 'CO₂ critical' },
    { level: 'warning', test: v => v < 30 || v > 60, label: 'CO₂ warning' },
  ],
  Paw: [
    { level: 'critical', test: v => v > 35, label: 'Paw critical' },
    { level: 'warning', test: v => v > 28, label: 'Paw warning' },
  ],
  FiO2: [
    { level: 'critical', test: v => v >= 0.85 || v >= 85, label: 'FiO₂ high support' },
    { level: 'warning', test: v => v >= 0.60 || v >= 60, label: 'FiO₂ moderate support' },
  ],
};

const EXTENDED_SNAPSHOT_MAX_SAMPLES = 200;
const WAVEFORM_TREND_WINDOW_S = 20;
const WAVEFORM_MAX_SAMPLES = 720;
const POPUP_CHART_DEFS = [
  { id: 'MAP', label: 'MAP', primary: 'MAP', source: 'bedside', unit: 'mmHg' },
  { id: 'SpO2', label: 'SpO₂', primary: 'SpO2_percent', source: 'bedside', unit: '%' },
  { id: 'CO2', label: 'PaCO₂ / EtCO₂', primary: 'PaCO2', secondary: 'EtCO2', source: 'bedside', unit: 'mmHg' },
  { id: 'HR', label: 'HR', primary: 'HR', source: 'bedside', unit: 'bpm' },
  { id: 'Paw', label: 'Paw', primary: 'Paw', source: 'bedside', unit: 'cmH₂O' },
  { id: 'lactate', label: 'Lattato', primary: 'lactate', source: 'snapshot', unit: 'mmol/L' },
  { id: 'urine', label: 'Diuresi', primary: 'urine_rate_mL_h', source: 'snapshot', unit: 'mL/h' },
  { id: 'fluid_balance', label: 'Bilancio fluidi', primary: 'fluid_balance', source: 'snapshot', unit: 'mL' },
  { id: 'DO2VO2', label: 'DO₂ / VO₂', primary: 'DO2', secondary: 'VO2', source: 'snapshot', unit: 'mL/min' },
  { id: 'glucose', label: 'Glucosio', primary: 'glucose_mmol_L', source: 'snapshot', unit: 'mmol/L' },
  { id: 'capnogram', label: 'Capnografia', type: 'capnogram', source: 'waveform', unit: 'mmHg' },
  { id: 'flow_volume', label: 'Flow-volume loop', type: 'flow_volume', source: 'waveform', unit: 'L/s / mL' },
  { id: 'pressure_volume', label: 'Pressure-volume loop', type: 'pressure_volume', source: 'waveform', unit: 'cmH2O / mL' },
];

const EXTENDED_MONITOR_GROUPS = [
  {
    title: 'Emodinamica / perfusione',
    open: true,
    items: [
      { label: 'SBP/DBP', combo: ['SBP', 'DBP'], unit: 'mmHg', digits: 0 },
      { label: 'MAP', keys: ['MAP'], unit: 'mmHg', digits: 0 },
      { label: 'HR', keys: ['HR'], unit: 'bpm', digits: 0 },
      { label: 'CO', keys: ['CO', 'cardiac_output_L_min'], unit: 'L/min', digits: 2 },
      { label: 'SV', keys: ['SV', 'stroke_volume_mL'], unit: 'mL', digits: 1 },
      { label: 'CVP', keys: ['CVP'], unit: 'mmHg', digits: 1 },
      { label: 'PAWP', keys: ['PAWP', 'PCWP'], unit: 'mmHg', digits: 1 },
      { label: 'PAP mean', keys: ['PAP_mean', 'mPAP'], unit: 'mmHg', digits: 1 },
      { label: 'SVR', keys: ['SVR', 'R_sys'], unit: '', digits: 2 },
      { label: 'PVR', keys: ['PVR', 'R_pulm'], unit: '', digits: 2 },
      { label: 'ScvO₂', derived: 'ScvO2', unit: '%', digits: 0 },
      { label: 'DO₂', keys: ['DO2'], unit: 'mL/min', digits: 0 },
      { label: 'VO₂', keys: ['VO2'], unit: 'mL/min', digits: 0 },
      { label: 'Lattato', keys: ['lactate'], unit: 'mmol/L', digits: 1 },
    ],
  },
  {
    title: 'Respiratorio',
    open: true,
    items: [
      { label: 'SpO₂', keys: ['SpO2_percent', 'SaO2'], unit: '%', digits: 0, percentFraction: true },
      { label: 'PaO₂', keys: ['PaO2'], unit: 'mmHg', digits: 0 },
      { label: 'PaCO₂', keys: ['PaCO2'], unit: 'mmHg', digits: 0 },
      { label: 'EtCO₂', keys: ['EtCO2', 'EtCO2_proxy'], unit: 'mmHg', digits: 0 },
      { label: 'A-a EtCO₂', keys: ['etco2_pa_gradient'], unit: 'mmHg', digits: 1 },
      { label: 'Vt', keys: ['Vt_mL', 'Vt'], unit: 'mL', digits: 0 },
      { label: 'RR', keys: ['RR_total', 'RR'], unit: '/min', digits: 0 },
      { label: 'Paw', keys: ['Paw'], unit: 'cmH₂O', digits: 1 },
      { label: 'PEEP', keys: ['PEEP'], unit: 'cmH₂O', digits: 1 },
      { label: 'PIP', keys: ['PIP', 'Ppeak'], unit: 'cmH₂O', digits: 1 },
      { label: 'Pmean', keys: ['Pmean', 'mean_airway_pressure', 'Paw'], unit: 'cmH₂O', digits: 1 },
      { label: 'Pplat', keys: ['Pplat', 'P_plateau'], unit: 'cmH₂O', digits: 1 },
      { label: 'Driving P', keys: ['Pdriving'], unit: 'cmH₂O', digits: 1 },
      { label: 'MP', keys: ['MP'], unit: 'J/min', digits: 2 },
      { label: 'Compliance', keys: ['compliance_dyn', 'C_rs', 'compliance_mL_cmH2O'], unit: 'mL/cmH₂O', digits: 1 },
      { label: 'Resistance', keys: ['resistance_meas', 'R_rs', 'resistance_cmH2O_L_s'], unit: 'cmH₂O/L/s', digits: 1 },
      { label: 'Shunt', keys: ['vq_shunt_frac'], unit: '%', digits: 0, percent: true },
      { label: 'Dead space', keys: ['vq_deadspace_frac'], unit: '%', digits: 0, percent: true },
    ],
  },
  {
    title: 'Metabolico / labs',
    open: true,
    items: [
      { label: 'Lattato', keys: ['lactate'], unit: 'mmol/L', digits: 1 },
      { label: 'Glucosio', keys: ['glucose_mmol_L', 'glucose'], unit: 'mmol/L', digits: 1 },
      { label: 'K⁺', keys: ['K_mmol_L', 'K'], unit: 'mmol/L', digits: 1 },
      { label: 'Na⁺', keys: ['Na_mmol_L', 'Na'], unit: 'mmol/L', digits: 0 },
      { label: 'Hb', keys: ['Hb'], unit: 'g/dL', digits: 1 },
      { label: 'pH', keys: ['pH_a', 'pH'], unit: '', digits: 2 },
      { label: 'HCO₃⁻', keys: ['HCO3_mmol_L', 'HCO3'], unit: 'mmol/L', digits: 1 },
      { label: 'BE', keys: ['BE_mmol_L', 'base_excess_mmol_L'], unit: 'mmol/L', digits: 1 },
      { label: 'Temp', keys: ['T_core', 'temperature_C'], unit: '°C', digits: 1 },
      { label: 'Albumina', keys: ['albumin_g_dL'], unit: 'g/dL', digits: 1 },
    ],
  },
  {
    title: 'Neurologico / sedazione',
    open: true,
    items: [
      { label: 'GCS proxy', keys: ['GCS_proxy', 'GCS'], unit: '', digits: 0 },
      { label: 'RASS proxy', keys: ['RASS_proxy', 'RASS'], unit: '', digits: 0 },
      { label: 'ICP', keys: ['ICP_mmHg', 'ICP'], unit: 'mmHg', digits: 1 },
      { label: 'CPP', keys: ['CPP_mmHg', 'CPP'], unit: 'mmHg', digits: 1 },
      { label: 'Pain score', keys: ['pain_score'], unit: '', digits: 1 },
      { label: 'Sedation score', keys: ['sedation_score'], unit: '', digits: 1 },
      { label: 'NMB', keys: ['drug_NMB_frac'], unit: '%', digits: 0, percent: true },
      { label: 'NMB active', keys: ['neuromuscular_blockade_active'], unit: '', digits: 0 },
    ],
  },
  {
    title: 'Renale / fluidi',
    open: true,
    items: [
      { label: 'Diuresi', keys: ['urine_rate_mL_h'], unit: 'mL/h', digits: 0 },
      { label: 'Diuresi/kg', keys: ['urine_output_mL_kg_h', 'urine_mL_kg_h'], unit: 'mL/kg/h', digits: 2 },
      { label: 'Bilancio', keys: ['fluid_balance', 'fluid_balance_mL'], unit: 'mL', digits: 0 },
      { label: 'Creatinina', keys: ['creatinine_mg_dL'], unit: 'mg/dL', digits: 2 },
      { label: 'GFR', keys: ['GFR'], unit: 'mL/min', digits: 1 },
      { label: 'Urea', keys: ['urea_mmol_L', 'BUN_mg_dL'], unit: 'mmol/L', digits: 1 },
      { label: 'Blood volume', keys: ['blood_volume_mL'], unit: 'mL', digits: 0 },
      { label: 'Overload', keys: ['fluid_overload_fraction', 'fluid_overload_percent'], unit: '%', digits: 0, percent: true },
      { label: 'CRRT rate', keys: ['CRRT_net_UF_mL_h', 'CRRT_UF_mL_h_effective', 'crrt_net_ultrafiltration_mL_h', 'CRRT_UF_mL_h'], unit: 'mL/h', digits: 0 },
    ],
  },
  {
    title: 'Coagulazione / ematologia',
    open: false,
    items: [
      { label: 'PLT', keys: ['platelets_10e9_L', 'PLT', 'PLT_count'], unit: '×10⁹/L', digits: 0 },
      { label: 'INR', keys: ['INR'], unit: '', digits: 2 },
      { label: 'Coag score', keys: ['coag_score', 'sepsis_coag_mod'], unit: '', digits: 2 },
      { label: 'Fibrinogeno', keys: ['fibrinogen_mg_dL', 'fibrinogen'], unit: 'mg/dL', digits: 0 },
      { label: 'D-dimero', keys: ['d_dimer_mg_L', 'D_dimer', 'd_dimer'], unit: 'mg/L', digits: 2 },
      { label: 'Hct', keys: ['Hct', 'Hct_percent'], unit: '%', digits: 0, percentFraction: true },
      { label: 'WBC', keys: ['WBC_10e9_L', 'WBC', 'WBC_count'], unit: '×10⁹/L', digits: 1 },
      { label: 'Bleeding risk', keys: ['bleeding_risk_index'], unit: '', digits: 2 },
    ],
  },
  {
    title: 'Epatico',
    open: false,
    items: [
      { label: 'Bilirubina totale', keys: ['bilirubin_total_mg_dL', 'bilirubin_mg_dL', 'total_bilirubin_mg_dL'], unit: 'mg/dL', digits: 1 },
      { label: 'Bilirubina diretta', keys: ['direct_bilirubin_mg_dL', 'bilirubin_direct_mg_dL'], unit: 'mg/dL', digits: 1 },
      { label: 'AST', keys: ['AST_U_L'], unit: 'U/L', digits: 0 },
      { label: 'ALT', keys: ['ALT_U_L'], unit: 'U/L', digits: 0 },
      { label: 'Albumina', keys: ['albumin_g_dL'], unit: 'g/dL', digits: 1 },
      { label: 'Ammonio', keys: ['ammonia_umol_L'], unit: 'µmol/L', digits: 0 },
      { label: 'Hepatic severity', keys: ['hepatic_severity_score'], unit: '', digits: 2 },
    ],
  },
  {
    title: 'Infezione / sepsi',
    open: false,
    items: [
      { label: 'Temp', keys: ['T_core', 'temperature_C'], unit: '°C', digits: 1 },
      { label: 'CRP proxy', keys: ['CRP_proxy', 'CRP_mg_L'], unit: 'mg/L', digits: 0 },
      { label: 'PCT proxy', keys: ['PCT_proxy', 'procalcitonin_proxy'], unit: '', digits: 2 },
      { label: 'Microbial burden', keys: ['microbial_burden', 'bacterial_load'], unit: '', digits: 2 },
      { label: 'Antibiotic coverage', keys: ['antibiotic_coverage'], unit: '%', digits: 0, percentFraction: true },
      { label: 'SIRS score', keys: ['SIRS_score', 'sepsis_severity_score', 'infection_severity_score'], unit: '', digits: 1 },
      { label: 'Sepsis phenotype', keys: ['sepsis_phenotype_code'], unit: '', digits: 0 },
      { label: 'Vasoplegia', keys: ['vasoplegia_index'], unit: '', digits: 2 },
    ],
  },
  {
    title: 'Ventilazione avanzata',
    open: false,
    items: [
      { label: 'VILI risk', keys: ['VILI_risk_index', 'VILI_risk'], unit: '', digits: 2 },
      { label: 'Overdistension', keys: ['overdistension_index'], unit: '', digits: 2 },
      { label: 'Atelectrauma', keys: ['atelectrauma_index'], unit: '', digits: 2 },
      { label: 'Auto-PEEP', keys: ['auto_PEEP', 'auto_PEEP_cmH2O'], unit: 'cmH₂O', digits: 1 },
      { label: 'WOB', keys: ['WOB', 'work_of_breathing_J_min'], unit: '', digits: 2 },
      { label: 'Recruited fraction', keys: ['recruited_frac'], unit: '%', digits: 0, percentFraction: true },
      { label: 'Air trapping', keys: ['air_trapping_index'], unit: '', digits: 2 },
      { label: 'Bronchospasm', keys: ['bronchospasm_index'], unit: '', digits: 2 },
    ],
  },
  {
    title: 'Farmaci / concentrazioni',
    open: false,
    items: [
      { label: 'C fentanyl', keys: ['C_fentanyl_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C morphine', keys: ['C_morphine_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C remifentanil', keys: ['C_remifentanil_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C midazolam', keys: ['C_midazolam_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C propofol', keys: ['C_propofol_mcg_mL', 'C_propofol_mg_L'], unit: 'µg/mL', digits: 2 },
      { label: 'C ketamine', keys: ['C_ketamine_mg_L'], unit: 'mg/L', digits: 2 },
      { label: 'C dexmed', keys: ['C_dexmedetomidine_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C norad', keys: ['C_noradrenaline_ng_mL', 'C_norad_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'C adrenaline', keys: ['C_adrenaline_ng_mL'], unit: 'ng/mL', digits: 2 },
      { label: 'NMB signal', keys: ['rocuronium_nmb_signal'], unit: '%', digits: 0, percent: true },
      { label: 'Insulin signal', keys: ['insulin_action_signal'], unit: '%', digits: 0, percent: true },
      { label: 'Furosemide signal', keys: ['furosemide_diuresis_signal'], unit: '%', digits: 0, percent: true },
    ],
  },
  {
    title: 'Nutrizione / catabolismo',
    open: false,
    items: [
      { label: 'Energy balance', keys: ['energy_balance_kcal_day'], unit: 'kcal/d', digits: 0 },
      { label: 'GIR', keys: ['GIR_mg_kg_min'], unit: 'mg/kg/min', digits: 1 },
      { label: 'Protein balance', keys: ['protein_balance_g_day'], unit: 'g/d', digits: 1 },
      { label: 'Catabolism index', keys: ['catabolism_index'], unit: '', digits: 2 },
      { label: 'REE', keys: ['REE_kcal_day', 'energy_expenditure_kcal_day'], unit: 'kcal/d', digits: 0 },
      { label: 'Nutrition delivery', keys: ['nutrition_delivery_fraction', 'energy_intake_fraction', 'nutrition_severity_score'], unit: '%', digits: 0, percentFraction: true },
    ],
  },
];


function controlNumberValue(el) {
  const n = Number(el && el.value);
  return Number.isFinite(n) ? n : 0;
}
function fluidTypeLabel(value) {
  const labels = {
    normal_saline: 'Fisiologica',
    ringer_lactate: 'Ringer',
    sterofundin: 'Sterofundin',
    dextrose_5: 'Glucosata 5%',
  };
  return labels[value] || value || '--';
}
function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}
function markControlTouched(key) {
  liveControlLastTouched.set(key, performance.now());
}
function canSyncControl(key, el) {
  if (!el) return false;
  if (document.activeElement === el) return false;
  const last = liveControlLastTouched.get(key) || 0;
  return (performance.now() - last) > CONTROL_SYNC_GRACE_MS;
}

function controlElementForKey(key) {
  if (!key) return null;
  if (key.startsWith('drug:')) return document.querySelector(`input[data-drug="${key.slice(5)}"]`);
  if (key === 'crystalloid_type') return document.querySelector('select[data-crystalloid-type]');
  return $(key);
}
function setControlStatus(key, status='idle') {
  const el = controlElementForKey(key);
  if (!el) return;
  const wrap = el.closest('label') || el;
  wrap.classList.remove('control-pending', 'control-confirmed', 'control-error');
  if (controlStatusTimers.has(key)) clearTimeout(controlStatusTimers.get(key));
  if (status && status !== 'idle') {
    wrap.classList.add(`control-${status}`);
    if (status === 'confirmed') {
      controlStatusTimers.set(key, setTimeout(() => {
        wrap.classList.remove('control-confirmed');
        controlStatusTimers.delete(key);
      }, 900));
    }
  }
}
function markControlPending(key, value) {
  const n = Number(value);
  controlPendingValues.set(key, Number.isFinite(n) ? n : value);
  setControlStatus(key, 'pending');
}
function markControlError(key) {
  controlPendingValues.delete(key);
  setControlStatus(key, 'error');
}
function confirmControlIfMatched(key, observedValue) {
  if (!controlPendingValues.has(key)) return;
  const expected = Number(controlPendingValues.get(key));
  const observed = Number(observedValue);
  if (!Number.isFinite(expected) || !Number.isFinite(observed)) return;
  const tolerance = Math.max(0.015, Math.abs(expected) * 0.03);
  if (Math.abs(expected - observed) <= tolerance) {
    controlPendingValues.delete(key);
    setControlStatus(key, 'confirmed');
  }
}
function syncControlsFromActionResponse(data) {
  const st = data?.session?.state;
  if (st) syncControlsFromState(st);
}
function setControlElementValue(el, value, output=null, formatter=(v) => String(v)) {
  const n = Number(value);
  if (!Number.isFinite(n)) return;
  const next = String(n);
  if (el.value !== next) el.value = next;
  if (output) output.textContent = formatter(n);
}
function syncControlsFromState(st) {
  const controls = st.controls || {};
  for (const [inputId, cfg] of Object.entries(RANGE_CONTROL_BINDINGS)) {
    const input = $(inputId);
    const output = $(cfg.outputId);
    const value = controls[cfg.key] ?? st[cfg.key];
    if (value === undefined || value === null) continue;
    confirmControlIfMatched(inputId, value);
    if (canSyncControl(inputId, input)) setControlElementValue(input, value, output, cfg.formatter);
  }
  document.querySelectorAll('input[data-drug]').forEach(inp => {
    const action = inp.dataset.drug;
    const stateKey = DRUG_CONTROL_BINDINGS[action];
    if (!stateKey) return;
    const value = controls[stateKey] ?? st[stateKey];
    if (value === undefined || value === null) return;
    const controlKey = `drug:${action}`;
    confirmControlIfMatched(controlKey, value);
    if (canSyncControl(controlKey, inp)) setControlElementValue(inp, value);
  });
  const fluidType = controls.crystalloid_type ?? st.crystalloid_type;
  if (fluidType !== undefined && fluidType !== null) {
    document.querySelectorAll('select[data-crystalloid-type]').forEach(sel => {
      if (canSyncControl('crystalloid_type', sel) && sel.value !== String(fluidType)) sel.value = String(fluidType);
    });
  }
  renderFluidControls(st);
}
function scheduleLiveAction(key, action, payloadFactory, options={}) {
  if (!sessionId) return;
  const payloadPreview = payloadFactory();
  markControlPending(key, payloadPreview.value);
  const delayMs = options.delayMs ?? LIVE_CONTROL_DEBOUNCE_MS;
  if (liveControlTimers.has(key)) clearTimeout(liveControlTimers.get(key));
  liveControlTimers.set(key, setTimeout(() => {
    liveControlTimers.delete(key);
    sendAction(action, payloadFactory(), { silent: options.silent ?? true })
      .then(syncControlsFromActionResponse)
      .catch(e => {
        console.error(e);
        markControlError(key);
        setStatus('action error');
      });
  }, delayMs));
}
function flushLiveAction(key, action, payloadFactory, options={}) {
  const payloadPreview = payloadFactory();
  markControlPending(key, payloadPreview.value);
  if (liveControlTimers.has(key)) {
    clearTimeout(liveControlTimers.get(key));
    liveControlTimers.delete(key);
  }
  return sendAction(action, payloadFactory(), { silent: options.silent ?? false })
    .then(data => { syncControlsFromActionResponse(data); return data; })
    .catch(e => { markControlError(key); throw e; });
}
function bindLiveRange(inputId, outputId, action, formatter=(v) => String(v)) {
  const input = $(inputId);
  const output = $(outputId);
  if (!input) return;
  const payloadFactory = () => ({ value: controlNumberValue(input) });
  const render = () => { if (output) output.textContent = formatter(controlNumberValue(input)); };
  input.oninput = () => {
    markControlTouched(inputId);
    render();
    scheduleLiveAction(inputId, action, payloadFactory, { silent: true });
  };
  input.onchange = () => {
    markControlTouched(inputId);
    render();
    flushLiveAction(inputId, action, payloadFactory, { silent: false }).catch(reportUiError);
  };
}
function bindLiveNumericInput(input, action) {
  // Test sentinel kept from v3.1-step1: input.oninput = () => scheduleLiveAction
  // Test sentinel kept from v3.1-step1: input.onchange = () => flushLiveAction
  if (!input) return;
  const key = `drug:${action}`;
  const payloadFactory = () => ({ value: controlNumberValue(input) });
  input.oninput = () => {
    markControlTouched(key);
    scheduleLiveAction(key, action, payloadFactory, { silent: true });
  };
  input.onchange = () => {
    markControlTouched(key);
    flushLiveAction(key, action, payloadFactory, { silent: false }).catch(reportUiError);
  };
}
function bindCrystalloidTypeSelect(sel) {
  if (!sel) return;
  sel.onchange = () => {
    markControlTouched('crystalloid_type');
    const value = sel.value;
    document.querySelectorAll('select[data-crystalloid-type]').forEach(other => {
      if (other !== sel) other.value = value;
    });
    sendAction('set_crystalloid_type', { value }, { silent: false })
      .then(syncControlsFromActionResponse)
      .catch(e => { markControlError('crystalloid_type'); reportUiError(e); });
  };
}

function renderFluidControls(st={}) {
  const type = st.crystalloid_type || 'normal_saline';
  const active = !!st.crystalloid_active || Number(st.crystalloid_effective_mL_h || st.crystalloid_rate_mL_h || 0) > 0;
  const rate = Number(st.crystalloid_effective_mL_h ?? st.crystalloid_rate_mL_h ?? 0);
  const response = Number(st.crystalloid_preload_response);
  const mapSupport = Number(st.crystalloid_MAP_support_mmHg);
  const urine = Number(st.urine_rate_mL_h);
  const balance = Number(st.fluid_balance);
  setText('fluidQuickStatus', active ? `${fluidTypeLabel(type)} ${fmt(rate, 0)} mL/h` : 'off');
  setText('fluidQuickResp', Number.isFinite(response) ? fmt(response, 2) : '--');
  setText('fluidQuickMap', Number.isFinite(mapSupport) ? `${fmt(mapSupport, 1)}` : '--');
  setText('fluidQuickUrine', Number.isFinite(urine) ? `${fmt(urine, 0)} mL/h` : '--');
  setText('fluidQuickBalance', Number.isFinite(balance) ? `${fmt(balance, 0)} mL` : '--');
  setText('fluidAuditType', fluidTypeLabel(type));
  setText('fluidAuditRate', `${fmt(rate, 0)} mL/h`);
  setText('fluidAuditResponse', Number.isFinite(response) ? fmt(response, 2) : '--');
  setText('fluidAuditMap', Number.isFinite(mapSupport) ? `+${fmt(mapSupport, 1)} mmHg` : '--');
  setText('fluidAuditUrine', Number.isFinite(urine) ? `${fmt(urine, 0)} mL/h` : '--');
  setText('fluidAuditBalance', Number.isFinite(balance) ? `${fmt(balance, 0)} mL` : '--');
  const panel = $('fluidQuickPanel');
  if (panel) panel.classList.toggle('fluid-active', active);
}

function bedsideTrendValue(st, key) {
  if (!st) return null;
  if (key === 'SpO2_percent') {
    const spo2 = Number(st.SpO2_percent ?? st.SaO2);
    if (!Number.isFinite(spo2)) return null;
    return spo2 <= 1.5 ? spo2 * 100.0 : spo2;
  }
  if (key === 'FiO2') {
    const fio2 = Number(st.FiO2_delivered ?? st.FiO2);
    if (!Number.isFinite(fio2)) return null;
    return fio2 <= 1.5 ? fio2 * 100.0 : fio2;
  }
  if (key === 'EtCO2') {
    const etco2 = Number(st.EtCO2 ?? st.EtCO2_proxy);
    return Number.isFinite(etco2) ? etco2 : null;
  }
  const value = Number(st[key]);
  return Number.isFinite(value) ? value : null;
}
function pushBedsideTrend(st, envelope={}) {
  if (!st) return;
  const tRaw = Number(envelope.time_s ?? st.time_s ?? st.t);
  const t = Number.isFinite(tRaw) ? tRaw : performance.now() / 1000.0;
  const last = bedsideTrendBuffer[bedsideTrendBuffer.length - 1];
  if (last && t < last.t) bedsideTrendBuffer.length = 0;
  const sample = { t };
  for (const def of SPARKLINE_DEFS) {
    sample[def.primary] = bedsideTrendValue(st, def.primary);
    if (def.secondary) sample[def.secondary] = bedsideTrendValue(st, def.secondary);
  }
  if (last && Math.abs(last.t - t) < 1e-6) bedsideTrendBuffer[bedsideTrendBuffer.length - 1] = sample;
  else bedsideTrendBuffer.push(sample);
  const latestT = bedsideTrendBuffer[bedsideTrendBuffer.length - 1]?.t ?? t;
  while (bedsideTrendBuffer.length > TREND_MAX_SAMPLES || (bedsideTrendBuffer.length > 2 && latestT - bedsideTrendBuffer[0].t > TREND_WINDOW_S)) {
    bedsideTrendBuffer.shift();
  }
}
function resolveTrendColor(canvas, attr, fallback='--text') {
  const token = canvas?.dataset?.[attr] || fallback;
  const styles = getComputedStyle(document.documentElement);
  if (token.startsWith('--')) return styles.getPropertyValue(token).trim() || styles.getPropertyValue(fallback).trim() || '#e7f0f8';
  return token;
}
function resizeCanvasToDisplaySize(canvas) {
  const ratio = Math.max(window.devicePixelRatio || 1, 1);
  const width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
  const height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  return { width, height, ratio };
}
function seriesRange(seriesA, seriesB=[]) {
  const values = [...seriesA, ...seriesB].filter(v => Number.isFinite(v));
  if (!values.length) return null;
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (Math.abs(hi - lo) < 1e-6) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.18;
  return { lo: lo - pad, hi: hi + pad };
}
function drawSeries(ctx, points, xOf, yOf, color, width) {
  if (points.length < 2) return;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = xOf(p);
    const y = yOf(p.value);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();
}
function drawSparklineGrid(ctx, width, height, canvas) {
  const ratio = window.devicePixelRatio || 1;
  const padX = 2 * ratio;
  ctx.save();
  ctx.globalAlpha = 0.38;
  ctx.strokeStyle = 'rgba(141,163,181,.18)';
  ctx.lineWidth = Math.max(1, ratio);
  for (let i = 1; i < 3; i++) {
    const y = (height * i) / 3;
    ctx.beginPath();
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
  }
  ctx.globalAlpha = 0.72;
  ctx.strokeStyle = resolveTrendColor(canvas, 'trendColor', '--text');
  ctx.beginPath();
  ctx.moveTo(padX, height / 2);
  ctx.lineTo(width - padX, height / 2);
  ctx.stroke();
  ctx.restore();
}
function drawSparkline(canvasId, primaryKey, secondaryKey=null) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const { width, height } = resizeCanvasToDisplaySize(canvas);
  ctx.clearRect(0, 0, width, height);
  drawSparklineGrid(ctx, width, height, canvas);
  if (bedsideTrendBuffer.length < 2) {
    ctx.save();
    ctx.fillStyle = 'rgba(141,163,181,.70)';
    ctx.font = `${9 * (window.devicePixelRatio || 1)}px ui-monospace, monospace`;
    ctx.fillText('waiting data', 5 * (window.devicePixelRatio || 1), height - 5 * (window.devicePixelRatio || 1));
    ctx.restore();
    return;
  }
  const primary = bedsideTrendBuffer
    .map(s => ({ t: s.t, value: s[primaryKey] }))
    .filter(p => Number.isFinite(p.value));
  const secondary = secondaryKey ? bedsideTrendBuffer
    .map(s => ({ t: s.t, value: s[secondaryKey] }))
    .filter(p => Number.isFinite(p.value)) : [];
  if (primary.length < 2 && secondary.length < 2) return;
  const range = seriesRange(primary.map(p => p.value), secondary.map(p => p.value));
  if (!range) return;
  const t0 = bedsideTrendBuffer[0].t;
  const t1 = bedsideTrendBuffer[bedsideTrendBuffer.length - 1].t;
  const span = Math.max(t1 - t0, 1);
  const padX = 3 * (window.devicePixelRatio || 1);
  const padY = 4 * (window.devicePixelRatio || 1);
  const xOf = (p) => padX + ((p.t - t0) / span) * Math.max(1, width - 2 * padX);
  const yOf = (value) => height - padY - ((value - range.lo) / Math.max(range.hi - range.lo, 1e-6)) * Math.max(1, height - 2 * padY);
  ctx.globalAlpha = secondary.length ? 0.70 : 0.95;
  drawSeries(ctx, secondary, xOf, yOf, resolveTrendColor(canvas, 'secondaryColor', '--muted'), 1.6 * (window.devicePixelRatio || 1));
  ctx.globalAlpha = 1.0;
  drawSeries(ctx, primary, xOf, yOf, resolveTrendColor(canvas, 'trendColor', '--text'), 2.2 * (window.devicePixelRatio || 1));
  ctx.globalAlpha = 1.0;
}
function renderVitalSparklines() {
  for (const def of SPARKLINE_DEFS) drawSparkline(def.canvasId, def.primary, def.secondary || null);
}

function pushExtendedSnapshot(st) {
  if (!st) return;
  const tRaw = Number(st.time_s ?? st.t ?? lastBedsideState.time_s ?? lastBedsideState.t);
  const t = Number.isFinite(tRaw) ? tRaw : performance.now() / 1000.0;
  const last = extendedSnapshotBuffer[extendedSnapshotBuffer.length - 1];
  if (last && t < last.t) extendedSnapshotBuffer.length = 0;
  const sample = { t, ...st };
  if (last && Math.abs(last.t - t) < 1e-6) extendedSnapshotBuffer[extendedSnapshotBuffer.length - 1] = sample;
  else extendedSnapshotBuffer.push(sample);
  while (extendedSnapshotBuffer.length > EXTENDED_SNAPSHOT_MAX_SAMPLES) extendedSnapshotBuffer.shift();
}
function pushWaveformTrend(st) {
  if (!st) return;
  const tRaw = Number(st.time_s ?? st.t);
  const t = Number.isFinite(tRaw) ? tRaw : performance.now() / 1000.0;
  const last = waveformTrendBuffer[waveformTrendBuffer.length - 1];
  const dt = last ? Math.max(0, Math.min(t - last.t, 0.25)) : 0;
  const flowMlS = Number(st.Flow_current_mL_s ?? (Number(st.flow_L_s) * 1000.0));
  const flow = Number.isFinite(flowMlS) ? flowMlS : 0;
  if (!last || (flow > 20 && Number(last.flow_mL_s || 0) <= 0)) waveformLoopVolumeMl = 0;
  waveformLoopVolumeMl += flow * dt;
  const vt = Number(st.Vt ?? 0);
  const maxVolume = Math.max(Number.isFinite(vt) ? vt * 1.5 : 0, 80);
  waveformLoopVolumeMl = Math.max(0, Math.min(waveformLoopVolumeMl, maxVolume));
  const sample = {
    t,
    EtCO2: Number(st.EtCO2 ?? st.EtCO2_proxy ?? 0),
    PaCO2: Number(st.PaCO2 ?? 0),
    RR_total: Number(st.RR_total ?? lastBedsideState.RR_total ?? 25),
    Paw: Number(st.Paw ?? 0),
    PEEP: Number(st.PEEP ?? 0),
    Vt: Number.isFinite(vt) ? vt : waveformLoopVolumeMl,
    volume_mL: waveformLoopVolumeMl,
    flow_mL_s: flow,
    flow_L_s: flow / 1000.0,
  };
  if (last && Math.abs(last.t - t) < 1e-6) waveformTrendBuffer[waveformTrendBuffer.length - 1] = sample;
  else waveformTrendBuffer.push(sample);
  const cutoff = t - WAVEFORM_TREND_WINDOW_S;
  while (waveformTrendBuffer.length > WAVEFORM_MAX_SAMPLES || (waveformTrendBuffer[0] && waveformTrendBuffer[0].t < cutoff)) waveformTrendBuffer.shift();
}
function capnogramValue(sample) {
  const et = Math.max(Number(sample.EtCO2 || 0), 0);
  const rr = Math.max(Number(sample.RR_total || 25), 4);
  const period = 60.0 / rr;
  const phase = ((sample.t % period) / period + 1) % 1;
  if (phase < 0.18) return et * 0.05;
  if (phase < 0.30) return et * ((phase - 0.18) / 0.12);
  if (phase < 0.72) return et * (0.88 + 0.12 * (phase - 0.30) / 0.42);
  if (phase < 0.82) return et * (1.0 - (phase - 0.72) / 0.10);
  return et * 0.04;
}
function drawAxisLabel(ctx, text, x, y, ratio) {
  ctx.fillStyle = '#8da2b3';
  ctx.font = `${12 * ratio}px ui-monospace, monospace`;
  ctx.fillText(text, x, y);
}
function drawCapnogram(ctx, width, height, ratio, msg) {
  const samples = waveformTrendBuffer.filter(s => Number.isFinite(s.EtCO2) && Number.isFinite(s.t));
  if (samples.length < 8) {
    if (msg) msg.textContent = 'Servono campioni waveform: avvia la sessione e attendi qualche secondo.';
    return;
  }
  const t0 = samples[0].t;
  const t1 = samples[samples.length - 1].t;
  const span = Math.max(t1 - t0, 1);
  const maxEt = Math.max(...samples.map(s => capnogramValue(s)), 10);
  const padX = 44 * ratio, padY = 28 * ratio;
  const xOf = s => padX + ((s.t - t0) / span) * Math.max(1, width - 2 * padX);
  const yOf = v => height - padY - (v / Math.max(maxEt, 1)) * Math.max(1, height - 2 * padY);
  ctx.strokeStyle = 'rgba(255,214,77,.92)';
  ctx.lineWidth = 2.2 * ratio;
  ctx.beginPath();
  samples.forEach((s, i) => { const x = xOf(s), y = yOf(capnogramValue(s)); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
  ctx.stroke();
  drawAxisLabel(ctx, `${maxEt.toFixed(0)} mmHg`, 8 * ratio, padY, ratio);
  drawAxisLabel(ctx, '0', 8 * ratio, height - padY, ratio);
  if (msg) msg.textContent = `Capnogramma accoppiato a EtCO2 reale · ${samples.length} campioni · EtCO2 ${samples[samples.length - 1].EtCO2.toFixed(0)} mmHg`;
}
function loopRange(values, fallbackLo=0, fallbackHi=1) {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return { lo: fallbackLo, hi: fallbackHi };
  const lo = Math.min(...finite), hi = Math.max(...finite);
  const pad = Math.max((hi - lo) * 0.08, 1);
  return { lo: lo - pad, hi: hi + pad };
}
function drawRespLoop(ctx, width, height, ratio, msg, mode) {
  const samples = waveformTrendBuffer.filter(s => Number.isFinite(s.volume_mL) && Number.isFinite(s.Paw));
  const usable = mode === 'flow_volume' ? samples.filter(s => Number.isFinite(s.flow_L_s)) : samples;
  if (usable.length < 12) {
    if (msg) msg.textContent = 'Servono campioni waveform con Vt/flow/Paw: avvia la sessione e attendi qualche secondo.';
    return;
  }
  const padX = 50 * ratio, padY = 30 * ratio;
  const xVals = usable.map(s => s.volume_mL);
  const yVals = mode === 'flow_volume' ? usable.map(s => s.flow_L_s) : usable.map(s => s.Paw);
  const xr = loopRange(xVals, 0, 100);
  const yr = loopRange(yVals, mode === 'flow_volume' ? -1 : 0, mode === 'flow_volume' ? 1 : 30);
  const xOf = v => padX + ((v - xr.lo) / Math.max(xr.hi - xr.lo, 1e-6)) * Math.max(1, width - 2 * padX);
  const yOf = v => height - padY - ((v - yr.lo) / Math.max(yr.hi - yr.lo, 1e-6)) * Math.max(1, height - 2 * padY);
  ctx.strokeStyle = 'rgba(215,232,247,.18)';
  ctx.lineWidth = ratio;
  ctx.beginPath(); ctx.moveTo(padX, padY); ctx.lineTo(padX, height - padY); ctx.lineTo(width - padX, height - padY); ctx.stroke();
  ctx.strokeStyle = mode === 'flow_volume' ? 'rgba(85,221,255,.95)' : 'rgba(255,90,106,.95)';
  ctx.lineWidth = 2.2 * ratio;
  ctx.beginPath();
  usable.forEach((s, i) => {
    const yv = mode === 'flow_volume' ? s.flow_L_s : s.Paw;
    const x = xOf(s.volume_mL), y = yOf(yv);
    if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
  });
  ctx.stroke();
  drawAxisLabel(ctx, 'Volume mL', width - 120 * ratio, height - 8 * ratio, ratio);
  drawAxisLabel(ctx, mode === 'flow_volume' ? 'Flow L/s' : 'Paw cmH2O', 8 * ratio, padY, ratio);
  if (msg) msg.textContent = `${mode === 'flow_volume' ? 'Flow-volume loop' : 'Pressure-volume loop'} · ${usable.length} campioni · volume ${xr.lo.toFixed(0)}-${xr.hi.toFixed(0)} mL`;
}
function chartValue(sample, key) {
  if (!sample) return null;
  if (key === 'SpO2_percent') return bedsideTrendValue(sample, 'SpO2_percent');
  if (key === 'EtCO2') return bedsideTrendValue(sample, 'EtCO2');
  const n = Number(sample[key]);
  return Number.isFinite(n) ? n : null;
}
function chartSeries(def, key) {
  const source = def.source === 'snapshot' ? extendedSnapshotBuffer : bedsideTrendBuffer;
  return source.map(s => ({ t: s.t, value: chartValue(s, key) })).filter(p => Number.isFinite(p.value));
}
function populatePopupChartSelector() {
  const sel = $('popupChartSelect');
  if (!sel || sel.dataset.ready === '1') return;
  sel.innerHTML = POPUP_CHART_DEFS.map(def => `<option value="${def.id}">${def.label}</option>`).join('');
  sel.dataset.ready = '1';
}
function openPopupChart(defaultId='MAP') {
  const overlay = $('popupChartOverlay');
  if (!overlay) return;
  populatePopupChartSelector();
  const sel = $('popupChartSelect');
  if (sel && defaultId) sel.value = defaultId;
  overlay.hidden = false;
  drawPopupChart();
}
function closePopupChart() {
  const overlay = $('popupChartOverlay');
  if (overlay) overlay.hidden = true;
}
function drawPopupChart() {
  const canvas = $('popupChartCanvas');
  const msg = $('popupChartMeta');
  const sel = $('popupChartSelect');
  if (!canvas || !sel) return;
  const def = POPUP_CHART_DEFS.find(d => d.id === sel.value) || POPUP_CHART_DEFS[0];
  const ctx = canvas.getContext('2d');
  const { width, height, ratio } = resizeCanvasToDisplaySize(canvas);
  ctx.clearRect(0, 0, width, height);
  if (def.type === 'capnogram') { drawCapnogram(ctx, width, height, ratio, msg); return; }
  if (def.type === 'flow_volume' || def.type === 'pressure_volume') { drawRespLoop(ctx, width, height, ratio, msg, def.type); return; }
  const primary = chartSeries(def, def.primary);
  const secondary = def.secondary ? chartSeries(def, def.secondary) : [];
  if (primary.length < 2 && secondary.length < 2) {
    if (msg) msg.textContent = def.source === 'snapshot'
      ? 'Servono almeno due snapshot: premi Aggiorna nel Monitor esteso più volte durante la simulazione.'
      : 'Servono almeno due campioni bedside: avvia la sessione per popolare il trend.';
    return;
  }
  const all = primary.length ? primary : secondary;
  const t0 = all[0].t;
  const t1 = all[all.length - 1].t;
  const span = Math.max(t1 - t0, 1);
  const range = seriesRange(primary.map(p => p.value), secondary.map(p => p.value));
  if (!range) return;
  const padX = 44 * ratio;
  const padY = 28 * ratio;
  const xOf = p => padX + ((p.t - t0) / span) * Math.max(1, width - 2 * padX);
  const yOf = value => height - padY - ((value - range.lo) / Math.max(range.hi - range.lo, 1e-6)) * Math.max(1, height - 2 * padY);
  ctx.strokeStyle = 'rgba(215,232,247,.18)';
  ctx.lineWidth = ratio;
  for (let i = 0; i < 4; i++) {
    const y = padY + i * (height - 2 * padY) / 3;
    ctx.beginPath(); ctx.moveTo(padX, y); ctx.lineTo(width - padX, y); ctx.stroke();
  }
  ctx.fillStyle = '#8da2b3';
  ctx.font = `${12 * ratio}px ui-monospace, monospace`;
  ctx.fillText(`${range.hi.toFixed(1)} ${def.unit || ''}`, 6 * ratio, padY + 4 * ratio);
  ctx.fillText(`${range.lo.toFixed(1)}`, 6 * ratio, height - padY + 4 * ratio);
  ctx.globalAlpha = secondary.length ? 0.68 : 0.95;
  drawSeries(ctx, secondary, xOf, yOf, '#9fb0bf', 2 * ratio);
  ctx.globalAlpha = 0.98;
  drawSeries(ctx, primary, xOf, yOf, '#d6e8f7', 2.4 * ratio);
  ctx.globalAlpha = 1.0;
  if (msg) {
    const src = def.source === 'snapshot' ? `${extendedSnapshotBuffer.length} snapshot` : `${bedsideTrendBuffer.length} campioni bedside`;
    msg.textContent = `${def.label} · ${src} · finestra t ${t0.toFixed(1)}–${t1.toFixed(1)} s`;
  }
}

function extendedStateValue(st, item) {
  if (!st) return null;
  if (item.derived === 'ScvO2') return deriveScvO2(st);
  if (item.combo) {
    const a = firstFinite(st, [item.combo[0]]);
    const b = firstFinite(st, [item.combo[1]]);
    if (a === null || b === null) return null;
    return `${fmt(a, item.digits ?? 0)}/${fmt(b, item.digits ?? 0)}`;
  }
  let value = firstFinite(st, item.keys || []);
  if (value === null) return null;
  if (item.percent) value *= 100.0;
  if (item.percentFraction && value <= 1.5) value *= 100.0;
  return value;
}
function firstFinite(st, keys) {
  for (const key of keys) {
    if (!key || st[key] === undefined || st[key] === null) continue;
    const n = Number(st[key]);
    if (Number.isFinite(n)) return n;
  }
  return null;
}
function deriveScvO2(st) {
  const explicit = firstFinite(st, ['ScvO2', 'SvO2']);
  if (explicit !== null) return explicit <= 1.5 ? explicit * 100.0 : explicit;
  const sao2 = firstFinite(st, ['SaO2']);
  const vo2 = firstFinite(st, ['VO2']);
  const co = firstFinite(st, ['CO']);
  const hb = firstFinite(st, ['Hb']);
  if (sao2 === null || vo2 === null || co === null || hb === null || co <= 0 || hb <= 0) return null;
  const scvo2 = (sao2 - (vo2 / Math.max(co * hb * 1.34 * 10.0, 1e-6))) * 100.0;
  return Math.max(5, Math.min(100, scvo2));
}
function formatExtendedValue(st, item) {
  const value = extendedStateValue(st, item);
  if (value === null || value === undefined) return '--';
  if (typeof value === 'string') return `${value}${item.unit ? ' ' + item.unit : ''}`;
  const digits = item.digits ?? 1;
  return `${fmt(value, digits)}${item.unit ? ' ' + item.unit : ''}`;
}

const EMOGAS_ITEMS = [
  { label: 'pH', keys: ['pH_a', 'pH'], unit: '', digits: 2 },
  { label: 'PaO2', keys: ['PaO2'], unit: 'mmHg', digits: 0 },
  { label: 'PaCO2', keys: ['PaCO2'], unit: 'mmHg', digits: 0 },
  { label: 'EtCO2', keys: ['EtCO2', 'EtCO2_proxy'], unit: 'mmHg', digits: 0 },
  { label: 'SaO2', keys: ['SpO2_percent', 'SaO2'], unit: '%', digits: 0, percentFraction: true },
  { label: 'HCO3-', keys: ['HCO3_mmol_L', 'HCO3'], unit: 'mmol/L', digits: 1 },
  { label: 'BE', keys: ['BE_mmol_L', 'base_excess_mmol_L'], unit: 'mmol/L', digits: 1 },
  { label: 'Lattato', keys: ['lactate'], unit: 'mmol/L', digits: 1 },
  { label: 'Hb', keys: ['Hb'], unit: 'g/dL', digits: 1 },
  { label: 'Na+', keys: ['Na_mmol_L', 'Na'], unit: 'mmol/L', digits: 0 },
  { label: 'K+', keys: ['K_mmol_L', 'K'], unit: 'mmol/L', digits: 1 },
  { label: 'Glucosio', keys: ['glucose_mmol_L', 'glucose'], unit: 'mmol/L', digits: 1 },
];

function isEmogasOpen() {
  const overlay = $('apparatusOverlay');
  const panel = $('emogasPanel');
  return !!(overlay && !overlay.hidden && panel && !panel.hidden);
}


function labsStripWindowItems() {
  const visible = 4;
  const items = [];
  for (let i = 0; i < visible; i += 1) {
    items.push(LABS_STRIP_ITEMS[(labsStripRotationIndex + i) % LABS_STRIP_ITEMS.length]);
  }
  return items;
}

function renderLabsStrip(st=null, source='cache') {
  const wrap = $('labsStripItems');
  if (!wrap) return;
  const data = st || Object.assign({}, lastBedsideState, lastExtendedMonitorState);
  if (!data || Object.keys(data).length === 0) {
    wrap.innerHTML = '<span class="muted">Carica una sessione per vedere i parametri.</span>';
    return;
  }
  wrap.innerHTML = labsStripWindowItems().map(item => {
    const raw = extendedStateValue(data, item);
    const missing = raw === null || raw === undefined;
    return `<div class="labs-strip-item ${missing ? 'missing' : ''}" title="${source}"><span>${item.label}</span><strong>${formatExtendedValue(data, item)}</strong></div>`;
  }).join('');
}

function rotateLabsStrip(nowMs=performance.now()) {
  if (!labsStripLastRotateMs || nowMs - labsStripLastRotateMs >= 8000) {
    labsStripRotationIndex = (labsStripRotationIndex + 4) % LABS_STRIP_ITEMS.length;
    labsStripLastRotateMs = nowMs;
    renderLabsStrip(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'rotating cache');
  }
}

function requestLabsStripSnapshotSoon() {
  if (!sessionId) return;
  const now = performance.now();
  if (fullProfileFetchInFlight || (now - labsStripLastFullRequestMs) < 8000) return;
  labsStripLastFullRequestMs = now;
  fullProfileFetchInFlight = true;
  refreshExtendedMonitor()
    .catch(e => console.error(e))
    .finally(() => { fullProfileFetchInFlight = false; });
}
function renderEmogasPanel(st=null, source='bedside') {
  const grid = $('emogasGrid');
  const meta = $('emogasMeta');
  if (!grid) return;
  const data = st || Object.assign({}, lastBedsideState, lastExtendedMonitorState);
  if (!data || Object.keys(data).length === 0) {
    grid.innerHTML = '<div class="muted">Nessuna sessione attiva.</div>';
    if (meta) meta.textContent = 'Carica una sessione e premi Aggiorna emogas.';
    return;
  }
  grid.innerHTML = EMOGAS_ITEMS.map(item => {
    const raw = extendedStateValue(data, item);
    const missing = raw === null || raw === undefined;
    return `<div class="extended-param emogas-param ${missing ? 'missing' : ''}"><span>${item.label}</span><strong>${formatExtendedValue(data, item)}</strong></div>`;
  }).join('');
  if (meta) {
    const t = data.time_s ?? data.t;
    meta.textContent = `Emogas: t = ${fmt(t, 1)} s - source: ${source} - ${new Date().toLocaleTimeString()}`;
  }
}
function renderExtendedMonitor(st=null, source='bedside') {
  const grid = $('extendedMonitorGrid');
  const meta = $('extendedMonitorMeta');
  if (!grid) return;
  const data = st || Object.assign({}, lastBedsideState, lastExtendedMonitorState);
  if (!data || Object.keys(data).length === 0) {
    grid.innerHTML = '<div class="muted">Nessuna sessione attiva.</div>';
    if (meta) meta.textContent = 'Carica una sessione per visualizzare il monitor esteso.';
    return;
  }
  grid.innerHTML = EXTENDED_MONITOR_GROUPS.map(group => {
    const rows = group.items.map(item => {
      const raw = extendedStateValue(data, item);
      const missing = raw === null || raw === undefined;
      return `<div class="extended-param ${missing ? 'missing' : ''}"><span>${item.label}</span><strong>${formatExtendedValue(data, item)}</strong></div>`;
    }).join('');
    const openAttr = group.open ? ' open' : '';
    return `<details class="extended-card"${openAttr}><summary><h3>${group.title}</h3><small>${group.items.length} parametri</small></summary><div class="extended-param-grid">${rows}</div></details>`;
  }).join('');
  if (meta) {
    const t = data.time_s ?? data.t;
    meta.textContent = `Snapshot manuale: t = ${fmt(t, 1)} s · source: ${source} · ${new Date().toLocaleTimeString()}`;
  }
}
function renderBolusControls() {
  const grid = $('bolusDoseGrid');
  if (!grid || grid.dataset.ready === '1') return;
  grid.innerHTML = BOLUS_DRUG_DEFS.map(def => `<div class="bolus-dose-card" data-bolus-card="${def.id}">
    <label>${def.label} <small>${def.unit}</small><input id="${def.id}" type="number" min="0" step="${def.step}" value="${def.defaultValue}" /></label>
    <button type="button" data-bolus="${def.id}">Bolo</button>
    <small>${def.nativeBolus ? 'bolo nativo' : `${def.durationSec}s -> ${def.rateUnit}`}</small>
    <span class="bolus-card-status muted" data-bolus-status="${def.id}">pronto</span>
  </div>`).join('');
  grid.querySelectorAll('button[data-bolus]').forEach(btn => {
    btn.onclick = () => administerBolus(btn.dataset.bolus).catch(reportUiError);
  });
  grid.dataset.ready = '1';
  updateBolusCardStates();
}
function setBolusStatus(text, isActive=false) {
  const el = $('bolusStatus');
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('bolus-active', isActive);
}
function bolusWallDelayMs(def) {
  const speed = SESSION_UI_STATE.running ? Number(SESSION_UI_STATE.speed || readSessionSpeed()) : 1;
  return Math.max(500, (Number(def.durationSec || 1) * 1000) / Math.max(speed, 0.1));
}
function updateBolusCardStates() {
  BOLUS_DRUG_DEFS.forEach(def => {
    const card = document.querySelector(`[data-bolus-card="${def.id}"]`);
    const status = document.querySelector(`[data-bolus-status="${def.id}"]`);
    const btn = document.querySelector(`button[data-bolus="${def.id}"]`);
    const record = activeBolusRecords.get(def.action);
    const active = !!record && record.state === 'active';
    if (card) {
      card.classList.toggle('bolus-active-card', active);
      card.classList.toggle('bolus-confirmed-card', !!record && record.state === 'completed');
    }
    if (status) status.textContent = record ? record.text : 'pronto';
    if (btn) {
      btn.classList.toggle('button-active', active);
      btn.classList.toggle('button-confirmed', !!record && record.state === 'completed');
      btn.dataset.stateLabel = active ? 'active' : (!!record && record.state === 'completed' ? 'done' : '');
    }
  });
}
async function administerBolus(id) {
  const def = BOLUS_DRUG_DEFS.find(x => x.id === id);
  if (!def || !sessionId) return;
  const input = $(def.id);
  const dose = Number(input?.value || 0);
  if (!Number.isFinite(dose) || dose <= 0) {
    setBolusStatus('Inserisci una dose bolo maggiore di zero.');
    return;
  }
  if (activeBolusTimers.has(def.action)) {
    clearTimeout(activeBolusTimers.get(def.action));
    activeBolusTimers.delete(def.action);
  }
  if (def.nativeBolus) {
    await sendAction(def.action, { value: dose }, { silent: true });
    activeBolusRecords.set(def.action, { state: 'completed', text: `${dose} ${def.unit} inviato` });
    updateBolusCardStates();
    setBolusStatus(`${def.label}: bolo ${dose} ${def.unit} inviato.`, false);
    logEvent('Bolus', `${def.label} ${dose} ${def.unit}`);
    setTimeout(() => {
      const rec = activeBolusRecords.get(def.action);
      if (rec?.state === 'completed') {
        activeBolusRecords.delete(def.action);
        updateBolusCardStates();
      }
    }, 2200);
    return;
  }
  const rate = def.rateFactor(dose);
  const wallDelayMs = bolusWallDelayMs(def);
  await sendAction(def.action, { value: rate }, { silent: true });
  activeBolusRecords.set(def.action, { state: 'active', text: `${dose} ${def.unit} -> ${rate.toFixed(2)} ${def.rateUnit} (${def.durationSec}s sim)` });
  updateBolusCardStates();
  setBolusStatus(`${def.label}: ${dose} ${def.unit} come ${rate.toFixed(2)} ${def.rateUnit} per ${def.durationSec}s simulati.`, true);
  logEvent('Bolus start', `${def.label} ${dose} ${def.unit} (${def.durationSec}s sim)`);
  const timer = setTimeout(async () => {
    activeBolusTimers.delete(def.action);
    if (!sessionId) return;
    try {
      await sendAction(def.action, { value: 0 }, { silent: true });
      activeBolusRecords.set(def.action, { state: 'completed', text: 'completato, infusione azzerata' });
      updateBolusCardStates();
      setBolusStatus(`${def.label}: bolo completato e infusione equivalente azzerata.`, false);
      logEvent('Bolus complete', def.label);
      setTimeout(() => {
        const rec = activeBolusRecords.get(def.action);
        if (rec?.state === 'completed') {
          activeBolusRecords.delete(def.action);
          updateBolusCardStates();
        }
      }, 2200);
    } catch (e) {
      setBolusStatus(`${def.label}: reset bolo non riuscito (${e.message}).`, false);
    }
  }, wallDelayMs);
  activeBolusTimers.set(def.action, timer);
}
function clearBolusStatus() {
  setBolusStatus('Nessun bolo attivo.', false);
  activeBolusRecords.clear();
  updateBolusCardStates();
}
function auditFirstValue(st, keys=[]) {
  for (const key of keys) {
    const value = st?.[key];
    if (value !== undefined && value !== null) return { key, value };
  }
  return null;
}
function formatAuditValue(value, digits=2) {
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  if (value === undefined || value === null || value === '') return '--';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= 100) return n.toFixed(1);
  if (Math.abs(n) >= 10) return n.toFixed(2);
  return n.toFixed(digits);
}
function auditMetricList(st, keys=[]) {
  const rows = [];
  for (const key of keys || []) {
    if (st?.[key] === undefined || st?.[key] === null) continue;
    rows.push(`<span><em>${key}</em><b>${formatAuditValue(st[key])}</b></span>`);
  }
  return rows.join('');
}
function renderDrugAudit(st=null, source='no snapshot') {
  const grid = $('drugAuditGrid');
  const meta = $('drugAuditMeta');
  if (!grid) return;
  if (!st) {
    grid.innerHTML = '<div class="drug-audit-empty">Carica una sessione e premi Aggiorna audit.</div>';
    if (meta) meta.textContent = 'Nessun audit eseguito.';
    return;
  }
  const t = st.time_s ?? st.t ?? 0;
  if (meta) meta.textContent = `Audit ${source} a t=${fmt(t, 1)} s.`;
  grid.innerHTML = DRUG_AUDIT_GROUPS.map(drug => {
    const dose = auditFirstValue(st, [drug.dose, drug.alternateDose].filter(Boolean));
    const concentration = auditFirstValue(st, drug.concentration || []);
    const effects = auditMetricList(st, drug.effects || []);
    const risks = auditMetricList(st, drug.risks || []);
    const active = Number(dose?.value || 0) > 0 || Number(concentration?.value || 0) > 0;
    return `<article class="drug-audit-card ${active ? 'active' : ''}">
      <header><h4>${drug.name}</h4><small>${active ? 'active / residual' : 'idle'}</small></header>
      <div class="drug-audit-main">
        <span>Dose</span><strong>${dose ? formatAuditValue(dose.value) : '--'} ${drug.unit || ''}</strong>
        <span>Concentrazione</span><strong>${concentration ? `${formatAuditValue(concentration.value)} <small>${concentration.key}</small>` : '--'}</strong>
      </div>
      ${effects ? `<div class="drug-audit-metrics"><label>PD / audit</label>${effects}</div>` : ''}
      ${risks ? `<div class="drug-audit-metrics risk"><label>Rischi</label>${risks}</div>` : ''}
    </article>`;
  }).join('');
}
async function refreshDrugAudit() {
  if (!sessionId) {
    renderDrugAudit(null, 'no session');
    return;
  }
  const data = await api(`/session/${sessionId}/state?profile=full`);
  const full = data.state || {};
  lastExtendedMonitorState = full;
  renderDrugAudit(Object.assign({}, lastBedsideState, full), 'full profile');
}
function rawBusValueToString(value) {
  if (value === undefined || value === null) return '--';
  if (typeof value === 'number') return Number.isFinite(value) ? formatAuditValue(value, 3) : String(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') {
    try { return JSON.stringify(value); } catch (e) { return String(value); }
  }
  return String(value);
}
function renderRawBusInspector(st=null) {
  const box = $('rawBusInspector');
  const table = $('rawBusTable');
  const meta = $('rawBusMeta');
  if (!box || !table) return;
  const data = st || lastExtendedMonitorState || {};
  const keys = Object.keys(data).sort((a, b) => a.localeCompare(b));
  const query = ($('rawBusFilter')?.value || '').trim().toLowerCase();
  const filtered = query ? keys.filter(k => k.toLowerCase().includes(query) || rawBusValueToString(data[k]).toLowerCase().includes(query)) : keys;
  if (meta) meta.textContent = keys.length ? `${filtered.length}/${keys.length} parametri nello snapshot full.` : 'Nessuno snapshot full disponibile.';
  table.innerHTML = filtered.length ? filtered.map(key => `<div class="raw-bus-row"><code>${key}</code><span>${rawBusValueToString(data[key])}</span></div>`).join('') : '<div class="raw-bus-empty">Nessun parametro corrisponde al filtro.</div>';
}
function toggleRawBusInspector() {
  const box = $('rawBusInspector');
  if (!box) return;
  box.hidden = !box.hidden;
  if (!box.hidden) renderRawBusInspector(lastExtendedMonitorState);
}
async function refreshExtendedMonitor() {
  if (!sessionId) {
    renderExtendedMonitor(null, 'no session');
    renderEmogasPanel(null, 'no session');
    renderLabsStrip(null, 'no session');
    return;
  }
  try {
    const data = await api(`/session/${sessionId}/state?profile=full`);
    lastExtendedMonitorState = data.state || {};
    pushExtendedSnapshot(Object.assign({}, lastBedsideState, lastExtendedMonitorState));
    renderExtendedMonitor(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'full profile');
    renderEmogasPanel(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'full profile');
    renderLabsStrip(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'full profile');
    renderRawBusInspector(lastExtendedMonitorState);
  } catch (e) {
    console.error(e);
    renderExtendedMonitor(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'bedside fallback');
    renderEmogasPanel(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'bedside fallback');
    renderLabsStrip(Object.assign({}, lastBedsideState, lastExtendedMonitorState), 'bedside fallback');
  }
}
function isExtendedMonitorOpen() {
  const overlay = $('apparatusOverlay');
  const panel = $('extendedMonitorPanel');
  return !!(overlay && !overlay.hidden && panel && !panel.hidden);
}
function shouldRefreshFullProfilePanels() {
  return isExtendedMonitorOpen() || isEmogasOpen();
}
function startExtendedMonitorSnapshot() {
  if (!shouldRefreshFullProfilePanels()) return;
  refreshExtendedMonitor().catch(e => console.error(e));
  if (extendedMonitorSnapshotTimer) clearInterval(extendedMonitorSnapshotTimer);
  extendedMonitorSnapshotTimer = setInterval(() => {
    if (!shouldRefreshFullProfilePanels()) {
      stopExtendedMonitorSnapshot();
      return;
    }
    refreshExtendedMonitor().catch(e => console.error(e));
  }, 2500);
}
function stopExtendedMonitorSnapshot() {
  if (extendedMonitorSnapshotTimer) {
    clearInterval(extendedMonitorSnapshotTimer);
    extendedMonitorSnapshotTimer = null;
  }
}
function requestFullProfileSnapshotSoon() {
  if (!sessionId || !shouldRefreshFullProfilePanels()) return;
  const now = performance.now();
  if (fullProfileFetchInFlight || (now - lastFullProfileFetchMs) < 2000) return;
  fullProfileFetchInFlight = true;
  lastFullProfileFetchMs = now;
  refreshExtendedMonitor()
    .catch(e => console.error(e))
    .finally(() => { fullProfileFetchInFlight = false; });
}
function logEvent(label, detail='') {
  const clock = $('simClock');
  const t = clock ? clock.textContent.replace('t = ', '') : 't --';
  const html = `<b>${t}</b> ${label}<br><span>${detail}</span>`;
  showActionFeedback(label, detail, 'confirmed');
  const wrap = $('eventLog');
  if (wrap) {
    const div = document.createElement('div');
    div.className = 'event';
    div.innerHTML = html;
    wrap.prepend(div);
  }
  const mini = $('miniEventLog');
  if (mini) {
    if (mini.classList.contains('muted')) { mini.classList.remove('muted'); mini.innerHTML = ''; }
    const div = document.createElement('div');
    div.className = 'mini-event';
    div.innerHTML = html;
    mini.prepend(div);
    while (mini.children.length > 5) mini.removeChild(mini.lastChild);
  }
}

async function loadAuthoringTemplates() {
  const select = $('authorTemplateSelect');
  if (!select) return;
  const data = await api('/authoring/templates');
  authoringTemplates = data.templates || [];
  select.innerHTML = authoringTemplates.map(t => `<option value="${t.id}">${t.label || t.id}</option>`).join('');
}
function authorQuestions() {
  const raw = ($('authorQuestionsInput')?.value || '').split('\n').map(x => x.trim()).filter(Boolean);
  return raw.length ? raw : undefined;
}
function authorDraftPayload() {
  const numOrNull = (id) => {
    const el = $(id); const n = Number(el && el.value);
    return Number.isFinite(n) && String(el.value).trim() !== '' ? n : null;
  };
  return {
    template_id: $('authorTemplateSelect')?.value || 'airway_deterioration',
    title: $('authorTitleInput')?.value || 'Authored training scenario',
    description: $('authorDescriptionInput')?.value || 'Educational authored scenario. Not for clinical use.',
    diagnosis: $('authorDiagnosisInput')?.value || null,
    age_y: numOrNull('authorAgeInput'),
    weight_kg: numOrNull('authorWeightInput'),
    duration_s: numOrNull('authorDurationInput'),
    severity: $('authorSeveritySelect')?.value || 'moderate',
    debrief_questions: authorQuestions(),
  };
}
function setAuthoringStatus(data) {
  const el = $('authoringStatus');
  if (!el) return;
  const validation = data.validation || {};
  const warnings = data.warnings || validation.warnings || [];
  const errors = validation.errors || [];
  el.classList.remove('muted');
  el.innerHTML = `<b>${validation.status || data.status || 'draft'}</b>` +
    (data.scenario_id ? ` · ${data.scenario_id}` : '') +
    (data.path ? ` · ${data.path}` : '') +
    (warnings.length ? `<br><span>Warnings: ${warnings.join('; ')}</span>` : '') +
    (errors.length ? `<br><span>Errors: ${errors.join('; ')}</span>` : '');
}
async function draftScenario() {
  const data = await api('/authoring/draft', { method: 'POST', body: JSON.stringify(authorDraftPayload()) });
  $('authorYamlText').value = data.yaml_text || '';
  if ($('authorFilenameInput') && data.suggested_filename) $('authorFilenameInput').value = data.suggested_filename;
  setAuthoringStatus(data);
  logEvent('Scenario drafted', data.scenario_id || 'authoring');
}
async function validateAuthoredScenario() {
  const yamlText = $('authorYamlText')?.value || '';
  const data = await api('/authoring/validate', { method: 'POST', body: JSON.stringify({ yaml_text: yamlText }) });
  setAuthoringStatus(data);
  logEvent('Scenario validated', data.validation?.status || 'validation');
}
async function saveAuthoredScenario() {
  const yamlText = $('authorYamlText')?.value || '';
  const filename = ($('authorFilenameInput')?.value || '').trim() || null;
  const data = await api('/authoring/save', { method: 'POST', body: JSON.stringify({ yaml_text: yamlText, filename, overwrite: true, publish_to_scenarios: true }) });
  authoringLastSavedScenario = data.scenario_id;
  setAuthoringStatus(data);
  await loadScenarios();
  if ($('scenarioSelect') && data.scenario_id) $('scenarioSelect').value = data.scenario_id;
  logEvent('Scenario saved', data.path || data.scenario_id);
}
async function loadAuthoredScenario() {
  if (!authoringLastSavedScenario) {
    const filename = ($('authorFilenameInput')?.value || '').replace(/\.yaml$/, '');
    authoringLastSavedScenario = filename || null;
  }
  if (!authoringLastSavedScenario) { alert('Save an authored scenario first.'); return; }
  if ($('scenarioSelect')) $('scenarioSelect').value = authoringLastSavedScenario;
  await loadSession();
  closeApparatus();
}


function scenarioMetaFor(idOrName) {
  if (!idOrName) return null;
  return scenarioCatalogMap.get(idOrName) || scenarioCatalogMap.get(String(idOrName).replace(/\.yaml$/, '')) || null;
}
function scenarioPatientLine(patient={}) {
  const bits = [];
  if (patient.age_y !== undefined) bits.push(`${fmt(patient.age_y, 1)} y`);
  if (patient.weight_kg !== undefined) bits.push(`${fmt(patient.weight_kg, 1)} kg`);
  if (patient.sex) bits.push(patient.sex);
  if (patient.diagnosis) bits.push(patient.diagnosis);
  return bits.join(' · ') || '--';
}
function updateScenarioInfoCard(metaOrId=null, envelope={}) {
  const card = $('scenarioInfoCard');
  if (!card) return;
  const id = metaOrId && typeof metaOrId === 'object' ? (metaOrId.id || currentScenario) : (metaOrId || currentScenario);
  const meta = (metaOrId && typeof metaOrId === 'object' ? metaOrId : scenarioMetaFor(id)) || {};
  const title = meta.name || envelope.scenario || id || 'No scenario loaded';
  const patient = meta.patient || {};
  const duration = meta.duration_s ?? envelope.duration_s;
  const desc = (meta.description || '').trim();
  const objectives = meta.educational_objectives || meta.objectives || meta.outputs || [];
  const objText = Array.isArray(objectives) ? objectives.slice(0, 8).join(', ') : String(objectives || '');
  const html = `
    <div class="scenario-info-main">
      <b>${title}</b>
      <span>${scenarioPatientLine(patient)}</span>
      <span>Durata: ${Number.isFinite(Number(duration)) ? fmt(duration, 0) + ' s' : '--'}</span>
    </div>
    <div class="scenario-info-description">${desc || 'Nessun brief disponibile nel file scenario.'}</div>
    ${objText ? `<div class="scenario-info-objectives"><span>Output/obiettivi:</span> ${objText}</div>` : ''}
  `;
  card.innerHTML = html;
}
function toggleScenarioInfoCard(force=null) {
  const card = $('scenarioInfoCard');
  const btn = $('scenarioInfoBtn');
  if (!card) return;
  const shouldHide = force === null ? !card.hidden : !force;
  card.hidden = shouldHide;
  if (!shouldHide) updateScenarioInfoCard(currentScenario);
  if (btn) btn.setAttribute('aria-expanded', String(!card.hidden));
}

async function loadScenarios() {
  const data = await api('/scenarios');
  const select = $('scenarioSelect');
  select.innerHTML = '';
  const preferred = ['airway_rsi_hypoxic_child_v1_24', 'airway_failed_intubation_cannot_oxygenate_v1_25', 'airway_niv_failure_to_intubation_v1_25', 'healthy_child_20kg'];
  const scenarios = data.scenarios.filter(s => !s.error);
  scenarioCatalogMap = new Map(scenarios.map(s => [s.id, s]));
  scenarios.sort((a,b) => {
    const ia = preferred.indexOf(a.id), ib = preferred.indexOf(b.id);
    if (ia >= 0 || ib >= 0) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    return a.id.localeCompare(b.id);
  });
  for (const s of scenarios) {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.id} (${Math.round(s.duration_s)} s)`;
    select.appendChild(opt);
  }
  if (select.value) {
    currentScenario = select.value;
    if ($('currentScenarioLabel')) $('currentScenarioLabel').textContent = select.value;
    updateScenarioInfoCard(select.value);
  }
}
async function loadEmergencyScenarios() {
  const data = await api('/training/scenarios');
  const select = $('emergencyScenarioSelect');
  if (!select) return;
  select.innerHTML = '';
  emergencyScenarioMap = new Map();
  const scenarios = (data.scenarios || []).sort((a,b) => `${a.category}:${a.id}`.localeCompare(`${b.category}:${b.id}`));
  for (const s of scenarios) {
    emergencyScenarioMap.set(s.id, s);
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.category} · ${s.id}`;
    select.appendChild(opt);
  }
  updateEmergencyScenarioDetails();
}
async function loadInstructorPresets() {
  const wrap = $('instructorPresetButtons');
  if (!wrap) return;
  const data = await api('/instructor/presets');
  instructorPresets = (data.presets || []).filter(p => p.available !== false);
  wrap.innerHTML = instructorPresets.map(p => `<button class="preset-btn ${p.category}" data-preset="${p.id}" title="${p.teaching_use || ''}">${p.label}</button>`).join('');
  wrap.querySelectorAll('button[data-preset]').forEach(btn => {
    btn.onclick = () => applyInstructorPreset(btn.dataset.preset).catch(reportUiError);
  });
}
async function applyInstructorPreset(id) {
  if (!sessionId) return;
  const preset = instructorPresets.find(p => p.id === id);
  if (!preset) return;
  await sendAction(preset.action, preset.payload || {});
  await addInstructorNote(`Preset: ${preset.label}`, 'preset', false, true);
}
async function addInstructorNote(text=null, kind='note', pinned=false, silent=false) {
  if (!sessionId) return;
  const bodyText = text ?? $('instructorNoteText').value;
  const data = await api(`/session/${sessionId}/instructor/note`, { method: 'POST', body: JSON.stringify({ text: bodyText, kind, pinned }) });
  if (!silent && $('instructorNoteText')) $('instructorNoteText').value = '';
  appendInstructorNote(data.note);
  if (!silent) logEvent('Instructor note', data.note.text);
}
function appendInstructorNote(note) {
  const wrap = $('instructorNotes');
  if (!wrap || !note) return;
  if (wrap.classList.contains('muted')) { wrap.classList.remove('muted'); wrap.innerHTML = ''; }
  const div = document.createElement('div');
  div.className = 'note-card';
  div.innerHTML = `<b>t=${fmt(note.t,1)}s · ${note.kind}${note.pinned ? ' · pinned' : ''}</b><small>${note.text}</small>`;
  wrap.prepend(div);
}
async function setDiagnosisVisibility(hidden) {
  diagnosisHidden = !!hidden;
  $('diagnosisVisibility').textContent = diagnosisHidden ? 'hidden' : 'visible';
  if (sessionId) {
    await api(`/session/${sessionId}/instructor/visibility`, { method: 'POST', body: JSON.stringify({ hide_diagnosis: diagnosisHidden }) });
  }
  updateEmergencyScenarioDetails();
  logEvent('Instructor visibility', diagnosisHidden ? 'diagnosis hidden' : 'diagnosis visible');
}
async function generateInstructorReport() {
  if (!sessionId) return;
  const data = await api(`/session/${sessionId}/instructor/report`);
  const r = data.report || {};
  const s = r.summary || {};
  const flags = (r.triggered_flags || []).map(f => f.flag).join(', ') || 'none';
  const wrap = $('instructorNotes');
  if (wrap) {
    wrap.classList.remove('muted');
    wrap.innerHTML = `<div class="note-card"><b>Instructor report</b><small>Notes: ${s.notes ?? 0} · flags: ${s.triggered_flags ?? 0} (${flags}) · SpO₂ nadir: ${fmt((s.SpO2_nadir || 0)*100,0)}% · PaCO₂ peak: ${fmt(s.PaCO2_peak,0)}</small></div>` + wrap.innerHTML;
  }
  logEvent('Instructor report', `${s.triggered_flags ?? 0} flags, ${s.notes ?? 0} notes`);
}

function openApparatus(panelId='sessionPanel', scrollTarget=null) {
  const overlay = $('apparatusOverlay');
  if (!overlay) return;
  overlay.hidden = false;
  document.body.classList.add('modal-open');
  setApparatusPanel(panelId, scrollTarget);
}
function closeApparatus() {
  const overlay = $('apparatusOverlay');
  if (!overlay) return;
  overlay.hidden = true;
  document.body.classList.remove('modal-open');
  updateDockButtonStates(null);
  stopExtendedMonitorSnapshot();
}
function quickMonitorButtonTarget(btn) {
  if (!btn) return null;
  if (btn.id === 'quickEmogasBtn') return { panel: 'emogasPanel' };
  if (btn.id === 'quickBolusBtn') return { panel: 'drugPanel', scroll: 'bolusPanel' };
  if (btn.id === 'quickExtendedMonitorBtn') return { panel: 'extendedMonitorPanel' };
  return null;
}
function updateDockButtonStates(panelId=null) {
  document.querySelectorAll('.dock-card[data-open-panel]').forEach(btn => {
    const active = !!panelId && btn.dataset.openPanel === panelId;
    btn.classList.toggle('dock-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  document.querySelectorAll('.monitor-header-actions button[id^="quick"]').forEach(btn => {
    const target = quickMonitorButtonTarget(btn);
    const active = !!target && !!panelId && target.panel === panelId;
    btn.classList.toggle('quick-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    if (active) btn.dataset.stateLabel = 'open';
    else delete btn.dataset.stateLabel;
  });
}
function setApparatusPanel(panelId, scrollTarget=null) {
  document.querySelectorAll('.apparatus-panel').forEach(panel => {
    panel.hidden = panel.id !== panelId;
  });
  document.querySelectorAll('[data-panel-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.panelTab === panelId);
  });
  const panel = $(panelId);
  const title = $('apparatusTitle');
  if (title && panel) title.textContent = panel.dataset.panelTitle || panel.querySelector('h2')?.textContent || 'Apparatus';
  updateDockButtonStates(panelId);
  if (panelId === 'extendedMonitorPanel' || panelId === 'emogasPanel') startExtendedMonitorSnapshot();
  else stopExtendedMonitorSnapshot();
  if (panelId === 'drugPanel') {
    renderBolusControls();
    updateBolusCardStates();
    renderDrugAudit(lastExtendedMonitorState && Object.keys(lastExtendedMonitorState).length ? Object.assign({}, lastBedsideState, lastExtendedMonitorState) : null, 'cached snapshot');
  }
  if (scrollTarget) {
    requestAnimationFrame(() => {
      const target = $(scrollTarget);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      target.classList.add('panel-focus-pulse');
      setTimeout(() => target.classList.remove('panel-focus-pulse'), 1300);
    });
  }
}
function setConsoleMode(mode='instructor') {
  document.body.classList.toggle('learner-mode', mode === 'learner');
  logEvent('Console view', mode === 'learner' ? 'learner clean view' : 'instructor control view');
}
function setupApparatusNavigation() {
  document.querySelectorAll('[data-open-panel]').forEach(btn => {
    btn.onclick = () => openApparatus(btn.dataset.openPanel, btn.dataset.scrollTarget || null);
  });
  document.querySelectorAll('[data-panel-scroll]').forEach(btn => {
    btn.onclick = () => {
      const target = $(btn.dataset.panelScroll);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      target.classList.add('panel-focus-pulse');
      setTimeout(() => target.classList.remove('panel-focus-pulse'), 1300);
    };
  });
  document.querySelectorAll('[data-panel-tab]').forEach(btn => {
    btn.onclick = () => setApparatusPanel(btn.dataset.panelTab);
  });
  if ($('closeApparatusBtn')) $('closeApparatusBtn').onclick = closeApparatus;
  const overlay = $('apparatusOverlay');
  if (overlay) {
    overlay.addEventListener('click', (ev) => { if (ev.target === overlay) closeApparatus(); });
  }
  const chartOverlay = $('popupChartOverlay');
  if (chartOverlay) chartOverlay.addEventListener('click', (ev) => { if (ev.target === chartOverlay) closePopupChart(); });
  window.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') { closePopupChart(); closeApparatus(); } });
  if ($('learnerViewBtn')) $('learnerViewBtn').onclick = () => setConsoleMode('learner');
  if ($('instructorViewBtn')) $('instructorViewBtn').onclick = () => setConsoleMode('instructor');
}

function updateEmergencyScenarioDetails() {
  const select = $('emergencyScenarioSelect');
  if (!select) return;
  const meta = emergencyScenarioMap.get(select.value);
  if (diagnosisHidden) {
    $('trainingCategory').textContent = 'hidden';
    $('trainingFocus').textContent = 'hidden for learner';
    $('trainingQuestions').innerHTML = '<div class="question">Instructor-only details hidden. Use debrief after the scenario.</div>';
    return;
  }
  $('trainingCategory').textContent = meta ? meta.category : '--';
  $('trainingFocus').textContent = meta && meta.focus ? meta.focus.join(', ') : '--';
  const q = (meta && meta.debrief_questions || []).slice(0, 4);
  $('trainingQuestions').innerHTML = q.length ? q.map(x => `<div class="question">${x}</div>`).join('') : 'No debrief questions configured.';
}
async function loadEmergencySession() {
  const select = $('emergencyScenarioSelect');
  if (!select || !select.value) return;
  const meta = emergencyScenarioMap.get(select.value);
  if (!meta) return;
  $('scenarioSelect').value = meta.id;
  disconnectStreams();
  const dt = Number($('dtInput').value || 0.2);
  const data = await api('/session/load', { method: 'POST', body: JSON.stringify({ scenario: meta.id, dt }) });
  sessionId = data.session_id;
  currentScenario = meta.id;
  $('sessionMeta').textContent = `${data.scenario} · ${sessionId.slice(0,8)} · emergency ${meta.category}`;
  if ($('currentScenarioLabel')) $('currentScenarioLabel').textContent = data.scenario;
  if ($('scenarioMirror')) $('scenarioMirror').value = data.scenario;
  updateScenarioInfoCard(currentScenario || data.scenario, data);
  SESSION_UI_STATE.loaded = true;
  SESSION_UI_STATE.running = false;
  SESSION_UI_STATE.simTimeS = Number(data.time_s ?? data.state?.time_s ?? data.state?.t ?? 0);
  SESSION_UI_STATE.speed = readSessionSpeed();
  resetWallClock();
  enableSessionButtons();
  updateBedside(data.state, data);
  connectStreams();
  logEvent('Emergency loaded', `${meta.category}: ${meta.id}`);
}
function metricLine(label, value, suffix='', digits=1) {
  const n = Number(value);
  const v = Number.isFinite(n) ? n.toFixed(digits) : '--';
  return `<div class="kv"><span>${label}</span><strong>${v}${suffix}</strong></div>`;
}
async function generateDebrief() {
  if (!sessionId) return;
  const data = await api(`/session/${sessionId}/debrief`);
  const d = data.debrief || {};
  const m = d.metrics || {};
  $('debriefSummary').innerHTML = [
    metricLine('SpO₂ nadir', (m.SpO2_nadir || 0) * 100, '%', 0),
    metricLine('Time SpO₂ < 90%', m.time_below_SpO2_90_s, ' s', 0),
    metricLine('Time SpO₂ < 80%', m.time_below_SpO2_80_s, ' s', 0),
    metricLine('PaCO₂ peak', m.PaCO2_peak, ' mmHg', 0),
    metricLine('MAP min', m.MAP_min, ' mmHg', 0),
    metricLine('Failed attempts', m.failed_intubation_count, '', 0),
    metricLine('Rescue ventilation', m.first_rescue_ventilation_time_s, ' s', 0),
    metricLine('Intubation success', m.intubation_success_time_s, ' s', 0),
  ].join('');
  const flags = (d.flags || []).filter(f => f.triggered);
  $('debriefFlags').innerHTML = flags.length ? `<h3>Triggered flags</h3>${flags.map(f => `<div class="flag">${f.flag}<span>${JSON.stringify(f.value)}</span></div>`).join('')}` : '<h3>Triggered flags</h3><div class="muted">None.</div>';
  const th = (d.threshold_events || []).filter(x => x.crossed).slice(0, 10);
  $('debriefThresholds').innerHTML = th.length ? `<h3>Threshold events</h3>${th.map(x => `<div class="threshold">${x.variable} ${x.direction} ${x.threshold}: first ${fmt(x.first_time_s,0)}s · duration ${fmt(x.duration_s,0)}s</div>`).join('')}` : '<h3>Threshold events</h3><div class="muted">None.</div>';
  logEvent('Debrief generated', `${flags.length} flags triggered`);
}
async function loadSession() {
  disconnectStreams();
  const scenario = $('scenarioSelect').value;
  const scenarioMeta = scenarioCatalogMap.get(scenario);
  const scenarioRef = scenarioMeta?.file || scenarioMeta?.path || scenario;
  const dt = Number($('dtInput').value || 0.2);
  const data = await api('/session/load', { method: 'POST', body: JSON.stringify({ scenario: scenarioRef, dt }) });
  sessionId = data.session_id;
  currentScenario = scenario;
  $('sessionMeta').textContent = `${data.scenario} · ${sessionId.slice(0,8)} · duration ${Math.round(data.duration_s)} s`;
  if ($('currentScenarioLabel')) $('currentScenarioLabel').textContent = data.scenario;
  if ($('scenarioMirror')) $('scenarioMirror').value = data.scenario;
  updateScenarioInfoCard(currentScenario || data.scenario, data);
  SESSION_UI_STATE.loaded = true;
  SESSION_UI_STATE.running = false;
  SESSION_UI_STATE.simTimeS = Number(data.time_s ?? data.state?.time_s ?? data.state?.t ?? 0);
  SESSION_UI_STATE.speed = readSessionSpeed();
  resetWallClock();
  enableSessionButtons();
  updateBedside(data.state, data);
  connectStreams();
  logEvent('Session loaded', scenario);
}
async function startSession() {
  if (!sessionId) return;
  const speed = readSessionSpeed();
  const data = await api(`/session/${sessionId}/start`, { method: 'POST', body: JSON.stringify({ speed }) });
  syncSessionTiming(data.state || {}, data);
  SESSION_UI_STATE.speed = Number(data.speed || speed);
  SESSION_UI_STATE.running = true;
  startWallClock();
  updateSessionButtonStates();
  logEvent('Started', `speed ×${fmt(SESSION_UI_STATE.speed, 1)}`);
}
async function pauseSession() {
  if (!sessionId) return;
  await api(`/session/${sessionId}/pause`, { method: 'POST' });
  SESSION_UI_STATE.running = false;
  pauseWallClock();
  updateSessionButtonStates();
  logEvent('Paused');
}
async function stepSession() {
  if (!sessionId) return;
  const data = await api(`/session/${sessionId}/step`, { method: 'POST', body: JSON.stringify({ seconds: 5 }) });
  syncSessionTiming(data.state || {}, data);
  updateBedside(data.state, data);
  markButtonMomentary('stepBtn', 'confirmed', 'stepped');
  logEvent('Manual step', '5 s');
}
async function resetSession() {
  if (!sessionId) return;
  const data = await api(`/session/${sessionId}/reset`, { method: 'POST' });
  disconnectStreams();
  sessionId = data.session_id;
  SESSION_UI_STATE.loaded = true;
  SESSION_UI_STATE.running = false;
  pauseWallClock();
  updateSessionButtonStates();
  updateBedside(data.state, data);
  connectStreams();
  if ($('eventLog')) $('eventLog').innerHTML = '';
  if ($('miniEventLog')) { $('miniEventLog').classList.add('muted'); $('miniEventLog').innerHTML = 'No events yet.'; }
  markButtonMomentary('resetBtn', 'confirmed', 'reset');
  logEvent('Reset', currentScenario || data.scenario);
}
async function sendAction(action, payload, options={}) {
  if (!sessionId) return;
  const data = await api(`/session/${sessionId}/action`, { method: 'POST', body: JSON.stringify({ action, payload }) });
  updateBedside(data.session.state, data.session);
  if (!options.silent) logEvent(action, JSON.stringify(payload));
  return data;
}

function airwayActiveEvents(st={}) {
  const active = new Set();
  const eventType = String(st.airway_event_type || st.airway_event_status || '');
  const rescueState = String(st.airway_rescue_state || '');
  const failedCount = Number(st.failed_intubation_count || 0);
  const extubationTime = Number(st.extubation_time_s);
  const isIntubated = st.intubated === true || st.airway_interface === 'ETT' || rescueState === 'secured_ETT';
  const bagMaskActive = st.bag_mask_ventilation_active === true || st.manual_ventilation_active === true || rescueState === 'rescued_BVM';

  if (failedCount > 0 || eventType === 'failed_intubation_attempt' || rescueState === 'failed_attempt') active.add('failed_intubation_attempt');
  if (bagMaskActive || eventType === 'start_bag_mask_ventilation') active.add('start_bag_mask_ventilation');
  if (isIntubated || eventType === 'perform_intubation') active.add('perform_intubation');
  const unresolvedExtubation = !isIntubated && !bagMaskActive && (
    eventType === 'accidental_extubation' ||
    rescueState === 'extubated' ||
    rescueState === 'at_risk' ||
    (Number.isFinite(extubationTime) && extubationTime >= 0 && !isIntubated)
  );
  if (unresolvedExtubation) {
    active.add('accidental_extubation');
  }
  return active;
}

function updateAirwayActionButtons(st={}) {
  const active = airwayActiveEvents(st);
  document.querySelectorAll('button[data-action="airway_event"]').forEach(btn => {
    const isActive = active.has(btn.dataset.event);
    btn.classList.toggle('action-active', isActive);
    btn.classList.remove('pending');
    btn.dataset.state = isActive ? 'active' : 'idle';
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
}
function applyVitalAlarm(vitalId, value, ruleKey) {
  const strong = $(vitalId);
  const card = strong?.closest('.vital');
  if (!card) return;
  const n = Number(value);
  card.classList.remove('alarm-warning', 'alarm-critical');
  card.removeAttribute('data-alarm-label');
  card.removeAttribute('title');
  if (!Number.isFinite(n)) return;
  const rules = VITAL_ALARM_RULES[ruleKey] || [];
  const hit = rules.find(r => r.test(n));
  if (!hit) return;
  card.classList.add(hit.level === 'critical' ? 'alarm-critical' : 'alarm-warning');
  card.dataset.alarmLabel = hit.label;
  card.title = hit.label;
}
function updateVisualAlarms(st) {
  if (!st) return;
  const spo2Raw = Number(st.SpO2_percent ?? st.SaO2);
  const spo2 = Number.isFinite(spo2Raw) ? (spo2Raw <= 1.5 ? spo2Raw * 100.0 : spo2Raw) : NaN;
  const fio2Raw = Number(st.FiO2_delivered ?? st.FiO2);
  const fio2 = Number.isFinite(fio2Raw) ? fio2Raw : NaN;
  applyVitalAlarm('vHR', st.HR, 'HR');
  applyVitalAlarm('vSpO2', spo2, 'SpO2');
  applyVitalAlarm('vMAP', st.MAP, 'MAP');
  applyVitalAlarm('vPaCO2', st.PaCO2 ?? st.EtCO2 ?? st.EtCO2_proxy, 'CO2');
  applyVitalAlarm('vPaw', st.Paw, 'Paw');
  applyVitalAlarm('vFiO2', fio2, 'FiO2');
}

function updateCardiacStatusStrip(st={}) {
  const strip = $('cardiacStatusStrip');
  if (!strip) return;
  const rhythm = String(st.cardiac_rhythm || 'sinus');
  const hasPulse = st.has_pulse !== false;
  const arrest = st.cardiac_arrest_active === true;
  const shockable = st.shockable_rhythm === true;
  const cpr = st.CPR_active === true;
  const rosc = st.ROSC === true;
  $('cardiacRhythm').textContent = rhythm;
  $('cardiacPulse').textContent = hasPulse ? 'present' : 'absent';
  $('cardiacRhythmClass').textContent = arrest ? (shockable ? 'shockable' : 'non-shockable') : (st.rhythm_category || 'pulsed');
  $('cardiacCprState').textContent = rosc ? 'ROSC' : (cpr ? `on q${fmt(st.CPR_quality, 1)}` : 'off');
  strip.classList.toggle('arrest', arrest);
  strip.classList.toggle('unstable', !arrest && rhythm !== 'sinus');
  strip.title = arrest
    ? `Cardiac arrest: ${shockable ? 'shockable rhythm' : 'non-shockable rhythm'}`
    : (rosc ? 'Return of spontaneous circulation' : 'Cardiac rhythm status');
}

function renderRcpPanel(st={}) {
  if (!$('rcpPanel')) return;
  const rhythm = String(st.cardiac_rhythm || 'sinus');
  const hasPulse = st.has_pulse !== false;
  const arrest = st.cardiac_arrest_active === true;
  const shockable = st.shockable_rhythm === true;
  const cpr = st.CPR_active === true;
  const rosc = st.ROSC === true;
  const cprQuality = st.CPR_quality ?? st.cpr_quality ?? $('cprQualityRange')?.value;
  if ($('rcpRhythm')) $('rcpRhythm').textContent = rhythm;
  if ($('rcpPulse')) $('rcpPulse').textContent = hasPulse ? 'present' : 'absent';
  if ($('rcpShockable')) $('rcpShockable').textContent = arrest ? (shockable ? 'shockable' : 'non-shockable') : (st.rhythm_category || 'pulsed');
  if ($('rcpEtco2')) $('rcpEtco2').textContent = `${fmt(st.EtCO2 ?? st.EtCO2_proxy, 0)} mmHg`;
  if ($('rcpMap')) $('rcpMap').textContent = `${fmt(st.MAP, 0)} mmHg`;
  if ($('rcpActiveState')) $('rcpActiveState').textContent = rosc ? 'ROSC' : (cpr ? `on q${fmt(cprQuality, 2)}` : 'off');
  if ($('rcpLastShock')) {
    const energy = Number(st.last_shock_energy_J || 0);
    const result = st.last_shock_result || 'none';
    $('rcpLastShock').textContent = energy > 0 ? `${fmt(energy, 0)} J · ${result}` : 'none';
  }
  if ($('rcpLastDrug')) {
    const drug = st.last_rcp_drug || 'none';
    const result = st.last_rcp_drug_result || 'none';
    $('rcpLastDrug').textContent = drug !== 'none' ? `${drug} · ${result}` : 'none';
  }
  const postRoscStatus = st.post_rosc_care_status || (rosc ? 'needed' : 'none');
  if ($('rcpPostRosc')) $('rcpPostRosc').textContent = postRoscStatus;
  if ($('rcpAcidosis')) $('rcpAcidosis').textContent = `${fmt((st.post_rosc_acidosis_burden ?? 0) * 100, 0)}%`;
  if ($('rcpRenalRisk')) $('rcpRenalRisk').textContent = `${fmt((st.renal_hypoperfusion_index ?? 0) * 100, 0)}%`;
  if ($('rcpReperfusionRisk')) $('rcpReperfusionRisk').textContent = `${fmt((st.reperfusion_injury_risk ?? 0) * 100, 0)}%`;
  const badge = $('rcpPanelBadge');
  if (badge) {
    badge.textContent = rosc ? `ROSC ${postRoscStatus}` : (arrest ? (shockable ? 'shockable arrest' : 'non-shockable arrest') : 'no arrest');
    badge.classList.toggle('arrest', arrest);
    badge.classList.toggle('cpr-active', cpr);
  }
  if ($('startCprBtn')) setButtonVisualState($('startCprBtn'), cpr ? 'active' : 'idle', cpr ? 'active' : '');
  if ($('stopCprBtn')) setButtonVisualState($('stopCprBtn'), !cpr && arrest ? 'confirmed' : 'idle', !cpr && arrest ? 'off' : '');
  if ($('postRoscCareBtn')) setButtonVisualState($('postRoscCareBtn'), postRoscStatus === 'active' ? 'confirmed' : (rosc ? 'pending' : 'idle'), postRoscStatus);
}

async function setCprActive(active=true) {
  if (!sessionId) return;
  const quality = clampNumber($('cprQualityRange')?.value, 0, 1, 0.75);
  const data = await sendAction('cpr_control', { active, quality, compression_fraction: active ? 0.85 : 0 }, { silent: true });
  const st = data?.session?.state || {};
  renderRcpPanel(st);
  const label = active ? 'RCP compressions started' : 'RCP compressions stopped';
  const detail = `quality ${fmt(st.CPR_quality ?? quality, 2)} · EtCO₂ ${fmt(st.EtCO2 ?? st.EtCO2_proxy, 0)} · MAP ${fmt(st.MAP, 0)}`;
  if ($('rcpFeedback')) $('rcpFeedback').textContent = `${label}: ${detail}`;
  showActionFeedback(label, detail, 'confirmed');
  logEvent(label, detail);
}

async function deliverShock(synchronized=false) {
  if (!sessionId) return;
  const energy = clampNumber($('shockEnergyInput')?.value, 1, 360, 40);
  const data = await sendAction('defibrillation', { energy_J: energy, synchronized }, { silent: true });
  const result = data?.result || {};
  const st = data?.session?.state || {};
  renderRcpPanel(st);
  const mode = synchronized ? 'Cardioversione sincronizzata' : 'Defib asincrona';
  const detail = `${fmt(result.energy_J, 0)} J · ${result.result || 'unknown'} · ${result.appropriate ? 'appropriata' : 'non indicata'}`;
  if ($('rcpFeedback')) $('rcpFeedback').textContent = `${mode}: ${detail}`;
  showActionFeedback(mode, detail, result.effective ? 'confirmed' : (result.appropriate ? 'pending' : 'error'));
  logEvent(mode, detail);
}

async function giveRcpDrug(drug) {
  if (!sessionId) return;
  const data = await sendAction('rcp_drug_bolus', { drug }, { silent: true });
  const result = data?.result || {};
  const st = data?.session?.state || {};
  renderRcpPanel(st);
  const labels = { epinephrine: 'Adrenalina bolo', amiodarone: 'Amiodarone bolo', atropine: 'Atropina bolo' };
  const label = labels[drug] || `Farmaco RCP ${drug}`;
  const detail = `${result.result || 'unknown'} · dose #${result.count || 0} · ${result.appropriate ? 'appropriato' : 'da rivalutare'}`;
  if ($('rcpFeedback')) $('rcpFeedback').textContent = `${label}: ${detail}`;
  showActionFeedback(label, detail, result.appropriate ? 'confirmed' : 'pending');
  logEvent(label, detail);
}

async function applyPostRoscCare() {
  if (!sessionId) return;
  const data = await sendAction('post_rosc_care', { fio2_target: 0.6, map_target: 55, paco2_target: 45 }, { silent: true });
  const result = data?.result || {};
  const st = data?.session?.state || {};
  renderRcpPanel(st);
  const label = 'Stabilizzazione post-ROSC';
  const detail = `${result.result || 'unknown'} · MAP ${fmt(st.MAP, 0)} · pH ${fmt(st.pH_a, 2)} · lactate ${fmt(st.lactate, 1)}`;
  if ($('rcpFeedback')) $('rcpFeedback').textContent = `${label}: ${detail}`;
  showActionFeedback(label, detail, result.appropriate ? 'confirmed' : 'pending');
  logEvent(label, detail);
}

function updateBedside(st, envelope={}) {
  if (!st) return;
  syncSessionTiming(st, envelope);
  lastBedsideState = st;
  $('vHR').textContent = fmt(st.HR, 0);
  $('vSpO2').textContent = fmt((st.SaO2 ?? 0) * 100, 0);
  $('vMAP').textContent = fmt(st.MAP, 0);
  const sbp = st.SBP ?? st.SAP;
  const dbp = st.DBP ?? st.DAP;
  if ($('vABP')) $('vABP').textContent = `${fmt(sbp, 0)}/${fmt(dbp, 0)}`;
  $('vPaCO2').textContent = fmt(st.PaCO2, 0);
  if ($('vEtCO2')) $('vEtCO2').textContent = fmt(st.EtCO2 ?? st.EtCO2_proxy, 0);
  $('vPaw').textContent = fmt(st.Paw, 0);
  const fio2 = st.FiO2_delivered ?? st.FiO2;
  $('vFiO2').textContent = Number.isFinite(Number(fio2)) ? Number(fio2).toFixed(2) : '--';
  $('simClock').textContent = `t = ${fmt(envelope.time_s ?? st.time_s ?? st.t, 1)} s`;
  updateVisualAlarms(st);
  updateCardiacStatusStrip(st);
  renderRcpPanel(st);
  pushBedsideTrend(st, envelope);
  renderVitalSparklines();
  if ($('popupChartOverlay') && !$('popupChartOverlay').hidden) drawPopupChart();
  $('airwayInterface').textContent = st.airway_interface || '--';
  $('ventMode').textContent = st.vent_mode || '--';
  $('airwayStatus').textContent = st.airway_event_type || st.airway_rescue_state || st.airway_event_status || '--';
  updateAirwayActionButtons(st);
  renderFluidControls(st);
  renderLabsStrip(Object.assign({}, st, lastExtendedMonitorState), 'bedside/full cache');
  requestLabsStripSnapshotSoon();
  if (isEmogasOpen()) {
    const hasFull = lastExtendedMonitorState && Object.keys(lastExtendedMonitorState).length > 0;
    renderEmogasPanel(Object.assign({}, st, lastExtendedMonitorState), hasFull ? 'full profile + bedside update' : 'waiting full profile');
    requestFullProfileSnapshotSoon();
  }
  syncControlsFromState(st);
  if ($('scenarioMirror') && currentScenario) $('scenarioMirror').value = currentScenario;
}
function connectStreams() {
  if (!sessionId) return;
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  bedsideWS = new WebSocket(`${scheme}://${location.host}/ws/session/${sessionId}/bedside?hz=4`);
  bedsideWS.onopen = () => setStatus('online', true);
  bedsideWS.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (!data.error) updateBedside(data.state, data);
  };
  bedsideWS.onclose = () => setStatus('offline');
  waveformWS = new WebSocket(`${scheme}://${location.host}/ws/session/${sessionId}/waveform?hz=24`);
  waveformWS.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (!data.error) {
      lastWaveform = data.state || {};
      pushWaveformTrend(lastWaveform);
      for (const r of renderers) r.update(lastWaveform);
    }
  };
}
function disconnectStreams() {
  if (bedsideWS) bedsideWS.close();
  if (waveformWS) waveformWS.close();
  bedsideWS = null; waveformWS = null;
}

window.addEventListener('resize', () => renderVitalSparklines());

function downloadText(filename, text, mime='text/plain') {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
function enableSessionButtons() {
  for (const id of ['startBtn','pauseBtn','stepBtn','resetBtn','debriefBtn','addInstructorNoteBtn','bookmarkBtn','instructorReportBtn','saveSessionBtn','exportJsonBtn','exportMdBtn']) {
    if ($(id)) $(id).disabled = false;
  }
  updateSessionButtonStates();
}
async function saveSessionToServer() {
  if (!sessionId) return;
  const basename = `${currentScenario || 'session'}_${sessionId.slice(0,8)}`;
  const data = await api(`/session/${sessionId}/save`, { method: 'POST', body: JSON.stringify({ basename }) });
  const saved = data.saved || {};
  if ($('saveMeta')) $('saveMeta').textContent = `Saved: ${saved.json_path || '--'} · ${saved.markdown_path || '--'}`;
  if ($('savedPathInput') && saved.json_path) $('savedPathInput').value = saved.json_path;
  logEvent('Session saved', saved.json_path || 'server export');
}
async function exportSession(format='json') {
  if (!sessionId) return;
  const res = await fetch(`/session/${sessionId}/export?format=${format}`);
  if (!res.ok) throw new Error(await res.text());
  if (format === 'md') {
    const text = await res.text();
    downloadText(`${currentScenario || 'session'}_${sessionId.slice(0,8)}.md`, text, 'text/markdown');
  } else {
    const data = await res.json();
    downloadText(`${currentScenario || 'session'}_${sessionId.slice(0,8)}.json`, JSON.stringify(data, null, 2), 'application/json');
  }
  logEvent('Session exported', format.toUpperCase());
}
async function loadSavedSession() {
  const path = ($('savedPathInput') && $('savedPathInput').value || '').trim();
  if (!path) { alert('Insert saved JSON path first.'); return; }
  disconnectStreams();
  const data = await api('/session/load_saved', { method: 'POST', body: JSON.stringify({ path, replay_actions: true }) });
  sessionId = data.session_id;
  currentScenario = data.scenario;
  if ($('scenarioSelect')) $('scenarioSelect').value = (data.scenario_path || '').split('/').pop()?.replace(/\.yaml$/, '') || currentScenario;
  $('sessionMeta').textContent = `${data.scenario} · restored ${sessionId.slice(0,8)} · t ${fmt(data.time_s,1)} s`;
  if ($('currentScenarioLabel')) $('currentScenarioLabel').textContent = data.scenario;
  if ($('scenarioMirror')) $('scenarioMirror').value = data.scenario;
  updateScenarioInfoCard(currentScenario || data.scenario, data);
  SESSION_UI_STATE.loaded = true;
  SESSION_UI_STATE.running = false;
  SESSION_UI_STATE.simTimeS = Number(data.time_s ?? data.state?.time_s ?? data.state?.t ?? 0);
  SESSION_UI_STATE.speed = readSessionSpeed();
  resetWallClock();
  enableSessionButtons();
  updateBedside(data.state, data);
  connectStreams();
  logEvent('Saved session loaded', path);
}

function setupControls() {
  setupApparatusNavigation();
  if ($('scenarioSelect')) $('scenarioSelect').onchange = () => { currentScenario = $('scenarioSelect').value; if ($('currentScenarioLabel')) $('currentScenarioLabel').textContent = currentScenario; updateScenarioInfoCard(currentScenario); };
  $('loadBtn').onclick = () => runSessionButtonAction('loadBtn', loadSession).catch(reportUiError);
  $('startBtn').onclick = () => runSessionButtonAction('startBtn', startSession).catch(reportUiError);
  $('pauseBtn').onclick = () => runSessionButtonAction('pauseBtn', pauseSession).catch(reportUiError);
  $('stepBtn').onclick = () => runSessionButtonAction('stepBtn', stepSession).catch(reportUiError);
  $('resetBtn').onclick = () => runSessionButtonAction('resetBtn', resetSession).catch(reportUiError);
  if ($('emergencyScenarioSelect')) $('emergencyScenarioSelect').onchange = updateEmergencyScenarioDetails;
  if ($('loadEmergencyBtn')) $('loadEmergencyBtn').onclick = () => loadEmergencySession().catch(reportUiError);
  if ($('debriefBtn')) $('debriefBtn').onclick = () => generateDebrief().catch(reportUiError);
  if ($('hideDiagnosisToggle')) $('hideDiagnosisToggle').onchange = (e) => setDiagnosisVisibility(e.target.checked).catch(err => alert(err.message));
  if ($('addInstructorNoteBtn')) $('addInstructorNoteBtn').onclick = () => addInstructorNote().catch(reportUiError);
  if ($('bookmarkBtn')) $('bookmarkBtn').onclick = () => addInstructorNote('Bookmark', 'bookmark', true).catch(reportUiError);
  if ($('instructorReportBtn')) $('instructorReportBtn').onclick = () => generateInstructorReport().catch(reportUiError);
  if ($('saveSessionBtn')) $('saveSessionBtn').onclick = () => saveSessionToServer().catch(reportUiError);
  if ($('exportJsonBtn')) $('exportJsonBtn').onclick = () => exportSession('json').catch(reportUiError);
  if ($('exportMdBtn')) $('exportMdBtn').onclick = () => exportSession('md').catch(reportUiError);
  if ($('loadSavedBtn')) $('loadSavedBtn').onclick = () => loadSavedSession().catch(reportUiError);
  if ($('scenarioInfoBtn')) $('scenarioInfoBtn').onclick = () => toggleScenarioInfoCard();
  if ($('quickEmogasBtn')) $('quickEmogasBtn').onclick = () => openApparatus('emogasPanel');
  if ($('quickBolusBtn')) $('quickBolusBtn').onclick = () => openApparatus('drugPanel', 'bolusPanel');
  if ($('quickExtendedMonitorBtn')) $('quickExtendedMonitorBtn').onclick = () => openApparatus('extendedMonitorPanel');
  if ($('audioMonitorBtn')) $('audioMonitorBtn').onclick = () => toggleAudioMonitor().catch(reportUiError);
  if ($('extendedMonitorRefreshBtn')) $('extendedMonitorRefreshBtn').onclick = () => refreshExtendedMonitor().catch(reportUiError);
  if ($('emogasRefreshBtn')) $('emogasRefreshBtn').onclick = () => refreshExtendedMonitor().catch(reportUiError);
  if ($('extendedChartsBtn')) $('extendedChartsBtn').onclick = () => openPopupChart('MAP');
  if ($('rawBusToggleBtn')) $('rawBusToggleBtn').onclick = toggleRawBusInspector;
  if ($('rawBusFilter')) $('rawBusFilter').oninput = () => renderRawBusInspector(lastExtendedMonitorState);
  if ($('drugAuditRefreshBtn')) $('drugAuditRefreshBtn').onclick = () => refreshDrugAudit().catch(reportUiError);
  if ($('clearBolusStatusBtn')) $('clearBolusStatusBtn').onclick = clearBolusStatus;
  if ($('popupChartCloseBtn')) $('popupChartCloseBtn').onclick = closePopupChart;
  if ($('popupChartRedrawBtn')) $('popupChartRedrawBtn').onclick = drawPopupChart;
  if ($('popupChartSelect')) $('popupChartSelect').onchange = drawPopupChart;
  if ($('draftScenarioBtn')) $('draftScenarioBtn').onclick = () => draftScenario().catch(reportUiError);
  if ($('validateScenarioBtn')) $('validateScenarioBtn').onclick = () => validateAuthoredScenario().catch(reportUiError);
  if ($('saveScenarioBtn')) $('saveScenarioBtn').onclick = () => saveAuthoredScenario().catch(reportUiError);
  if ($('loadAuthoredScenarioBtn')) $('loadAuthoredScenarioBtn').onclick = () => loadAuthoredScenario().catch(reportUiError);
  if ($('cprQualityRange')) $('cprQualityRange').oninput = () => { if ($('cprQualityOut')) $('cprQualityOut').textContent = Number($('cprQualityRange').value).toFixed(2); };
  if ($('startCprBtn')) $('startCprBtn').onclick = () => setCprActive(true).catch(reportUiError);
  if ($('stopCprBtn')) $('stopCprBtn').onclick = () => setCprActive(false).catch(reportUiError);
  if ($('defibAsyncBtn')) $('defibAsyncBtn').onclick = () => deliverShock(false).catch(reportUiError);
  if ($('cardioversionSyncBtn')) $('cardioversionSyncBtn').onclick = () => deliverShock(true).catch(reportUiError);
  if ($('rcpEpinephrineBtn')) $('rcpEpinephrineBtn').onclick = () => giveRcpDrug('epinephrine').catch(reportUiError);
  if ($('rcpAmiodaroneBtn')) $('rcpAmiodaroneBtn').onclick = () => giveRcpDrug('amiodarone').catch(reportUiError);
  if ($('rcpAtropineBtn')) $('rcpAtropineBtn').onclick = () => giveRcpDrug('atropine').catch(reportUiError);
  if ($('postRoscCareBtn')) $('postRoscCareBtn').onclick = () => applyPostRoscCare().catch(reportUiError);
  bindLiveRange('fio2Range', 'fio2Out', 'set_fio2', (v) => v.toFixed(2));
  bindLiveRange('peepRange', 'peepOut', 'set_peep', (v) => String(v));
  bindLiveRange('rrRange', 'rrOut', 'set_rr', (v) => String(v));
  document.querySelectorAll('button[data-action="airway_event"]').forEach(btn => {
    btn.setAttribute('aria-pressed', 'false');
    btn.onclick = () => {
      btn.classList.add('pending');
      btn.dataset.state = 'pending';
      btn.setAttribute('aria-pressed', 'true');
      const eventName = btn.dataset.event;
      const severity = btn.dataset.severity || AIRWAY_EVENT_DEFAULT_SEVERITIES[eventName] || 'moderate';
      sendAction('airway_event', { name: eventName, severity })
        .catch(e => {
          btn.classList.remove('pending');
          updateAirwayActionButtons(lastBedsideState);
          reportUiError(e);
        });
    };
  });
  document.querySelectorAll('input[data-drug]').forEach(inp => {
    bindLiveNumericInput(inp, inp.dataset.drug);
  });
  document.querySelectorAll('select[data-crystalloid-type]').forEach(sel => bindCrystalloidTypeSelect(sel));
}
function animate(now) {
  const dt = Math.min(0.05, (now - lastFrame) / 1000);
  lastFrame = now;
  for (const r of renderers) r.draw(dt);
  driveMonitorAudio(now);
  rotateLabsStrip(now);
  updateTimeTelemetry(now);
  requestAnimationFrame(animate);
}
async function init() {
  renderers = [
    new WaveformRenderer($('ecgCanvas'), 'ecg', '#4dff88'),
    new WaveformRenderer($('plethCanvas'), 'pleth', '#55ddff'),
    new WaveformRenderer($('abpCanvas'), 'abp', '#ff5a6a'),
    new WaveformRenderer($('respCanvas'), 'resp', '#ffd64d'),
  ];
  setupControls();
  setApparatusPanel('sessionPanel');
  await loadScenarios();
  await loadEmergencyScenarios();
  await loadInstructorPresets();
  await loadAuthoringTemplates();
  setStatus('ready');
  requestAnimationFrame(animate);
}
init().catch(err => { setStatus('error'); console.error(err); alert(err.message); });






























