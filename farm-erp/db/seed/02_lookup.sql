-- =====================================================================
-- 02_lookup.sql — সংকেত তালিকা (গ্লোবাল সিড)
-- =====================================================================

-- ---------------------------------------------------------------------
-- ঘরের ধরন
-- ---------------------------------------------------------------------
insert into master.house_type (house_type_code, name_bn, name_en, animal_class, sort_order)
select v.* from (values
  -- পোল্ট্রি
  ('BROODER',        'ব্রুডার ঘর',            'Brooder House',         'poultry', 10),
  ('BROILER_SHED',   'ব্রয়লার শেড',           'Broiler Shed',          'poultry', 11),
  ('GROWER_SHED',    'গ্রোয়ার শেড',           'Grower Shed',           'poultry', 12),
  ('LAYER_CAGE',     'লেয়ার শেড (খাঁচা)',      'Layer Shed (Cage)',     'poultry', 13),
  ('LAYER_FLOOR',    'লেয়ার শেড (মেঝে)',       'Layer Shed (Floor)',    'poultry', 14),
  ('SONALI_SHED',    'সোনালি শেড',            'Sonali Shed',           'poultry', 15),
  ('COCKEREL_SHED',  'ককরেল শেড',            'Cockerel Shed',         'poultry', 16),
  ('BREEDER_SHED',   'ব্রিডার শেড',            'Breeder Shed',          'poultry', 17),
  ('DUCK_SHED',      'হাঁসের ঘর',             'Duck House',            'poultry', 20),
  ('DUCK_POND_YARD', 'হাঁসের ঘর ও জলাঙ্গন',    'Duck House with Pond',  'poultry', 21),
  ('QUAIL_SHED',     'কোয়েলের ঘর',           'Quail House',           'poultry', 22),
  ('PIGEON_LOFT',    'কবুতরের খোপ',          'Pigeon Loft',           'poultry', 23),
  ('TURKEY_SHED',    'টার্কির ঘর',             'Turkey Shed',           'poultry', 24),
  ('HATCHERY',       'হ্যাচারি',               'Hatchery',              'poultry', 30),
  -- রুমিন্যান্ট
  ('CATTLE_BARN',    'গোয়ালঘর',              'Cattle Barn',           'ruminant', 40),
  ('DAIRY_BARN',     'দুগ্ধ খামার ঘর',          'Dairy Barn',            'ruminant', 41),
  ('MILKING_PARLOUR','দুধ দোহনের ঘর',         'Milking Parlour',       'ruminant', 42),
  ('FATTENING_SHED', 'হৃষ্টপুষ্টকরণ শেড',        'Fattening Shed',        'ruminant', 43),
  ('CALF_PEN',       'বাছুরের খোপ',           'Calf Pen',              'ruminant', 44),
  ('GOAT_SHED',      'ছাগলের ঘর',            'Goat Shed',             'ruminant', 45),
  ('GOAT_MACHA',     'ছাগলের মাচা ঘর',        'Goat Raised Platform',  'ruminant', 46),
  ('SHEEP_SHED',     'ভেড়ার ঘর',              'Sheep Shed',            'ruminant', 47),
  ('BUFFALO_SHED',   'মহিষের ঘর',             'Buffalo Shed',          'ruminant', 48),
  ('BATHAN',         'বাথান (চারণভূমি)',        'Bathan (Grazing Camp)', 'ruminant', 49),
  ('QUARANTINE',     'কোয়ারেন্টাইন ঘর',        'Quarantine Shed',       'mixed',    50),
  -- জলজ ও সমন্বিত
  ('POND',           'পুকুর',                 'Pond',                  'aquaculture', 60),
  ('DUCK_FISH',      'হাঁস-মাছ সমন্বিত পুকুর',   'Duck-cum-Fish Pond',    'aquaculture', 61),
  ('POULTRY_FISH',   'মুরগি-মাছ সমন্বিত',      'Poultry-cum-Fish',      'aquaculture', 62),
  -- সহায়ক
  ('FEED_STORE',     'খাদ্য গুদাম',            'Feed Store',            'support', 70),
  ('FEED_MILL',      'ফিড মিল (নিজে মিক্স)',    'Feed Mill',             'support', 71),
  ('MEDICINE_STORE', 'ঔষধ ও টিকার ঘর',        'Medicine Store',        'support', 72),
  ('EQUIPMENT_STORE','যন্ত্রপাতির ঘর',          'Equipment Store',       'support', 73),
  ('MANURE_PIT',     'গোবর/বিষ্ঠার গর্ত',       'Manure Pit',            'support', 74),
  ('BIOGAS',         'বায়োগ্যাস প্ল্যান্ট',       'Biogas Plant',          'support', 75),
  ('COMPOST',        'কম্পোস্ট ইউনিট',         'Compost Unit',          'support', 76),
  ('FODDER_PLOT',    'ঘাসের জমি',             'Fodder Plot',           'support', 77),
  ('GENERATOR_ROOM', 'জেনারেটর ঘর',          'Generator Room',        'support', 78),
  ('LABOUR_QUARTER', 'শ্রমিকের থাকার ঘর',      'Labour Quarter',        'support', 79),
  ('OFFICE',         'অফিস',                 'Office',                'support', 80)
) as v(house_type_code, name_bn, name_en, animal_class, sort_order)
where not exists (select 1 from master.house_type t
  where t.organization_no is null and t.house_type_code = v.house_type_code::citext);

-- ---------------------------------------------------------------------
-- পালন পদ্ধতি
-- ---------------------------------------------------------------------
insert into master.rearing_system (rearing_system_code, name_bn, name_en, sort_order)
select v.* from (values
  ('DEEP_LITTER',     'ডিপ লিটার',                 'Deep Litter',            10),
  ('FLOOR',           'মেঝেতে পালন',               'Floor Rearing',          11),
  ('CAGE',            'খাঁচায় পালন',                'Cage',                   12),
  ('SLATTED',         'স্ল্যাট পদ্ধতি',               'Slatted Floor',          13),
  ('SLAT_LITTER',     'স্ল্যাট ও লিটার মিশ্র',         'Slat-cum-Litter',        14),
  ('ENV_CONTROLLED',  'ইসি শেড (নিয়ন্ত্রিত পরিবেশ)',  'Environment Controlled', 15),
  ('MACHA',           'মাচা পদ্ধতি (উঁচু মেঝে)',       'Raised Platform',        16),
  ('BACKYARD',        'বাড়ির আঙিনায় (ছেড়ে পালন)',   'Backyard Scavenging',    20),
  ('SEMI_SCAVENGING', 'আধা-ছাড়া পালন',             'Semi-Scavenging',        21),
  ('FREE_RANGE',      'মুক্ত চারণ',                 'Free Range',             22),
  ('TETHERED',        'দড়িতে বেঁধে পালন',           'Tethered',               30),
  ('ZERO_GRAZING',    'স্টল ফিডিং (ঘরে খাওয়ানো)',    'Zero Grazing',           31),
  ('SEMI_INTENSIVE',  'আধা-নিবিড়',                 'Semi-Intensive',         32),
  ('EXTENSIVE',       'বিস্তৃত চারণ',                'Extensive Grazing',      33),
  ('BATHAN_GRAZING',  'বাথানে চারণ (মৌসুমি)',       'Bathan Grazing',         34),
  ('DUCK_FISH_INT',   'হাঁস-মাছ সমন্বিত',            'Duck-cum-Fish',          40),
  ('POULTRY_FISH_INT','মুরগি-মাছ সমন্বিত',          'Poultry-cum-Fish',       41)
) as v(rearing_system_code, name_bn, name_en, sort_order)
where not exists (select 1 from master.rearing_system t
  where t.organization_no is null and t.rearing_system_code = v.rearing_system_code::citext);

-- ---------------------------------------------------------------------
-- উৎপাদনের উদ্দেশ্য
--
-- QURBANI আলাদা উদ্দেশ্য হিসেবে রাখা হয়েছে — সাধারণ হৃষ্টপুষ্টকরণ নয়।
-- কারণ কুরবানির গরুর পরিকল্পনা ঈদের তারিখ ধরে ৬–৮ মাস আগে শুরু হয়,
-- দাম ঠিক হয় চেহারা ও লাইভ ওয়েট দেখে, আর বিক্রি হয় হাটে —
-- খরচ, সময়সূচি ও দামের যুক্তি সবই ভিন্ন।
-- ---------------------------------------------------------------------
insert into master.production_purpose
  (production_purpose_code, name_bn, name_en, yields_meat, yields_egg, yields_milk,
   yields_young, yields_draft, sort_order)
select v.* from (values
  ('BROILER',       'ব্রয়লার (মাংস)',          'Broiler',            true,  false, false, false, false, 10),
  ('LAYER',         'লেয়ার (ডিম)',            'Layer',              false, true,  false, false, false, 11),
  ('DUAL_POULTRY',  'দ্বৈত (ডিম ও মাংস)',       'Dual Purpose',       true,  true,  false, false, false, 12),
  ('COCKEREL',      'ককরেল (মাংস)',          'Cockerel',           true,  false, false, false, false, 13),
  ('POULTRY_BREEDER','ব্রিডার (হ্যাচিং ডিম)',    'Poultry Breeder',    false, true,  false, true,  false, 14),
  ('EGG_DUCK',      'হাঁস (ডিম)',              'Egg Duck',           false, true,  false, false, false, 20),
  ('MEAT_DUCK',     'হাঁস (মাংস)',             'Meat Duck',          true,  false, false, false, false, 21),
  ('QUAIL_EGG',     'কোয়েল (ডিম)',           'Quail Egg',          false, true,  false, false, false, 22),
  ('QUAIL_MEAT',    'কোয়েল (মাংস)',          'Quail Meat',         true,  false, false, false, false, 23),
  ('SQUAB',         'কবুতর (বাচ্চা/মাংস)',      'Squab',              true,  false, false, true,  false, 24),
  ('DAIRY',         'দুগ্ধ',                   'Dairy',              false, false, true,  false, false, 30),
  ('DAIRY_BREEDING','দুগ্ধ ও প্রজনন',          'Dairy & Breeding',   false, false, true,  true,  false, 31),
  ('FATTENING',     'হৃষ্টপুষ্টকরণ (মাংস)',      'Fattening',          true,  false, false, false, false, 32),
  ('QURBANI',       'কুরবানির জন্য প্রস্তুতি',    'Qurbani Preparation',true,  false, false, false, false, 33),
  ('REARING',       'বাছুর/বকনা পালন',        'Young Stock Rearing',false, false, false, true,  false, 34),
  ('BREEDING_STOCK','প্রজনন স্টক',             'Breeding Stock',     false, false, false, true,  false, 35),
  ('DRAFT',         'হালচাষ/ভার বহন',         'Draft Animal',       false, false, false, false, true,  36),
  ('ORNAMENTAL',    'শৌখিন/সৌন্দর্য',          'Ornamental',         false, false, false, true,  false, 90),
  ('PET',           'পোষা',                   'Pet',                false, false, false, false, false, 91)
) as v(production_purpose_code, name_bn, name_en, yields_meat, yields_egg, yields_milk,
       yields_young, yields_draft, sort_order)
where not exists (select 1 from master.production_purpose t
  where t.organization_no is null and t.production_purpose_code = v.production_purpose_code::citext);

-- ---------------------------------------------------------------------
-- চলাচলের ধরন
--
-- কুরবানি, সদকা, জাকাত ও পারিবারিক ভোগ আলাদা ধরন হিসেবে আছে — কারণ
-- এগুলো বিক্রি নয় (আয় হয় না) কিন্তু স্টক কমে এবং খরচ বহন করা হয়েছে।
-- অনেক খামারি এগুলো কোথাও লেখেন না, ফলে বছর শেষে হিসাব মেলে না এবং
-- মনে হয় "এত প্রাণী গেল কোথায়"।
-- ---------------------------------------------------------------------
insert into master.movement_type
  (movement_type_code, name_bn, name_en, direction, is_mortality, is_culling, is_sale,
   is_purchase, is_internal_transfer, is_home_consumption, is_donation,
   requires_counterparty, requires_amount, requires_cause, sort_order)
select v.* from (values
  -- ঢোকা
  ('OPENING',      'প্রারম্ভিক স্থিতি',      'Opening Balance',   1, false,false,false,false,false,false,false, false,false,false, 10),
  ('DOC_RECEIPT',  'একদিনের বাচ্চা গ্রহণ',  'Day-Old Chick In',  1, false,false,false,true, false,false,false, true, true, false, 11),
  ('PURCHASE',     'ক্রয়',                'Purchase',          1, false,false,false,true, false,false,false, true, true, false, 12),
  ('BIRTH',        'জন্ম',                'Birth',             1, false,false,false,false,false,false,false, false,false,false, 13),
  ('HATCH',        'ডিম ফুটে বাচ্চা',      'Hatched',           1, false,false,false,false,false,false,false, false,false,false, 14),
  ('TRANSFER_IN',  'শাখান্তর (আগমন)',     'Transfer In',       1, false,false,false,false,true, false,false, false,false,false, 15),
  ('GIFT_IN',      'উপহার গ্রহণ',         'Gift In',           1, false,false,false,false,false,false,false, false,false,false, 16),
  ('COUNT_UP',     'গণনা সংশোধন (বৃদ্ধি)', 'Count Correction+', 1, false,false,false,false,false,false,false, false,false,false, 17),
  -- বেরোনো
  ('DEATH',        'মৃত্যু',               'Death',            -1, true, false,false,false,false,false,false, false,false,true,  20),
  ('PREDATION',    'শিয়াল/কুকুরে নেওয়া',  'Predation',        -1, true, false,false,false,false,false,false, false,false,true,  21),
  ('CULL',         'কালিং (বাতিল)',        'Culling',          -1, false,true, false,false,false,false,false, false,false,true,  22),
  ('SALE_LIVE',    'জীবন্ত বিক্রি',         'Live Sale',        -1, false,false,true, false,false,false,false, true, true, false, 30),
  ('SALE_MEAT',    'জবাই করে মাংস বিক্রি', 'Slaughter & Sell', -1, false,false,true, false,false,false,false, true, true, false, 31),
  ('SALE_BREEDING','প্রজননের জন্য বিক্রি',  'Breeding Sale',    -1, false,false,true, false,false,false,false, true, true, false, 32),
  ('SALE_CULL',    'বাতিল প্রাণী বিক্রি',    'Cull Sale',        -1, false,false,true, false,false,false,false, true, true, false, 33),
  ('TRANSFER_OUT', 'শাখান্তর (প্রেরণ)',     'Transfer Out',     -1, false,false,false,false,true, false,false, false,false,false, 40),
  ('HOME_CONSUME', 'পারিবারিক ভোগ',       'Home Consumption', -1, false,false,false,false,false,true, false, false,false,false, 50),
  ('QURBANI',      'কুরবানি',              'Qurbani',          -1, false,false,false,false,false,false,true,  false,false,false, 51),
  ('SADAQAH',      'সদকা/দান',            'Sadaqah',          -1, false,false,false,false,false,false,true,  false,false,false, 52),
  ('ZAKAT',        'জাকাত',               'Zakat',            -1, false,false,false,false,false,false,true,  false,false,false, 53),
  ('GIFT_OUT',     'উপহার প্রদান',         'Gift Out',         -1, false,false,false,false,false,false,true,  false,false,false, 54),
  ('THEFT',        'চুরি',                 'Theft',            -1, false,false,false,false,false,false,false, false,false,true,  60),
  ('MISSING',      'নিখোঁজ',               'Missing',          -1, false,false,false,false,false,false,false, false,false,false, 61),
  ('COUNT_DOWN',   'গণনা সংশোধন (হ্রাস)',  'Count Correction-',-1, false,false,false,false,false,false,false, false,false,false, 62),
  ('CLOSING',      'ব্যাচ বন্ধ (অবশিষ্ট)',   'Closing Out',      -1, false,false,false,false,false,false,false, false,false,false, 70)
) as v(movement_type_code, name_bn, name_en, direction, is_mortality, is_culling, is_sale,
       is_purchase, is_internal_transfer, is_home_consumption, is_donation,
       requires_counterparty, requires_amount, requires_cause, sort_order)
where not exists (select 1 from master.movement_type t
  where t.organization_no is null and t.movement_type_code = v.movement_type_code::citext);

-- ---------------------------------------------------------------------
-- মৃতদেহ নিষ্পত্তি
--
-- অনিরাপদ পদ্ধতিগুলোও (মাছের খাদ্য, ব্যবসায়ীর কাছে বিক্রি) তালিকায়
-- রাখা হয়েছে — কারণ বাস্তবে এগুলো ঘটে। লুকিয়ে রাখলে পরামর্শ দেওয়া
-- যায় না; is_biosecure = false দেখে সিস্টেম নিজেই সতর্ক করতে পারবে।
-- ---------------------------------------------------------------------
insert into master.disposal_method (disposal_method_code, name_bn, name_en, is_biosecure, sort_order)
select v.* from (values
  ('DEEP_BURIAL_LIME','চুন দিয়ে গভীর গর্তে পুঁতে ফেলা','Deep Burial with Lime', true,  10),
  ('BURIAL',          'গর্তে পুঁতে ফেলা',              'Burial',                true,  11),
  ('INCINERATION',    'পুড়িয়ে ফেলা',                 'Incineration',          true,  12),
  ('DEAD_BIRD_PIT',   'ডেড বার্ড পিট',                'Dead Bird Pit',         true,  13),
  ('COMPOSTING',      'কম্পোস্ট করা',                'Composting',            true,  14),
  ('RENDERING',       'রেন্ডারিং প্ল্যান্টে পাঠানো',      'Rendering',             true,  15),
  ('FISH_FEED',       'মাছের খাদ্য হিসেবে দেওয়া',      'Fed to Fish',           false, 80),
  ('THROWN_OPEN',     'খোলা জায়গায়/পানিতে ফেলা',     'Thrown in Open/Water',  false, 81),
  ('SOLD',            'ব্যবসায়ীর কাছে বিক্রি',         'Sold to Trader',        false, 82),
  ('OTHER',           'অন্যান্য',                    'Other',                 false, 90)
) as v(disposal_method_code, name_bn, name_en, is_biosecure, sort_order)
where not exists (select 1 from master.disposal_method t
  where t.organization_no is null and t.disposal_method_code = v.disposal_method_code::citext);
