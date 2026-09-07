# countthedots.click

The landing page for **Count the Dots** — the three-button counter.
The app itself lives in a separate, private repo.

Static HTML, CSS and four PNGs. No build step and no dependencies. The only
JavaScript is the CloudWatch RUM tag — the screenshot switcher runs on two radio
inputs and `:checked` selectors rather than a script, and `/go` is a plain
redirect.

RUM is on this page only. The app itself stays script-free: "nothing leaves your
device" is a claim about the counter, and it stays literally true. Cookies are
disabled in the RUM config, so nothing is stored in the browser and no consent
banner is owed.

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

## Traffic

Amplify's own **Hosting → Monitoring** tab charts requests over time. For visits
versus click-throughs specifically, `/go` is a real page load, so any page-view
analytics separates the two without custom events — CloudWatch RUM being the
AWS-native option.

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
