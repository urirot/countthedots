#!/usr/bin/env python3
"""Turn an Amplify access-log CSV into visits vs click-throughs, over time.

    python3 tools/read-logs.py access-logs.csv
    python3 tools/read-logs.py access-logs.csv --hours     # add time-of-day

Get the CSV from: Amplify console -> your landing app -> Hosting -> Monitoring
-> Access logs -> pick a date range -> Download.

A "visit" is a request for the page itself; a "click" is a request for /go,
which only happens when someone presses an Open the app button. Assets, bots
and redirects are excluded so the numbers mean something.
"""
import csv, sys, re
from collections import Counter, defaultdict
from datetime import datetime, timezone

BOT = re.compile(r'bot|crawl|spider|slurp|preview|monitor|curl|wget|headless|lighthouse|python-requests', re.I)


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
    if re.fullmatch(r'\d{10}', v):                      # epoch seconds
        return datetime.fromtimestamp(int(v), timezone.utc)
    if re.fullmatch(r'\d{13}', v):                      # epoch millis
        return datetime.fromtimestamp(int(v) / 1000, timezone.utc)
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S',
                '%d/%b/%Y:%H:%M:%S %z'):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            pass
    try:                                                 # last resort
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return None


def classify(path):
    p = path.split('?')[0].rstrip('/').lower() or '/'
    if p in ('/', '/index.html'):
        return 'visit'
    if p == '/go' or p.startswith('/go/'):
        return 'click'
    return None                                          # assets, favicon, junk


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    path_arg, show_hours = argv[1], '--hours' in argv

    with open(path_arg, newline='', encoding='utf-8', errors='replace') as fh:
        rows = list(csv.reader(fh))
    if not rows:
        sys.exit('empty file')

    head = rows[0]
    i_time = pick(head, 'timestamp', 'time', 'date', 'requesttime')
    i_path = pick(head, 'uri', 'path', 'request', 'url', 'cs-uri-stem')
    i_stat = pick(head, 'status', 'sc-status', 'statuscode')
    i_ua   = pick(head, 'useragent', 'user_agent', 'user-agent', 'agent')
    if i_time is None or i_path is None:
        print('Could not find the time and path columns. Headers were:')
        for h in head:
            print('   ', h)
        sys.exit('\nSend me this header line and I will teach the script the layout.')

    by_day = defaultdict(Counter)
    by_hour = Counter()
    totals = Counter()
    skipped_bots = 0

    for r in rows[1:]:
        if len(r) <= max(i_time, i_path):
            continue
        kind = classify(r[i_path])
        if not kind:
            continue
        if i_stat is not None and len(r) > i_stat:
            s = r[i_stat].strip()
            if s.startswith('3') or s.startswith('4') or s.startswith('5'):
                if not (kind == 'visit' and s == '304'):   # 304 = a real revisit
                    continue
        if i_ua is not None and len(r) > i_ua and BOT.search(r[i_ua]):
            skipped_bots += 1
            continue
        t = parse_time(r[i_time])
        if not t:
            continue
        by_day[t.strftime('%Y-%m-%d')][kind] += 1
        if kind == 'click':
            by_hour[t.hour] += 1
        totals[kind] += 1

    if not totals:
        sys.exit('No page or /go requests found — is this the right log file?')

    print(f'\n{"day":<12}{"visits":>8}{"clicks":>8}{"rate":>8}')
    print('-' * 36)
    for day in sorted(by_day):
        v, c = by_day[day]['visit'], by_day[day]['click']
        rate = f'{round(100 * c / v)}%' if v else '—'
        print(f'{day:<12}{v:>8}{c:>8}{rate:>8}')
    print('-' * 36)
    v, c = totals['visit'], totals['click']
    print(f'{"TOTAL":<12}{v:>8}{c:>8}{(f"{round(100 * c / v)}%" if v else "—"):>8}')
    if skipped_bots:
        print(f'\n({skipped_bots} bot/preview requests excluded)')

    if show_hours and by_hour:
        print('\nclicks by hour (UTC)')
        peak = max(by_hour.values())
        for h in range(24):
            n = by_hour.get(h, 0)
            bar = '#' * round(18 * n / peak) if n else ''
            print(f'  {h:02d}:00 {n:>4} {bar}')

    print('\nRequests are not people: reloads count twice, and the ratio is the')
    print('trustworthy number rather than either total on its own.')


if __name__ == '__main__':
    main(sys.argv)
