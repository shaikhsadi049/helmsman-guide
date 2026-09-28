-- =====================================================================
-- 02_master_uom.sql — পরিমাপের একক ও রূপান্তর
--
-- বাংলাদেশের খামারে একক মেশানো থাকে: ফিড আসে বস্তায়, ওজন হয় কেজিতে,
-- পাইকারি হিসাব মনে, ডিম বিক্রি হয় শ/হালি/ট্রেতে, জমি শতকে।
-- একটাই ভুল রূপান্তর মানে পুরো খরচের হিসাব ভুল — তাই এটা মাস্টার ডেটা,
-- কোডে হার্ডকোড করা সংখ্যা নয়।
-- =====================================================================

create table master.uom (
  uom_no          uuid primary key default core.uuidv7(),
  organization_no uuid,                       -- NULL = গ্লোবাল (সব খামারে এক)
  uom_code        citext not null,
  name_bn         text   not null,
  name_en         text   not null,
  dimension       text   not null
      check (dimension in ('mass','count','volume','length','area','time','ratio','currency')),
  decimal_places  smallint not null default 3 check (decimal_places between 0 and 6),
  is_base         boolean  not null default false,   -- প্রতি dimension-এ একটাই base
  note_bn         text,
  like core.ss_row_template including all
);

create unique index ux_uom_code_global on master.uom (uom_code)
  where organization_no is null and ss_deleted_flag = false;
create unique index ux_uom_code_tenant on master.uom (organization_no, uom_code)
  where organization_no is not null and ss_deleted_flag = false;
create unique index ux_uom_base_per_dim on master.uom (dimension)
  where is_base and organization_no is null and ss_deleted_flag = false;

select core.ss_apply('master.uom', 'shared');

-- ---------------------------------------------------------------------
-- রূপান্তর: to_value = from_value * factor
-- শুধু একই dimension-এর ভেতরে। ভর ↔ সংখ্যা রূপান্তর এখানে নয় —
-- সেটা পণ্যনির্ভর (এক বস্তা ফিড ৫০ কেজি, এক বস্তা ভুট্টা আলাদা),
-- তাই সেই তথ্য item টেবিলে থাকবে, এখানে নয়।
-- ---------------------------------------------------------------------
create table master.uom_conversion (
  uom_conversion_no uuid primary key default core.uuidv7(),
  organization_no   uuid,
  from_uom_no       uuid not null references master.uom(uom_no),
  to_uom_no         uuid not null references master.uom(uom_no),
  factor            numeric(20,10) not null check (factor > 0),
  like core.ss_row_template including all,
  constraint ck_uom_conv_distinct check (from_uom_no <> to_uom_no)
);

create unique index ux_uom_conv on master.uom_conversion
  (coalesce(organization_no,'00000000-0000-0000-0000-000000000000'::uuid), from_uom_no, to_uom_no)
  where ss_deleted_flag = false;

select core.ss_apply('master.uom_conversion', 'shared');

-- একই dimension না হলে রূপান্তর অর্থহীন — ডাটাবেসই আটকাবে
create or replace function master.uom_conversion_guard()
returns trigger language plpgsql as $$
declare v_from text; v_to text;
begin
  select dimension into v_from from master.uom where uom_no = new.from_uom_no;
  select dimension into v_to   from master.uom where uom_no = new.to_uom_no;
  if v_from is distinct from v_to then
    raise exception 'ভিন্ন dimension-এর মধ্যে রূপান্তর করা যায় না: % -> %', v_from, v_to
      using errcode = 'check_violation';
  end if;
  return new;
end $$;

create trigger uom_conversion_guard_biu
  before insert or update on master.uom_conversion
  for each row execute function master.uom_conversion_guard();

-- ---------------------------------------------------------------------
-- যেকোনো দুই একক মধ্যে রূপান্তর (base unit হয়ে ঘুরে)
-- ---------------------------------------------------------------------
create or replace function master.convert_uom(
  p_value numeric, p_from uuid, p_to uuid
) returns numeric
language plpgsql stable as $$
declare
  v_f numeric; v_t numeric; v_dim_f text; v_dim_t text;
begin
  if p_from = p_to then return p_value; end if;

  select dimension into v_dim_f from master.uom where uom_no = p_from;
  select dimension into v_dim_t from master.uom where uom_no = p_to;
  if v_dim_f is distinct from v_dim_t then
    raise exception 'ভিন্ন dimension: % ও %', v_dim_f, v_dim_t using errcode = 'check_violation';
  end if;

  -- from -> base
  select case when u.is_base then 1
              else (select c.factor from master.uom_conversion c
                     where c.from_uom_no = p_from and c.to_uom_no =
                       (select uom_no from master.uom
                         where dimension = v_dim_f and is_base and organization_no is null)) end
    into v_f from master.uom u where u.uom_no = p_from;

  -- to -> base
  select case when u.is_base then 1
              else (select c.factor from master.uom_conversion c
                     where c.from_uom_no = p_to and c.to_uom_no =
                       (select uom_no from master.uom
                         where dimension = v_dim_t and is_base and organization_no is null)) end
    into v_t from master.uom u where u.uom_no = p_to;

  if v_f is null or v_t is null then
    raise exception 'রূপান্তরের হার সংজ্ঞায়িত নেই (from=%, to=%)', p_from, p_to
      using errcode = 'no_data_found';
  end if;

  return p_value * v_f / v_t;
end $$;
