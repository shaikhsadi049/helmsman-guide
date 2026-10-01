get(){ page="https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/xauusd/$1"
 curl -sS -c cj.txt -b cj.txt "$page" -o p.html
 tk=$(grep -oE 'name="tk" id="tk" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 d=$(grep -oE 'name="date" id="date" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 dm=$(grep -oE 'name="datemonth" id="datemonth" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 curl -sS -c cj.txt -b cj.txt -e "$page" -X POST https://www.histdata.com/get.php \
   --data "tk=$tk&date=$d&datemonth=$dm&platform=ASCII&timeframe=T&fxpair=XAUUSD" -o "hdt/$2.zip"
 ls -la hdt/$2.zip; sleep 1; }
mkdir -p hdt
for y in 2025 2026; do for m in 1 2 3 4 5 6 7 8 9 10 11 12; do [ $y = 2026 ] && [ $m -gt 9 ] && break; get $y/$m ${y}_$m; done; done
