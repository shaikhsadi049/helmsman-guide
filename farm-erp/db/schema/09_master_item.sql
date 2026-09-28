-- =====================================================================
-- 09_master_item.sql — পণ্য, প্যাকেজিং ও পুষ্টিমান
--
-- এখানে একটা একক সিদ্ধান্ত পুরো ফিড হিসাবের ভিত্তি:
--
--   সব পুষ্টিমান "যেমন খাওয়ানো হয়" (as-fed) ভিত্তিতে, প্রতি কেজিতে।
--
-- রুমিন্যান্টের বইপত্রে পুষ্টিমান সাধারণত শুষ্ক পদার্থ (DM) ভিত্তিতে দেওয়া
-- থাকে, পোল্ট্রিতে as-fed। দুই ভিত্তি একই টেবিলে মিশলে একদিন কেউ কাঁচা
-- ঘাসের ৯% আমিষকে as-fed ধরে হিসাব করবে — অথচ ঘাসে ৮০% পানি, আসল
-- as-fed আমিষ ১.৮%। সেই ভুলে গরু অর্ধেক আমিষ পাবে।
--
-- তাই এখানে সব as-fed, আর শুষ্ক পদার্থ (DM%) নিজেই একটা পুষ্টি উপাদান।
-- রুমিন্যান্টের রিপোর্টে DM ভিত্তিতে রূপান্তর করা হয়, উল্টোটা নয়।
-- =====================================================================

-- ---------------------------------------------------------------------
-- পণ্যের শ্রেণি
-- ---------------------------------------------------------------------
create table master.item_category (
  item_category_no   uuid primary key default core.uuidv7(),
  organization_no    uuid,
  item_category_code citext not null,
  name_bn            text not null,
  name_en            text not null,
  item_type          text not null
      check (item_type in ('feed_finished','feed_ingredient','feed_additive',
                           'medicine','vaccine','supplement','litter',
                           'equipment','consumable','fuel','utility','produce','other')),
  sort_order         smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_item_category_code on master.item_category
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), item_category_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.item_category', 'shared');

-- ---------------------------------------------------------------------
-- পণ্য
-- ---------------------------------------------------------------------
create table master.item (
  item_no          uuid primary key default core.uuidv7(),
  organization_no  uuid,
  item_code        citext not null,
  name_bn          text not null,
  name_en          text not null,
  item_category_no uuid not null references master.item_category(item_category_no),
  item_type        text not null
      check (item_type in ('feed_finished','feed_ingredient','feed_additive',
                           'medicine','vaccine','supplement','litter',
                           'equipment','consumable','fuel','utility','produce','other')),
  base_uom_no      uuid not null references master.uom(uom_no),

  brand            text,
  manufacturer     text,

  is_stock_tracked boolean not null default true,
  is_lot_tracked   boolean not null default false,   -- ঔষধ, টিকা, ফিডের লট
  has_expiry       boolean not null default false,
  shelf_life_days  integer check (shelf_life_days > 0),

  -- ঔষধের প্রত্যাহারকাল। ইচ্ছাকৃতভাবে সিডে ফাঁকা রাখা হয়েছে —
  -- এটা পণ্যের লেবেল ও নিবন্ধন-নির্দিষ্ট, একই ওষুধের ভিন্ন ব্র্যান্ডে
  -- ভিন্ন হয়। ভুল মান বসানোর চেয়ে ফাঁকা থাকা নিরাপদ, কারণ এর উপর
  -- ভিত্তি করে ডিম/দুধ/মাংস বিক্রি আটকানো হবে।
  withdrawal_days_meat integer check (withdrawal_days_meat >= 0),
  withdrawal_days_egg  integer check (withdrawal_days_egg  >= 0),
  withdrawal_days_milk integer check (withdrawal_days_milk >= 0),

  is_medicated     boolean not null default false,   -- কক্সিডিওস্ট্যাট/অ্যান্টিবায়োটিক মেশানো ফিড

  -- শুধু রুমিন্যান্টে দেওয়ার যোগ্য। সবচেয়ে গুরুত্বপূর্ণ উদাহরণ ইউরিয়া:
  -- এর "আমিষ" আসলে অ-প্রোটিন নাইট্রোজেন, যা রুমেনের জীবাণু ব্যবহার করতে
  -- পারে কিন্তু মুরগি পারে না। পোল্ট্রির ফরমুলায় ভুলে দিলে হিসাব দেখাবে
  -- ২৮০% আমিষ — পুষ্টি চাহিদা "পূরণ" দেখাবে অথচ পাখি বিষক্রিয়ায় মরবে।
  -- তাই এটা শুধু সতর্কবাণী নয়, ডাটাবেসই আটকায় (feed.formula_line_guard)।
  is_ruminant_only boolean not null default false,
  is_feed          boolean generated always as
                     (item_type in ('feed_finished','feed_ingredient','feed_additive')) stored,
  indicative_rate  numeric(14,4) check (indicative_rate >= 0),  -- আনুমানিক বাজারদর, শুধু ইঙ্গিত
  note_bn          text,
  sort_order       smallint not null default 100,
  like core.ss_row_template including all,

  constraint ck_item_expiry check (not has_expiry or is_lot_tracked),
  constraint ck_item_shelf  check (shelf_life_days is null or has_expiry)
);
create unique index ux_item_code on master.item
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), item_code)
  where ss_deleted_flag = false;
create index ix_item_type on master.item (item_type) where ss_deleted_flag = false;
create index ix_item_feed on master.item (is_feed) where is_feed and ss_deleted_flag = false;
select core.ss_apply('master.item', 'shared');

-- শ্রেণি ও পণ্যের ধরন না মিললে রিপোর্ট বিভ্রান্তিকর হয়
create or replace function master.item_guard()
returns trigger language plpgsql as $$
declare v_cat_type text;
begin
  select item_type into v_cat_type from master.item_category
   where item_category_no = new.item_category_no;
  if v_cat_type is distinct from new.item_type then
    raise exception 'পণ্যের ধরন (%) ও শ্রেণির ধরন (%) মেলে না', new.item_type, v_cat_type
      using errcode = 'check_violation';
  end if;
  return new;
end $$;

create trigger item_guard_biu before insert or update on master.item
  for each row execute function master.item_guard();

-- ---------------------------------------------------------------------
-- প্যাকেজিং
--
-- একক সিডে "বস্তা" নিয়ে লেখা ছিল: এক বস্তা কত কেজি তা পণ্যনির্ভর।
-- সেই তথ্যের জায়গা এটাই। ফিডের বস্তা ৫০ কেজি, প্রোটিন কনসেনট্রেটের
-- বস্তা ২৫ কেজি, ভিটামিন প্রিমিক্সের প্যাকেট ১ কেজি।
-- ---------------------------------------------------------------------
create table master.item_pack (
  item_pack_no    uuid primary key default core.uuidv7(),
  organization_no uuid,
  item_no         uuid not null references master.item(item_no) on delete cascade,
  pack_uom_no     uuid not null references master.uom(uom_no),
  qty_in_base     numeric(16,6) not null check (qty_in_base > 0),
  is_default      boolean not null default false,
  barcode         text,
  like core.ss_row_template including all
);
create unique index ux_item_pack on master.item_pack (item_no, pack_uom_no)
  where ss_deleted_flag = false;
create unique index ux_item_pack_default on master.item_pack (item_no)
  where is_default and ss_deleted_flag = false;
select core.ss_apply('master.item_pack', 'shared');

-- ---------------------------------------------------------------------
-- পুষ্টি উপাদান
-- ---------------------------------------------------------------------
create table master.nutrient (
  nutrient_no     uuid primary key default core.uuidv7(),
  organization_no uuid,
  nutrient_code   citext not null,
  name_bn         text not null,
  name_en         text not null,
  nutrient_group  text not null
      check (nutrient_group in ('dry_matter','energy','protein','amino_acid',
                                'fibre','fat','mineral','vitamin','additive','other')),
  -- মান কোন এককে: PCT (শতাংশ) অথবা KCAL_KG (কিলোক্যালরি/কেজি) ইত্যাদি
  value_uom_code  citext not null,
  -- রেশন হিসাবে এটা সীমাবদ্ধ করা যায় কি না (DM% তথ্য, সীমা নয়)
  is_constrainable boolean not null default true,
  sort_order      smallint not null default 100,
  note_bn         text,
  like core.ss_row_template including all
);
create unique index ux_nutrient_code on master.nutrient
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), nutrient_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.nutrient', 'shared');

-- ---------------------------------------------------------------------
-- পণ্যের পুষ্টিমান — সব as-fed, প্রতি কেজিতে
-- ---------------------------------------------------------------------
create table master.item_nutrient (
  item_nutrient_no uuid primary key default core.uuidv7(),
  organization_no  uuid,
  item_no          uuid not null references master.item(item_no) on delete cascade,
  nutrient_no      uuid not null references master.nutrient(nutrient_no),
  value_per_kg     numeric(16,6) not null check (value_per_kg >= 0),
  source_note_bn   text,     -- কোথা থেকে পাওয়া: ল্যাব রিপোর্ট, সরবরাহকারীর তথ্য, বইয়ের গড়
  is_lab_tested    boolean not null default false,
  tested_on        date,
  like core.ss_row_template including all
);
create unique index ux_item_nutrient on master.item_nutrient (item_no, nutrient_no)
  where ss_deleted_flag = false;
create index ix_item_nutrient_nut on master.item_nutrient (nutrient_no);
select core.ss_apply('master.item_nutrient', 'shared');

-- শুধু খাদ্যদ্রব্যেই পুষ্টিমান থাকতে পারে
create or replace function master.item_nutrient_guard()
returns trigger language plpgsql as $$
declare v_is_feed boolean;
begin
  select is_feed into v_is_feed from master.item where item_no = new.item_no;
  if not v_is_feed then
    raise exception 'পুষ্টিমান শুধু খাদ্যদ্রব্যে দেওয়া যায়' using errcode = 'check_violation';
  end if;
  return new;
end $$;

create trigger item_nutrient_guard_biu before insert or update on master.item_nutrient
  for each row execute function master.item_nutrient_guard();

-- ---------------------------------------------------------------------
-- সুবিধার ভিউ: পণ্যের পুষ্টিমান প্রশস্ত আকারে দেখা
-- ---------------------------------------------------------------------
create view master.v_item_nutrient as
select i.item_no,
       i.organization_no,
       i.item_code,
       i.name_bn      as item_name_bn,
       i.item_type,
       n.nutrient_code,
       n.name_bn      as nutrient_name_bn,
       n.nutrient_group,
       n.value_uom_code,
       inut.value_per_kg,
       inut.is_lab_tested
  from master.item i
  join master.item_nutrient inut on inut.item_no = i.item_no and inut.ss_deleted_flag = false
  join master.nutrient n on n.nutrient_no = inut.nutrient_no
 where i.ss_deleted_flag = false;

grant select on master.v_item_nutrient to farmerp_app, farmerp_readonly;
