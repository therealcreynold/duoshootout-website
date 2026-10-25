#!/usr/bin/env bash
# Photographs every page, so the site is looked at rather than assumed.
#
#     scripts/shoot.sh /some/empty/dir
#
# Writes, for each of the two pages: a desktop (1280 px) and a phone (390 px, drawn at 2x) capture, in
# light and in dark, each the page's FULL height, then cuts each into slices no taller than a screen and
# downscales those to 1100 px (sips -Z 1100), which is what to open and read. Then: read every string,
# check both themes, the phone's gutters and that nothing scrolls sideways. (sips darkens the outermost
# pixel column when it downscales; a thin grey line down a slice's left edge is that, not the page.)
#
# LOCAL FILES ONLY. The pages use root relative URLs ("/style.css"), which is right for GitHub Pages
# (the 404 is served at whatever path was asked for) and wrong for file://, where "/" is the disk's
# root. So the site is copied to a temporary directory and every root relative href and src in the
# COPY is rewritten to a file:// URL inside it, directory links to their index.html. The copy also gets
# one line of script that writes the page's height into an attribute, read back with --dump-dom so the
# capture is exactly as tall as the page. The repository's own files are never touched, and they never
# carry a script.
set -euo pipefail
SITE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:?usage: scripts/shoot.sh OUTPUT_DIR}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
[ -x "$BRAVE" ] || { echo "shoot: headless Brave not found at $BRAVE"; exit 1; }

WORK="$(mktemp -d -t site-shoot)"
trap 'rm -rf "$WORK"' EXIT
COPY="$WORK/site"
rsync -a --exclude .git --exclude scripts "$SITE/" "$COPY/"

python3 - "$COPY" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
def fix(m):
    attr, url = m.group(1), m.group(2)
    path, _, frag = url.partition("#")
    target = root / path.lstrip("/")
    if path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return f'{attr}="file://{target}' + (f"#{frag}" if frag else "") + '"'
probe = ('<script>addEventListener("load",()=>{const d=document.documentElement;'
         'parent.postMessage({h:Math.ceil(d.scrollHeight),w:Math.ceil(d.scrollWidth)},"*")})</script></body>')
for page in root.rglob("*.html"):
    text = page.read_text()
    text = re.sub(r'(href|src)="(/[^"]*)"', fix, text)
    page.write_text(text.replace("</body>", probe))
PY

flags=(--headless --disable-gpu --hide-scrollbars --no-first-run --disable-background-networking
       --disable-component-update --disable-sync)

# THE PAGE IS DRAWN IN AN IFRAME OF THE EXACT WIDTH. A headless browser window is never narrower than
# 500 px, so a "390 px" window lays the page out at 500 and the capture silently clips it; an iframe has
# no such floor, and the page's media queries answer to the iframe's width. The page's height comes back
# from inside the frame by postMessage (file:// frames cannot read each other's documents).
frame() {  # url width height -> a wrapper page holding the url in a frame of that size
    local f="$WORK/frame-$RANDOM.html"
    printf '<!doctype html><html><body style="margin:0;background:#888">' > "$f"
    printf '<iframe src="%s" style="display:block;border:0;width:%spx;height:%spx"></iframe>' "$1" "$2" "$3" >> "$f"
    printf '<script>addEventListener("message",e=>{const d=document.documentElement;' >> "$f"
    printf 'd.dataset.h=e.data.h;d.dataset.w=e.data.w})</script></body></html>' >> "$f"
    echo "$f"
}

shoot() {  # name page width scale scheme(0 dark, 1 light)
    local name="$1" page="$2" width="$3" scale="$4" scheme="$5"
    local url="file://$COPY/$page" dom h w win
    win=$(( width < 500 ? 500 : width ))
    dom=$("$BRAVE" "${flags[@]}" --force-device-scale-factor=1 --blink-settings=preferredColorScheme="$scheme" \
        --window-size="$win,900" --virtual-time-budget=3000 --dump-dom "file://$(frame "$url" "$width" 900)" 2>/dev/null)
    h=$(grep -o 'data-h="[0-9]*"' <<< "$dom" | head -1 | tr -dc 0-9)
    w=$(grep -o 'data-w="[0-9]*"' <<< "$dom" | head -1 | tr -dc 0-9)
    [ -n "$h" ] || { echo "shoot: could not measure $page"; exit 1; }
    # Sideways scrolling is invisible in a capture (the window clips it), so it is measured instead.
    [ "${w:-0}" -le "$width" ] || echo "  OVERFLOW $page at $width px: the page is $w px wide"
    local full="$WORK/$name-full.png"
    "$BRAVE" "${flags[@]}" --force-device-scale-factor="$scale" --blink-settings=preferredColorScheme="$scheme" \
        --window-size="$win,$h" --virtual-time-budget=3000 --screenshot="$full" "file://$(frame "$url" "$width" "$h")" >/dev/null 2>&1
    [ -s "$full" ] || { echo "shoot: no capture of $page"; exit 1; }
    # Slices: each a window onto the full capture, drawn by the same browser (sips cannot crop at an
    # offset reliably). The slice height is in device pixels of the capture.
    local pw=$((width * scale)) ph=$((h * scale)) slice=$((width * scale * 3 / 2)) top=0 n=1
    [ "$slice" -lt 1400 ] && slice=1400
    while [ "$top" -lt "$ph" ]; do
        local hh=$(( ph - top < slice ? ph - top : slice ))
        printf '<!doctype html><body style="margin:0"><img src="file://%s" style="display:block;margin-top:-%spx">' \
            "$full" "$top" > "$WORK/slice.html"
        "$BRAVE" "${flags[@]}" --force-device-scale-factor=1 --window-size="$pw,$hh" \
            --screenshot="$OUT/$name-$n.png" "file://$WORK/slice.html" >/dev/null 2>&1
        sips -Z 1100 "$OUT/$name-$n.png" >/dev/null
        top=$((top + slice)); n=$((n + 1))
    done
    printf '  %-28s %4s x %-5s %s slice(s)\n' "$name" "$width" "$h" "$((n - 1))"
}

for spec in "home:index.html" "404:404.html"; do
    name="${spec%%:*}"; page="${spec#*:}"
    shoot "$name-desktop-light" "$page" 1280 1 1
    shoot "$name-desktop-dark"  "$page" 1280 1 0
    shoot "$name-phone-light"   "$page" 390 2 1
    shoot "$name-phone-dark"    "$page" 390 2 0
done
echo "wrote $(ls "$OUT"/*.png | wc -l | tr -d ' ') slices to $OUT"
