-- =====================================================================
-- 12_feed_ration.sql — রেশন ফরমুলেশন ও লিস্ট-কস্ট অপটিমাইজেশন
--
-- খামারের খরচের ৬৫–৭০% খাদ্য। তাই এই মডিউলটাই খামারিকে সবচেয়ে দ্রুত
-- টাকা ফেরত দেয় — এক কেজি ফিডে ২ টাকা বাঁচলে ১০০০ বার্ডের ব্যাচে
-- ৬–৭ হাজার টাকা।
--
-- দুইটা আলাদা কাজ, গুলিয়ে ফেলা চলবে না:
--
--   ১. মূল্যায়ন (evaluate) — খামারি নিজে যে মিশ্রণ বানিয়েছে, তাতে পুষ্টি
--      চাহিদা মিটছে কি না আর কত খরচ পড়ছে। এটাই বেশি ব্যবহৃত হবে, কারণ
--      খামারি হাতে হিসাব করেই অভ্যস্ত — সে শুধু জানতে চায় ঠিক আছে কি না।
--
--   ২. অপটিমাইজ (optimize) — একই চাহিদা সবচেয়ে কম খরচে মেটানোর মিশ্রণ
--      বের করা। LP সমস্যা, core.lp_solve() দিয়ে সমাধান।
--
-- গুরুত্বপূর্ণ: অপটিমাইজার শুধু ফরমুলায় *ইতিমধ্যে যোগ করা* উপাদানগুলো
-- নিয়েই কাজ করে। কারণ বগুড়ার খামারিকে "ফিশ মিল ব্যবহার করুন" বলে লাভ
-- নেই যদি এলাকায় ফিশ মিল না পাওয়া যায়। কী পাওয়া যায় সেটা খামারি ঠিক
-- করে, কত দেবে সেটা গণিত ঠিক করে।
-- =====================================================================

-- ---------------------------------------------------------------------
-- পুষ্টি চাহিদার সেট (গ্লোবাল টেমপ্লেট + খামারির নিজের)
--
-- মান প্রতি কেজি খাদ্যে, as-fed ভিত্তিতে — item_nutrient এর মতোই।
-- ---------------------------------------------------------------------
create table master.ration_requirement_set (
  ration_requirement_set_no uuid primary key default core.uuidv7(),
  organization_no           uuid,
  requirement_set_code      citext not null,
  name_bn                   text not null,
  name_en                   text not null,
  species_no                uuid not null references master.species(species_no),
  production_purpose_no     uuid not null references master.production_purpose(production_purpose_no),
  phase_code                citext,          -- lifecycle_phase.phase_code এর সাথে মেলে
  from_day                  integer check (from_day >= 0),
  to_day                    integer,
  source_note_bn            text,
  sort_order                smallint not null default 100,
  like core.ss_row_template including all,
  constraint ck_rrs_range check (to_day is null or from_day is null or to_day >= from_day)
);
create unique index ux_rrs_code on master.ration_requirement_set
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), requirement_set_code)
  where ss_deleted_flag = false;
create index ix_rrs_species on master.ration_requirement_set (species_no, production_purpose_no);
select core.ss_apply('master.ration_requirement_set', 'shared');

create table master.ration_requirement_line (
  ration_requirement_line_no uuid primary key default core.uuidv7(),
  organization_no            uuid,
  ration_requirement_set_no  uuid not null
      references master.ration_requirement_set(ration_requirement_set_no) on delete cascade,
  nutrient_no                uuid not null references master.nutrient(nutrient_no),
  min_per_kg                 numeric(16,6) check (min_per_kg >= 0),
  max_per_kg                 numeric(16,6) check (max_per_kg >= 0),
  like core.ss_row_template including all,
  constraint ck_rrl_bounds check (
    (min_per_kg is not null or max_per_kg is not null)
    and (min_per_kg is null or max_per_kg is null or max_per_kg >= min_per_kg)
  )
);
create unique index ux_rrl on master.ration_requirement_line
  (ration_requirement_set_no, nutrient_no) where ss_deleted_flag = false;
select core.ss_apply('master.ration_requirement_line', 'shared');

-- ---------------------------------------------------------------------
-- ফরমুলা
-- ---------------------------------------------------------------------
create table feed.ration_formula (
  ration_formula_no         uuid primary key default core.uuidv7(),
  organization_no           uuid not null references core.organization(organization_no),
  formula_code              citext not null,
  name_bn                   text not null,
  species_no                uuid not null references master.species(species_no),
  production_purpose_no     uuid not null references master.production_purpose(production_purpose_no),
  ration_requirement_set_no uuid references master.ration_requirement_set(ration_requirement_set_no),
  batch_size_kg             numeric(14,3) not null default 100 check (batch_size_kg > 0),
  status                    text not null default 'draft'
      check (status in ('draft','approved','archived')),
  priced_on                 date not null default current_date,  -- কোন তারিখের দামে হিসাব
  approved_by               uuid,
  approved_on               date,
  remarks_bn                text,
  like core.ss_row_template including all,
  constraint ck_formula_approved check (status <> 'approved' or approved_on is not null)
);
create unique index ux_formula_code on feed.ration_formula (organization_no, formula_code)
  where ss_deleted_flag = false;
select core.ss_apply('feed.ration_formula', 'tenant');

-- আটকানো: অনুমোদিত ফরমুলা আর বদলানো যাবে না (কপি করে নতুন সংস্করণ বানাতে হবে),
-- নইলে "ওই ব্যাচে কোন ফরমুলা ব্যবহার হয়েছিল" প্রশ্নের উত্তর হারিয়ে যায়
create or replace function feed.formula_lock_guard()
returns trigger language plpgsql as $$
begin
  if old.status = 'approved' and new.status = 'approved'
     and (new.batch_size_kg, new.ration_requirement_set_no, new.priced_on)
         is distinct from (old.batch_size_kg, old.ration_requirement_set_no, old.priced_on) then
    raise exception 'অনুমোদিত ফরমুলা বদলানো যায় না। কপি করে নতুন সংস্করণ বানান।'
      using errcode = 'restrict_violation';
  end if;
  return new;
end $$;

create trigger formula_lock_bu before update on feed.ration_formula
  for each row execute function feed.formula_lock_guard();

-- ---------------------------------------------------------------------
-- ফরমুলার সারি
--
-- একই সারিতে দুই ভূমিকা:
--   min_pct / max_pct = অপটিমাইজারের জন্য *ইনপুট* (অনুমোদিত সীমা)
--   qty_kg            = *ফলাফল* (কত দেওয়া হবে)
-- হাতে বানানো ফরমুলায় min/max ফাঁকা থাকে, শুধু qty_kg থাকে।
-- ---------------------------------------------------------------------
create table feed.ration_formula_line (
  ration_formula_line_no uuid primary key default core.uuidv7(),
  organization_no        uuid not null references core.organization(organization_no),
  ration_formula_no      uuid not null
      references feed.ration_formula(ration_formula_no) on delete cascade,
  item_no                uuid not null references master.item(item_no),
  qty_kg                 numeric(16,4) not null default 0 check (qty_kg >= 0),
  min_pct                numeric(8,4) check (min_pct  >= 0 and min_pct  <= 100),
  max_pct                numeric(8,4) check (max_pct  >= 0 and max_pct  <= 100),
  is_fixed               boolean not null default false,  -- true = অপটিমাইজার ছোঁবে না
  unit_cost_snapshot     numeric(16,6) check (unit_cost_snapshot >= 0),
  sort_order             smallint not null default 100,
  like core.ss_row_template including all,
  constraint ck_rfl_pct check (min_pct is null or max_pct is null or max_pct >= min_pct)
);
create unique index ux_rfl on feed.ration_formula_line (ration_formula_no, item_no)
  where ss_deleted_flag = false;
select core.ss_apply('feed.ration_formula_line', 'tenant');

-- শুধু খাদ্যদ্রব্য ফরমুলায় থাকতে পারে
create or replace function feed.formula_line_guard()
returns trigger language plpgsql as $$
declare
  v_is_feed boolean; v_type text; v_org uuid;
  v_rum_only boolean; v_name text; v_class text;
begin
  select is_feed, item_type, is_ruminant_only, name_bn
    into v_is_feed, v_type, v_rum_only, v_name
    from master.item where item_no = new.item_no;
  if not v_is_feed then
    raise exception 'ফরমুলায় শুধু খাদ্যদ্রব্য দেওয়া যায় (পণ্যের ধরন: %)', v_type
      using errcode = 'check_violation';
  end if;
  -- সমাপ্ত ফিড আরেকটা ফরমুলার উপাদান হতে পারে না (বৃত্তাকার হিসাব এড়াতে)
  if v_type = 'feed_finished' then
    raise exception 'সমাপ্ত ফিড (%) ফরমুলার উপাদান হতে পারে না', v_type
      using errcode = 'check_violation';
  end if;
  select f.organization_no, s.animal_class
    into v_org, v_class
    from feed.ration_formula f
    join master.species s on s.species_no = f.species_no
   where f.ration_formula_no = new.ration_formula_no;

  if v_org is distinct from new.organization_no then
    raise exception 'ফরমুলাটি এই প্রতিষ্ঠানের নয়' using errcode = 'check_violation';
  end if;

  -- রুমিন্যান্ট-নির্দিষ্ট উপাদান অ-রুমিন্যান্টের ফরমুলায় ঢুকতে পারবে না।
  -- ইউরিয়াই প্রধান কারণ: পোল্ট্রিতে দিলে হিসাব আমিষ "পূরণ" দেখাবে
  -- অথচ পাখি মরবে — নীরব ভুলগুলোই সবচেয়ে বিপজ্জনক।
  if v_rum_only and v_class not in ('ruminant','pseudoruminant') then
    raise exception
      '% শুধু রুমিন্যান্টে (গরু/মহিষ/ছাগল/ভেড়া) দেওয়া যায়, % প্রজাতির ফরমুলায় নয়',
      v_name, v_class
      using errcode = 'check_violation';
  end if;

  return new;
end $$;

create trigger formula_line_guard_biu before insert or update on feed.ration_formula_line
  for each row execute function feed.formula_line_guard();

-- এখন feed স্কিমা আছে, তাই স্টক খাতার সংযোগটা জুড়ে দিই।
-- শর্তসহ, যাতে ফাইলটা বারবার চালানো যায় — মাইগ্রেশন স্ক্রিপ্ট
-- পুনরায় চালানোর যোগ্য না হলে ডেভেলপমেন্টে প্রতিবার পুরো ডাটাবেস
-- মুছে বানাতে হয়, আর তখন কেউ স্ক্রিপ্ট চালানো বন্ধ করে দেয়।
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fk_sm_ration_formula') then
    alter table inv.stock_movement
      add constraint fk_sm_ration_formula
      foreign key (ration_formula_no) references feed.ration_formula(ration_formula_no);
  end if;
end $$;

-- ---------------------------------------------------------------------
-- খরচ
-- ---------------------------------------------------------------------
create or replace function feed.formula_cost(p_formula_no uuid)
returns table (total_kg numeric, total_cost numeric, cost_per_kg numeric)
language sql stable as $$
  with f as (select * from feed.ration_formula where ration_formula_no = p_formula_no),
  l as (
    select l.qty_kg,
           coalesce(l.unit_cost_snapshot,
                    inv.effective_price(f.organization_no, l.item_no, f.priced_on),
                    0) as rate
      from feed.ration_formula_line l, f
     where l.ration_formula_no = p_formula_no and l.ss_deleted_flag = false
  )
  select round(sum(qty_kg), 4),
         round(sum(qty_kg * rate), 4),
         case when sum(qty_kg) > 0 then round(sum(qty_kg * rate) / sum(qty_kg), 4) end
    from l;
$$;

-- ---------------------------------------------------------------------
-- মূল্যায়ন — চাহিদার সাথে মিলিয়ে দেখা
-- ---------------------------------------------------------------------
create or replace function feed.evaluate_formula(p_formula_no uuid)
returns table (
  nutrient_code   citext,
  nutrient_name_bn text,
  value_uom_code  citext,
  achieved_per_kg numeric,
  min_per_kg      numeric,
  max_per_kg      numeric,
  verdict         text,
  ingredients_with_data integer,
  ingredients_total     integer
)
language sql stable as $$
  with f as (select * from feed.ration_formula where ration_formula_no = p_formula_no),
  lines as (
    select l.item_no, l.qty_kg
      from feed.ration_formula_line l
     where l.ration_formula_no = p_formula_no and l.ss_deleted_flag = false
  ),
  total as (select nullif(sum(qty_kg), 0) as kg from lines),
  -- চাহিদার সেটে থাকা পুষ্টি, আর সেই সাথে যেগুলোর মান আছে কিন্তু চাহিদায় নেই
  nutrients as (
    select rl.nutrient_no, rl.min_per_kg, rl.max_per_kg
      from master.ration_requirement_line rl, f
     where rl.ration_requirement_set_no = f.ration_requirement_set_no
       and rl.ss_deleted_flag = false
    union
    select distinct inut.nutrient_no, null::numeric, null::numeric
      from lines l
      join master.item_nutrient inut on inut.item_no = l.item_no and inut.ss_deleted_flag = false
     where not exists (
       select 1 from master.ration_requirement_line rl2, f
        where rl2.ration_requirement_set_no = f.ration_requirement_set_no
          and rl2.nutrient_no = inut.nutrient_no and rl2.ss_deleted_flag = false)
  ),
  calc as (
    select nu.nutrient_no, nu.min_per_kg, nu.max_per_kg,
           sum(l.qty_kg * coalesce(inut.value_per_kg, 0)) as total_amount,
           count(inut.item_nutrient_no)                   as with_data,
           count(l.item_no)                               as n_items
      from nutrients nu
      cross join lines l
      left join master.item_nutrient inut
             on inut.item_no = l.item_no
            and inut.nutrient_no = nu.nutrient_no
            and inut.ss_deleted_flag = false
     group by nu.nutrient_no, nu.min_per_kg, nu.max_per_kg
  )
  select n.nutrient_code,
         n.name_bn,
         n.value_uom_code,
         round((c.total_amount / t.kg)::numeric, 4)                as achieved_per_kg,
         c.min_per_kg,
         c.max_per_kg,
         case
           when c.min_per_kg is null and c.max_per_kg is null then 'তথ্য'
           when c.with_data = 0                               then 'তথ্য নেই'
           when c.min_per_kg is not null
                and c.total_amount / t.kg < c.min_per_kg * 0.9999 then 'কম'
           when c.max_per_kg is not null
                and c.total_amount / t.kg > c.max_per_kg * 1.0001 then 'বেশি'
           else 'ঠিক আছে'
         end                                                       as verdict,
         c.with_data::integer,
         c.n_items::integer
    from calc c
    join master.nutrient n on n.nutrient_no = c.nutrient_no
    cross join total t
   order by n.sort_order, n.nutrient_code;
$$;

comment on function feed.evaluate_formula(uuid) is
  'ফরমুলার অর্জিত পুষ্টিমান বনাম চাহিদা। verdict: ঠিক আছে | কম | বেশি | তথ্য নেই | তথ্য';

-- ---------------------------------------------------------------------
-- লিস্ট-কস্ট অপটিমাইজেশন
--
-- LP গঠন:
--   চলক      x_i = i-তম উপাদানের কেজি
--   উদ্দেশ্য   minimize Σ (দাম_i × x_i)
--   শর্ত      Σ x_i = ব্যাচের আকার
--            Σ (পুষ্টি_ij × x_i) >= নিম্নসীমা_j × ব্যাচের আকার
--            Σ (পুষ্টি_ij × x_i) <= উচ্চসীমা_j × ব্যাচের আকার
--            x_i >= min_pct_i/100 × ব্যাচ,   x_i <= max_pct_i/100 × ব্যাচ
--            স্থির (is_fixed) উপাদানে x_i = নির্ধারিত পরিমাণ
-- ---------------------------------------------------------------------
create or replace function feed.optimize_formula(
  p_formula_no uuid,
  p_apply      boolean default true   -- false = শুধু হিসাব দেখাও, সারি বদলাবে না
)
returns table (
  status        text,
  total_cost    numeric,
  cost_per_kg   numeric,
  item_code     citext,
  item_name_bn  text,
  qty_kg        numeric,
  pct           numeric
)
language plpgsql
as $$
declare
  v_f        record;
  v_items    uuid[];
  v_codes    citext[];
  v_names    text[];
  v_cost     float8[] := '{}';
  v_nut      uuid[];
  n          integer;
  v_a        float8[] := '{}';
  v_op       text[]   := '{}';
  v_b        float8[] := '{}';
  v_row      float8[];
  v_res      record;
  v_missing  text;
  v_batch    float8;
  i          integer;
  rec        record;
begin
  select * into v_f from feed.ration_formula
   where ration_formula_no = p_formula_no and ss_deleted_flag = false;
  if not found then
    raise exception 'ফরমুলা পাওয়া যায়নি' using errcode = 'no_data_found';
  end if;
  if v_f.status = 'approved' and p_apply then
    raise exception 'অনুমোদিত ফরমুলা অপটিমাইজ করে বদলানো যায় না। কপি করে নতুন সংস্করণ বানান।'
      using errcode = 'restrict_violation';
  end if;
  if v_f.ration_requirement_set_no is null then
    raise exception 'ফরমুলায় পুষ্টি চাহিদার সেট নির্ধারণ করা নেই — কী লক্ষ্য তা না জানলে অপটিমাইজ করা যায় না'
      using errcode = 'null_value_not_allowed';
  end if;
  v_batch := v_f.batch_size_kg::float8;

  -- ── উপাদান ও দাম ──
  select array_agg(l.item_no order by l.sort_order, it.item_code),
         array_agg(it.item_code order by l.sort_order, it.item_code),
         array_agg(it.name_bn  order by l.sort_order, it.item_code)
    into v_items, v_codes, v_names
    from feed.ration_formula_line l
    join master.item it on it.item_no = l.item_no
   where l.ration_formula_no = p_formula_no and l.ss_deleted_flag = false;

  n := coalesce(array_length(v_items, 1), 0);
  if n < 2 then
    raise exception 'অপটিমাইজ করতে অন্তত দুইটা উপাদান দরকার (এখন %টি)', n
      using errcode = 'invalid_parameter_value';
  end if;

  -- দাম না থাকলে থামি — দাম ছাড়া "সবচেয়ে কম খরচ" অর্থহীন
  select string_agg(v_names[idx], ', ')
    into v_missing
    from generate_subscripts(v_items, 1) as g(idx)
   where inv.effective_price(v_f.organization_no, v_items[idx], v_f.priced_on) is null;
  if v_missing is not null then
    raise exception 'এই উপাদানগুলোর দাম জানা নেই: %। inv.item_price এ দাম দিন।', v_missing
      using errcode = 'null_value_not_allowed';
  end if;

  for i in 1 .. n loop
    v_cost := v_cost ||
      inv.effective_price(v_f.organization_no, v_items[i], v_f.priced_on)::float8;
  end loop;

  -- সিডে বসানো অনুমানকৃত দাম ব্যবহার হলে নীরবে যেতে দেওয়া যায় না —
  -- ভুল দামে "সবচেয়ে কম খরচ" বের করা ভুল সিদ্ধান্তের সবচেয়ে সহজ পথ
  select string_agg(v_names[idx], ', ')
    into v_missing
    from generate_subscripts(v_items, 1) as g(idx)
   where inv.price_source(v_f.organization_no, v_items[idx], v_f.priced_on) = 'indicative';
  if v_missing is not null then
    raise notice
      'সতর্কতা: এই উপাদানগুলোর দাম সিডের অনুমান থেকে নেওয়া হয়েছে (বাজারদর নয়): %. '
      'নিজের ক্রয়মূল্য inv.item_price এ দিলে ফলাফল বিশ্বাসযোগ্য হবে।', v_missing;
  end if;

  -- ── শর্ত ১: মোট = ব্যাচের আকার ──
  v_a  := v_a || array_fill(1::float8, array[n]);
  v_op := v_op || '='::text;
  v_b  := v_b || v_batch;

  -- ── শর্ত ২: পুষ্টির সীমা ──
  for rec in
    select rl.nutrient_no, nu.nutrient_code, rl.min_per_kg, rl.max_per_kg
      from master.ration_requirement_line rl
      join master.nutrient nu on nu.nutrient_no = rl.nutrient_no
     where rl.ration_requirement_set_no = v_f.ration_requirement_set_no
       and rl.ss_deleted_flag = false
       and nu.is_constrainable
     order by nu.sort_order
  loop
    v_row := '{}';
    for i in 1 .. n loop
      v_row := v_row || coalesce(
        (select inut.value_per_kg::float8 from master.item_nutrient inut
          where inut.item_no = v_items[i] and inut.nutrient_no = rec.nutrient_no
            and inut.ss_deleted_flag = false), 0::float8);
    end loop;

    -- কোনো উপাদানেই এই পুষ্টির তথ্য না থাকলে শর্তটা অসম্ভব করে দেবে —
    -- নীরবে বাদ দেওয়ার চেয়ে স্পষ্ট বলা ভালো
    if rec.min_per_kg is not null and (select coalesce(sum(v), 0) from unnest(v_row) v) = 0 then
      raise exception
        '% পুষ্টির নিম্নসীমা দেওয়া আছে, কিন্তু কোনো উপাদানেই এর মান নেই। '
        'master.item_nutrient এ মান দিন, নয়তো চাহিদা থেকে এটা বাদ দিন।', rec.nutrient_code
        using errcode = 'no_data_found';
    end if;

    if rec.min_per_kg is not null then
      v_a  := v_a || v_row;
      v_op := v_op || '>='::text;
      v_b  := v_b || (rec.min_per_kg::float8 * v_batch);
    end if;
    if rec.max_per_kg is not null then
      v_a  := v_a || v_row;
      v_op := v_op || '<='::text;
      v_b  := v_b || (rec.max_per_kg::float8 * v_batch);
    end if;
  end loop;

  -- ── শর্ত ৩: উপাদানের সীমা ও স্থির পরিমাণ ──
  for rec in
    select l.item_no, l.min_pct, l.max_pct, l.is_fixed, l.qty_kg
      from feed.ration_formula_line l
     where l.ration_formula_no = p_formula_no and l.ss_deleted_flag = false
  loop
    i := array_position(v_items, rec.item_no);
    v_row := array_fill(0::float8, array[n]);
    v_row[i] := 1;

    if rec.is_fixed then
      v_a := v_a || v_row; v_op := v_op || '='::text;  v_b := v_b || rec.qty_kg::float8;
    else
      if rec.min_pct is not null and rec.min_pct > 0 then
        v_a := v_a || v_row; v_op := v_op || '>='::text; v_b := v_b || (rec.min_pct::float8 / 100 * v_batch);
      end if;
      if rec.max_pct is not null and rec.max_pct < 100 then
        v_a := v_a || v_row; v_op := v_op || '<='::text; v_b := v_b || (rec.max_pct::float8 / 100 * v_batch);
      end if;
    end if;
  end loop;

  -- ── সমাধান ──
  select * into v_res from core.lp_solve(v_cost, v_a, v_op, v_b);

  if v_res.status <> 'optimal' then
    return query select v_res.status, null::numeric, null::numeric,
                        null::citext, null::text, null::numeric, null::numeric;
    return;
  end if;

  -- ── ফলাফল প্রয়োগ ──
  if p_apply then
    for i in 1 .. n loop
      update feed.ration_formula_line
         set qty_kg = round((v_res.x)[i]::numeric, 4),
             unit_cost_snapshot = v_cost[i]::numeric
       where ration_formula_no = p_formula_no and item_no = v_items[i];
    end loop;
  end if;

  return query
  select 'optimal'::text,
         round(v_res.objective::numeric, 4),
         round((v_res.objective / v_batch)::numeric, 4),
         v_codes[idx],
         v_names[idx],
         round((v_res.x)[idx]::numeric, 4),
         round(((v_res.x)[idx] / v_batch * 100)::numeric, 3)
    from generate_subscripts(v_items, 1) as g(idx)
   where (v_res.x)[idx] > 1e-6
   order by (v_res.x)[idx] desc;
end
$$;

comment on function feed.optimize_formula(uuid, boolean) is
  'লিস্ট-কস্ট রেশন। ফরমুলায় যোগ করা উপাদানগুলোর মধ্যেই সবচেয়ে কম খরচের '
  'মিশ্রণ বের করে। p_apply=false দিলে সারি বদলায় না, শুধু ফলাফল দেখায়।';

-- ---------------------------------------------------------------------
-- সারসংক্ষেপ ভিউ
-- ---------------------------------------------------------------------
create view feed.v_formula_summary as
select f.ration_formula_no,
       f.organization_no,
       f.formula_code,
       f.name_bn,
       s.name_bn  as species_name_bn,
       pp.name_bn as purpose_name_bn,
       rs.name_bn as requirement_set_bn,
       f.batch_size_kg,
       f.status,
       f.priced_on,
       c.total_kg,
       c.total_cost,
       c.cost_per_kg,
       (select count(*) from feed.ration_formula_line l
         where l.ration_formula_no = f.ration_formula_no and l.ss_deleted_flag = false
           and l.qty_kg > 0)                                    as ingredient_count,
       -- চাহিদা পূরণ হয়েছে কি না, এক নজরে
       (select count(*) from feed.evaluate_formula(f.ration_formula_no) e
         where e.verdict in ('কম','বেশি'))                       as violation_count
  from feed.ration_formula f
  join master.species s on s.species_no = f.species_no
  join master.production_purpose pp on pp.production_purpose_no = f.production_purpose_no
  left join master.ration_requirement_set rs
         on rs.ration_requirement_set_no = f.ration_requirement_set_no
  cross join lateral feed.formula_cost(f.ration_formula_no) c
 where f.ss_deleted_flag = false;

grant select on feed.v_formula_summary to farmerp_app, farmerp_readonly;
grant execute on function feed.evaluate_formula(uuid),
                          feed.formula_cost(uuid),
                          feed.optimize_formula(uuid, boolean),
                          core.lp_solve(float8[], float8[], text[], float8[], integer, float8)
  to farmerp_app;
