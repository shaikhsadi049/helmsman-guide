-- =====================================================================
-- smoke_test.sql — বাস্তব সমন্বিত খামার দিয়ে পরীক্ষা
--
-- এটা প্রদর্শনী নয়, পরীক্ষা। প্রতিটা দাবি যাচাই করা হয় এবং মিথ্যা হলে
-- ব্যতিক্রম ছুড়ে মাইগ্রেশন ব্যর্থ করে দেয়।
--
-- খামারটি ইচ্ছাকৃতভাবে সমন্বিত: ৫০০ লেয়ার, ৩০০ ব্রয়লার, ২৫ হাঁস,
-- ১টি গাভি, ২টি ছাগল — একই মালিক, একই ক্যাশবাক্স।
-- =====================================================================

do $smoke$
declare
  v_org     uuid;
  v_org2    uuid;
  v_user    uuid;
  v_farm    uuid;
  v_h_layer uuid; v_h_broiler uuid; v_h_duck uuid; v_h_cattle uuid; v_h_goat uuid;
  v_u_layer uuid; v_u_broiler uuid; v_u_duck uuid; v_u_cow uuid; v_u_goat uuid;
  v_n       integer;
  v_num     numeric;
  v_txt     text;
  v_log     uuid;
  v_ok      boolean;
begin
  -- ─────────────────────────────────────────────────────────────────
  -- ১. প্রতিষ্ঠান ও ব্যবহারকারী (প্ল্যাটফর্ম স্তরের কাজ, superuser দিয়ে)
  -- ─────────────────────────────────────────────────────────────────
  insert into core.organization (org_code, org_name, legal_form, owner_name, mobile,
                                 district, upazila, operating_mode)
  values ('KHAMAR01','রহিম সমন্বিত খামার','individual','মোঃ আব্দুর রহিম','01712345678',
          'বগুড়া','শেরপুর','household')
  returning organization_no into v_org;

  insert into core.organization (org_code, org_name, owner_name, district)
  values ('KHAMAR02','অন্য খামার (RLS পরীক্ষার জন্য)','করিম মিয়া','যশোর')
  returning organization_no into v_org2;

  insert into core.app_user (organization_no, login_id, full_name, mobile, user_type)
  values (v_org, 'rahim', 'মোঃ আব্দুর রহিম', '01712345678', 'owner')
  returning user_no into v_user;

  perform set_config('app.organization_no', v_org::text, true);
  perform set_config('app.user_no', v_user::text, true);

  -- ─────────────────────────────────────────────────────────────────
  -- ২. খামার ও ঘর
  -- ─────────────────────────────────────────────────────────────────
  insert into core.farm (organization_no, farm_code, farm_name, district, upazila,
                         land_area_decimal, established_on)
  values (v_org,'F01','বাড়ির খামার','বগুড়া','শেরপুর', 45.500, '2024-03-01')
  returning farm_no into v_farm;

  insert into core.house (organization_no, farm_no, house_code, house_name, house_type_no,
                          rearing_system_no, capacity_qty, length_ft, width_ft, height_ft,
                          construction_type, ventilation_type, has_generator)
  select v_org, v_farm, 'H-LAYER', '১ নং লেয়ার শেড',
         (select house_type_no from master.house_type where house_type_code='LAYER_CAGE' and organization_no is null),
         (select rearing_system_no from master.rearing_system where rearing_system_code='CAGE' and organization_no is null),
         600, 60, 22, 10, 'tin_shed', 'open_sided', true
  returning house_no into v_h_layer;

  insert into core.house (organization_no, farm_no, house_code, house_name, house_type_no,
                          rearing_system_no, capacity_qty, length_ft, width_ft, height_ft)
  select v_org, v_farm, 'H-BROILER', '২ নং ব্রয়লার শেড',
         (select house_type_no from master.house_type where house_type_code='BROILER_SHED' and organization_no is null),
         (select rearing_system_no from master.rearing_system where rearing_system_code='DEEP_LITTER' and organization_no is null),
         400, 40, 20, 9
  returning house_no into v_h_broiler;

  insert into core.house (organization_no, farm_no, house_code, house_name, house_type_no, rearing_system_no, capacity_qty)
  select v_org, v_farm, 'H-DUCK', 'হাঁসের ঘর',
         (select house_type_no from master.house_type where house_type_code='DUCK_SHED' and organization_no is null),
         (select rearing_system_no from master.rearing_system where rearing_system_code='SEMI_SCAVENGING' and organization_no is null),
         40
  returning house_no into v_h_duck;

  insert into core.house (organization_no, farm_no, house_code, house_name, house_type_no, rearing_system_no, capacity_qty)
  select v_org, v_farm, 'H-GOALA', 'গোয়ালঘর',
         (select house_type_no from master.house_type where house_type_code='CATTLE_BARN' and organization_no is null),
         (select rearing_system_no from master.rearing_system where rearing_system_code='ZERO_GRAZING' and organization_no is null),
         5
  returning house_no into v_h_cattle;

  insert into core.house (organization_no, farm_no, house_code, house_name, house_type_no, rearing_system_no, capacity_qty)
  select v_org, v_farm, 'H-CHAGOL', 'ছাগলের মাচা ঘর',
         (select house_type_no from master.house_type where house_type_code='GOAT_MACHA' and organization_no is null),
         (select rearing_system_no from master.rearing_system where rearing_system_code='MACHA' and organization_no is null),
         15
  returning house_no into v_h_goat;

  -- generated column সত্যিই হিসাব করছে কি না
  select floor_area_sqft into v_num from core.house where house_no = v_h_layer;
  if v_num <> 1320 then
    raise exception 'floor_area_sqft ভুল: প্রত্যাশা ১৩২০, পাওয়া গেছে %', v_num;
  end if;

  -- ─────────────────────────────────────────────────────────────────
  -- ৩. উৎপাদন ইউনিট — দলগত ও একক, একই টেবিলে
  -- ─────────────────────────────────────────────────────────────────
  -- (ক) লেয়ার ব্যাচ (দলগত)
  insert into prod.production_unit
    (organization_no, farm_no, house_no, unit_code, unit_name, species_no, breed_no,
     production_purpose_no, lifecycle_template_no, tracking_mode, source_type,
     source_ref_text, opened_on, age_reference_date)
  select v_org, v_farm, v_h_layer, 'L-2025-01', 'লেয়ার ব্যাচ ১',
         s.species_no, b.breed_no, p.production_purpose_no, t.lifecycle_template_no,
         'group', 'hatchery_doc', 'কাজী হ্যাচারি', '2025-01-10', '2025-01-10'
    from master.species s
    join master.breed b on b.species_no = s.species_no and b.breed_code = 'HYLINE_BROWN'
    join master.production_purpose p on p.production_purpose_code = 'LAYER'
    join master.lifecycle_template t on t.template_code = 'LAYER_80W'
   where s.species_code = 'CHICKEN' and s.organization_no is null
  returning production_unit_no into v_u_layer;

  insert into prod.flock (production_unit_no, organization_no, hatch_date, doc_supplier_name,
                          doc_unit_cost, doc_avg_weight_g, sexing)
  values (v_u_layer, v_org, '2025-01-10', 'কাজী হ্যাচারি', 62.00, 38.5, 'female');

  -- (খ) ব্রয়লার ব্যাচ (দলগত)
  insert into prod.production_unit
    (organization_no, farm_no, house_no, unit_code, unit_name, species_no, breed_no,
     production_purpose_no, lifecycle_template_no, tracking_mode, source_type,
     opened_on, age_reference_date)
  select v_org, v_farm, v_h_broiler, 'B-2025-07', 'ব্রয়লার ব্যাচ ৭',
         s.species_no, b.breed_no, p.production_purpose_no, t.lifecycle_template_no,
         'group', 'hatchery_doc', current_date - 35, current_date - 35
    from master.species s
    join master.breed b on b.species_no = s.species_no and b.breed_code = 'COBB500'
    join master.production_purpose p on p.production_purpose_code = 'BROILER'
    join master.lifecycle_template t on t.template_code = 'BROILER_35'
   where s.species_code = 'CHICKEN' and s.organization_no is null
  returning production_unit_no into v_u_broiler;

  insert into prod.flock (production_unit_no, organization_no, hatch_date, doc_supplier_name, doc_unit_cost)
  values (v_u_broiler, v_org, current_date - 35, 'নারিশ', 55.00);

  -- (গ) হাঁসের দল
  insert into prod.production_unit
    (organization_no, farm_no, house_no, unit_code, species_no, breed_no,
     production_purpose_no, tracking_mode, source_type, opened_on, age_reference_date)
  select v_org, v_farm, v_h_duck, 'D-2025-01',
         s.species_no, b.breed_no, p.production_purpose_no,
         'group', 'market_purchase', current_date - 200, current_date - 200
    from master.species s
    join master.breed b on b.species_no = s.species_no and b.breed_code = 'KHAKI_CAMPBELL'
    join master.production_purpose p on p.production_purpose_code = 'EGG_DUCK'
   where s.species_code = 'DUCK' and s.organization_no is null
  returning production_unit_no into v_u_duck;

  -- (ঘ) গাভি (একক) — একই টেবিল, ভিন্ন tracking_mode
  insert into prod.production_unit
    (organization_no, farm_no, house_no, unit_code, unit_name, species_no, breed_no,
     production_purpose_no, lifecycle_template_no, tracking_mode, source_type,
     opened_on, age_reference_date, age_is_estimated)
  select v_org, v_farm, v_h_cattle, 'C-001', 'লালী',
         s.species_no, b.breed_no, p.production_purpose_no, t.lifecycle_template_no,
         'individual', 'market_purchase', current_date - 400, current_date - 1200, true
    from master.species s
    join master.breed b on b.species_no = s.species_no and b.breed_code = 'HF_CROSS'
    join master.production_purpose p on p.production_purpose_code = 'DAIRY'
    join master.lifecycle_template t on t.template_code = 'DAIRY_COW'
   where s.species_code = 'CATTLE' and s.organization_no is null
  returning production_unit_no into v_u_cow;

  insert into prod.animal (production_unit_no, organization_no, tag_no, call_name, sex,
                           date_of_birth, colour_marking_bn, horn_status,
                           is_breeding_stock, purchased_on, purchase_cost)
  values (v_u_cow, v_org, 'BD-001', 'লালী', 'female', current_date - 1200,
          'লাল রঙ, কপালে সাদা তিলক, ডান পিছনের পা সাদা', 'horned',
          true, current_date - 400, 145000.00);

  -- (ঙ) ছাগল (একক)
  insert into prod.production_unit
    (organization_no, farm_no, house_no, unit_code, unit_name, species_no, breed_no,
     production_purpose_no, tracking_mode, source_type, opened_on, age_reference_date)
  select v_org, v_farm, v_h_goat, 'G-001', 'কালী',
         s.species_no, b.breed_no, p.production_purpose_no,
         'individual', 'own_born', current_date - 300, current_date - 300
    from master.species s
    join master.breed b on b.species_no = s.species_no and b.breed_code = 'BLACK_BENGAL'
    join master.production_purpose p on p.production_purpose_code = 'BREEDING_STOCK'
   where s.species_code = 'GOAT' and s.organization_no is null
  returning production_unit_no into v_u_goat;

  insert into prod.animal (production_unit_no, organization_no, tag_no, call_name, sex, date_of_birth)
  values (v_u_goat, v_org, 'BD-G01', 'কালী', 'female', current_date - 300);

  -- ─────────────────────────────────────────────────────────────────
  -- ৪. চলাচল
  -- ─────────────────────────────────────────────────────────────────
  -- লেয়ার: ৫০০ বাচ্চা ঢুকল, সময়ে ১৮টি মরেছে, ৫টি কালিং হয়েছে
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, unit_rate, total_amount, counterparty_name)
  select v_org, v_farm, v_u_layer, mt.movement_type_no, '2025-01-10', 500, 62.00, 31000.00, 'কাজী হ্যাচারি'
    from master.movement_type mt where mt.movement_type_code = 'DOC_RECEIPT' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, disease_no)
  select v_org, v_farm, v_u_layer, mt.movement_type_no, '2025-02-15', 18,
         (select disease_no from master.disease where disease_code='IBD' and organization_no is null)
    from master.movement_type mt where mt.movement_type_code = 'DEATH' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, disease_no)
  select v_org, v_farm, v_u_layer, mt.movement_type_no, '2025-06-20', 5,
         (select disease_no from master.disease where disease_code='CULL_LOW_YIELD' and organization_no is null)
    from master.movement_type mt where mt.movement_type_code = 'CULL' and mt.organization_no is null;

  -- ব্রয়লার: ৩০০ বাচ্চা ঢুকল
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, unit_rate, total_amount, counterparty_name)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 35, 300, 55.00, 16500.00, 'নারিশ ডিলার'
    from master.movement_type mt where mt.movement_type_code = 'DOC_RECEIPT' and mt.organization_no is null;

  -- মড়ক ১২টি (রানীক্ষেত ৫, হিট স্ট্রেস ৭)
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, disease_no, disposal_method_no)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 20, 5,
         (select disease_no from master.disease where disease_code='ND' and organization_no is null),
         (select disposal_method_no from master.disposal_method where disposal_method_code='DEEP_BURIAL_LIME' and organization_no is null)
    from master.movement_type mt where mt.movement_type_code = 'DEATH' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, disease_no)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 8, 7,
         (select disease_no from master.disease where disease_code='HEAT_STRESS' and organization_no is null)
    from master.movement_type mt where mt.movement_type_code = 'DEATH' and mt.organization_no is null;

  -- কালিং ৩টি (খোঁড়া)
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, disease_no)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 5, 3,
         (select disease_no from master.disease where disease_code='CULL_SICK' and organization_no is null)
    from master.movement_type mt where mt.movement_type_code = 'CULL' and mt.organization_no is null;

  -- বিক্রি ২৭০টি + পারিবারিক ভোগ ২টি + সদকা ১টি
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, total_weight_kg, unit_rate, total_amount, counterparty_name)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 1, 270,
         540.000, 175.00, 94500.00, 'ফড়িয়া — জামাল মিয়া'
    from master.movement_type mt where mt.movement_type_code = 'SALE_LIVE' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 1, 2
    from master.movement_type mt where mt.movement_type_code = 'HOME_CONSUME' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty)
  select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date - 1, 1
    from master.movement_type mt where mt.movement_type_code = 'SADAQAH' and mt.organization_no is null;

  -- গাভি ও ছাগল ঢুকল
  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty, total_amount, counterparty_name)
  select v_org, v_farm, v_u_cow, mt.movement_type_no, current_date - 400, 1, 145000.00, 'গরুর হাট — শেরপুর'
    from master.movement_type mt where mt.movement_type_code = 'PURCHASE' and mt.organization_no is null;

  insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
    movement_type_no, movement_date, qty)
  select v_org, v_farm, v_u_goat, mt.movement_type_no, current_date - 300, 1
    from master.movement_type mt where mt.movement_type_code = 'BIRTH' and mt.organization_no is null;

  -- ═════════════════ যাচাই ১: স্টকের হিসাব ═════════════════
  select current_qty into v_n from prod.v_unit_balance where production_unit_no = v_u_broiler;
  -- ৩০০ - ১২ মড়ক - ৩ কালিং - ২৭০ বিক্রি - ২ ভোগ - ১ সদকা = ১২
  if v_n <> 12 then
    raise exception 'ব্রয়লারের অবশিষ্ট সংখ্যা ভুল: প্রত্যাশা ১২, পাওয়া গেছে %', v_n;
  end if;

  select mortality_pct into v_num from prod.v_unit_balance where production_unit_no = v_u_broiler;
  if round(v_num,2) <> 4.00 then    -- 12/300
    raise exception 'মড়কের হার ভুল: প্রত্যাশা ৪.০০%%, পাওয়া গেছে %', v_num;
  end if;

  select depletion_pct into v_num from prod.v_unit_balance where production_unit_no = v_u_broiler;
  if round(v_num,2) <> 5.00 then    -- (12+3)/300
    raise exception 'অবক্ষয়ের হার ভুল: প্রত্যাশা ৫.০০%%, পাওয়া গেছে %', v_num;
  end if;

  select total_donated_qty + total_home_qty into v_n
    from prod.v_unit_balance where production_unit_no = v_u_broiler;
  if v_n <> 3 then
    raise exception 'ভোগ ও দানের সংখ্যা ভুল: প্রত্যাশা ৩, পাওয়া গেছে %', v_n;
  end if;

  -- লেয়ার: ৫০০ - ১৮ - ৫ = ৪৭৭
  select current_qty into v_n from prod.v_unit_balance where production_unit_no = v_u_layer;
  if v_n <> 477 then
    raise exception 'লেয়ারের অবশিষ্ট সংখ্যা ভুল: প্রত্যাশা ৪৭৭, পাওয়া গেছে %', v_n;
  end if;

  -- ═════════════════ যাচাই ২: ঋণাত্মক স্টক আটকায় কি ═════════════════
  begin
    insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
      movement_type_no, movement_date, qty, total_amount, counterparty_name)
    select v_org, v_farm, v_u_broiler, mt.movement_type_no, current_date, 100, 1000, 'কেউ'
      from master.movement_type mt where mt.movement_type_code='SALE_LIVE' and mt.organization_no is null;
    raise exception 'ব্যর্থ: ১২টি থেকে ১০০টি বিক্রি হয়ে গেল!';
  exception when check_violation then
    null;  -- প্রত্যাশিত
  end;

  -- ═════════════════ যাচাই ৩: চলাচল অপরিবর্তনীয় ═════════════════
  begin
    update prod.unit_movement set qty = 1
     where production_unit_no = v_u_broiler and qty = 270;
    raise exception 'ব্যর্থ: অ্যাপেন্ড-অনলি টেবিল সম্পাদনা করা গেল!';
  exception when restrict_violation then
    null;
  end;

  -- ═════════════════ যাচাই ৪: দৈনিক লগ ও মেট্রিক প্রযোজ্যতা ═════════════════
  insert into prod.daily_log (organization_no, farm_no, production_unit_no, log_date,
                              recorded_by_user_no, is_complete, remarks_bn)
  values (v_org, v_farm, v_u_layer, current_date - 1, v_user, true, 'স্বাভাবিক দিন')
  returning daily_log_no into v_log;

  -- বয়স স্বয়ংক্রিয়ভাবে বসেছে কি
  select age_day into v_n from prod.daily_log where daily_log_no = v_log;
  if v_n <> (current_date - 1 - date '2025-01-10') then
    raise exception 'বয়স স্বয়ংক্রিয়ভাবে বসেনি: %', v_n;
  end if;

  -- লেয়ারে ডিম বসানো বৈধ
  insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, int_value)
  select v_org, v_log, m.metric_no, 437
    from master.metric_definition m where m.metric_code='egg_total' and m.organization_no is null;

  insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, num_value)
  select v_org, v_log, m.metric_no, 58.500
    from master.metric_definition m where m.metric_code='feed_intake_kg' and m.organization_no is null;

  -- uom স্বয়ংক্রিয়ভাবে বসেছে কি
  select u.uom_code into v_txt
    from prod.daily_log_value dlv
    join master.uom u on u.uom_no = dlv.uom_no
    join master.metric_definition m on m.metric_no = dlv.metric_no
   where dlv.daily_log_no = v_log and m.metric_code = 'feed_intake_kg';
  if v_txt <> 'KG' then
    raise exception 'ডিফল্ট একক বসেনি: %', v_txt;
  end if;

  -- ব্রয়লারে ডিম বসানো অবৈধ হওয়া উচিত
  insert into prod.daily_log (organization_no, farm_no, production_unit_no, log_date, recorded_by_user_no)
  values (v_org, v_farm, v_u_broiler, current_date - 2, v_user)
  returning daily_log_no into v_log;

  begin
    insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, int_value)
    select v_org, v_log, m.metric_no, 100
      from master.metric_definition m where m.metric_code='egg_total' and m.organization_no is null;
    raise exception 'ব্যর্থ: ব্রয়লারে ডিমের হিসাব বসানো গেল!';
  exception when check_violation then
    null;
  end;

  -- মড়ক দৈনিক লগে বসানো অবৈধ হওয়া উচিত
  begin
    insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, int_value)
    select v_org, v_log, m.metric_no, 5
      from master.metric_definition m where m.metric_code='mortality_qty' and m.organization_no is null;
    raise exception 'ব্যর্থ: মড়ক দৈনিক লগে বসানো গেল — দুই জায়গায় সত্য তৈরি হলো!';
  exception when check_violation then
    null;
  end;

  -- সীমার বাইরে মান আটকায় কি (৪০ কেজির ব্রয়লার = টাইপো)
  begin
    insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, num_value)
    select v_org, v_log, m.metric_no, 40000000
      from master.metric_definition m where m.metric_code='body_weight_avg_g' and m.organization_no is null;
    raise exception 'ব্যর্থ: অসম্ভব ওজন গ্রহণ করা হলো!';
  exception when check_violation then
    null;
  end;

  -- গাভিতে দুধ বৈধ, ডিম অবৈধ
  insert into prod.daily_log (organization_no, farm_no, production_unit_no, log_date, recorded_by_user_no)
  values (v_org, v_farm, v_u_cow, current_date - 1, v_user)
  returning daily_log_no into v_log;

  insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, num_value)
  select v_org, v_log, m.metric_no, 6.500
    from master.metric_definition m where m.metric_code='milk_morning_litre' and m.organization_no is null;
  insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, num_value)
  select v_org, v_log, m.metric_no, 5.250
    from master.metric_definition m where m.metric_code='milk_evening_litre' and m.organization_no is null;
  insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, num_value)
  select v_org, v_log, m.metric_no, 18.000
    from master.metric_definition m where m.metric_code='green_fodder_kg' and m.organization_no is null;

  begin
    insert into prod.daily_log_value (organization_no, daily_log_no, metric_no, int_value)
    select v_org, v_log, m.metric_no, 1
      from master.metric_definition m where m.metric_code='egg_total' and m.organization_no is null;
    raise exception 'ব্যর্থ: গাভি ডিম দিল!';
  exception when check_violation then
    null;
  end;

  -- ═════════════════ যাচাই ৫: অডিট কলাম স্বয়ংক্রিয় ═════════════════
  select ss_created_by, ss_row_version into v_user, v_n
    from prod.production_unit where production_unit_no = v_u_layer;
  if v_user is null then raise exception 'ss_created_by বসেনি'; end if;
  if v_n <> 1 then raise exception 'ss_row_version প্রাথমিক মান ১ নয়: %', v_n; end if;

  update prod.production_unit set unit_name = 'লেয়ার ব্যাচ ১ (সংশোধিত)'
   where production_unit_no = v_u_layer;

  select ss_row_version, ss_modified_time is not null
    into v_n, v_ok
    from prod.production_unit where production_unit_no = v_u_layer;
  if v_n <> 2 then raise exception 'ss_row_version বাড়েনি: %', v_n; end if;
  if not v_ok then raise exception 'ss_modified_time বসেনি'; end if;

  -- ═════════════════ যাচাই ৬: অপরিবর্তনীয় ফিল্ড ═════════════════
  begin
    update prod.production_unit set organization_no = v_org2
     where production_unit_no = v_u_layer;
    raise exception 'ব্যর্থ: organization_no বদলানো গেল!';
  exception when check_violation then
    null;
  end;

  begin
    update prod.production_unit set tracking_mode = 'individual'
     where production_unit_no = v_u_layer;
    raise exception 'ব্যর্থ: tracking_mode বদলানো গেল!';
  exception when check_violation or foreign_key_violation then
    null;
  end;

  -- ═════════════════ যাচাই ৭: ভুল ধরনের সন্তান সারি ═════════════════
  begin
    -- গাভি (individual) ইউনিটে flock সারি বসানো যাবে না
    insert into prod.flock (production_unit_no, organization_no, doc_supplier_name)
    values (v_u_cow, v_org, 'ভুল সারি');
    raise exception 'ব্যর্থ: একক প্রাণীর ইউনিটে ফ্লক সারি বসানো গেল!';
  exception when foreign_key_violation then
    null;
  end;

  -- ═════════════════ যাচাই ৮: একক প্রাণীর সংখ্যা সর্বদা ১ ═════════════════
  begin
    insert into prod.unit_movement (organization_no, farm_no, production_unit_no,
      movement_type_no, movement_date, qty)
    select v_org, v_farm, v_u_goat, mt.movement_type_no, current_date, 5
      from master.movement_type mt where mt.movement_type_code='BIRTH' and mt.organization_no is null;
    raise exception 'ব্যর্থ: একটা ছাগল ৫টা হয়ে গেল!';
  exception when check_violation then
    null;
  end;

  -- ═════════════════ যাচাই ৯: অর্থবছর পরস্পর ছেদ করে না ═════════════════
  insert into core.fiscal_year (organization_no, fy_code, start_date, end_date)
  values (v_org, '2025-26', '2025-07-01', '2026-06-30');
  begin
    insert into core.fiscal_year (organization_no, fy_code, start_date, end_date)
    values (v_org, '2026-27-ভুল', '2026-06-01', '2027-05-31');
    raise exception 'ব্যর্থ: ছেদকারী অর্থবছর গ্রহণ করা হলো!';
  exception when exclusion_violation then
    null;
  end;

  raise notice 'স্মোক টেস্ট সফল — ৯টি বিভাগের সব যাচাই পাস করেছে।';
end
$smoke$;

-- ---------------------------------------------------------------------
-- সমন্বিত খামারের ছবি
-- ---------------------------------------------------------------------
select o.org_name as "খামার",
       s.name_bn  as "প্রজাতি",
       b.name_bn  as "জাত",
       pp.name_bn as "উদ্দেশ্য",
       pu.unit_code as "ইউনিট",
       pu.tracking_mode as "ট্র্যাকিং",
       vb.current_qty   as "বর্তমান",
       vb.total_dead_qty as "মড়ক",
       vb.mortality_pct  as "মড়ক %",
       vb.depletion_pct  as "অবক্ষয় %"
  from prod.production_unit pu
  join core.organization o on o.organization_no = pu.organization_no
  join master.species s on s.species_no = pu.species_no
  left join master.breed b on b.breed_no = pu.breed_no
  join master.production_purpose pp on pp.production_purpose_no = pu.production_purpose_no
  join prod.v_unit_balance vb on vb.production_unit_no = pu.production_unit_no
 where o.org_code = 'KHAMAR01'
 order by s.sort_order, pu.unit_code;
