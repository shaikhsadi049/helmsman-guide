-- =====================================================================
-- 08_vaccine.sql — টিকা ও টিকার সূচি (গ্লোবাল সিড)
--
-- ⚠ গুরুত্বপূর্ণ সতর্কতা
-- নিচের সূচিগুলো বাংলাদেশে *প্রচলিত* অনুশীলনের নির্দেশক রূপ। এগুলো
-- চিকিৎসা-পরামর্শ নয়। প্রকৃত সূচি নির্ভর করে:
--   • হ্যাচারি ইতিমধ্যে কোন টিকা দিয়ে দিয়েছে (মারেক্স প্রায়ই দেওয়া থাকে)
--   • এলাকার রোগের চাপ ও সাম্প্রতিক প্রাদুর্ভাব
--   • টিকার ব্র্যান্ড, স্ট্রেইন ও প্রস্তুতকারকের নির্দেশনা
--   • বাচ্চার মাতৃ-অ্যান্টিবডির মাত্রা
-- তাই প্রতিটা খামারে সূচি চূড়ান্ত করতে হবে নিবন্ধিত পশুচিকিৎসক অথবা
-- উপজেলা প্রাণিসম্পদ কর্মকর্তার পরামর্শে। সিস্টেম টেমপ্লেট দেয়, সিদ্ধান্ত নয়।
-- =====================================================================

create temporary table _vac (
  vaccine_code text, name_bn text, name_en text, disease_code text,
  kind text, route text, dose_bn text, cold_chain boolean, booster_days int, sort_order int
);

insert into _vac values
-- মুরগি
('MAREK_HVT','মারেক্স (HVT)','Marek''s HVT','MAREK','live_attenuated','subcutaneous',
  'একদিন বয়সে ঘাড়ের চামড়ার নিচে, সাধারণত হ্যাচারিতেই দেওয়া হয়',true,null,10),
('BCRDV','বিসিআরডিভি','Baby Chick Ranikhet Disease Vaccine','ND','live','eye_drop',
  '১ ফোঁটা চোখে',true,null,11),
('RDV_LASOTA','আরডিভি — লাসোটা','ND Lasota','ND','live','drinking_water',
  'খাবার পানিতে; আগে ২ ঘণ্টা পানি বন্ধ রাখুন',true,null,12),
('RDV_R2B','আরডিভি — আর২বি (মুক্তেশ্বর)','ND R2B (Mukteswar)','ND','live','intramuscular',
  'রানের মাংসে ০.৫ মিলি',true,null,13),
('ND_KILLED','রানীক্ষেত কিলড','ND Inactivated','ND','killed','intramuscular',
  '০.৫ মিলি',true,null,14),
('IBD_LIVE','গামবোরো (লাইভ)','IBD Live (Intermediate)','IBD','live','drinking_water',
  'খাবার পানিতে',true,null,15),
('IBD_KILLED','গামবোরো কিলড','IBD Inactivated','IBD','killed','intramuscular',
  '০.৫ মিলি',true,null,16),
('IB_H120','আইবি এইচ১২০','IB H120','IB','live','drinking_water','খাবার পানিতে',true,null,17),
('IB_KILLED','আইবি কিলড','IB Inactivated','IB','killed','intramuscular','০.৫ মিলি',true,null,18),
('FOWL_POX_V','ফাউল পক্স','Fowl Pox','FOWL_POX','live','wing_web',
  'ডানার চামড়ায় সুচ ফুটিয়ে',true,null,19),
('FOWL_CHOLERA_V','ফাউল কলেরা','Fowl Cholera','FOWL_CHOLERA','killed','subcutaneous',
  '০.৫ মিলি চামড়ার নিচে',true,21,20),
('CORYZA_V','করাইজা','Infectious Coryza','CORYZA','killed','intramuscular','০.৫ মিলি',true,null,21),
('EDS_KILLED','ইডিএস কিলড','EDS Inactivated','EDS','killed','intramuscular','০.৫ মিলি',true,null,22),
('ILT_V','আইএলটি','ILT','ILT','live','eye_drop','১ ফোঁটা চোখে',true,null,23),
('AI_KILLED','বার্ড ফ্লু (কিলড)','Avian Influenza Inactivated','AI','killed','subcutaneous',
  '০.৫ মিলি — বাংলাদেশে সরকারি অনুমোদন ও নির্দেশনা সাপেক্ষে',true,null,24),
-- হাঁস
('DUCK_PLAGUE_V','ডাক প্লেগ','Duck Plague','DUCK_PLAGUE','live','intramuscular',
  '১ মিলি রানের মাংসে',true,null,30),
('DUCK_CHOLERA_V','ডাক কলেরা','Duck Cholera','FOWL_CHOLERA','killed','subcutaneous',
  '১ মিলি চামড়ার নিচে',true,21,31),
-- গরু ও মহিষ
('FMD_V','ক্ষুরারোগ (এফএমডি)','FMD Vaccine','FMD','killed','intramuscular',
  '২ মিলি ঘাড়ের মাংসে',true,28,40),
('ANTHRAX_V','তড়কা','Anthrax Spore Vaccine','ANTHRAX','live_attenuated','subcutaneous',
  '১ মিলি চামড়ার নিচে; বছরে একবার',true,null,41),
('BQ_V','বাদলা','Black Quarter Vaccine','BQ','killed','subcutaneous',
  '৫ মিলি; বছরে একবার',true,null,42),
('HS_V','গলাফুলা','HS Vaccine','HS','killed','subcutaneous',
  '২ মিলি; বর্ষার আগে বছরে একবার',true,null,43),
('LSD_V','লাম্পি স্কিন ডিজিজ','LSD Vaccine','LSD','live_attenuated','subcutaneous',
  '২ মিলি',true,null,44),
-- ছাগল ও ভেড়া
('PPR_V','পিপিআর','PPR Vaccine','PPR','live_attenuated','subcutaneous',
  '১ মিলি; একবার দিলে ৩ বছর সুরক্ষা',true,null,50),
('GOAT_POX_V','ছাগলের বসন্ত','Goat Pox Vaccine','GOAT_POX','live_attenuated','subcutaneous',
  '১ মিলি',true,null,51),
('TETANUS_TT','ধনুষ্টংকার টক্সয়েড','Tetanus Toxoid','TETANUS','toxoid','intramuscular',
  '০.৫ মিলি; খাসি করার আগে',true,null,52),
('RABIES_V','জলাতঙ্ক','Rabies Vaccine','RABIES','killed','intramuscular',
  'কামড়ালে সাথে সাথে পশুচিকিৎসকের পরামর্শে',true,null,53);

insert into master.vaccine
  (vaccine_code, name_bn, name_en, disease_no, vaccine_kind, route,
   dose_text_bn, needs_cold_chain, booster_after_days, sort_order)
select v.vaccine_code, v.name_bn, v.name_en,
       (select disease_no from master.disease
         where organization_no is null and disease_code = v.disease_code::citext),
       v.kind, v.route, v.dose_bn, v.cold_chain, v.booster_days, v.sort_order
from _vac v
where not exists (select 1 from master.vaccine x
  where x.organization_no is null and x.vaccine_code = v.vaccine_code::citext);

drop table _vac;

-- ---------------------------------------------------------------------
-- সূচি (টেমপ্লেট)
-- ---------------------------------------------------------------------
create temporary table _sch (
  species_code text, purpose_code text, schedule_code text, name_bn text, name_en text
);
create temporary table _schl (
  schedule_code text, age_day int, age_day_to int, vaccine_code text,
  is_booster boolean, remarks_bn text
);

insert into _sch values
('CHICKEN','BROILER',        'SCH_BROILER',  'ব্রয়লার টিকার সূচি',        'Broiler Schedule'),
('CHICKEN','LAYER',          'SCH_LAYER',    'লেয়ার টিকার সূচি',         'Layer Schedule'),
('CHICKEN','DUAL_POULTRY',   'SCH_SONALI',   'সোনালি/দেশি ক্রস টিকার সূচি','Sonali Schedule'),
('CHICKEN','COCKEREL',       'SCH_COCKEREL', 'ককরেল টিকার সূচি',         'Cockerel Schedule'),
('DUCK','EGG_DUCK',          'SCH_DUCK',     'হাঁস টিকার সূচি',           'Duck Schedule'),
('CATTLE','DAIRY',           'SCH_CATTLE',   'গরু টিকার সূচি',           'Cattle Schedule'),
('CATTLE','FATTENING',       'SCH_CATTLE_FAT','হৃষ্টপুষ্টকরণ গরুর টিকার সূচি','Cattle Fattening Schedule'),
('GOAT','BREEDING_STOCK',    'SCH_GOAT',     'ছাগল টিকার সূচি',          'Goat Schedule'),
('SHEEP','BREEDING_STOCK',   'SCH_SHEEP',    'ভেড়া টিকার সূচি',          'Sheep Schedule'),
('BUFFALO','DAIRY',          'SCH_BUFFALO',  'মহিষ টিকার সূচি',          'Buffalo Schedule');

insert into _schl values
-- ব্রয়লার
('SCH_BROILER',  1, 1,  'MAREK_HVT',     false,'সাধারণত হ্যাচারিতেই দেওয়া থাকে — নিশ্চিত হয়ে নিন'),
('SCH_BROILER',  3, 5,  'BCRDV',         false,'চোখে ১ ফোঁটা; সকালে ঠান্ডা সময়ে দিন'),
('SCH_BROILER', 11,12,  'IBD_LIVE',      false,'প্রথম ডোজ; পানিতে'),
('SCH_BROILER', 18,19,  'IBD_LIVE',      true, 'দ্বিতীয় ডোজ (বুস্টার)'),
('SCH_BROILER', 21,24,  'RDV_LASOTA',    true, 'রানীক্ষেত বুস্টার; পানিতে'),
-- লেয়ার
('SCH_LAYER',    1, 1,  'MAREK_HVT',     false,'হ্যাচারিতে'),
('SCH_LAYER',    3, 5,  'BCRDV',         false,'চোখে ১ ফোঁটা'),
('SCH_LAYER',    9,11,  'IBD_LIVE',      false,'প্রথম ডোজ'),
('SCH_LAYER',   16,18,  'IBD_LIVE',      true, 'বুস্টার'),
('SCH_LAYER',   21,24,  'RDV_LASOTA',    true, 'পানিতে'),
('SCH_LAYER',   28,30,  'IB_H120',       false,'পানিতে বা স্প্রে'),
('SCH_LAYER',   35,38,  'FOWL_POX_V',    false,'ডানার চামড়ায়'),
('SCH_LAYER',   42,45,  'RDV_R2B',       true, '৬ সপ্তাহ; রানের মাংসে'),
('SCH_LAYER',   56,60,  'FOWL_CHOLERA_V',false,'৮ সপ্তাহ; প্রথম ডোজ'),
('SCH_LAYER',   77,84,  'FOWL_CHOLERA_V',true, '১১–১২ সপ্তাহ; বুস্টার'),
('SCH_LAYER',  105,112, 'ND_KILLED',     true, '১৫–১৬ সপ্তাহ; ডিমে আসার আগে'),
('SCH_LAYER',  105,112, 'IB_KILLED',     true, '১৫–১৬ সপ্তাহ'),
('SCH_LAYER',  105,112, 'EDS_KILLED',    false,'১৫–১৬ সপ্তাহ; ডিম কমে যাওয়া প্রতিরোধে'),
('SCH_LAYER',  168,175, 'RDV_LASOTA',    true, 'ডিম পাড়া শুরুর পর প্রতি ৮–১০ সপ্তাহে পুনরাবৃত্তি'),
-- সোনালি
('SCH_SONALI',   3, 5,  'BCRDV',         false,'চোখে ১ ফোঁটা'),
('SCH_SONALI',  11,12,  'IBD_LIVE',      false,'প্রথম ডোজ'),
('SCH_SONALI',  18,19,  'IBD_LIVE',      true, 'বুস্টার'),
('SCH_SONALI',  21,24,  'RDV_LASOTA',    true, 'পানিতে'),
('SCH_SONALI',  35,38,  'FOWL_POX_V',    false,'ডানার চামড়ায়'),
('SCH_SONALI',  42,45,  'RDV_R2B',       true, 'রানের মাংসে'),
-- ককরেল
('SCH_COCKEREL', 3, 5,  'BCRDV',         false,null),
('SCH_COCKEREL',11,12,  'IBD_LIVE',      false,null),
('SCH_COCKEREL',18,19,  'IBD_LIVE',      true, null),
('SCH_COCKEREL',21,24,  'RDV_LASOTA',    true, null),
-- হাঁস
('SCH_DUCK',    21,28,  'DUCK_PLAGUE_V', false,'প্রথম ডোজ'),
('SCH_DUCK',    56,60,  'DUCK_CHOLERA_V',false,'প্রথম ডোজ'),
('SCH_DUCK',    77,84,  'DUCK_CHOLERA_V',true, 'বুস্টার'),
('SCH_DUCK',   120,150, 'DUCK_PLAGUE_V', true, 'বুস্টার; এরপর বছরে একবার'),
-- গরু (দুগ্ধ)
('SCH_CATTLE',  90,120, 'FMD_V',         false,'প্রথম ডোজ (৩–৪ মাস বয়সে)'),
('SCH_CATTLE', 118,150, 'FMD_V',         true, 'বুস্টার — প্রথম ডোজের ২৮ দিন পর'),
('SCH_CATTLE', 180,210, 'ANTHRAX_V',     false,'৬ মাস বয়স থেকে; এরপর বছরে একবার'),
('SCH_CATTLE', 180,210, 'BQ_V',          false,'৬ মাস–২ বছর; এরপর বছরে একবার'),
('SCH_CATTLE', 180,210, 'HS_V',          false,'বর্ষার আগে; বছরে একবার'),
('SCH_CATTLE', 180,210, 'LSD_V',         false,'এলাকায় প্রাদুর্ভাব থাকলে'),
('SCH_CATTLE', 300,365, 'FMD_V',         true, 'এরপর প্রতি ৬ মাসে পুনরাবৃত্তি'),
-- গরু (হৃষ্টপুষ্টকরণ) — ক্রয়ের পরপর সময় গণনা
('SCH_CATTLE_FAT', 7,14,'FMD_V',         false,'ক্রয়ের পর কোয়ারেন্টাইনে; কৃমিনাশকের সাথে'),
('SCH_CATTLE_FAT',14,21,'ANTHRAX_V',     false,'এলাকায় তড়কা থাকলে অগ্রাধিকার'),
('SCH_CATTLE_FAT',14,21,'HS_V',          false,null),
('SCH_CATTLE_FAT',35,45,'FMD_V',         true, 'বুস্টার'),
-- ছাগল
('SCH_GOAT',    90,120, 'PPR_V',         false,'৩ মাস বয়সে; একবারেই ৩ বছর সুরক্ষা'),
('SCH_GOAT',   120,150, 'GOAT_POX_V',    false,'এলাকায় বসন্ত থাকলে'),
('SCH_GOAT',   150,180, 'FMD_V',         false,'ছাগলেও ক্ষুরারোগ হয়'),
('SCH_GOAT',   180,210, 'ANTHRAX_V',     false,'বছরে একবার'),
('SCH_GOAT',   210,240, 'TETANUS_TT',    false,'খাসি করার আগে দিলে সবচেয়ে ভালো'),
-- ভেড়া
('SCH_SHEEP',   90,120, 'PPR_V',         false,'৩ মাস বয়সে'),
('SCH_SHEEP',  150,180, 'FMD_V',         false,null),
('SCH_SHEEP',  180,210, 'ANTHRAX_V',     false,'বছরে একবার'),
-- মহিষ
('SCH_BUFFALO', 90,120, 'FMD_V',         false,'প্রথম ডোজ'),
('SCH_BUFFALO',118,150, 'FMD_V',         true, 'বুস্টার'),
('SCH_BUFFALO',180,210, 'ANTHRAX_V',     false,'বছরে একবার'),
('SCH_BUFFALO',180,210, 'BQ_V',          false,'বছরে একবার'),
('SCH_BUFFALO',180,210, 'HS_V',          false,'মহিষে গলাফুলা বেশি মারাত্মক');

insert into master.vaccine_schedule
  (species_no, production_purpose_no, schedule_code, name_bn, name_en, is_default, source_note_bn)
select s.species_no, p.production_purpose_no, c.schedule_code, c.name_bn, c.name_en, true,
  'নির্দেশক সূচি — বাংলাদেশে প্রচলিত অনুশীলনের ভিত্তিতে। হ্যাচারি কী দিয়েছে, '
  'এলাকার রোগের চাপ ও টিকার ব্র্যান্ড অনুসারে বদলায়। নিবন্ধিত পশুচিকিৎসক অথবা '
  'উপজেলা প্রাণিসম্পদ কর্মকর্তার পরামর্শে চূড়ান্ত করুন।'
from _sch c
join master.species s on s.organization_no is null and s.species_code = c.species_code::citext
join master.production_purpose p on p.organization_no is null
                                and p.production_purpose_code = c.purpose_code::citext
where not exists (select 1 from master.vaccine_schedule x
  where x.organization_no is null and x.schedule_code = c.schedule_code::citext);

insert into master.vaccine_schedule_line
  (vaccine_schedule_no, age_day, age_day_to, vaccine_no, is_booster, remarks_bn)
select sc.vaccine_schedule_no, l.age_day, l.age_day_to, v.vaccine_no, l.is_booster, l.remarks_bn
from _schl l
join master.vaccine_schedule sc on sc.organization_no is null
                               and sc.schedule_code = l.schedule_code::citext
join master.vaccine v on v.organization_no is null and v.vaccine_code = l.vaccine_code::citext
where not exists (select 1 from master.vaccine_schedule_line x
  where x.vaccine_schedule_no = sc.vaccine_schedule_no
    and x.age_day = l.age_day and x.vaccine_no = v.vaccine_no);

drop table _sch; drop table _schl;
