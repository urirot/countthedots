# countthedots.click

The landing page for **Count the Dots** — the three-button counter.
The app itself lives in a separate, private repo.

Static HTML, CSS and four PNGs. No build step, no dependencies, no JavaScript
on the landing page itself — the screenshot switcher runs on two radio inputs
and `:checked` selectors rather than a script.

```
index.html        the page
styles.css        palette and type, deliberately matching the app
go/index.html     the click-through redirect — the ONE file you must edit
shot-pad.png      real screenshots, generated from the running app
shot-timeline.png
og.png            1200x630 share card
icon-192/512.png  favicon, same three dots as the app
amplify.yml       build spec (nothing to build)
customHttp.yml    response headers — the cache rules are load-bearing, see below
```

## Before the first deploy

Open `go/index.html` and set `APP_URL` to the app's real URL. That is the only
edit this repo needs. Until it is set, `/go` says so on the page instead of
bouncing visitors to a domain that does not exist.

## How the two numbers work

No analytics script, no cookies, no consent banner. Both numbers come out of
Amplify's own access logs:

| Question | Where it comes from |
|---|---|
| How many people opened the landing page? | requests to `/` |
| How many went on to the app? | requests to `/go` |

That works because every "Open the app" button points at `/go` **on this
domain**, so the click is a real request to our own site before the visitor is
sent onward. An ad blocker cannot suppress it, because there is nothing to
block.

Read them in the Amplify console: **Hosting → Monitoring → Access logs**,
pick a date range, **Download**, then:

```sh
python3 tools/read-logs.py access-logs.csv          # per-day visits, clicks, rate
python3 tools/read-logs.py access-logs.csv --hours  # plus clicks by hour
```

It counts `/` as a visit and `/go` as a click, skips assets, bots and link
previewers, keeps `304`s (a revalidated revisit is still a visit), and finds
the columns by shape rather than by fixed position, since Amplify has changed
that CSV's layout before. If the layout ever changes past recognition it prints
the header row rather than guessing.

**The cache headers in `customHttp.yml` are what make this work, so do not
"tidy" them.** A page served from the *browser's* own cache never reaches the
server and is never logged. So HTML must revalidate, and `/go` is `no-store`
— otherwise a returning visitor's second click is invisible.

Two honest caveats about the numbers:

* **Requests are not people.** One person reloading twice is two rows. Bots and
  link previewers also hit `/`. Treat the numbers as a trend, not a census.
* **The ratio is the useful part.** `/go` ÷ `/` is your click-through rate, and
  that ratio stays meaningful even though neither number is exact.

### The /usage page

`countthedots.click/usage` shows total visits, clicks to the app, the rate between
them, and a per-day chart. It is **generated, not live** — a browser cannot read
Amplify's access logs, so the page is built from the CSV and committed:

```sh
python3 tools/build-usage.py ~/Downloads/access-logs.csv
git add usage && git commit -m "usage: refresh" && git push
```

The page states the date its data runs through, so it can't be mistaken for
real-time. Both tools read through `tools/logs.py`, so "visit" and "click" cannot
come to mean different things in the terminal and on the page.

Chart colours are `--c-visits` / `--c-clicks` in `styles.css`, not the UI palette.
The dark-mode gold is deliberately different from `--yellow`: chart marks have to
sit inside OKLCH lightness 0.48–0.67 against the dark surface and the UI yellow is
0.82. Both pairs were run through a palette validator — blue/gold is also the pair
that survives every kind of colour blindness. Gold falls under 3:1 on the light
surface, which is why the page carries a table of the same figures rather than
relying on the bars alone.

If you later want referrers, uniques and trends on a dashboard, add a cookieless
tool (GoatCounter is free for personal use; Plausible and Umami are the paid
equivalents). Keep it on this page only — the app's whole pitch is that nothing
leaves the device.

## Deploying

Amplify Hosting, connected to this repo's default branch. It picks up
`amplify.yml` automatically; there is no build to configure.

Then **Hosting → Custom domains** to attach `countthedots.click`, which issues
a managed TLS certificate. You will either delegate the domain to Route 53 or
add the validation and ALIAS records at whichever registrar holds it.

## Regenerating the screenshots

They are real captures of the app, not mockups. To refresh them, run the app
locally, seed some believable data, and screenshot at a 390px-wide layout
inside a fixed-size iframe — headless Chrome ignores `--window-size` for the
layout viewport, so an iframe is the only reliable way to get a true phone
width.
