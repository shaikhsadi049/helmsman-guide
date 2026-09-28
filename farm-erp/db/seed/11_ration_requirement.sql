-- =====================================================================
-- 11_ration_requirement.sql — পুষ্টি চাহিদার টেমপ্লেট
--
-- ⚠ নির্দেশক মান। প্রকাশিত পুষ্টি সুপারিশ ও বাংলাদেশে প্রচলিত অনুশীলনের
--    কাছাকাছি। প্রকৃত চাহিদা নির্ভর করে জেনেটিক লাইন (কব/রস/হাই-লাইন),
--    আবহাওয়া (গরমে শক্তি কম খায় তাই ঘনত্ব বাড়াতে হয়), লক্ষ্য ওজন ও
--    উৎপাদনের হারের উপর। হ্যাচারি বা জাতের প্রস্তুতকারক নিজস্ব সুপারিশ
--    দেয় — সেটাই বেশি নির্ভরযোগ্য।
--
-- এককের রীতি: শতাংশভিত্তিক মান শতাংশের সংখ্যায় (২২% = ২২), শক্তি kcal/kg।
-- =====================================================================

create temporary table _req (
  set_code text, name_bn text, name_en text, species_code text, purpose_code text,
  phase_code text, from_day integer, to_day integer,
  nutrient_code text, min_v numeric, max_v numeric
);

insert into _req values
-- ══════════ ব্রয়লার ══════════
('BR_STARTER','ব্রয়লার স্টার্টার (০–১০ দিন)','Broiler Starter','CHICKEN','BROILER','BROODING',0,10,'ME_P',2950,null),
('BR_STARTER',null,null,null,null,null,null,null,'CP',22.0,null),
('BR_STARTER',null,null,null,null,null,null,null,'LYS',1.25,null),
('BR_STARTER',null,null,null,null,null,null,null,'MET',0.50,null),
('BR_STARTER',null,null,null,null,null,null,null,'MET_CYS',0.95,null),
('BR_STARTER',null,null,null,null,null,null,null,'CA',0.95,1.10),
('BR_STARTER',null,null,null,null,null,null,null,'P_AV',0.45,null),
('BR_STARTER',null,null,null,null,null,null,null,'CF',null,4.5),
('BR_STARTER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('BR_GROWER','ব্রয়লার গ্রোয়ার (১১–২৪ দিন)','Broiler Grower','CHICKEN','BROILER','GROWING',11,24,'ME_P',3050,null),
('BR_GROWER',null,null,null,null,null,null,null,'CP',20.5,null),
('BR_GROWER',null,null,null,null,null,null,null,'LYS',1.12,null),
('BR_GROWER',null,null,null,null,null,null,null,'MET',0.46,null),
('BR_GROWER',null,null,null,null,null,null,null,'MET_CYS',0.88,null),
('BR_GROWER',null,null,null,null,null,null,null,'CA',0.88,1.05),
('BR_GROWER',null,null,null,null,null,null,null,'P_AV',0.42,null),
('BR_GROWER',null,null,null,null,null,null,null,'CF',null,5.0),
('BR_GROWER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('BR_FINISHER','ব্রয়লার ফিনিশার (২৫ দিন+)','Broiler Finisher','CHICKEN','BROILER','FINISHING',25,null,'ME_P',3150,null),
('BR_FINISHER',null,null,null,null,null,null,null,'CP',18.5,null),
('BR_FINISHER',null,null,null,null,null,null,null,'LYS',1.00,null),
('BR_FINISHER',null,null,null,null,null,null,null,'MET',0.40,null),
('BR_FINISHER',null,null,null,null,null,null,null,'MET_CYS',0.78,null),
('BR_FINISHER',null,null,null,null,null,null,null,'CA',0.82,1.00),
('BR_FINISHER',null,null,null,null,null,null,null,'P_AV',0.38,null),
('BR_FINISHER',null,null,null,null,null,null,null,'CF',null,5.5),
('BR_FINISHER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

-- ══════════ লেয়ার ══════════
('LY_CHICK','লেয়ার চিক (০–৬ সপ্তাহ)','Layer Chick','CHICKEN','LAYER','BROODING',0,42,'ME_P',2850,null),
('LY_CHICK',null,null,null,null,null,null,null,'CP',19.5,null),
('LY_CHICK',null,null,null,null,null,null,null,'LYS',1.05,null),
('LY_CHICK',null,null,null,null,null,null,null,'MET',0.42,null),
('LY_CHICK',null,null,null,null,null,null,null,'MET_CYS',0.80,null),
('LY_CHICK',null,null,null,null,null,null,null,'CA',0.95,1.10),
('LY_CHICK',null,null,null,null,null,null,null,'P_AV',0.45,null),
('LY_CHICK',null,null,null,null,null,null,null,'CF',null,5.0),
('LY_CHICK',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('LY_GROWER','লেয়ার গ্রোয়ার (৭–১৬ সপ্তাহ)','Layer Grower','CHICKEN','LAYER','GROWING',43,112,'ME_P',2750,null),
('LY_GROWER',null,null,null,null,null,null,null,'CP',16.0,null),
('LY_GROWER',null,null,null,null,null,null,null,'LYS',0.78,null),
('LY_GROWER',null,null,null,null,null,null,null,'MET',0.32,null),
('LY_GROWER',null,null,null,null,null,null,null,'MET_CYS',0.62,null),
('LY_GROWER',null,null,null,null,null,null,null,'CA',0.90,1.05),
('LY_GROWER',null,null,null,null,null,null,null,'P_AV',0.38,null),
('LY_GROWER',null,null,null,null,null,null,null,'CF',null,7.0),
('LY_GROWER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('LY_PRELAY','লেয়ার প্রি-লে (১৭–১৯ সপ্তাহ)','Layer Pre-lay','CHICKEN','LAYER','PRELAY',113,133,'ME_P',2750,null),
('LY_PRELAY',null,null,null,null,null,null,null,'CP',17.5,null),
('LY_PRELAY',null,null,null,null,null,null,null,'LYS',0.85,null),
('LY_PRELAY',null,null,null,null,null,null,null,'MET',0.38,null),
('LY_PRELAY',null,null,null,null,null,null,null,'CA',2.00,2.50),
('LY_PRELAY',null,null,null,null,null,null,null,'P_AV',0.42,null),
('LY_PRELAY',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('LY_PHASE1','লেয়ার ফেজ ১ (২০–৪৫ সপ্তাহ, পিক)','Layer Phase 1','CHICKEN','LAYER','PEAK',134,315,'ME_P',2750,null),
('LY_PHASE1',null,null,null,null,null,null,null,'CP',17.5,null),
('LY_PHASE1',null,null,null,null,null,null,null,'LYS',0.85,null),
('LY_PHASE1',null,null,null,null,null,null,null,'MET',0.40,null),
('LY_PHASE1',null,null,null,null,null,null,null,'MET_CYS',0.72,null),
('LY_PHASE1',null,null,null,null,null,null,null,'CA',3.70,4.20),
('LY_PHASE1',null,null,null,null,null,null,null,'P_AV',0.40,null),
('LY_PHASE1',null,null,null,null,null,null,null,'CF',null,7.0),
('LY_PHASE1',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('LY_PHASE2','লেয়ার ফেজ ২ (৪৬ সপ্তাহ+)','Layer Phase 2','CHICKEN','LAYER','LATE_LAY',316,null,'ME_P',2700,null),
('LY_PHASE2',null,null,null,null,null,null,null,'CP',16.5,null),
('LY_PHASE2',null,null,null,null,null,null,null,'LYS',0.78,null),
('LY_PHASE2',null,null,null,null,null,null,null,'MET',0.37,null),
('LY_PHASE2',null,null,null,null,null,null,null,'CA',3.90,4.40),
('LY_PHASE2',null,null,null,null,null,null,null,'P_AV',0.36,null),
('LY_PHASE2',null,null,null,null,null,null,null,'SALT',0.25,0.45),

-- ══════════ সোনালি / দেশি ক্রস ══════════
('SN_GROWER','সোনালি গ্রোয়ার','Sonali Grower','CHICKEN','DUAL_POULTRY','GROWING',22,90,'ME_P',2800,null),
('SN_GROWER',null,null,null,null,null,null,null,'CP',18.0,null),
('SN_GROWER',null,null,null,null,null,null,null,'LYS',0.90,null),
('SN_GROWER',null,null,null,null,null,null,null,'MET',0.38,null),
('SN_GROWER',null,null,null,null,null,null,null,'CA',0.90,1.10),
('SN_GROWER',null,null,null,null,null,null,null,'P_AV',0.40,null),
('SN_GROWER',null,null,null,null,null,null,null,'CF',null,6.0),
('SN_GROWER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

-- ══════════ হাঁস ══════════
('DK_LAYER','হাঁস (ডিম)','Duck Layer','DUCK','EGG_DUCK','LAYING',141,null,'ME_P',2700,null),
('DK_LAYER',null,null,null,null,null,null,null,'CP',17.0,null),
('DK_LAYER',null,null,null,null,null,null,null,'LYS',0.80,null),
('DK_LAYER',null,null,null,null,null,null,null,'MET',0.35,null),
('DK_LAYER',null,null,null,null,null,null,null,'CA',3.00,3.60),
('DK_LAYER',null,null,null,null,null,null,null,'P_AV',0.38,null),
('DK_LAYER',null,null,null,null,null,null,null,'CF',null,7.0),
('DK_LAYER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('DK_MEAT','হাঁস (মাংস)','Meat Duck','DUCK','MEAT_DUCK','FINISHING',15,null,'ME_P',2900,null),
('DK_MEAT',null,null,null,null,null,null,null,'CP',19.0,null),
('DK_MEAT',null,null,null,null,null,null,null,'LYS',1.00,null),
('DK_MEAT',null,null,null,null,null,null,null,'MET',0.42,null),
('DK_MEAT',null,null,null,null,null,null,null,'CA',0.85,1.05),
('DK_MEAT',null,null,null,null,null,null,null,'P_AV',0.40,null),
('DK_MEAT',null,null,null,null,null,null,null,'SALT',0.25,0.45),

-- ══════════ কোয়েল ══════════
('QL_STARTER','কোয়েল স্টার্টার','Quail Starter','QUAIL','QUAIL_MEAT','BROODING',0,14,'ME_P',2900,null),
('QL_STARTER',null,null,null,null,null,null,null,'CP',24.0,null),
('QL_STARTER',null,null,null,null,null,null,null,'LYS',1.30,null),
('QL_STARTER',null,null,null,null,null,null,null,'MET',0.50,null),
('QL_STARTER',null,null,null,null,null,null,null,'CA',0.80,1.00),
('QL_STARTER',null,null,null,null,null,null,null,'P_AV',0.45,null),
('QL_STARTER',null,null,null,null,null,null,null,'CF',null,5.0),
('QL_STARTER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

('QL_LAYER','কোয়েল (ডিম)','Quail Layer','QUAIL','QUAIL_EGG','LAYING',42,null,'ME_P',2800,null),
('QL_LAYER',null,null,null,null,null,null,null,'CP',20.0,null),
('QL_LAYER',null,null,null,null,null,null,null,'LYS',1.00,null),
('QL_LAYER',null,null,null,null,null,null,null,'MET',0.45,null),
('QL_LAYER',null,null,null,null,null,null,null,'CA',2.50,3.00),
('QL_LAYER',null,null,null,null,null,null,null,'P_AV',0.42,null),
('QL_LAYER',null,null,null,null,null,null,null,'SALT',0.25,0.45),

-- ══════════ গরু ও মহিষ (দানাদার মিশ্রণ) ══════════
('CT_DAIRY','গরুর দানাদার (দুগ্ধ)','Dairy Concentrate','CATTLE','DAIRY',null,null,null,'TDN',70,null),
('CT_DAIRY',null,null,null,null,null,null,null,'CP',18.0,null),
('CT_DAIRY',null,null,null,null,null,null,null,'CA',0.70,1.10),
('CT_DAIRY',null,null,null,null,null,null,null,'P_TOT',0.45,null),
('CT_DAIRY',null,null,null,null,null,null,null,'CF',7.0,14.0),
('CT_DAIRY',null,null,null,null,null,null,null,'SALT',0.50,1.20),

('CT_FAT','গরুর দানাদার (হৃষ্টপুষ্টকরণ)','Fattening Concentrate','CATTLE','FATTENING',null,null,null,'TDN',72,null),
('CT_FAT',null,null,null,null,null,null,null,'CP',14.0,null),
('CT_FAT',null,null,null,null,null,null,null,'CA',0.60,1.00),
('CT_FAT',null,null,null,null,null,null,null,'P_TOT',0.35,null),
('CT_FAT',null,null,null,null,null,null,null,'CF',6.0,14.0),
('CT_FAT',null,null,null,null,null,null,null,'SALT',0.50,1.20),

('CT_CALF','বাছুরের স্টার্টার','Calf Starter','CATTLE','REARING','CALF',0,90,'TDN',74,null),
('CT_CALF',null,null,null,null,null,null,null,'CP',20.0,null),
('CT_CALF',null,null,null,null,null,null,null,'CA',0.80,1.20),
('CT_CALF',null,null,null,null,null,null,null,'P_TOT',0.50,null),
('CT_CALF',null,null,null,null,null,null,null,'CF',null,10.0),
('CT_CALF',null,null,null,null,null,null,null,'SALT',0.40,1.00),

('BF_DAIRY','মহিষের দানাদার (দুগ্ধ)','Buffalo Dairy Concentrate','BUFFALO','DAIRY',null,null,null,'TDN',70,null),
('BF_DAIRY',null,null,null,null,null,null,null,'CP',17.0,null),
('BF_DAIRY',null,null,null,null,null,null,null,'CA',0.70,1.10),
('BF_DAIRY',null,null,null,null,null,null,null,'P_TOT',0.45,null),
('BF_DAIRY',null,null,null,null,null,null,null,'CF',7.0,14.0),
('BF_DAIRY',null,null,null,null,null,null,null,'SALT',0.50,1.20),

-- ══════════ ছাগল ও ভেড়া ══════════
('GT_CONC','ছাগলের দানাদার','Goat Concentrate','GOAT','BREEDING_STOCK',null,null,null,'TDN',68,null),
('GT_CONC',null,null,null,null,null,null,null,'CP',16.0,null),
('GT_CONC',null,null,null,null,null,null,null,'CA',0.60,1.00),
('GT_CONC',null,null,null,null,null,null,null,'P_TOT',0.35,null),
('GT_CONC',null,null,null,null,null,null,null,'CF',7.0,15.0),
('GT_CONC',null,null,null,null,null,null,null,'SALT',0.40,1.00),

('GT_FAT','ছাগলের দানাদার (হৃষ্টপুষ্টকরণ)','Goat Fattening Concentrate','GOAT','FATTENING',null,null,null,'TDN',70,null),
('GT_FAT',null,null,null,null,null,null,null,'CP',15.0,null),
('GT_FAT',null,null,null,null,null,null,null,'CA',0.60,1.00),
('GT_FAT',null,null,null,null,null,null,null,'P_TOT',0.35,null),
('GT_FAT',null,null,null,null,null,null,null,'CF',6.0,14.0),
('GT_FAT',null,null,null,null,null,null,null,'SALT',0.40,1.00),

('SH_CONC','ভেড়ার দানাদার','Sheep Concentrate','SHEEP','BREEDING_STOCK',null,null,null,'TDN',68,null),
('SH_CONC',null,null,null,null,null,null,null,'CP',15.0,null),
('SH_CONC',null,null,null,null,null,null,null,'CA',0.60,1.00),
('SH_CONC',null,null,null,null,null,null,null,'P_TOT',0.35,null),
('SH_CONC',null,null,null,null,null,null,null,'CF',7.0,15.0),
('SH_CONC',null,null,null,null,null,null,null,'SALT',0.40,1.00);

-- সেটের শিরোনাম (যে সারিতে নাম দেওয়া আছে সেটাই শিরোনাম)
insert into master.ration_requirement_set
  (requirement_set_code, name_bn, name_en, species_no, production_purpose_no,
   phase_code, from_day, to_day, source_note_bn, sort_order)
select r.set_code, r.name_bn, r.name_en, s.species_no, p.production_purpose_no,
       r.phase_code::citext, r.from_day, r.to_day,
       'নির্দেশক মান — প্রকাশিত পুষ্টি সুপারিশ ও বাংলাদেশে প্রচলিত অনুশীলনের ভিত্তিতে। '
       'জাতের প্রস্তুতকারক বা হ্যাচারির নিজস্ব সুপারিশ পেলে সেটাই ব্যবহার করুন।',
       row_number() over (order by r.set_code)::smallint
  from _req r
  join master.species s on s.organization_no is null and s.species_code = r.species_code::citext
  join master.production_purpose p on p.organization_no is null
                                  and p.production_purpose_code = r.purpose_code::citext
 where r.name_bn is not null
   and not exists (select 1 from master.ration_requirement_set x
     where x.organization_no is null and x.requirement_set_code = r.set_code::citext);

insert into master.ration_requirement_line
  (ration_requirement_set_no, nutrient_no, min_per_kg, max_per_kg)
select rs.ration_requirement_set_no, n.nutrient_no, r.min_v, r.max_v
  from _req r
  join master.ration_requirement_set rs on rs.organization_no is null
                                       and rs.requirement_set_code = r.set_code::citext
  join master.nutrient n on n.organization_no is null and n.nutrient_code = r.nutrient_code::citext
 where not exists (select 1 from master.ration_requirement_line x
   where x.ration_requirement_set_no = rs.ration_requirement_set_no
     and x.nutrient_no = n.nutrient_no);

drop table _req;
