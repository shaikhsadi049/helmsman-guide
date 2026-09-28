-- =====================================================================
-- 99_verify.sql — কনভেনশন যাচাই (প্রতিটা মাইগ্রেশনের শেষ ধাপ)
--
-- "প্রতিটা টেবিলে অডিট কলাম আছে" — এই দাবিটা নথিতে লিখে রাখা যথেষ্ট নয়।
-- ছয় মাস পর কেউ তাড়াহুড়োয় একটা টেবিল বানাবে আর ss_apply() ডাকতে
-- ভুলে যাবে। এই স্ক্রিপ্ট সেটা ধরে ফেলে এবং মাইগ্রেশন ব্যর্থ করে দেয়।
--
-- CI-তে এটা চালানো বাধ্যতামূলক।
-- =====================================================================

do $verify$
declare
  v_err    text := '';
  v_row    record;
  v_count  integer;
  v_required text[] := array[
    'ss_created_by','ss_created_time','ss_modified_by','ss_modified_time',
    'ss_row_version','ss_active_flag','ss_deleted_flag','ss_deleted_by',
    'ss_deleted_time','ss_client_uuid','ss_device_no','ss_device_time','ss_sync_seq'
  ];
  -- ছাঁচ ও রেজিস্ট্রি নিজে ব্যবসায়িক টেবিল নয়
  v_exempt text[] := array['ss_row_template','ss_table_registry'];
begin
  -- ==================================================================
  -- ১. রেজিস্ট্রিতে নেই এমন টেবিল
  -- ==================================================================
  for v_row in
    select n.nspname as sch, c.relname as tbl
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
     where c.relkind = 'r'
       and n.nspname in ('core','master','prod')
       and c.relname <> all(v_exempt)
       and not exists (
         select 1 from core.ss_table_registry r
          where r.table_schema = n.nspname and r.table_name = c.relname)
     order by 1,2
  loop
    v_err := v_err || format(
      E'\n  [রেজিস্ট্রি নেই] %s.%s — টেবিল বানানোর পর core.ss_apply() ডাকা হয়নি',
      v_row.sch, v_row.tbl);
  end loop;

  -- ==================================================================
  -- ২. বাধ্যতামূলক ss_* কলাম
  -- ==================================================================
  for v_row in
    select r.table_schema as sch, r.table_name as tbl,
           string_agg(x.col, ', ') as missing
      from core.ss_table_registry r
      cross join unnest(v_required) as x(col)
     where not exists (
       select 1 from pg_attribute a
        where a.attrelid = format('%I.%I', r.table_schema, r.table_name)::regclass
          and a.attname = x.col and a.attnum > 0 and not a.attisdropped)
     group by 1,2 order by 1,2
  loop
    v_err := v_err || format(E'\n  [কলাম নেই] %s.%s → %s',
      v_row.sch, v_row.tbl, v_row.missing);
  end loop;

  -- ==================================================================
  -- ৩. অডিট ট্রিগার
  -- ==================================================================
  for v_row in
    select r.table_schema as sch, r.table_name as tbl
      from core.ss_table_registry r
     where not exists (
       select 1 from pg_trigger t
        where t.tgrelid = format('%I.%I', r.table_schema, r.table_name)::regclass
          and t.tgname = 'ss_audit_biu' and not t.tgisinternal)
     order by 1,2
  loop
    v_err := v_err || format(E'\n  [ট্রিগার নেই] %s.%s → ss_audit_biu',
      v_row.sch, v_row.tbl);
  end loop;

  -- ==================================================================
  -- ৪. টেন্যান্ট কলাম ও RLS
  -- ==================================================================
  for v_row in
    select r.table_schema as sch, r.table_name as tbl, r.ss_scope,
           c.relrowsecurity, c.relforcerowsecurity,
           (select count(*) from pg_policy p where p.polrelid = c.oid) as policy_count
      from core.ss_table_registry r
      join pg_class c on c.oid = format('%I.%I', r.table_schema, r.table_name)::regclass
     where r.ss_scope in ('root','tenant','shared')
     order by 1,2
  loop
    if not v_row.relrowsecurity then
      v_err := v_err || format(E'\n  [RLS বন্ধ] %s.%s (scope=%s)',
        v_row.sch, v_row.tbl, v_row.ss_scope);
    end if;
    if not v_row.relforcerowsecurity then
      v_err := v_err || format(E'\n  [FORCE RLS বন্ধ] %s.%s — টেবিলের মালিকও RLS মানবে না',
        v_row.sch, v_row.tbl);
    end if;
    if v_row.policy_count < 4 then
      v_err := v_err || format(E'\n  [পলিসি কম] %s.%s — %s টি আছে, ৪টি (select/insert/update/delete) দরকার',
        v_row.sch, v_row.tbl, v_row.policy_count);
    end if;
  end loop;

  -- tenant scope এ organization_no NOT NULL হতেই হবে, নয়তো সারি
  -- কোনো টেন্যান্টেরই না হয়ে "অনাথ" হয়ে যেতে পারে
  for v_row in
    select r.table_schema as sch, r.table_name as tbl
      from core.ss_table_registry r
      join pg_attribute a
        on a.attrelid = format('%I.%I', r.table_schema, r.table_name)::regclass
       and a.attname = 'organization_no'
     where r.ss_scope = 'tenant' and not a.attnotnull
     order by 1,2
  loop
    v_err := v_err || format(E'\n  [NULL দেওয়া আছে] %s.%s.organization_no — tenant scope এ NOT NULL হতে হবে',
      v_row.sch, v_row.tbl);
  end loop;

  -- ==================================================================
  -- ৫. অ্যাপেন্ড-অনলি টেবিলের রক্ষী
  -- ==================================================================
  for v_row in
    select r.table_schema as sch, r.table_name as tbl
      from core.ss_table_registry r
     where r.is_append_only
       and not exists (
         select 1 from pg_trigger t
          where t.tgrelid = format('%I.%I', r.table_schema, r.table_name)::regclass
            and t.tgname = 'ss_append_only_bud' and not t.tgisinternal)
     order by 1,2
  loop
    v_err := v_err || format(E'\n  [অ্যাপেন্ড-অনলি রক্ষী নেই] %s.%s', v_row.sch, v_row.tbl);
  end loop;

  -- ==================================================================
  -- ৬. প্রাইমারি কী uuid কি না (অফলাইন সিঙ্কের পূর্বশর্ত)
  -- ==================================================================
  for v_row in
    select r.table_schema as sch, r.table_name as tbl, a.attname as col, t.typname
      from core.ss_table_registry r
      join pg_class c on c.oid = format('%I.%I', r.table_schema, r.table_name)::regclass
      join pg_constraint k on k.conrelid = c.oid and k.contype = 'p'
      join pg_attribute a on a.attrelid = c.oid and a.attnum = any(k.conkey)
      join pg_type t on t.oid = a.atttypid
     where t.typname <> 'uuid'
       -- composite কী-তে tracking_mode text থাকা বৈধ (prod.flock, prod.animal)
       and a.attname <> 'tracking_mode'
     order by 1,2
  loop
    v_err := v_err || format(E'\n  [PK uuid নয়] %s.%s.%s → %s (অফলাইনে তৈরি করা যাবে না)',
      v_row.sch, v_row.tbl, v_row.col, v_row.typname);
  end loop;

  -- ==================================================================
  -- ফলাফল
  -- ==================================================================
  if v_err <> '' then
    raise exception E'কনভেনশন যাচাই ব্যর্থ:%', v_err;
  end if;

  select count(*) into v_count from core.ss_table_registry;
  raise notice 'কনভেনশন যাচাই সফল — %টি টেবিল পরীক্ষিত।', v_count;
end
$verify$;

-- সারসংক্ষেপ প্রতিবেদন
select r.ss_scope                                as "পরিসর",
       count(*)                                  as "টেবিল",
       count(*) filter (where r.is_append_only)  as "অ্যাপেন্ড-অনলি"
  from core.ss_table_registry r
 group by rollup (r.ss_scope)
 order by r.ss_scope nulls last;
