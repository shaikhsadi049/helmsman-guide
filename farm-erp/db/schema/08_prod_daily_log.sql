-- =====================================================================
-- 08_prod_daily_log.sql — দৈনিক লগ
--
-- প্রকল্পের সবচেয়ে গুরুত্বপূর্ণ পর্দার টেবিল। যদি ম্যানেজার দিন শেষে
-- ৩০ সেকেন্ডে আজকের হিসাব দিতে না পারে, তাহলে বাকি পুরো ERP অচল।
-- তাই এখানে কোনো প্রজাতি-নির্দিষ্ট কলাম নেই — metric_applicability
-- ঠিক করে দেয় কোন ইউনিটে কোন ঘর দেখাতে হবে।
--
-- একটা কঠোর নিয়ম: মড়কের সংখ্যা এখানে রাখা হয় না।
-- মড়ক স্টক বদলায়, আর স্টকের একমাত্র সত্য prod.unit_movement।
-- দুই জায়গায় রাখলে একদিন দুটো অমিল হবেই — "লগে ৫টা মরেছে, চলাচলে ৩টা"।
-- তাই ডাটাবেস নিজেই মড়ক-শ্রেণির মেট্রিক এখানে বসাতে দেয় না।
-- =====================================================================

create table prod.daily_log (
  daily_log_no       uuid primary key default core.uuidv7(),
  organization_no    uuid not null references core.organization(organization_no),
  farm_no            uuid not null references core.farm(farm_no),
  production_unit_no uuid not null references prod.production_unit(production_unit_no),
  log_date           date not null,
  age_day            integer check (age_day >= 0),
  recorded_by_user_no uuid references core.app_user(user_no),
  -- মাঠে কাজ করার সময় সব ঘর ভরা যায় না; অসম্পূর্ণ লগও রাখা দরকার,
  -- না হলে খামারি কিছুই না লিখে চলে যাবে
  is_complete        boolean not null default false,
  is_locked          boolean not null default false,
  remarks_bn         text,
  voice_note_url     text,     -- স্বল্পশিক্ষিত শ্রমিকের জন্য: বলে রাখা যাবে
  like core.ss_row_template including all
);
create unique index ux_daily_log_unit_date
  on prod.daily_log (production_unit_no, log_date) where ss_deleted_flag = false;
create index ix_daily_log_org_date on prod.daily_log (organization_no, log_date);
create index ix_daily_log_farm_date on prod.daily_log (organization_no, farm_no, log_date);
select core.ss_apply('prod.daily_log', 'tenant');

-- লগের তারিখ ইউনিট খোলার আগে বা বন্ধ হওয়ার পরে হতে পারে না;
-- বয়স স্বয়ংক্রিয়ভাবে বসে
create or replace function prod.daily_log_guard()
returns trigger language plpgsql as $$
declare v_pu record;
begin
  select * into v_pu from prod.production_unit where production_unit_no = new.production_unit_no;

  if v_pu.organization_no is distinct from new.organization_no
     or v_pu.farm_no is distinct from new.farm_no then
    raise exception 'ইউনিটটি এই প্রতিষ্ঠান/খামারের নয়' using errcode = 'check_violation';
  end if;
  if new.log_date < v_pu.opened_on then
    raise exception 'লগের তারিখ (%) ইউনিট খোলার আগে হতে পারে না (%)',
      new.log_date, v_pu.opened_on using errcode = 'check_violation';
  end if;
  if v_pu.closed_on is not null and new.log_date > v_pu.closed_on then
    raise exception 'লগের তারিখ (%) ইউনিট বন্ধ হওয়ার পরে হতে পারে না (%)',
      new.log_date, v_pu.closed_on using errcode = 'check_violation';
  end if;
  if new.log_date > current_date then
    raise exception 'ভবিষ্যতের তারিখে লগ দেওয়া যায় না (%)' , new.log_date
      using errcode = 'check_violation';
  end if;

  if new.age_day is null and v_pu.age_reference_date is not null then
    new.age_day := greatest(0, new.log_date - v_pu.age_reference_date);
  end if;
  return new;
end $$;

create trigger daily_log_guard_biu
  before insert or update on prod.daily_log
  for each row execute function prod.daily_log_guard();

create trigger daily_log_immutable_bu
  before update on prod.daily_log
  for each row execute function core.ss_immutable_columns_trigger(
    'production_unit_no', 'log_date');

-- ---------------------------------------------------------------------
-- লগের মান
--
-- একটা সারি = একটা মাপ। প্রজাতিভেদে ঘরের সংখ্যা ভিন্ন, তাই কলাম নয় সারি।
-- এর দাম: টাইপ-নিরাপত্তা কমে। তাই value_type অনুসারে আলাদা কলাম রাখা
-- হয়েছে, আর ট্রিগার যাচাই করে সঠিক কলামে মান বসেছে কি না।
-- ---------------------------------------------------------------------
create table prod.daily_log_value (
  daily_log_value_no uuid primary key default core.uuidv7(),
  organization_no    uuid not null references core.organization(organization_no),
  daily_log_no       uuid not null references prod.daily_log(daily_log_no) on delete cascade,
  metric_no          uuid not null references master.metric_definition(metric_no),
  num_value          numeric(18,4),
  int_value          integer,
  bool_value         boolean,
  txt_value          text,
  uom_no             uuid references master.uom(uom_no),
  like core.ss_row_template including all,

  -- ঠিক একটা মান থাকতে হবে — কোনোটাই নয়, বা একাধিক নয়
  constraint ck_dlv_one_value check (
    (case when num_value  is not null then 1 else 0 end
   + case when int_value   is not null then 1 else 0 end
   + case when bool_value  is not null then 1 else 0 end
   + case when txt_value   is not null then 1 else 0 end) = 1
  )
);
create unique index ux_dlv_log_metric on prod.daily_log_value (daily_log_no, metric_no)
  where ss_deleted_flag = false;
create index ix_dlv_metric on prod.daily_log_value (organization_no, metric_no);
select core.ss_apply('prod.daily_log_value', 'tenant');

-- ---------------------------------------------------------------------
-- মেট্রিক প্রযোজ্যতা যাচাই
--
-- এখানেই "প্রজাতিভেদে ভিন্ন আচরণ" বাস্তবায়িত হয় — কোনো if-else ছাড়া,
-- শুধু কনফিগ টেবিল দেখে। ব্রয়লারে ডিমের সারি বসাতে গেলে ডাটাবেস
-- আটকে দেবে, কারণ metric_applicability-তে সেই জোড়া নেই।
-- ---------------------------------------------------------------------
create or replace function prod.daily_log_value_guard()
returns trigger language plpgsql as $$
declare
  v_log   record;
  v_pu    record;
  v_m     record;
  v_ok    boolean;
begin
  select * into v_log from prod.daily_log where daily_log_no = new.daily_log_no;
  if v_log.is_locked then
    raise exception 'এই লগ লক করা হয়েছে, পরিবর্তন করা যাবে না'
      using errcode = 'restrict_violation';
  end if;
  if v_log.organization_no is distinct from new.organization_no then
    raise exception 'লগটি এই প্রতিষ্ঠানের নয়' using errcode = 'check_violation';
  end if;

  select * into v_pu from prod.production_unit
   where production_unit_no = v_log.production_unit_no;
  select * into v_m from master.metric_definition where metric_no = new.metric_no;

  -- মড়ক এখানে নয় — prod.unit_movement এ
  if v_m.category = 'mortality' then
    raise exception
      'মড়কের মেট্রিক (%) দৈনিক লগে রাখা যায় না — prod.unit_movement এ চলাচল হিসেবে দিন। '
      'স্টকের একমাত্র সত্য চলাচলের খাতা।', v_m.metric_code
      using errcode = 'check_violation';
  end if;

  -- এই প্রজাতি ও উদ্দেশ্যে মেট্রিকটা প্রযোজ্য কি না
  select exists (
    select 1 from master.metric_applicability a
     where a.metric_no = new.metric_no
       and a.ss_deleted_flag = false
       and (a.species_no is null or a.species_no = v_pu.species_no)
       and (a.production_purpose_no is null
            or a.production_purpose_no = v_pu.production_purpose_no)
  ) into v_ok;

  if not v_ok then
    raise exception
      'মেট্রিক % এই ইউনিটে প্রযোজ্য নয় (প্রজাতি/উদ্দেশ্য মেলে না)', v_m.metric_code
      using errcode = 'check_violation';
  end if;

  -- সঠিক কলামে মান বসেছে কি না
  if v_m.value_type = 'numeric' and new.num_value is null then
    raise exception '% সংখ্যাসূচক মেট্রিক — num_value দিতে হবে', v_m.metric_code
      using errcode = 'check_violation';
  elsif v_m.value_type = 'integer' and new.int_value is null then
    raise exception '% পূর্ণসংখ্যার মেট্রিক — int_value দিতে হবে', v_m.metric_code
      using errcode = 'check_violation';
  elsif v_m.value_type = 'boolean' and new.bool_value is null then
    raise exception '% হ্যাঁ/না মেট্রিক — bool_value দিতে হবে', v_m.metric_code
      using errcode = 'check_violation';
  elsif v_m.value_type = 'text' and new.txt_value is null then
    raise exception '% লিখিত মেট্রিক — txt_value দিতে হবে', v_m.metric_code
      using errcode = 'check_violation';
  end if;

  -- সীমার বাইরে গেলে আটকাই: ৪০ কেজি ওজনের ব্রয়লার নিশ্চয়ই টাইপো
  if v_m.min_value is not null
     and coalesce(new.num_value, new.int_value) < v_m.min_value then
    raise exception '% এর মান সর্বনিম্ন সীমার (%) নিচে', v_m.metric_code, v_m.min_value
      using errcode = 'check_violation';
  end if;
  if v_m.max_value is not null
     and coalesce(new.num_value, new.int_value) > v_m.max_value then
    raise exception '% এর মান সর্বোচ্চ সীমার (%) উপরে', v_m.metric_code, v_m.max_value
      using errcode = 'check_violation';
  end if;

  if new.uom_no is null then
    new.uom_no := v_m.default_uom_no;
  end if;

  return new;
end $$;

create trigger dlv_guard_biu
  before insert or update on prod.daily_log_value
  for each row execute function prod.daily_log_value_guard();

-- ---------------------------------------------------------------------
-- একত্রিত দৈনিক দৃশ্য
--
-- রিপোর্ট দুই জায়গা থেকে পড়ার দরকার নেই — লগের মান আর চলাচল থেকে
-- আসা মড়ক এখানে একসাথে মিলে যায়।
-- ---------------------------------------------------------------------
create view prod.v_daily_metric as
select
  dl.organization_no,
  dl.farm_no,
  dl.production_unit_no,
  dl.log_date,
  dl.age_day,
  md.metric_code,
  md.name_bn as metric_name_bn,
  md.category,
  coalesce(dlv.num_value, dlv.int_value::numeric) as value_num,
  dlv.bool_value,
  dlv.txt_value,
  dlv.uom_no
from prod.daily_log dl
join prod.daily_log_value dlv on dlv.daily_log_no = dl.daily_log_no
                             and dlv.ss_deleted_flag = false
join master.metric_definition md on md.metric_no = dlv.metric_no
where dl.ss_deleted_flag = false

union all

-- মড়ক চলাচলের খাতা থেকে, একই আকারে
select
  m.organization_no,
  m.farm_no,
  m.production_unit_no,
  m.movement_date as log_date,
  m.age_day_at_event as age_day,
  'mortality_qty'::citext as metric_code,
  'মড়ক (সংখ্যা)'::text   as metric_name_bn,
  'mortality'::text       as category,
  sum(m.qty)::numeric     as value_num,
  null::boolean, null::text, null::uuid
from prod.unit_movement m
join master.movement_type mt on mt.movement_type_no = m.movement_type_no
where mt.is_mortality and m.ss_deleted_flag = false
group by m.organization_no, m.farm_no, m.production_unit_no,
         m.movement_date, m.age_day_at_event;

grant select on prod.v_daily_metric to farmerp_app, farmerp_readonly;
