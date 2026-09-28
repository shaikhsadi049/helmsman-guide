-- =====================================================================
-- 07_prod_unit.sql — উৎপাদন ইউনিট ও প্রাণীর চলাচল
--
-- স্কিমার সবচেয়ে গুরুত্বপূর্ণ সিদ্ধান্ত এখানে:
--
--   ব্রয়লারের ব্যাচ আর নাম ধরে চেনা গাভি — দুটোই একই টেবিলে।
--
-- প্রথম দেখায় অস্বাভাবিক লাগে, কিন্তু এর ফলে দৈনিক লগ, খরচ বণ্টন,
-- হিসাবের পোস্টিং, রিপোর্ট — সব একবার লিখলেই সব প্রজাতির জন্য কাজ করে।
-- tracking_mode ফিল্ড দুটো ধরন আলাদা করে, আর বিশেষায়িত তথ্য যায়
-- prod.flock (দলগত) বা prod.animal (একক) টেবিলে।
-- =====================================================================

create table prod.production_unit (
  production_unit_no    uuid primary key default core.uuidv7(),
  organization_no       uuid not null references core.organization(organization_no),
  farm_no               uuid not null references core.farm(farm_no),
  house_no              uuid references core.house(house_no),
  pen_no                uuid references core.pen(pen_no),

  unit_code             citext not null,   -- ব্যাচ নম্বর বা প্রাণীর ট্যাগ
  unit_name             text,

  species_no            uuid not null references master.species(species_no),
  breed_no              uuid references master.breed(breed_no),   -- দেশি হলে অজানাও হতে পারে
  production_purpose_no uuid not null references master.production_purpose(production_purpose_no),
  lifecycle_template_no uuid references master.lifecycle_template(lifecycle_template_no),

  tracking_mode         text not null
      check (tracking_mode in ('group','individual')),

  status                text not null default 'active'
      check (status in ('planned','active','closed')),

  source_type           text not null default 'market_purchase'
      check (source_type in ('hatchery_doc','market_purchase','own_born','own_hatched',
                             'gift','transfer_in','government_grant','ngo_grant','other')),
  source_ref_text       text,     -- হ্যাচারি/ডিলার/বেপারির নাম (Party মডিউল আসার আগ পর্যন্ত)

  opened_on             date not null,
  closed_on             date,

  -- বয়স গণনার ভিত্তি: পাখির ক্ষেত্রে ফোটার তারিখ, প্রাণীর ক্ষেত্রে জন্মতারিখ।
  -- ক্রয় করা প্রাণীর বয়স অনুমান হতে পারে, তাই আলাদা ফিল্ড — opened_on দিয়ে
  -- বয়স হিসাব করা ভুল হতো (২ বছরের গাভি কিনলে তার বয়স ০ দিন নয়)।
  age_reference_date    date,
  age_is_estimated      boolean not null default false,

  -- লক্ষ্য করুন: এখানে opening_qty বা current_qty নামের কোনো কলাম নেই।
  -- ইউনিটে কত প্রাণী ঢুকল তা জানা যায় OPENING বা DOC_RECEIPT ধরনের
  -- চলাচল থেকে, আর বর্তমানে কত আছে তা প্রতিটা চলাচলের যোগফল থেকে।
  -- সংখ্যা আলাদা কলামে রাখলে একদিন সেটা খাতার সাথে অমিল হবেই —
  -- ঠিক এই কারণেই মড়কও দৈনিক লগে রাখা হয়নি। একটাই সত্য, একটাই জায়গা।
  parent_unit_no        uuid references prod.production_unit(production_unit_no),

  remarks_bn            text,
  like core.ss_row_template including all,

  constraint ck_pu_close check (
    (status = 'closed' and closed_on is not null) or
    (status <> 'closed')
  ),
  constraint ck_pu_close_date check (closed_on is null or closed_on >= opened_on),

  -- composite FK এর লক্ষ্য: prod.flock ও prod.animal যেন ভুল ধরনের
  -- ইউনিটকে নির্দেশ করতে না পারে (নিচে দেখুন)
  unique (production_unit_no, tracking_mode)
);

create unique index ux_production_unit_code
  on prod.production_unit (organization_no, unit_code) where ss_deleted_flag = false;
create index ix_pu_farm_status on prod.production_unit (organization_no, farm_no, status);
create index ix_pu_house on prod.production_unit (organization_no, house_no) where house_no is not null;
create index ix_pu_species on prod.production_unit (organization_no, species_no, production_purpose_no);

select core.ss_apply('prod.production_unit', 'tenant');

-- ইউনিট তৈরির পর এই ফিল্ডগুলো বদলানো মানে আগের সব হিসাব মিথ্যা হয়ে যাওয়া
create trigger pu_immutable_bu
  before update on prod.production_unit
  for each row execute function core.ss_immutable_columns_trigger(
    'tracking_mode', 'species_no', 'farm_no', 'opened_on');

-- ইউনিটের farm ও house একই প্রতিষ্ঠানের কি না, এবং pen সেই house-এর কি না
create or replace function prod.production_unit_guard()
returns trigger language plpgsql as $$
declare v_x uuid;
begin
  select organization_no into v_x from core.farm where farm_no = new.farm_no;
  if v_x is distinct from new.organization_no then
    raise exception 'খামারটি এই প্রতিষ্ঠানের নয়' using errcode = 'check_violation';
  end if;

  if new.house_no is not null then
    select farm_no into v_x from core.house where house_no = new.house_no;
    if v_x is distinct from new.farm_no then
      raise exception 'ঘরটি নির্বাচিত খামারের নয়' using errcode = 'check_violation';
    end if;
  end if;

  if new.pen_no is not null then
    select house_no into v_x from core.pen where pen_no = new.pen_no;
    if v_x is distinct from new.house_no then
      raise exception 'খোপটি নির্বাচিত ঘরের নয়' using errcode = 'check_violation';
    end if;
  end if;

  -- জাত ও প্রজাতি মিলছে কি না
  if new.breed_no is not null then
    select species_no into v_x from master.breed where breed_no = new.breed_no;
    if v_x is distinct from new.species_no then
      raise exception 'জাতটি নির্বাচিত প্রজাতির নয়' using errcode = 'check_violation';
    end if;
  end if;

  return new;
end $$;

create trigger pu_guard_biu
  before insert or update on prod.production_unit
  for each row execute function prod.production_unit_guard();

-- ---------------------------------------------------------------------
-- দলগত ইউনিটের বিশেষ তথ্য (ফ্লক / ব্যাচ)
--
-- composite FK (production_unit_no, tracking_mode) → production_unit এর
-- একই জোড়া, আর এখানে tracking_mode CHECK দিয়ে 'group' এ আটকানো।
-- ফলে একক প্রাণীর ইউনিটে ভুল করে ফ্লক সারি বসানো ডাটাবেসই আটকায় —
-- অ্যাপ কোডের সদিচ্ছার উপর নির্ভর করতে হয় না।
-- ---------------------------------------------------------------------
create table prod.flock (
  production_unit_no uuid primary key,
  organization_no    uuid not null references core.organization(organization_no),
  tracking_mode      text not null default 'group' check (tracking_mode = 'group'),

  hatch_date           date,
  doc_supplier_name    text,            -- কাজী, নারিশ, সিপি, আফতাব, প্যারাগন…
  -- বাচ্চার সংখ্যা এখানে নেই — সেটা DOC_RECEIPT চলাচলে। এখানে শুধু
  -- প্রতি-বাচ্চার তথ্য, যা যোগফল নয় তাই অমিলের ঝুঁকি নেই।
  doc_unit_cost        numeric(14,4) check (doc_unit_cost >= 0),
  doc_avg_weight_g     numeric(8,2) check (doc_avg_weight_g > 0),
  sexing               text not null default 'as_hatched'
      check (sexing in ('as_hatched','male','female','mixed')),
  like core.ss_row_template including all,

  foreign key (production_unit_no, tracking_mode)
    references prod.production_unit (production_unit_no, tracking_mode)
    on delete cascade on update restrict
);
select core.ss_apply('prod.flock', 'tenant');

-- ---------------------------------------------------------------------
-- একক প্রাণীর বিশেষ তথ্য (গাভি, মহিষ, ছাগল, ভেড়া, ব্রিডার)
-- ---------------------------------------------------------------------
create table prod.animal (
  production_unit_no uuid primary key,
  organization_no    uuid not null references core.organization(organization_no),
  tracking_mode      text not null default 'individual' check (tracking_mode = 'individual'),

  tag_no             citext,          -- কানের ট্যাগ; দেশি পালনে প্রায়ই থাকে না
  call_name          text,            -- ডাকনাম — "লালী", "কালী" — বাস্তবে এভাবেই চেনা হয়
  sex                text not null default 'unknown'
      check (sex in ('male','female','castrated','unknown')),   -- castrated = খাসি
  date_of_birth      date,
  birth_weight_kg    numeric(8,3) check (birth_weight_kg > 0),

  dam_no             uuid references prod.animal(production_unit_no),   -- মা
  sire_no            uuid references prod.animal(production_unit_no),   -- বাবা (নিজের ষাঁড়)
  sire_semen_code    text,     -- কৃত্রিম প্রজনন হলে সিমেন/স্ট্রর সংকেত

  -- ট্যাগ ছাড়া প্রাণী চেনার বাস্তব উপায়। বাংলাদেশে ছোট খামারে
  -- ট্যাগ দুর্লভ, কিন্তু "কপালে সাদা তিলক, ডান পা সাদা" — এভাবেই চেনা হয়।
  colour_marking_bn  text,
  horn_status        text check (horn_status in ('horned','polled','dehorned','unknown')),
  photo_url          text,

  is_breeding_stock  boolean not null default false,
  purchased_on       date,
  purchase_cost      numeric(14,2) check (purchase_cost >= 0),
  like core.ss_row_template including all,

  foreign key (production_unit_no, tracking_mode)
    references prod.production_unit (production_unit_no, tracking_mode)
    on delete cascade on update restrict,

  -- নিজের মা বা নিজের বাবা হওয়া অসম্ভব
  constraint ck_animal_not_own_parent check (
    production_unit_no <> dam_no and production_unit_no <> sire_no
  )
);
create unique index ux_animal_tag on prod.animal (organization_no, tag_no)
  where tag_no is not null and ss_deleted_flag = false;
create index ix_animal_dam on prod.animal (dam_no) where dam_no is not null;
create index ix_animal_sire on prod.animal (sire_no) where sire_no is not null;
select core.ss_apply('prod.animal', 'tenant');

-- ---------------------------------------------------------------------
-- প্রাণীর চলাচল (append-only খাতা)
--
-- এখানেই স্টকের একমাত্র সত্য। কোথাও "বর্তমান সংখ্যা" নামের কলাম রাখা
-- হয়নি — ইচ্ছাকৃতভাবে। কারণ সংখ্যা আলাদা কলামে রাখলে একদিন সেটা
-- চলাচলের সাথে অমিল হবেই (ট্রিগার মিস, সমকালীন আপডেট, ব্যাকডেটেড সংশোধন)।
-- সংখ্যা সর্বদা যোগফল থেকে আসে, তাই অমিল হওয়া অসম্ভব।
--
-- UPDATE/DELETE নিষিদ্ধ। ভুল হলে উল্টো চলাচল (reversal) দিতে হবে —
-- ঠিক যেমন হিসাবের খাতায় কাটাকুটি করা হয় না।
-- ---------------------------------------------------------------------
create table prod.unit_movement (
  unit_movement_no      uuid primary key default core.uuidv7(),
  organization_no       uuid not null references core.organization(organization_no),
  farm_no               uuid not null references core.farm(farm_no),
  production_unit_no    uuid not null references prod.production_unit(production_unit_no),
  movement_type_no      uuid not null references master.movement_type(movement_type_no),
  movement_date         date not null,

  qty                   integer not null check (qty > 0),
  total_weight_kg       numeric(12,3) check (total_weight_kg > 0),
  unit_rate             numeric(14,4) check (unit_rate >= 0),
  total_amount          numeric(16,2) check (total_amount >= 0),

  counterparty_name     text,      -- বেপারি/ফড়িয়া/ডিলার/ক্রেতা
  disease_no            uuid references master.disease(disease_no),        -- মৃত্যুর কারণ
  disposal_method_no    uuid references master.disposal_method(disposal_method_no),
  to_production_unit_no uuid references prod.production_unit(production_unit_no),
  age_day_at_event      integer check (age_day_at_event >= 0),
  reference_doc_no      text,
  reversal_of_no        uuid references prod.unit_movement(unit_movement_no),
  remarks_bn            text,
  like core.ss_row_template including all,

  constraint ck_um_transfer_target check (
    to_production_unit_no is null or to_production_unit_no <> production_unit_no
  )
);
create index ix_um_unit_date on prod.unit_movement (production_unit_no, movement_date);
create index ix_um_org_date  on prod.unit_movement (organization_no, movement_date);
create index ix_um_type      on prod.unit_movement (organization_no, movement_type_no, movement_date);

select core.ss_apply('prod.unit_movement', 'tenant', p_append_only => true);

-- ---------------------------------------------------------------------
-- চলাচল যাচাই
--
-- দুটো জিনিস নিশ্চিত করে:
--   ১. চলাচলের ধরন যা দাবি করে তা আছে (মড়কে কারণ, বিক্রিতে টাকা)
--   ২. স্টক কখনো ঋণাত্মক হয় না — ৮০টার ফ্লক থেকে ১০০টা বিক্রি করা যাবে না।
--      ব্যাকডেটেড এন্ট্রিও ধরা পড়ে: শুধু শেষ ব্যালেন্স নয়, প্রতিটা দিনের
--      চলমান ব্যালেন্স পরীক্ষা করা হয়।
-- ---------------------------------------------------------------------
create or replace function prod.unit_movement_guard()
returns trigger language plpgsql as $$
declare
  v_mt          record;
  v_pu          record;
  v_min_balance bigint;
begin
  select * into v_mt from master.movement_type where movement_type_no = new.movement_type_no;
  if not found then
    raise exception 'চলাচলের ধরন পাওয়া যায়নি' using errcode = 'foreign_key_violation';
  end if;

  select * into v_pu from prod.production_unit where production_unit_no = new.production_unit_no;
  if v_pu.organization_no is distinct from new.organization_no
     or v_pu.farm_no is distinct from new.farm_no then
    raise exception 'ইউনিটটি এই প্রতিষ্ঠান/খামারের নয়' using errcode = 'check_violation';
  end if;

  if new.movement_date < v_pu.opened_on then
    raise exception 'চলাচলের তারিখ (%) ইউনিট খোলার তারিখের (%) আগে হতে পারে না',
      new.movement_date, v_pu.opened_on using errcode = 'check_violation';
  end if;

  -- একক প্রাণীর ইউনিটে সংখ্যা সর্বদা ১
  if v_pu.tracking_mode = 'individual' and new.qty <> 1 then
    raise exception 'একক প্রাণীর চলাচলে সংখ্যা ১ হতে হবে, দেওয়া হয়েছে %', new.qty
      using errcode = 'check_violation';
  end if;

  -- ধরন অনুসারে বাধ্যতামূলক তথ্য
  if v_mt.requires_cause and new.disease_no is null then
    raise exception '% এর জন্য কারণ (disease_no) দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;
  if v_mt.requires_amount and new.total_amount is null then
    raise exception '% এর জন্য টাকার অঙ্ক দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;
  if v_mt.requires_counterparty and coalesce(new.counterparty_name,'') = '' then
    raise exception '% এর জন্য পক্ষের নাম দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;
  if v_mt.is_internal_transfer and new.to_production_unit_no is null then
    raise exception 'শাখান্তরে গন্তব্য ইউনিট দিতে হবে' using errcode = 'not_null_violation';
  end if;

  -- বয়স স্বয়ংক্রিয়ভাবে বসাই, যাতে রিপোর্টে হিসাব করতে না হয়
  if new.age_day_at_event is null and v_pu.age_reference_date is not null then
    new.age_day_at_event := greatest(0, new.movement_date - v_pu.age_reference_date);
  end if;

  -- ঋণাত্মক স্টক প্রতিরোধ: নতুন সারিসহ প্রতিটা তারিখের চলমান যোগফল
  with all_mv as (
    select m.movement_date, mt.direction * m.qty as delta
      from prod.unit_movement m
      join master.movement_type mt on mt.movement_type_no = m.movement_type_no
     where m.production_unit_no = new.production_unit_no
    union all
    select new.movement_date, v_mt.direction * new.qty
  ),
  daily as (
    select movement_date, sum(delta) as day_delta
      from all_mv group by movement_date
  )
  select min(running) into v_min_balance
    from (select sum(day_delta) over (order by movement_date) as running from daily) s;

  if coalesce(v_min_balance, 0) < 0 then
    raise exception
      'এই চলাচলে স্টক ঋণাত্মক হয়ে যায় (সর্বনিম্ন %)। ইউনিট %, তারিখ %।',
      v_min_balance, v_pu.unit_code, new.movement_date
      using errcode = 'check_violation';
  end if;

  return new;
end $$;

create trigger um_guard_bi
  before insert on prod.unit_movement
  for each row execute function prod.unit_movement_guard();

-- ---------------------------------------------------------------------
-- বর্তমান সংখ্যা ও মড়কের হিসাব — সবই চলাচল থেকে নেওয়া
-- ---------------------------------------------------------------------
create view prod.v_unit_balance as
select
  pu.production_unit_no,
  pu.organization_no,
  pu.farm_no,
  pu.unit_code,
  pu.species_no,
  pu.tracking_mode,
  pu.status,
  pu.opened_on,
  pu.age_reference_date,
  coalesce(sum(mt.direction * m.qty), 0)::integer                          as current_qty,
  coalesce(sum(case when mt.direction = 1 then m.qty end), 0)::integer     as total_in_qty,
  coalesce(sum(case when mt.is_mortality then m.qty end), 0)::integer      as total_dead_qty,
  coalesce(sum(case when mt.is_culling   then m.qty end), 0)::integer      as total_culled_qty,
  coalesce(sum(case when mt.is_sale then m.qty end), 0)::integer           as total_sold_qty,
  coalesce(sum(case when mt.is_home_consumption then m.qty end), 0)::integer as total_home_qty,
  coalesce(sum(case when mt.is_donation then m.qty end), 0)::integer       as total_donated_qty,
  -- মড়ক ও অবক্ষয় আলাদা করে দেখানো হয়:
  --   মড়ক (mortality)  = মারা গেছে
  --   অবক্ষয় (depletion) = মারা গেছে + কালিং করা হয়েছে
  -- ব্রয়লারে ৫% মড়ক আর ৫% অবক্ষয় সম্পূর্ণ ভিন্ন দুটো গল্প।
  case when coalesce(sum(case when mt.direction = 1 then m.qty end), 0) > 0
       then round(100.0 * coalesce(sum(case when mt.is_mortality then m.qty end), 0)
                  / sum(case when mt.direction = 1 then m.qty end), 3)
  end                                                                      as mortality_pct,
  case when coalesce(sum(case when mt.direction = 1 then m.qty end), 0) > 0
       then round(100.0 * coalesce(sum(case when mt.is_mortality or mt.is_culling
                                            then m.qty end), 0)
                  / sum(case when mt.direction = 1 then m.qty end), 3)
  end                                                                      as depletion_pct,
  max(m.movement_date)                                                     as last_movement_date
from prod.production_unit pu
left join prod.unit_movement m
       on m.production_unit_no = pu.production_unit_no
      and m.ss_deleted_flag = false
left join master.movement_type mt
       on mt.movement_type_no = m.movement_type_no
where pu.ss_deleted_flag = false
group by pu.production_unit_no, pu.organization_no, pu.farm_no, pu.unit_code,
         pu.species_no, pu.tracking_mode, pu.status, pu.opened_on, pu.age_reference_date;

grant select on prod.v_unit_balance to farmerp_app, farmerp_readonly;
