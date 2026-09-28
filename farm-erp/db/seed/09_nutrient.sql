-- =====================================================================
-- 09_nutrient.sql — পুষ্টি উপাদান, পণ্যের শ্রেণি, স্টক চলাচলের ধরন
--
-- এককের রীতি (এটা না বুঝলে সব হিসাব ভুল হবে):
--   শতাংশভিত্তিক পুষ্টি শতাংশের সংখ্যা হিসেবেই রাখা হয় — ২৩% আমিষ মানে ২৩,
--   ০.২৩ নয়। শক্তি kcal/kg। দুই জায়গাতেই একই রীতি (পণ্যের মান ও চাহিদার
--   সীমা), তাই LP-র দুই পাশ মিলে যায়।
-- =====================================================================

insert into master.nutrient
  (nutrient_code, name_bn, name_en, nutrient_group, value_uom_code,
   is_constrainable, sort_order, note_bn)
select v.* from (values
  ('DM',      'শুষ্ক পদার্থ',            'Dry Matter',              'dry_matter','PCT',     false, 10,
     'সীমাবদ্ধ করা হয় না — রুমিন্যান্টের হিসাব DM ভিত্তিতে রূপান্তরের জন্য দরকার'),
  ('ME_P',    'বিপাকীয় শক্তি (পোল্ট্রি)','Metabolizable Energy (Poultry)','energy','KCAL_KG',true, 20, null),
  ('TDN',     'মোট পরিপাক্য পুষ্টি',     'Total Digestible Nutrients','energy','PCT',      true, 21,
     'রুমিন্যান্টের শক্তির মাপ'),
  ('CP',      'আমিষ (ক্রুড প্রোটিন)',    'Crude Protein',           'protein','PCT',       true, 30, null),
  ('DCP',     'পরিপাক্য আমিষ',          'Digestible Crude Protein','protein','PCT',       true, 31, null),
  ('LYS',     'লাইসিন',                'Lysine',                  'amino_acid','PCT',    true, 40, null),
  ('MET',     'মেথিওনিন',              'Methionine',              'amino_acid','PCT',    true, 41, null),
  ('MET_CYS', 'মেথিওনিন + সিস্টিন',     'Methionine + Cystine',    'amino_acid','PCT',    true, 42, null),
  ('THR',     'থ্রিওনিন',               'Threonine',               'amino_acid','PCT',    true, 43, null),
  ('TRP',     'ট্রিপ্টোফ্যান',           'Tryptophan',              'amino_acid','PCT',    true, 44, null),
  ('ARG',     'আরজিনিন',               'Arginine',                'amino_acid','PCT',    true, 45, null),
  ('CF',      'আঁশ (ক্রুড ফাইবার)',      'Crude Fibre',             'fibre','PCT',         true, 50,
     'পোল্ট্রিতে উচ্চসীমা দিতে হয়, রুমিন্যান্টে নিম্নসীমাও দরকার হয়'),
  ('EE',      'চর্বি (ইথার এক্সট্রাক্ট)', 'Ether Extract (Fat)',     'fat','PCT',           true, 60, null),
  ('ASH',     'ভস্ম',                  'Ash',                     'other','PCT',         true, 65, null),
  ('CA',      'ক্যালসিয়াম',             'Calcium',                 'mineral','PCT',       true, 70, null),
  ('P_TOT',   'মোট ফসফরাস',            'Total Phosphorus',        'mineral','PCT',       true, 71, null),
  ('P_AV',    'গ্রহণযোগ্য ফসফরাস',       'Available Phosphorus',    'mineral','PCT',       true, 72,
     'পোল্ট্রিতে মোট ফসফরাস নয়, গ্রহণযোগ্যটাই গুরুত্বপূর্ণ'),
  ('NA',      'সোডিয়াম',               'Sodium',                  'mineral','PCT',       true, 73, null),
  ('CL',      'ক্লোরিন',                'Chlorine',                'mineral','PCT',       true, 74, null),
  ('SALT',    'লবণ',                   'Salt',                    'mineral','PCT',       true, 75, null)
) as v(nutrient_code, name_bn, name_en, nutrient_group, value_uom_code,
       is_constrainable, sort_order, note_bn)
where not exists (select 1 from master.nutrient x
  where x.organization_no is null and x.nutrient_code = v.nutrient_code::citext);

-- ---------------------------------------------------------------------
-- পণ্যের শ্রেণি
-- ---------------------------------------------------------------------
insert into master.item_category (item_category_code, name_bn, name_en, item_type, sort_order)
select v.* from (values
  ('FEED_READY',    'রেডি ফিড',                'Ready Feed',           'feed_finished',   10),
  ('GRAIN',         'দানাশস্য',                 'Cereal Grain',         'feed_ingredient', 20),
  ('BRAN',          'কুঁড়া ও ভুসি',              'Bran & Byproduct',     'feed_ingredient', 21),
  ('OILCAKE',       'খৈল ও মিল',               'Oilcake & Meal',       'feed_ingredient', 22),
  ('ANIMAL_PROTEIN','প্রাণিজ আমিষ',             'Animal Protein',       'feed_ingredient', 23),
  ('MINERAL_FEED',  'খনিজ উপাদান',             'Mineral Source',       'feed_ingredient', 24),
  ('FAT_OIL',       'তেল ও চর্বি',              'Fat & Oil',            'feed_ingredient', 25),
  ('ROUGHAGE',      'আঁশযুক্ত খাদ্য ও ঘাস',      'Roughage & Fodder',    'feed_ingredient', 26),
  ('AMINO',         'অ্যামিনো অ্যাসিড',          'Synthetic Amino Acid', 'feed_additive',   30),
  ('PREMIX',        'ভিটামিন-মিনারেল প্রিমিক্স',  'Vitamin-Mineral Premix','feed_additive',  31),
  ('FEED_ADD',      'অন্যান্য ফিড সংযোজন',       'Other Feed Additive',  'feed_additive',   32),
  ('MEDICINE',      'ঔষধ',                     'Medicine',             'medicine',        40),
  ('VACCINE_STOCK', 'টিকা',                    'Vaccine',              'vaccine',         41),
  ('SUPPLEMENT',    'ভিটামিন ও পুষ্টি সহায়ক',    'Supplement',           'supplement',      42),
  ('DISINFECTANT',  'জীবাণুনাশক',               'Disinfectant',         'consumable',      43),
  ('LITTER',        'লিটার',                   'Litter',               'litter',          50),
  ('EQUIPMENT',     'যন্ত্রপাতি',                'Equipment',            'equipment',       60),
  ('CONSUMABLE',    'ভোগ্য সামগ্রী',             'Consumable',           'consumable',      61),
  ('FUEL',          'ইন্ধন',                    'Fuel',                 'fuel',            70),
  ('UTILITY',       'ইউটিলিটি',                 'Utility',              'utility',         71),
  ('PRODUCE',       'উৎপাদিত পণ্য',             'Farm Produce',         'produce',         80)
) as v(item_category_code, name_bn, name_en, item_type, sort_order)
where not exists (select 1 from master.item_category x
  where x.organization_no is null and x.item_category_code = v.item_category_code::citext);

-- ---------------------------------------------------------------------
-- স্টক চলাচলের ধরন
-- ---------------------------------------------------------------------
insert into master.stock_movement_type
  (stock_movement_type_code, name_bn, name_en, direction,
   is_purchase, is_issue, is_production, is_transfer, is_sale, is_wastage,
   is_adjustment, is_own_harvest,
   requires_production_unit, requires_counterparty, requires_unit_cost, requires_target_store,
   sort_order)
select v.* from (values
  -- ঢোকা
  ('OPENING_STOCK','প্রারম্ভিক স্টক',        'Opening Stock',     1, false,false,false,false,false,false,true, false, false,false,true, false, 10),
  ('PURCHASE',     'ক্রয়',                 'Purchase',          1, true, false,false,false,false,false,false,false, false,true, true, false, 11),
  ('MIX_IN',       'নিজে মিক্স করা ফিড (উৎপাদন)','Mixed Feed In',1, false,false,true, false,false,false,false,false, false,false,true, false, 12),
  ('OWN_HARVEST',  'নিজের ফসল (ভুট্টা/খড়/ঘাস)','Own Harvest',    1, false,false,false,false,false,false,false,true,  false,false,true, false, 13),
  ('TRANSFER_IN',  'গুদামান্তর (আগমন)',      'Transfer In',       1, false,false,false,true, false,false,false,false, false,false,false,false, 14),
  ('RETURN_IN',    'ব্যাচ থেকে ফেরত',        'Return from Unit',  1, false,false,false,false,false,false,false,false, true, false,false,false, 15),
  ('GIFT_IN',      'উপহার/অনুদান গ্রহণ',     'Gift/Grant In',     1, false,false,false,false,false,false,false,false, false,false,false,false, 16),
  ('COUNT_UP',     'গণনা সংশোধন (বৃদ্ধি)',   'Count Correction+', 1, false,false,false,false,false,false,true, false, false,false,false,false, 17),
  -- বেরোনো
  ('ISSUE_UNIT',   'ব্যাচে/ঘরে দেওয়া',       'Issue to Unit',    -1, false,true, false,false,false,false,false,false, true, false,false,false, 20),
  ('ISSUE_GENERAL','সাধারণ ব্যবহারে দেওয়া',  'General Issue',    -1, false,true, false,false,false,false,false,false, false,false,false,false, 21),
  ('MIX_OUT',      'মিক্সে উপাদান খরচ',      'Consumed in Mix',  -1, false,false,true, false,false,false,false,false, false,false,false,false, 22),
  ('TRANSFER_OUT', 'গুদামান্তর (প্রেরণ)',     'Transfer Out',     -1, false,false,false,true, false,false,false,false, false,false,false,true,  23),
  ('SALE',         'বিক্রি',                'Sale',             -1, false,false,false,false,true, false,false,false, false,true, false,false, 24),
  ('WASTAGE',      'নষ্ট/অপচয়',             'Wastage',          -1, false,false,false,false,false,true, false,false, false,false,false,false, 25),
  ('EXPIRED',      'মেয়াদোত্তীর্ণ',           'Expired',          -1, false,false,false,false,false,true, false,false, false,false,false,false, 26),
  ('DAMAGED',      'ক্ষতিগ্রস্ত (ভিজে/ইঁদুরে)','Damaged',         -1, false,false,false,false,false,true, false,false, false,false,false,false, 27),
  ('THEFT',        'চুরি',                  'Theft',            -1, false,false,false,false,false,true, false,false, false,false,false,false, 28),
  ('HOME_USE',     'পারিবারিক ব্যবহার',      'Household Use',    -1, false,false,false,false,false,false,false,false, false,false,false,false, 29),
  ('COUNT_DOWN',   'গণনা সংশোধন (হ্রাস)',    'Count Correction-',-1, false,false,false,false,false,false,true, false, false,false,false,false, 30)
) as v(stock_movement_type_code, name_bn, name_en, direction,
       is_purchase, is_issue, is_production, is_transfer, is_sale, is_wastage,
       is_adjustment, is_own_harvest,
       requires_production_unit, requires_counterparty, requires_unit_cost, requires_target_store,
       sort_order)
where not exists (select 1 from master.stock_movement_type x
  where x.organization_no is null and x.stock_movement_type_code = v.stock_movement_type_code::citext);
