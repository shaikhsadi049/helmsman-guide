-- =====================================================================
-- feed_test.sql — গুদাম ও রেশন ফরমুলেশনের পরীক্ষা
--
-- smoke_test.sql এর তৈরি খামারের উপরেই চলে (KHAMAR01, ব্রয়লার ব্যাচ B-2025-07)।
-- প্রতিটা দাবি যাচাই করা হয়; মিথ্যা হলে ব্যতিক্রম ছুড়ে বিল্ড ব্যর্থ করে।
-- =====================================================================

do $feed$
declare
  v_org     uuid;
  v_farm    uuid;
  v_user    uuid;
  v_store   uuid;
  v_unit    uuid;
  v_f1      uuid;    -- অপটিমাইজ করা ফরমুলা
  v_f2      uuid;    -- সীমা চাপানো ফরমুলা (তুলনার জন্য)
  v_set     uuid;
  v_lot     uuid;
  v_n       integer;
  v_num     numeric;
  v_cost1   numeric;
  v_cost2   numeric;
  v_kg      numeric;
  v_txt     text;
  v_status  text;
  v_maize   uuid;
  v_sbm     uuid;
  v_rf      uuid;
  v_mixval  numeric;
  rec       record;
begin
  select organization_no into v_org from core.organization where org_code = 'KHAMAR01';
  select farm_no into v_farm from core.farm where organization_no = v_org and farm_code = 'F01';
  select user_no into v_user from core.app_user where login_id = 'rahim';
  select production_unit_no into v_unit from prod.production_unit
   where organization_no = v_org and unit_code = 'B-2025-07';

  perform set_config('app.organization_no', v_org::text, true);
  perform set_config('app.user_no', v_user::text, true);

  select item_no into v_maize from master.item where organization_no is null and item_code = 'MAIZE';
  select item_no into v_sbm   from master.item where organization_no is null and item_code = 'SBM44';
  select item_no into v_rf    from master.item where organization_no is null and item_code = 'RF_BROILER_GROWER';

  -- ═════════════════ ১. গুদাম ও নিজের ক্রয়মূল্য ═════════════════
  insert into inv.store (organization_no, farm_no, store_code, store_name, store_type, is_default)
  values (v_org, v_farm, 'ST-01', 'প্রধান খাদ্য গুদাম', 'feed', true)
  returning store_no into v_store;

  -- নিজের বাস্তব ক্রয়মূল্য — এতে সিডের অনুমান আর ব্যবহার হবে না
  insert into inv.item_price (organization_no, item_no, effective_from, unit_cost, source_note_bn)
  select v_org, i.item_no, current_date - 30, v.rate, 'শেরপুর বাজার, নিজের ক্রয়'
    from (values
      ('MAIZE',33.50),('SBM44',63.00),('RICE_POLISH',34.00),('MUSTARD_CAKE',41.00),
      ('FULLFAT_SOY',76.00),('SOY_OIL',152.00),('OYSTER_SHELL',11.50),('DCP',61.00),
      ('SALT',17.00),('DL_MET',425.00),('LYSINE',385.00),('WHEAT_BRAN',27.50)
    ) as v(code, rate)
    join master.item i on i.organization_no is null and i.item_code = v.code::citext;

  -- ═════════════════ ২. ফরমুলা: ব্রয়লার গ্রোয়ার ═════════════════
  select ration_requirement_set_no into v_set
    from master.ration_requirement_set
   where organization_no is null and requirement_set_code = 'BR_GROWER';

  insert into feed.ration_formula
    (organization_no, formula_code, name_bn, species_no, production_purpose_no,
     ration_requirement_set_no, batch_size_kg, priced_on)
  select v_org, 'F-BR-GROW-1', 'ব্রয়লার গ্রোয়ার — নিজের মিক্স',
         s.species_no, p.production_purpose_no, v_set, 100, current_date
    from master.species s, master.production_purpose p
   where s.organization_no is null and s.species_code = 'CHICKEN'
     and p.organization_no is null and p.production_purpose_code = 'BROILER'
  returning ration_formula_no into v_f1;

  -- স্থানীয়ভাবে যা পাওয়া যায় শুধু সেগুলোই, বাস্তবসম্মত সীমা সহ
  insert into feed.ration_formula_line
    (organization_no, ration_formula_no, item_no, min_pct, max_pct, sort_order)
  select v_org, v_f1, i.item_no, v.lo, v.hi, v.ord
    from (values
      ('MAIZE',        0.00, 65.00, 10),
      ('SBM44',        0.00, 40.00, 20),
      ('FULLFAT_SOY',  0.00, 15.00, 25),
      ('RICE_POLISH',  0.00, 10.00, 30),   -- চর্বি বেশি, তাই সীমিত
      ('MUSTARD_CAKE', 0.00,  7.00, 35),   -- গ্লুকোসিনোলেট, তাই ৭%
      ('WHEAT_BRAN',   0.00,  8.00, 40),
      ('SOY_OIL',      0.00,  5.00, 45),
      ('OYSTER_SHELL', 0.00,  2.00, 50),
      ('DCP',          0.00,  2.00, 55),
      ('SALT',         0.25,  0.45, 60),
      ('DL_MET',       0.00,  0.50, 65),
      ('LYSINE',       0.00,  0.50, 70)
    ) as v(code, lo, hi, ord)
    join master.item i on i.organization_no is null and i.item_code = v.code::citext;

  -- ═════════════════ ৩. অপটিমাইজ ═════════════════
  select o.status, o.total_cost into v_status, v_cost1
    from feed.optimize_formula(v_f1, true) o limit 1;

  if v_status <> 'optimal' then
    raise exception 'অপটিমাইজেশন সফল হয়নি: %', v_status;
  end if;

  -- যোগফল ঠিক ১০০ কেজি
  select sum(qty_kg) into v_kg from feed.ration_formula_line
   where ration_formula_no = v_f1 and ss_deleted_flag = false;
  if abs(v_kg - 100) > 0.01 then
    raise exception 'ফরমুলার যোগফল ১০০ কেজি নয়: %', v_kg;
  end if;

  -- প্রতিটা সীমা মানা হয়েছে কি
  for rec in
    select l.item_no, it.name_bn, l.qty_kg, l.min_pct, l.max_pct
      from feed.ration_formula_line l
      join master.item it on it.item_no = l.item_no
     where l.ration_formula_no = v_f1 and l.ss_deleted_flag = false
  loop
    if rec.min_pct is not null and rec.qty_kg < rec.min_pct - 0.01 then
      raise exception '% এর নিম্নসীমা % শতাংশ ভাঙা হয়েছে, দেওয়া হয়েছে % কেজি',
        rec.name_bn, rec.min_pct, rec.qty_kg;
    end if;
    if rec.max_pct is not null and rec.qty_kg > rec.max_pct + 0.01 then
      raise exception '% এর উচ্চসীমা % শতাংশ ভাঙা হয়েছে, দেওয়া হয়েছে % কেজি',
        rec.name_bn, rec.max_pct, rec.qty_kg;
    end if;
  end loop;

  -- পুষ্টি চাহিদা পূরণ হয়েছে কি — একটাও লঙ্ঘন থাকা চলবে না
  select count(*) into v_n from feed.evaluate_formula(v_f1) e
   where e.verdict in ('কম','বেশি');
  if v_n > 0 then
    select string_agg(format('%s (অর্জিত %s, চাহিদা %s–%s)',
                             e.nutrient_code, e.achieved_per_kg,
                             coalesce(e.min_per_kg::text,'—'), coalesce(e.max_per_kg::text,'—')), '; ')
      into v_txt from feed.evaluate_formula(v_f1) e where e.verdict in ('কম','বেশি');
    raise exception 'অপটিমাইজ করা ফরমুলায় % টি পুষ্টি চাহিদা ভাঙা: %', v_n, v_txt;
  end if;

  -- ═════════════════ ৪. সর্বোত্তমতার পরীক্ষা ═════════════════
  -- একটা উপাদানকে তার সর্বোত্তম মাত্রার উপরে যেতে বাধ্য করলে খরচ বাড়তেই হবে।
  -- না বাড়লে আগের সমাধান সর্বোত্তম ছিল না।
  select qty_kg into v_num from feed.ration_formula_line
   where ration_formula_no = v_f1 and item_no = v_maize;

  insert into feed.ration_formula
    (organization_no, formula_code, name_bn, species_no, production_purpose_no,
     ration_requirement_set_no, batch_size_kg, priced_on)
  select v_org, 'F-BR-GROW-2', 'ব্রয়লার গ্রোয়ার — ভুট্টা জোর করে বাড়ানো',
         species_no, production_purpose_no, v_set, 100, current_date
    from feed.ration_formula where ration_formula_no = v_f1
  returning ration_formula_no into v_f2;

  insert into feed.ration_formula_line
    (organization_no, ration_formula_no, item_no, min_pct, max_pct, sort_order)
  select v_org, v_f2, l.item_no,
         case when l.item_no = v_maize
              then least(round(v_num + 5, 2), 65)     -- ভুট্টা ৫% বেশি দিতে বাধ্য
              else l.min_pct end,
         l.max_pct, l.sort_order
    from feed.ration_formula_line l
   where l.ration_formula_no = v_f1 and l.ss_deleted_flag = false;

  select o.status, o.total_cost into v_status, v_cost2
    from feed.optimize_formula(v_f2, true) o limit 1;

  if v_status = 'optimal' and v_cost2 < v_cost1 - 0.01 then
    raise exception
      'সর্বোত্তমতা ভুল: সীমা চাপানোর পরেও খরচ কমে গেল (% → %)', v_cost1, v_cost2;
  end if;

  -- ═════════════════ ৫. অসম্ভব চাহিদা ═════════════════
  -- এই উপাদানগুলো দিয়ে ৪৫% আমিষ সম্ভব নয় (সর্বোচ্চ SBM ৪০% হলেও)
  update master.ration_requirement_line
     set min_per_kg = 45
   where ration_requirement_set_no = v_set
     and nutrient_no = (select nutrient_no from master.nutrient
                         where organization_no is null and nutrient_code = 'CP');

  select o.status into v_status from feed.optimize_formula(v_f1, false) o limit 1;
  if v_status <> 'infeasible' then
    raise exception 'অসম্ভব চাহিদাতেও status = % পাওয়া গেল', v_status;
  end if;

  update master.ration_requirement_line
     set min_per_kg = 20.5
   where ration_requirement_set_no = v_set
     and nutrient_no = (select nutrient_no from master.nutrient
                         where organization_no is null and nutrient_code = 'CP');

  -- ═════════════════ ৬. স্টক: ক্রয় ও ভারিত গড় ═════════════════
  insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
    stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
  select v_org, v_farm, v_store, v_maize, mt.stock_movement_type_no,
         current_date - 20, 1000, 32.00, 'শেরপুর আড়ত'
    from master.stock_movement_type mt
   where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';

  insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
    stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
  select v_org, v_farm, v_store, v_maize, mt.stock_movement_type_no,
         current_date - 10, 500, 36.00, 'শেরপুর আড়ত'
    from master.stock_movement_type mt
   where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';

  -- ভারিত গড় = (১০০০×৩২ + ৫০০×৩৬) / ১৫০০ = ৩৩.৩৩৩৩
  select avg_unit_cost into v_num from inv.v_stock_balance
   where organization_no = v_org and store_no = v_store and item_no = v_maize;
  if abs(v_num - 33.3333) > 0.001 then
    raise exception 'ভারিত গড় খরচ ভুল: প্রত্যাশা ৩৩.৩৩৩৩, পাওয়া গেছে %', v_num;
  end if;

  select qty_on_hand into v_num from inv.v_stock_balance
   where organization_no = v_org and store_no = v_store and item_no = v_maize;
  if v_num <> 1500 then
    raise exception 'স্টক পরিমাণ ভুল: প্রত্যাশা ১৫০০, পাওয়া গেছে %', v_num;
  end if;

  insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
    stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
  select v_org, v_farm, v_store, v_sbm, mt.stock_movement_type_no,
         current_date - 20, 500, 63.00, 'ঢাকা ডিলার'
    from master.stock_movement_type mt
   where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';

  -- ═════════════════ ৭. ঋণাত্মক স্টক আটকায় কি ═════════════════
  begin
    insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
      stock_movement_type_no, movement_date, qty, production_unit_no)
    select v_org, v_farm, v_store, v_maize, mt.stock_movement_type_no,
           current_date, 5000, v_unit
      from master.stock_movement_type mt
     where mt.organization_no is null and mt.stock_movement_type_code = 'ISSUE_UNIT';
    raise exception 'ব্যর্থ: ১৫০০ কেজি থেকে ৫০০০ কেজি বের করা গেল!';
  exception when check_violation then
    null;
  end;

  -- ═════════════════ ৮. ব্যাচে দেওয়া ও বেরোনোর খরচ ═════════════════
  insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
    stock_movement_type_no, movement_date, qty, production_unit_no)
  select v_org, v_farm, v_store, v_maize, mt.stock_movement_type_no,
         current_date, 300, v_unit
    from master.stock_movement_type mt
   where mt.organization_no is null and mt.stock_movement_type_code = 'ISSUE_UNIT';

  -- বেরোনোর দর ট্রিগারই বসিয়েছে, দেওয়া হয়নি — ভারিত গড় হওয়া উচিত
  select unit_cost into v_num from inv.stock_movement
   where organization_no = v_org and item_no = v_maize
     and production_unit_no = v_unit order by ss_sync_seq desc limit 1;
  if abs(v_num - 33.3333) > 0.001 then
    raise exception 'ব্যাচে দেওয়ার খরচ ভারিত গড়ের সমান নয়: %', v_num;
  end if;

  -- ইস্যুর পরেও গড় অপরিবর্তিত থাকা উচিত (ভারিত গড়ের ধর্ম)
  select avg_unit_cost into v_num from inv.v_stock_balance
   where organization_no = v_org and store_no = v_store and item_no = v_maize;
  if abs(v_num - 33.3333) > 0.001 then
    raise exception 'ইস্যুর পরে গড় বদলে গেছে: %', v_num;
  end if;

  -- ব্যাচের খরচের ভিউ
  select feed_cost into v_num from inv.v_unit_input_cost
   where production_unit_no = v_unit and item_type = 'feed_ingredient';
  if abs(v_num - round(300 * 33.3333, 4)) > 0.05 then
    raise exception 'ব্যাচের খাদ্য খরচ ভুল: প্রত্যাশা ~%, পাওয়া গেছে %',
      round(300 * 33.3333, 2), v_num;
  end if;

  -- ═════════════════ ৯. লট বাধ্যতামূলক পণ্য ═════════════════
  begin
    insert into inv.stock_movement (organization_no, farm_no, store_no, item_no,
      stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
    select v_org, v_farm, v_store, v_rf, mt.stock_movement_type_no,
           current_date, 100, 58.00, 'ডিলার'
      from master.stock_movement_type mt
     where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';
    raise exception 'ব্যর্থ: লট-বাধ্যতামূলক পণ্য লট ছাড়াই ঢুকল!';
  exception when not_null_violation then
    null;
  end;

  insert into inv.stock_lot (organization_no, item_no, lot_code, manufacture_date,
                             expiry_date, supplier_name, received_on)
  values (v_org, v_rf, 'LOT-2026-09', current_date - 5, current_date + 10,
          'স্থানীয় ডিলার', current_date - 3)
  returning stock_lot_no into v_lot;

  insert into inv.stock_movement (organization_no, farm_no, store_no, item_no, stock_lot_no,
    stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
  select v_org, v_farm, v_store, v_rf, v_lot, mt.stock_movement_type_no,
         current_date - 3, 200, 58.00, 'স্থানীয় ডিলার'
    from master.stock_movement_type mt
   where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';

  select days_to_expiry into v_n from inv.v_stock_lot_balance
   where organization_no = v_org and stock_lot_no = v_lot;
  if v_n <> 10 then
    raise exception 'মেয়াদের হিসাব ভুল: প্রত্যাশা ১০ দিন, পাওয়া গেছে %', v_n;
  end if;

  -- অন্য পণ্যের লট দিয়ে চলাচল আটকানো উচিত
  begin
    insert into inv.stock_movement (organization_no, farm_no, store_no, item_no, stock_lot_no,
      stock_movement_type_no, movement_date, qty, unit_cost, counterparty_name)
    select v_org, v_farm, v_store, v_maize, v_lot, mt.stock_movement_type_no,
           current_date, 50, 33.00, 'কেউ'
      from master.stock_movement_type mt
     where mt.organization_no is null and mt.stock_movement_type_code = 'PURCHASE';
    raise exception 'ব্যর্থ: ভুল পণ্যের লট গ্রহণ করা হলো!';
  exception when check_violation then
    null;
  end;

  -- ═════════════════ ১০. পুনঃক্রয়ের সতর্কতা ═════════════════
  insert into inv.item_setting (organization_no, item_no, reorder_level, reorder_qty)
  values (v_org, v_maize, 1500, 1000);

  select count(*) into v_n from inv.v_reorder_alert
   where organization_no = v_org and item_no = v_maize;
  if v_n <> 1 then
    raise exception 'পুনঃক্রয়ের সতর্কতা আসেনি (স্টক ১২০০, সীমা ১৫০০)';
  end if;

  -- ═════════════════ ১১. অনুমোদিত ফরমুলা তালাবদ্ধ ═════════════════
  update feed.ration_formula
     set status = 'approved', approved_on = current_date, approved_by = v_user
   where ration_formula_no = v_f1;

  begin
    perform feed.optimize_formula(v_f1, true);
    raise exception 'ব্যর্থ: অনুমোদিত ফরমুলা অপটিমাইজ করে বদলানো গেল!';
  exception when restrict_violation then
    null;
  end;

  -- অনুমোদিত ফরমুলাতেও শুধু হিসাব দেখা বৈধ
  select o.status into v_status from feed.optimize_formula(v_f1, false) o limit 1;
  if v_status <> 'optimal' then
    raise exception 'p_apply=false দিয়েও অনুমোদিত ফরমুলা হিসাব করা গেল না: %', v_status;
  end if;

  -- ═════════════════ ১২. ভুল পণ্য ফরমুলায় ═════════════════
  begin
    insert into feed.ration_formula_line (organization_no, ration_formula_no, item_no)
    select v_org, v_f2, item_no from master.item
     where organization_no is null and item_code = 'AB_DOXY';
    raise exception 'ব্যর্থ: ঔষধ ফরমুলার উপাদান হিসেবে ঢুকল!';
  exception when check_violation then
    null;
  end;

  begin
    insert into feed.ration_formula_line (organization_no, ration_formula_no, item_no)
    values (v_org, v_f2, v_rf);
    raise exception 'ব্যর্থ: সমাপ্ত ফিড ফরমুলার উপাদান হিসেবে ঢুকল!';
  exception when check_violation then
    null;
  end;

  -- ═════════════════ ১৩. ইউরিয়া: পোল্ট্রিতে নিষিদ্ধ, গরুতে বৈধ ═════════════════
  begin
    insert into feed.ration_formula_line (organization_no, ration_formula_no, item_no)
    select v_org, v_f2, item_no from master.item
     where organization_no is null and item_code = 'UREA_FEED';
    raise exception 'ব্যর্থ: ইউরিয়া ব্রয়লারের ফরমুলায় ঢুকল — হিসাব ২৮০%% আমিষ দেখাত!';
  exception when check_violation then
    null;
  end;

  -- একই উপাদান গরুর ফরমুলায় বৈধ হওয়া উচিত
  declare
    v_f3 uuid;
  begin
    insert into feed.ration_formula
      (organization_no, formula_code, name_bn, species_no, production_purpose_no,
       ration_requirement_set_no, batch_size_kg, priced_on)
    select v_org, 'F-CT-DAIRY-1', 'গরুর দানাদার — নিজের মিক্স',
           s.species_no, p.production_purpose_no,
           (select ration_requirement_set_no from master.ration_requirement_set
             where organization_no is null and requirement_set_code = 'CT_DAIRY'),
           100, current_date
      from master.species s, master.production_purpose p
     where s.organization_no is null and s.species_code = 'CATTLE'
       and p.organization_no is null and p.production_purpose_code = 'DAIRY'
    returning ration_formula_no into v_f3;

    insert into feed.ration_formula_line (organization_no, ration_formula_no, item_no, max_pct)
    select v_org, v_f3, item_no, 1.00 from master.item
     where organization_no is null and item_code = 'UREA_FEED';

    select count(*) into v_n from feed.ration_formula_line
     where ration_formula_no = v_f3 and ss_deleted_flag = false;
    if v_n <> 1 then
      raise exception 'গরুর ফরমুলায় ইউরিয়া ঢোকানো গেল না';
    end if;
  end;

  raise notice 'ফিড ও গুদামের পরীক্ষা সফল — ১৩টি বিভাগের সব যাচাই পাস করেছে।';
  raise notice 'অপটিমাইজ করা ব্রয়লার গ্রোয়ার রেশনের খরচ: প্রতি কেজি % টাকা',
    round(v_cost1 / 100, 2);
end
$feed$;

-- ---------------------------------------------------------------------
-- ফলাফল দেখা
-- ---------------------------------------------------------------------
\echo ''
\echo '── অপটিমাইজ করা ব্রয়লার গ্রোয়ার রেশন (১০০ কেজি) ──'
select it.name_bn as "উপাদান",
       l.qty_kg   as "কেজি",
       round(l.qty_kg, 2) as "শতকরা",
       l.unit_cost_snapshot as "দর",
       round(l.qty_kg * l.unit_cost_snapshot, 2) as "টাকা"
  from feed.ration_formula_line l
  join master.item it on it.item_no = l.item_no
  join feed.ration_formula f on f.ration_formula_no = l.ration_formula_no
 where f.formula_code = 'F-BR-GROW-1' and l.qty_kg > 0.0001
 order by l.qty_kg desc;

select round(total_cost,2) as "মোট টাকা", round(cost_per_kg,2) as "প্রতি কেজি",
       violation_count as "চাহিদা ভঙ্গ"
  from feed.v_formula_summary where formula_code = 'F-BR-GROW-1';

\echo ''
\echo '── পুষ্টিমান বনাম চাহিদা ──'
select e.nutrient_name_bn as "পুষ্টি", e.value_uom_code as "একক",
       e.achieved_per_kg as "অর্জিত",
       coalesce(e.min_per_kg::text,'—') as "নিম্নসীমা",
       coalesce(e.max_per_kg::text,'—') as "উচ্চসীমা",
       e.verdict as "ফলাফল"
  from feed.ration_formula f,
       feed.evaluate_formula(f.ration_formula_no) e
 where f.formula_code = 'F-BR-GROW-1'
   and (e.min_per_kg is not null or e.max_per_kg is not null);
