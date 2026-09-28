-- =====================================================================
-- rls_test.sql — টেন্যান্ট পৃথকীকরণের পরীক্ষা
--
-- এটা আলাদা ফাইল কারণ এখানে ভূমিকা বদলাতে হয় (SET ROLE farmerp_app)।
-- superuser সর্বদা RLS বাইপাস করে, তাই superuser দিয়ে পরীক্ষা করলে
-- কিছুই প্রমাণ হয় না — এই ভুলটা খুব সাধারণ।
-- =====================================================================

\set ON_ERROR_STOP on

-- দুই খামারের no সংগ্রহ
select organization_no as org1 from core.organization where org_code = 'KHAMAR01' \gset
select organization_no as org2 from core.organization where org_code = 'KHAMAR02' \gset

-- সিকোয়েন্স ও ফাংশনের অনুমতি (ss_apply টেবিল পর্যায়ে দেয়, এগুলো আলাদা)
grant usage on schema core, master, prod to farmerp_app;

\echo ''
\echo '── ১. superuser হিসেবে: সব খামার দেখা যায় (RLS বাইপাস) ──'
select count(*) as "মোট খামার (superuser)" from core.farm;

\echo ''
\echo '── ২. farmerp_app হিসেবে, খামার ১ এর প্রসঙ্গে ──'
set role farmerp_app;
select set_config('app.organization_no', :'org1', false) is not null as ctx_set;
select count(*) as "দৃশ্যমান খামার" from core.farm;
select count(*) as "দৃশ্যমান ইউনিট" from prod.production_unit;
select org_name as "দৃশ্যমান প্রতিষ্ঠান" from core.organization;

\echo ''
\echo '── ৩. একই ভূমিকা, কিন্তু খামার ২ এর প্রসঙ্গে ──'
select set_config('app.organization_no', :'org2', false) is not null as ctx_set;
select count(*) as "দৃশ্যমান খামার" from core.farm;
select count(*) as "দৃশ্যমান ইউনিট" from prod.production_unit;
select org_name as "দৃশ্যমান প্রতিষ্ঠান" from core.organization;

\echo ''
\echo '── ৪. প্রসঙ্গ ছাড়া (fail-closed হওয়া উচিত) ──'
select set_config('app.organization_no', '', false) is not null as ctx_cleared;
select count(*) as "দৃশ্যমান খামার" from core.farm;
select count(*) as "দৃশ্যমান ইউনিট" from prod.production_unit;
select count(*) as "দৃশ্যমান দৈনিক লগ" from prod.daily_log;

\echo ''
\echo '── ৫. গ্লোবাল মাস্টার ডেটা প্রসঙ্গ ছাড়াও পড়া যায় (shared scope) ──'
select count(*) as "প্রজাতি" from master.species;
select count(*) as "জাত" from master.breed;

\echo ''
\echo '── ৬. অন্য টেন্যান্টের নামে সারি ঢোকানোর চেষ্টা ──'
select set_config('app.organization_no', :'org1', false) is not null as ctx_set;
do $$
begin
  begin
    insert into core.farm (organization_no, farm_code, farm_name)
    values (current_setting('app.organization_no')::uuid, 'X1', 'বৈধ খামার');
    raise notice '   ✔ নিজের টেন্যান্টে ঢোকানো গেছে';
  exception when others then
    raise exception '   ✘ নিজের টেন্যান্টে ঢোকানো যায়নি: %', sqlerrm;
  end;
end $$;

do $$
declare v_other uuid;
begin
  select organization_no into v_other from core.organization where organization_no <> current_setting('app.organization_no')::uuid limit 1;
  if v_other is null then
    -- RLS এর কারণেই অন্য org দেখা যাচ্ছে না; সংকেত দিয়ে খুঁজি
    v_other := '00000000-0000-0000-0000-0000000000ff'::uuid;
  end if;
  begin
    insert into core.farm (organization_no, farm_code, farm_name)
    values (v_other, 'X2', 'অন্যের খামার');
    raise exception '   ✘ ব্যর্থ: অন্য টেন্যান্টের নামে সারি ঢোকানো গেল!';
  exception
    when insufficient_privilege then raise notice '   ✔ RLS আটকে দিয়েছে (insufficient_privilege)';
    when foreign_key_violation  then raise notice '   ✔ আটকে দিয়েছে (foreign_key_violation)';
  end;
end $$;

reset role;
\echo ''
\echo '✔ RLS পরীক্ষা শেষ'
