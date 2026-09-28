-- =====================================================================
-- 06_lifecycle.sql — জীবনচক্র টেমপ্লেট ও পর্যায় (গ্লোবাল সিড)
--
-- দিনের সীমাগুলো ব্যবস্থাপনার পর্যায় বোঝায় — খাদ্যের ধরন, তাপ, ঘনত্ব ও
-- টিকা যেখানে বদলায়। বাংলাদেশের প্রচলিত অনুশীলনের কাছাকাছি রাখা হয়েছে,
-- এবং খামারি নিজের মতো বদলাতে পারবে।
-- =====================================================================

create temporary table _lc (
  species_code text, purpose_code text, template_code text,
  name_bn text, name_en text, tracking_mode text, total_days int
);
create temporary table _lp (
  template_code text, phase_code text, name_bn text, name_en text,
  from_day int, to_day int, sort_order int
);

insert into _lc values
('CHICKEN','BROILER',        'BROILER_35',    'ব্রয়লার — ৩৫ দিন',          'Broiler 35-day',        'group', 35),
('CHICKEN','LAYER',          'LAYER_80W',     'লেয়ার — ৮০ সপ্তাহ',         'Layer 80-week',         'group', 560),
('CHICKEN','DUAL_POULTRY',   'SONALI_90',     'সোনালি/দেশি ক্রস — ৯০ দিন',  'Sonali 90-day',         'group', 90),
('CHICKEN','COCKEREL',       'COCKEREL_75',   'ককরেল — ৭৫ দিন',           'Cockerel 75-day',       'group', 75),
('CHICKEN','POULTRY_BREEDER','BREEDER_64W',   'ব্রিডার — ৬৪ সপ্তাহ',        'Breeder 64-week',       'group', 448),
('DUCK','EGG_DUCK',          'DUCK_LAYER',    'হাঁস (ডিম) — ২ বছর',        'Egg Duck 2-year',       'group', 730),
('DUCK','MEAT_DUCK',         'DUCK_MEAT_49',  'হাঁস (মাংস) — ৪৯ দিন',      'Meat Duck 49-day',      'group', 49),
('MUSCOVY','DUAL_POULTRY',   'MUSCOVY_120',   'চীনা হাঁস — ১২০ দিন',       'Muscovy 120-day',       'group', 120),
('GOOSE','DUAL_POULTRY',     'GOOSE_180',     'রাজহাঁস — ১৮০ দিন',         'Goose 180-day',         'group', 180),
('QUAIL','QUAIL_EGG',        'QUAIL_LAYER',   'কোয়েল (ডিম) — ১ বছর',      'Quail Layer 1-year',    'group', 365),
('QUAIL','QUAIL_MEAT',       'QUAIL_MEAT_35', 'কোয়েল (মাংস) — ৩৫ দিন',   'Quail Meat 35-day',     'group', 35),
('PIGEON','SQUAB',           'PIGEON_PAIR',   'কবুতর — জোড়া (চলমান)',     'Pigeon Pair Ongoing',   'group', null),
('TURKEY','FATTENING',       'TURKEY_150',    'টার্কি — ১৫০ দিন',          'Turkey 150-day',        'group', 150),
('GUINEA_FOWL','DUAL_POULTRY','GUINEA_120',   'তিতির — ১২০ দিন',          'Guinea Fowl 120-day',   'group', 120),
('CATTLE','DAIRY',           'DAIRY_COW',     'দুগ্ধ গাভি — আজীবন',        'Dairy Cow Lifetime',    'individual', null),
('CATTLE','FATTENING',       'CATTLE_FAT_180','গরু হৃষ্টপুষ্টকরণ — ১৮০ দিন','Cattle Fattening 180',  'individual', 180),
('CATTLE','QURBANI',         'QURBANI_240',   'কুরবানি প্রস্তুতি — ২৪০ দিন', 'Qurbani Prep 240-day',  'individual', 240),
('CATTLE','REARING',         'CATTLE_REAR',   'বাছুর/বকনা পালন',          'Calf & Heifer Rearing', 'individual', 730),
('BUFFALO','DAIRY',          'BUFFALO_DAIRY', 'দুগ্ধ মহিষ — আজীবন',       'Dairy Buffalo Lifetime','individual', null),
('GOAT','BREEDING_STOCK',    'GOAT_BREED',    'ছাগল প্রজনন — আজীবন',      'Goat Breeding Lifetime','individual', null),
('GOAT','FATTENING',         'GOAT_FAT_180',  'ছাগল হৃষ্টপুষ্টকরণ — ১৮০ দিন','Goat Fattening 180',   'individual', 180),
('SHEEP','BREEDING_STOCK',   'SHEEP_BREED',   'ভেড়া প্রজনন — আজীবন',      'Sheep Breeding Lifetime','individual', null),
('RABBIT','FATTENING',       'RABBIT_90',     'খরগোশ — ৯০ দিন',           'Rabbit 90-day',         'group', 90),
('FISH','FATTENING',         'FISH_CYCLE',    'মাছ — এক চাষচক্র',          'Fish Culture Cycle',    'group', 300);

insert into _lp values
-- ব্রয়লার
('BROILER_35','BROODING','ব্রুডিং','Brooding',0,10,10),
('BROILER_35','GROWING','গ্রোয়িং','Growing',11,24,20),
('BROILER_35','FINISHING','ফিনিশিং','Finishing',25,null,30),
-- লেয়ার
('LAYER_80W','BROODING','ব্রুডিং (০–৬ সপ্তাহ)','Brooding',0,42,10),
('LAYER_80W','GROWING','গ্রোয়িং (৭–১৬ সপ্তাহ)','Growing',43,112,20),
('LAYER_80W','PRELAY','প্রি-লেয়িং (১৭–১৯ সপ্তাহ)','Pre-lay',113,133,30),
('LAYER_80W','PEAK','পিক লেয়িং (২০–৪৩ সপ্তাহ)','Peak Lay',134,300,40),
('LAYER_80W','LATE_LAY','লেট লেয়িং (৪৪ সপ্তাহ+)','Late Lay',301,null,50),
-- সোনালি
('SONALI_90','BROODING','ব্রুডিং','Brooding',0,21,10),
('SONALI_90','GROWING','গ্রোয়িং','Growing',22,60,20),
('SONALI_90','MARKETABLE','বিক্রয়যোগ্য','Marketable',61,null,30),
-- ককরেল
('COCKEREL_75','BROODING','ব্রুডিং','Brooding',0,21,10),
('COCKEREL_75','GROWING','গ্রোয়িং','Growing',22,null,20),
-- ব্রিডার
('BREEDER_64W','BROODING','ব্রুডিং','Brooding',0,42,10),
('BREEDER_64W','REARING','রিয়ারিং','Rearing',43,140,20),
('BREEDER_64W','PRODUCTION','হ্যাচিং ডিম উৎপাদন','Hatching Egg Production',141,null,30),
-- হাঁস (ডিম)
('DUCK_LAYER','BROODING','ব্রুডিং','Brooding',0,21,10),
('DUCK_LAYER','GROWING','গ্রোয়িং','Growing',22,140,20),
('DUCK_LAYER','LAYING','ডিম পাড়া','Laying',141,null,30),
-- হাঁস (মাংস)
('DUCK_MEAT_49','BROODING','ব্রুডিং','Brooding',0,14,10),
('DUCK_MEAT_49','FINISHING','ফিনিশিং','Finishing',15,null,20),
-- চীনা হাঁস, রাজহাঁস, তিতির
('MUSCOVY_120','BROODING','ব্রুডিং','Brooding',0,21,10),
('MUSCOVY_120','GROWING','গ্রোয়িং','Growing',22,null,20),
('GOOSE_180','BROODING','ব্রুডিং','Brooding',0,28,10),
('GOOSE_180','GRAZING','চারণ ও বৃদ্ধি','Grazing & Growth',29,null,20),
('GUINEA_120','BROODING','ব্রুডিং','Brooding',0,28,10),
('GUINEA_120','GROWING','গ্রোয়িং','Growing',29,null,20),
-- কোয়েল
('QUAIL_LAYER','BROODING','ব্রুডিং','Brooding',0,14,10),
('QUAIL_LAYER','GROWING','গ্রোয়িং','Growing',15,41,20),
('QUAIL_LAYER','LAYING','ডিম পাড়া','Laying',42,null,30),
('QUAIL_MEAT_35','BROODING','ব্রুডিং','Brooding',0,14,10),
('QUAIL_MEAT_35','FINISHING','ফিনিশিং','Finishing',15,null,20),
-- কবুতর
('PIGEON_PAIR','PAIRING','জোড়া বাঁধা','Pairing',0,180,10),
('PIGEON_PAIR','BREEDING','প্রজননক্ষম','Breeding',181,null,20),
-- টার্কি
('TURKEY_150','BROODING','ব্রুডিং','Brooding',0,28,10),
('TURKEY_150','GROWING','গ্রোয়িং','Growing',29,90,20),
('TURKEY_150','FINISHING','ফিনিশিং','Finishing',91,null,30),
-- গাভি
('DAIRY_COW','CALF','বাছুর','Calf',0,90,10),
('DAIRY_COW','WEANED','দুধ ছাড়ানো বাছুর','Weaned Calf',91,180,20),
('DAIRY_COW','HEIFER','বকনা','Heifer',181,730,30),
('DAIRY_COW','ADULT','প্রাপ্তবয়স্ক (দুগ্ধচক্র)','Adult (Lactation Cycles)',731,null,40),
-- গরু হৃষ্টপুষ্টকরণ
('CATTLE_FAT_180','ADAPTATION','অভ্যস্তকরণ ও কৃমিমুক্তি','Adaptation & Deworming',0,21,10),
('CATTLE_FAT_180','GROWTH','দেহ গঠন','Growth',22,120,20),
('CATTLE_FAT_180','FINISHING','চূড়ান্ত পুষ্টিকরণ','Finishing',121,null,30),
-- কুরবানি
('QURBANI_240','ADAPTATION','ক্রয় ও অভ্যস্তকরণ','Purchase & Adaptation',0,21,10),
('QURBANI_240','FRAME','দেহ গঠন','Frame Building',22,150,20),
('QURBANI_240','FINISHING','চূড়ান্ত পুষ্টিকরণ (ঈদের আগে)','Pre-Eid Finishing',151,null,30),
-- বাছুর পালন
('CATTLE_REAR','CALF','বাছুর','Calf',0,90,10),
('CATTLE_REAR','WEANED','দুধ ছাড়ানো','Weaned',91,180,20),
('CATTLE_REAR','HEIFER','বকনা','Heifer',181,null,30),
-- মহিষ
('BUFFALO_DAIRY','CALF','বাছুর','Calf',0,120,10),
('BUFFALO_DAIRY','HEIFER','বকনা','Heifer',121,900,20),
('BUFFALO_DAIRY','ADULT','প্রাপ্তবয়স্ক','Adult',901,null,30),
-- ছাগল
('GOAT_BREED','KID','বাচ্চা','Kid',0,90,10),
('GOAT_BREED','GROWING','বাড়ন্ত','Growing',91,210,20),
('GOAT_BREED','BREEDING','প্রজননক্ষম','Breeding',211,null,30),
('GOAT_FAT_180','ADAPTATION','অভ্যস্তকরণ ও কৃমিমুক্তি','Adaptation & Deworming',0,14,10),
('GOAT_FAT_180','GROWTH','দেহ গঠন','Growth',15,120,20),
('GOAT_FAT_180','FINISHING','চূড়ান্ত পুষ্টিকরণ','Finishing',121,null,30),
-- ভেড়া
('SHEEP_BREED','LAMB','বাচ্চা','Lamb',0,90,10),
('SHEEP_BREED','GROWING','বাড়ন্ত','Growing',91,240,20),
('SHEEP_BREED','BREEDING','প্রজননক্ষম','Breeding',241,null,30),
-- খরগোশ ও মাছ
('RABBIT_90','NURSING','দুধ খাওয়া','Nursing',0,30,10),
('RABBIT_90','GROWING','বাড়ন্ত','Growing',31,null,20),
('FISH_CYCLE','NURSERY','নার্সারি (পোনা)','Nursery',0,45,10),
('FISH_CYCLE','REARING','বৃদ্ধি','Rearing',46,210,20),
('FISH_CYCLE','HARVEST','আহরণযোগ্য','Harvest Ready',211,null,30);

insert into master.lifecycle_template
  (species_no, production_purpose_no, template_code, name_bn, name_en,
   tracking_mode, total_days, is_default)
select s.species_no, p.production_purpose_no, l.template_code, l.name_bn, l.name_en,
       l.tracking_mode, l.total_days, true
from _lc l
join master.species s on s.organization_no is null and s.species_code = l.species_code::citext
join master.production_purpose p on p.organization_no is null
                                and p.production_purpose_code = l.purpose_code::citext
where not exists (select 1 from master.lifecycle_template t
  where t.organization_no is null and t.template_code = l.template_code::citext);

insert into master.lifecycle_phase
  (lifecycle_template_no, phase_code, name_bn, name_en, from_day, to_day, sort_order)
select t.lifecycle_template_no, f.phase_code, f.name_bn, f.name_en,
       f.from_day, f.to_day, f.sort_order
from _lp f
join master.lifecycle_template t on t.organization_no is null
                                and t.template_code = f.template_code::citext
where not exists (select 1 from master.lifecycle_phase x
  where x.lifecycle_template_no = t.lifecycle_template_no
    and x.phase_code = f.phase_code::citext);

drop table _lc; drop table _lp;
