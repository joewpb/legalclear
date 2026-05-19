-- Phase 3: seed 2026 Florida state court holiday closures.
-- circuit=0 = statewide. Source: Fla. Stat. § 110.117.
-- July 4 falls on Saturday; observed Friday July 3 per § 110.117(2).

insert into public.court_closures (circuit, county, closure_date, reason, source)
values
  (0, null, '2026-01-01', 'New Year''s Day',             'Fla. Stat. § 110.117'),
  (0, null, '2026-01-19', 'Martin Luther King Jr. Day',  'Fla. Stat. § 110.117'),
  (0, null, '2026-05-25', 'Memorial Day',                'Fla. Stat. § 110.117'),
  (0, null, '2026-07-03', 'Independence Day (observed)', 'Fla. Stat. § 110.117(2) — July 4 falls on Saturday'),
  (0, null, '2026-09-07', 'Labor Day',                   'Fla. Stat. § 110.117'),
  (0, null, '2026-11-11', 'Veterans Day',                'Fla. Stat. § 110.117'),
  (0, null, '2026-11-26', 'Thanksgiving Day',            'Fla. Stat. § 110.117'),
  (0, null, '2026-11-27', 'Day After Thanksgiving',      'Fla. Stat. § 110.117'),
  (0, null, '2026-12-25', 'Christmas Day',               'Fla. Stat. § 110.117')
on conflict do nothing;
