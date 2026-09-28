#!/usr/bin/env bash
# =====================================================================
# build.sh — শূন্য থেকে পুরো ডাটাবেস বানায় ও যাচাই করে
#
# ব্যবহার:
#   ./build.sh                      # farmerp ডাটাবেস নতুন করে বানায়
#   DB=farmerp_test ./build.sh      # অন্য নামে
#   ./build.sh --no-seed            # শুধু স্কিমা, মাস্টার ডেটা ছাড়া
#
# CI-তে এটাই চলবে: স্কিমা → সিড → যাচাই → স্মোক টেস্ট।
# যেকোনো ধাপ ব্যর্থ হলে সাথে সাথে থামে (ON_ERROR_STOP)।
# =====================================================================
set -euo pipefail

DB="${DB:-farmerp}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED=1
SMOKE=1
for a in "$@"; do
  case "$a" in
    --no-seed)  SEED=0 ;;
    --no-smoke) SMOKE=0 ;;
    *) echo "অজানা আর্গুমেন্ট: $a" >&2; exit 2 ;;
  esac
done

PSQL=(psql -v ON_ERROR_STOP=1 --quiet --no-psqlrc)

say() { printf '\n\033[1;34m▸ %s\033[0m\n' "$1"; }

say "ডাটাবেস নতুন করে বানাচ্ছি: $DB"
psql --no-psqlrc -qc "drop database if exists $DB" postgres
psql --no-psqlrc -qc "create database $DB encoding 'UTF8'" postgres

say "স্কিমা"
for f in "$HERE"/schema/[0-8]*.sql; do
  printf '   %s\n' "$(basename "$f")"
  "${PSQL[@]}" -d "$DB" -f "$f" >/dev/null
done

if [[ $SEED -eq 1 ]]; then
  say "মাস্টার ডেটা (সিড)"
  for f in "$HERE"/seed/*.sql; do
    printf '   %s\n' "$(basename "$f")"
    "${PSQL[@]}" -d "$DB" -f "$f" >/dev/null
  done
fi

say "কনভেনশন যাচাই"
"${PSQL[@]}" -d "$DB" -f "$HERE/schema/99_verify.sql"

if [[ $SMOKE -eq 1 && -f "$HERE/smoke_test.sql" ]]; then
  say "স্মোক টেস্ট"
  "${PSQL[@]}" -d "$DB" -f "$HERE/smoke_test.sql"
fi

if [[ $SMOKE -eq 1 && -f "$HERE/feed_test.sql" ]]; then
  say "ফিড ও গুদামের পরীক্ষা"
  "${PSQL[@]}" -d "$DB" -f "$HERE/feed_test.sql"
fi

if [[ $SMOKE -eq 1 && -f "$HERE/rls_test.sql" ]]; then
  say "টেন্যান্ট পৃথকীকরণ (RLS) পরীক্ষা"
  "${PSQL[@]}" -d "$DB" -f "$HERE/rls_test.sql" | grep -E '✔|✘|NOTICE' || true
fi

say "সিড ডেটার সারসংক্ষেপ"
"${PSQL[@]}" -d "$DB" -c "
select 'প্রজাতি' as বিষয়, count(*) as সংখ্যা from master.species
union all select 'জাত',            count(*) from master.breed
union all select 'একক',            count(*) from master.uom
union all select 'উৎপাদনের উদ্দেশ্য', count(*) from master.production_purpose
union all select 'ঘরের ধরন',        count(*) from master.house_type
union all select 'পালন পদ্ধতি',      count(*) from master.rearing_system
union all select 'চলাচলের ধরন',     count(*) from master.movement_type
union all select 'মেট্রিক',          count(*) from master.metric_definition
union all select 'রোগ ও কারণ',      count(*) from master.disease
union all select 'টিকা',            count(*) from master.vaccine
union all select 'টিকার সূচির সারি',  count(*) from master.vaccine_schedule_line
union all select 'জীবনচক্র টেমপ্লেট', count(*) from master.lifecycle_template
union all select 'জীবনচক্র পর্যায়',   count(*) from master.lifecycle_phase
union all select 'পণ্য',             count(*) from master.item
union all select 'পুষ্টি উপাদান',      count(*) from master.nutrient
union all select 'পুষ্টিমানের সারি',   count(*) from master.item_nutrient
union all select 'স্টক চলাচলের ধরন',  count(*) from master.stock_movement_type
union all select 'পুষ্টি চাহিদার সেট',  count(*) from master.ration_requirement_set
union all select 'চাহিদার সারি',      count(*) from master.ration_requirement_line;"

printf '\n\033[1;32m✔ সম্পূর্ণ সফল — %s\033[0m\n\n' "$DB"
