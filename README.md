# ALE — Adaptive Learning Environment

An AI-guided coding practice platform for undergraduate programming courses (C++).

## Services

| Service | Port | Description |
|---|---|---|
| Frontend | 3000 | React student + admin UI |
| Backend | 8000 | FastAPI REST API |
| Code Runner | 8001 (internal) | C++ sandbox execution |
| PostgreSQL | 5432 | Database |

## Quick Start

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY in .env

docker compose up --build
```

Then open http://localhost:3000

Default admin: `admin@example.com` / `adminpassword` (set via env vars).

## Architecture

```
frontend (React + Monaco)
    ↕ REST
backend (FastAPI)
    ├── /auth         — JWT auth (register/login)
    ├── /tasks        — task listing (student)
    ├── /sessions     — learning sessions + AI agent
    └── /admin        — task & test case management
         ↕ HTTP (internal)
code-runner (g++ sandbox)
         ↕ PostgreSQL
```

## AI Agent (Amazon Strands SDK)

The agent uses **GPT-4o** via OpenAI and has three capabilities:

1. **Plan generation** — on session start, analyzes task requirements + model solution → produces ordered steps (correctness-first, optimization-last)
2. **Step evaluation** — on "Check Step", evaluates student code against current step criteria → pass/fail + feedback
3. **Hints** — targeted guidance without revealing the answer

## Student Flow

1. Register / Login
2. Pick a task from the list
3. Click **Start Session** → AI generates a step-by-step plan
4. Write code in Monaco editor
5. **Check Step** → AI evaluates, gives feedback
6. **Hint** → AI gives a nudge without the answer
7. **Run All Tests** → runs all (including hidden) test cases
8. Progress through all steps to complete the task

## Admin Flow

1. Login with admin account
2. Go to **Admin** → **Manage Tasks**
3. Create task: title, description (Markdown), starter code, model solution, test cases
4. Test cases can be `code_sample` (snippet inserted into main) or `stdin_stdout`
5. Mark test cases as hidden to use them for grading but not show to students

## courses.finki (Moodle) — LTI 1.3

ALE works as an external tool inside the faculty's Moodle: people open it from their Moodle course and are signed
in without a password, land in the linked subject's space with their Moodle role (teacher / student), and
points go back into Moodle's gradebook.

**Register (once, ALE admin + Moodle admin)**

1. ALE: *Administration → courses.finki (LTI) → New registration link* (valid 7 days, one use).
2. Moodle: *Site administration → Plugins → Activity modules → External tool → Manage tools*, paste the link into
   *Tool URL*, click *Add LTI Advantage*, then *Activate* the new "ALE" tool.
   Recommended in the tool's settings: *Tool configuration usage* — "Show in activity chooser and as a preconfigured
   tool"; *Default launch container* — "New window" (or "Embed" on HTTPS).
3. No dynamic registration? Use *configure a tool manually* with the values shown on the same ALE page and add the
   platform there (Moodle address, Client ID, Deployment ID).

**In a course (teacher)**

1. In the Moodle course add the activity *ALE* and click *Select content*. The first time, ALE asks which subject this
   Moodle course is (the subject with the same name is suggested).
2. Choose a link to the whole course and/or assignments: each assignment becomes a Moodle activity with its own grade
   column.
3. ALE → course → *Students* (or *Grades*): *Pull participants* (everyone from Moodle with their role) and *Send grades*.
   *Publish grades* on an assignment also sends them.

Only published assignments whose points students may already see are sent. Moodle can raise a person's course role
in ALE, never lower one, and never changes a role the admin set (locked). Moodle sends only Instructor / Learner: see *Roles* below.

Standards: LTI 1.3 Core, Deep Linking 2.0, Assignment and Grade Services 2.0, Names and Role Provisioning 2.0,
Dynamic Registration 1.0. Tested with Moodle 4.5.

## Subjects, accounts and permissions

There are no courses to make: **every subject has one space** (its labs, colloquia, homework, points, final grades,
materials, mail and the Moodle link). Accounts are only **student**, **teacher** and **admin**, and the e-mail decides
which: `…@students.finki.ukim.mk` signs up as a student, `…@finki.ukim.mk` as a teacher with **no permissions** until
the admin adds them to a subject; other e-mails cannot sign up (`STUDENT_EMAIL_DOMAINS` / `TEACHER_EMAIL_DOMAINS`).
The admin can still change an account by hand (e.g. a student-лаборант keeps a student account and gets the лаборант's
permissions in one subject).

**Estimated grade.** ALE is for practice, so each student sees their estimated grade at once (in the subject's header
and under *Standing*): every point they may already see counts, also of labs and colloquia still open; a part with no
points yet comes from their practice. The real grade is entered later by a teacher with *final grades*.

| Who | What they do |
|---|---|
| **Admin** | Everything. Manages the subjects (the FINKI catalogue), users, AI, mail, LTI, and in *Administration → Teachers* adds the teachers to each subject and ticks what each of them may do there. |
| **Teacher** | In each subject only what the admin ticked for them (below). A teacher of one subject is nobody in another. |
| **Student** | Is in the spaces of their studies on their own: **every mandatory subject** and **the electives they chose** (dropping an elective takes them out). There they do the labs and colloquia and practise with the teachers' practice tasks ("the higher level"). In any other subject only the public tasks and AI practice on their own key. The admin or Moodle can add a student to any subject. |

**Permissions of a teacher in a subject** (like Moodle's capabilities): labs and practice — *see / make and edit (and
their type) / enter points, attendance, comments*; colloquia, exams, homework — *see / set up / enter points*; points
and grades — *see all points and the standing / final grades / grading rules*; and *see the people, upload materials,
send mail, see the subject's logs, see the students' own AI practice*. The buttons **Like a professor / an assistant / a
лаборант** only tick the boxes (professor: all; assistant: all but final grades and grading rules; лаборант: the labs
and the students' practice) — any box can then be changed one by one, nothing else is stored.

**Grading tutor.** On the grading page, *Grading tutor* asks the AI for a suggestion: points (or rubric scores), what
is good, the issues by line (each can become a code comment) and a comment for the student. Nothing is saved until
the grader saves the points.

**Roles from courses.finki (LTI).** Moodle sends only *Instructor* / *Learner* (+ *Administrator*): Learner → student,
Instructor → a teacher with the assistant's boxes ticked, Instructor#Grader → the лаборант's, Administrator → the
professor's. The admin links a Moodle course to a subject's space (a teacher of the subject can link it too). What the
admin sets is **locked** (🔒 in *Students*) — Moodle never changes it (click the lock to let Moodle add permissions
again); Moodle can only add, never take away.

## Logs

*Administration → Logs* shows everything the platform records, newest first: **AI calls** (tutor steps and checks,
hints, explanations, visualisations, the grading tutor, generated tasks — with model, tokens, duration), **test runs**
(passed / total, language), and **activity** — sign-ins (also failed ones; an unknown e-mail is masked), tutor
sessions, steps checked, finished tasks, submissions, points, published points, comments, attendance, assignments,
courses and people, electives and requests, LTI launches, grading rules, final grades, subject and role changes.
Filter by kind, period, operation or person; *Live* refreshes every 5 s; *CSV* exports up to 20 000 lines; a line opens
its details. The professor and assistants see the course's activity in the course (*Activity* tab, incl. the students'
own practice in the subject); everyone sees their own in *Profile → My activity*. Logs older than
`LOG_RETENTION_DAYS` (default 180, `0` = keep) are deleted at start-up.

## Subjects

The subjects of FINKI's 2023 study programmes that have a programming language or programming logic — 78 of them
(`backend/app/data/finki_subjects.csv`: code, name, recommended semester, mandatory / elective) — are added once by
`seed.py`; the admin adds new subjects to the catalogue when they appear. Subjects without programming (mathematics,
business, pedagogy, networks theory…) were removed by the migration `20261104_programming_only` — except those that
already had tasks or courses, so nothing anyone made is lost.

**Electives.** Each student puts electives into their own semesters (*Subjects*): with the semester on the card,
with "Add an elective" in a semester, or by dragging the card onto a semester. They choose freely once and then
*Confirm*; after that a change is a **request to the admin** that always has both parts — one elective out and one
in (or the same one into another semester). Whichever part the student starts with, the dialog asks for the other;
*Send the request* / *Cancel*. The admin approves or rejects it in *Administration → Elective requests* (and can let
a student choose freely again).

**Staff and the students' practice.** The professor, assistants and лаборанти of a course of a subject see
everything in it, and also what the students practise there with their own AI key (the subject page → *Students'
own practice*: their tasks, steps and code).

**Tasks made with the tutor.** In an assignment, *Make tasks with the tutor* writes new tasks for the course's
subject: with test examples (kept only where the AI's own solution passes them) or a project handed in as a zip
(rubric + the reference solution zipped for the staff). They go into the bank (not public).

**Colloquium exercises and the estimated grade.** A practice assignment can be *Preparation for* colloquium 1 / 2 /
the exam: it never counts, but it feeds each student's **estimated grade** — the course's weights and thresholds,
with every part that has no points yet taken from that preparation, the labs still open, or the student's own
practice in the subject (tasks finished out of those started). Students see it in *My standing*, staff in the
*Estimate* column.

## DevOps tasks

"Континуирана интеграција и испорака (DevOps)" has tasks in **Git** (a script of git commands, run in a fresh
folder; the tests inspect the repository), **Bash**, **Dockerfile**, **YAML** (GitHub Actions, docker-compose,
Kubernetes) and **Terraform**. Dockerfile / YAML / Terraform files are parsed (nothing is built or deployed) and
the tests are Python asserts with helpers — see `code-runner/app/devops.py`.
