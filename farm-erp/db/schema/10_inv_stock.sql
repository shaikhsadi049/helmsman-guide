-- =====================================================================
-- 10_inv_stock.sql — গুদাম, লট ও স্টকের খাতা
--
-- prod.unit_movement এর মতোই নীতি: স্টকের একমাত্র সত্য অ্যাপেন্ড-অনলি
-- খাতা। কোথাও "বর্তমান স্টক" নামের কলাম নেই।
--
-- খরচের পদ্ধতি: চলমান ভারিত গড় (perpetual weighted average)।
-- বেরোনোর সময়ের গড় খরচ ট্রিগার হিসাব করে সারিতেই বসিয়ে দেয়, এবং
-- টেবিল অ্যাপেন্ড-অনলি হওয়ায় সেটা আর কখনো বদলায় না। ফলে ছয় মাস পরেও
-- "ওই ব্যাচে ফিডের খরচ কত ছিল" প্রশ্নের একটাই উত্তর থাকে।
--
-- খরচের পাত্র (cost pool) = (গুদাম, পণ্য)। লট শুধু মেয়াদ ও ট্রেসেবিলিটির
-- জন্য, খরচের জন্য নয় — একই ফিড দুই লটে এলে দাম আলাদা করে রাখার চেয়ে
-- গড় করাই খামারের বাস্তবতার কাছাকাছি, এবং বোঝা সহজ।
-- =====================================================================

-- ---------------------------------------------------------------------
-- স্টক চলাচলের ধরন
-- ---------------------------------------------------------------------
create table master.stock_movement_type (
  stock_movement_type_no   uuid primary key default core.uuidv7(),
  organization_no          uuid,
  stock_movement_type_code citext not null,
  name_bn                  text not null,
  name_en                  text not null,
  direction                smallint not null check (direction in (-1, 1)),

  is_purchase              boolean not null default false,
  is_issue                 boolean not null default false,  -- ব্যাচ/ঘরে দেওয়া
  is_production            boolean not null default false,  -- নিজে ফিড মিক্স
  is_transfer              boolean not null default false,
  is_sale                  boolean not null default false,
  is_wastage               boolean not null default false,
  is_adjustment            boolean not null default false,
  is_own_harvest           boolean not null default false,  -- নিজের ভুট্টা/খড়

  requires_production_unit boolean not null default false,
  requires_counterparty    boolean not null default false,
  requires_unit_cost       boolean not null default false,
  requires_target_store    boolean not null default false,
  sort_order               smallint not null default 100,
  like core.ss_row_template including all,

  constraint ck_smt_coherent check (
      (case when is_purchase   then 1 else 0 end
     + case when is_issue      then 1 else 0 end
     + case when is_production then 1 else 0 end
     + case when is_transfer   then 1 else 0 end
     + case when is_sale       then 1 else 0 end
     + case when is_wastage    then 1 else 0 end
     + case when is_adjustment then 1 else 0 end
     + case when is_own_harvest then 1 else 0 end) <= 1
  ),
  constraint ck_smt_direction check (
    not ((is_issue or is_sale or is_wastage) and direction = 1)
    and not ((is_purchase or is_own_harvest) and direction = -1)
  )
);
create unique index ux_smt_code on master.stock_movement_type
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), stock_movement_type_code)
  where ss_deleted_flag = false;
select core.ss_apply('master.stock_movement_type', 'shared');

-- ---------------------------------------------------------------------
-- গুদাম
--
-- ঘরের সাথে ঐচ্ছিক সংযোগ — গুদাম আলাদা ঘর হতে পারে, আবার শেডের এক
-- কোণাও হতে পারে। ছোট খামারে সাধারণত একটাই "প্রধান গুদাম"।
-- ---------------------------------------------------------------------
create table inv.store (
  store_no        uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  farm_no         uuid not null references core.farm(farm_no),
  house_no        uuid references core.house(house_no),
  store_code      citext not null,
  store_name      text not null,
  store_type      text not null default 'general'
      check (store_type in ('general','feed','medicine','equipment','fuel','produce')),
  is_default      boolean not null default false,
  like core.ss_row_template including all
);
create unique index ux_store_code on inv.store (organization_no, store_code)
  where ss_deleted_flag = false;
create unique index ux_store_default on inv.store (organization_no, farm_no)
  where is_default and ss_deleted_flag = false;
select core.ss_apply('inv.store', 'tenant');

-- ---------------------------------------------------------------------
-- লট / ব্যাচ — মেয়াদ ও ট্রেসেবিলিটি
--
-- টিকার ঠান্ডা শৃঙ্খল ভাঙলে বা ফিডে অ্যাফ্লাটক্সিন পাওয়া গেলে "কোন লট
-- কোন ব্যাচে গিয়েছিল" প্রশ্নের উত্তর এখান থেকেই আসে।
-- ---------------------------------------------------------------------
create table inv.stock_lot (
  stock_lot_no     uuid primary key default core.uuidv7(),
  organization_no  uuid not null references core.organization(organization_no),
  item_no          uuid not null references master.item(item_no),
  lot_code         citext not null,
  manufacture_date date,
  expiry_date      date,
  supplier_name    text,
  received_on      date,
  remarks_bn       text,
  like core.ss_row_template including all,
  constraint ck_lot_dates check (expiry_date is null or manufacture_date is null
                                 or expiry_date >= manufacture_date)
);
create unique index ux_stock_lot on inv.stock_lot (organization_no, item_no, lot_code)
  where ss_deleted_flag = false;
create index ix_stock_lot_expiry on inv.stock_lot (organization_no, expiry_date)
  where expiry_date is not null and ss_deleted_flag = false;
select core.ss_apply('inv.stock_lot', 'tenant');

-- ---------------------------------------------------------------------
-- পণ্যের টেন্যান্ট সেটিং — পুনঃক্রয়ের সীমা
--
-- master.item গ্লোবাল, কিন্তু "কত হলে আবার কিনব" প্রতিটা খামারে ভিন্ন।
-- তাই আলাদা টেবিল, গ্লোবাল পণ্যকে ওভাররাইড না করে।
-- ---------------------------------------------------------------------
create table inv.item_setting (
  item_setting_no uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  item_no         uuid not null references master.item(item_no),
  reorder_level   numeric(16,4) check (reorder_level >= 0),
  reorder_qty     numeric(16,4) check (reorder_qty > 0),
  max_level       numeric(16,4) check (max_level > 0),
  preferred_supplier text,
  like core.ss_row_template including all,
  constraint ck_item_setting_levels check (max_level is null or reorder_level is null
                                           or max_level >= reorder_level)
);
create unique index ux_item_setting on inv.item_setting (organization_no, item_no)
  where ss_deleted_flag = false;
select core.ss_apply('inv.item_setting', 'tenant');

-- ---------------------------------------------------------------------
-- দামের তালিকা — রেশন হিসাবের জন্য
--
-- লিস্ট-কস্ট রেশন বের করতে উপাদানের দাম লাগে। দাম আসে তিন জায়গা থেকে,
-- এই ক্রমে: (১) এই তালিকা, (২) সর্বশেষ ক্রয়ের দাম, (৩) পণ্যের আনুমানিক দর।
-- ---------------------------------------------------------------------
create table inv.item_price (
  item_price_no   uuid primary key default core.uuidv7(),
  organization_no uuid not null references core.organization(organization_no),
  item_no         uuid not null references master.item(item_no),
  effective_from  date not null,
  unit_cost       numeric(16,4) not null check (unit_cost >= 0),
  source_note_bn  text,
  like core.ss_row_template including all
);
create unique index ux_item_price on inv.item_price (organization_no, item_no, effective_from)
  where ss_deleted_flag = false;
select core.ss_apply('inv.item_price', 'tenant');

-- ---------------------------------------------------------------------
-- স্টকের খাতা (অ্যাপেন্ড-অনলি)
-- ---------------------------------------------------------------------
create table inv.stock_movement (
  stock_movement_no      uuid primary key default core.uuidv7(),
  organization_no        uuid not null references core.organization(organization_no),
  farm_no                uuid not null references core.farm(farm_no),
  store_no               uuid not null references inv.store(store_no),
  item_no                uuid not null references master.item(item_no),
  stock_lot_no           uuid references inv.stock_lot(stock_lot_no),
  stock_movement_type_no uuid not null references master.stock_movement_type(stock_movement_type_no),
  movement_date          date not null,

  qty                    numeric(16,4) not null check (qty > 0),  -- পণ্যের মূল এককে
  unit_cost              numeric(16,6) check (unit_cost >= 0),
  total_value            numeric(18,4) check (total_value >= 0),

  -- ব্যাচে দেওয়া ফিড/ঔষধ। এই একটা কলামই প্রতি-ব্যাচ খরচের হিসাব সম্ভব করে।
  production_unit_no     uuid references prod.production_unit(production_unit_no),
  to_store_no            uuid references inv.store(store_no),
  -- নিজে ফিড মিক্স করলে: কোন ফরমুলা অনুসারে (feed স্কিমা পরে সংযুক্ত হয়)
  ration_formula_no      uuid,

  counterparty_name      text,
  reference_doc_no       text,
  reversal_of_no         uuid references inv.stock_movement(stock_movement_no),
  remarks_bn             text,
  like core.ss_row_template including all,

  constraint ck_sm_transfer_target check (to_store_no is null or to_store_no <> store_no)
);
create index ix_sm_store_item_date on inv.stock_movement (store_no, item_no, movement_date);
create index ix_sm_org_date        on inv.stock_movement (organization_no, movement_date);
create index ix_sm_unit            on inv.stock_movement (production_unit_no)
  where production_unit_no is not null;
create index ix_sm_lot             on inv.stock_movement (stock_lot_no) where stock_lot_no is not null;

select core.ss_apply('inv.stock_movement', 'tenant', p_append_only => true);

-- ---------------------------------------------------------------------
-- চলমান ভারিত গড় খরচ — একটা নির্দিষ্ট তারিখের আগ পর্যন্ত
-- ---------------------------------------------------------------------
create or replace function inv.avg_cost_before(
  p_org uuid, p_store uuid, p_item uuid, p_date date
) returns numeric
language sql stable as $$
  select case when sum(mt.direction * m.qty) > 0
              then sum(mt.direction * coalesce(m.total_value, 0))
                   / sum(mt.direction * m.qty)
         end
    from inv.stock_movement m
    join master.stock_movement_type mt
      on mt.stock_movement_type_no = m.stock_movement_type_no
   where m.organization_no = p_org
     and m.store_no  = p_store
     and m.item_no   = p_item
     and m.movement_date <= p_date
     and m.ss_deleted_flag = false;
$$;

-- দাম খোঁজার অনুক্রম: দামের তালিকা → সর্বশেষ ক্রয় → আনুমানিক দর
create or replace function inv.effective_price(
  p_org uuid, p_item uuid, p_date date default current_date
) returns numeric
language sql stable as $$
  select coalesce(
    (select p.unit_cost from inv.item_price p
      where p.organization_no = p_org and p.item_no = p_item
        and p.effective_from <= p_date and p.ss_deleted_flag = false
      order by p.effective_from desc limit 1),
    (select m.unit_cost from inv.stock_movement m
       join master.stock_movement_type mt on mt.stock_movement_type_no = m.stock_movement_type_no
      where m.organization_no = p_org and m.item_no = p_item
        and mt.is_purchase and m.unit_cost is not null and m.ss_deleted_flag = false
        and m.movement_date <= p_date
      order by m.movement_date desc, m.ss_sync_seq desc limit 1),
    (select i.indicative_rate from master.item i where i.item_no = p_item)
  );
$$;

-- দাম কোথা থেকে এলো — টাকার সিদ্ধান্তে এটা জানা জরুরি।
-- 'price_list' ও 'last_purchase' নির্ভরযোগ্য; 'indicative' মানে সিডে
-- বসানো অনুমান, যা বাজারদর নয় এবং দ্রুত পুরোনো হয়।
create or replace function inv.price_source(
  p_org uuid, p_item uuid, p_date date default current_date
) returns text
language sql stable as $$
  select case
    when exists (select 1 from inv.item_price p
                  where p.organization_no = p_org and p.item_no = p_item
                    and p.effective_from <= p_date and p.ss_deleted_flag = false)
      then 'price_list'
    when exists (select 1 from inv.stock_movement m
                   join master.stock_movement_type mt
                     on mt.stock_movement_type_no = m.stock_movement_type_no
                  where m.organization_no = p_org and m.item_no = p_item
                    and mt.is_purchase and m.unit_cost is not null
                    and m.movement_date <= p_date and m.ss_deleted_flag = false)
      then 'last_purchase'
    when (select i.indicative_rate from master.item i where i.item_no = p_item) is not null
      then 'indicative'
    else 'none'
  end;
$$;

-- ---------------------------------------------------------------------
-- খাতার রক্ষী
-- ---------------------------------------------------------------------
create or replace function inv.stock_movement_guard()
returns trigger language plpgsql as $$
declare
  v_mt      record;
  v_item    record;
  v_store   record;
  v_min     numeric;
  v_avg     numeric;
begin
  select * into v_mt from master.stock_movement_type
   where stock_movement_type_no = new.stock_movement_type_no;
  if not found then
    raise exception 'স্টক চলাচলের ধরন পাওয়া যায়নি' using errcode = 'foreign_key_violation';
  end if;

  select * into v_item  from master.item  where item_no  = new.item_no;
  select * into v_store from inv.store    where store_no = new.store_no;

  if v_store.organization_no is distinct from new.organization_no
     or v_store.farm_no is distinct from new.farm_no then
    raise exception 'গুদামটি এই প্রতিষ্ঠান/খামারের নয়' using errcode = 'check_violation';
  end if;

  if not v_item.is_stock_tracked then
    raise exception '% পণ্যের স্টক রাখা হয় না', v_item.name_bn using errcode = 'check_violation';
  end if;

  -- লট বাধ্যতামূলক কি না
  if v_item.is_lot_tracked and new.stock_lot_no is null then
    raise exception '% পণ্যে লট দিতে হবে (মেয়াদ ও ট্রেসেবিলিটির জন্য)', v_item.name_bn
      using errcode = 'not_null_violation';
  end if;
  if new.stock_lot_no is not null then
    if not exists (select 1 from inv.stock_lot l
                    where l.stock_lot_no = new.stock_lot_no and l.item_no = new.item_no) then
      raise exception 'লটটি এই পণ্যের নয়' using errcode = 'check_violation';
    end if;
  end if;

  -- ধরন অনুসারে বাধ্যতামূলক তথ্য
  if v_mt.requires_production_unit and new.production_unit_no is null then
    raise exception '% এর জন্য উৎপাদন ইউনিট দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;
  if v_mt.requires_counterparty and coalesce(new.counterparty_name,'') = '' then
    raise exception '% এর জন্য পক্ষের নাম দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;
  if v_mt.requires_target_store and new.to_store_no is null then
    raise exception '% এর জন্য গন্তব্য গুদাম দিতে হবে', v_mt.name_bn
      using errcode = 'not_null_violation';
  end if;

  if new.production_unit_no is not null then
    if not exists (select 1 from prod.production_unit pu
                    where pu.production_unit_no = new.production_unit_no
                      and pu.organization_no = new.organization_no) then
      raise exception 'উৎপাদন ইউনিটটি এই প্রতিষ্ঠানের নয়' using errcode = 'check_violation';
    end if;
  end if;

  -- ── খরচ নির্ধারণ ──
  if v_mt.direction = 1 then
    -- ঢোকার সময় দাম জানা থাকতে হয় (ক্রয়, নিজের উৎপাদন, নিজের ফসল)
    if new.unit_cost is null and v_mt.requires_unit_cost then
      raise exception '% এর জন্য একক দর দিতে হবে', v_mt.name_bn
        using errcode = 'not_null_violation';
    end if;
    -- সমন্বয়ে (গণনা বেশি পাওয়া) দাম না দিলে চলতি গড় ধরা হয়
    if new.unit_cost is null then
      new.unit_cost := coalesce(
        inv.avg_cost_before(new.organization_no, new.store_no, new.item_no, new.movement_date),
        inv.effective_price(new.organization_no, new.item_no, new.movement_date),
        0);
    end if;
  else
    -- বেরোনোর সময় দাম হিসাব করা হয়, দেওয়া হয় না — এভাবেই ভারিত গড় ঠিক থাকে
    v_avg := inv.avg_cost_before(new.organization_no, new.store_no, new.item_no, new.movement_date);
    if v_avg is null then
      v_avg := coalesce(inv.effective_price(new.organization_no, new.item_no, new.movement_date), 0);
    end if;
    new.unit_cost := v_avg;
  end if;

  new.total_value := round(new.qty * new.unit_cost, 4);

  -- ── ঋণাত্মক স্টক প্রতিরোধ ──
  -- প্রতিটা তারিখের চলমান যোগফল পরীক্ষা করা হয়, তাই ব্যাকডেটেড
  -- এন্ট্রিও ধরা পড়ে। লট থাকলে লট ধরে, না থাকলে পণ্য ধরে।
  with all_mv as (
    select m.movement_date, mt2.direction * m.qty as delta
      from inv.stock_movement m
      join master.stock_movement_type mt2 on mt2.stock_movement_type_no = m.stock_movement_type_no
     where m.organization_no = new.organization_no
       and m.store_no = new.store_no
       and m.item_no  = new.item_no
       and (new.stock_lot_no is null or m.stock_lot_no = new.stock_lot_no)
       and m.ss_deleted_flag = false
    union all
    select new.movement_date, v_mt.direction * new.qty
  ),
  daily as (select movement_date, sum(delta) as d from all_mv group by movement_date)
  select min(running) into v_min
    from (select sum(d) over (order by movement_date) as running from daily) s;

  if coalesce(v_min, 0) < -0.0001 then
    raise exception
      'এই চলাচলে % এর স্টক ঋণাত্মক হয়ে যায় (সর্বনিম্ন %)। গুদামে যা নেই তা বের করা যাবে না।',
      v_item.name_bn, round(v_min, 4)
      using errcode = 'check_violation';
  end if;

  return new;
end $$;

create trigger sm_guard_bi before insert on inv.stock_movement
  for each row execute function inv.stock_movement_guard();

-- ---------------------------------------------------------------------
-- ভিউ
-- ---------------------------------------------------------------------

-- গুদাম ও পণ্য অনুসারে স্টক ও মূল্য
create view inv.v_stock_balance as
select m.organization_no,
       m.farm_no,
       m.store_no,
       s.store_name,
       m.item_no,
       i.item_code,
       i.name_bn as item_name_bn,
       i.item_type,
       u.uom_code,
       sum(mt.direction * m.qty)::numeric(16,4)                       as qty_on_hand,
       sum(mt.direction * coalesce(m.total_value,0))::numeric(18,4)   as stock_value,
       case when sum(mt.direction * m.qty) > 0
            then round(sum(mt.direction * coalesce(m.total_value,0))
                       / sum(mt.direction * m.qty), 4)
       end                                                            as avg_unit_cost,
       max(m.movement_date)                                           as last_movement_date
  from inv.stock_movement m
  join master.stock_movement_type mt on mt.stock_movement_type_no = m.stock_movement_type_no
  join master.item i on i.item_no = m.item_no
  join master.uom  u on u.uom_no  = i.base_uom_no
  join inv.store   s on s.store_no = m.store_no
 where m.ss_deleted_flag = false
 group by m.organization_no, m.farm_no, m.store_no, s.store_name,
          m.item_no, i.item_code, i.name_bn, i.item_type, u.uom_code;

-- লট অনুসারে স্টক (মেয়াদের হিসাবের জন্য)
create view inv.v_stock_lot_balance as
select m.organization_no,
       m.store_no,
       m.item_no,
       i.name_bn      as item_name_bn,
       m.stock_lot_no,
       l.lot_code,
       l.expiry_date,
       (l.expiry_date - current_date)                as days_to_expiry,
       sum(mt.direction * m.qty)::numeric(16,4)      as qty_on_hand
  from inv.stock_movement m
  join master.stock_movement_type mt on mt.stock_movement_type_no = m.stock_movement_type_no
  join master.item i on i.item_no = m.item_no
  join inv.stock_lot l on l.stock_lot_no = m.stock_lot_no
 where m.stock_lot_no is not null and m.ss_deleted_flag = false
 group by m.organization_no, m.store_no, m.item_no, i.name_bn,
          m.stock_lot_no, l.lot_code, l.expiry_date;

-- পুনঃক্রয়ের সতর্কতা
create view inv.v_reorder_alert as
select b.organization_no, b.farm_no, b.store_no, b.item_no,
       b.item_name_bn, b.uom_code,
       b.qty_on_hand,
       st.reorder_level,
       st.reorder_qty,
       (st.reorder_level - b.qty_on_hand)::numeric(16,4) as shortfall
  from inv.v_stock_balance b
  join inv.item_setting st on st.organization_no = b.organization_no
                          and st.item_no = b.item_no
                          and st.ss_deleted_flag = false
 where st.reorder_level is not null
   and b.qty_on_hand <= st.reorder_level;

-- ইউনিট অনুসারে খরচ — এটাই টাকার হিসাবের ভিত্তি
create view inv.v_unit_input_cost as
select m.organization_no,
       m.production_unit_no,
       pu.unit_code,
       i.item_type,
       sum(case when i.is_feed then m.qty else 0 end)::numeric(16,4)                 as feed_qty_kg,
       sum(case when i.is_feed then coalesce(m.total_value,0) else 0 end)::numeric(18,4) as feed_cost,
       sum(case when i.item_type in ('medicine','vaccine','supplement')
                then coalesce(m.total_value,0) else 0 end)::numeric(18,4)            as health_cost,
       sum(case when i.item_type in ('litter','consumable','fuel','utility')
                then coalesce(m.total_value,0) else 0 end)::numeric(18,4)            as other_cost,
       sum(coalesce(m.total_value,0))::numeric(18,4)                                 as total_cost
  from inv.stock_movement m
  join master.stock_movement_type mt on mt.stock_movement_type_no = m.stock_movement_type_no
  join master.item i on i.item_no = m.item_no
  join prod.production_unit pu on pu.production_unit_no = m.production_unit_no
 where m.production_unit_no is not null
   and mt.is_issue
   and m.ss_deleted_flag = false
 group by m.organization_no, m.production_unit_no, pu.unit_code, i.item_type;

grant select on inv.v_stock_balance, inv.v_stock_lot_balance,
                inv.v_reorder_alert, inv.v_unit_input_cost
  to farmerp_app, farmerp_readonly;
