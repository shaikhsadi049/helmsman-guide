-- =====================================================================
-- 11_core_lp.sql — রৈখিক প্রোগ্রামিং সলভার (দুই-পর্যায় সিমপ্লেক্স)
--
-- কেন ডাটাবেসের ভেতরে:
-- লিস্ট-কস্ট রেশন বের করা একটা LP সমস্যা। এটা অ্যাপ্লিকেশন স্তরে রাখলে
-- (Python + scipy) সেই স্তর ছাড়া রেশন হিসাব করা যায় না — রিপোর্ট থেকে,
-- ব্যাচ কপি করার সময়, বা রাতের ব্যাচ জব থেকে নয়। উপাদানের দাম ও
-- পুষ্টিমান যেহেতু ডাটাবেসেই, সলভারও এখানেই থাকা যুক্তিসঙ্গত।
--
-- সমস্যার রূপ:  minimize c'x  subject to  A x {<=,>=,=} b,  x >= 0
-- চলকের উপরের-নিচের সীমা (যেমন "ভুট্টা সর্বোচ্চ ৬০%") আলাদা সারি হিসেবে
-- পাঠানো হয় — বাউন্ডেড-ভেরিয়েবল সিমপ্লেক্সের জটিলতা এড়াতে। রেশনের
-- আকারে (২০–৪০ উপাদান) এর খরচ অগ্রাহ্য।
--
-- চক্রায়ন (cycling) এড়াতে Bland-এর নিয়ম: প্রবেশক ও নির্গমনকারী দুটোতেই
-- সবচেয়ে ছোট সূচক বেছে নেওয়া হয়। এতে ধাপ কিছু বাড়ে কিন্তু সমাপ্তি
-- গাণিতিকভাবে নিশ্চিত — একটা রেশন সলভার কখনো অনির্দিষ্টকাল ঘুরতে পারে না।
-- =====================================================================

create or replace function core.lp_solve(
  p_c       float8[],                 -- n টি উদ্দেশ্য সহগ (ন্যূনতমীকরণ)
  p_a       float8[],                 -- m×n ম্যাট্রিক্স, row-major সমতল
  p_relop   text[],                   -- m টি: '<=', '>=', '='
  p_b       float8[],                 -- m টি ডান পক্ষ
  p_maxiter integer default 20000,
  p_eps     float8  default 1e-9
)
returns table (status text, objective float8, x float8[])
language plpgsql
immutable
as $$
declare
  n        integer;          -- মূল চলক সংখ্যা
  m        integer;          -- শর্ত সংখ্যা
  nx       integer;          -- মোট কলাম (মূল + স্ল্যাক + সারপ্লাস + কৃত্রিম)
  w        integer;          -- সারির প্রস্থ = nx + 1 (শেষ কলাম RHS)
  t        float8[];         -- সমতল টেবিলো, আকার m*w
  bas      integer[];        -- প্রতিটা সারির ভিত্তি চলকের কলাম সূচক
  is_art   boolean[];        -- কোন কলাম কৃত্রিম
  cost     float8[];         -- বর্তমান পর্যায়ের উদ্দেশ্য সহগ
  d        float8[];         -- হ্রাসকৃত ব্যয়
  relop    text[];
  bb       float8[];
  sgn      float8;
  ncol     integer;
  i        integer; j integer; k integer; r integer;
  piv      float8; ratio float8; best float8;
  enter    integer; leave integer;
  iter     integer := 0;
  phase    integer;
  zval     float8;
  cb       float8;
  xout     float8[];
  art_count integer := 0;
begin
  n := coalesce(array_length(p_c, 1), 0);
  m := coalesce(array_length(p_b, 1), 0);

  if n = 0 then
    raise exception 'LP: উদ্দেশ্য সহগ খালি' using errcode = 'invalid_parameter_value';
  end if;
  if m = 0 then
    -- শর্তহীন সমস্যা: c >= 0 হলে x = 0 সর্বোত্তম, নইলে অসীম
    if exists (select 1 from unnest(p_c) v where v < -p_eps) then
      return query select 'unbounded'::text, null::float8, null::float8[];
    end if;
    return query select 'optimal'::text, 0::float8, array_fill(0::float8, array[n]);
  end if;
  if array_length(p_a, 1) <> m * n then
    raise exception 'LP: A এর আকার (%) m*n (%) এর সাথে মেলে না',
      array_length(p_a, 1), m * n using errcode = 'invalid_parameter_value';
  end if;
  if array_length(p_relop, 1) <> m then
    raise exception 'LP: relop সংখ্যা (%) শর্ত সংখ্যার (%) সমান নয়',
      array_length(p_relop, 1), m using errcode = 'invalid_parameter_value';
  end if;

  -- ── ধাপ ১: স্বাভাবিকীকরণ — সব b >= 0 করা ──
  relop := p_relop;
  bb    := p_b;
  for i in 1 .. m loop
    if relop[i] not in ('<=', '>=', '=') then
      raise exception 'LP: অজানা relop "%" (সারি %)', relop[i], i
        using errcode = 'invalid_parameter_value';
    end if;
    if bb[i] < 0 then
      bb[i] := -bb[i];
      relop[i] := case relop[i] when '<=' then '>=' when '>=' then '<=' else '=' end;
    end if;
  end loop;

  -- ── ধাপ ২: অতিরিক্ত কলাম গণনা ──
  ncol := n;
  for i in 1 .. m loop
    if    relop[i] = '<=' then ncol := ncol + 1;                  -- স্ল্যাক
    elsif relop[i] = '>=' then ncol := ncol + 2;                  -- সারপ্লাস + কৃত্রিম
    else                       ncol := ncol + 1;                  -- কৃত্রিম
    end if;
  end loop;
  nx := ncol;
  w  := nx + 1;

  -- ── ধাপ ৩: টেবিলো গঠন ──
  t      := array_fill(0::float8, array[m * w]);
  is_art := array_fill(false, array[nx]);
  bas    := array_fill(0, array[m]);

  -- মূল সহগ বসানো (চিহ্ন সংশোধন সহ)
  for i in 1 .. m loop
    sgn := case when p_b[i] < 0 then -1 else 1 end;
    for j in 1 .. n loop
      t[(i - 1) * w + j] := sgn * p_a[(i - 1) * n + j];
    end loop;
    t[(i - 1) * w + w] := bb[i];
  end loop;

  k := n;
  for i in 1 .. m loop
    if relop[i] = '<=' then
      k := k + 1;
      t[(i - 1) * w + k] := 1;            -- স্ল্যাক
      bas[i] := k;
    elsif relop[i] = '>=' then
      k := k + 1;
      t[(i - 1) * w + k] := -1;           -- সারপ্লাস
      k := k + 1;
      t[(i - 1) * w + k] := 1;            -- কৃত্রিম
      is_art[k] := true;
      bas[i] := k;
      art_count := art_count + 1;
    else
      k := k + 1;
      t[(i - 1) * w + k] := 1;            -- কৃত্রিম
      is_art[k] := true;
      bas[i] := k;
      art_count := art_count + 1;
    end if;
  end loop;

  -- ── ধাপ ৪: দুই পর্যায় ──
  for phase in 1 .. 2 loop

    if phase = 1 then
      if art_count = 0 then
        continue;                         -- সব সারি '<=', ভিত্তি ইতিমধ্যেই সম্ভাব্য
      end if;
      cost := array_fill(0::float8, array[nx]);
      for j in 1 .. nx loop
        if is_art[j] then cost[j] := 1; end if;
      end loop;
    else
      cost := array_fill(0::float8, array[nx]);
      for j in 1 .. n loop
        cost[j] := p_c[j];
      end loop;
    end if;

    loop
      -- হ্রাসকৃত ব্যয়: d[j] = c[j] - Σ c[bas[i]] * t[i][j]
      d := array_fill(0::float8, array[nx]);
      for j in 1 .. nx loop
        d[j] := cost[j];
      end loop;
      zval := 0;
      for i in 1 .. m loop
        cb := cost[bas[i]];
        if cb <> 0 then
          for j in 1 .. nx loop
            d[j] := d[j] - cb * t[(i - 1) * w + j];
          end loop;
          zval := zval + cb * t[(i - 1) * w + w];
        end if;
      end loop;

      -- প্রবেশক নির্বাচন (Bland: সবচেয়ে ছোট সূচক যার d < 0)
      enter := 0;
      for j in 1 .. nx loop
        -- পর্যায় ২-এ কৃত্রিম চলক আর ঢুকতে পারবে না
        if phase = 2 and is_art[j] then
          continue;
        end if;
        if d[j] < -p_eps then
          enter := j;
          exit;
        end if;
      end loop;

      exit when enter = 0;                -- সর্বোত্তম

      -- নির্গমনকারী নির্বাচন (অনুপাত পরীক্ষা, সমতায় ছোট ভিত্তি সূচক)
      leave := 0;
      best  := null;
      for i in 1 .. m loop
        piv := t[(i - 1) * w + enter];
        if piv > p_eps then
          ratio := t[(i - 1) * w + w] / piv;
          if best is null
             or ratio < best - p_eps
             or (abs(ratio - best) <= p_eps and bas[i] < bas[leave]) then
            best  := ratio;
            leave := i;
          end if;
        end if;
      end loop;

      if leave = 0 then
        if phase = 1 then
          raise exception 'LP: পর্যায় ১ অসীম — অভ্যন্তরীণ ত্রুটি';
        end if;
        return query select 'unbounded'::text, null::float8, null::float8[];
        return;
      end if;

      -- ── পিভট ──
      r   := leave;
      piv := t[(r - 1) * w + enter];
      for j in 1 .. w loop
        t[(r - 1) * w + j] := t[(r - 1) * w + j] / piv;
      end loop;
      for i in 1 .. m loop
        if i <> r then
          cb := t[(i - 1) * w + enter];
          if cb <> 0 then
            for j in 1 .. w loop
              t[(i - 1) * w + j] := t[(i - 1) * w + j] - cb * t[(r - 1) * w + j];
            end loop;
          end if;
        end if;
      end loop;
      bas[r] := enter;

      iter := iter + 1;
      if iter > p_maxiter then
        raise exception 'LP: % ধাপেও সমাধান হয়নি (phase %)', p_maxiter, phase
          using errcode = 'program_limit_exceeded';
      end if;
    end loop;

    -- পর্যায় ১ শেষে সম্ভাব্যতা পরীক্ষা
    if phase = 1 and art_count > 0 then
      if zval > 1e-7 then
        return query select 'infeasible'::text, null::float8, null::float8[];
        return;
      end if;
      -- শূন্য মানে ভিত্তিতে থাকা কৃত্রিম চলক বের করার চেষ্টা
      for i in 1 .. m loop
        if is_art[bas[i]] then
          enter := 0;
          for j in 1 .. nx loop
            if not is_art[j] and abs(t[(i - 1) * w + j]) > p_eps then
              enter := j; exit;
            end if;
          end loop;
          if enter > 0 then
            r := i;
            piv := t[(r - 1) * w + enter];
            for j in 1 .. w loop
              t[(r - 1) * w + j] := t[(r - 1) * w + j] / piv;
            end loop;
            for k in 1 .. m loop
              if k <> r then
                cb := t[(k - 1) * w + enter];
                if cb <> 0 then
                  for j in 1 .. w loop
                    t[(k - 1) * w + j] := t[(k - 1) * w + j] - cb * t[(r - 1) * w + j];
                  end loop;
                end if;
              end if;
            end loop;
            bas[r] := enter;
          end if;
          -- বের করা না গেলে সারিটা অপ্রয়োজনীয় (redundant); রেখে দেওয়া নিরাপদ,
          -- কারণ পর্যায় ২-এ কৃত্রিম চলক ঢুকতে পারে না আর তার মান শূন্য
        end if;
      end loop;
    end if;

  end loop;

  -- ── সমাধান বের করা ──
  xout := array_fill(0::float8, array[n]);
  for i in 1 .. m loop
    if bas[i] <= n then
      xout[bas[i]] := t[(i - 1) * w + w];
    end if;
  end loop;

  zval := 0;
  for j in 1 .. n loop
    zval := zval + p_c[j] * xout[j];
  end loop;

  return query select 'optimal'::text, zval, xout;
end
$$;

comment on function core.lp_solve(float8[], float8[], text[], float8[], integer, float8) is
  'দুই-পর্যায় সিমপ্লেক্স। minimize c''x s.t. A x {<=,>=,=} b, x >= 0। '
  'status: optimal | infeasible | unbounded';
