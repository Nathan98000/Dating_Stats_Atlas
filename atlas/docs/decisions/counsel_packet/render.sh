#!/bin/sh
# Renders counsel_packet.md to counsel_packet.docx and counsel_packet.pdf.
#
# Method, recorded 24 September 2026 (Phase 3c, A4). The 12 September files
# were made with pandoc (the DOCX carries pandoc's reference-document
# styles: Compact, BodyText, FirstParagraph) and LibreOffice Writer 26.2.5.2
# (the PDF's producer field), the PDF rendered from the DOCX. Neither tool
# was on this machine on 24 September, so the script takes pandoc from
# $PANDOC or the PATH, and renders the PDF with the first of: soffice
# (the original route), Microsoft Word through AppleScript (the same DOCX,
# a different office suite), or Google Chrome headless from pandoc's HTML.
# The route taken is printed so the report can record it.
set -eu
cd "$(dirname "$0")"
PANDOC="${PANDOC:-pandoc}"
"$PANDOC" counsel_packet.md -o counsel_packet.docx
echo "docx: $("$PANDOC" --version | head -1)"

if command -v soffice >/dev/null 2>&1; then
  soffice --headless --convert-to pdf counsel_packet.docx --outdir . >/dev/null
  echo "pdf: soffice ($(soffice --version | head -1)) from the DOCX"
elif [ -d "/Applications/Microsoft Word.app" ] && [ "${NO_WORD:-}" = "" ]; then
  HERE="$(pwd)"
  osascript - "$HERE" <<'APPLESCRIPT'
on run argv
  set here to item 1 of argv
  tell application "Microsoft Word"
    set d to open file name (here & "/counsel_packet.docx")
    save as d file name (here & "/counsel_packet.pdf") file format format PDF
    close d saving no
  end tell
end run
APPLESCRIPT
  echo "pdf: Microsoft Word (AppleScript) from the DOCX"
else
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  TMP="$(mktemp -d)"
  cat > "$TMP/packet.css" <<'CSS'
body { font-family: Georgia, "Times New Roman", serif; font-size: 11pt; line-height: 1.4; max-width: 46em; margin: 2em auto; }
h1 { font-size: 18pt; } h2 { font-size: 14pt; margin-top: 1.6em; }
table { border-collapse: collapse; font-size: 9pt; width: 100%; }
th, td { border: 1px solid #999; padding: 3px 5px; vertical-align: top; text-align: left; }
code { font-size: 90%; }
@page { size: A4; margin: 18mm; }
CSS
  "$PANDOC" -s counsel_packet.md --css "$TMP/packet.css" --embed-resources \
    --metadata pagetitle="Dating Stats Atlas — data licensing and publication review" \
    -o "$TMP/packet.html"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$(pwd)/counsel_packet.pdf" "file://$TMP/packet.html" 2>/dev/null
  rm -rf "$TMP"
  echo "pdf: Google Chrome headless from pandoc's HTML"
fi
