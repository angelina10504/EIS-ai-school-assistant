-- XYZ AI — demo data for Supabase / Postgres.
-- Run after schema.sql. Safe to re-run: it clears the tables first.
--
-- Attendance is generated relative to CURRENT_DATE (the last 34 weekdays), so the
-- demo never goes stale. Every account's password is: password123
--
-- The same data can be created locally with: python -m app.db.seed --reset

begin;

truncate audit_log, conversation_messages, conversation_sessions, escalation_requests,
         attendance, parent_student_link, students, classes, users restart identity cascade;

-- Fixed UUIDs keep the demo links stable across reseeds.
insert into users (id, role, name, email, password_hash, preferred_language) values
  ('00000000-0000-4000-8000-000000000001','principal','Dr. Meera Iyer','principal@xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000002','teacher','Anita Sharma','anita@teacher.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000003','teacher','Vikram Rao','vikram@teacher.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000011','student','Rahul Verma','rahul@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000012','student','Priya Nair','priya@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000013','student','Arjun Nair','arjun@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000014','student','Sneha Kulkarni','sneha@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000015','student','Imran Khan','imran@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000016','student','Divya Reddy','divya@student.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000021','parent','Sunita Verma','sunita@parent.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000022','parent','Ramesh Nair','ramesh@parent.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en'),
  ('00000000-0000-4000-8000-000000000023','parent','Farah Khan','farah@parent.xyz.edu','pbkdf2_sha256$120000$xyzaidemosalt0001$4fa4066a8d03fbf490750393952bd734c4c880064b018047cd2afc0097781168','en');

insert into classes (id, name, teacher_id) values
  ('00000000-0000-4000-8000-0000000000a1','Class 8A','00000000-0000-4000-8000-000000000002'),
  ('00000000-0000-4000-8000-0000000000a2','Class 8B','00000000-0000-4000-8000-000000000003');

insert into students (id, roll_number, class_id) values
  ('00000000-0000-4000-8000-000000000011','8A-01','00000000-0000-4000-8000-0000000000a1'),
  ('00000000-0000-4000-8000-000000000012','8A-02','00000000-0000-4000-8000-0000000000a1'),
  ('00000000-0000-4000-8000-000000000013','8A-03','00000000-0000-4000-8000-0000000000a1'),
  ('00000000-0000-4000-8000-000000000014','8B-01','00000000-0000-4000-8000-0000000000a2'),
  ('00000000-0000-4000-8000-000000000015','8B-02','00000000-0000-4000-8000-0000000000a2'),
  ('00000000-0000-4000-8000-000000000016','8B-03','00000000-0000-4000-8000-0000000000a2');

-- Ramesh Nair has two children, which is what makes the "which child?" clarification demoable.
insert into parent_student_link (parent_id, student_id) values
  ('00000000-0000-4000-8000-000000000021','00000000-0000-4000-8000-000000000011'),
  ('00000000-0000-4000-8000-000000000022','00000000-0000-4000-8000-000000000012'),
  ('00000000-0000-4000-8000-000000000022','00000000-0000-4000-8000-000000000013'),
  ('00000000-0000-4000-8000-000000000023','00000000-0000-4000-8000-000000000015');

-- ~7 weeks of weekday attendance. Rahul lands on 91.2%, matching the brief's example.
with all_days as (
  select g.d::date as day
  from generate_series(current_date - interval '80 days', current_date, interval '1 day') as g(d)
  where extract(isodow from g.d) < 6
),
last_days as (
  select day from all_days order by day desc limit 34
),
days as (
  select day, (row_number() over (order by day)) - 1 as idx from last_days
),
plan (roll, absent_days, late_days) as (values
  ('8A-01', array[6,19],                 array[11,27]),
  ('8A-02', array[3],                    array[22]),
  ('8A-03', array[1,2,9,14,20,25,30],    array[8]),
  ('8B-01', array[12],                   array[]::int[]),
  ('8B-02', array[4,5,17],               array[21,29]),
  ('8B-03', array[7,16,23,28],           array[2,13])
)
insert into attendance (student_id, date, status, marked_by)
select s.id,
       d.day,
       case
         when d.idx = any(p.absent_days) then 'absent'
         when d.idx = any(p.late_days)   then 'late'
         else 'present'
       end,
       c.teacher_id
from days d
cross join plan p
join students s on s.roll_number = p.roll
join classes  c on c.id = s.class_id;

commit;
