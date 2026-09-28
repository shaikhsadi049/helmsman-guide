-- =====================================================================
-- 01_uom.sql — একক ও রূপান্তর (গ্লোবাল সিড)
--
-- সব সারিতে organization_no = NULL, অর্থাৎ গ্লোবাল — সব খামারে এক।
-- idempotent: বারবার চালালেও ডুপ্লিকেট হবে না।
-- =====================================================================

insert into master.uom (uom_code, name_bn, name_en, dimension, is_base, decimal_places, note_bn)
select v.uom_code, v.name_bn, v.name_en, v.dimension, v.is_base, v.decimal_places, v.note_bn
from (values
  -- ভর
  ('KG',      'কেজি',        'Kilogram',      'mass',    true,  3, null),
  ('GM',      'গ্রাম',        'Gram',          'mass',    false, 1, null),
  ('TON',     'টন',          'Metric Ton',    'mass',    false, 4, null),
  ('MON',     'মন',          'Maund',         'mass',    false, 4, '১ মন = ৪০ সের = ৩৭.৩২৪২ কেজি'),
  ('SEER',    'সের',         'Seer',          'mass',    false, 4, '১ সের = ০.৯৩৩১০৫ কেজি'),
  -- সংখ্যা
  ('PCS',     'পিস',         'Piece',         'count',   true,  0, null),
  ('HALI',    'হালি',        'Hali (4 pcs)',  'count',   false, 2, 'ডিম/ফল বিক্রির প্রচলিত একক'),
  ('DOZEN',   'ডজন',         'Dozen',         'count',   false, 2, null),
  ('SHO',     'শ',           'Sho (100 pcs)', 'count',   false, 2, 'ডিমের পাইকারি দাম প্রতি শ-তে বলা হয়'),
  ('TRAY',    'ট্রে',         'Egg Tray',      'count',   false, 2, '১ ট্রে = ৩০টি ডিম'),
  ('BOSTA',   'বস্তা',        'Sack',          'count',   false, 2,
     'প্যাকেজিং একক। এক বস্তার কত কেজি তা পণ্যনির্ভর (ফিড সাধারণত ৫০ কেজি) — সেই তথ্য item টেবিলে, এখানে নয়'),
  ('BIRD',    'পাখি',        'Bird',          'count',   false, 0, null),
  ('HEAD',    'টি (প্রাণী)',  'Head',          'count',   false, 0, null),
  -- আয়তন
  ('LTR',     'লিটার',        'Litre',         'volume',  true,  3, null),
  ('ML',      'মিলি',         'Millilitre',    'volume',  false, 1, null),
  -- ক্ষেত্রফল (বাংলাদেশি জমির একক)
  ('SQFT',    'বর্গফুট',      'Square Foot',   'area',    true,  2, null),
  ('SHOTOK',  'শতক',         'Decimal',       'area',    false, 3, '১ শতক = ১/১০০ একর = ৪৩৫.৬ বর্গফুট'),
  ('KATHA',   'কাঠা',        'Katha',         'area',    false, 3, '১ কাঠা = ৭২০ বর্গফুট'),
  ('BIGHA',   'বিঘা',        'Bigha',         'area',    false, 4, '১ বিঘা = ২০ কাঠা = ১৪৪০০ বর্গফুট'),
  ('ACRE',    'একর',         'Acre',          'area',    false, 4, '১ একর = ৪৩৫৬০ বর্গফুট = ১০০ শতক'),
  ('HECTARE', 'হেক্টর',       'Hectare',       'area',    false, 4, null),
  -- দৈর্ঘ্য
  ('FT',      'ফুট',         'Foot',          'length',  true,  2, null),
  ('INCH',    'ইঞ্চি',        'Inch',          'length',  false, 2, null),
  ('METER',   'মিটার',        'Metre',         'length',  false, 3, null),
  -- সময়
  ('DAY',     'দিন',         'Day',           'time',    true,  0, null),
  ('WEEK',    'সপ্তাহ',       'Week',          'time',    false, 2, null),
  ('MONTH',   'মাস',         'Month',         'time',    false, 2, null),
  ('YEAR',    'বছর',         'Year',          'time',    false, 2, null),
  -- অনুপাত ও মুদ্রা
  ('PCT',     'শতাংশ',       'Percent',       'ratio',   true,  3, null),
  ('RATIO',   'অনুপাত',       'Ratio',         'ratio',   false, 4, 'যেমন FCR'),
  ('BDT',     'টাকা',        'Taka',          'currency',true,  2, null)
) as v(uom_code, name_bn, name_en, dimension, is_base, decimal_places, note_bn)
where not exists (
  select 1 from master.uom u
   where u.organization_no is null and u.uom_code = v.uom_code::citext
);

-- ---------------------------------------------------------------------
-- রূপান্তর: প্রতিটা অ-মূল একক → তার dimension-এর মূল এককে
-- ---------------------------------------------------------------------
insert into master.uom_conversion (from_uom_no, to_uom_no, factor)
select f.uom_no, b.uom_no, v.factor
from (values
  -- ভর → কেজি
  ('GM',      0.001),
  ('TON',     1000),
  ('MON',     37.3242),        -- ৪০ সের
  ('SEER',    0.933105),
  -- সংখ্যা → পিস
  ('HALI',    4),
  ('DOZEN',   12),
  ('SHO',     100),
  ('TRAY',    30),
  ('BIRD',    1),
  ('HEAD',    1),
  -- আয়তন → লিটার
  ('ML',      0.001),
  -- ক্ষেত্রফল → বর্গফুট
  ('SHOTOK',  435.6),
  ('KATHA',   720),
  ('BIGHA',   14400),
  ('ACRE',    43560),
  ('HECTARE', 107639.104),
  -- দৈর্ঘ্য → ফুট
  ('INCH',    0.0833333333),
  ('METER',   3.280839895),
  -- সময় → দিন
  ('WEEK',    7),
  ('MONTH',   30.4375),
  ('YEAR',    365.25)
) as v(from_code, factor)
join master.uom f on f.organization_no is null and f.uom_code = v.from_code::citext
join master.uom b on b.organization_no is null and b.is_base
                 and b.dimension = f.dimension
where not exists (
  select 1 from master.uom_conversion c
   where c.organization_no is null
     and c.from_uom_no = f.uom_no and c.to_uom_no = b.uom_no
);
