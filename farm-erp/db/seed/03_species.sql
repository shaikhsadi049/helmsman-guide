-- =====================================================================
-- 03_species.sql — প্রজাতি (গ্লোবাল সিড)
--
-- livestock_unit_weight নিয়ে একটা কথা:
-- এটা শেয়ার্ড খরচ (শ্রম, বিদ্যুৎ, পানি, ভাড়া) ভাগ করার ওজন। মানগুলো
-- প্রচলিত Livestock Unit রীতির কাছাকাছি, গরু = ১.০ ধরে। কিন্তু এগুলো
-- ধ্রুব সত্য নয় — প্রতিটা খামারে শ্রমের বাস্তব বিন্যাস ভিন্ন। তাই এগুলো
-- সম্পাদনযোগ্য ডিফল্ট, এবং খামারি নিজের হিসাবে বদলাতে পারবে।
-- =====================================================================

insert into master.species
  (species_code, name_bn, name_en, scientific_name, animal_class,
   default_tracking_mode, livestock_unit_weight, gestation_days, incubation_days,
   typical_lifespan_days, sort_order, note_bn)
select v.* from (values
  -- পাখি
  ('CHICKEN',     'মুরগি',      'Chicken',     'Gallus gallus domesticus', 'poultry',
     'group', 0.0100, null, 21, 2555, 10, null),
  ('DUCK',        'হাঁস',       'Duck',        'Anas platyrhynchos domesticus', 'poultry',
     'group', 0.0150, null, 28, 3285, 20, 'দেশি হাঁস প্রায়ই আধা-ছাড়া পালন হয়; খাদ্য খরচ কম'),
  ('MUSCOVY',     'চীনা হাঁস',   'Muscovy Duck','Cairina moschata', 'poultry',
     'group', 0.0200, null, 35, 3285, 21, null),
  ('GOOSE',       'রাজহাঁস',     'Goose',       'Anser cygnoides domesticus', 'poultry',
     'group', 0.0250, null, 30, 5475, 22, null),
  ('QUAIL',       'কোয়েল',     'Quail',       'Coturnix japonica', 'poultry',
     'group', 0.0020, null, 17, 730, 30, null),
  ('PIGEON',      'কবুতর',      'Pigeon',      'Columba livia domestica', 'poultry',
     'group', 0.0030, null, 18, 2190, 40, 'জোড়া ধরে হিসাব করা হয়; বাচ্চা (স্কোয়াব) বিক্রি হয়'),
  ('TURKEY',      'টার্কি',      'Turkey',      'Meleagris gallopavo', 'poultry',
     'group', 0.0300, null, 28, 3650, 50, null),
  ('GUINEA_FOWL', 'তিতির',      'Guinea Fowl', 'Numida meleagris', 'poultry',
     'group', 0.0120, null, 28, 3650, 51, null),
  -- রুমিন্যান্ট
  ('CATTLE',      'গরু',        'Cattle',      'Bos indicus', 'ruminant',
     'individual', 1.0000, 283, null, 6570, 60, null),
  ('BUFFALO',     'মহিষ',       'Buffalo',     'Bubalus bubalis', 'ruminant',
     'individual', 1.2000, 310, null, 7300, 61,
     'উপকূলীয় ও চরাঞ্চলে বাথান পদ্ধতিতে পালন হয়; দুধে চর্বি বেশি'),
  ('GOAT',        'ছাগল',       'Goat',        'Capra aegagrus hircus', 'ruminant',
     'individual', 0.1500, 150, null, 3650, 70, null),
  ('SHEEP',       'ভেড়া',       'Sheep',       'Ovis aries', 'ruminant',
     'individual', 0.1500, 148, null, 3650, 71, null),
  -- অন্যান্য
  ('RABBIT',      'খরগোশ',      'Rabbit',      'Oryctolagus cuniculus', 'other',
     'group', 0.0100, 31, null, 2920, 80, null),
  ('FISH',        'মাছ',        'Fish',        null, 'aquaculture',
     'group', 0.0001, null, null, 1095, 90,
     'সমন্বিত খামারে পুকুর প্রায় সবসময় থাকে — হাঁস-মাছ, মুরগি-মাছ। '
     'মাছের পূর্ণাঙ্গ ব্যবস্থাপনা আলাদা মডিউল, এখানে শুধু সমন্বয়ের জন্য')
) as v(species_code, name_bn, name_en, scientific_name, animal_class,
       default_tracking_mode, livestock_unit_weight, gestation_days, incubation_days,
       typical_lifespan_days, sort_order, note_bn)
where not exists (select 1 from master.species s
  where s.organization_no is null and s.species_code = v.species_code::citext);
