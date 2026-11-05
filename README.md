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
in without a password, land in the linked ALE course with their Moodle role (teacher / assistant / student), and
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

1. In the Moodle course add the activity *ALE* and click *Select content*. The first time, ALE asks which ALE course
   this Moodle course is (a course of the same subject is suggested) or makes a new one.
2. Choose a link to the whole course and/or assignments: each assignment becomes a Moodle activity with its own grade
   column.
3. ALE → course → *Students* (or *Grades*): *Pull participants* (everyone from Moodle with their role) and *Send grades*.
   *Publish grades* on an assignment also sends them.

Only published assignments whose points students may already see are sent. Moodle can raise a person's course role
in ALE, never lower one, and never changes a role the admin set (locked). Moodle sends only Instructor / Learner: see *Roles* below.

Standards: LTI 1.3 Core, Deep Linking 2.0, Assignment and Grade Services 2.0, Names and Role Provisioning 2.0,
Dynamic Registration 1.0. Tested with Moodle 4.5.

## Roles

| Who | What they do |
|---|---|
| **Admin** | Everything: makes courses (*Administration → Courses*) and puts people in them with their role, manages subjects (the FINKI catalogue, electives per semester), users, AI, mail, LTI. |
| **Professor** (course role *teacher*) | Everything in the course: sees the points of the labs and the colloquia, writes the **grading rules** (*Grades → Standing*) and enters the **final grades** (5–10; the standing only proposes one). |
| **Assistant** | Adds the labs (mainly their job) and sets their type, sets up colloquia / exams and homework, reviews and comments, enters points and attendance, publishes the points; sees the gradebook. No grading rules, no final grades. |
| **Lab assistant** (*лаборант*) | The labs (and practice) only: adds and edits them when needed and sets their type (lab or practice), looks at the submissions, enters points (the **grading tutor** suggests them) and attendance, comments, publishes the lab points. |
| **Student** | Practises in every subject; solves the labs and everything else only in the courses they are enrolled in (by the admin, or by Moodle via LTI). |

**Grading tutor.** On the grading page, *Grading tutor* asks the AI for a suggestion: points (or rubric scores), what
is good, the issues by line (each can become a code comment) and a comment for the student. Nothing is saved until
the grader saves the points.

**Roles from courses.finki (LTI).** Moodle sends only *Instructor* / *Learner* (+ *Administrator*), so: Administrator →
professor, Instructor (and Instructor#TeachingAssistant) → assistant, Instructor#Grader → лаборант, Learner → student.
The admin sets the professor and the лаборанти once per course; a role the admin sets is **locked** (🔒 in *Students*)
— Moodle never changes it (click the lock to let Moodle set it again). Moodle can only raise an unlocked role.

## Subjects

All 174 subjects of FINKI's 2023 study programmes (`backend/app/data/finki_subjects.csv`: code, name, recommended
semester, mandatory / elective) are added once by `seed.py`; the admin adds new subjects to the catalogue when they appear.

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
