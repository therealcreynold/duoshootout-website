# duoshootout.com

The holding page for **Duo Shootout**, an arcade game of penalty kicks against a goalkeeper that is
being made for a phone that folds (bundle `com.duoshootout.game`, App Store Connect Apple ID
`6826691751`). The game has no code yet. This site exists so the domain, which points at GitHub Pages,
is claimed by a real site from the day the DNS changed, and so anyone who types it finds out what it is.

One page, a 404, one stylesheet. No build step, no framework, no JavaScript, no web fonts, no images and
nothing fetched from another host: every file here is the file that gets served.

| Path | Why it exists |
|---|---|
| `index.html` | The page: the name, what the game is going to be, "Coming to the App Store.", and the contact address |
| `404.html` | Served by GitHub Pages for any other path ("Off target"), at whatever path was asked for |
| `style.css` | Both pages' styles, light and dark |
| `CNAME` | The custom domain, for GitHub Pages |
| `robots.txt` | Allows everything |
| `_config.yml` | The list of things this repository is **not** allowed to publish |
| `scripts/` | The lint, the page photographer and the live checks. Not published |

## What the page says, and why only that

**Every sentence is true today.** The game does not exist yet, so the page says what it is going to be
and nothing it does: the first sentence is the brief's premise (`02-KEEPER-GAME.md`, section 1:
penalty kicks, a goalkeeper, the goal standing up on the raised half, the shot crossing the fold), and
"Coming to the App Store." is the only word about availability. There is no feature list, no date, no
screenshot, no icon (none has been drawn) and no privacy page (there is no app to describe, and the page
collects nothing and runs no code). It says nothing about data at all.

The contact address is **info@crindustries.xyz**, the one the owner's other games and their sites use.
Nothing here needs email at duoshootout.com, so no forwarding address was configured; the domain does
carry Namecheap's default email forwarding records (five `eforward*.registrar-servers.com` MX records
and an SPF `TXT`), which are not GitHub's business and were left alone.

## Words that must never appear on this site

The game's house rules, and they hold here because a web page is what a search engine reads and what a
lawyer is shown, and this repository is public:

- **No em or en dash**, anywhere, as a character or an entity.
- **No protected name**: the arcade basketball machine and alley game trademarks, the league and
  governing body abbreviations, competition names, the catch phrase, any team, league or player name.
- **None of the owner's other games**, by name or by link, the sibling Duo games included.
- **The device's name only as a platform statement** ("Designed for iPhone Duo"), never in prose and
  never as part of the game's name. The page's prose says "a phone that folds".

`scripts/lint-site.py` enforces these over every text file in the repository, this README and its own
source included, with its patterns spelled in pieces so it does not fail its own scan; `--self-test`
proves each pattern still catches what it should and lets near misses through. It also fails on a
script, an iframe, a form, an inline handler, a web font, any `url(` in the stylesheet, any image, an
external link, a mailto that is not the contact address, a link that does not resolve, a missing
title, viewport, stylesheet or canonical URL, a date on the home page, Liquid syntax or front matter,
`CNAME`, `robots.txt` or `_config.yml` drifting from this README, and **any published file that is not
one of the five above**. Run it before every commit:

    python3 scripts/lint-site.py

## What this repository publishes

**Only what `_config.yml` allows.** GitHub Pages deploys every file in a repository by default, so
without it this README and `scripts/` would be public pages. `.nojekyll` cannot help: with Jekyll off
there is no ignore list at all. So Jekyll is on, and `exclude:` names `README.md` and `scripts`. Jekyll
copies both pages byte for byte because neither has front matter or Liquid syntax, and the lint fails
if one ever does. Anything added here is public the moment it is pushed unless it is named in
`_config.yml`; add it there first, and re-run `scripts/check-live.sh` after any change to that file.

## Looking at it

A lint asserts what a file holds; a defect is a fact about what a page draws. Both pages are
photographed before a commit:

    scripts/shoot.sh /tmp/duoshootout-shots

That renders the two pages with headless Brave from **local files only** (the root relative URLs are
rewritten in a temporary copy, never here), at 1280 px and at a 390 px phone width drawn at 2x, in light
and dark, and reports any page wider than its window. A headless window is never narrower than 500 px,
so the phone width is an iframe of exactly 390 px. Then open every slice and read it.

## The DNS

duoshootout.com is registered at Namecheap. These nine records point it at GitHub Pages, the same nine
the owner's other game sites use. An apex domain needs A and AAAA records rather than a CNAME:

| Type | Host | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | therealcreynold.github.io |

All four of each, not one: they are GitHub's edge addresses, and dropping some costs availability
rather than breaking the site outright. Namecheap's parking records on a new domain (a `CNAME www` to
`parkingpage.namecheap.com` and a `URL Redirect @`) go; the email forwarding MX and SPF records stay.
Read what is there before changing anything:

    dig +short @1.1.1.1 duoshootout.com A
    dig +short @1.1.1.1 duoshootout.com AAAA
    dig +short @1.1.1.1 www.duoshootout.com CNAME

## How it was set up

In order, which is also how to rebuild it:

1. **The repository** `therealcreynold/duoshootout-website`, **public** (GitHub Pages on a free account
   serves only public repositories), created empty and pushed from `main`.
2. **Pages**: deploy from the branch `main`, folder `/ (root)`, through the API:

       gh api -X POST repos/therealcreynold/duoshootout-website/pages \
         -f 'source[branch]=main' -f 'source[path]=/'

3. **The custom domain** `duoshootout.com` (the committed `CNAME` agrees):

       gh api -X PUT repos/therealcreynold/duoshootout-website/pages -f cname=duoshootout.com

4. **The DNS** above, at Namecheap.
5. **Wait for GitHub's certificate** to reach `approved`, covering the apex and `www`:

       gh api repos/therealcreynold/duoshootout-website/pages --jq .https_certificate

6. **Enforce HTTPS**:

       gh api -X PUT repos/therealcreynold/duoshootout-website/pages -F https_enforced=true

7. Run `scripts/check-live.sh` until it is clean.

## Checking it actually works

    scripts/check-live.sh

Network, read only. It holds that the home page is 200 over HTTPS and byte for byte this repository's
`index.html`; that `http://`, `https://www` and `http://www` all land on `https://duoshootout.com/`; that
an unknown path is a 404 with the styled page; that `README.md`, `scripts/`, `_config.yml` and
`.gitignore` are **not** served; and that the page agrees with the App Store: it asks Apple's public
lookup for Apple ID `6826691751` and **fails if the game is on sale while the page still says "Coming
to the App Store."**

## When the game exists

**The real site replaces this one**, in this repository, at this domain, built the way the owner's
other game sites are. Before the game can be submitted it needs, at the least:

- **`privacy/index.html`**, the App Store Connect Privacy Policy URL, compiled into the app and named in
  the advertising consent messages; it is the game's own privacy policy, word for word, and the lint
  learns to compare the two;
- **`support/index.html`**, the App Store Connect Support URL, written from the game's code;
- **`app-ads.txt`** at the root, `text/plain`, with `OWNERDOMAIN=duoshootout.com` and the advertising
  network's seller line exactly as its dashboard gives it, never guessed;
- the home page as the App Store Connect **Marketing URL**, the **apex** and not a page, because that is
  where ad networks start the crawl to `app-ads.txt`;
- the game's own icon and screenshots, drawn by the game, once they exist.

Each new file goes into `PUBLISHED` in `scripts/lint-site.py` and into the table at the top of this
README in the same commit, and the image ban comes out when the art exists. On the day the game goes on
sale, "Coming to the App Store." becomes a link to `https://apps.apple.com/app/id6826691751` (no country
code, so each visitor lands in their own storefront); `scripts/check-live.sh` fails until it does.
