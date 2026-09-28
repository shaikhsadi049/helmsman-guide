-- =====================================================================
-- 01_core_audit.sql — পরিচয়, অডিট ও টেন্যান্ট মেশিনারি
--
-- এই ফাইলটাই প্রকল্পের মেরুদণ্ড। এখানে ঠিক করা হয়েছে:
--   ১. প্রাইমারি কী কেমন হবে (UUIDv7 — অফলাইনে তৈরি করা যায়)
--   ২. প্রতিটা টেবিলে কোন কোন ss_* কলাম বাধ্যতামূলক
--   ৩. সেগুলো কে বসাবে (ডাটাবেস ট্রিগার, অ্যাপ কোড নয়)
--   ৪. টেন্যান্ট পৃথকীকরণ কীভাবে জোর করে আদায় হবে (RLS)
-- =====================================================================

-- ---------------------------------------------------------------------
-- ১. UUIDv7
--
-- কেন integer auto-increment নয়:
--   অফলাইন-ফার্স্ট অ্যাপে মোবাইল নেট ছাড়া রেকর্ড তৈরি করে, তখন সার্ভার
--   সিকোয়েন্স পাওয়া যায় না। UUID ডিভাইসেই তৈরি হয়, কোলিশন নেই।
-- কেন v4 নয়, v7:
--   v7 এর প্রথম ৪৮ বিট = ইউনিক্স মিলিসেকেন্ড, তাই কী গুলো সময় অনুসারে
--   সাজানো থাকে। ফলে B-tree ইনডেক্সে র‍্যান্ডম ইনসার্টের পেজ-স্প্লিট হয় না
--   — বড় টেবিলে v4 এর তুলনায় অনেক দ্রুত।
--
-- PostgreSQL 18 এ uuidv7() বিল্ট-ইন। এই ফাংশনটা PG 13–17 এর জন্য,
-- এবং PG 18 এ গেলে নিচের বডি বদলে শুধু `select uuidv7()` করলেই হবে।
-- ---------------------------------------------------------------------
create or replace function core.uuidv7()
returns uuid
language plpgsql
volatile
as $$
declare
  v_ms    bigint;
  v_bytes bytea;
begin
  v_ms    := (extract(epoch from clock_timestamp()) * 1000)::bigint;
  v_bytes := gen_random_bytes(16);

  -- byte 0..5 = 48-bit unix timestamp (big endian)
  v_bytes := set_byte(v_bytes, 0, ((v_ms >> 40) & 255)::int);
  v_bytes := set_byte(v_bytes, 1, ((v_ms >> 32) & 255)::int);
  v_bytes := set_byte(v_bytes, 2, ((v_ms >> 24) & 255)::int);
  v_bytes := set_byte(v_bytes, 3, ((v_ms >> 16) & 255)::int);
  v_bytes := set_byte(v_bytes, 4, ((v_ms >>  8) & 255)::int);
  v_bytes := set_byte(v_bytes, 5, ( v_ms        & 255)::int);

  -- byte 6 উচ্চ নিবল = version 7 (0111)
  v_bytes := set_byte(v_bytes, 6, ((get_byte(v_bytes, 6) & 15) | 112));
  -- byte 8 উচ্চ দুই বিট = variant 10 (RFC 9562)
  v_bytes := set_byte(v_bytes, 8, ((get_byte(v_bytes, 8) & 63) | 128));

  return encode(v_bytes, 'hex')::uuid;
end
$$;

comment on function core.uuidv7() is
  'RFC 9562 UUIDv7 — সময়-ক্রমানুসারী, অফলাইনে নিরাপদে তৈরিযোগ্য প্রাইমারি কী।';

-- ---------------------------------------------------------------------
-- ২. সেশন প্রসঙ্গ (session context)
--
-- অ্যাপ প্রতিটা কানেকশনে এই দুটো বসাবে:
--   SET LOCAL app.organization_no = '...';
--   SET LOCAL app.user_no         = '...';
-- SET LOCAL ব্যবহার করুন — কানেকশন পুল থেকে অন্য টেন্যান্টের সেশনে
-- মান লিক হওয়া আটকাতে।
-- ---------------------------------------------------------------------

-- সিস্টেম ব্যবহারকারী: মাইগ্রেশন ও গ্লোবাল সিড ডেটার কর্তা।
-- স্থির UUID, যাতে সব পরিবেশে (dev/staging/prod) এক থাকে।
create or replace function core.system_user_no()
returns uuid language sql immutable parallel safe as
$$ select '00000000-0000-0000-0000-000000000001'::uuid $$;

create or replace function core.current_org_no()
returns uuid language sql stable as
$$ select nullif(current_setting('app.organization_no', true), '')::uuid $$;

create or replace function core.current_user_no()
returns uuid language sql stable as
$$ select coalesce(
       nullif(current_setting('app.user_no', true), '')::uuid,
       core.system_user_no()
   ) $$;

create or replace function core.current_device_no()
returns uuid language sql stable as
$$ select nullif(current_setting('app.device_no', true), '')::uuid $$;

-- ইনক্রিমেন্টাল সিঙ্কের জন্য একটাই গ্লোবাল সিকোয়েন্স।
-- ক্লায়েন্ট শুধু "আমার শেষ দেখা seq এর পরের সব" চাইবে।
create sequence if not exists core.ss_sync_seq as bigint;

-- ---------------------------------------------------------------------
-- ৩. আদর্শ কলাম ব্লক (template)
--
-- এই টেবিলটা কখনো ডেটা রাখে না — শুধু `LIKE ... INCLUDING ALL` দিয়ে
-- অন্য টেবিলে কলামগুলো কপি করার ছাঁচ।
--
-- লক্ষ্য করুন: ss_modified_by আছে, ss_update_by নেই। দুটো একসাথে রাখলে
-- ছয় মাস পর কেউ জানবে না কোনটা আসল — একটাই রাখা হয়েছে।
-- ---------------------------------------------------------------------
create table if not exists core.ss_row_template (
  -- কে, কখন
  ss_created_by     uuid        not null default core.current_user_no(),
  ss_created_time   timestamptz not null default now(),      -- সার্ভার সময়, UTC
  ss_modified_by    uuid,
  ss_modified_time  timestamptz,

  -- সমকালীন সম্পাদনা (optimistic locking)
  ss_row_version    integer     not null default 1,

  -- অবস্থা। active ≠ deleted:
  --   ss_active_flag  = ব্যবহারযোগ্য কি না (মাস্টার ডেটা নিষ্ক্রিয় করা)
  --   ss_deleted_flag = মুছে ফেলা হয়েছে (সফট ডিলিট, অডিট ট্রেইল অক্ষত)
  ss_active_flag    boolean     not null default true,
  ss_deleted_flag   boolean     not null default false,
  ss_deleted_by     uuid,
  ss_deleted_time   timestamptz,

  -- অফলাইন সিঙ্ক
  ss_client_uuid    uuid,          -- idempotency key: রিট্রাই করলেও ডুপ্লিকেট হবে না
  ss_device_no      uuid,          -- কোন ডিভাইস থেকে এন্ট্রি
  ss_device_time    timestamptz,   -- ডিভাইসের ঘড়ি (গ্রামে প্রায়ই ভুল থাকে,
                                   -- তাই ss_created_time এর বিকল্প নয়, পাশাপাশি)
  ss_sync_seq       bigint      not null default nextval('core.ss_sync_seq')
);

comment on table core.ss_row_template is
  'ছাঁচ টেবিল — ডেটা রাখে না। সব ব্যবসায়িক টেবিলে LIKE দিয়ে কপি হয়।';

-- ---------------------------------------------------------------------
-- ৪. অডিট ট্রিগার
--
-- নীতি: এই কলামগুলো অ্যাপ্লিকেশন কোড কখনো বসাবে না। ১৫০+ টেবিলে হাতে
-- লিখলে কোথাও একটা বাদ পড়বেই — তাই ডাটাবেসই দায়িত্ব নেয়।
-- ---------------------------------------------------------------------
create or replace function core.ss_audit_trigger()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    new.ss_created_by    := coalesce(new.ss_created_by, core.current_user_no());
    new.ss_created_time  := coalesce(new.ss_created_time, now());
    new.ss_device_no     := coalesce(new.ss_device_no, core.current_device_no());
    new.ss_modified_by   := null;
    new.ss_modified_time := null;
    new.ss_row_version   := 1;
    new.ss_sync_seq      := nextval('core.ss_sync_seq');

    if new.ss_deleted_flag then
      new.ss_deleted_by   := coalesce(new.ss_deleted_by, core.current_user_no());
      new.ss_deleted_time := coalesce(new.ss_deleted_time, now());
    else
      new.ss_deleted_by   := null;
      new.ss_deleted_time := null;
    end if;

    return new;

  elsif tg_op = 'UPDATE' then
    -- তৈরির তথ্য অপরিবর্তনীয় — কেউ বদলাতে চাইলে চুপচাপ পুরোনোটাই রাখা হয়
    new.ss_created_by   := old.ss_created_by;
    new.ss_created_time := old.ss_created_time;

    new.ss_modified_by   := core.current_user_no();
    new.ss_modified_time := now();
    new.ss_row_version   := old.ss_row_version + 1;
    new.ss_sync_seq      := nextval('core.ss_sync_seq');

    -- সফট ডিলিটের রূপান্তর
    if new.ss_deleted_flag and not old.ss_deleted_flag then
      new.ss_deleted_by   := core.current_user_no();
      new.ss_deleted_time := now();
    elsif not new.ss_deleted_flag and old.ss_deleted_flag then
      new.ss_deleted_by   := null;
      new.ss_deleted_time := null;
    else
      new.ss_deleted_by   := old.ss_deleted_by;
      new.ss_deleted_time := old.ss_deleted_time;
    end if;

    return new;
  end if;

  return new;
end
$$;

-- টেন্যান্ট কলাম অপরিবর্তনীয় রাখার আলাদা ট্রিগার।
-- একটা রেকর্ড কখনো এক খামার থেকে আরেক খামারে "সরে" যেতে পারে না।
create or replace function core.ss_tenant_guard_trigger()
returns trigger
language plpgsql
as $$
begin
  if new.organization_no is distinct from old.organization_no then
    raise exception
      'organization_no পরিবর্তন করা যায় না (টেবিল %): % -> %',
      tg_table_name, old.organization_no, new.organization_no
      using errcode = 'check_violation';
  end if;
  return new;
end
$$;

-- অ্যাপেন্ড-অনলি টেবিলের (লেজার, চলাচল, লগ) জন্য: UPDATE/DELETE নিষিদ্ধ।
-- হিসাবের সারি কখনো সম্পাদনা হয় না — উল্টো এন্ট্রি দিয়ে বাতিল হয়।
create or replace function core.ss_append_only_trigger()
returns trigger
language plpgsql
as $$
begin
  raise exception
    '% টেবিল অ্যাপেন্ড-অনলি — % করা যায় না। বাতিল করতে উল্টো এন্ট্রি (reversal) দিন।',
    tg_table_name, tg_op
    using errcode = 'restrict_violation';
end
$$;

-- ---------------------------------------------------------------------
-- ৫. টেবিল রেজিস্ট্রি
--
-- প্রতিটা ব্যবসায়িক টেবিল এখানে নথিবদ্ধ থাকবে। 99_verify.sql এই
-- রেজিস্ট্রির সাথে বাস্তব স্কিমা মিলিয়ে দেখে — কোনো টেবিল কনভেনশনের
-- বাইরে থাকলে মাইগ্রেশন ব্যর্থ হবে।
-- ---------------------------------------------------------------------
create table if not exists core.ss_table_registry (
  table_schema   text    not null,
  table_name     text    not null,
  ss_scope       text    not null
      check (ss_scope in ('root','tenant','shared','system')),
  is_append_only boolean not null default false,
  registered_at  timestamptz not null default now(),
  primary key (table_schema, table_name)
);

comment on column core.ss_table_registry.ss_scope is
  $c$root   = টেবিলের প্রাইমারি কী-ই organization_no (core.organization)
tenant = organization_no NOT NULL, শুধু নিজের টেন্যান্টের সারি দেখা যায়
shared = organization_no NULL হতে পারে; NULL মানে গ্লোবাল মাস্টার ডেটা,
         সবাই পড়তে পারে কিন্তু লিখতে পারে শুধু নিজের সারিতে
system = টেন্যান্ট কলাম নেই, RLS নেই (শুধু অবকাঠামোগত টেবিল)$c$;

-- ---------------------------------------------------------------------
-- ৬. core.ss_apply() — কনভেনশন প্রয়োগকারী
--
-- একটা টেবিল বানানোর পর শুধু এই ফাংশনটা ডাকতে হয়। এটা নিজে থেকেই:
--   • ss_* কলাম আছে কি না যাচাই করে (না থাকলে ত্রুটি)
--   • অডিট ট্রিগার বসায়
--   • organization_no অপরিবর্তনীয় করে
--   • Row Level Security চালু করে ও পলিসি বানায়
--   • সিঙ্ক-পুলের ইনডেক্স বানায়
--   • অ্যাপ ভূমিকাকে অনুমতি দেয়
--   • রেজিস্ট্রিতে নথিবদ্ধ করে
-- ---------------------------------------------------------------------
create or replace function core.ss_apply(
  p_table        regclass,
  p_scope        text    default 'tenant',
  p_append_only  boolean default false
)
returns void
language plpgsql
as $$
declare
  v_schema   text;
  v_name     text;
  v_fq       text;
  v_missing  text;
  v_org_col  text := 'organization_no';
  v_required text[] := array[
    'ss_created_by','ss_created_time','ss_modified_by','ss_modified_time',
    'ss_row_version','ss_active_flag','ss_deleted_flag','ss_deleted_by',
    'ss_deleted_time','ss_client_uuid','ss_device_no','ss_device_time','ss_sync_seq'
  ];
begin
  if p_scope not in ('root','tenant','shared','system') then
    raise exception 'অজানা ss_scope: %', p_scope;
  end if;

  select n.nspname, c.relname
    into v_schema, v_name
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where c.oid = p_table;

  v_fq := format('%I.%I', v_schema, v_name);

  -- (ক) বাধ্যতামূলক কলাম আছে কি না
  select string_agg(r, ', ')
    into v_missing
  from unnest(v_required) as r
  where not exists (
    select 1 from pg_attribute a
    where a.attrelid = p_table and a.attname = r and a.attnum > 0 and not a.attisdropped
  );
  if v_missing is not null then
    raise exception
      '% টেবিলে অডিট কলাম নেই: %। `LIKE core.ss_row_template INCLUDING ALL` যোগ করুন।',
      v_fq, v_missing;
  end if;

  -- (খ) টেন্যান্ট কলাম আছে কি না
  if p_scope in ('tenant','shared') then
    if not exists (
      select 1 from pg_attribute a
      where a.attrelid = p_table and a.attname = v_org_col
        and a.attnum > 0 and not a.attisdropped
    ) then
      raise exception '% টেবিলে % কলাম নেই, অথচ ss_scope = %।', v_fq, v_org_col, p_scope;
    end if;
  elsif p_scope = 'root' then
    v_org_col := 'organization_no';   -- root টেবিলে এটাই প্রাইমারি কী
  end if;

  -- (গ) অডিট ট্রিগার
  execute format('drop trigger if exists ss_audit_biu on %s', v_fq);
  execute format($f$
    create trigger ss_audit_biu
      before insert or update on %s
      for each row execute function core.ss_audit_trigger()
  $f$, v_fq);

  -- (ঘ) টেন্যান্ট কলাম অপরিবর্তনীয়
  if p_scope in ('tenant','shared','root') then
    execute format('drop trigger if exists ss_tenant_guard_bu on %s', v_fq);
    execute format($f$
      create trigger ss_tenant_guard_bu
        before update on %s
        for each row execute function core.ss_tenant_guard_trigger()
    $f$, v_fq);
  end if;

  -- (ঙ) অ্যাপেন্ড-অনলি হলে UPDATE/DELETE বন্ধ
  if p_append_only then
    execute format('drop trigger if exists ss_append_only_bud on %s', v_fq);
    execute format($f$
      create trigger ss_append_only_bud
        before update or delete on %s
        for each row execute function core.ss_append_only_trigger()
    $f$, v_fq);
  end if;

  -- (চ) Row Level Security
  --
  -- এটাই টেন্যান্ট পৃথকীকরণের আসল প্রতিরক্ষা। কুয়েরিতে কেউ
  -- `WHERE organization_no = ?` ভুলে বাদ দিলেও অন্য খামারির ডেটা বেরোবে না।
  -- current_org_no() NULL হলে তুলনাটা NULL → false, অর্থাৎ কোনো সারিই
  -- দেখা যায় না — fail-closed, যা fail-open এর চেয়ে সর্বদা নিরাপদ।
  if p_scope in ('root','tenant','shared') then
    execute format('alter table %s enable row level security', v_fq);
    execute format('alter table %s force row level security', v_fq);

    execute format('drop policy if exists ss_sel on %s', v_fq);
    execute format('drop policy if exists ss_ins on %s', v_fq);
    execute format('drop policy if exists ss_upd on %s', v_fq);
    execute format('drop policy if exists ss_del on %s', v_fq);

    if p_scope = 'shared' then
      -- গ্লোবাল মাস্টার সারি (organization_no IS NULL) সবাই পড়তে পারে,
      -- কিন্তু কেউ বদলাতে পারে না — শুধু নিজের যোগ করা সারিতে লিখতে পারে।
      execute format($f$
        create policy ss_sel on %s for select
          using (%I is null or %I = core.current_org_no())
      $f$, v_fq, v_org_col, v_org_col);
    else
      execute format($f$
        create policy ss_sel on %s for select
          using (%I = core.current_org_no())
      $f$, v_fq, v_org_col);
    end if;

    execute format($f$
      create policy ss_ins on %s for insert
        with check (%I = core.current_org_no())
    $f$, v_fq, v_org_col);

    execute format($f$
      create policy ss_upd on %s for update
        using (%I = core.current_org_no())
        with check (%I = core.current_org_no())
    $f$, v_fq, v_org_col, v_org_col);

    execute format($f$
      create policy ss_del on %s for delete
        using (%I = core.current_org_no())
    $f$, v_fq, v_org_col);
  end if;

  -- (ছ) ইনক্রিমেন্টাল সিঙ্কের ইনডেক্স
  if p_scope in ('tenant','shared','root') then
    execute format(
      'create index if not exists %I on %s (%I, ss_sync_seq)',
      format('ix_%s_sync', v_name), v_fq, v_org_col);
  else
    execute format(
      'create index if not exists %I on %s (ss_sync_seq)',
      format('ix_%s_sync', v_name), v_fq);
  end if;

  -- (জ) idempotency key — একই ss_client_uuid দুইবার সিঙ্ক হলে ঠেকাবে
  execute format(
    'create unique index if not exists %I on %s (ss_client_uuid) where ss_client_uuid is not null',
    format('ux_%s_client_uuid', v_name), v_fq);

  -- (ঝ) অনুমতি
  execute format('grant select, insert, update, delete on %s to farmerp_app', v_fq);
  execute format('grant select on %s to farmerp_readonly', v_fq);

  -- (ঞ) রেজিস্ট্রি
  insert into core.ss_table_registry (table_schema, table_name, ss_scope, is_append_only)
  values (v_schema, v_name, p_scope, p_append_only)
  on conflict (table_schema, table_name)
    do update set ss_scope = excluded.ss_scope,
                  is_append_only = excluded.is_append_only;
end
$$;

comment on function core.ss_apply(regclass, text, boolean) is
  'প্রতিটা টেবিল তৈরির পর ডাকতে হয়। অডিট ট্রিগার, RLS, ইনডেক্স ও অনুমতি বসায়।';

grant usage, select on sequence core.ss_sync_seq to farmerp_app;

-- ---------------------------------------------------------------------
-- ৭. অপরিবর্তনীয় কলাম রক্ষী (পুনর্ব্যবহারযোগ্য)
--
-- ব্যবহার:
--   create trigger x_immutable before update on t for each row
--     execute function core.ss_immutable_columns_trigger('species_no','tracking_mode');
--
-- কেন দরকার: কিছু ফিল্ড তৈরির পর বদলানো মানে ইতিহাস মিথ্যা হয়ে যাওয়া।
-- একটা ব্যাচ "ব্রয়লার" হিসেবে শুরু করে মাঝপথে "লেয়ার" হয়ে গেলে আগের
-- সব হিসাব অর্থহীন। ভুল হলে ইউনিট বাতিল করে নতুন খুলতে হবে।
-- ---------------------------------------------------------------------
create or replace function core.ss_immutable_columns_trigger()
returns trigger
language plpgsql
as $$
declare
  v_col  text;
  v_old  text;
  v_new  text;
begin
  foreach v_col in array tg_argv loop
    execute format('select ($1).%I::text, ($2).%I::text', v_col, v_col)
      into v_old, v_new using old, new;
    if v_old is distinct from v_new then
      raise exception '%.% পরিবর্তন করা যায় না (ছিল %, দেওয়া হয়েছে %)',
        tg_table_name, v_col, coalesce(v_old,'NULL'), coalesce(v_new,'NULL')
        using errcode = 'check_violation';
    end if;
  end loop;
  return new;
end
$$;
