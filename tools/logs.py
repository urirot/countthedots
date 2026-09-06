"""Shared reading of an Amplify access-log CSV.

Both read-logs.py (terminal) and build-usage.py (the /usage page) parse through
here, so the definition of a "visit" and a "click" cannot drift between them.
"""
import csv, re
from collections import Counter, defaultdict
from datetime import datetime, timezone

BOT = re.compile(r'bot|crawl|spider|slurp|preview|monitor|curl|wget|headless|'
                 r'lighthouse|python-requests', re.I)


def pick(headers, *wants):
    """Amplify has changed these column names before, so find them by shape."""
    low = [h.lower().strip() for h in headers]
    for want in wants:
        for i, h in enumerate(low):
            if h == want:
                return i
    for want in wants:
        for i, h in enumerate(low):
            if want in h:
                return i
    return None


def parse_time(v):
    v = v.strip().strip('"')
    if re.fullmatch(r'\d{10}', v):
        return datetime.fromtimestamp(int(v), timezone.utc)
    if re.fullmatch(r'\d{13}', v):
        return datetime.fromtimestamp(int(v) / 1000, timezone.utc)
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S',
                '%d/%b/%Y:%H:%M:%S %z'):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return None


def classify(path):
    """A visit is the page; a click is /go, which only a CTA press produces."""
    p = path.split('?')[0].rstrip('/').lower() or '/'
    if p in ('/', '/index.html'):
        return 'visit'
    if p == '/go' or p.startswith('/go/'):
        return 'click'
    return None                      # assets, favicon, /usage itself, junk


class LayoutError(Exception):
    def __init__(self, headers):
        self.headers = headers


def read(path):
    """-> dict(days={'YYYY-MM-DD': Counter}, hours=Counter, totals=Counter, bots=int)"""
    # utf-8-sig: CloudFront exports carry a BOM that would otherwise glue itself to
    # the first header name and break an exact match on it
    with open(path, newline='', encoding='utf-8-sig', errors='replace') as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise LayoutError([])

    head = rows[0]
    # Two shapes in the wild: one timestamp column, or a CloudFront-style export
    # with 'date' and 'time' split apart. A lone '06:01:15' parses as nothing, so
    # the halves have to be rejoined before anything else looks at them.
    i_ts = pick(head, 'timestamp', 'requesttime', 'datetime')
    i_date = pick(head, 'date')
    i_clock = pick(head, 'time')
    i_time = i_ts if i_ts is not None else (i_clock if i_clock is not None else i_date)
    i_path = pick(head, 'uri', 'path', 'request', 'url', 'cs-uri-stem')
    i_stat = pick(head, 'status', 'sc-status', 'statuscode')
    i_ua = pick(head, 'useragent', 'user_agent', 'user-agent', 'agent')
    if i_time is None or i_path is None:
        raise LayoutError(head)

    days, hours, totals, bots = defaultdict(Counter), Counter(), Counter(), 0
    for r in rows[1:]:
        if len(r) <= max(i_time, i_path):
            continue
        kind = classify(r[i_path])
        if not kind:
            continue
        if i_stat is not None and len(r) > i_stat:
            s = r[i_stat].strip()
            # 304 is a revalidated revisit — a real one. Other 3xx/4xx/5xx are not.
            if s[:1] in '345' and s != '304':
                continue
        if i_ua is not None and len(r) > i_ua and BOT.search(r[i_ua]):
            bots += 1
            continue
        if i_ts is None and i_date is not None and i_clock is not None and i_date != i_clock:
            stamp = f'{r[i_date].strip()}T{r[i_clock].strip()}'
        else:
            stamp = r[i_time]
        t = parse_time(stamp)
        if not t:
            continue
        days[t.strftime('%Y-%m-%d')][kind] += 1
        if kind == 'click':
            hours[t.hour] += 1
        totals[kind] += 1

    return {'days': dict(days), 'hours': hours, 'totals': totals, 'bots': bots}
