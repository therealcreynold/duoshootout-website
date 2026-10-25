#!/usr/bin/env python3
"""The site's gate: run it before every commit that touches a word or a file.

    python3 scripts/lint-site.py              everything, offline
    python3 scripts/lint-site.py --self-test  proves every pattern catches what it should

Ported from the owner's other game sites and trimmed to a holding page: no images, no privacy page,
no app-ads.txt, no sitemap. It needs nothing but Python 3 and never touches the network. What it
fails on, and why each one is here:

  WORDS (every text file in the repository, this one included, README and comments included, because
  the repository itself is public on GitHub):
  - an em or en dash, as a character or as an HTML entity. The house rule: no em or en dash in any
    user-facing string, and a website is nothing but user-facing strings.
  - a protected name: the arcade machine and alley game trademarks, the league abbreviations and
    competitions, the catch phrase, and the names of the developer's other games (on a website those
    names are what a search engine indexes and a lawyer reads). Spelled in pieces, so this file does
    not trip its own scan.
  - the device's name anywhere but a "Designed for iPhone Duo" statement, in the published files.

  THE PUBLISHED FILES (everything _config.yml does not exclude):
  - exactly the files in PUBLISHED, no more and no fewer. A holding page has nothing else to serve,
    and a file added by accident is public the moment it is pushed.
  - a Liquid tag opener or YAML front matter (Jekyll copies a page byte for byte only while it has
    neither; see _config.yml).
  - a <script>, an inline event handler, an iframe, a form, a web font, an @import, any url( in the
    stylesheet, or anything loaded from another host. The site runs no code and fetches nothing.
  - an image of any kind: no game art exists yet, and the page says only what is true today.
  - an external link at all (there is no host on the allowlist), a mailto that is not the contact
    address, a relative URL, or a root relative link or fragment that does not resolve.
  - a page without the doctype, a viewport, a title or the stylesheet, and a home page without its
    canonical URL, without "Coming to the App Store.", or naming a date.

  THE FILES THAT ARE CONTRACTS: CNAME, robots.txt (no Disallow) and _config.yml (its exclude list is
  NOT_PUBLISHED below, exactly), and no .nojekyll.
"""

from __future__ import annotations

import html.parser
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOMAIN = "duoshootout.com"
CONTACT = "info@crindustries.xyz"
PUBLISHED = {"index.html", "404.html", "style.css", "CNAME", "robots.txt"}
NOT_PUBLISHED = {"scripts", "README.md"}            # must agree with _config.yml's exclude list
TEXT_SUFFIXES = {".html", ".css", ".txt", ".yml", ".md", ".py", ".sh", ""}

# Hosts a page may link out to. None: a holding page sends nobody anywhere but the contact address.
LINK_HOSTS: set[str] = set()

# Spelled in pieces so that this file does not fail its own scan (it is scanned like every other
# file). Every piece holding a backslash is a raw string: a plain "\b" is a backspace, and a pattern
# built with one silently matches nothing.
PROTECTED = [
    (re.compile(r"pop[\s-]?a[\s-]?" + "shot", re.I), "a registered trademark (an arcade basketball machine)"),
    (re.compile(r"skee[\s-]?" + "ball", re.I), "a registered trademark (an alley game)"),
    (re.compile(r"\b(" + "N" + "BA|W" + "N" + "BA|N" + "CAA|FI" + "FA|UE" + "FA|M" + "LS" + r")\b"),
     "a league or governing body"),
    (re.compile(r"\b(premier|champions)\s+" + "league" + r"\b|\bworld\s+" + "cup" + r"\b", re.I),
     "a competition's name"),
    (re.compile(r"he['\u2019]?s on " + "fire", re.I), "a catch phrase the house forbids"),
    (re.compile(r"\b(" + "muta" + "bloom|crater" + "gut|turf" + "storm|wen" + "dra" + r")\b", re.I),
     "another of the developer's apps (the site names none of them)"),
    (re.compile(r"\bhalf[\s-]?" + "court" + r"[\s-]?duo\b|\bduo[\s-]?" + "al" + r"ley\b", re.I),
     "another of the developer's apps (the sibling Duo games)"),
]
DASH = re.compile("[\u2013\u2014]|&[mn]dash;|&#(8211|8212|x201[34]);", re.I)
DEVICE = re.compile(r"iphone\s+duo", re.I)
DEVICE_ALLOWED = re.compile(r"Designed for iPhone Duo")
# Months capitalized (so "may" and "march" stay words), seasons either way; "fall" is left out.
DATE = re.compile(r"\b(19|20)\d\d\b|\b(January|February|March|April|May|June|July|August|September|"
                  r"October|November|December)\b|\b([Ss]pring|[Ss]ummer|[Aa]utumn|[Ww]inter)\b")


def published_files() -> list[pathlib.Path]:
    out = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        top = path.relative_to(ROOT).parts[0]
        if top.startswith(".") or top.startswith("_") or top in NOT_PUBLISHED:
            continue
        out.append(path)
    return out


def text_files() -> list[pathlib.Path]:
    out = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(ROOT).parts[:1]:
            continue
        if path.name == ".DS_Store" or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        out.append(path)
    return out


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def check_words(problems: list[str]) -> None:
    published = set(published_files())
    for path in text_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if DASH.search(line):
                problems.append(f"{rel(path)}:{number}: an em or en dash")
            for pattern, why in PROTECTED:
                if pattern.search(line):
                    problems.append(f"{rel(path)}:{number}: {why}")
            if path in published and DEVICE.search(DEVICE_ALLOWED.sub("", line)):
                problems.append(f"{rel(path)}:{number}: the device's name outside 'Designed for iPhone Duo'")
    for path in ROOT.rglob("*"):                      # a file name is as public as a sentence
        if ".git" in path.relative_to(ROOT).parts[:1]:
            continue
        for pattern, why in PROTECTED:
            if pattern.search(path.name):
                problems.append(f"{rel(path)}: {why}, in the file name")


class Page(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.main_text: list[str] = []
        self.in_main = 0

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, {k: (v or "") for k, v in attrs}))
        if tag == "main":
            self.in_main += 1

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main -= 1

    def handle_data(self, data):
        if self.in_main:
            self.main_text.append(data)


def resolve(url: str) -> pathlib.Path | None:
    """A root relative URL to the file GitHub Pages would serve for it, or None."""
    path = url.split("#", 1)[0].split("?", 1)[0]
    if not path.startswith("/"):
        return None
    target = ROOT / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    return target if target.is_file() else None


def check_published(problems: list[str]) -> None:
    have = {rel(p) for p in published_files()}
    for extra in sorted(have - PUBLISHED):
        problems.append(f"{extra} would be published: name it in _config.yml, or add it to PUBLISHED and README.md")
    for missing in sorted(PUBLISHED - have):
        problems.append(f"{missing} is missing")

    css = (ROOT / "style.css").read_text(encoding="utf-8") if (ROOT / "style.css").exists() else ""
    for needle, why in (("url(", "a url( (the site fetches nothing but this file)"),
                        ("@import", "an @import"), ("@font-face", "a web font")):
        if needle in css:
            problems.append(f"style.css: {why}")


def check_pages(problems: list[str]) -> None:
    for path in published_files():
        if path.suffix != ".html":
            continue
        text = path.read_text(encoding="utf-8")
        name = rel(path)
        if text.startswith("---"):
            problems.append(f"{name}: YAML front matter (Jekyll would render this page)")
        if "{" + "{" in text or "{" + "%" in text:
            problems.append(f"{name}: a Liquid tag opener (Jekyll would rewrite this page)")
        if not text.lower().startswith("<!doctype html>"):
            problems.append(f"{name}: does not begin with <!doctype html>")
        if re.search(r"\son[a-z]+\s*=", text, re.I):
            problems.append(f"{name}: an inline event handler (the site runs no code)")
        if "@font-face" in text or "@import" in text or "<style" in text.lower():
            problems.append(f"{name}: inline styles or a web font (everything lives in /style.css)")

        page = Page()
        page.feed(text)
        tags = page.tags
        names = [t for t, _ in tags]
        for banned in ("script", "iframe", "object", "embed", "form", "base"):
            if banned in names:
                problems.append(f"{name}: a <{banned}> (the site runs no code and collects nothing)")
        for banned in ("img", "picture", "svg", "video", "audio", "canvas"):
            if banned in names:
                problems.append(f"{name}: a <{banned}> (no game art exists yet; the site is text)")
        metas = {a.get("name") or a.get("property"): a.get("content", "") for t, a in tags if t == "meta"}
        if "viewport" not in metas:
            problems.append(f"{name}: no viewport meta")
        if "title" not in names:
            problems.append(f"{name}: no <title>")
        links = [a for t, a in tags if t == "link"]
        if not any(a.get("rel") == "stylesheet" and a.get("href") == "/style.css" for a in links):
            problems.append(f"{name}: does not link /style.css")
        canon = [a.get("href", "") for a in links if a.get("rel") == "canonical"]
        if name == "index.html":
            if canon != [f"https://{DOMAIN}/"]:
                problems.append(f"{name}: canonical is {canon}, expected ['https://{DOMAIN}/']")
            main_text = " ".join("".join(page.main_text).split())
            if main_text.count("Coming to the App Store.") != 1:
                problems.append(f"{name}: the page must say 'Coming to the App Store.' exactly once")
            if DATE.search(main_text):
                problems.append(f"{name}: a date ({DATE.search(main_text).group(0)!r}); the page promises none")
        elif canon:
            problems.append(f"{name}: a canonical URL (the 404 is served at every missing path)")

        ids = {a.get("id") for _, a in tags}
        for tag, a in tags:
            for attr in ("href", "src"):
                url = a.get(attr)
                if url is None:
                    continue
                if url.startswith(("http://", "https://", "//")):
                    host = re.sub(r"^(https?:)?//", "", url).split("/", 1)[0]
                    if tag == "link" and a.get("rel") == "canonical":
                        if host != DOMAIN:
                            problems.append(f"{name}: a canonical URL on another host: {url}")
                    elif tag != "a":
                        problems.append(f"{name}: <{tag} {attr}> loads from another host: {url}")
                    elif url.startswith("http://"):
                        problems.append(f"{name}: a plain http link: {url}")
                    elif host not in LINK_HOSTS:
                        problems.append(f"{name}: a link to {host}, which is not on LINK_HOSTS")
                elif url.startswith("mailto:"):
                    if url != f"mailto:{CONTACT}":
                        problems.append(f"{name}: a mailto that is not the contact address: {url}")
                elif url.startswith("#"):
                    if url[1:] and url[1:] not in ids:
                        problems.append(f"{name}: a fragment link to #{url[1:]}, which no element has")
                elif url.startswith("/"):
                    if resolve(url) is None:
                        problems.append(f"{name}: {url} does not resolve to a file here")
                else:
                    problems.append(f"{name}: a relative URL {url!r} (use root relative: the 404 is served at any path)")


def check_contracts(problems: list[str]) -> None:
    cname = (ROOT / "CNAME").read_text().strip() if (ROOT / "CNAME").exists() else None
    if cname != DOMAIN:
        problems.append(f"CNAME is {cname!r}, expected {DOMAIN!r}")

    robots = (ROOT / "robots.txt").read_text() if (ROOT / "robots.txt").exists() else ""
    if re.search(r"^\s*Disallow:\s*\S", robots, re.M):
        problems.append("robots.txt: a Disallow (the domain must stay crawlable)")

    config = (ROOT / "_config.yml").read_text() if (ROOT / "_config.yml").exists() else ""
    excluded = set(re.findall(r"^\s*-\s*(\S+)\s*$", config, re.M))
    if excluded != NOT_PUBLISHED:
        problems.append(f"_config.yml excludes {sorted(excluded)}; this script believes {sorted(NOT_PUBLISHED)}")
    if (ROOT / ".nojekyll").exists():
        problems.append(".nojekyll exists: with Jekyll off, _config.yml's exclude list is ignored")


def self_test() -> list[str]:
    caught = {
        "pop": ["Pop-A-" + "Shot", "pop a " + "shot"],
        "skee": ["Skee-" + "Ball", "skee" + "ball"],
        "league": ["the N" + "BA finals", "a W" + "N" + "BA star", "NC" + "AA bracket", "FI" + "FA rules",
                   "a UE" + "FA night", "an M" + "LS club", "the Premier " + "League", "champions " + "league",
                   "a World " + "Cup final"],
        "phrase": ["He's on " + "fire!", "he\u2019s on " + "fire"],
        "apps": ["like crater" + "gut", "muta" + "bloom's lesson", "Turf" + "storm", "wen" + "dra",
                 "Half Court " + "Duo", "half" + "court" + "duo.com", "Duo Al" + "ley", "duo" + "alley-website"],
    }
    missed = ["ABBA", "nbattery", "unbalanced", "HTML", "on fire", "a mutable bloom", "cratered",
              "stormy turf", "a half court", "a bowling alley", "a cup of tea", "a league of its own",
              "Duo Shootout", "duoshootout.com"]
    problems = []
    for group, needles in caught.items():
        for needle in needles:
            if not any(p.search(needle) for p, _ in PROTECTED):
                problems.append(f"self-test: no pattern catches {needle!r} ({group})")
    for text in missed:
        for p, why in PROTECTED:
            if p.search(text):
                problems.append(f"self-test: {text!r} is caught as {why}, and should not be")
    for needle in ["an em \u2014 dash", "1\u20132", "&m" + "dash;", "&n" + "dash;", "&#82" + "12;", "&#x20" + "13;"]:
        if not DASH.search(needle):
            problems.append(f"self-test: the dash pattern misses {needle!r}")
    if DASH.search("a hyphen-minus is fine, and &middot; too"):
        problems.append("self-test: the dash pattern catches a hyphen")
    if DEVICE.search(DEVICE_ALLOWED.sub("", "Designed for iPhone Duo")):
        problems.append("self-test: the allowed platform statement is refused")
    if not DEVICE.search(DEVICE_ALLOWED.sub("", "the iPhone Duo game")):
        problems.append("self-test: the device's name in prose is not caught")
    for needle in ["in 2027", "this spring", "by December"]:
        if not DATE.search(needle):
            problems.append(f"self-test: the date pattern misses {needle!r}")
    if DATE.search("Coming to the App Store. Stand it up like a laptop."):
        problems.append("self-test: the date pattern catches the page's own words")
    return problems


def main() -> int:
    problems = self_test()
    if "--self-test" in sys.argv:
        for p in problems:
            print(f"FAIL {p}")
        print("self-test: " + ("failed" if problems else "clean"))
        return 1 if problems else 0
    check_words(problems)
    check_published(problems)
    check_pages(problems)
    check_contracts(problems)
    for p in problems:
        print(f"FAIL {p}")
    print("lint-site: " + (f"{len(problems)} problem(s)" if problems else "clean"))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
