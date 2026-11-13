"""Claude Usage Tracker: counts your Claude Code usage from the logs on this computer.

    python3 -I build.py                      # writes ~/.claude/usage-tracker/claude-usage.json
    python3 -I build.py OUT.json             # writes the data somewhere else
    python3 -I build.py --html OUT.html      # also writes a self-contained dashboard page

Reads only local files: ~/.claude/projects/**/*.jsonl (or $CLAUDE_CONFIG_DIR/projects) and,
if the focus tracker is installed, ~/.claude/usage-tracker/focus.log. Sends nothing anywhere.
"""
import argparse, json, glob, collections, os, re, sys
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude')
ROOT = os.path.join(CONFIG, 'projects')
BOARD = os.path.join(CONFIG, 'usage-tracker')
ap = argparse.ArgumentParser(description='Count Claude Code usage from local logs.')
ap.add_argument('out', nargs='?', default=os.path.join(BOARD, 'claude-usage.json'), help='where to write the JSON data')
ap.add_argument('--html', help='also write a self-contained dashboard page here')
ap.add_argument('--idle', type=int, default=300, help='seconds of silence that count as a break (default 300)')
ap.add_argument('--no-titles', action='store_true', help='leave session titles out (for sharing screenshots)')
args = ap.parse_args()
OUT = args.out
IDLE = args.idle
W = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

def model_name(m):
    """claude-opus-5-5 -> Opus 5.5; anything unrecognised is shown as is."""
    mm = re.match(r'^claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$', m or '')
    return f"{mm.group(1).title()} {mm.group(2)}{'.' + mm.group(3) if mm.group(3) else ''}" if mm else (m or '?')

def proj(cwd):
    if not cwd: return 'other'
    if '/scratch-workspaces/' in cwd: return 'Scratch (chat-style tasks)'
    wt = re.search(r'/([^/]+)/\.claude/worktrees/', cwd)
    if wt: return wt.group(1) + ' (worktrees)'
    return os.path.basename(cwd.rstrip('/')) or cwd

def ts(s): return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone()

seen = set(); D = collections.defaultdict(collections.Counter)
model = collections.Counter(); projects = collections.Counter(); tools = collections.Counter(); heat = collections.Counter()
sess = collections.defaultdict(lambda: {'tok': 0, 'msgs': 0, 'proj': None, 'start': None, 'end': None, 'times': []})
titles = {}; art_days = collections.Counter(); art_calls = {}; art_created = collections.defaultdict(set); art_edited = collections.defaultdict(set); prompts = 0; sub = 0; events = []
for f in glob.glob(ROOT + '/**/*.jsonl', recursive=True):
    for line in open(f, errors='ignore'):
        try: d = json.loads(line)
        except Exception: continue
        t = d.get('type'); sid = d.get('sessionId'); stamp = d.get('timestamp')
        if t == 'custom-title' and sid: titles[sid] = d.get('customTitle') or d.get('title')
        if t not in ('user', 'assistant') or not stamp: continue
        if not d.get('isSidechain'):
            dt = ts(stamp); events.append(dt); sess[sid]['times'].append(dt)
        if t == 'user':
            m = d.get('message') or {}; c = m.get('content')
            for x in c if isinstance(c, list) else []:
                if isinstance(x, dict) and x.get('type') == 'tool_result' and x.get('tool_use_id') in art_calls:
                    name, inp, day = art_calls.pop(x['tool_use_id'])
                    rc = x.get('content'); txt = rc if isinstance(rc, str) else ' '.join(y.get('text', '') for y in rc or [] if isinstance(y, dict))
                    if x.get('is_error'): continue
                    if name == 'Artifact':
                        mm = re.search(r'https://claude\.ai/(?:code/)?artifact/([A-Za-z0-9-]+)', txt)
                        if not mm or inp.get('asset'): continue
                        aid = mm.group(1)
                        if txt.startswith('Created a new Artifact') or re.search(r'\(Version 1,', txt): art_created[day].add(aid)
                        elif txt.startswith('Published') or txt.startswith('Updated the Artifact'): art_edited[day].add(aid)
                    else:
                        mm = re.search(r'artifact/([A-Za-z0-9-]+)', inp.get('url') or '')
                        if mm and ('committed' in txt or 'version' in txt.lower()): art_edited[day].add(mm.group(1))
            if not d.get('isSidechain') and not d.get('toolUseResult') and (isinstance(c, str) or (isinstance(c, list) and any(isinstance(x, dict) and x.get('type') == 'text' for x in c))):
                prompts += 1
            continue
        m = d.get('message') or {}; mid = m.get('id')
        for c in m.get('content') or []:
            if isinstance(c, dict) and c.get('type') == 'tool_use' and (mid, c.get('id')) not in seen:
                seen.add((mid, c.get('id')))
                n = re.sub(r'^mcp__[0-9a-f-]{36}__', '', c['name']).replace('mcp__', '').replace('ccd_turn__', '').replace('Claude_Browser__', 'browser_').replace('claude-code-remote__', 'remote_')
                tools[n] += 1
                inp = c.get('input') or {}
                if (c['name'] == 'Artifact' and inp.get('action', 'publish') == 'publish') or (c['name'] == 'ArtifactData' and inp.get('action') in ('set', 'update', 'batch', 'str_replace', 'delete')):
                    art_calls[c.get('id')] = (c['name'], inp, ts(stamp).strftime('%Y-%m-%d'))
        u = m.get('usage')
        if not u or not mid or (mid, 'u') in seen: continue
        seen.add((mid, 'u'))
        dt = ts(stamp); day = dt.strftime('%Y-%m-%d')
        i, o, cr, cc = (u.get(k, 0) or 0 for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
        tot = i + o + cr + cc
        D[day].update({'in': i, 'out': o, 'cr': cr, 'cc': cc, 'msgs': 1})
        model[m.get('model', '?')] += tot; projects[proj(d.get('cwd'))] += tot; heat[(dt.weekday(), dt.hour)] += tot
        if d.get('isSidechain'): sub += tot
        s = sess[sid]; s['tok'] += tot; s['msgs'] += 1; s['proj'] = proj(d.get('cwd'))
        s['start'] = min(filter(None, [s['start'], stamp])); s['end'] = max(filter(None, [s['end'], stamp]))

def active(times):
    """Seconds of activity: sum of gaps between consecutive events no longer than IDLE, plus per-day split."""
    times = sorted(times); per_day = collections.Counter(); per_hour = collections.Counter(); total = 0
    for a, b in zip(times, times[1:]):
        g = (b - a).total_seconds()
        if 0 < g <= IDLE: total += g; per_day[a.strftime('%Y-%m-%d')] += g; per_hour[a.hour] += g
    return total, per_day, per_hour

act_total, act_day, act_hour = active(events)

# Minutes the Claude app was in front (one line per minute from focus-tick.sh).
FOCUS = os.path.join(BOARD, 'focus.log')
app_day = collections.Counter(); app_hour = collections.Counter(); tracking_since = None
if os.path.exists(FOCUS):
    for line in sorted(set(open(FOCUS).read().split())):
        app_day[line[:10]] += 1; app_hour[int(line[11:13])] += 1
        tracking_since = tracking_since or line[:10]
for k, s in sess.items():
    s['active'] = active(s['times'])[0]

if not D and not app_day:
    sys.exit('No Claude Code logs found in ' + ROOT + '. Use Claude Code for a bit, then run this again.')
days = []
all_art = set().union(*art_created.values(), *art_edited.values()) if (art_created or art_edited) else set()
for day in sorted(set(D) | set(act_day) | set(app_day)):
    v = D[day]
    days.append(dict(date=day, input=v['in'], output=v['out'], cache_read=v['cr'], cache_write=v['cc'],
                     total=v['in'] + v['out'] + v['cr'] + v['cc'], replies=v['msgs'],
                     artifacts=len(art_created[day] | art_edited[day]), artifacts_created=len(art_created[day]), artifacts_edited=len(art_edited[day] - art_created[day]),
                     active_minutes=round(act_day.get(day, 0) / 60),
                     app_minutes=app_day.get(day, 0) if tracking_since and day >= tracking_since else None))
top = sorted((s for s in sess.values() if s['tok']), key=lambda s: -s['tok'])[:8]
names_by = {id(s): titles.get(k) for k, s in sess.items()}
out = dict(
    daily=days,
    models=[dict(model=model_name(m), tokens=t) for m, t in model.most_common() if t > 0 and m != '<synthetic>'],
    projects=[dict(project=p, tokens=t) for p, t in projects.most_common(6)],
    tools=[dict(tool=t, calls=c) for t, c in tools.most_common(12)],
    hourly=[dict(hour=h, active_minutes=round(act_hour.get(h, 0) / 60), avg_minutes=round(act_hour.get(h, 0) / 60 / max(1, sum(1 for v in act_day.values() if v)), 1), app_minutes=app_hour.get(h, 0)) for h in range(24)],
    heat=[dict(weekday=W[w], hour=h, tokens=v) for (w, h), v in heat.items()],
    sessions=[dict(title=(None if args.no_titles else names_by[id(s)]) or f'Session {i + 1}', project=s['proj'], tokens=s['tok'], replies=s['msgs'],
                   active_minutes=round(s['active'] / 60), started=s['start'][:10], ended=s['end'][:10]) for i, s in enumerate(top)],
    totals=[dict(tokens=sum(d['total'] for d in days), output=sum(d['output'] for d in days), cache_read=sum(d['cache_read'] for d in days),
                 sessions=sum(1 for s in sess.values() if s['tok']), prompts=prompts, artifacts=len(all_art), artifacts_created=len(set().union(*art_created.values())) if art_created else 0, tool_calls=sum(tools.values()),
                 subagent_tokens=sub, days_active=sum(1 for d in days if d['total']), first_day=days[0]['date'], last_day=days[-1]['date'],
                 active_hours=round(act_total / 3600, 1), app_hours=round(sum(app_day.values()) / 60, 1), tracking_since=tracking_since, generated=datetime.now().isoformat(timespec='minutes'))])
def write(path, text):
    """Write via a temporary file, so a reader never sees a half-written or empty file."""
    path = os.path.abspath(path); os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w') as f: f.write(text)
    os.replace(tmp, path)

write(OUT, json.dumps(out))
if args.html:
    tpl = open(os.path.join(HERE, 'dashboard.template.html')).read()
    if '/*__DATA__*/null' not in tpl:
        sys.exit('dashboard.template.html is missing its data marker; reinstall Claude Usage Tracker.')
    write(args.html, tpl.replace('/*__DATA__*/null', json.dumps(out).replace('<', '\\u003c')))
print(json.dumps(out['totals'][0]))
