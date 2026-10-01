get(){ # $1 path suffix, $2 out
 page="https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/xauusd/$1"
 curl -sS -c cj.txt -b cj.txt "$page" -o p.html
 tk=$(grep -oE 'name="tk" id="tk" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 d=$(grep -oE 'name="date" id="date" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 dm=$(grep -oE 'name="datemonth" id="datemonth" value="[^"]+' p.html | head -1 | sed 's/.*value="//')
 curl -sS -c cj.txt -b cj.txt -e "$page" -X POST https://www.histdata.com/get.php \
   --data "tk=$tk&date=$d&datemonth=$dm&platform=ASCII&timeframe=M1&fxpair=XAUUSD" -o "hd/$2.zip"
 ls -la hd/$2.zip; sleep 2
}
get 2024 2024; get 2025 2025
for m in 1 2 3 4 5 6 7 8 9; do get 2026/$m 2026_$m; done
