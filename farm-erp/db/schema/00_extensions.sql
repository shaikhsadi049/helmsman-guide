-- =====================================================================
-- 00_extensions.sql — এক্সটেনশন, স্কিমা ও ভূমিকা (roles)
-- Farm ERP — বাংলাদেশের সমন্বিত খামারের জন্য
-- =====================================================================

create extension if not exists pgcrypto;   -- gen_random_bytes() — uuidv7 এর জন্য
create extension if not exists citext;     -- কেস-সংবেদনশীল নয় এমন কোড/ইমেইল
create extension if not exists btree_gist; -- uuid + daterange একসাথে exclusion constraint-এ

-- ---------------------------------------------------------------------
-- স্কিমা বিভাজন
--   core   : টেন্যান্ট, খামার কাঠামো, ব্যবহারকারী, অডিট মেশিনারি
--   master : মাস্টার ডেটা (প্রজাতি, জাত, একক, রোগ) — গ্লোবাল + টেন্যান্ট
--   prod   : উৎপাদন (ইউনিট, চলাচল, দৈনিক লগ)
--   inv    : গুদাম ও স্টক
--   feed   : রেশন ফরমুলেশন
-- ---------------------------------------------------------------------
create schema if not exists core;
create schema if not exists master;
create schema if not exists prod;
create schema if not exists inv;
create schema if not exists feed;

-- ---------------------------------------------------------------------
-- অ্যাপ্লিকেশন ভূমিকা।
-- গুরুত্বপূর্ণ: অ্যাপ কখনো superuser দিয়ে কানেক্ট করবে না, কারণ
-- superuser ডিফল্টভাবে RLS বাইপাস করে। মাইগ্রেশন/সিড superuser দিয়ে,
-- রানটাইম farmerp_app দিয়ে।
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'farmerp_app') then
    create role farmerp_app nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'farmerp_readonly') then
    create role farmerp_readonly nologin;
  end if;
end $$;

grant usage on schema core, master, prod, inv, feed to farmerp_app, farmerp_readonly;
