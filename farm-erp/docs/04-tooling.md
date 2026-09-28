# ডাটাবেস ব্রাউজ করার টুল

## সংক্ষেপে

**DBeaver Community** ব্যবহার করুন। বিনামূল্যে, Windows/Mac/Linux, এবং Oracle-এ
Toad-এ অভ্যস্ত হলে এটাই সবচেয়ে কম ধাক্কা।

| টুল | কখন | দাম |
|---|---|---|
| **DBeaver Community** | দৈনন্দিন ব্রাউজিং, ডেটা সম্পাদনা, SQL এডিটর, ER ডায়াগ্রাম | বিনামূল্যে |
| **pgAdmin 4** | প্রশাসনিক কাজ — ভূমিকা, RLS পলিসি, ট্রিগার, ভ্যাকুয়াম, লগ | বিনামূল্যে |
| **psql** | স্ক্রিপ্ট, মাইগ্রেশন, CI, দ্রুত প্রশ্ন | সাথেই আসে |
| **pgModeler** | প্রকৃত ER মডেলিং ও ডকুমেন্টেশন ডায়াগ্রাম | বিনামূল্যে/সস্তা |
| **DataGrip** (JetBrains) | সেরা SQL এডিটর, যদি টাকা খরচে আপত্তি না থাকে | সাবস্ক্রিপশন |

দুটো টুলই রাখুন: DBeaver দেখার জন্য, pgAdmin প্রশাসনের জন্য। ওরা পরস্পরের প্রতিদ্বন্দ্বী নয়।

## Toad কেন নয়

Toad Edge ২.০+ Postgres সমর্থন করে, চললে চলবে। কিন্তু এই স্কিমা Postgres-নির্দিষ্ট
জিনিসের উপর দাঁড়ানো — RLS পলিসি, plpgsql ট্রিগার, generated column,
exclusion constraint, partial unique index। Toad Edge মূলত MySQL টুলিং থেকে বেড়েছে,
তাই এগুলোর অনেকটাই সে দেখায় না।

আরও গুরুত্বপূর্ণ: **কোনো GUI দিয়ে ডায়াগ্রাম থেকে DDL জেনারেট করলে RLS পলিসি,
ট্রিগার ও COMMENT নিঃশব্দে হারিয়ে যায়।** সত্যের একমাত্র উৎস `db/schema/` এর
`.sql` ফাইলগুলো, কোনো GUI নয়। টুল দিয়ে দেখুন, টুল দিয়ে স্কিমা বানাবেন না।

---

## এই স্কিমার দুটো ফাঁদ

### ১. RLS — superuser দিয়ে দেখলে আসল আচরণ দেখবেন না

`postgres` (superuser) দিয়ে কানেক্ট করলে RLS সম্পূর্ণ বাইপাস হয় — সব খামারের সব
ডেটা দেখবেন। এটা প্রশাসনের জন্য ঠিক, কিন্তু "অ্যাপ কী দেখে" বোঝার জন্য ভুল।

তাই দুটো আলাদা কানেকশন সেভ করুন:

| কানেকশন | ব্যবহারকারী | দেখে |
|---|---|---|
| `farmerp — admin` | `postgres` | সব কিছু (RLS বাইপাস) |
| `farmerp — app` | `farmerp_dev` | অ্যাপ যা দেখে (RLS প্রযোজ্য) |

লগইন-সক্ষম ভূমিকা বানাতে:

```bash
psql -d farmerp -v app_password='আপনার_পাসওয়ার্ড' -f db/dev_roles.sql
```

এটা `farmerp_dev` (পড়া-লেখা) ও `farmerp_dev_ro` (শুধু পড়া) বানায়, যেগুলো
`farmerp_app`/`farmerp_readonly` এর অনুমতি উত্তরাধিকার পায়। স্ক্রিপ্ট শেষে
প্রতিটা খামারের `organization_no` ছাপিয়ে দেয় — পরের ধাপে লাগবে।

### ২. প্রসঙ্গ না বসালে টেবিল ফাঁকা দেখাবে

`farmerp_dev` দিয়ে কানেক্ট করে `core.farm` খুললে **শূন্য সারি** দেখবেন। ডেটা
হারায়নি — RLS fail-closed, আর আপনি বলেননি কোন খামারের হয়ে দেখছেন।

DBeaver-এ: কানেকশন সেটিংস → **Initialization** → *Bootstrap queries* এ যোগ করুন:

```sql
SET app.organization_no = '01a0e907-58d1-7fb8-8291-c4f134e98a6d';
SET app.user_no         = '00000000-0000-0000-0000-000000000001';
```

(`organization_no` আপনার নিজের ডাটাবেসে ভিন্ন হবে — `dev_roles.sql` যেটা ছাপিয়েছে
সেটা বসান।)

pgAdmin-এ bootstrap query নেই, তাই প্রতি সেশনে Query Tool-এ হাতে চালাতে হবে।
এটাও একটা কারণ কেন ব্রাউজিংয়ে DBeaver বেশি সুবিধাজনক।

যাচাই করে দেখুন — প্রসঙ্গ বসানো আর না বসানোর পার্থক্য:

```sql
-- প্রসঙ্গ ছাড়া
select count(*) from core.farm;        -- 0   ← fail-closed
select count(*) from master.breed;     -- 116 ← গ্লোবাল মাস্টার ডেটা

-- প্রসঙ্গ বসিয়ে
set app.organization_no = '<uuid>';
select count(*) from core.farm;        -- আপনার খামারগুলো
select count(*) from prod.production_unit;
```

---

## বাংলা লেখা ঠিকভাবে দেখা

ডাটাবেস UTF-8, টেবিল ও কলামের মন্তব্যও বাংলায়। কিন্তু টুলের ফন্ট বাংলা না জানলে
যুক্তাক্ষর ভেঙে যাবে ("ক্ষ" → "ক্‌ষ")।

- **DBeaver** — Window → Preferences → User Interface → Appearance → Colors and Fonts →
  গ্রিড ও এডিটরের ফন্ট এমন কিছু দিন যা বাংলা রেন্ডার করে: **Noto Sans Bengali**,
  **Nirmala UI** (Windows-এ আছে), বা **SolaimanLipi**
- **pgAdmin** — ব্রাউজারে চলে, সিস্টেম ফন্টই ব্যবহার করে, সাধারণত এমনিতেই ঠিক থাকে
- **Windows-এ psql** — `chcp 65001` চালিয়ে UTF-8 কোডপেজ দিন, আর টার্মিনালে
  Windows Terminal ব্যবহার করুন (পুরোনো cmd.exe বাংলা ভাঙে)

---

## যেগুলো টুলে দেখে নেওয়া মূল্যবান

স্কিমার অনেক যুক্তি টেবিলের গঠনে নয়, ট্রিগার ও মন্তব্যে। DBeaver-এ এগুলো দেখুন:

| কোথায় | কী দেখবেন |
|---|---|
| `core.ss_table_registry` | প্রতিটা টেবিল কোন scope-এ, কোনটা অ্যাপেন্ড-অনলি |
| যেকোনো টেবিল → Triggers | `ss_audit_biu`, `ss_tenant_guard_bu`, প্রয়োজনে `ss_append_only_bud` |
| যেকোনো টেবিল → Permissions/Policies | চারটি RLS পলিসি (`ss_sel/ins/upd/del`) |
| `master.metric_applicability` | কোন প্রজাতির কোন উদ্দেশ্যে কোন মাপ প্রযোজ্য |
| `prod.v_unit_balance` | বর্তমান সংখ্যা, মড়ক %, অবক্ষয় % — সবই চলাচল থেকে হিসাব করা |
| টেবিল ও কলামের Comments | বাংলায় ব্যাখ্যা — কেন এই ডিজাইন |

মন্তব্য দেখার দ্রুত উপায়, টুল যা-ই হোক:

```sql
-- একটা টেবিলের সব কলামের মন্তব্য
select a.attname as কলাম, col_description(a.attrelid, a.attnum) as মন্তব্য
  from pg_attribute a
 where a.attrelid = 'master.movement_type'::regclass
   and a.attnum > 0 and not a.attisdropped
 order by a.attnum;
```

---

## psql দিয়ে দ্রুত কাজ

GUI খোলার দরকার নেই এমন কাজে:

```bash
psql -d farmerp                          # কানেক্ট
\dt core.*                               # core স্কিমার টেবিল
\d+ prod.production_unit                 # গঠন, ইনডেক্স, ট্রিগার, মন্তব্য
\dp prod.unit_movement                   # অনুমতি ও RLS পলিসি
\df core.ss_*                            # কনভেনশন ফাংশনগুলো
\x on                                    # লম্বা সারি উল্লম্বভাবে দেখা
```

`\d+` সবচেয়ে কাজের — একটা কমান্ডেই কলাম, ডিফল্ট, ইনডেক্স, constraint, ট্রিগার,
পলিসি ও মন্তব্য সব দেখায়। অনেক GUI-তে এতগুলো ট্যাব ঘুরতে হয়।
