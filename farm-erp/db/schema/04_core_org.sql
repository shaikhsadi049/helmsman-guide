-- =====================================================================
-- 04_core_org.sql — প্রতিষ্ঠান, ব্যবহারকারী, খামার কাঠামো, অর্থবছর
--
-- অনুক্রম:  organization → farm → house → pen
-- একজন মালিকের একাধিক খামার থাকতে পারে (সমন্বিত খামারে খুব সাধারণ:
-- বাড়ির উঠানে মুরগি, একটু দূরে গোয়ালঘর, চরে বাথান)।
-- =====================================================================

-- বাংলাদেশি মোবাইল নম্বর — একবার সংজ্ঞায়িত, সব টেবিলে এক নিয়ম
create domain core.bd_mobile as text
  check (value is null or value ~ '^01[3-9][0-9]{8}$');
comment on domain core.bd_mobile is '১১ অঙ্কের বাংলাদেশি মোবাইল, যেমন 01712345678';

-- ---------------------------------------------------------------------
-- প্রতিষ্ঠান (টেন্যান্ট মূল)
--
-- নাম COMPANY_NO নয়, ORGANIZATION_NO — কারণ বাংলাদেশের বেশিরভাগ খামার
-- কোম্পানি নয়, ব্যক্তিমালিকানা বা পারিবারিক অংশীদারি।
--
-- লক্ষ্য করুন: RLS-এর কারণে অ্যাপ নিজে নতুন organization তৈরি করতে পারে না
-- (যে org এখনো নেই, তার no সেশনে বসানো যায় না)। নতুন খামার নিবন্ধন
-- প্ল্যাটফর্ম-স্তরের কাজ, superuser/প্রভিশনিং সার্ভিসের দায়িত্ব। এটা
-- সীমাবদ্ধতা নয়, উদ্দেশ্যমূলক।
-- ---------------------------------------------------------------------
create table core.organization (
  organization_no   uuid primary key default core.uuidv7(),
  org_code          citext not null,
  org_name          text   not null,
  legal_form        text   not null default 'individual'
      check (legal_form in ('individual','partnership','company','cooperative','ngo','government')),
  owner_name        text,
  mobile            core.bd_mobile,
  email             citext,

  -- ঠিকানা (বাংলাদেশি প্রশাসনিক স্তর)
  village           text,
  union_name        text,
  upazila           text,
  district          text,
  division          text,
  postcode          text,

  -- নিবন্ধন
  bin_no            text,      -- ভ্যাট নিবন্ধন
  tin_no            text,      -- আয়কর
  dls_reg_no        text,      -- প্রাণিসম্পদ অধিদপ্তরের খামার নিবন্ধন

  -- আঞ্চলিক সেটিং
  base_currency           char(3)  not null default 'BDT',
  fiscal_year_start_month smallint not null default 7   -- জুলাই–জুন
      check (fiscal_year_start_month between 1 and 12),
  time_zone               text     not null default 'Asia/Dhaka',
  default_language        text     not null default 'bn' check (default_language in ('bn','en')),

  -- দুই ব্যবহার-ধরন, একই ডেটা মডেল:
  --   household  = পারিবারিক/সমন্বিত — সহজ পর্দা, কম ফিল্ড
  --   commercial = বাণিজ্যিক — ব্যাচ কস্টিং, ডাবল এন্ট্রি, পে-রোল
  operating_mode    text not null default 'household'
      check (operating_mode in ('household','commercial')),

  subscription_plan       text,
  subscription_valid_till date,

  like core.ss_row_template including all
);
create unique index ux_organization_code on core.organization (org_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.organization', 'root');

-- ---------------------------------------------------------------------
-- ব্যবহারকারী
--
-- organization_no NULL রাখা যায় — সেটা প্ল্যাটফর্ম-স্তরের ব্যবহারকারী
-- (যেমন core.system_user_no(), যার নামে মাইগ্রেশন ও গ্লোবাল সিড হয়)।
--
-- ইচ্ছাকৃত সিদ্ধান্ত: ss_created_by / ss_modified_by তে app_user এর
-- ফরেন কী দেওয়া হয়নি। দুই কারণে —
--   ১. প্রতিটা INSERT-এ একটা অতিরিক্ত যাচাই, উচ্চ-ভলিউম দৈনিক লগে ব্যয়বহুল
--   ২. ব্যবহারকারী মুছলে পুরো অডিট ইতিহাস আটকে যেত
-- পরিচয় মেলানো হয় রিপোর্টে JOIN দিয়ে, constraint দিয়ে নয়।
-- ---------------------------------------------------------------------
create table core.app_user (
  user_no           uuid primary key default core.uuidv7(),
  organization_no   uuid references core.organization(organization_no),
  login_id          citext not null,
  full_name         text   not null,
  mobile            core.bd_mobile,
  email             citext,
  password_hash     text,
  pin_hash          text,          -- মাঠে দ্রুত লগইনের জন্য ৪–৬ অঙ্কের পিন
  user_type         text   not null default 'worker'
      check (user_type in ('platform_admin','owner','manager','accountant','worker','veterinarian','viewer')),
  preferred_language text  not null default 'bn' check (preferred_language in ('bn','en')),
  last_login_at     timestamptz,
  failed_attempts   smallint not null default 0,
  locked_till       timestamptz,
  like core.ss_row_template including all
);
create unique index ux_app_user_login on core.app_user (login_id)
  where ss_deleted_flag = false;
select core.ss_apply('core.app_user', 'shared');

-- সিস্টেম ব্যবহারকারী — মাইগ্রেশন ও গ্লোবাল সিড ডেটার কর্তা।
-- RLS সক্রিয় হওয়ার আগেই বসাতে হয়, তাই এখানেই।
insert into core.app_user (user_no, organization_no, login_id, full_name, user_type, ss_created_by)
values (core.system_user_no(), null, 'system', 'সিস্টেম', 'platform_admin', core.system_user_no())
on conflict (user_no) do nothing;

-- ---------------------------------------------------------------------
-- ভূমিকা ও অনুমতি
-- ---------------------------------------------------------------------
create table core.role (
  role_no         uuid primary key default core.uuidv7(),
  organization_no uuid,
  role_code       citext not null,
  name_bn         text not null,
  name_en         text not null,
  is_system       boolean not null default false,
  like core.ss_row_template including all
);
create unique index ux_role_code on core.role
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), role_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.role', 'shared');

create table core.role_permission (
  role_permission_no uuid primary key default core.uuidv7(),
  organization_no    uuid,
  role_no            uuid not null references core.role(role_no) on delete cascade,
  permission_code    citext not null,   -- যেমন 'daily_log.write', 'accounting.post'
  like core.ss_row_template including all
);
create unique index ux_role_permission on core.role_permission (role_no, permission_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.role_permission', 'shared');

create table core.user_role (
  user_role_no    uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  user_no         uuid not null references core.app_user(user_no) on delete cascade,
  role_no         uuid not null references core.role(role_no),
  like core.ss_row_template including all
);
create unique index ux_user_role on core.user_role (user_no, role_no)
  where ss_deleted_flag = false;
select core.ss_apply('core.user_role', 'tenant');

-- ---------------------------------------------------------------------
-- খামার
-- ---------------------------------------------------------------------
create table core.farm (
  farm_no         uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  farm_code       citext not null,
  farm_name       text   not null,
  established_on  date,

  village         text,
  union_name      text,
  upazila         text,
  district        text,
  latitude        numeric(9,6)  check (latitude  between -90  and 90),
  longitude       numeric(9,6)  check (longitude between -180 and 180),

  -- জমির পরিমাণ শতকে (বাংলাদেশের প্রচলিত একক; ১ একর = ১০০ শতক)
  land_area_decimal numeric(12,3) check (land_area_decimal >= 0),
  is_leased         boolean not null default false,
  monthly_rent      numeric(14,2) check (monthly_rent >= 0),

  like core.ss_row_template including all
);
create unique index ux_farm_code on core.farm (organization_no, farm_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.farm', 'tenant');

-- ---------------------------------------------------------------------
-- ঘর / শেড / গোয়াল / বাথান / পুকুর
-- ---------------------------------------------------------------------
create table core.house (
  house_no          uuid primary key default core.uuidv7(),
  organization_no   uuid not null references core.organization(organization_no),
  farm_no           uuid not null references core.farm(farm_no),
  house_code        citext not null,
  house_name        text   not null,
  house_type_no     uuid not null references master.house_type(house_type_no),
  rearing_system_no uuid references master.rearing_system(rearing_system_no),

  capacity_qty      integer check (capacity_qty > 0),
  length_ft         numeric(8,2) check (length_ft > 0),
  width_ft          numeric(8,2) check (width_ft  > 0),
  height_ft         numeric(8,2) check (height_ft > 0),
  -- মেঝের ক্ষেত্রফল হাতে লেখা হয় না, হিসাব করা হয় — ভুলের সুযোগ বন্ধ
  floor_area_sqft   numeric(12,2) generated always as (length_ft * width_ft) stored,

  construction_type text check (construction_type in
      ('pucca','semi_pucca','tin_shed','bamboo','open_yard','other')),
  ventilation_type  text check (ventilation_type in
      ('open_sided','environment_controlled','tunnel','semi_open','open_grazing')),
  has_generator     boolean not null default false,   -- লোডশেডিং বাস্তবতা
  commissioned_on   date,
  like core.ss_row_template including all
);
create unique index ux_house_code on core.house (organization_no, house_code)
  where ss_deleted_flag = false;
create index ix_house_farm on core.house (organization_no, farm_no);
select core.ss_apply('core.house', 'tenant');

-- ---------------------------------------------------------------------
-- খোপ / খাঁচার সারি / স্টল — ঘরের ভেতরের ভাগ
-- লেয়ার কেজে সারি-ভিত্তিক ডিম সংগ্রহ, গোয়ালে গরুর স্টল
-- ---------------------------------------------------------------------
create table core.pen (
  pen_no          uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  house_no        uuid not null references core.house(house_no),
  pen_code        citext not null,
  pen_name        text,
  capacity_qty    integer check (capacity_qty > 0),
  tier_count      smallint check (tier_count > 0),   -- কেজের তলা সংখ্যা
  like core.ss_row_template including all
);
create unique index ux_pen_code on core.pen (organization_no, house_no, pen_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.pen', 'tenant');

-- ---------------------------------------------------------------------
-- ব্যবহারকারী কোন খামার দেখতে পাবে
-- ---------------------------------------------------------------------
create table core.user_farm_access (
  user_farm_access_no uuid primary key default core.uuidv7(),
  organization_no     uuid not null references core.organization(organization_no),
  user_no             uuid not null references core.app_user(user_no) on delete cascade,
  farm_no             uuid not null references core.farm(farm_no),
  can_write           boolean not null default false,
  like core.ss_row_template including all
);
create unique index ux_user_farm_access on core.user_farm_access (user_no, farm_no)
  where ss_deleted_flag = false;
select core.ss_apply('core.user_farm_access', 'tenant');

-- ---------------------------------------------------------------------
-- অর্থবছর ও পিরিয়ড — বাংলাদেশে জুলাই থেকে জুন
--
-- exclusion constraint নিশ্চিত করে একই প্রতিষ্ঠানে দুটো অর্থবছরের
-- তারিখ কখনো একে অন্যের উপর পড়বে না। অ্যাপ কোডে যাচাই করলে
-- একদিন কোথাও ফাঁক থেকে যেত।
-- ---------------------------------------------------------------------
create table core.fiscal_year (
  fiscal_year_no  uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  fy_code         citext not null,        -- '2026-27'
  start_date      date not null,
  end_date        date not null,
  is_closed       boolean not null default false,
  closed_by       uuid,
  closed_time     timestamptz,
  like core.ss_row_template including all,
  constraint ck_fy_range check (end_date > start_date),
  constraint ex_fy_no_overlap exclude using gist (
    organization_no with =,
    daterange(start_date, end_date, '[]') with &&
  )
);
create unique index ux_fiscal_year_code on core.fiscal_year (organization_no, fy_code)
  where ss_deleted_flag = false;
select core.ss_apply('core.fiscal_year', 'tenant');

create table core.fiscal_period (
  fiscal_period_no uuid primary key default core.uuidv7(),
  organization_no  uuid not null references core.organization(organization_no),
  fiscal_year_no   uuid not null references core.fiscal_year(fiscal_year_no) on delete cascade,
  period_no        smallint not null check (period_no between 1 and 12),
  start_date       date not null,
  end_date         date not null,
  is_locked        boolean not null default false,   -- লক হলে ওই সময়ে আর এন্ট্রি নয়
  like core.ss_row_template including all,
  constraint ck_period_range check (end_date >= start_date),
  constraint ex_period_no_overlap exclude using gist (
    fiscal_year_no with =,
    daterange(start_date, end_date, '[]') with &&
  )
);
create unique index ux_fiscal_period on core.fiscal_period (fiscal_year_no, period_no)
  where ss_deleted_flag = false;
select core.ss_apply('core.fiscal_period', 'tenant');
