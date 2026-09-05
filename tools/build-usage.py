#!/usr/bin/env python3
"""Generate usage/index.html from an Amplify access-log CSV.

    python3 tools/build-usage.py ~/Downloads/access-logs.csv
    git add usage && git commit -m "usage: refresh" && git push

A browser cannot read Amplify's access logs, so the page is generated rather
than live. It says which date the data runs through, so it is never mistaken
for real-time.

  visit = a request for the landing page
  click = a request for /go, which only happens when someone presses an
          "Open the app" button
"""
import io, os, sys, html
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs

W, H = 520, 230
M = {'top': 22, 'right': 10, 'bottom': 26, 'left': 34}


def nice_step(peak, target=4):
    if peak <= 0:
        return 1
    raw = peak / target
    pow10 = 10 ** len(str(int(raw))) // 10 or 1
    for f in (1, 2, 2.5, 5, 10):
        v = max(1, round(pow10 * f))
        if v >= raw:
            return v
    return max(1, round(pow10 * 10))


def bar(x, y, w, h, r=4):
    """Square at the baseline, rounded at the data end — the mark spec."""
    r = max(0, min(r, w / 2, h))
    return (f'M{x:.1f} {y + h:.1f}'
            f'L{x:.1f} {y + r:.1f}Q{x:.1f} {y:.1f} {x + r:.1f} {y:.1f}'
            f'L{x + w - r:.1f} {y:.1f}Q{x + w:.1f} {y:.1f} {x + w:.1f} {y + r:.1f}'
            f'L{x + w:.1f} {y + h:.1f}Z')


def chart(series):
    """series: [(date_str, visits, clicks)] — grouped bars, one shared axis."""
    n = len(series)
    iw = W - M['left'] - M['right']
    ih = H - M['top'] - M['bottom']
    peak = max([max(v, c) for _, v, c in series] + [1])
    step = nice_step(peak)
    top = max(step, -(-peak // step) * step)
    y0 = M['top'] + ih

    def y(val):
        return y0 - (val / top) * ih

    slot = iw / n
    bw = max(1.5, min(14, (slot - 6) / 2))          # 2px gap inside each pair
    out = []

    for v in range(0, top + 1, step):               # recessive grid
        py = y(v)
        cls = 'u-base' if v == 0 else 'u-grid'
        out.append(f'<line class="{cls}" x1="{M["left"]}" x2="{M["left"] + iw:.1f}" '
                   f'y1="{py:.1f}" y2="{py:.1f}"/>')
        out.append(f'<text class="u-y" x="{M["left"] - 8}" y="{py + 3.5:.1f}" '
                   f'text-anchor="end">{v}</text>')

    every = max(1, -(-n // 6))
    peak_i = max(range(n), key=lambda i: series[i][1])

    for i, (d, vis, clk) in enumerate(series):
        cx = M['left'] + slot * i + slot / 2
        for j, (val, key, name) in enumerate(((vis, 'visits', 'visits'),
                                              (clk, 'clicks', 'clicks'))):
            bx = cx - bw - 1 + j * (bw + 2)
            bh = max(0.0, y0 - y(val))
            if bh > 0:
                out.append(
                    f'<path class="u-bar u-{key}" d="{bar(bx, y(val), bw, bh)}">'
                    f'<title>{d} — {val} {name}</title></path>')
        if i % every == 0 or i == n - 1:
            label = d[5:].replace('-', '/')
            anchor = 'end' if i == n - 1 else ('start' if i == 0 else 'middle')
            lx = M['left'] + iw if i == n - 1 else (M['left'] if i == 0 else cx)
            out.append(f'<text class="u-x" x="{lx:.1f}" y="{H - 8}" '
                       f'text-anchor="{anchor}">{label}</text>')

    # one direct label, on the busiest day only — never a number on every bar
    d, vis, _ = series[peak_i]
    px = M['left'] + slot * peak_i + slot / 2 - bw / 2 - 1
    out.append(f'<text class="u-peak" x="{px:.1f}" y="{y(vis) - 7:.1f}" '
               f'text-anchor="middle">{vis}</text>')

    return (f'<svg class="u-chart" viewBox="0 0 {W} {H}" role="img" '
            f'aria-labelledby="chart-desc">' + ''.join(out) + '</svg>')


def page(body, stamp):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Usage — Count the Dots</title>
<meta name="description" content="Visits and click-throughs for countthedots.click.">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#f9f9f7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d0d0d" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../icon-192.png" sizes="192x192" type="image/png">
<link rel="stylesheet" href="../styles.css?v=3">
</head>
<body>
<div class="wrap">
  <header class="hero u-hero">
    <div class="dots dots-sm" aria-hidden="true"><i></i><i></i><i></i></div>
    <h1 class="u-h1">Usage</h1>
    <p class="lede u-lede">How <a href="/">countthedots.click</a> is doing.
      Counted from the server's own logs — no tracking script, no cookies.</p>
  </header>
{body}
  <footer>
    <p class="footnote">Data through {stamp}. This page is generated from the access
      log by hand, so it is a snapshot, not a live dashboard.
      <strong>Requests are not people</strong> — one person reloading counts twice,
      so the rate is the number worth trusting.</p>
  </footer>
</div>
</body>
</html>
'''


def empty():
    return page('''  <section>
    <p>No data yet. Download the access log from Amplify
      (<em>Hosting → Monitoring → Access logs</em>) and run:</p>
    <p><code>python3 tools/build-usage.py access-logs.csv</code></p>
  </section>
''', 'nothing yet')


def build(path):
    data = logs.read(path)
    days = data['days']
    if not days:
        return empty()

    lo, hi = min(days), max(days)
    d0 = date.fromisoformat(lo)
    d1 = date.fromisoformat(hi)
    series = []
    d = d0
    while d <= d1:                        # keep quiet days, or the chart lies
        k = d.isoformat()
        c = days.get(k, {})
        series.append((k, c.get('visit', 0), c.get('click', 0)))
        d += timedelta(days=1)

    tv = data['totals']['visit']
    tc = data['totals']['click']
    rate = f'{round(100 * tc / tv)}%' if tv else '—'

    tiles = ''.join(
        f'<div class="u-tile"><b>{v}</b><span>{k}</span></div>'
        for k, v in (('total visits', f'{tv:,}'),
                     ('clicks to the app', f'{tc:,}'),
                     ('click-through rate', rate),
                     ('days counted', f'{len(series):,}')))

    rows = ''.join(
        f'<tr><td>{d}</td><td>{v}</td><td>{c}</td>'
        f'<td>{(str(round(100 * c / v)) + "%") if v else "—"}</td></tr>'
        for d, v, c in reversed(series))

    body = f'''  <section>
    <div class="u-tiles">{tiles}</div>
  </section>

  <section>
    <p class="label">Visits and clicks per day</p>
    <p class="sr-only" id="chart-desc">Grouped bars, one pair per day: visits and
      clicks to the app, on a shared count axis. The same figures are in the table
      below.</p>
    <div class="u-legend">
      <span><i class="u-key u-visits" aria-hidden="true"></i>Visits</span>
      <span><i class="u-key u-clicks" aria-hidden="true"></i>Clicks to the app</span>
    </div>
    {chart(series)}
    <details class="u-table">
      <summary>The same numbers as a table</summary>
      <table>
        <thead><tr><th>Day</th><th>Visits</th><th>Clicks</th><th>Rate</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </details>
  </section>
'''
    return page(body, hi)


def main(argv):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'usage', 'index.html')
    if len(argv) < 2:
        sys.exit(__doc__)
    try:
        doc = build(argv[1])
    except logs.LayoutError as e:
        print('Could not find the time and path columns. Headers were:')
        for h in e.headers:
            print('   ', h)
        sys.exit('\nSend me this header line and I will teach the parser the layout.')
    io.open(out, 'w', encoding='utf-8').write(doc)
    print('wrote', os.path.normpath(out))


if __name__ == '__main__':
    main(sys.argv)
