-- =====================================================================
-- 03_master_lookup.sql — সংকেত তালিকা (lookup)
--
-- নীতি: যে তালিকা খামারি নিজে বাড়াতে চাইতে পারে, সেটা টেবিল।
-- যে তালিকা ব্যবসায়িক যুক্তির অংশ (যেমন tracking_mode) সেটা CHECK constraint,
-- কারণ সেখানে নতুন মান যোগ হলে কোডও বদলাতে হবে।
-- সব লুকআপ 'shared' scope — গ্লোবাল সারি (organization_no IS NULL) সবাই পায়,
-- খামারি নিজের সারি যোগ করলে সেটা শুধু তারই।
-- =====================================================================

-- ---------------------------------------------------------------------
-- ঘরের ধরন — মুরগির শেড থেকে গোয়ালঘর, বাথান, পুকুর, হ্যাচারি পর্যন্ত
-- ---------------------------------------------------------------------
create table master.house_type (
  house_type_no   uuid primary key default core.uuidv7(),
  organization_no uuid,
  house_type_code citext not null,
  name_bn         text not null,
  name_en         text not null,
  animal_class    text not null
      check (animal_class in ('poultry','ruminant','aquaculture','mixed','support')),
  sort_order      smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_house_type_code on master.house_type
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), house_type_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.house_type', 'shared');

-- ---------------------------------------------------------------------
-- পালন পদ্ধতি — বাংলাদেশে এটাই খরচ ও উৎপাদনের সবচেয়ে বড় নির্ধারক
-- ---------------------------------------------------------------------
create table master.rearing_system (
  rearing_system_no   uuid primary key default core.uuidv7(),
  organization_no     uuid,
  rearing_system_code citext not null,
  name_bn             text not null,
  name_en             text not null,
  sort_order          smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_rearing_system_code on master.rearing_system
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), rearing_system_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.rearing_system', 'shared');

-- ---------------------------------------------------------------------
-- উৎপাদনের উদ্দেশ্য — একই জাত ভিন্ন উদ্দেশ্যে পালা হয়, আর উদ্দেশ্যই
-- ঠিক করে কোন মেট্রিক প্রযোজ্য (ব্রয়লারে ডিম নেই, লেয়ারে ADG গৌণ)
-- ---------------------------------------------------------------------
create table master.production_purpose (
  production_purpose_no   uuid primary key default core.uuidv7(),
  organization_no         uuid,
  production_purpose_code citext not null,
  name_bn                 text not null,
  name_en                 text not null,
  -- কোন ধরনের ফলন আসে — মেট্রিক প্রযোজ্যতার ভিত্তি
  yields_meat  boolean not null default false,
  yields_egg   boolean not null default false,
  yields_milk  boolean not null default false,
  yields_young boolean not null default false,   -- বাচ্চা/ডিওসি উৎপাদন
  yields_draft boolean not null default false,   -- হালচাষ/গাড়ি টানা
  sort_order   smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_prod_purpose_code on master.production_purpose
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), production_purpose_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.production_purpose', 'shared');

-- ---------------------------------------------------------------------
-- চলাচলের ধরন (movement type)
--
-- এটা স্কিমার সবচেয়ে গুরুত্বপূর্ণ লুকআপ। খামারে প্রাণীর সংখ্যা যেভাবেই
-- বদলাক — জন্ম, ক্রয়, মৃত্যু, বিক্রি, কুরবানি, নিজেরা খাওয়া, শিয়ালে নেওয়া —
-- প্রতিটাই এখানে একটা ধরন। সংখ্যা সরাসরি কোথাও আপডেট হয় না, প্রতিটা
-- পরিবর্তন একটা সারি। ফলে যেকোনো তারিখের স্টক পুনর্গঠন করা যায়।
-- ---------------------------------------------------------------------
create table master.movement_type (
  movement_type_no   uuid primary key default core.uuidv7(),
  organization_no    uuid,
  movement_type_code citext not null,
  name_bn            text not null,
  name_en            text not null,
  direction          smallint not null check (direction in (-1, 1)),  -- 1=ঢোকা, -1=বেরোনো
  -- শ্রেণিবিন্যাস: রিপোর্ট ও হিসাবের পোস্টিং এগুলোর উপর নির্ভর করে
  is_mortality          boolean not null default false,  -- মড়ক হারে গণ্য হবে
  -- কালিং মড়ক নয়। খোঁড়া, রুগ্‌ণ বা কম উৎপাদনশীল পাখি/প্রাণী ইচ্ছাকৃতভাবে
  -- সরানো হয় — এটা ব্যবস্থাপনার সিদ্ধান্ত, দুর্ঘটনা নয়। পোল্ট্রির আদর্শ
  -- হিসাবে দুটো আলাদা রিপোর্ট হয়:  অবক্ষয় (depletion) = মড়ক + কালিং।
  -- একসাথে মিশিয়ে ফেললে খামারি বুঝতে পারবে না সমস্যাটা রোগ না নির্বাচন।
  is_culling            boolean not null default false,
  is_sale               boolean not null default false,  -- আয়
  is_purchase           boolean not null default false,  -- সম্পদ ক্রয়
  is_internal_transfer  boolean not null default false,  -- শাখান্তর, বাইরে যায় না
  is_home_consumption   boolean not null default false,  -- পারিবারিক ভোগ
  is_donation           boolean not null default false,  -- কুরবানি/সদকা/জাকাত
  requires_counterparty boolean not null default false,  -- ক্রেতা/বিক্রেতা লাগবে
  requires_amount       boolean not null default false,  -- টাকার অঙ্ক লাগবে
  requires_cause        boolean not null default false,  -- মৃত্যুর কারণ লাগবে
  sort_order            smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_movement_type_code on master.movement_type
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), movement_type_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.movement_type', 'shared');

-- মড়ককে আয় বা ক্রয় বলা যাবে না — পরস্পরবিরোধী সংকেত আটকাই
alter table master.movement_type add constraint ck_movement_type_coherent check (
      (case when is_mortality then 1 else 0 end
     + case when is_culling then 1 else 0 end
     + case when is_sale then 1 else 0 end
     + case when is_purchase then 1 else 0 end
     + case when is_internal_transfer then 1 else 0 end
     + case when is_home_consumption then 1 else 0 end
     + case when is_donation then 1 else 0 end) <= 1
);

-- মড়ক ও দান কখনো "ঢোকা" হতে পারে না
alter table master.movement_type add constraint ck_movement_type_direction check (
  not ((is_mortality or is_culling or is_sale or is_home_consumption or is_donation)
       and direction = 1)
);
alter table master.movement_type add constraint ck_movement_type_purchase_in check (
  not (is_purchase and direction = -1)
);
