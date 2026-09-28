-- =====================================================================
-- dev_roles.sql — ডেভেলপমেন্টে কানেক্ট করার ভূমিকা
--
-- সমস্যা: farmerp_app ও farmerp_readonly হলো NOLOGIN ভূমিকা — এগুলো
-- অনুমতির পাত্র, কানেক্ট করার অ্যাকাউন্ট নয়। তাই GUI টুল দিয়ে ওদের নামে
-- ঢুকে RLS আসলে কী আটকাচ্ছে তা দেখা যায় না।
--
-- এই স্ক্রিপ্ট দুটো লগইন-সক্ষম ভূমিকা বানায় যেগুলো ওই অনুমতি উত্তরাধিকার পায়।
--
-- ব্যবহার:
--   psql -d farmerp -v app_password='আপনার_পাসওয়ার্ড' -f dev_roles.sql
--
-- ⚠ শুধু লোকাল ডেভেলপমেন্টের জন্য। প্রোডাকশনে পাসওয়ার্ড কখনো স্ক্রিপ্টে
--   বা git-এ রাখবেন না — পরিবেশের secret ব্যবস্থাপনা ব্যবহার করুন।
-- =====================================================================

\if :{?app_password}
\else
  \echo ''
  \echo 'ত্রুটি: app_password দেওয়া হয়নি।'
  \echo 'ব্যবহার:  psql -d farmerp -v app_password=''...'' -f dev_roles.sql'
  \echo ''
  \quit
\endif

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'farmerp_dev') then
    create role farmerp_dev login inherit in role farmerp_app;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'farmerp_dev_ro') then
    create role farmerp_dev_ro login inherit in role farmerp_readonly;
  end if;
end $$;

alter role farmerp_dev    password :'app_password';
alter role farmerp_dev_ro password :'app_password';

-- ভবিষ্যতে বানানো টেবিলেও অনুমতি যেন স্বয়ংক্রিয়ভাবে যায়।
-- (ss_apply() প্রতিটা টেবিলে গ্রান্ট দেয়, কিন্তু কেউ ss_apply ছাড়া
--  টেবিল বানালে 99_verify ধরবে — এটা অতিরিক্ত জাল।)
alter default privileges in schema core, master, prod
  grant select, insert, update, delete on tables to farmerp_app;
alter default privileges in schema core, master, prod
  grant select on tables to farmerp_readonly;
alter default privileges in schema core, master, prod
  grant usage, select on sequences to farmerp_app;

\echo ''
\echo 'তৈরি হয়েছে:'
\echo '  farmerp_dev     — অ্যাপের মতো (RLS প্রযোজ্য)'
\echo '  farmerp_dev_ro  — শুধু পড়ার (RLS প্রযোজ্য)'
\echo ''
\echo 'কানেক্ট করার পর প্রসঙ্গ বসাতে ভুলবেন না, নইলে কোনো সারিই দেখবেন না:'
\echo '  SET app.organization_no = ''<uuid>'';'
\echo ''

select org_code as "খামারের সংকেত", organization_no as "organization_no"
  from core.organization order by org_code;
