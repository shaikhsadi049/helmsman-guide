-- =====================================================================
-- 10_item.sql — পণ্য, প্যাকেজিং ও খাদ্য উপাদানের পুষ্টিমান
--
-- ⚠ দুইটা সতর্কতা, আলাদা করে পড়ুন:
--
-- ১. পুষ্টিমান নির্দেশক। প্রকাশিত ফিড কম্পোজিশন টেবিল ও ক্রান্তীয় অঞ্চলের
--    প্রচলিত গড়ের কাছাকাছি। বাস্তব মান লট থেকে লটে বদলায় — বিশেষত কুঁড়া
--    (কত তুষ মিশেছে), খৈল (কত তেল বাকি আছে) ও ফিশ মিলে (কী মাছ, কত লবণ)।
--    গুরুত্বপূর্ণ সিদ্ধান্তে ল্যাব পরীক্ষা করান; is_lab_tested = true দিয়ে
--    নিজের মান বসান।
--
-- ২. indicative_rate শুধু যাতে সিস্টেম প্রথম দিনেই চলতে পারে, তার জন্য।
--    এগুলো বাজারদর নয় এবং দ্রুত পুরোনো হয়। নিজের ক্রয়মূল্য
--    inv.item_price এ দিন — দাম খোঁজার ক্রমে সেটাই আগে আসে, আর
--    feed.optimize_formula() জানিয়ে দেয় কোন উপাদানের দাম অনুমান করা হচ্ছে।
--
-- ব্র্যান্ড-নির্দিষ্ট রেডি ফিড (নারিশ, প্যারাগন, কাজী…) ইচ্ছাকৃতভাবে সিড
-- করা হয়নি — ওদের প্রকৃত স্পেসিফিকেশন আমার জানা নেই, আর বানানো সংখ্যা
-- দিয়ে খামারির হিসাব ভুল করানোর চেয়ে সাধারণ ধরনগুলো রেখে দেওয়া ভালো।
-- খামারি ব্র্যান্ড লিখে নিজের পণ্য বানাবে, স্পেসিফিকেশন বস্তার গায়ে থাকে।
-- =====================================================================

create temporary table _feed_seed (
  item_code text, cat text, name_bn text, name_en text, rate numeric, note_bn text,
  dm numeric, me numeric, tdn numeric, cp numeric,
  lys numeric, met numeric, metcys numeric,
  cf numeric, ee numeric, ca numeric, ptot numeric, pav numeric,
  na numeric, salt numeric
);

--                কোড              শ্রেণি          বাংলা নাম              ইংরেজি                 দর   নোট
insert into _feed_seed values
-- ─────────── দানাশস্য ───────────
('MAIZE','GRAIN','ভুট্টা','Maize',32,'পোল্ট্রি ফিডের প্রধান শক্তির উৎস; বাংলাদেশে ৫০–৬০% পর্যন্ত ব্যবহৃত হয়',
  88,3350,88,8.5, 0.26,0.18,0.36, 2.5,3.8,0.02,0.28,0.10, 0.02,0.05),
('WHEAT','GRAIN','গম','Wheat',38,null,
  88,3120,80,12.0, 0.34,0.19,0.45, 2.6,1.9,0.05,0.33,0.13, 0.02,0.05),
('BROKEN_RICE','GRAIN','খুদ / ভাঙা চাল','Broken Rice',42,'শক্তি বেশি, আঁশ কম; বাচ্চার ফিডে ভালো',
  88,3400,85,8.0, 0.28,0.18,0.30, 0.8,1.2,0.03,0.12,0.05, 0.02,0.04),
('SORGHUM','GRAIN','জোয়ার','Sorghum',34,null,
  88,3250,82,9.5, 0.22,0.17,0.33, 2.2,2.9,0.03,0.30,0.10, 0.02,0.04),
-- ─────────── কুঁড়া ও ভুসি ───────────
('RICE_POLISH','BRAN','রাইস পলিশ (অটো কুঁড়া)','Rice Polish',35,
  'চর্বি বেশি, তাই বেশিদিন রাখলে গন্ধ হয়ে যায়। ৮–১০%-এর বেশি দিলে ফিড আঠালো হয়',
  90,2900,70,12.5, 0.55,0.25,0.45, 7.0,13.0,0.07,1.50,0.20, 0.04,0.08),
('RICE_BRAN','BRAN','ঢেঁকি কুঁড়া (তুষ মিশ্রিত)','Rice Bran (with husk)',22,
  'তুষ মেশানো থাকে, তাই আঁশ বেশি ও শক্তি কম — দাম কম দেখে বেশি দিলে বৃদ্ধি কমে যায়',
  90,2200,55,9.0, 0.38,0.18,0.32, 14.0,8.0,0.08,1.20,0.15, 0.04,0.08),
('DORB','BRAN','তেল নিষ্কাশিত কুঁড়া','De-oiled Rice Bran',20,null,
  90,1800,52,14.0, 0.60,0.25,0.48, 14.0,1.0,0.10,1.60,0.20, 0.05,0.10),
('WHEAT_BRAN','BRAN','গমের ভুসি','Wheat Bran',28,'রুমিন্যান্টে চমৎকার; পোল্ট্রিতে আঁশ বেশি',
  88,1900,70,15.0, 0.60,0.22,0.48, 11.0,3.8,0.13,1.15,0.15, 0.04,0.08),
('PULSE_BRAN','BRAN','ডালের ভুসি (খেসারি/মাসকলাই)','Pulse Bran',26,null,
  89,2000,68,16.0, 0.75,0.20,0.42, 10.0,2.0,0.25,0.55,0.12, 0.03,0.06),
-- ─────────── খৈল ও মিল ───────────
('SBM44','OILCAKE','সয়াবিন মিল ৪৪%','Soybean Meal 44%',62,'পোল্ট্রির প্রধান আমিষের উৎস',
  89,2230,78,44.0, 2.83,0.62,1.28, 7.0,1.5,0.29,0.65,0.22, 0.02,0.05),
('SBM48','OILCAKE','সয়াবিন মিল ৪৮%','Soybean Meal 48%',68,null,
  89,2440,80,48.0, 3.02,0.67,1.38, 3.9,1.0,0.27,0.62,0.21, 0.02,0.05),
('FULLFAT_SOY','OILCAKE','ভাজা সয়াবিন (ফুল ফ্যাট)','Full-fat Soybean',75,
  'কাঁচা সয়াবিন দেওয়া যায় না — ট্রিপসিন ইনহিবিটর থাকে, ভাজা বা সেদ্ধ করতে হয়',
  90,3300,85,36.0, 2.25,0.53,1.05, 5.5,18.0,0.25,0.58,0.20, 0.02,0.04),
('MUSTARD_CAKE','OILCAKE','সরিষার খৈল','Mustard Oil Cake',42,
  'বাংলাদেশে সহজলভ্য ও সস্তা, কিন্তু গ্লুকোসিনোলেট থাকায় পোল্ট্রিতে ৫–৭%-এর বেশি নয়',
  90,1900,72,32.0, 1.60,0.60,1.10, 11.0,8.0,0.65,1.00,0.25, 0.03,0.06),
('SESAME_CAKE','OILCAKE','তিলের খৈল','Sesame Cake',48,'মেথিওনিন বেশি; ক্যালসিয়ামও ভালো',
  92,2200,75,38.0, 1.00,1.00,1.60, 6.0,10.0,2.00,1.20,0.30, 0.04,0.08),
('COCONUT_CAKE','OILCAKE','নারিকেলের খৈল','Coconut (Copra) Cake',35,null,
  90,1800,72,21.0, 0.60,0.30,0.55, 12.0,6.5,0.10,0.55,0.15, 0.04,0.08),
('GROUNDNUT_CAKE','OILCAKE','চীনাবাদামের খৈল','Groundnut Cake',60,
  'অ্যাফ্লাটক্সিনের ঝুঁকি সবচেয়ে বেশি — ভেজা বা ছাতাপড়া খৈল কখনো নয়',
  90,2500,78,45.0, 1.50,0.50,0.95, 6.0,6.0,0.15,0.55,0.15, 0.03,0.06),
('PROTEIN_CONC','OILCAKE','প্রোটিন কনসেনট্রেট ৪০%','Protein Concentrate 40%',85,
  'মিশ্র বাণিজ্যিক পণ্য — প্রকৃত মান ব্র্যান্ডভেদে ব্যাপকভাবে ভিন্ন, বস্তার স্পেসিফিকেশন দেখে বদলান',
  92,2400,80,40.0, 2.50,1.00,1.60, 4.0,5.0,3.00,1.50,1.20, 0.30,0.70),
-- ─────────── প্রাণিজ আমিষ ───────────
('FISHMEAL55','ANIMAL_PROTEIN','ফিশ মিল ৫৫%','Fish Meal 55%',95,
  'লাইসিন ও গ্রহণযোগ্য ফসফরাসের চমৎকার উৎস; লবণের মাত্রা যাচাই করুন',
  92,2800,80,55.0, 4.20,1.50,1.95, 1.0,8.0,5.00,3.00,2.70, 0.80,2.00),
('FISHMEAL60','ANIMAL_PROTEIN','ফিশ মিল ৬০%','Fish Meal 60%',110,null,
  92,2900,82,60.0, 4.60,1.70,2.20, 0.8,9.0,4.50,2.80,2.50, 0.70,1.80),
('MBM','ANIMAL_PROTEIN','মিট অ্যান্ড বোন মিল','Meat & Bone Meal',70,null,
  93,2200,72,50.0, 2.60,0.70,1.05, 2.0,10.0,10.00,5.00,4.50, 0.70,1.60),
('BLOOD_MEAL','ANIMAL_PROTEIN','ব্লাড মিল','Blood Meal',80,
  'আমিষ খুব বেশি কিন্তু আইসোলিউসিন কম ও সুস্বাদু নয় — ৩%-এর বেশি নয়',
  90,2600,70,80.0, 7.00,1.00,2.00, 1.0,1.5,0.30,0.25,0.20, 0.30,0.60),
-- ─────────── খনিজ ───────────
('OYSTER_SHELL','MINERAL_FEED','ঝিনুকের গুঁড়া','Oyster Shell',12,
  'লেয়ারে ডিমের খোসার জন্য; মোটা দানা দিলে রাতে ধীরে ক্যালসিয়াম ছাড়ে',
  99,0,0,0, 0,0,0, 0,0,38.00,0.02,0.02, 0.10,0.20),
('LIMESTONE','MINERAL_FEED','চুনাপাথরের গুঁড়া','Limestone Powder',8,null,
  99,0,0,0, 0,0,0, 0,0,38.00,0.02,0.02, 0.05,0.10),
('DCP','MINERAL_FEED','ডাই-ক্যালসিয়াম ফসফেট','Di-calcium Phosphate',60,null,
  99,0,0,0, 0,0,0, 0,0,23.00,18.00,18.00, 0.20,0.40),
('MDCP','MINERAL_FEED','মনো-ডাই-ক্যালসিয়াম ফসফেট','Mono-di-calcium Phosphate',75,null,
  99,0,0,0, 0,0,0, 0,0,17.00,21.00,21.00, 0.20,0.40),
('SALT','MINERAL_FEED','লবণ','Common Salt',18,'০.৫%-এর বেশি দিলে পাতলা পায়খানা ও ভেজা লিটার হয়',
  99,0,0,0, 0,0,0, 0,0,0.10,0,0, 39.00,100.00),
('SODA_BICARB','MINERAL_FEED','সোডিয়াম বাইকার্বোনেট','Sodium Bicarbonate',55,
  'গরমে হিট স্ট্রেসে ও রুমিন্যান্টে অ্যাসিডোসিসে উপকারী',
  99,0,0,0, 0,0,0, 0,0,0,0,0, 27.00,0),
-- ─────────── তেল ও চর্বি ───────────
('SOY_OIL','FAT_OIL','সয়াবিন তেল','Soybean Oil',150,
  'শক্তি বাড়াতে ও ফিডের ধুলা কমাতে; ৪–৫%-এর বেশি দিলে মিক্সিং কঠিন হয়',
  99,8800,180,0, 0,0,0, 0,99.0,0,0,0, 0,0),
('PALM_OIL','FAT_OIL','পাম তেল','Palm Oil',130,null,
  99,8200,175,0, 0,0,0, 0,99.0,0,0,0, 0,0),
('RICE_BRAN_OIL','FAT_OIL','রাইস ব্র্যান তেল','Rice Bran Oil',140,null,
  99,8500,178,0, 0,0,0, 0,99.0,0,0,0, 0,0),
-- ─────────── আঁশযুক্ত খাদ্য ও ঘাস (রুমিন্যান্ট) ───────────
-- লক্ষ্য করুন: কাঁচা ঘাসে ৮০% পানি, তাই as-fed আমিষ খুব কম দেখাচ্ছে।
-- এটাই সঠিক। DM ভিত্তিতে নেপিয়ারের আমিষ ৯%, কিন্তু as-fed ১.৮%।
('RICE_STRAW','ROUGHAGE','ধানের খড়','Rice Straw',8,
  'শুধু পেট ভরায়, পুষ্টি কম। ইউরিয়া-মোলাসেস দিয়ে প্রক্রিয়া করলে অনেক ভালো হয়',
  90,0,40,3.5, 0,0,0, 35.0,1.2,0.30,0.10,0, 0.10,0.20),
('UMS','ROUGHAGE','ইউরিয়া-মোলাসেস খড় (UMS)','Urea Molasses Straw',14,
  'খড় + ৩% ইউরিয়া + ১০% মোলাসেস। শুধু রুমিন্যান্টে, এবং ধীরে অভ্যস্ত করাতে হয়',
  60,0,52,9.0, 0,0,0, 25.0,1.0,0.35,0.15,0, 0.15,0.30),
('NAPIER','ROUGHAGE','নেপিয়ার ঘাস','Napier Grass',3,
  'বাংলাদেশে সবচেয়ে প্রচলিত চাষ করা ঘাস; ৪৫–৬০ দিনে কাটা সবচেয়ে ভালো',
  20,0,12,1.8, 0,0,0, 6.5,0.4,0.08,0.05,0, 0.02,0.04),
('PARA_GRASS','ROUGHAGE','পারা ঘাস','Para Grass',3,'ভেজা ও নিচু জমিতে ভালো হয়',
  22,0,13,2.0, 0,0,0, 7.0,0.4,0.09,0.06,0, 0.02,0.04),
('GERMAN_GRASS','ROUGHAGE','জার্মান ঘাস','German Grass',3,null,
  18,0,11,1.6, 0,0,0, 5.5,0.3,0.07,0.05,0, 0.02,0.04),
('MAIZE_SILAGE','ROUGHAGE','ভুট্টার সাইলেজ','Maize Silage',8,
  'শুকনো মৌসুমে ঘাসের অভাব মেটানোর সেরা উপায়',
  30,0,20,2.4, 0,0,0, 6.0,0.9,0.08,0.06,0, 0.02,0.04),
('MOLASSES','ROUGHAGE','ঝোলা গুড় (মোলাসেস)','Molasses',45,
  'স্বাদ বাড়ায় ও ধুলা কমায়; ৫–৭%-এর বেশি দিলে পায়খানা পাতলা হয়',
  75,1900,72,3.0, 0,0,0, 0,0,0.80,0.10,0, 0.20,0.40),
('UREA_FEED','ROUGHAGE','ফিড গ্রেড ইউরিয়া','Feed Grade Urea',30,
  '⚠ শুধু রুমিন্যান্টে, দানাদার খাদ্যের ১%-এর বেশি কখনো নয়। পোল্ট্রিতে বিষ। '
  'আমিষের মান অ-প্রোটিন নাইট্রোজেন (NPN) হিসেবে, প্রকৃত আমিষ নয়',
  99,0,0,280.0, 0,0,0, 0,0,0,0,0, 0,0),
-- ─────────── অ্যামিনো অ্যাসিড ও সংযোজন ───────────
('LYSINE','AMINO','লাইসিন HCl','L-Lysine HCl',380,null,
  99,0,0,95.0, 78.00,0,0, 0,0,0,0,0, 0,0),
('DL_MET','AMINO','ডিএল-মেথিওনিন','DL-Methionine',420,null,
  99,0,0,58.0, 0,99.00,99.00, 0,0,0,0,0, 0,0),
('THREONINE','AMINO','এল-থ্রিওনিন','L-Threonine',400,null,
  99,0,0,73.0, 0,0,0, 0,0,0,0,0, 0,0);

-- খাদ্য উপাদান তৈরি
insert into master.item
  (item_code, name_bn, name_en, item_category_no, item_type, base_uom_no,
   is_stock_tracked, is_lot_tracked, is_ruminant_only, indicative_rate, note_bn, sort_order)
select f.item_code, f.name_bn, f.name_en, c.item_category_no, c.item_type,
       (select uom_no from master.uom where organization_no is null and uom_code = 'KG'),
       true, false,
       -- রুমিন্যান্ট ছাড়া দেওয়া নিষিদ্ধ: ইউরিয়া (NPN, পোল্ট্রিতে বিষ) ও
       -- ইউরিয়াযুক্ত প্রক্রিয়াজাত খড়
       f.item_code in ('UREA_FEED','UMS'),
       f.rate, f.note_bn, 100
  from _feed_seed f
  join master.item_category c on c.organization_no is null
                            and c.item_category_code = f.cat::citext
 where not exists (select 1 from master.item x
   where x.organization_no is null and x.item_code = f.item_code::citext);

-- পুষ্টিমান — প্রশস্ত থেকে লম্বা রূপে
insert into master.item_nutrient (item_no, nutrient_no, value_per_kg, source_note_bn)
select i.item_no, n.nutrient_no, v.val,
       'প্রকাশিত ফিড কম্পোজিশন টেবিলের নির্দেশক গড় — ল্যাব পরীক্ষা করে বদলান'
  from _feed_seed f
  join master.item i on i.organization_no is null and i.item_code = f.item_code::citext
  cross join lateral (values
      ('DM', f.dm), ('ME_P', f.me), ('TDN', f.tdn), ('CP', f.cp),
      ('LYS', f.lys), ('MET', f.met), ('MET_CYS', f.metcys),
      ('CF', f.cf), ('EE', f.ee), ('CA', f.ca), ('P_TOT', f.ptot), ('P_AV', f.pav),
      ('NA', f.na), ('SALT', f.salt)
    ) as v(code, val)
  join master.nutrient n on n.organization_no is null and n.nutrient_code = v.code::citext
 where v.val is not null
   and not exists (select 1 from master.item_nutrient x
     where x.item_no = i.item_no and x.nutrient_no = n.nutrient_no);

-- ফিডের বস্তা সাধারণত ৫০ কেজি
insert into master.item_pack (item_no, pack_uom_no, qty_in_base, is_default)
select i.item_no,
       (select uom_no from master.uom where organization_no is null and uom_code = 'BOSTA'),
       50, true
  from master.item i
  join _feed_seed f on f.item_code = i.item_code::text
 where i.organization_no is null
   and f.cat in ('GRAIN','BRAN','OILCAKE','ANIMAL_PROTEIN','MINERAL_FEED')
   and not exists (select 1 from master.item_pack p
     where p.item_no = i.item_no
       and p.pack_uom_no = (select uom_no from master.uom
                             where organization_no is null and uom_code = 'BOSTA'));

drop table _feed_seed;

-- =====================================================================
-- সাধারণ রেডি ফিডের ধরন
--
-- ব্র্যান্ড ছাড়া, শুধু ধরন। খামারি "নারিশ ব্রয়লার স্টার্টার" নামে নিজের
-- পণ্য বানিয়ে brand ফিল্ডে ব্র্যান্ড লিখবে, আর বস্তার গায়ের স্পেসিফিকেশন
-- থেকে পুষ্টিমান বসাবে।
-- =====================================================================
insert into master.item
  (item_code, name_bn, name_en, item_category_no, item_type, base_uom_no,
   is_stock_tracked, is_lot_tracked, has_expiry, shelf_life_days, note_bn, sort_order)
select v.item_code, v.name_bn, v.name_en, c.item_category_no, 'feed_finished',
       (select uom_no from master.uom where organization_no is null and uom_code = 'KG'),
       true, true, true, 90, v.note_bn, v.sort_order
from (values
  ('RF_BROILER_STARTER','রেডি ফিড — ব্রয়লার স্টার্টার','Ready Feed — Broiler Starter',
     'সাধারণ ধরন; ব্র্যান্ড ও প্রকৃত স্পেসিফিকেশন নিজের পণ্যে বসান', 10),
  ('RF_BROILER_GROWER', 'রেডি ফিড — ব্রয়লার গ্রোয়ার','Ready Feed — Broiler Grower', null, 11),
  ('RF_BROILER_FINISHER','রেডি ফিড — ব্রয়লার ফিনিশার','Ready Feed — Broiler Finisher', null, 12),
  ('RF_LAYER_CHICK',    'রেডি ফিড — লেয়ার চিক','Ready Feed — Layer Chick', null, 20),
  ('RF_LAYER_GROWER',   'রেডি ফিড — লেয়ার গ্রোয়ার','Ready Feed — Layer Grower', null, 21),
  ('RF_LAYER_PRELAY',   'রেডি ফিড — লেয়ার প্রি-লে','Ready Feed — Layer Pre-lay', null, 22),
  ('RF_LAYER_1',        'রেডি ফিড — লেয়ার ১','Ready Feed — Layer Phase 1', null, 23),
  ('RF_LAYER_2',        'রেডি ফিড — লেয়ার ২','Ready Feed — Layer Phase 2', null, 24),
  ('RF_SONALI',         'রেডি ফিড — সোনালি','Ready Feed — Sonali', null, 30),
  ('RF_DUCK',           'রেডি ফিড — হাঁস','Ready Feed — Duck', null, 31),
  ('RF_QUAIL',          'রেডি ফিড — কোয়েল','Ready Feed — Quail', null, 32),
  ('RF_CATTLE_DAIRY',   'রেডি ফিড — গরুর দানাদার (দুগ্ধ)','Ready Feed — Dairy Concentrate', null, 40),
  ('RF_CATTLE_FAT',     'রেডি ফিড — গরুর দানাদার (হৃষ্টপুষ্টকরণ)','Ready Feed — Fattening Concentrate', null, 41),
  ('RF_CALF',           'রেডি ফিড — বাছুরের স্টার্টার','Ready Feed — Calf Starter', null, 42),
  ('RF_GOAT',           'রেডি ফিড — ছাগলের দানাদার','Ready Feed — Goat Concentrate', null, 43)
) as v(item_code, name_bn, name_en, note_bn, sort_order)
cross join (select item_category_no from master.item_category
             where organization_no is null and item_category_code = 'FEED_READY') c
where not exists (select 1 from master.item x
  where x.organization_no is null and x.item_code = v.item_code::citext);

-- =====================================================================
-- অ-খাদ্য পণ্য
--
-- ঔষধের প্রত্যাহারকাল (withdrawal_days_*) ইচ্ছাকৃতভাবে ফাঁকা।
-- এটা পণ্যের লেবেল ও নিবন্ধন-নির্দিষ্ট; একই ওষুধের ভিন্ন ব্র্যান্ডে ভিন্ন।
-- এর উপর ভিত্তি করে ডিম/দুধ/মাংস বিক্রি আটকানো হবে, তাই ভুল মান বসানোর
-- চেয়ে ফাঁকা থাকা নিরাপদ — খামারি বোতলের লেবেল দেখে বসাবে।
-- =====================================================================
insert into master.item
  (item_code, name_bn, name_en, item_category_no, item_type, base_uom_no,
   is_stock_tracked, is_lot_tracked, has_expiry, shelf_life_days, note_bn, sort_order)
select v.item_code, v.name_bn, v.name_en, c.item_category_no, c.item_type,
       (select uom_no from master.uom where organization_no is null and uom_code = v.uom),
       true, v.lot, v.lot, v.shelf, v.note_bn, v.sort_order
from (values
  -- ঔষধ
  ('DEWORM_ALBEND','MEDICINE','কৃমিনাশক — অ্যালবেন্ডাজল','Albendazole','PCS',true,730,
     'গবাদি ও ছাগলে; গর্ভের প্রথম তিন মাসে সতর্কতা',10),
  ('DEWORM_IVERM','MEDICINE','কৃমিনাশক — আইভারমেক্টিন','Ivermectin','ML',true,730,
     'অন্তঃপরজীবী ও বহিঃপরজীবী (উকুন, মাইট, টিক) দুটোতেই কাজ করে',11),
  ('DEWORM_LEVAM','MEDICINE','কৃমিনাশক — লেভামিসোল','Levamisole','PCS',true,730,null,12),
  ('DEWORM_PIPERA','MEDICINE','কৃমিনাশক — পিপারাজিন','Piperazine','GM',true,730,'পোল্ট্রিতে গোলকৃমি',13),
  ('AB_OXYTET','MEDICINE','অক্সিটেট্রাসাইক্লিন','Oxytetracycline','GM',true,730,null,20),
  ('AB_ENRO','MEDICINE','এনরোফ্লক্সাসিন','Enrofloxacin','ML',true,730,null,21),
  ('AB_DOXY','MEDICINE','ডক্সিসাইক্লিন','Doxycycline','GM',true,730,null,22),
  ('AB_TYLOSIN','MEDICINE','টাইলোসিন','Tylosin','GM',true,730,'সিআরডি/মাইকোপ্লাজমায়',23),
  ('AB_AMOX','MEDICINE','অ্যামোক্সিসিলিন','Amoxicillin','GM',true,730,null,24),
  ('COCCI_TOLTRA','MEDICINE','টলট্রাজুরিল','Toltrazuril','ML',true,730,'ককসিডিওসিসে',30),
  ('COCCI_AMPRO','MEDICINE','অ্যামপ্রোলিয়াম','Amprolium','GM',true,730,null,31),
  -- পুষ্টি সহায়ক
  ('VIT_AD3E','SUPPLEMENT','ভিটামিন এ-ডি৩-ই','Vitamin AD3E','ML',true,730,null,40),
  ('VIT_BCOMPLEX','SUPPLEMENT','বি-কমপ্লেক্স','B-Complex','ML',true,730,null,41),
  ('VIT_C','SUPPLEMENT','ভিটামিন সি','Vitamin C','GM',true,730,'গরমে হিট স্ট্রেস কমাতে',42),
  ('ELECTROLYTE','SUPPLEMENT','ইলেকট্রোলাইট','Electrolyte','GM',true,730,
     'গরমে ও পরিবহনের ধকলে; পানিতে মিশিয়ে',43),
  ('CALCIUM_LIQ','SUPPLEMENT','তরল ক্যালসিয়াম','Liquid Calcium','ML',true,730,
     'দুগ্ধজ্বর ও নরম খোসার ডিমে',44),
  ('LIVER_TONIC','SUPPLEMENT','লিভার টনিক','Liver Tonic','ML',true,730,null,45),
  ('PROBIOTIC','SUPPLEMENT','প্রোবায়োটিক','Probiotic','GM',true,545,null,46),
  ('TOXIN_BINDER','SUPPLEMENT','টক্সিন বাইন্ডার','Toxin Binder','KG',true,730,
     'অ্যাফ্লাটক্সিনের ঝুঁকি কমাতে; বর্ষায় বিশেষভাবে দরকার',47),
  ('PREMIX_POULTRY','SUPPLEMENT','ভিটামিন-মিনারেল প্রিমিক্স (পোল্ট্রি)','VM Premix (Poultry)','KG',true,545,null,48),
  ('PREMIX_CATTLE','SUPPLEMENT','ভিটামিন-মিনারেল প্রিমিক্স (গবাদি)','VM Premix (Cattle)','KG',true,545,null,49),
  ('DCP_LICK','SUPPLEMENT','মিনারেল ব্লক / চাটার খনিজ','Mineral Lick Block','PCS',false,null,null,50),
  -- জীবাণুনাশক
  ('DISINF_IODINE','DISINFECTANT','আয়োডিন জীবাণুনাশক','Iodine Disinfectant','ML',true,730,null,60),
  ('DISINF_GLUT','DISINFECTANT','গ্লুটারালডিহাইড','Glutaraldehyde','ML',true,730,null,61),
  ('LIME_POWDER','DISINFECTANT','চুনের গুঁড়া','Slaked Lime','KG',false,null,null,62),
  ('BLEACHING','DISINFECTANT','ব্লিচিং পাউডার','Bleaching Powder','KG',false,null,null,63),
  ('FORMALIN','DISINFECTANT','ফরমালিন','Formalin','ML',true,730,'হ্যাচারি ফিউমিগেশনে',64),
  -- লিটার
  ('HUSK','LITTER','ধানের তুষ','Rice Husk','KG',false,null,
     'বাংলাদেশে সবচেয়ে প্রচলিত লিটার; ২–৩ ইঞ্চি পুরু',70),
  ('SAWDUST','LITTER','করাত কাঠের গুঁড়া','Sawdust','KG',false,null,null,71),
  ('SAND','LITTER','বালি','Sand','KG',false,null,null,72),
  ('STRAW_LITTER','LITTER','খড় (বিছানা)','Straw (bedding)','KG',false,null,null,73),
  -- যন্ত্রপাতি
  ('FEEDER','EQUIPMENT','ফিডার','Feeder','PCS',false,null,null,80),
  ('DRINKER','EQUIPMENT','ড্রিংকার','Drinker','PCS',false,null,null,81),
  ('NIPPLE','EQUIPMENT','নিপল ড্রিংকার','Nipple Drinker','PCS',false,null,null,82),
  ('BROODER_GAS','EQUIPMENT','গ্যাস ব্রুডার','Gas Brooder','PCS',false,null,null,83),
  ('BULB','EQUIPMENT','বাল্ব','Bulb','PCS',false,null,null,84),
  ('CURTAIN','EQUIPMENT','পর্দা','Curtain','SQFT',false,null,null,85),
  ('NET','EQUIPMENT','জাল','Net','SQFT',false,null,'বন্য পাখি ও শিয়াল ঠেকাতে',86),
  ('WEIGH_SCALE','EQUIPMENT','ওজন মাপার যন্ত্র','Weighing Scale','PCS',false,null,null,87),
  ('SPRAYER','EQUIPMENT','স্প্রেয়ার','Sprayer','PCS',false,null,null,88),
  ('CHAFF_CUTTER','EQUIPMENT','চাফ কাটার (ঘাস কাটার যন্ত্র)','Chaff Cutter','PCS',false,null,null,89),
  ('MILKING_MACHINE','EQUIPMENT','দুধ দোহনের যন্ত্র','Milking Machine','PCS',false,null,null,90),
  ('FEED_MIXER','EQUIPMENT','ফিড মিক্সার','Feed Mixer','PCS',false,null,null,91),
  ('EAR_TAG','CONSUMABLE','কানের ট্যাগ','Ear Tag','PCS',false,null,null,95),
  ('EGG_TRAY','CONSUMABLE','ডিমের ট্রে','Egg Tray','PCS',false,null,null,96),
  ('SYRINGE','CONSUMABLE','সিরিঞ্জ','Syringe','PCS',false,null,null,97),
  -- ইন্ধন ও ইউটিলিটি
  ('DIESEL','FUEL','ডিজেল','Diesel','LTR',false,null,'জেনারেটর — লোডশেডিংয়ের খরচ',100),
  ('LPG','FUEL','এলপিজি সিলিন্ডার','LPG Cylinder','PCS',false,null,'ব্রুডারের জ্বালানি',101),
  ('ELECTRICITY','UTILITY','বিদ্যুৎ','Electricity','PCS',false,null,null,102)
) as v(item_code, cat, name_bn, name_en, uom, lot, shelf, note_bn, sort_order)
cross join lateral (select item_category_no, item_type from master.item_category
                     where organization_no is null and item_category_code = v.cat::citext) c
where not exists (select 1 from master.item x
  where x.organization_no is null and x.item_code = v.item_code::citext);
