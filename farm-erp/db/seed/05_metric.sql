-- =====================================================================
-- 05_metric.sql — মেট্রিক সংজ্ঞা ও প্রযোজ্যতা (গ্লোবাল সিড)
--
-- এই ফাইলটাই দৈনিক লগের পর্দা তৈরি করে। খামারি যখন একটা ইউনিট খুলে
-- দৈনিক এন্ট্রিতে যাবে, অ্যাপ metric_applicability দেখে ঠিক করবে কোন
-- ঘরগুলো দেখাতে হবে। ব্রয়লারে ডিমের ঘর আসবে না, লেয়ারে আসবে,
-- গাভিতে দুধের ঘর আসবে — কোনো if-else ছাড়া।
-- =====================================================================

-- ---------------------------------------------------------------------
-- মেট্রিক সংজ্ঞা
-- ---------------------------------------------------------------------
insert into master.metric_definition
  (metric_code, name_bn, name_en, category, value_type, aggregation,
   better_direction, min_value, max_value, default_uom_no, sort_order)
select v.metric_code, v.name_bn, v.name_en, v.category, v.value_type, v.aggregation,
       v.better_direction, v.min_value, v.max_value,
       (select uom_no from master.uom where organization_no is null and uom_code = v.uom_code::citext),
       v.sort_order
from (values
  -- ─── মড়ক (শুধু রিপোর্টের জন্য; দৈনিক লগে বসানো নিষিদ্ধ) ───
  ('mortality_qty','মড়ক (সংখ্যা)','Mortality Count','mortality','integer','sum','down',
     0,null,'PCS',5),

  -- ─── উৎপাদন: ডিম ───
  ('egg_total','ডিম সংগ্রহ (মোট)','Eggs Collected','production','integer','sum','up',
     0,null,'PCS',10),
  ('egg_cracked','ভাঙা ডিম','Cracked Eggs','production','integer','sum','down',
     0,null,'PCS',11),
  ('egg_dirty','নোংরা ডিম','Dirty Eggs','production','integer','sum','down',
     0,null,'PCS',12),
  ('egg_small','ছোট ডিম','Small/Pullet Eggs','production','integer','sum','down',
     0,null,'PCS',13),
  ('egg_soft_shell','নরম খোসার ডিম','Soft-shell Eggs','production','integer','sum','down',
     0,null,'PCS',14),
  ('egg_double_yolk','ডাবল ইয়ক ডিম','Double-yolk Eggs','production','integer','sum','neutral',
     0,null,'PCS',15),
  ('egg_avg_weight_g','ডিমের গড় ওজন','Avg Egg Weight','production','numeric','avg','up',
     10,120,'GM',16),
  ('hatching_egg_set','হ্যাচিংয়ে বসানো ডিম','Hatching Eggs Set','production','integer','sum','up',
     0,null,'PCS',17),

  -- ─── উৎপাদন: দুধ ───
  ('milk_morning_litre','দুধ — সকাল','Milk (Morning)','production','numeric','sum','up',
     0,60,'LTR',20),
  ('milk_noon_litre','দুধ — দুপুর','Milk (Noon)','production','numeric','sum','up',
     0,60,'LTR',21),
  ('milk_evening_litre','দুধ — বিকাল','Milk (Evening)','production','numeric','sum','up',
     0,60,'LTR',22),
  ('milk_rejected_litre','বাতিল দুধ','Rejected Milk','production','numeric','sum','down',
     0,60,'LTR',23),
  ('milk_fat_pct','দুধের চর্বি','Milk Fat','production','numeric','avg','up',
     0,15,'PCT',24),
  ('milk_snf_pct','দুধের SNF','Milk SNF','production','numeric','avg','up',
     0,15,'PCT',25),

  -- ─── খাদ্য ───
  ('feed_intake_kg','খাবার খাওয়া','Feed Consumed','feed','numeric','sum','neutral',
     0,null,'KG',30),
  ('feed_offered_kg','খাবার দেওয়া','Feed Offered','feed','numeric','sum','neutral',
     0,null,'KG',31),
  ('feed_wastage_kg','খাবার নষ্ট','Feed Wasted','feed','numeric','sum','down',
     0,null,'KG',32),
  ('concentrate_kg','দানাদার খাদ্য','Concentrate Feed','feed','numeric','sum','neutral',
     0,null,'KG',33),
  ('green_fodder_kg','কাঁচা ঘাস','Green Fodder','feed','numeric','sum','neutral',
     0,null,'KG',34),
  ('straw_kg','খড়','Straw','feed','numeric','sum','neutral',
     0,null,'KG',35),
  ('silage_kg','সাইলেজ','Silage','feed','numeric','sum','neutral',
     0,null,'KG',36),
  ('grazing_hours','চারণের সময়','Grazing Hours','feed','numeric','sum','neutral',
     0,24,'DAY',37),
  ('water_intake_litre','পানি খাওয়া','Water Consumed','water','numeric','sum','neutral',
     0,null,'LTR',40),

  -- ─── ওজন ও দেহ ───
  ('body_weight_avg_g','গড় দেহ ওজন (গ্রাম)','Avg Body Weight (g)','weight','numeric','last','up',
     1,20000,'GM',50),
  ('body_weight_avg_kg','গড় দেহ ওজন (কেজি)','Avg Body Weight (kg)','weight','numeric','last','up',
     0.1,1200,'KG',51),
  ('weight_sample_size','ওজনের নমুনা সংখ্যা','Weight Sample Size','weight','integer','last','neutral',
     1,null,'PCS',52),
  ('weight_cv_pct','সমতা (CV%)','Uniformity CV%','weight','numeric','last','down',
     0,100,'PCT',53),
  ('chest_girth_inch','বুকের বেড়','Chest Girth','weight','numeric','last','up',
     10,120,'INCH',54),
  ('body_length_inch','দেহের দৈর্ঘ্য','Body Length','weight','numeric','last','up',
     10,120,'INCH',55),
  ('body_condition_score','দেহ অবস্থার স্কোর (BCS)','Body Condition Score','weight','numeric','last','neutral',
     1,5,'RATIO',56),

  -- ─── পরিবেশ ───
  ('temp_max_c','সর্বোচ্চ তাপমাত্রা','Max Temperature','environment','numeric','avg','neutral',
     -5,55,'RATIO',60),
  ('temp_min_c','সর্বনিম্ন তাপমাত্রা','Min Temperature','environment','numeric','avg','neutral',
     -5,55,'RATIO',61),
  ('humidity_pct','আপেক্ষিক আর্দ্রতা','Relative Humidity','environment','numeric','avg','neutral',
     0,100,'PCT',62),
  ('litter_moisture_pct','লিটারের আর্দ্রতা','Litter Moisture','environment','numeric','avg','down',
     0,100,'PCT',63),
  ('ammonia_ppm','অ্যামোনিয়া','Ammonia','environment','numeric','avg','down',
     0,200,'RATIO',64),
  ('power_outage_hours','লোডশেডিং','Power Outage','environment','numeric','sum','down',
     0,24,'DAY',65),
  ('generator_run_hours','জেনারেটর চালানো','Generator Run','environment','numeric','sum','neutral',
     0,24,'DAY',66),

  -- ─── স্বাস্থ্য ───
  ('sick_count','অসুস্থ সংখ্যা','Sick Count','health','integer','last','down',
     0,null,'PCS',70),
  ('treated_count','চিকিৎসা দেওয়া হয়েছে','Treated Count','health','integer','sum','neutral',
     0,null,'PCS',71),
  ('vaccinated_count','টিকা দেওয়া হয়েছে','Vaccinated Count','health','integer','sum','up',
     0,null,'PCS',72),
  ('lameness_count','খোঁড়া/পা সমস্যা','Lameness Count','health','integer','last','down',
     0,null,'PCS',73),
  ('heat_detected','গরম হয়েছে (প্রজননের লক্ষণ)','Heat Detected','health','boolean','last','neutral',
     null,null,null,74),

  -- ─── শ্রম ও অন্যান্য ───
  ('labour_hours','শ্রমঘণ্টা','Labour Hours','labour','numeric','sum','neutral',
     0,null,'DAY',80),
  ('day_note','দিনের মন্তব্য','Day Note','other','text','none','neutral',
     null,null,null,90)
) as v(metric_code, name_bn, name_en, category, value_type, aggregation,
       better_direction, min_value, max_value, uom_code, sort_order)
where not exists (select 1 from master.metric_definition m
  where m.organization_no is null and m.metric_code = v.metric_code::citext);

-- ---------------------------------------------------------------------
-- প্রযোজ্যতা ১: সব প্রজাতি, সব উদ্দেশ্য
-- ---------------------------------------------------------------------
insert into master.metric_applicability (metric_no, species_no, production_purpose_no, is_required, is_daily)
select m.metric_no, null, null, v.req, v.daily
from (values
  ('feed_intake_kg',      true,  true),
  ('feed_offered_kg',     false, true),
  ('feed_wastage_kg',     false, true),
  ('water_intake_litre',  false, true),
  ('sick_count',          false, true),
  ('treated_count',       false, true),
  ('vaccinated_count',    false, false),
  ('temp_max_c',          false, true),
  ('temp_min_c',          false, true),
  ('humidity_pct',        false, true),
  ('power_outage_hours',  false, true),
  ('generator_run_hours', false, true),
  ('labour_hours',        false, true),
  ('day_note',            false, true)
) as v(code, req, daily)
join master.metric_definition m on m.organization_no is null and m.metric_code = v.code::citext
where not exists (
  select 1 from master.metric_applicability a
   where a.metric_no = m.metric_no and a.species_no is null and a.production_purpose_no is null);

-- ---------------------------------------------------------------------
-- প্রযোজ্যতা ২: উদ্দেশ্য অনুসারে (ডিম, দুধ)
-- ---------------------------------------------------------------------
insert into master.metric_applicability (metric_no, species_no, production_purpose_no, is_required, is_daily)
select m.metric_no, null, p.production_purpose_no, v.req, true
from (values
  -- ডিম দেয় এমন সব উদ্দেশ্য
  ('egg_total',        'LAYER',            true),
  ('egg_total',        'DUAL_POULTRY',     true),
  ('egg_total',        'POULTRY_BREEDER',  true),
  ('egg_total',        'EGG_DUCK',         true),
  ('egg_total',        'QUAIL_EGG',        true),
  ('egg_cracked',      'LAYER',            false),
  ('egg_cracked',      'DUAL_POULTRY',     false),
  ('egg_cracked',      'POULTRY_BREEDER',  false),
  ('egg_cracked',      'EGG_DUCK',         false),
  ('egg_cracked',      'QUAIL_EGG',        false),
  ('egg_dirty',        'LAYER',            false),
  ('egg_dirty',        'POULTRY_BREEDER',  false),
  ('egg_dirty',        'EGG_DUCK',         false),
  ('egg_small',        'LAYER',            false),
  ('egg_small',        'EGG_DUCK',         false),
  ('egg_soft_shell',   'LAYER',            false),
  ('egg_soft_shell',   'EGG_DUCK',         false),
  ('egg_double_yolk',  'LAYER',            false),
  ('egg_avg_weight_g', 'LAYER',            false),
  ('egg_avg_weight_g', 'POULTRY_BREEDER',  false),
  ('egg_avg_weight_g', 'EGG_DUCK',         false),
  ('egg_avg_weight_g', 'QUAIL_EGG',        false),
  ('hatching_egg_set', 'POULTRY_BREEDER',  false),
  -- দুধ
  ('milk_morning_litre','DAIRY',           true),
  ('milk_morning_litre','DAIRY_BREEDING',  true),
  ('milk_noon_litre',   'DAIRY',           false),
  ('milk_noon_litre',   'DAIRY_BREEDING',  false),
  ('milk_evening_litre','DAIRY',           true),
  ('milk_evening_litre','DAIRY_BREEDING',  true),
  ('milk_rejected_litre','DAIRY',          false),
  ('milk_rejected_litre','DAIRY_BREEDING', false),
  ('milk_fat_pct',      'DAIRY',           false),
  ('milk_fat_pct',      'DAIRY_BREEDING',  false),
  ('milk_snf_pct',      'DAIRY',           false),
  ('milk_snf_pct',      'DAIRY_BREEDING',  false),
  -- প্রজননের লক্ষণ
  ('heat_detected',     'DAIRY',           false),
  ('heat_detected',     'DAIRY_BREEDING',  false),
  ('heat_detected',     'BREEDING_STOCK',  false),
  ('heat_detected',     'REARING',         false)
) as v(code, purpose_code, req)
join master.metric_definition m on m.organization_no is null and m.metric_code = v.code::citext
join master.production_purpose p on p.organization_no is null
                                and p.production_purpose_code = v.purpose_code::citext
where not exists (
  select 1 from master.metric_applicability a
   where a.metric_no = m.metric_no and a.species_no is null
     and a.production_purpose_no = p.production_purpose_no);

-- ---------------------------------------------------------------------
-- প্রযোজ্যতা ৩: প্রজাতির শ্রেণি অনুসারে
--
-- রুমিন্যান্টে ঘাস-খড়-সাইলেজ-চারণ ও BCS; পোল্ট্রিতে লিটার, অ্যামোনিয়া
-- ও সমতা (CV%)। গরু-মহিষে বুকের বেড় ও দেহের দৈর্ঘ্য — বাংলাদেশে
-- ওজন মাপার যন্ত্র দুর্লভ, তাই ফিতা দিয়ে মেপে সূত্রে ওজন বের করা হয়।
-- ---------------------------------------------------------------------
insert into master.metric_applicability (metric_no, species_no, production_purpose_no, is_required, is_daily)
select m.metric_no, s.species_no, null, false, v.daily
from (values
  -- রুমিন্যান্ট
  ('concentrate_kg',      'ruminant', true),
  ('green_fodder_kg',     'ruminant', true),
  ('straw_kg',            'ruminant', true),
  ('silage_kg',           'ruminant', true),
  ('grazing_hours',       'ruminant', true),
  ('body_condition_score','ruminant', false),
  ('body_weight_avg_kg',  'ruminant', false),
  ('chest_girth_inch',    'ruminant', false),
  ('body_length_inch',    'ruminant', false),
  ('lameness_count',      'ruminant', false),
  -- পোল্ট্রি
  ('litter_moisture_pct', 'poultry',  false),
  ('ammonia_ppm',         'poultry',  false),
  ('body_weight_avg_g',   'poultry',  false),
  ('weight_sample_size',  'poultry',  false),
  ('weight_cv_pct',       'poultry',  false),
  -- অন্যান্য (খরগোশ)
  ('body_weight_avg_g',   'other',    false),
  ('weight_sample_size',  'other',    false)
) as v(code, animal_class, daily)
join master.metric_definition m on m.organization_no is null and m.metric_code = v.code::citext
join master.species s on s.organization_no is null and s.animal_class = v.animal_class
where not exists (
  select 1 from master.metric_applicability a
   where a.metric_no = m.metric_no and a.species_no = s.species_no
     and a.production_purpose_no is null);
