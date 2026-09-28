-- =====================================================================
-- 05_master_species.sql — প্রজাতি, জাত, জীবনচক্র, মেট্রিক
--
-- এই ফাইলটাই "সকল লাইভস্টোক" সম্ভব করে। মূল ধারণা:
--
--   প্রজাতিভেদে স্ট্রাকচার বদলায় না, মেট্রিক বদলায়।
--
-- তাই ব্রয়লার/লেয়ার/ছাগল/গরুর জন্য আলাদা টেবিল বা আলাদা কোড নেই।
-- আছে একটাই প্রজাতি তালিকা, একটাই জাত তালিকা, আর metric_applicability
-- টেবিল ঠিক করে দেয় কোন প্রজাতির কোন উদ্দেশ্যে কোন মাপ প্রযোজ্য।
-- নতুন প্রাণী যোগ করা মানে নতুন কনফিগ সারি — নতুন কোড নয়।
-- =====================================================================

-- ---------------------------------------------------------------------
-- প্রজাতি
-- ---------------------------------------------------------------------
create table master.species (
  species_no      uuid primary key default core.uuidv7(),
  organization_no uuid,
  species_code    citext not null,
  name_bn         text not null,
  name_en         text not null,
  scientific_name text,
  animal_class    text not null
      check (animal_class in ('poultry','ruminant','pseudoruminant','aquaculture','other')),

  -- ডিফল্ট ট্র্যাকিং ধরন। এই একটা ফিল্ডই ঠিক করে দেয় প্রাণীটা দলগতভাবে
  -- গোনা হবে (মুরগি, হাঁস, কোয়েল) নাকি একক হিসেবে (গাভি, ছাগল)।
  -- খামারি ইউনিট খোলার সময় বদলাতে পারে — ২০টা ছাগল দলগতভাবেও রাখা যায়।
  default_tracking_mode text not null default 'group'
      check (default_tracking_mode in ('group','individual')),

  -- শেয়ার্ড খরচ বণ্টনের ওজন (Livestock Unit)।
  -- সমন্বিত খামারে একজন শ্রমিক গরু-ছাগল-মুরগি সবই দেখে; বিদ্যুৎ, পানি,
  -- শ্রম, ভাড়া ভাগ হয় "ওজনযুক্ত প্রাণী-দিন" অনুপাতে। এই ওজন ছাড়া
  -- কোন শাখায় লাভ কোথায় লস তা কখনো বের হয় না।
  livestock_unit_weight numeric(8,4) not null default 1
      check (livestock_unit_weight > 0),

  gestation_days        smallint check (gestation_days > 0),   -- স্তন্যপায়ী
  incubation_days       smallint check (incubation_days > 0),  -- পাখি
  typical_lifespan_days integer  check (typical_lifespan_days > 0),
  sort_order            smallint not null default 100,
  note_bn               text,
  like core.ss_row_template including all,

  -- পাখির গর্ভকাল থাকে না, স্তন্যপায়ীর ডিম ফোটার সময় থাকে না
  constraint ck_species_repro check (
    not (animal_class = 'poultry' and gestation_days is not null)
  )
);
create unique index ux_species_code on master.species
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), species_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.species', 'shared');

-- ---------------------------------------------------------------------
-- জাত
--
-- সারসংক্ষেপ ফিল্ডগুলো (market_age_days, annual_egg_yield ইত্যাদি) রাখা
-- হয়েছে পর্দায় দেখানো ও ডিফল্ট মান বসানোর জন্য। দিনে-দিনে লক্ষ্যমাত্রার
-- পূর্ণ কার্ভ আলাদা টেবিলে (master.breed_standard) — কারণ Cobb 500 এর
-- ৩৫ দিনের ওজন একটা সংখ্যা নয়, ৩৫টা সংখ্যা।
-- ---------------------------------------------------------------------
create table master.breed (
  breed_no        uuid primary key default core.uuidv7(),
  organization_no uuid,
  species_no      uuid not null references master.species(species_no),
  breed_code      citext not null,
  name_bn         text not null,
  name_en         text not null,
  origin_country  text,
  breed_kind      text not null default 'exotic'
      check (breed_kind in ('indigenous','exotic','crossbred','local_cross','synthetic')),
  is_dual_purpose boolean not null default false,

  -- সারসংক্ষেপ মানদণ্ড (সবই ঐচ্ছিক — প্রজাতিভেদে প্রযোজ্যতা ভিন্ন)
  market_age_days        smallint  check (market_age_days > 0),
  market_weight_kg       numeric(8,3) check (market_weight_kg > 0),
  fcr_target             numeric(6,3) check (fcr_target > 0),
  mature_weight_male_kg  numeric(8,3) check (mature_weight_male_kg > 0),
  mature_weight_female_kg numeric(8,3) check (mature_weight_female_kg > 0),
  age_at_first_egg_days  smallint  check (age_at_first_egg_days > 0),
  annual_egg_yield       smallint  check (annual_egg_yield >= 0),
  avg_egg_weight_g       numeric(6,2) check (avg_egg_weight_g > 0),
  lactation_yield_litre  numeric(10,2) check (lactation_yield_litre >= 0),
  lactation_days         smallint  check (lactation_days > 0),
  avg_litter_size        numeric(5,2) check (avg_litter_size > 0),  -- ছাগল/ভেড়া
  note_bn                text,
  like core.ss_row_template including all
);
create unique index ux_breed_code on master.breed
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), species_no, breed_code)
  where ss_deleted_flag = false;
create index ix_breed_species on master.breed (species_no);
select core.ss_apply('master.breed', 'shared');

-- ---------------------------------------------------------------------
-- মেট্রিক সংজ্ঞা — কী কী মাপা হয়
-- ---------------------------------------------------------------------
create table master.metric_definition (
  metric_no       uuid primary key default core.uuidv7(),
  organization_no uuid,
  metric_code     citext not null,
  name_bn         text not null,
  name_en         text not null,
  category        text not null
      check (category in ('production','mortality','feed','water','weight',
                          'environment','health','labour','other')),
  value_type      text not null default 'numeric'
      check (value_type in ('numeric','integer','boolean','text')),
  default_uom_no  uuid references master.uom(uom_no),

  -- একাধিক দিনের মান একত্র করার নিয়ম। ভুল হলে রিপোর্ট ভুল:
  -- খাবার যোগ হয়, ওজনের গড় হয়, ডিমের মোট হয়, তাপমাত্রার গড় হয়।
  aggregation     text not null default 'sum'
      check (aggregation in ('sum','avg','last','max','min','none')),

  -- ড্যাশবোর্ডে তীর কোন দিকে গেলে ভালো — মড়ক কমা ভালো, ডিম বাড়া ভালো
  better_direction text not null default 'up'
      check (better_direction in ('up','down','neutral')),

  min_value       numeric,
  max_value       numeric,
  sort_order      smallint not null default 100,
  like core.ss_row_template including all,
  constraint ck_metric_range check (min_value is null or max_value is null or max_value >= min_value)
);
create unique index ux_metric_code on master.metric_definition
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), metric_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.metric_definition', 'shared');

-- ---------------------------------------------------------------------
-- মেট্রিক প্রযোজ্যতা
--
-- species_no NULL = সব প্রজাতিতে প্রযোজ্য
-- production_purpose_no NULL = সব উদ্দেশ্যে প্রযোজ্য
-- এভাবে "মড়ক সবার", "ডিম শুধু লেয়ার/ব্রিডারে", "দুধ শুধু ডেইরিতে"
-- — সব একই টেবিলে, কোনো if-else ছাড়া।
-- ---------------------------------------------------------------------
create table master.metric_applicability (
  metric_applicability_no uuid primary key default core.uuidv7(),
  organization_no         uuid,
  metric_no               uuid not null references master.metric_definition(metric_no) on delete cascade,
  species_no              uuid references master.species(species_no),
  production_purpose_no   uuid references master.production_purpose(production_purpose_no),
  is_required             boolean not null default false,
  is_daily                boolean not null default true,   -- false = মাঝে মাঝে (ওজন স্যাম্পল)
  sort_order              smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_metric_applicability on master.metric_applicability (
  metric_no,
  coalesce(species_no,'00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(production_purpose_no,'00000000-0000-0000-0000-000000000000'::uuid)
) where ss_deleted_flag = false;
select core.ss_apply('master.metric_applicability', 'shared');

-- ---------------------------------------------------------------------
-- জীবনচক্র টেমপ্লেট
--
-- ব্রয়লার ৩৫ দিনের এক দফা, লেয়ার ৭২–৮০ সপ্তাহের ব্রুডিং→গ্রোয়িং→লেয়িং,
-- সোনালি মাঝামাঝি, গাভি বাছুর→বকনা→দুগ্ধবতী→শুষ্ক। এগুলো আলাদা কোড নয়,
-- আলাদা টেমপ্লেট।
-- ---------------------------------------------------------------------
create table master.lifecycle_template (
  lifecycle_template_no uuid primary key default core.uuidv7(),
  organization_no        uuid,
  species_no             uuid not null references master.species(species_no),
  production_purpose_no  uuid not null references master.production_purpose(production_purpose_no),
  template_code          citext not null,
  name_bn                text not null,
  name_en                text not null,
  tracking_mode          text not null
      check (tracking_mode in ('group','individual')),
  total_days             integer check (total_days > 0),
  is_default             boolean not null default false,
  like core.ss_row_template including all
);
create unique index ux_lifecycle_template_code on master.lifecycle_template
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), template_code)
  where ss_deleted_flag = false;
create unique index ux_lifecycle_default on master.lifecycle_template
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), species_no, production_purpose_no)
  where is_default and ss_deleted_flag = false;
select core.ss_apply('master.lifecycle_template', 'shared');

-- পর্যায়গুলো দিনের পরিসর দিয়ে সংজ্ঞায়িত, এবং exclusion constraint
-- নিশ্চিত করে একই টেমপ্লেটের দুই পর্যায় কখনো একে অন্যের উপর পড়বে না।
create table master.lifecycle_phase (
  lifecycle_phase_no    uuid primary key default core.uuidv7(),
  organization_no       uuid,
  lifecycle_template_no uuid not null
      references master.lifecycle_template(lifecycle_template_no) on delete cascade,
  phase_code            citext not null,
  name_bn               text not null,
  name_en               text not null,
  from_day              integer not null check (from_day >= 0),
  to_day                integer,                      -- NULL = খোলা প্রান্ত
  sort_order            smallint not null default 100,
  like core.ss_row_template including all,
  constraint ck_phase_range check (to_day is null or to_day >= from_day),
  constraint ex_phase_no_overlap exclude using gist (
    lifecycle_template_no with =,
    int4range(from_day, coalesce(to_day, 2147483646), '[]') with &&
  )
);
create unique index ux_lifecycle_phase_code
  on master.lifecycle_phase (lifecycle_template_no, phase_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.lifecycle_phase', 'shared');

-- ---------------------------------------------------------------------
-- জাতের মানদণ্ড কার্ভ — বয়স অনুসারে লক্ষ্যমাত্রা
--
-- এটাই "আমার ব্যাচ কি ঠিক চলছে?" প্রশ্নের উত্তর দেয়। Cobb 500 এর
-- ২১ দিনে ১.০০ কেজি হওয়া উচিত — আপনার হয়েছে ০.৮৫, অর্থাৎ ১৫% পিছিয়ে।
-- ---------------------------------------------------------------------
create table master.breed_standard (
  breed_standard_no uuid primary key default core.uuidv7(),
  organization_no   uuid,
  breed_no          uuid not null references master.breed(breed_no) on delete cascade,
  metric_no         uuid not null references master.metric_definition(metric_no),
  age_day           integer not null check (age_day >= 0),
  target_value      numeric(16,4) not null,
  tolerance_pct     numeric(6,2) check (tolerance_pct >= 0),
  like core.ss_row_template including all
);
create unique index ux_breed_standard on master.breed_standard (breed_no, metric_no, age_day)
  where ss_deleted_flag = false;
select core.ss_apply('master.breed_standard', 'shared');
