#!/usr/bin/env bash
# Checks the LIVE site, once DNS, GitHub Pages and HTTPS are set up (README.md, "How it was set up").
#
#     scripts/check-live.sh
#
# Network, read only: curl against the domain and one App Store lookup. Changes nothing. Run it after
# every push and after any change to _config.yml. Every line it prints is PASS or FAIL; it exits
# non-zero on any FAIL.
#
# What it holds, and why:
#   - the home page serves 200 over HTTPS (curl refuses a certificate that does not cover the name),
#     and byte for byte this repository's index.html (a push that did not deploy looks fine in a
#     browser);
#   - plain HTTP, www over HTTPS and www over HTTP all land on the HTTPS apex;
#   - an unknown path serves the styled 404 with a 404 status;
#   - README.md, scripts/, _config.yml and .gitignore are NOT served (_config.yml's exclude list is
#     what keeps them off the site);
#   - THE "COMING" LINE AGREES WITH THE APP STORE. A sibling site once said "Coming soon" for three
#     days after its game went on sale. This asks Apple's public lookup whether the app is on sale
#     and fails while the home page still says it is coming, which is the day this holding page
#     should give way to the real site.
set -uo pipefail
SITE="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="duoshootout.com"
HOST="https://$DOMAIN"
APPLE_ID="6826691751"          # App Store Connect's Apple ID for this game
NOT_FOUND="Off target"         # the 404 page's heading
fails=0
pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails + 1)); }

status() { curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$1" 2>/dev/null; }
header() { curl -sSI --max-time 20 "$1" 2>/dev/null | tr -d '\r' | awk -v h="$(tr A-Z a-z <<< "$2")" \
    'BEGIN{FS=": "} tolower($1)==h {print $2}' | tail -1; }
lands() { curl -sS -o /dev/null -L --max-redirs 5 -w '%{http_code} %{url_effective}' --max-time 20 "$1" 2>/dev/null; }

for path in / /style.css /robots.txt; do
    code=$(status "$HOST$path")
    [ "$code" = 200 ] && pass "$path is 200 over HTTPS" || fail "$path is $code over HTTPS, expected 200"
done

if curl -sS --max-time 20 "$HOST/" 2>/dev/null | cmp -s - "$SITE/index.html"; then
    pass "the served home page is this repository's index.html, byte for byte"
else
    fail "the served home page differs from index.html (not deployed yet, or the wrong branch)"
fi

type=$(header "$HOST/" content-type)
case "$type" in text/html*) pass "the home page is $type" ;; *) fail "the home page is '$type', expected text/html" ;; esac

loc=$(header "http://$DOMAIN/" location)
[ "$loc" = "$HOST/" ] && pass "http:// redirects to the HTTPS apex" || fail "http:// goes to '$loc', expected $HOST/"
loc=$(header "https://www.$DOMAIN/" location)
[ "$loc" = "$HOST/" ] && pass "https://www redirects to the apex" || fail "https://www goes to '$loc', expected $HOST/"
end=$(lands "http://www.$DOMAIN/")
[ "$end" = "200 $HOST/" ] && pass "http://www lands on the HTTPS apex" || fail "http://www lands on '$end', expected 200 $HOST/"

code=$(status "$HOST/no-such-page-$$")
body=$(curl -sS --max-time 20 "$HOST/no-such-page-$$" 2>/dev/null)
if [ "$code" = 404 ] && grep -q "$NOT_FOUND" <<< "$body"; then pass "an unknown path serves the styled 404"
else fail "an unknown path is $code$(grep -q "$NOT_FOUND" <<< "$body" || echo ', not the styled 404')"; fi

for path in /README.md /scripts/lint-site.py /scripts/check-live.sh /scripts/shoot.sh /_config.yml /.gitignore; do
    code=$(status "$HOST$path")
    [ "$code" = 404 ] && pass "$path is not published" || fail "$path is $code: it is PUBLIC (see _config.yml)"
done

# The App Store's own answer. An empty result means not on sale in the US storefront (yet).
count=$(curl -sS --max-time 20 "https://itunes.apple.com/lookup?id=$APPLE_ID" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("resultCount", 0))' 2>/dev/null)
says_coming=$(grep -c "Coming to the App Store" "$SITE/index.html")
if [ -z "$count" ]; then
    fail "could not ask the App Store whether the game is on sale"
elif [ "$count" -gt 0 ] && [ "$says_coming" -gt 0 ]; then
    fail "the game is ON SALE and index.html still says 'Coming to the App Store'. README.md, 'When the game exists'."
else
    pass "the home page agrees with the App Store (on sale: $([ "$count" -gt 0 ] && echo yes || echo no))"
fi

echo
[ "$fails" -eq 0 ] && echo "check-live: clean" || echo "check-live: $fails failure(s)"
[ "$fails" -eq 0 ]
