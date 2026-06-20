class WaveformRenderer {
  constructor(canvas, kind, color) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.kind = kind;
    this.color = color;
    this.phase = 0;
    this.state = { HR: 120, SaO2: 0.98, MAP: 65, SBP: 90, DBP: 55, RR_total: 25, Paw: 5, EtCO2: 35, EtCO2_proxy: 35 };
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }
  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(300, Math.floor(rect.width * dpr));
    this.canvas.height = Math.max(100, Math.floor(rect.height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  update(state) { this.state = { ...this.state, ...state }; }
  draw(dt) {
    this.phase += dt;
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#03080d';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(50, 80, 100, 0.25)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 34) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const t = this.phase + u * 5.0;
      const y = this.sample(t, u, h);
      if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  sample(t, u, h) {
    if (this.kind === 'ecg') return this.ecg(t, h);
    if (this.kind === 'pleth') return this.pleth(t, h);
    if (this.kind === 'abp') return this.abp(t, h);
    return this.resp(t, h);
  }
  cycle(t, rate) {
    const period = 60 / Math.max(1, rate);
    return ((t % period) + period) % period / period;
  }
  ecg(t, h) {
    const hr = Number(this.state.HR || 120);
    const p = this.cycle(t, hr);
    let v = 0.02 * Math.sin(2 * Math.PI * p);
    v += 0.08 * Math.exp(-Math.pow((p - 0.18) / 0.035, 2));
    v += -0.18 * Math.exp(-Math.pow((p - 0.30) / 0.012, 2));
    v += 0.95 * Math.exp(-Math.pow((p - 0.33) / 0.010, 2));
    v += -0.25 * Math.exp(-Math.pow((p - 0.36) / 0.018, 2));
    v += 0.25 * Math.exp(-Math.pow((p - 0.62) / 0.07, 2));
    return h * 0.58 - v * h * 0.34;
  }
  pleth(t, h) {
    const hr = Number(this.state.HR || 120);
    const spo2 = Number(this.state.SaO2 || 0.98);
    const p = this.cycle(t, hr);
    const up = Math.exp(-Math.pow((p - 0.18) / 0.09, 2));
    const notch = -0.20 * Math.exp(-Math.pow((p - 0.42) / 0.035, 2));
    const wave = Math.max(0, up + notch) * (0.5 + spo2 * 0.5);
    return h * 0.78 - wave * h * 0.45;
  }
  abp(t, h) {
    const hr = Number(this.state.HR || 120);
    const map = Number(this.state.MAP || 65);
    const rawSbp = this.state.SBP ?? this.state.SAP ?? (map + 20);
    const rawDbp = this.state.DBP ?? this.state.DAP ?? Math.max(map - 15, 10);
    let sbp = Number(rawSbp);
    let dbp = Number(rawDbp);
    if (!Number.isFinite(sbp)) sbp = map + 20;
    if (!Number.isFinite(dbp)) dbp = Math.max(map - 15, 10);
    if (sbp <= dbp) sbp = dbp + 5;

    const p = this.cycle(t, hr);
    const pulsePressure = Math.max(4, sbp - dbp);
    const systolicUpstroke = Math.exp(-Math.pow((p - 0.16) / 0.075, 2));
    const dicroticShoulder = 0.18 * Math.exp(-Math.pow((p - 0.42) / 0.12, 2));
    const pulseShape = Math.min(1, Math.max(0, systolicUpstroke + dicroticShoulder));

    // legacy contract: const pressure = dbp + (sbp - dbp) * pulseShape
    // The ABP trace is pressure-coupled: the vertical position follows MAP,
    // and the visible amplitude expands/contracts with pulse pressure.
    const modelPressure = dbp + pulsePressure * pulseShape;
    const pulseGain = Math.max(0.35, Math.min(1.35, pulsePressure / 35));
    const pressure = map + (modelPressure - map) * pulseGain;

    // Fixed bedside scale: low pressures stay visually low instead of being
    // cosmetically recentered around MAP.
    return h - ((pressure - 15) / 165) * h;
  }
  resp(t, h) {
    const rr = Number(this.state.RR_total || 25);
    const paw = Number(this.state.Paw || 5);
    const etco2 = Number(this.state.EtCO2 ?? this.state.EtCO2_proxy ?? 35);
    const p = this.cycle(t, rr);
    const breath = p < 0.38 ? Math.sin((p / 0.38) * Math.PI) : 0.1 * Math.exp(-(p - 0.38) * 6);
    const pressure = Math.max(0, paw) + breath * Math.max(5, etco2 / 4);
    return h - Math.min(1, pressure / 40) * h * 0.75 - h * 0.1;
  }
}
window.WaveformRenderer = WaveformRenderer;
