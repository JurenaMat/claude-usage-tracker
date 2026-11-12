// Claude Usage Tracker — desktop widget for Übersicht. Recounts local Claude Code logs every 15 minutes.
// Click it to open the full dashboard.
import { run } from "uebersicht";
// install.sh replaces __BOARD__ with the folder it installed to.
const BOARD = "__BOARD__";
export const command = `CLAUDE_CONFIG_DIR="${BOARD}/.." /usr/bin/python3 -I "${BOARD}/build.py" "${BOARD}/widget.json" --html "${BOARD}/dashboard.html" >/dev/null && cat "${BOARD}/widget.json"`;
export const refreshFrequency = 15 * 60 * 1000;

export const className = `
  right: 28px; bottom: 28px; width: 300px; cursor: pointer;
  padding: 16px 18px 14px;
  border-radius: 16px;
  background: rgba(22, 24, 32, 0.62);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  border: 1px solid rgba(255,255,255,0.10);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  color: #f2efe8;
  font-family: -apple-system, "SF Pro Text", "Helvetica Neue", sans-serif;
  font-size: 12px;
  .hd { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:10px; }
  .ttl { font-weight:600; letter-spacing:.08em; text-transform:uppercase; font-size:10.5px; color:#d9a679; }
  .muted { color: rgba(242,239,232,0.6); }
  .row { display:flex; gap:18px; margin-bottom:12px; }
  .big { font-size:26px; font-weight:300; font-variant-numeric: tabular-nums; line-height:1.05; }
  .lab { font-size:10.5px; color: rgba(242,239,232,0.6); margin-top:2px; }
  .bars { display:flex; align-items:flex-end; gap:6px; height:56px; margin:4px 0 2px; }
  .bar { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; height:100%; }
  .fill { width:100%; border-radius:3px; background:#d9a679; min-height:2px; }
  .fill.today { background:#f2c79a; }
  .fill.est { background: transparent; border: 1px dashed rgba(217,166,121,0.7); box-sizing: border-box; }
  .dl { display:flex; gap:6px; margin-bottom:10px; }
  .dl span { flex:1; text-align:center; font-size:10px; color: rgba(242,239,232,0.55); }
  .ft { display:flex; justify-content:space-between; border-top:1px solid rgba(255,255,255,0.08); padding-top:8px; font-size:11px; }
`;

const fmt = (n) => {
  if (n == null) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e8 ? 0 : 1) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(0) + "k";
  return String(Math.round(n));
};
const dur = (m) => (m >= 60 ? Math.floor(m / 60) + "h " + String(Math.round(m % 60)).padStart(2, "0") + "m" : Math.round(m || 0) + "m");
const iso = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");

export const render = ({ output, error }) => {
  let data;
  try { data = JSON.parse(output); } catch (e) { return <div className="muted">Claude usage: waiting for data… (use Claude Code for a bit)</div>; }
  const byDay = Object.fromEntries(data.daily.map((d) => [d.date, d]));
  const today = new Date();
  const week = [...Array(7)].map((_, i) => { const d = new Date(today); d.setDate(today.getDate() - 6 + i); const r = byDay[iso(d)] || {}; const app = r.app_minutes != null; return { d, m: app ? r.app_minutes : (r.active_minutes || 0), est: !app, a: r.active_minutes || 0, t: r.total || 0, ac: r.artifacts_created || 0, ae: r.artifacts_edited || 0 }; });
  const t = week[6];
  const max = Math.max(30, ...week.map((w) => w.m));
  const peak = data.hourly ? data.hourly.reduce((a, b) => (b.avg_minutes > a.avg_minutes ? b : a)) : null;
  const tot = data.totals[0];
  const weekMin = week.reduce((s, w) => s + w.m, 0);
  return (
    <div onClick={() => run(`open "${BOARD}/dashboard.html"`)}>
      <div className="hd"><span className="ttl">Claude today</span><span className="muted">{today.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}</span></div>
      <div className="row">
        <div><div className="big">{t.est ? "—" : dur(t.m)}</div><div className="lab">in the app</div></div>
        <div><div className="big">{dur(t.a)}</div><div className="lab">working</div></div>
        <div><div className="big">{fmt(t.t)}</div><div className="lab">tokens</div></div>
      </div>
      <div className="bars">
        {week.map((w, i) => (
          <div className="bar" key={i} title={dur(w.m)}><div className={"fill" + (i === 6 ? " today" : "") + (w.est ? " est" : "")} style={{ height: Math.max(2, (w.m / max) * 56) + "px" }} /></div>
        ))}
      </div>
      <div className="dl">{week.map((w, i) => <span key={i}>{w.d.toLocaleDateString(undefined, { weekday: "narrow" })}</span>)}</div>
      <div className="ft">
        <span className="muted">Artifacts today: {t.ac} new · {t.ae} edited</span>
        <span className="muted">Peak {peak ? String(peak.hour).padStart(2, "0") + ":00" : "—"}</span>
      </div>
    </div>
  );
};
