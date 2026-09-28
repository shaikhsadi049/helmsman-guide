-- =====================================================================
-- 06_master_health.sql — রোগ, মৃত্যুর কারণ, টিকা, টিকার সূচি
--
-- master.disease টেবিলটা শুধু সংক্রামক রোগ নয় — মৃত্যুর *সব* কারণ ধরে:
-- হিট স্ট্রেস, শিয়ালে নেওয়া, চাপাচাপিতে মারা যাওয়া, বিষক্রিয়া, দুর্ঘটনা।
-- কারণ মড়কের কারণ বিশ্লেষণে এগুলো একই তালিকায় লাগে, আর বাংলাদেশে
-- গ্রীষ্মে হিট স্ট্রেস ও শিয়াল/কুকুর বাস্তবেই বড় কারণ।
-- =====================================================================

create table master.disease (
  disease_no      uuid primary key default core.uuidv7(),
  organization_no uuid,
  disease_code    citext not null,
  name_bn         text not null,
  name_en         text not null,
  cause_type      text not null
      check (cause_type in ('viral','bacterial','parasitic','fungal','protozoal',
                            'nutritional','metabolic','toxic','environmental',
                            'predation','traumatic','genetic','culling','unknown')),
  -- প্রাণিসম্পদ অধিদপ্তরে জানানো বাধ্যতামূলক (বার্ড ফ্লু, তড়কা, ক্ষুরারোগ)
  is_notifiable   boolean not null default false,
  is_zoonotic     boolean not null default false,   -- মানুষে ছড়ায়
  is_contagious   boolean not null default true,
  typical_signs_bn text,
  prevention_bn    text,
  sort_order      smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_disease_code on master.disease
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), disease_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.disease', 'shared');

-- কোন রোগ কোন প্রজাতিতে হয় — ছাগলের PPR গরুতে নেই, গরুর ক্ষুরারোগ
-- মুরগিতে নেই। সারি না থাকলে "সব প্রজাতিতে প্রযোজ্য" ধরা হয়।
create table master.disease_species (
  disease_species_no uuid primary key default core.uuidv7(),
  organization_no    uuid,
  disease_no         uuid not null references master.disease(disease_no) on delete cascade,
  species_no         uuid not null references master.species(species_no),
  like core.ss_row_template including all
);
create unique index ux_disease_species on master.disease_species (disease_no, species_no)
  where ss_deleted_flag = false;
select core.ss_apply('master.disease_species', 'shared');

-- মৃতদেহ নিষ্পত্তির পদ্ধতি — বায়োসিকিউরিটির অংশ, আর বার্ড ফ্লুর সময়
-- এটার নথি রাখা আইনগত দায়
create table master.disposal_method (
  disposal_method_no   uuid primary key default core.uuidv7(),
  organization_no      uuid,
  disposal_method_code citext not null,
  name_bn              text not null,
  name_en              text not null,
  is_biosecure         boolean not null default true,
  sort_order           smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_disposal_method_code on master.disposal_method
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), disposal_method_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.disposal_method', 'shared');

-- ---------------------------------------------------------------------
-- টিকা
-- ---------------------------------------------------------------------
create table master.vaccine (
  vaccine_no      uuid primary key default core.uuidv7(),
  organization_no uuid,
  vaccine_code    citext not null,
  name_bn         text not null,
  name_en         text not null,
  disease_no      uuid references master.disease(disease_no),
  vaccine_kind    text not null default 'live'
      check (vaccine_kind in ('live','killed','live_attenuated','vector','toxoid','other')),
  route           text not null
      check (route in ('drinking_water','eye_drop','nasal_drop','spray','wing_web',
                       'subcutaneous','intramuscular','oral','in_ovo','other')),
  dose_text_bn    text,
  manufacturer    text,
  -- জীবন্ত টিকা ঠান্ডা শৃঙ্খলে রাখতে হয়; লোডশেডিং-এ এটা বাস্তব ঝুঁকি
  needs_cold_chain boolean not null default true,
  booster_after_days smallint check (booster_after_days > 0),
  sort_order      smallint not null default 100,
  like core.ss_row_template including all
);
create unique index ux_vaccine_code on master.vaccine
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), vaccine_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.vaccine', 'shared');

-- ---------------------------------------------------------------------
-- টিকার সূচি (টেমপ্লেট)
--
-- প্রজাতি + উদ্দেশ্য অনুসারে বয়সভিত্তিক সূচি। ইউনিট খোলার সময়
-- টেমপ্লেট থেকে প্রকৃত তারিখ বসে যায়, আর সেখান থেকেই "আজকের কাজ"
-- তালিকায় টিকার কথা উঠে আসে। খামারে টিকার তারিখ ভুলে যাওয়া
-- মড়কের সবচেয়ে সাধারণ কারণ — তাই এটা অনুমান নয়, ডেটা।
-- ---------------------------------------------------------------------
create table master.vaccine_schedule (
  vaccine_schedule_no   uuid primary key default core.uuidv7(),
  organization_no       uuid,
  species_no            uuid not null references master.species(species_no),
  production_purpose_no uuid not null references master.production_purpose(production_purpose_no),
  schedule_code         citext not null,
  name_bn               text not null,
  name_en               text not null,
  is_default            boolean not null default false,
  source_note_bn        text,     -- কোন সূত্র থেকে নেওয়া (DLS, হ্যাচারি, BLRI)
  like core.ss_row_template including all
);
create unique index ux_vaccine_schedule_code on master.vaccine_schedule
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), schedule_code)
  where ss_deleted_flag = false;
create unique index ux_vaccine_schedule_default on master.vaccine_schedule
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), species_no, production_purpose_no)
  where is_default and ss_deleted_flag = false;
select core.ss_apply('master.vaccine_schedule', 'shared');

create table master.vaccine_schedule_line (
  vaccine_schedule_line_no uuid primary key default core.uuidv7(),
  organization_no          uuid,
  vaccine_schedule_no      uuid not null
      references master.vaccine_schedule(vaccine_schedule_no) on delete cascade,
  age_day                  integer not null check (age_day >= 0),
  age_day_to               integer check (age_day_to >= 0),   -- পরিসর হলে
  vaccine_no               uuid not null references master.vaccine(vaccine_no),
  route                    text,        -- টেমপ্লেটে ভিন্ন হলে এখানে ওভাররাইড
  dose_text_bn             text,
  is_booster               boolean not null default false,
  remarks_bn               text,
  like core.ss_row_template including all,
  constraint ck_vsl_range check (age_day_to is null or age_day_to >= age_day)
);
create unique index ux_vaccine_schedule_line
  on master.vaccine_schedule_line (vaccine_schedule_no, age_day, vaccine_no)
  where ss_deleted_flag = false;
create index ix_vsl_schedule on master.vaccine_schedule_line (vaccine_schedule_no, age_day);
select core.ss_apply('master.vaccine_schedule_line', 'shared');
