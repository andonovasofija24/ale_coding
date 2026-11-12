--
-- PostgreSQL database dump
--

\restrict BhRvJ5xDyO7Sy5FQ2joBFEVSv2VJRdNehfLm26gQMiqPG7I94gQFc2YLwdJeh9I

-- Dumped from database version 15.19
-- Dumped by pg_dump version 15.19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: session_status; Type: TYPE; Schema: public; Owner: ale
--

CREATE TYPE public.session_status AS ENUM (
    'in_progress',
    'completed'
);


ALTER TYPE public.session_status OWNER TO ale;

--
-- Name: step_status; Type: TYPE; Schema: public; Owner: ale
--

CREATE TYPE public.step_status AS ENUM (
    'pending',
    'active',
    'completed'
);


ALTER TYPE public.step_status OWNER TO ale;

--
-- Name: step_type; Type: TYPE; Schema: public; Owner: ale
--

CREATE TYPE public.step_type AS ENUM (
    'correctness',
    'optimization'
);


ALTER TYPE public.step_type OWNER TO ale;

--
-- Name: test_case_type; Type: TYPE; Schema: public; Owner: ale
--

CREATE TYPE public.test_case_type AS ENUM (
    'code_sample',
    'stdin_stdout',
    'diagram'
);


ALTER TYPE public.test_case_type OWNER TO ale;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: ale
--

CREATE TYPE public.user_role AS ENUM (
    'student',
    'admin',
    'assistant',
    'professor'
);


ALTER TYPE public.user_role OWNER TO ale;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_settings; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.ai_settings (
    id integer NOT NULL,
    provider character varying(32) NOT NULL,
    model character varying(200) NOT NULL,
    base_url character varying(500) DEFAULT ''::character varying NOT NULL,
    api_key_encrypted text DEFAULT ''::text NOT NULL,
    key_hint character varying(32) DEFAULT ''::character varying NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_by uuid
);


ALTER TABLE public.ai_settings OWNER TO ale;

--
-- Name: ai_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: ale
--

CREATE SEQUENCE public.ai_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ai_settings_id_seq OWNER TO ale;

--
-- Name: ai_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ale
--

ALTER SEQUENCE public.ai_settings_id_seq OWNED BY public.ai_settings.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO ale;

--
-- Name: assignment_attempts; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.assignment_attempts (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    started_at timestamp without time zone DEFAULT now() NOT NULL,
    ends_at timestamp without time zone,
    finished_at timestamp without time zone,
    ip character varying(64) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE public.assignment_attempts OWNER TO ale;

--
-- Name: assignment_tasks; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.assignment_tasks (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    task_id uuid NOT NULL,
    points double precision DEFAULT '10'::double precision NOT NULL,
    "order" integer DEFAULT 0 NOT NULL,
    variant_group integer
);


ALTER TABLE public.assignment_tasks OWNER TO ale;

--
-- Name: assignments; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.assignments (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    title character varying(300) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    kind character varying(20) DEFAULT 'lab'::character varying NOT NULL,
    group_id uuid,
    opens_at timestamp without time zone,
    due_at timestamp without time zone,
    allow_late boolean DEFAULT false NOT NULL,
    late_penalty integer DEFAULT 0 NOT NULL,
    published boolean DEFAULT false NOT NULL,
    created_by uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    ai_mode character varying(10) DEFAULT 'full'::character varying NOT NULL,
    hint_limit integer DEFAULT 3 NOT NULL,
    exam boolean DEFAULT false NOT NULL,
    duration_minutes integer,
    allowed_ips text DEFAULT ''::text NOT NULL,
    results_visibility character varying(10) DEFAULT 'full'::character varying NOT NULL,
    scores_after_publish boolean DEFAULT false NOT NULL,
    grades_published boolean DEFAULT false NOT NULL,
    review_threshold integer DEFAULT 85 NOT NULL,
    improve_limit integer DEFAULT 2 NOT NULL,
    category character varying(10),
    editor_checks boolean DEFAULT true NOT NULL,
    practice_for character varying(10)
);


ALTER TABLE public.assignments OWNER TO ale;

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.attendance (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    status character varying(10) NOT NULL,
    updated_by uuid,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.attendance OWNER TO ale;

--
-- Name: code_comments; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.code_comments (
    id uuid NOT NULL,
    submission_id uuid NOT NULL,
    line integer NOT NULL,
    body text NOT NULL,
    author_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    path character varying(500) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE public.code_comments OWNER TO ale;

--
-- Name: course_groups; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.course_groups (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    language character varying(2)
);


ALTER TABLE public.course_groups OWNER TO ale;

--
-- Name: course_materials; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.course_materials (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    section character varying(10) DEFAULT 'lecture'::character varying NOT NULL,
    title character varying(300) NOT NULL,
    week integer,
    "position" integer DEFAULT 0 NOT NULL,
    published boolean DEFAULT true NOT NULL,
    file_name character varying(255) NOT NULL,
    file_type character varying(100) NOT NULL,
    file_size integer NOT NULL,
    has_preview boolean DEFAULT false NOT NULL,
    created_by uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.course_materials OWNER TO ale;

--
-- Name: course_members; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.course_members (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(20) DEFAULT 'student'::character varying NOT NULL,
    group_id uuid,
    joined_at timestamp without time zone DEFAULT now() NOT NULL,
    role_locked boolean DEFAULT false NOT NULL
);


ALTER TABLE public.course_members OWNER TO ale;

--
-- Name: courses; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.courses (
    id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(300) NOT NULL,
    semester character varying(100) DEFAULT ''::character varying NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    join_code character varying(20) NOT NULL,
    join_enabled boolean DEFAULT true NOT NULL,
    archived boolean DEFAULT false NOT NULL,
    created_by uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    language character varying(2) DEFAULT 'mk'::character varying NOT NULL,
    grading jsonb DEFAULT '{}'::jsonb NOT NULL,
    reminders_enabled boolean DEFAULT true NOT NULL,
    reminder_hours integer DEFAULT 24 NOT NULL,
    subject_id uuid,
    final_grades jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.courses OWNER TO ale;

--
-- Name: diagram_uploads; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.diagram_uploads (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid NOT NULL,
    file_name character varying(255) DEFAULT ''::character varying NOT NULL,
    file_type character varying(100) DEFAULT ''::character varying NOT NULL,
    data bytea NOT NULL,
    reading text DEFAULT ''::text NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.diagram_uploads OWNER TO ale;

--
-- Name: elective_choices; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.elective_choices (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    subject_id uuid NOT NULL,
    semester integer NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.elective_choices OWNER TO ale;

--
-- Name: elective_plans; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.elective_plans (
    user_id uuid NOT NULL,
    confirmed_at timestamp without time zone
);


ALTER TABLE public.elective_plans OWNER TO ale;

--
-- Name: elective_requests; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.elective_requests (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    remove_subject_id uuid NOT NULL,
    remove_semester integer NOT NULL,
    add_subject_id uuid NOT NULL,
    add_semester integer NOT NULL,
    reason text,
    status character varying(12) DEFAULT 'pending'::character varying NOT NULL,
    admin_note text,
    created_at timestamp without time zone,
    decided_at timestamp without time zone,
    decided_by uuid
);


ALTER TABLE public.elective_requests OWNER TO ale;

--
-- Name: email_deliveries; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.email_deliveries (
    id uuid NOT NULL,
    email_id uuid NOT NULL,
    user_id uuid,
    address character varying(255) NOT NULL,
    lang character varying(2) DEFAULT 'mk'::character varying NOT NULL,
    status character varying(10) DEFAULT 'queued'::character varying NOT NULL,
    error text DEFAULT ''::text NOT NULL,
    sent_at timestamp without time zone
);


ALTER TABLE public.email_deliveries OWNER TO ale;

--
-- Name: emails; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.emails (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    assignment_id uuid,
    kind character varying(20) NOT NULL,
    audience character varying(10) DEFAULT 'students'::character varying NOT NULL,
    group_id uuid,
    subject_mk character varying(300) DEFAULT ''::character varying NOT NULL,
    body_mk text DEFAULT ''::text NOT NULL,
    subject_en character varying(300) DEFAULT ''::character varying NOT NULL,
    body_en text DEFAULT ''::text NOT NULL,
    status character varying(10) DEFAULT 'draft'::character varying NOT NULL,
    created_by uuid,
    approved_by uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    sent_at timestamp without time zone,
    recipients integer DEFAULT 0 NOT NULL,
    failed integer DEFAULT 0 NOT NULL,
    attachment_name character varying(255) DEFAULT ''::character varying NOT NULL,
    attachment_type character varying(100) DEFAULT ''::character varying NOT NULL,
    attachment bytea
);


ALTER TABLE public.emails OWNER TO ale;

--
-- Name: events; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.events (
    id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    kind character varying(16) NOT NULL,
    operation character varying(32) NOT NULL,
    ok boolean DEFAULT true NOT NULL,
    duration_ms integer DEFAULT 0 NOT NULL,
    provider character varying(32) DEFAULT ''::character varying NOT NULL,
    model character varying(200) DEFAULT ''::character varying NOT NULL,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    prog_language character varying(16) DEFAULT ''::character varying NOT NULL,
    error text DEFAULT ''::text NOT NULL,
    request_id character varying(64) DEFAULT ''::character varying NOT NULL,
    user_id uuid,
    task_id uuid,
    session_id uuid,
    extra jsonb DEFAULT '{}'::jsonb NOT NULL,
    course_id uuid
);


ALTER TABLE public.events OWNER TO ale;

--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: ale
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.events_id_seq OWNER TO ale;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ale
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: exam_events; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.exam_events (
    id integer NOT NULL,
    assignment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid,
    kind character varying(20) NOT NULL,
    detail text DEFAULT ''::text NOT NULL,
    ip character varying(64) DEFAULT ''::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.exam_events OWNER TO ale;

--
-- Name: exam_events_id_seq; Type: SEQUENCE; Schema: public; Owner: ale
--

CREATE SEQUENCE public.exam_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.exam_events_id_seq OWNER TO ale;

--
-- Name: exam_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ale
--

ALTER SEQUENCE public.exam_events_id_seq OWNED BY public.exam_events.id;


--
-- Name: lti_contexts; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_contexts (
    id uuid NOT NULL,
    platform_id uuid NOT NULL,
    context_id character varying(255) NOT NULL,
    deployment_id character varying(255) DEFAULT ''::character varying NOT NULL,
    label character varying(255) DEFAULT ''::character varying NOT NULL,
    title character varying(500) DEFAULT ''::character varying NOT NULL,
    course_id uuid,
    lineitems_url character varying(500) DEFAULT ''::character varying NOT NULL,
    ags_scopes jsonb DEFAULT '[]'::jsonb NOT NULL,
    memberships_url character varying(500) DEFAULT ''::character varying NOT NULL,
    last_roster_sync timestamp without time zone,
    last_grade_sync timestamp without time zone,
    created_at timestamp without time zone
);


ALTER TABLE public.lti_contexts OWNER TO ale;

--
-- Name: lti_line_items; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_line_items (
    id uuid NOT NULL,
    context_id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    url character varying(500) NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.lti_line_items OWNER TO ale;

--
-- Name: lti_nonces; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_nonces (
    nonce character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL
);


ALTER TABLE public.lti_nonces OWNER TO ale;

--
-- Name: lti_platforms; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_platforms (
    id uuid NOT NULL,
    name character varying(200) DEFAULT 'Moodle'::character varying NOT NULL,
    issuer character varying(500) NOT NULL,
    client_id character varying(200) NOT NULL,
    deployment_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    auth_login_url character varying(500) NOT NULL,
    auth_token_url character varying(500) NOT NULL,
    jwks_url character varying(500) NOT NULL,
    link_by_email boolean DEFAULT true NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.lti_platforms OWNER TO ale;

--
-- Name: lti_registrations; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_registrations (
    token character varying(64) NOT NULL,
    name character varying(200) DEFAULT 'Moodle'::character varying NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    platform_id uuid,
    created_by uuid
);


ALTER TABLE public.lti_registrations OWNER TO ale;

--
-- Name: lti_tool_keys; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_tool_keys (
    kid character varying(64) NOT NULL,
    private_pem_encrypted text NOT NULL,
    public_jwk jsonb NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.lti_tool_keys OWNER TO ale;

--
-- Name: lti_users; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.lti_users (
    id uuid NOT NULL,
    platform_id uuid NOT NULL,
    sub character varying(255) NOT NULL,
    user_id uuid NOT NULL,
    last_launch_at timestamp without time zone
);


ALTER TABLE public.lti_users OWNER TO ale;

--
-- Name: material_files; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.material_files (
    material_id uuid NOT NULL,
    data bytea NOT NULL,
    preview bytea
);


ALTER TABLE public.material_files OWNER TO ale;

--
-- Name: reminder_log; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.reminder_log (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    sent_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reminder_log OWNER TO ale;

--
-- Name: session_steps; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.session_steps (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    step_number integer NOT NULL,
    title character varying(500) NOT NULL,
    description text NOT NULL,
    step_type public.step_type DEFAULT 'correctness'::public.step_type NOT NULL,
    status public.step_status DEFAULT 'pending'::public.step_status NOT NULL,
    agent_feedback text DEFAULT ''::text NOT NULL,
    why text DEFAULT ''::text NOT NULL,
    tip text DEFAULT ''::text NOT NULL
);


ALTER TABLE public.session_steps OWNER TO ale;

--
-- Name: sessions; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid NOT NULL,
    status public.session_status DEFAULT 'in_progress'::public.session_status NOT NULL,
    current_step integer DEFAULT 0 NOT NULL,
    current_code text DEFAULT ''::text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    solution_no integer DEFAULT 1 NOT NULL,
    approach text DEFAULT ''::text NOT NULL,
    alternatives jsonb DEFAULT '[]'::jsonb NOT NULL
);


ALTER TABLE public.sessions OWNER TO ale;

--
-- Name: step_attempts; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.step_attempts (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    step_id uuid NOT NULL,
    code text NOT NULL,
    submitted_at timestamp without time zone DEFAULT now() NOT NULL,
    passed boolean DEFAULT false NOT NULL,
    feedback text DEFAULT ''::text NOT NULL
);


ALTER TABLE public.step_attempts OWNER TO ale;

--
-- Name: subjects; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.subjects (
    id uuid NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    name_en character varying(200) DEFAULT ''::character varying NOT NULL,
    semester integer,
    languages jsonb DEFAULT '[]'::jsonb NOT NULL,
    icon character varying(40) DEFAULT 'book-open'::character varying NOT NULL,
    color character varying(9) DEFAULT '#2747C9'::character varying NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    elective boolean DEFAULT false NOT NULL,
    finki_code character varying(20)
);


ALTER TABLE public.subjects OWNER TO ale;

--
-- Name: submission_files; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.submission_files (
    submission_id uuid NOT NULL,
    data bytea NOT NULL
);


ALTER TABLE public.submission_files OWNER TO ale;

--
-- Name: submissions; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.submissions (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    code text NOT NULL,
    passed integer NOT NULL,
    total integer NOT NULL,
    score double precision NOT NULL,
    late boolean DEFAULT false NOT NULL,
    submitted_at timestamp without time zone DEFAULT now() NOT NULL,
    status character varying(10) DEFAULT 'done'::character varying NOT NULL,
    results jsonb,
    attempts integer DEFAULT 0 NOT NULL,
    error text DEFAULT ''::text NOT NULL,
    started_at timestamp without time zone,
    finished_at timestamp without time zone,
    file_name character varying(255) DEFAULT ''::character varying NOT NULL,
    file_type character varying(100) DEFAULT ''::character varying NOT NULL,
    file_size integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.submissions OWNER TO ale;

--
-- Name: task_files; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.task_files (
    task_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    content_type character varying(100) NOT NULL,
    size integer NOT NULL,
    data bytea NOT NULL,
    uploaded_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.task_files OWNER TO ale;

--
-- Name: task_grades; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.task_grades (
    id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    adjust double precision DEFAULT '0'::double precision NOT NULL,
    override double precision,
    comment text DEFAULT ''::text NOT NULL,
    graded_by uuid,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    rubric_scores jsonb
);


ALTER TABLE public.task_grades OWNER TO ale;

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.tasks (
    id uuid NOT NULL,
    title character varying(500) NOT NULL,
    description text NOT NULL,
    starter_code text DEFAULT ''::text NOT NULL,
    model_solution text DEFAULT ''::text NOT NULL,
    language character varying(50) DEFAULT 'cpp'::character varying NOT NULL,
    created_by uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    is_public boolean DEFAULT true NOT NULL,
    kind character varying(12) DEFAULT 'code'::character varying NOT NULL,
    content_lang character varying(2) DEFAULT 'en'::character varying NOT NULL,
    translations jsonb DEFAULT '{}'::jsonb NOT NULL,
    rubric jsonb DEFAULT '[]'::jsonb NOT NULL,
    subject_id uuid,
    generated_for uuid
);


ALTER TABLE public.tasks OWNER TO ale;

--
-- Name: test_cases; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.test_cases (
    id uuid NOT NULL,
    task_id uuid NOT NULL,
    type public.test_case_type NOT NULL,
    test_code text DEFAULT ''::text NOT NULL,
    stdin text DEFAULT ''::text NOT NULL,
    expected_output text NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    "order" integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.test_cases OWNER TO ale;

--
-- Name: user_ai_keys; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.user_ai_keys (
    user_id uuid NOT NULL,
    provider character varying(32) NOT NULL,
    model character varying(120) DEFAULT ''::character varying NOT NULL,
    base_url character varying(500) DEFAULT ''::character varying NOT NULL,
    api_key_encrypted text NOT NULL,
    key_hint character varying(40) DEFAULT ''::character varying NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_ai_keys OWNER TO ale;

--
-- Name: user_profiles; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.user_profiles (
    user_id uuid NOT NULL,
    avatar bytea,
    avatar_type character varying(30) DEFAULT ''::character varying NOT NULL,
    title character varying(120) DEFAULT ''::character varying NOT NULL,
    bio text DEFAULT ''::text NOT NULL,
    office character varying(120) DEFAULT ''::character varying NOT NULL,
    consultation_hours character varying(300) DEFAULT ''::character varying NOT NULL,
    website character varying(300) DEFAULT ''::character varying NOT NULL,
    index_number character varying(30) DEFAULT ''::character varying NOT NULL,
    study_program character varying(200) DEFAULT ''::character varying NOT NULL,
    study_year integer,
    show_email boolean DEFAULT true NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    email_reminders boolean DEFAULT true NOT NULL
);


ALTER TABLE public.user_profiles OWNER TO ale;

--
-- Name: users; Type: TABLE; Schema: public; Owner: ale
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    role public.user_role DEFAULT 'student'::public.user_role NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    auth_provider character varying(20) DEFAULT 'password'::character varying NOT NULL,
    avatar_version integer
);


ALTER TABLE public.users OWNER TO ale;

--
-- Name: ai_settings id; Type: DEFAULT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.ai_settings ALTER COLUMN id SET DEFAULT nextval('public.ai_settings_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: exam_events id; Type: DEFAULT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.exam_events ALTER COLUMN id SET DEFAULT nextval('public.exam_events_id_seq'::regclass);


--
-- Data for Name: ai_settings; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.ai_settings (id, provider, model, base_url, api_key_encrypted, key_hint, updated_at, updated_by) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.alembic_version (version_num) FROM stdin;
20261105_logs
\.


--
-- Data for Name: assignment_attempts; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.assignment_attempts (id, assignment_id, user_id, started_at, ends_at, finished_at, ip) FROM stdin;
\.


--
-- Data for Name: assignment_tasks; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.assignment_tasks (id, assignment_id, task_id, points, "order", variant_group) FROM stdin;
59056a23-eac9-45ef-91f5-892340191e66	089909f0-fa20-414b-9e04-d9050da3f825	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	10	0	\N
800d222f-7180-4c99-b96f-63d8eef3b510	14266a6f-132a-41e9-b4ae-a372a89f0cb1	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	10	0	\N
\.


--
-- Data for Name: assignments; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.assignments (id, course_id, title, description, kind, group_id, opens_at, due_at, allow_late, late_penalty, published, created_by, created_at, ai_mode, hint_limit, exam, duration_minutes, allowed_ips, results_visibility, scores_after_publish, grades_published, review_threshold, improve_limit, category, editor_checks, practice_for) FROM stdin;
089909f0-fa20-414b-9e04-d9050da3f825	747dcf96-61e0-4096-b127-0e6fc42d14ae	Лабораториска вежба1 - низи		lab	\N	2026-10-28 10:52:00	2026-10-30 23:00:00	t	20	t	a6e4546c-b906-4a1a-9229-e10633019f6d	2026-10-28 10:53:48.994395	full	3	f	\N		full	f	f	85	2	\N	t	\N
14266a6f-132a-41e9-b4ae-a372a89f0cb1	747dcf96-61e0-4096-b127-0e6fc42d14ae	Колоквиум 1		exam	\N	2026-10-28 11:08:00	2026-11-06 23:00:00	f	0	t	788e299a-5aed-4d68-84cd-de6b55ff5369	2026-10-28 11:09:38.485834	full	3	t	90		full	f	t	85	2	\N	t	\N
\.


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.attendance (id, assignment_id, user_id, status, updated_by, updated_at) FROM stdin;
\.


--
-- Data for Name: code_comments; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.code_comments (id, submission_id, line, body, author_id, created_at, path) FROM stdin;
\.


--
-- Data for Name: course_groups; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.course_groups (id, course_id, name, language) FROM stdin;
\.


--
-- Data for Name: course_materials; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.course_materials (id, course_id, section, title, week, "position", published, file_name, file_type, file_size, has_preview, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: course_members; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.course_members (id, course_id, user_id, role, group_id, joined_at, role_locked) FROM stdin;
c13e3fc3-036c-46ea-8cca-bcfbb03991a9	747dcf96-61e0-4096-b127-0e6fc42d14ae	92485f51-e2ab-4aea-9b03-720c1a4f4421	student	\N	2026-10-27 23:47:56.250714	t
ef410dcf-05dc-4e78-8c52-08e5fee2192e	747dcf96-61e0-4096-b127-0e6fc42d14ae	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	student	\N	2026-10-28 10:47:35.941173	t
80e6da70-4383-416b-9a34-c905a20c8267	747dcf96-61e0-4096-b127-0e6fc42d14ae	426bbbba-3b70-4a0a-b950-21978ec3ab3f	teacher	\N	2026-10-28 10:48:02.417319	t
e082be38-e4f8-4caf-99c5-d8cb8cb330e9	747dcf96-61e0-4096-b127-0e6fc42d14ae	a6e4546c-b906-4a1a-9229-e10633019f6d	lab	\N	2026-10-28 10:48:24.689866	t
08ea13d0-c6f1-4820-b169-7a70d549342f	747dcf96-61e0-4096-b127-0e6fc42d14ae	788e299a-5aed-4d68-84cd-de6b55ff5369	assistant	\N	2026-10-28 10:48:37.79588	t
\.


--
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.courses (id, code, name, semester, description, join_code, join_enabled, archived, created_by, created_at, language, grading, reminders_enabled, reminder_hours, subject_id, final_grades) FROM stdin;
747dcf96-61e0-4096-b127-0e6fc42d14ae	F23L3S118	Континуирана интеграција и испорака (DevOps)	2026/27		6GW24ZS	t	f	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:45:46.407252	mk	{"rules": [{"type": "max_missed_labs", "value": 1, "enabled": false}, {"type": "min_labs_signature", "value": 50.0, "enabled": false}, {"type": "min_colloquium", "value": 50.0, "enabled": false}, {"type": "k1_exempt_qualifying", "value": 80.0, "enabled": false}, {"type": "signature_for_exam", "value": null, "enabled": false}], "weights": {"k1": 40.0, "k2": 40.0, "exam": 0.0, "labs": 20.0, "homework": 0.0}, "thresholds": [50.0, 60.0, 70.0, 80.0, 90.0]}	t	24	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	{"ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2": {"at": "2026-10-28T11:13:59.019767Z", "by": "426bbbba-3b70-4a0a-b950-21978ec3ab3f", "grade": 7}}
\.


--
-- Data for Name: diagram_uploads; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.diagram_uploads (id, user_id, task_id, file_name, file_type, data, reading, created_at) FROM stdin;
\.


--
-- Data for Name: elective_choices; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.elective_choices (id, user_id, subject_id, semester, created_at) FROM stdin;
\.


--
-- Data for Name: elective_plans; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.elective_plans (user_id, confirmed_at) FROM stdin;
ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	2026-10-28 11:16:44.535601
\.


--
-- Data for Name: elective_requests; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.elective_requests (id, user_id, remove_subject_id, remove_semester, add_subject_id, add_semester, reason, status, admin_note, created_at, decided_at, decided_by) FROM stdin;
\.


--
-- Data for Name: email_deliveries; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.email_deliveries (id, email_id, user_id, address, lang, status, error, sent_at) FROM stdin;
\.


--
-- Data for Name: emails; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.emails (id, course_id, assignment_id, kind, audience, group_id, subject_mk, body_mk, subject_en, body_en, status, created_by, approved_by, created_at, sent_at, recipients, failed, attachment_name, attachment_type, attachment) FROM stdin;
b0be4c14-7da5-4cdd-9287-05a64aaea35d	747dcf96-61e0-4096-b127-0e6fc42d14ae	089909f0-fa20-414b-9e04-d9050da3f825	announcement	students	\N	[F23L3S118] Објавена е нова активност: Лабораториска вежба1 - низи	Почитувани студенти,\n\nВо предметот F23L3S118 — Континуирана интеграција и испорака (DevOps) е објавена „Лабораториска вежба1 - низи“.\nРок: сабота, 31 октомври 2026, 00:00.\n\nЗадачите се достапни на: http://localhost:3000/assignments/089909f0-fa20-414b-9e04-d9050da3f825\n\nПоздрав,\ndemo.laborant	[F23L3S118] New assignment: Лабораториска вежба1 - низи	Dear students,\n\n“Лабораториска вежба1 - низи” has been published in F23L3S118 — Континуирана интеграција и испорака (DevOps).\nDeadline: Saturday, 31 October 2026, 00:00.\n\nYou can find the tasks at: http://localhost:3000/assignments/089909f0-fa20-414b-9e04-d9050da3f825\n\nBest regards,\ndemo.laborant	draft	a6e4546c-b906-4a1a-9229-e10633019f6d	\N	2026-10-28 10:53:49.004116	\N	0	0			\N
28a87c82-18dd-4083-9500-5221f3e9e957	747dcf96-61e0-4096-b127-0e6fc42d14ae	14266a6f-132a-41e9-b4ae-a372a89f0cb1	announcement	students	\N	[F23L3S118] Објавена е нова активност: Колоквиум 1	Почитувани студенти,\n\nВо предметот F23L3S118 — Континуирана интеграција и испорака (DevOps) е објавена „Колоквиум 1“.\nРок: сабота, 7 ноември 2026, 00:00.\n\nЗадачите се достапни на: http://localhost:3000/assignments/14266a6f-132a-41e9-b4ae-a372a89f0cb1\n\nПоздрав,\ndemo.asistent	[F23L3S118] New assignment: Колоквиум 1	Dear students,\n\n“Колоквиум 1” has been published in F23L3S118 — Континуирана интеграција и испорака (DevOps).\nDeadline: Saturday, 07 November 2026, 00:00.\n\nYou can find the tasks at: http://localhost:3000/assignments/14266a6f-132a-41e9-b4ae-a372a89f0cb1\n\nBest regards,\ndemo.asistent	draft	788e299a-5aed-4d68-84cd-de6b55ff5369	\N	2026-10-28 11:09:38.492829	\N	0	0			\N
755f3f50-2339-4929-a37d-282b462ef1a9	747dcf96-61e0-4096-b127-0e6fc42d14ae	14266a6f-132a-41e9-b4ae-a372a89f0cb1	grades	students	\N	[F23L3S118] Објавени се поените: Колоквиум 1	Почитувани студенти,\n\nПоените и коментарите за „Колоквиум 1“ се објавени. Можете да ги видите на: http://localhost:3000/assignments/14266a6f-132a-41e9-b4ae-a372a89f0cb1\n\nПоздрав,\ndemo.asistent	[F23L3S118] Grades published: Колоквиум 1	Dear students,\n\nThe points and comments for “Колоквиум 1” have been published. You can see them at: http://localhost:3000/assignments/14266a6f-132a-41e9-b4ae-a372a89f0cb1\n\nBest regards,\ndemo.asistent	draft	788e299a-5aed-4d68-84cd-de6b55ff5369	\N	2026-10-28 11:10:16.689592	\N	0	0			\N
55699ee0-4b82-47e7-ac6d-7fbd169da4a3	747dcf96-61e0-4096-b127-0e6fc42d14ae	14266a6f-132a-41e9-b4ae-a372a89f0cb1	gradesheet	staff	\N	[F23L3S118] Листа со оцени по „Колоквиум 1“	Во прилог е листата со оцени за F23L3S118 — Континуирана интеграција и испорака (DevOps) по „Колоквиум 1“, со статусот на секој студент (потпис, право на полагање, предлог оценка).\n\nПредметот: http://localhost:3000/courses/747dcf96-61e0-4096-b127-0e6fc42d14ae?tab=grades	[F23L3S118] Grade sheet after “Колоквиум 1”	Attached is the grade sheet for F23L3S118 — Континуирана интеграција и испорака (DevOps) after “Колоквиум 1”, with each student's standing (signature, exam eligibility, proposed grade).\n\nCourse: http://localhost:3000/courses/747dcf96-61e0-4096-b127-0e6fc42d14ae?tab=grades	draft	788e299a-5aed-4d68-84cd-de6b55ff5369	\N	2026-10-28 11:10:16.691425	\N	0	0			\N
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.events (id, created_at, kind, operation, ok, duration_ms, provider, model, input_tokens, output_tokens, prog_language, error, request_id, user_id, task_id, session_id, extra, course_id) FROM stdin;
1	2026-10-28 10:55:54.449166	ai	next_step	t	3539	openai	gpt-4o	1588	205	c		f55fd691b08740d1	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{}	\N
2	2026-10-28 10:56:40.639276	ai	evaluate	t	1760	openai	gpt-4o	806	109	c		ec5c7c7330c3453b	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
3	2026-10-28 10:56:58.063797	ai	evaluate	t	1944	openai	gpt-4o	838	103	c		333a87648b1c4213	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
4	2026-10-28 10:56:58.14526	tests	run_tests	t	69			0	0	c		333a87648b1c4213	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{"total": 3, "passed": 0, "compile_errors": 0}	\N
5	2026-10-28 10:57:00.668005	ai	next_step	t	2511	openai	gpt-4o	1724	223	c		333a87648b1c4213	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
6	2026-10-28 10:57:26.257594	ai	evaluate	t	2462	openai	gpt-4o	866	146	c		175daac3e68e495f	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
7	2026-10-28 10:58:01.861943	ai	evaluate	t	2380	openai	gpt-4o	889	107	c		ae6c5cd47e924f12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
8	2026-10-28 10:58:01.942754	tests	run_tests	t	67			0	0	c		ae6c5cd47e924f12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{"total": 3, "passed": 3, "compile_errors": 0}	\N
9	2026-10-28 10:58:03.16808	ai	next_step	t	1213	openai	gpt-4o	1726	42	c		ae6c5cd47e924f12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
10	2026-10-28 10:58:03.918625	ai	alternatives	t	733	openai	gpt-4o	837	13	c		ae6c5cd47e924f12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	f7261bed-d68d-429f-a5c9-736114f2cced	{}	\N
11	2026-10-28 10:58:25.59611	tests	run_tests	t	55			0	0	c		f786b82347a84fbb	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{"total": 1, "passed": 0, "compile_errors": 0}	\N
12	2026-10-28 10:58:39.955897	tests	run_tests	t	107			0	0	c		4c9af9a572344f3e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{"total": 3, "passed": 3, "compile_errors": 0}	\N
13	2026-10-28 10:58:53.993051	ai	visualize	t	7561	openai	gpt-4o	1572	1116	c		ec6427951f87452e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{}	\N
14	2026-10-28 10:59:15.413806	ai	visualize	t	3284	openai	gpt-4o	1556	428	c		84695fe6481d4d12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{}	\N
15	2026-10-28 10:59:34.930632	tests	run_tests	t	64			0	0	c		e95c53b6d5224a34	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{"total": 3, "passed": 3, "compile_errors": 0}	\N
16	2026-10-28 10:59:40.078807	tests	run_tests	t	99			0	0	c		cf01fe442ccc4d38	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{"total": 3, "passed": 3, "compile_errors": 0}	\N
17	2026-10-28 10:59:42.365666	ai	task_improve	t	2274	openai	gpt-4o	608	226	c		cf01fe442ccc4d38	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	\N	{}	\N
18	2026-10-28 11:00:51.06569	ai	next_step	t	2468	openai	gpt-4o	2633	147	usecase		a08547f732ed49f2	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	\N	{}	\N
19	2026-10-28 11:01:06.01256	ai	evaluate	t	1859	openai	gpt-4o	854	116	usecase		4de683955f134579	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
20	2026-10-28 11:01:06.025011	tests	diagram_checks	t	0			0	0	usecase		4de683955f134579	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 1}	\N
21	2026-10-28 11:01:08.030878	ai	next_step	t	1992	openai	gpt-4o	3126	151	usecase		4de683955f134579	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
22	2026-10-28 11:01:55.385306	ai	evaluate	t	1948	openai	gpt-4o	937	116	usecase		5307d75701784bf2	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
23	2026-10-28 11:01:55.398095	tests	diagram_checks	t	0			0	0	usecase		5307d75701784bf2	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 2}	\N
24	2026-10-28 11:01:57.448225	ai	next_step	t	2042	openai	gpt-4o	3178	168	usecase		5307d75701784bf2	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
25	2026-10-28 11:02:17.627366	ai	evaluate	t	1559	openai	gpt-4o	1000	89	usecase		229b396af31744cf	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
26	2026-10-28 11:02:17.643947	tests	diagram_checks	t	0			0	0	usecase		229b396af31744cf	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 3}	\N
27	2026-10-28 11:02:20.623837	ai	next_step	t	2970	openai	gpt-4o	3217	195	usecase		229b396af31744cf	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
28	2026-10-28 11:02:46.492369	ai	evaluate	t	1562	openai	gpt-4o	1066	103	usecase		70fdcc88b2044cd1	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
29	2026-10-28 11:02:53.797762	ai	evaluate	t	1394	openai	gpt-4o	1066	100	usecase		1dfa4046bd0f4a6b	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
30	2026-10-28 11:02:53.813269	tests	diagram_checks	t	0			0	0	usecase		1dfa4046bd0f4a6b	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 4}	\N
31	2026-10-28 11:02:56.508365	ai	next_step	t	2684	openai	gpt-4o	3265	183	usecase		1dfa4046bd0f4a6b	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
32	2026-10-28 11:03:14.742889	ai	evaluate	t	1505	openai	gpt-4o	1128	91	usecase		5579a97f77d54440	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
33	2026-10-28 11:03:14.758016	tests	diagram_checks	t	0			0	0	usecase		5579a97f77d54440	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 5}	\N
34	2026-10-28 11:03:17.096046	ai	next_step	t	2327	openai	gpt-4o	3318	173	usecase		5579a97f77d54440	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
35	2026-10-28 11:03:46.153378	ai	evaluate	t	2380	openai	gpt-4o	1205	104	usecase		cb2a06dda70c49f8	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
36	2026-10-28 11:03:46.169127	tests	diagram_checks	t	0			0	0	usecase		cb2a06dda70c49f8	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 6}	\N
37	2026-10-28 11:03:48.264328	ai	next_step	t	2083	openai	gpt-4o	3363	166	usecase		cb2a06dda70c49f8	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
38	2026-10-28 11:04:05.582108	ai	evaluate	t	1576	openai	gpt-4o	1254	104	usecase		da6519a255194772	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
39	2026-10-28 11:04:05.594063	tests	diagram_checks	t	0			0	0	usecase		da6519a255194772	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{"total": 13, "passed": 7}	\N
40	2026-10-28 11:04:07.691266	ai	next_step	t	2086	openai	gpt-4o	3412	181	usecase		da6519a255194772	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	{}	\N
41	2026-10-28 11:05:40.496968	ai	next_step	t	2466	openai	gpt-4o	1703	180	git		0d15a8fbcbe043e9	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	7deda453-9f15-447d-893c-6a1efcbe2b29	\N	{}	\N
42	2026-10-28 11:05:55.992262	ai	evaluate	t	1828	openai	gpt-4o	837	94	git		f98a9934574e485e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	7deda453-9f15-447d-893c-6a1efcbe2b29	31be6474-7471-4f59-8dda-100ed793ebfd	{}	\N
43	2026-10-28 11:05:56.115817	tests	run_tests	t	112			0	0	git		f98a9934574e485e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	7deda453-9f15-447d-893c-6a1efcbe2b29	31be6474-7471-4f59-8dda-100ed793ebfd	{"total": 5, "passed": 0, "compile_errors": 0}	\N
44	2026-10-28 11:05:58.87836	ai	next_step	t	2748	openai	gpt-4o	1814	198	git		f98a9934574e485e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	7deda453-9f15-447d-893c-6a1efcbe2b29	31be6474-7471-4f59-8dda-100ed793ebfd	{}	\N
45	2026-10-28 11:06:39.551094	ai	next_step	t	2384	openai	gpt-4o	1710	188	git		aa9332f32a214b12	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	\N	{}	\N
46	2026-10-28 11:07:08.284482	ai	evaluate	t	1388	openai	gpt-4o	810	110	git		43f50622ba5e40a2	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
51	2026-10-28 11:07:35.222031	tests	run_tests	t	238			0	0	git		c1bcf2d476394fa9	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{"total": 5, "passed": 5, "compile_errors": 0}	\N
47	2026-10-28 11:07:20.575356	ai	evaluate	t	1243	openai	gpt-4o	834	88	git		2dc0b881c9f34ef1	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
49	2026-10-28 11:07:23.380947	ai	next_step	t	2642	openai	gpt-4o	1813	178	git		2dc0b881c9f34ef1	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
54	2026-10-28 11:07:43.644813	tests	run_tests	t	239			0	0	git		40ad8b8a5873442a	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	\N	{"total": 5, "passed": 5, "compile_errors": 0}	\N
48	2026-10-28 11:07:20.72351	tests	run_tests	t	134			0	0	git		2dc0b881c9f34ef1	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{"total": 5, "passed": 2, "compile_errors": 0}	\N
50	2026-10-28 11:07:34.969915	ai	evaluate	t	1289	openai	gpt-4o	873	95	git		c1bcf2d476394fa9	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
52	2026-10-28 11:07:36.396951	ai	next_step	t	1159	openai	gpt-4o	1809	38	git		c1bcf2d476394fa9	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
53	2026-10-28 11:07:37.089283	ai	alternatives	t	675	openai	gpt-4o	831	13	git		c1bcf2d476394fa9	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	71a9062b-cca6-4076-8170-e055eff7a6a7	{}	\N
55	2026-11-07 14:22:23.578099	activity	login	t	0			0	0			da1e395a4f4b46e6	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	\N	\N	{"method": "password"}	\N
56	2026-11-07 14:23:59.394497	activity	login	t	0			0	0			077e2de5a6e74919	a6e4546c-b906-4a1a-9229-e10633019f6d	\N	\N	{"method": "password"}	\N
\.


--
-- Data for Name: exam_events; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.exam_events (id, assignment_id, user_id, task_id, kind, detail, ip, created_at) FROM stdin;
\.


--
-- Data for Name: lti_contexts; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_contexts (id, platform_id, context_id, deployment_id, label, title, course_id, lineitems_url, ags_scopes, memberships_url, last_roster_sync, last_grade_sync, created_at) FROM stdin;
\.


--
-- Data for Name: lti_line_items; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_line_items (id, context_id, assignment_id, url, created_at) FROM stdin;
\.


--
-- Data for Name: lti_nonces; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_nonces (nonce, expires_at) FROM stdin;
\.


--
-- Data for Name: lti_platforms; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_platforms (id, name, issuer, client_id, deployment_ids, auth_login_url, auth_token_url, jwks_url, link_by_email, active, created_at) FROM stdin;
\.


--
-- Data for Name: lti_registrations; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_registrations (token, name, expires_at, used_at, platform_id, created_by) FROM stdin;
\.


--
-- Data for Name: lti_tool_keys; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_tool_keys (kid, private_pem_encrypted, public_jwk, active, created_at) FROM stdin;
dd35800b02c9df80	gAAAAABq4dlkrXFBhiwvhJXddxwFBMDdDQz24T3kLO5pXTi3zTMpE2iq5PRm8MsIOFfiG7V000zD9ZQuKTKhO-LVHvmLkaPkhu3dDvgARVvGIgM0hFAgwS1rsP2OpA-w4frzP1S1bp-yGnseHu6cnetLsgxGmolOFTeeOZs6nbL0PB_Su8bmSGCd0B9xZ5iIYGa7R1BzI97UPc4lmPe9eOcfq825owPEZXvHWVk3TwIN4by9lHw_13M3-hcxLnqrkRvUmsv1hkcT4tC7QhYVTHEHp74XDVQy3Gqf5Tv6VdUxbNytvd4kZplYRJc5h49blDE2Tr4Tt5G4BOZO_n-1vsT0X_79l5f-gYqXNqjpiHiS4p41v3HQOC58Edkj_7TB-JzNsZP6ALUDI0axWBlNnvIktbJQW2xd4Scs4lb6yUNT0ejQXcDGfotDAdyp2g87IH_EYYkqT6kSyuobQv3JV3IXlBlvQ8m3zqt4XeMO3kLa18hsuUhAj8MTv_TXU2XFRH9_KISuzfN8Z1UhBGpQb8GHDzt7mLeDrhez451i4vSbfJRZ9WqOdJJxVNL88agBoFjLuXqJvRrjRTAuwO3X0RIsY0nywPeXolGLSU0x9uf1ifpOihf-ilQ2H5-PwvvwcQ3ccOZeKgoyJHa8d02obOkA7-N8zkaShWw94CQM4GVuGPK0_zawt1orCiyXyBCK6_m_bFRbVsfQdR4VXEoG6zjYHd2c9qwu5aqddJrqh6KEimUlxSHfC7eAhBnrPSOW4alpk94n08wSh07F5E4fXSPFrRn3x5uQmNPDwfHwyRn7L1O50lrP8HGH-NHaLnVZ2bwsizHrIX0DHLv_NjGMXUWN23IfNxlGOsByssrzcsmZfLh8tAXsj12rsAUPq9V8dUKv-4cJhKk9aBk6sqnZ9X33lMSkZoIV_LTuyCjBPo4Ju2oMlo7RhOrosn5SO1XJjBDIl25x3UwzanOvGr0C-Cq7Fp_NQFDU0izIpaUdF2BsponNB4AFFtCg6yH0GFt4XqhPuJhSixZJDDtentsxqf9VrpdL-n78ljB1HEyRmoThCmM-NPFByx5psRUJu87KPQaZsyO3DX5P45aqHQjzjFOIL6B3WH8JdBDILAjU6maIaXc08vN3Xz-lelf1GhQQA-NMeCqiV9q0YRPpVvZq5LjDMPm7Q-z_vyIv8U4ULNGnkAGRLL6IBAqU5k0Xrq5v5TMtnCOp11LMnSrvDFlVflkVNVA8JSYUCnMhxyRadSZHpyPy_4QkeeKkrYKiW4j7nssiDB5m2UXKV-M3_QUtXXISQ9nN6E3SEmRE-yKFVwG3O1gUx_GrF_gB3kPS4zkjrFTyeZdxBaLjUnBaFQWk3Xoq_B8W8BYosPToRW8dwiG-pz18csij7BA811kiDT1zLraoxNrMZpO1FW4Fni6-CXk8bza9xfliHwRFfaufbm5f1idnj3IaWqcFpq0-q7gWmhbElrnKRoXPXDX1igaRwKRXqGPEIx-NYWR1pIUFB96gZ4_3JPTq0XoaS7p37YooLHXc0cZ3jdoXwW_PnNXrx5Zv8pWC-fBdFFyHTkhDNYDW6tN37bOHcKEGP8Yc06KppLRcYCmN07YyvJodalYN8YPGO08cPiGVZavGiE0pjBwvIry0YwQPczLtfQRLi5VsqTrMPzWA9fIW3EuJkiI3cDEsGpA3JZ13vollP0LuqFZy2ODEBgV49bIH6-_uozh0kad2Lp8oWILIDOSTcd6oKaDxHKsjq_KqBdAcebJPdxu1SVznmkw9bMN9JmW8fTBS0w-TrbYnS96KyIF1OQos54h-mEN51911uTzqKvwFMIS7jSNduukIjmuwRcH0-2SzP5K5opt32izdkZMQPYhO_0TIpUXhHHk66TjrJAthpewhdT4e30ek7zAdJNgj9glZVb0vgUr5zTf26OS1xQ-814JSG6fBns-l1T9i2RoV4EvQZe-pRRZm1HM2Amw65jhXLAFJiEi04y9JalYeiLNOWLAkDACm2suUof4F9crDbrW2NQjhQqEDg4TCH0T96R6BVQBVLjLAP4xrsqGwPd9XId_Mdd6CAL2NQESDMnOMo7L5zHt1qI-pMtlywTnj-BSso84-ZL8lfA6KnZhNiBj_PGuNZzHpWKn85mCZmi5YFelh3ydoFlMSjcOh5cWd7O-gKLcVvGpZnfFSFRbX4BNPd7EXfa4t-G6uiATncrlvtWPlgrZdq2V9YE9lTcAeAXtEgeqvA0xvvOt1Tcjekjy_1m-mzmjmH6FJXDC-KV2UrGL2oGQOZ_pt4V1AylS5--VIjY4A6wNH5K1T9ELrNlvZtT-47Yom2DsDiSRmWRnNngXILGMf0-VrDz8=	{"e": "AQAB", "n": "xC3KBYUtNYPRnweNfGCGztHWwQrGjo6d1QxyfQbKGww53LRndhJxOBdimgkHULO3GgCg1QaN5snlUbPQ_i02DS6QrB5FWm-8IT28YW1vaOaEknQwvnQDvOUeSN2VUEoWXMNYxof_cmsIX63vzsB-JCC4XRU3Xesat5hg6PM2F1SK5SAqg1pZbrjeKBXVI7CzQCEMYyWz5-VQ_-J53EOMJyCngfw4xhBGtEIZS2DXPnXn5WiNwZhn24QyoOqN29JF8UPAyTpN-aPhF8W6q5jWSqsp2pqMMzgXcU16_5cvGsxRbRWxWllSSAhspK-9IRJlCjuMuPHeIrQae1mEct1fFQ", "alg": "RS256", "kid": "dd35800b02c9df80", "kty": "RSA", "use": "sig"}	t	2026-10-28 11:15:48.799446
\.


--
-- Data for Name: lti_users; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.lti_users (id, platform_id, sub, user_id, last_launch_at) FROM stdin;
\.


--
-- Data for Name: material_files; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.material_files (material_id, data, preview) FROM stdin;
\.


--
-- Data for Name: reminder_log; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.reminder_log (id, assignment_id, user_id, sent_at) FROM stdin;
\.


--
-- Data for Name: session_steps; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.session_steps (id, session_id, step_number, title, description, step_type, status, agent_feedback, why, tip) FROM stdin;
122d501c-4d16-4a45-a5dd-d80f7c2379c2	f7261bed-d68d-429f-a5c9-736114f2cced	0	Декларирај низа за складирање на броевите	Декларирај целобројна низа со големина 1000 за да ги складираш прочитаните броеви. Оваа низа ќе ја користиме за чување на броевите што ќе ги внесеме подоцна.	correctness	completed	Успешно декларираше целобројна низа 'a' со големина 1000. Ова овозможува складирање на најмногу 1000 броја, што ги исполнува барањата на задачата за вчитување и чување на броеви, бидејќи 'n' може да биде најмногу 1000.	Низата ќе ни овозможи да ги зачуваме броевите што се внесуваат и подоцна да ги испечатиме во обратен редослед. Ова е основа за обработка на податоците и за исписот.	Во C, честопати се користат фиксни големини на низите кога е дадено максималното ограничување на елементите, како што е случајот тука со максимум 1000 броја.
eb48c2d3-10d5-4d77-b6ce-70b444f13acd	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	1	Додај системска граница 'Студентски сервис'	Додај квадрат околу случаите на употреба, означувајќи го како 'Студентски сервис'.	correctness	completed	Одлично! Ги постави системските граници 'Студентски сервис' во вашиот use case дијаграм. Ова го постигнуваш со додавање на елемент од типот 'system' кој го опкружува случаите на употреба, означувајќи ја границата на системот, што е важен концепт за разбирање кој дел од функционалноста е опфатен со системот.	Системската граница го претставува опсегот на апликацијата и ги вклучува сите случаи на употреба кои се дел од студентскиот сервис.	Системската граница се користи за да се одвои деловите кои се под контрола на системот од надворешниот свет.
c093d898-af34-4392-b0f4-a17bf8ba14e5	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	2	Додај актер за референт	Додај актер во дијаграмот кој ќе го претставува референтот. Тој е одговорен за внесување на оценките.	correctness	completed	Одлично! Имаш додадено актер за референт во дијаграмот, што е важно бидејќи референтот е клучен за внесување на оценките. Моделот ја претставува неговата улога како дел од системот, што го исполнува бараното во задачата.	Актерите во use case дијаграмот претставуваат ентитети кои учествуваат во системот. Референтот е важен актер бидејќи има специфична улога во процесот на внесување оценки.	Во UML use case дијаграм, актери се обично надворешни ентитети кои комуницираат со системот, како корисници или други системи.
0869bbbe-64e9-460a-9788-e32ac4524cd6	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	7	Додади случај на употреба 'Внес на оценки'	Додади нов случај на употреба наречен 'Внес на оценки' во дијаграмот со линија на асоцијација кон актерот 'Референт'.	correctness	active		Случајот на употреба 'Внес на оценки' е важен за да се овозможи референтот да ги внесе оценките во системот. Ова е клучна функционалност на студентскиот сервис.	Случаите на употреба треба да опишуваат различни активности во системот, при што секој случај претставува одредена задача што треба да биде поддржана.
0d26d7bc-640c-4def-9dd4-f94b52a4b4da	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	5	Додај случај на употреба „Плаќање со картичка“	Додади нов случај на употреба со име „Плаќање со картичка“ во дијаграмот, внатре во границата на системот „Студентски сервис“.	correctness	completed	Добра работа! Го додаде случајот на употреба „Плаќање со картичка“ и го смести внатре во границата на системот „Студентски сервис“. Ова ви овозможува да го прикажете павилното проширување на функционалностите со опционалното плаќање, што е дел од барањата.	Ова е потребно за да овозможиш функционалност која Студентот може да ја користи како проширување при пријавување на испит.	Случајот на употреба кој користи `«extend»` ја покажува опционалноста на дополнителната акција во основниот случај на употреба.
c848379c-692c-4917-bbde-1e08da123de7	31be6474-7471-4f59-8dda-100ed793ebfd	1	Додади и иницијализирај README.md и .gitignore	Создади ги датотеките README.md и .gitignore со соодветната содржина и увери се дека тие се следат од Git. Користи соодветните команди за да ги додадеш во складиштето.	correctness	active		Овој чекор е потребен за да се обезбедат потребните датотеки во складиштето пред да се направи првиот commit. Тоа гарантира дека README.md и .gitignore ќе бидат вклучени во промените при 'Initial commit'.	Кога додаваш датотеки, можеш да користиш 'git add' за специфични датотеки или за сите одредени со шаблон.
d51b4001-7f24-4543-95db-08e09d251dc4	f7261bed-d68d-429f-a5c9-736114f2cced	1	Испечати броевите во обратен редослед	Додади код во програмата којшто ќе ги испечати броевите во обратен редослед. Користи for јамка за да ги читаш елементите од низата 'a' од крајот кон почеток и печати го секој елемент.	correctness	completed	Одлична работа! Кодот успешно печати броеви во обратен редослед. Го користиш for јамката за да се движиш од крајот на низата 'a' кон почеток, притоа печатејќи секој елемент. Успешно постигна условите на чекорот и правилно справуваш со интервалите меѓу броевите.	Целта на оваа задача е да ги испечати внесените броеви во обратно редослед соодветно барањето во задачата. Промената ќе помогне да се заврши задачата со испечатување на броевите во точниот редослед.	Кога печатиш броеви во C, може да користиш услов во printf() за да одржиш правилно форматирање, како печатење на празно место меѓу броевите освен после последниот.
3eee9d43-0465-4e02-bfd1-95acdf26175b	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	0	Додај актер за студент	Додај нов актер наречен 'Студент' во use case дијаграмот.	correctness	completed	Одлично, го додадовте актерот 'Студент' во use case дијаграмот! Ова е важно бидејќи претставува корисник кој ќе ги користи функционалностите на студентскиот сервис, како што е пријавување на испит и прегледување на оценките. Внесениот актер има валидно `id` и правилна позиционираност што може да биде важно за визуелната презентација.	Студентот е клучен актер во системот што ги користи случаите на употреба како 'пријавување на испит' и 'преглед на оценки'.	Актерите во UML се претставени како човечки фигури и тие го покажуваат интерфејсот со кој корисниците или надворешните системи комуницираат со апликацијата.
ae65101c-70b8-43a0-9ec3-95b104cdc6dd	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	3	Додај случај на употреба „Пријава на испит“	Додај случај на употреба наречен „Пријава на испит“ во границата на системот „Студентски сервис“.	correctness	completed	Одлично! Го додадовте случајот на употреба „Пријава на испит“ во рамките на системот „Студентски сервис“. Ова е потребно бидејќи точно го претставува сценариото каде студентот се пријавува на испит, што е еден од основните делови на системот за студентски услуги.	Случајот на употреба „Пријава на испит“ е централен дел од функционалноста што студентите го користат во студентскиот сервис. Тој е основен дел од дијаграмот кој треба да е поврзан со актерот 'Студент'.	Секогаш дефинирајте ги случаите на употреба како глагол-реченици кои јасно опишуваат некоја акција или процес.
b1a2593d-cbc5-4418-a994-1b742fa95477	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	4	Додади случај на употреба „Најава“ во дијаграмот	Додади нов случај на употреба со име „Најава“ внатре во границите на системот Студентски сервис.	correctness	completed	Одлично! Успешно додадовте случај на употреба „Најава“ во границите на системот Студентски сервис. Ова е правилно бидејќи овозможува спојување на овој случај со функционално значење како дел од процесот 'Пријава на испит'.	Случајот на употреба „Најава“ е потребен како дел од процесот за пријава на испит и служи како зависност од типот „include“ во други случаи на употреба.	Случајот на употреба „Најава“ е фундаментален бидејќи овозможува автентикација на студентите, и може да биде поврзуван со други случаи на употреба преку '«include»'.
950e96a8-0050-4e11-af94-e8dc0913b1ca	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	6	Додади случај на употреба „Преглед на оценки“	Додади нов случај на употреба во дијаграмот со име „Преглед на оценки“ во рамките на системската граница 'Студентски сервис'.	correctness	completed	Одлично си ја завршил работата! Го додаде случајот на употреба „Преглед на оценки“ во рамките на системската граница 'Студентски сервис'. Ова го постигнуваш со додавање на нов јазол од типот 'usecase' со соодветно име, што точно го прикажува овој аспект на системот.	Случајот на употреба 'Преглед на оценки' му овозможува на студентот да ги прегледа своите оценки, што е дел од функционалностите на студентскиот сервис.	Секој случај на употреба претставува специфична функционалност на системот која е значајна за крајниот корисник.
8f18917d-ad99-4dd4-96e1-b08714760044	31be6474-7471-4f59-8dda-100ed793ebfd	0	Иницијализирај празно складиште во тековната папка	Треба да иницијализирате празно гит складиште во тековната папка користејќи ја командата `git init`.	correctness	completed	Честитки, успешно иницијализиравте празно гит складиште во тековната папка со командата `git init`. Ова значи дека gит сега го следи тековниот директориум за какви било верзиони на датотеки и го подготвува за понатамошно следење на промените.	Иницијализацијата на празно складиште е првиот чекор за да можете да го следите развојот на проектот и да почнете да додавате датотеки во истото.	Кога ќе ја извршите командата `git init`, во тековната папка ќе се креира скриена папка `.git`, што значи дека папката е гит складиште.
dff49266-9200-4576-af5c-f3e83f5c31f2	71a9062b-cca6-4076-8170-e055eff7a6a7	0	Креирај гранка feature/login	Користи ја командата git switch за да создадеш нова гранка наречена feature/login и да се префрлиш на неа.	correctness	completed	Одлично! Успешно ја користиш командата `git switch -c feature/login` за да создадеш нова гранка и автоматски да се префрлиш на неа. Ова овозможува создавање на посебен работен простор за различните карактеристики што ги развиваш.	Со оваа акција се формира нова гранка во складиштето каде ќе се прават измените поврзани со логин функционалноста. Ова е многу корисно бидејќи овозможува изолирано развивање на специфични функционалности без да се менува главната гранка.	Гранките во Гит се користат за да се овозможи паралелен развој на код и полесно управување со различни верзии на проектот.
348a26c4-f359-4a04-b091-a72b468dd2ef	71a9062b-cca6-4076-8170-e055eff7a6a7	1	Додај датотека login.txt во feature/login	Додај ја датотеката login.txt во индексот на Git користејќи ја командата git add за да ја подготвиш за комитирање.	correctness	completed	Одлично! Користеше `git add login.txt` за да ја додадеш датотеката `login.txt` во индексот на Git. Тоа значи дека датотеката е подготвена за комитирање со следниот `git commit` и ќе биде вклучена во историскиот запис на складиштето.	Откако ќе ја додадеш датотеката login.txt во индексот, ќе можеш да направиш commit на тие промени на гранката feature/login, што е потребно пред да се префрлиш назад на main и да почнеш процесот на спојување.	Командата git add се користи за додавање на нови или изменети датотеки во индексот, што им овозможува да бидат вклучени во следниот commit.
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.sessions (id, user_id, task_id, status, current_step, current_code, created_at, updated_at, solution_no, approach, alternatives) FROM stdin;
c3c21eb0-d528-4d4f-ac95-731141c9b3ad	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	fed45caf-a572-4634-bdfc-389d091fe71c	in_progress	7	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 526,\n   "y": 327,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0a0nbknk",\n   "name": "Најава",\n   "type": "usecase",\n   "x": 586,\n   "y": 251,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0aiqxka6",\n   "name": "Плаќање со картичка",\n   "type": "usecase",\n   "x": 524,\n   "y": 183,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0b538wac",\n   "name": "Преглед на оценки",\n   "type": "usecase",\n   "x": 414,\n   "y": 374,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:00:48.589371	2026-10-28 11:04:07.700574	1		[]
71a9062b-cca6-4076-8170-e055eff7a6a7	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	47a54cea-9655-42a8-9dc5-e78f5d827b55	completed	1	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\ngit switch -c feature/login\necho login > login.txt\ngit add login.txt\ngit commit -m 'Add login'\ngit switch main\ngit merge --no-ff feature/login -m 'Merge feature/login'	2026-10-28 11:06:37.160582	2026-10-28 11:07:36.403543	1		[]
31be6474-7471-4f59-8dda-100ed793ebfd	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	7deda453-9f15-447d-893c-6a1efcbe2b29	in_progress	1	git init\n	2026-10-28 11:05:38.022165	2026-10-28 11:05:58.885411	1		[]
f7261bed-d68d-429f-a5c9-736114f2cced	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	completed	1	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) {\n        scanf("%d", &a[i]);\n    }\n    for (int i = n - 1; i >= 0; i--) {\n        printf("%d", a[i]);\n        if (i > 0) {\n            printf(" ");\n        }\n    }\n    printf("\\n");\n    return 0;\n}	2026-10-28 10:55:50.687226	2026-10-28 10:58:03.176197	1		[]
\.


--
-- Data for Name: step_attempts; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.step_attempts (id, session_id, step_id, code, submitted_at, passed, feedback) FROM stdin;
119ed06e-ac37-48b2-a362-f0420a0b34ff	f7261bed-d68d-429f-a5c9-736114f2cced	122d501c-4d16-4a45-a5dd-d80f7c2379c2	#include <stdio.h>\n\nint main(void) {\n    int n;\n    scanf("%d", &n);\n    return 0;\n}\n	2026-10-28 10:56:40.648902	f	Не успеавте да ја постигнете целта на овој чекор. Вашиот код недостасува декларација на целобројна низа со големина 1000, која е потребна за чување на влезните броеви. Ова е важно за да можете подоцна да работите со овие броеви и да ги прикажете во обратен редослед.
83bf7dc1-276c-4fbc-b31a-dd3842ed214b	f7261bed-d68d-429f-a5c9-736114f2cced	122d501c-4d16-4a45-a5dd-d80f7c2379c2	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) {\n        scanf("%d", &a[i]);\n    }\n    return 0;\n}	2026-10-28 10:56:58.072968	t	Успешно декларираше целобројна низа 'a' со големина 1000. Ова овозможува складирање на најмногу 1000 броја, што ги исполнува барањата на задачата за вчитување и чување на броеви, бидејќи 'n' може да биде најмногу 1000.
90594ab9-50f5-44e7-b5d6-023eba90a8f0	f7261bed-d68d-429f-a5c9-736114f2cced	d51b4001-7f24-4543-95db-08e09d251dc4	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) {\n        scanf("%d", &a[i]);\n    }\n    for (int i = n; i >= 0; i--) {\n        printf("%d ", a[i]);\n    }\n    return 0;\n}	2026-10-28 10:57:26.26473	f	Кодот не ги печати броевите во обратен редослед правилно бидејќи фор јамката се започнува од 'n' наместо 'n-1' и продолжува до 'i >= 0'. Ова предизвикува обид за пристап до непостоечкиот елемент 'a[n]', што води до неочекувано однесување. За да го решиш овој проблем, започни ја јамката од 'i = n - 1' и користи 'i >= 0' како услов за продолжување на јамката.
918bfcbf-cfe3-420c-a35a-cf36ba65052e	f7261bed-d68d-429f-a5c9-736114f2cced	d51b4001-7f24-4543-95db-08e09d251dc4	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) {\n        scanf("%d", &a[i]);\n    }\n    for (int i = n - 1; i >= 0; i--) {\n        printf("%d", a[i]);\n        if (i > 0) {\n            printf(" ");\n        }\n    }\n    printf("\\n");\n    return 0;\n}	2026-10-28 10:58:01.872474	t	Одлична работа! Кодот успешно печати броеви во обратен редослед. Го користиш for јамката за да се движиш од крајот на низата 'a' кон почеток, притоа печатејќи секој елемент. Успешно постигна условите на чекорот и правилно справуваш со интервалите меѓу броевите.
cb65dc8b-b09a-4f4f-aa9f-81742df49de4	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	3eee9d43-0465-4e02-bfd1-95acdf26175b	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 476,\n   "y": 60,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:01:06.02121	t	Одлично, го додадовте актерот 'Студент' во use case дијаграмот! Ова е важно бидејќи претставува корисник кој ќе ги користи функционалностите на студентскиот сервис, како што е пријавување на испит и прегледување на оценките. Внесениот актер има валидно `id` и правилна позиционираност што може да биде важно за визуелната презентација.
e957a843-08cd-4449-83cf-869891e57e05	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	eb48c2d3-10d5-4d77-b6ce-70b444f13acd	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  }\n ],\n "edges": []\n}	2026-10-28 11:01:55.394119	t	Одлично! Ги постави системските граници 'Студентски сервис' во вашиот use case дијаграм. Ова го постигнуваш со додавање на елемент од типот 'system' кој го опкружува случаите на употреба, означувајќи ја границата на системот, што е важен концепт за разбирање кој дел од функционалноста е опфатен со системот.
70413a9e-3023-43dc-a96b-ac70b640f8fe	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	c093d898-af34-4392-b0f4-a17bf8ba14e5	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:02:17.637552	t	Одлично! Имаш додадено актер за референт во дијаграмот, што е важно бидејќи референтот е клучен за внесување на оценките. Моделот ја претставува неговата улога како дел од системот, што го исполнува бараното во задачата.
18517b66-b12f-4898-ad29-a4f5a37c1db1	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	ae65101c-70b8-43a0-9ec3-95b104cdc6dd	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 587,\n   "y": 554,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:02:46.502156	f	Случајот на употреба 'Пријава на испит' е додаден, но не се наоѓа во границата на системот 'Студентски сервис'. Важно е овој случај на употреба да биде внатре во границата на системот за да се укаже на тоа дека е дел од функционалноста на студентскиот сервис.
6ac84faf-9bba-4148-a19a-053829c1ecc4	71a9062b-cca6-4076-8170-e055eff7a6a7	348a26c4-f359-4a04-b091-a72b468dd2ef	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\ngit switch -c feature/login\necho login > login.txt\ngit add login.txt\ngit commit -m 'Add login'\ngit switch main\ngit merge --no-ff feature/login -m 'Merge feature/login'	2026-10-28 11:07:34.980339	t	Одлично! Користеше `git add login.txt` за да ја додадеш датотеката `login.txt` во индексот на Git. Тоа значи дека датотеката е подготвена за комитирање со следниот `git commit` и ќе биде вклучена во историскиот запис на складиштето.
2e21bd5c-324a-4589-a260-1e201499032d	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	ae65101c-70b8-43a0-9ec3-95b104cdc6dd	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 526,\n   "y": 327,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:02:53.807663	t	Одлично! Го додадовте случајот на употреба „Пријава на испит“ во рамките на системот „Студентски сервис“. Ова е потребно бидејќи точно го претставува сценариото каде студентот се пријавува на испит, што е еден од основните делови на системот за студентски услуги.
85991f35-352d-4ca0-ab13-e836f7e27135	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	0d26d7bc-640c-4def-9dd4-f94b52a4b4da	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 526,\n   "y": 327,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0a0nbknk",\n   "name": "Најава",\n   "type": "usecase",\n   "x": 586,\n   "y": 251,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0aiqxka6",\n   "name": "Плаќање со картичка",\n   "type": "usecase",\n   "x": 524,\n   "y": 183,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:03:46.163782	t	Добра работа! Го додаде случајот на употреба „Плаќање со картичка“ и го смести внатре во границата на системот „Студентски сервис“. Ова ви овозможува да го прикажете павилното проширување на функционалностите со опционалното плаќање, што е дел од барањата.
0f447e85-7621-4681-9ebf-4911d4578b6d	71a9062b-cca6-4076-8170-e055eff7a6a7	dff49266-9200-4576-af5c-f3e83f5c31f2	git init\necho v1 > app.txt\n	2026-10-28 11:07:08.294137	f	Кодот што го достави ученикот не ја остварува целта на тековниот чекор. За да создадеш нова гранка `feature/login` и да се префрлиш на неа, треба да користиш командата `git switch -c feature/login`. Ова е важно бидејќи ни овозможува да работиме со нова гранка одделено од главната (`main`).
b66984fe-00be-4960-83ca-74a7d4c0e9df	71a9062b-cca6-4076-8170-e055eff7a6a7	dff49266-9200-4576-af5c-f3e83f5c31f2	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\ngit switch -c feature/login\necho login > login.txt\n	2026-10-28 11:07:20.585966	t	Одлично! Успешно ја користиш командата `git switch -c feature/login` за да создадеш нова гранка и автоматски да се префрлиш на неа. Ова овозможува создавање на посебен работен простор за различните карактеристики што ги развиваш.
5ba4000c-ad58-47cd-8ba8-ccfb7d4e31dc	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	b1a2593d-cbc5-4418-a994-1b742fa95477	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 526,\n   "y": 327,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0a0nbknk",\n   "name": "Најава",\n   "type": "usecase",\n   "x": 586,\n   "y": 251,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:03:14.753565	t	Одлично! Успешно додадовте случај на употреба „Најава“ во границите на системот Студентски сервис. Ова е правилно бидејќи овозможува спојување на овој случај со функционално значење како дел од процесот 'Пријава на испит'.
8e07cbdb-e80a-4f64-9b5e-954b6b3df1de	c3c21eb0-d528-4d4f-ac95-731141c9b3ad	950e96a8-0050-4e11-af94-e8dc0913b1ca	{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "nmvs06y52n0b",\n   "name": "Студент",\n   "type": "actor",\n   "x": 442,\n   "y": 190,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs07y65jwl",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 398,\n   "y": 139,\n   "attributes": [],\n   "methods": [],\n   "w": 360,\n   "h": 300\n  },\n  {\n   "id": "nmvs08s6a86e",\n   "name": "Референт",\n   "type": "actor",\n   "x": 281,\n   "y": 462,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs09cubz49",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 526,\n   "y": 327,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0a0nbknk",\n   "name": "Најава",\n   "type": "usecase",\n   "x": 586,\n   "y": 251,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0aiqxka6",\n   "name": "Плаќање со картичка",\n   "type": "usecase",\n   "x": 524,\n   "y": 183,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nmvs0b538wac",\n   "name": "Преглед на оценки",\n   "type": "usecase",\n   "x": 414,\n   "y": 374,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": []\n}	2026-10-28 11:04:05.589457	t	Одлично си ја завршил работата! Го додаде случајот на употреба „Преглед на оценки“ во рамките на системската граница 'Студентски сервис'. Ова го постигнуваш со додавање на нов јазол од типот 'usecase' со соодветно име, што точно го прикажува овој аспект на системот.
67c4f7d0-eccd-4788-bdb7-216050c5dc75	31be6474-7471-4f59-8dda-100ed793ebfd	8f18917d-ad99-4dd4-96e1-b08714760044	git init\n	2026-10-28 11:05:56.000779	t	Честитки, успешно иницијализиравте празно гит складиште во тековната папка со командата `git init`. Ова значи дека gит сега го следи тековниот директориум за какви било верзиони на датотеки и го подготвува за понатамошно следење на промените.
\.


--
-- Data for Name: subjects; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.subjects (id, code, name, name_en, semester, languages, icon, color, description, "position", elective, finki_code) FROM stdin;
0432c1a5-03ba-4113-aed7-46652eb46c94	SI	Софтверско инженерство	Software Engineering	4	["java"]	drafting-compass	#F08C00		5	f	F23L2S029
1eaa5ef5-23c2-47b0-92f1-7c5d9dcb0da9	NP	Напредно програмирање	Advanced Programming	5	["java", "kotlin"]	rocket	#C2255C		10	f	F23L3W140
3f1ec06a-0600-4a27-b37b-e7921c2ba937	VI	Вештачка интелигенција	Artificial Intelligence	4	["python"]	brain	#D6336C		6	f	F23L2S030
4aeca440-512b-4623-8372-2c5cdb48cddd	APS	Алгоритми и податочни структури	Algorithms and Data Structures	3	["python", "java", "cpp", "c"]	git-fork	#0CA678		3	f	F23L2W001
629f33c6-62f8-46c6-8aee-0623706c441f	AOK	Архитектура и организација на компјутери	Computer Architecture and Organization	2	["asm", "c"]	cpu	#495057		2	f	F23L1S003
6af3c09a-d677-48ed-8426-08bc0cd302cc	OOAID	Објектно-ориентирана анализа и дизајн	Object-Oriented Analysis and Design	2	["uml", "usecase", "sequence", "state", "activity", "component", "package", "deployment"]	shapes	#0B7285		7	f	F23L2S015
6bdb8d08-42fd-4b05-862a-3e1124e4d380	MPP	Мобилни платформи и програмирање	Mobile Platforms and Programming	7	["kotlin", "java"]	smartphone	#12B886		17	t	F23L3W129
6e523396-fbbb-4301-8e1d-b9453d9e3a03	DIANS	Дизајн и архитектура на софтвер	Software Design and Architecture	5	["component", "package", "deployment", "uml"]	layers	#E8590C		12	f	F23L3W009
858895d3-de07-4584-a344-e72bb93a4d5d	OS	Оперативни системи	Operating Systems	4	["bash", "c", "java"]	terminal	#343A40		4	f	F23L2S017
9469cc9a-21d5-4aee-a436-a21097e815ff	ISSOK	Имплементација на системи со слободен и отворен код	Implementation of Free and Open Source Systems	7	["php", "web", "postgresql"]	unlock	#40C057		16	t	F23L3W103
9f2089a0-09c0-473a-90a0-891e5bdccd6c	IPNKS	Интернет програмирање на клиентска страна	Client-Side Internet Programming	3	["javascript", "web", "typescript"]	mouse-pointer-click	#F59F00		14	t	F23L2W109
a6937632-a996-41dc-8333-3792261b71e2	OOP	Објектно-ориентирано програмирање	Object-Oriented Programming	2	["cpp", "uml"]	boxes	#7048E8		1	f	F23L1S016
aff098bb-b566-4bab-a216-188f334d956e	PP	Програмски парадигми	Programming Paradigms	7	["prolog", "lisp", "python", "kotlin"]	infinity	#862E9C		11	t	F23L3W038
c6b22b4b-1a01-420e-8637-6414ac355c00	SP	Структурно програмирање	Structured Programming	1	["c", "cpp", "python"]	braces	#2747C9		0	f	F23L1W020
cfdff677-27d5-47fd-80a8-6b4d3df45835	VP	Веб програмирање	Web Programming	5	["java", "web", "javascript", "typescript"]	globe	#1971C2		9	t	F23L3W024
d3e9fc2c-8656-492d-9362-f7c24151b4a3	BP	Бази на податоци	Databases	5	["sql", "postgresql", "er", "relational"]	database	#2B8A3E		8	f	F23L3W004
f3528493-8622-4f52-8c64-8cd55f453dec	IT	Интернет технологии	Internet Technologies	4	["csharp", "web"]	server	#5C7CFA		15	t	F23L2S110
c1e09a60-de84-47eb-9953-e684a1129ec6	F23L1W007	Вовед во компјутерските науки	Introduction to Computer Science	1	["python"]	book-open	#2747C9		19	f	F23L1W007
e4abeed0-dfd0-47ee-a410-3a94255515e1	ONVD	Основи на веб дизајн	Fundamentals of Web Design	6	["web"]	palette	#FF6B6B		13	t	F23L1S146
c45d3083-b08d-4015-b9fb-2bb3e521a80f	F23L1S120	Креативни вештини за решавање проблеми		2	[]	book-open	#7048E8		38	t	F23L1S120
c8093025-7df5-4430-a598-05250124a46f	F23L2W201	Примена на алгоритми и податочни структури	Applied Algorithms and Data Structures	3	["python", "cpp", "java"]	git-fork	#0CA678		43	f	F23L2W201
cffc06a5-f693-4cd1-975a-ea8f78d5226e	F23L2S082	Визуелно програмирање	Visual Programming	4	["csharp"]	mouse-pointer-click	#5C7CFA		56	t	F23L2S082
05912157-a0a9-4444-b0f7-5ca87c3a9602	F23L2S095	Дигитално процесирање на слика		4	[]	palette	#F08C00		59	t	F23L2S095
dea8a3a4-a4eb-4378-9c65-406914d4733b	F23L2S097	Дизајн на алгоритми	Algorithm Design	4	["python", "cpp"]	git-fork	#0CA678		60	t	F23L2S097
d9da804b-b7c2-4377-8d6a-dd7e64add1e5	F23L2S114	Компјутерска графика		4	[]	palette	#F08C00		64	t	F23L2S114
4b4dc4e0-6b5a-45f6-bab7-3e83a4a48d0c	F23L3W008	Вовед во науката за податоци	Introduction to Data Science	5	["python", "sql"]	database	#2B8A3E		69	f	F23L3W008
21fcae57-a610-444c-bd31-60348509e714	F23L3W060	Администрација на системи	System Administration	5	["bash", "git", "dockerfile"]	terminal	#343A40		70	t	F23L3W060
dd183763-5e62-4b38-a13e-7449b6a49432	F23L3W081	Визуелизација		5	[]	palette	#2B8A3E		71	t	F23L3W081
8c658211-1609-45e8-acd0-a92a846b3caa	F23L3W136	Напреден веб дизајн	Advanced Web Design	5	["web", "javascript"]	palette	#FF6B6B		78	t	F23L3W136
0d2bbf21-9f0d-4d5c-a035-c314c6431813	F23L3W142	Обработка на природните јазици		5	[]	book-open	#2B8A3E		79	t	F23L3W142
d3b25fc1-d7d6-4ba4-b889-ee9192c36367	F23L3W037	Паралелно и дистрибуирано процесирање	Parallel and Distributed Processing	5	["c", "java"]	cpu	#495057		81	t	F23L3W037
40e96bb7-4d3b-4d5e-9e5e-b8c005141e44	F23L3W161	Теорија на графови и социјални мрежи		5	[]	sigma	#2B8A3E		85	t	F23L3W161
cc3b3c59-6df5-4005-a899-ce583b75dc27	F23L3S012	Интегрирани системи		6	[]	book-open	#0B7285		87	f	F23L3S012
ef9f4dd4-0577-49f6-a594-272bb5fc7093	F23L3S138	Напредни бази на податоци	Advanced Databases	6	["postgresql", "sql", "er"]	database	#2B8A3E		88	f	F23L3S138
b110ac01-0d95-4c4c-b2b5-3f88ad0145eb	F23L3S019	Софтверски квалитет и тестирање	Software Quality and Testing	6	["java", "python"]	shield	#E8590C		89	f	F23L3S019
06080d7e-1bec-403a-984c-be37edbf262f	F23L3S163	Автоматизирање на процеси во машинско учење	Process Automation with Machine Learning	6	["python"]	brain	#D6336C		90	t	F23L3S163
bc6bd54e-9590-40e5-963c-c63f0be9c5da	F23L3S073	Агентно-базирани системи		6	[]	database	#0B7285		91	t	F23L3S073
5b022077-1522-4ac8-9e10-12b69db4fdca	F23L3S040	Вградливи микропроцесорски системи		6	[]	cpu	#0B7285		93	t	F23L3S040
ff563eb4-93f2-4a3f-ad89-0cc3c0f02cf4	F23L3S153	Вештачка интелигенција за игри		6	[]	brain	#0B7285		94	t	F23L3S153
85ffe809-4f17-44c2-b968-337e4f15343b	F23L3S062	Виртуелизација	Virtualization	6	["dockerfile", "yaml", "bash"]	container	#0B7285		95	t	F23L3S062
3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	F23L3S118	Континуирана интеграција и испорака (DevOps)	Continuous Integration and Delivery (DevOps)	6	["git", "bash", "dockerfile", "yaml", "terraform"]	git-branch	#1864AB		103	t	F23L3S118
8718d662-554b-479c-a6d8-9fe3c85edb33	F23L3S122	Криптографија		6	[]	shield	#0B7285		104	t	F23L3S122
5a967019-a23a-4920-a545-e873dd8762cd	F23L3S036	Машинско учење	Machine Learning	6	["python"]	brain	#D6336C		105	t	F23L3S036
0cf3b1d2-62ea-4896-af33-23552e9c6099	F23L3S039	Основи на теоријата на компјутерските науки		6	[]	book-open	#0B7285		108	t	F23L3S039
4f92063d-3e8e-421a-86a3-404669d77165	F23L3S149	Паралелно програмирање	Parallel Programming	6	["c", "cpp"]	cpu	#495057		109	t	F23L3S149
7eb36b2a-23a5-4db7-9f0f-56ebb7f0c6b6	F23L3S150	Податочно рударење		6	[]	book-open	#0B7285		110	t	F23L3S150
589cdb20-a68c-4e9f-a39f-8a33717f5134	F23L3S155	Сервисно ориентирани софтверски архитектури		6	[]	cpu	#0B7285		114	t	F23L3S155
8998ddee-f5c2-4e1e-8f5c-9750e6272a96	F23L3S157	Складови на податоци и аналитичка обработка	Data Warehouses and OLAP	6	["sql", "postgresql"]	database	#2B8A3E		115	t	F23L3S157
c73de5e7-f195-45ac-accd-74086bf26e65	F23L3W021	Тимски проект	Team Project	7	["git", "yaml", "dockerfile"]	git-branch	#C2255C		119	f	F23L3W021
a9683d8e-ec8c-434e-826a-624ba32718f7	F23L3W074	Администрација на бази податоци	Database Administration	7	["postgresql", "sql", "bash"]	database	#2B8A3E		121	t	F23L3W074
4be86d8e-28e1-47d4-b29b-ebdf22e1995c	F23L3W075	Анализа и дизајн на ИС	Analysis and Design of Information Systems	7	["uml", "er", "usecase"]	drafting-compass	#F08C00		122	t	F23L3W075
0561473d-81be-475d-8738-5021d551cc30	F23L1W121	Блоковски вериги и криптовалути		7	[]	book-open	#C2255C		123	t	F23L1W121
d9b11450-2f58-44c5-a85c-eb2c9359c818	F23L3W079	Веб базирани системи	Web-based Systems	7	["java", "web", "javascript"]	globe	#1971C2		124	t	F23L3W079
2a26d157-2e1d-469e-a079-935a3a2ae8a0	F23L3W085	Вовед во биоинформатиката		7	[]	book-open	#C2255C		125	t	F23L3W085
6cde64f0-ca5a-4e2b-901b-a0fc47b14574	F23L3W089	Вовед во препознавање на облици		7	[]	book-open	#C2255C		127	t	F23L3W089
43e0568d-096a-46ea-a999-a714146bd6b4	F23L3W154	Вовед во рударење на масивни податоци		7	[]	database	#C2255C		128	t	F23L3W154
6ebe5db5-a617-4fc4-ad5f-52a32fe6eae4	F23L3W064	Дистрибуирани системи	Distributed Systems	7	["java", "yaml", "dockerfile"]	network	#1971C2		130	t	F23L3W064
6233c0c2-8f2c-4ccb-a574-1387c8b1a64a	F23L3W098	Дистрибуирано складирање на податоци		7	[]	database	#C2255C		131	t	F23L3W098
dc083065-7b67-4571-8186-7b4ac18444e8	F23L3W108	Интернет на нештата		7	[]	globe	#C2255C		133	t	F23L3W108
82f432dd-e3f4-4dda-b7a0-747952ee05b8	F23L3W162	Квантно пресметување		7	[]	book-open	#C2255C		134	t	F23L3W162
b9d7f154-dd7c-4ce3-8b4e-760673ab565e	F23L3W123	Машинска визија		7	[]	brain	#C2255C		136	t	F23L3W123
9080bb1f-827e-4f14-9a15-62b090f80d67	F23L3W068	Пресметување во облак	Cloud Computing	7	["terraform", "yaml", "dockerfile"]	cloud	#1971C2		143	t	F23L3W068
29d6d90c-9f76-41d9-871d-e82e7ad0fc14	F23L3W152	Програмирање на видео игри	Video Game Programming	7	["python", "csharp"]	bot	#862E9C		144	t	F23L3W152
457f6f4a-0237-49b7-bfc4-8e3b54de3f31	F23L3W048	Софтвер за вградливи системи		7	[]	cpu	#C2255C		147	t	F23L3W048
997c0667-4977-4645-a6c2-3e8ee09ee17b	F23L3S139	Web3 апликации	Web3 Applications	8	["javascript", "typescript"]	globe	#1971C2		151	t	F23L3S139
3de3ae86-87f4-44e7-99f1-b3be6984bef0	F23L3S069	Адаптивни и интерактивни веб информациски системи		8	[]	globe	#495057		152	t	F23L3S069
3c73cd51-d709-4d7a-b291-2ac4abb64ac5	F23L3S078	Биолошки инспирирано пресметување		8	[]	book-open	#495057		153	t	F23L3S078
9bbf5511-1956-4a2a-b65e-ab14b72e0f58	F23L3S080	Веб пребарувачки системи		8	[]	globe	#495057		154	t	F23L3S080
da9cc80f-1dae-4456-b9d8-d26d2a0acc74	F23L3S083	Виртуелна реалност		8	[]	book-open	#495057		155	t	F23L3S083
32e9b913-e208-47e2-9c94-e50d2a9db07e	F23L3S101	Етичко хакирање	Ethical Hacking	8	["bash", "python"]	shield	#C92A2A		158	t	F23L3S101
0f094c83-aa3a-4155-9ba6-ce76bf681116	F23L3S107	Интелигентни системи		8	[]	brain	#495057		160	t	F23L3S107
a345fc15-1045-4922-9d9b-dbb57e8c1525	F23L3S111	Инфраструктурно програмирање	Infrastructure Programming	8	["terraform", "yaml", "dockerfile", "bash", "git"]	cloud	#5F3DC4		161	t	F23L3S111
7bdaa07f-9304-4d5f-9493-57a24989a8b9	F23L3S127	Мобилни апликации	Mobile Applications	8	["kotlin", "java"]	smartphone	#12B886		164	t	F23L3S127
d27f145d-c86f-49ac-91c2-43803ace120e	F23L3S131	Моделирање и симулација		8	[]	book-open	#495057		166	t	F23L3S131
21519c97-fdee-4388-ab9c-6738de0aa8ad	F23L3S141	Неструктурирани бази на податоци		8	[]	database	#495057		168	t	F23L3S141
02c908de-106b-4c89-a04a-bde0a09f2821	F23L3S106	Откривање знаење со длабоко учење		8	[]	graduation-cap	#495057		170	t	F23L3S106
dd1da8c6-1c73-40ae-a75a-d06490169c77	F23L3S112	Програмски јазици и компајлери	Programming Languages and Compilers	8	["python", "c"]	braces	#862E9C		171	t	F23L3S112
2c0ad82f-72ec-48d5-ac0b-b42cad3f6aaa	F23L3S160	Софтверски дефинирани мрежи		8	[]	network	#495057		172	t	F23L3S160
\.


--
-- Data for Name: submission_files; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.submission_files (submission_id, data) FROM stdin;
\.


--
-- Data for Name: submissions; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.submissions (id, assignment_id, task_id, user_id, code, passed, total, score, late, submitted_at, status, results, attempts, error, started_at, finished_at, file_name, file_type, file_size) FROM stdin;
c4321246-b62c-44f8-8844-650efb1675e0	089909f0-fa20-414b-9e04-d9050da3f825	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) {\n        scanf("%d", &a[i]);\n    }\n    for (int i = n - 1; i >= 0; i--) {\n        printf("%d", a[i]);\n        if (i > 0) {\n            printf(" ");\n        }\n    }\n    printf("\\n");\n    return 0;\n}	3	3	10	f	2026-10-28 10:59:34.843434	done	{"staff": [{"type": "stdin_stdout", "error": null, "stdin": "5\\n1 2 3 4 5\\n", "hidden": false, "images": null, "passed": true, "test_code": "", "test_number": 1, "actual_output": "5 4 3 2 1\\n", "expected_output": "5 4 3 2 1\\n"}, {"type": "stdin_stdout", "error": null, "stdin": "1\\n42\\n", "hidden": false, "images": null, "passed": true, "test_code": "", "test_number": 2, "actual_output": "42\\n", "expected_output": "42\\n"}, {"type": "stdin_stdout", "error": null, "stdin": "4\\n-3 0 7 -3\\n", "hidden": true, "images": null, "passed": true, "test_code": "", "test_number": 3, "actual_output": "-3 7 0 -3\\n", "expected_output": "-3 7 0 -3\\n"}], "student": [{"type": "stdin_stdout", "error": null, "stdin": "5\\n1 2 3 4 5\\n", "hidden": false, "images": null, "passed": true, "test_code": "", "test_number": 1, "actual_output": "5 4 3 2 1\\n", "expected_output": "5 4 3 2 1\\n"}, {"type": "stdin_stdout", "error": null, "stdin": "1\\n42\\n", "hidden": false, "images": null, "passed": true, "test_code": "", "test_number": 2, "actual_output": "42\\n", "expected_output": "42\\n"}, {"type": "stdin_stdout", "error": null, "stdin": "", "hidden": true, "images": null, "passed": true, "test_code": "", "test_number": 3, "actual_output": "", "expected_output": ""}]}	1		2026-10-28 10:59:34.849913	2026-10-28 10:59:34.934319			0
\.


--
-- Data for Name: task_files; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.task_files (task_id, name, content_type, size, data, uploaded_at) FROM stdin;
\.


--
-- Data for Name: task_grades; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.task_grades (id, assignment_id, task_id, user_id, adjust, override, comment, graded_by, updated_at, rubric_scores) FROM stdin;
4cfe3199-9314-4d53-8651-7e02cedba74b	089909f0-fa20-414b-9e04-d9050da3f825	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	0	\N		a6e4546c-b906-4a1a-9229-e10633019f6d	2026-10-28 11:11:24.556607	null
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.tasks (id, title, description, starter_code, model_solution, language, created_by, created_at, updated_at, is_public, kind, content_lang, translations, rubric, subject_id, generated_for) FROM stdin;
5b54df3c-259d-41ad-be90-be985d43a701	Најголем збир на делители	Од стандарден влез се чита еден природен број n. Меѓу природните броеви помали од n, да се најде оној чиј што збир на делителите е најголем. Во пресметувањето на збирот на делителите на даден број, да не се зема предвид самиот број.		#include <stdio.h>\n\nint main()\n{\n    int i, n, del, zbir, maks = 0, broj = 1;\n    scanf("%d", &n);\n    for(i = 1; i < n; i++)\n    {\n        zbir = 0;\n        for(del = 1; del <= i/2; del++)\n            if(i % del == 0)\n                zbir += del;\n        if(zbir > maks){\n            maks = zbir;\n            broj = i;\n        }\n    }\n    printf("%d", broj);\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.26523	2026-10-28 11:16:05.265239	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
f24d9543-4edb-4eb0-9de3-46e328b56f2d	Најди го збирот	Од стандарден влез се читаат знаци се додека не се прочита извичник. Во вака внесениот текст се скриени цели броеви (помали од 100\\). Да се напише програма што ќе ги прочита сите знаци и на излез ќе го испечати збирот на сите броеви скриени во текстот.\n\nНапомена: cin во C\\+\\+ ги игнорира празните места (space). За да не ги игнорира потребно е да се додаде noskipws пред читањето на знакот (пр. cin \\>\\> noskipws \\>\\> znak;)		#include <stdio.h>\n\nint main()\n{\n    char znak;\n    short broj = 0;\n    int zbir = 0;\n    while(1)\n    {\n        scanf("%c", &znak);\n        if(znak == '!')\n            break;\n        switch(znak)\n        {\n            case '0': broj = broj*10; break;\n            case '1': broj = broj*10 + 1; break;\n            case '2': broj = broj*10 + 2; break;\n            case '3': broj = broj*10 + 3; break;\n            case '4': broj = broj*10 + 4; break;\n            case '5': broj = broj*10 + 5; break;\n            case '6': broj = broj*10 + 6; break;\n            case '7': broj = broj*10 + 7; break;\n            case '8': broj = broj*10 + 8; break;\n            case '9': broj = broj*10 + 9; break;\n            default:\n                zbir += broj;\n                broj = 0;\n                break;\n        }\n    }\n    zbir += broj;\n    printf("%d", zbir);\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.268647	2026-10-28 11:16:05.26865	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
e2ca494b-a8e9-45ff-879e-72d937b03d7d	Парен еквивалент	Од тастатура се читаат 2 позитивни цели броеви. Доколку се внесе барем еден негативен број или 0 треба да се печати „Invalid input“.\n\nТреба да се определи дали помалиот број “**е парен еквивалент**” од поголемиот број. \n\nЕден број “е парен еквивалент” на друг број, ако и само ако неговите цифри се наоѓаат на парните позиции од другиот број, во истиот редослед. Соодветно да се испечатат пораки „PAREN“ и „NE“. \n\nПозициите треба да се сметаат оддесно\\-налево (најмалку значајната цифра е на позиција 1\\)		#include <stdio.h>\n\nint main() {\n\n  int tmp, pomal, pogolem, c1, c2;\n  int e_par_equ;\n\n  /* Reading errors */\n  if (scanf("%d %d",&pogolem, &pomal) == 2) {\n\n      if (pogolem <= 0 || pomal <= 0) {\n      \tprintf("Invalid input");\n        return 0;\n      }\n\n    /* Swap */\n    if (pomal > pogolem) {\n      tmp=pomal;\n      pomal = pogolem;\n      pogolem = tmp;\n    }\n\n    e_par_equ = 1;\n    while (pomal>0) {\n      c1 = pomal % 10;\n      c2 = (pogolem % 100)/10;\n\n      if (c1 != c2) {\n\t    e_par_equ = 0;\n\t    break;\n      }\n\n      pomal /= 10;\n      pogolem /= 100;\n\n    }\n\n    if (e_par_equ) {\n      printf("PAREN\\n");\n    }\n    else {\n      printf("NE\\n");\n    }\n  }\n  else {\n  \tprintf("Invalid input");\n  }\n\n  return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.271073	2026-10-28 11:16:05.271077	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
4b264492-51c6-4123-ab54-80d2ed44bab7	Парови цели броеви	Да се напише програма во која од стандарден влез прво се внесува еден позитивен цел број z, а потоа последователно се внесуваат парови цели броеви (a, b). Внесувањето на парови цели броеви треба да заврши кога корисникот ќе го внесе парот (0, 0\\). Треба да се пресмета колку пати z е еднаков на збирот на секој внесен пар броеви a и b, како и колкав процент од вкупниот број внесени парови (a, b) даваат збир z (ЗАБЕЛЕШКА: парот (0, 0\\) не се зема во предвид при извршувањето на пресметките!).		#include <stdio.h>\n#include<iostream>\n\nusing namespace std;\n\nint main()\n{\n    int z, a, b, br = 0, n = 0;\n    scanf("%d", &z);\n    do\n    {\n        scanf("%d%d", &a, &b);\n        if(a == 0&&b == 0)\n            break;\n        n++;\n        if(z == a + b)\n            br++;\n    }while(1);\n    printf("Vnesovte %d parovi od broevi chij zbir e %d\\n", br, z);\n    // printf("Procentot na parovi so zbir %d e %f%%", z, 100.0*br/n);\n    cout << "Procentot na parovi so zbir " << z << " e " << 100.0*br/n <<"%";\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.273577	2026-10-28 11:16:05.273581	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
f9c379c6-91f3-4005-9d5a-32a8eb262bec	Плетка	Со помош на знаците ‘@’,'%', и ‘.‘ се формира квадратна слика со „должина“ m (m\\>2\\) која претставува квадрат од знаците '.', впишан во квадрат од знаците @ и %(види примери). За внесено m да се испечати на екран соодветната слика. Внимавајте – не печатете нити еден дополнителен знак, како празно место, непотребен знак за нов ред... Сликата завршува со знак за нов ред. Забелешка: Бидејќи е дадено ограничување за m, во точно решение на задачата не треба да се користи низа/матрица.		#include <stdio.h>\n#include <stdlib.h>\n\nint main()\n{\n    int m,n,i,j;\n    scanf("%d",&m);\n    n=m;\n    for (i=0; i<m; i++)\n    {\n        for (j=0;j<n;j++)\n        if (i>0&&i<m-1&&j>0&&j<n-1)\n            printf(".");\n        else\n            if (j>0&&j<n-1)\n\t\t\t\tprintf("@");\n\t\t\telse\n            \tprintf("%%");\n        printf("\\n");\n    }\n\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.277127	2026-10-28 11:16:05.277132	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
fd196046-62cb-490e-a3ca-3a18829d7905	Line Statistics (Bash)	Write a Bash script that reads lines from standard input and prints three numbers on one line:\nthe number of lines, the number of words and the length of the longest line.	#!/bin/bash\n# TODO\n	#!/bin/bash\nlines=0; words=0; longest=0\nwhile IFS= read -r line || [ -n "$line" ]; do\n  lines=$((lines + 1))\n  set -- $line\n  words=$((words + $#))\n  [ ${#line} -gt $longest ] && longest=${#line}\ndone\necho "$lines $words $longest"\n	bash	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.262584	2026-10-27 21:19:15.390655	t	code	en	{"mk": {"title": "Статистика за редови (Bash)", "description": "Напишете Bash скрипта што чита редови од стандардниот влез и печати три броја во еден ред:\\nбројот на редови, бројот на зборови и должината на најдолгиот ред.\\n"}}	[]	858895d3-de07-4584-a344-e72bb93a4d5d	\N
9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	Навигациско мени (HTML/CSS)	Направете **навигациско мени** за веб-страница на факултет.\n\n**Структура** (во `index.html`):\n- елемент `<nav class="menu">` со листа `<ul>` и **4** ставки `<li>`, во секоја по една врска `<a>` со атрибут `href`:\n  „Почетна“, „Студии“, „Вести“, „Контакт“;\n- врската на тековната страница („Почетна“) има класа `active`;\n- под менито, наслов `<h1>` со текст по ваш избор.\n\n**Изглед** (во `style.css`):\n- ставките на менито се **во ред** (flexbox), листата нема точки (`list-style: none`);\n- позадина на менито: `#1A2233`, врските се бели и **без подвлекување**;\n- активната врска има позадина `#FCC419` и темен текст (`#1A2233`);\n- на екран потесен од **600px** ставките се **една под друга**.\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Мени</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Мени</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <nav class="menu">\n    <ul>\n      <li><a href="index.html" class="active">Почетна</a></li>\n      <li><a href="studii.html">Студии</a></li>\n      <li><a href="vesti.html">Вести</a></li>\n      <li><a href="kontakt.html">Контакт</a></li>\n    </ul>\n  </nav>\n  <h1>Добредојдовте на ФИНКИ</h1>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n.menu {\n  background: #1A2233;\n}\n.menu ul {\n  display: flex;\n  gap: 4px;\n  list-style: none;\n  margin: 0;\n  padding: 8px;\n}\n.menu a {\n  display: block;\n  color: #fff;\n  text-decoration: none;\n  padding: 10px 16px;\n  border-radius: 6px;\n}\n.menu a.active {\n  background: #FCC419;\n  color: #1A2233;\n}\nh1 {\n  padding: 0 16px;\n}\n@media (max-width: 600px) {\n  .menu ul { flex-direction: column; }\n}\n<!-- file: script.js -->\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.38015	2026-10-27 21:19:15.380151	t	code	mk	{"en": {"title": "Navigation menu (HTML/CSS)", "description": "Make a **navigation menu** for a faculty website.\\n\\n**Structure** (`index.html`): a `<nav class=\\"menu\\">` with a `<ul>` of **4** `<li>` items, each with one link `<a href>`:\\n\\"Home\\", \\"Studies\\", \\"News\\", \\"Contact\\"; the link of the current page (\\"Home\\") has the class `active`; under the menu an\\n`<h1>` with any text.\\n\\n**Look** (`style.css`): the items are **in a row** (flexbox), the list has no bullets; menu background `#1A2233`, white\\nlinks **without underline**; the active link has the background `#FCC419` and dark text (`#1A2233`); on screens\\nnarrower than **600px** the items are **one under another**."}}	[]	e4abeed0-dfd0-47ee-a410-3a94255515e1	\N
36932216-3ce4-4e93-91fc-f960b8524d5b	Ценовник со CSS Grid (HTML/CSS)	Направете **ценовник** со три пакети.\n\n**Структура:** `<section class="plans">` со **три** `<article class="plan">`. Секој пакет има:\nнаслов `<h3>`, цена `<p class="price">` (на пр. `9 ден./мес.`), листа `<ul>` со барем **3** можности и врска\n`<a class="btn">` „Избери“. Средниот пакет има и класа `featured`.\n\n**Изглед:**\n- `.plans` е **CSS Grid** со **3 колони** на компјутер и **1 колона** на екран потесен од **700px**, со растојание\n  (`gap`) од `24px`;\n- секој пакет: бела позадина, заоблени агли `12px`, рамка `1px solid #D9DEE7`;\n- `.featured` има рамка `2px solid #2747C9`;\n- `.btn` е син (`#2747C9`) со бел текст, без подвлекување.\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Ценовник</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Ценовник</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <section class="plans">\n    <article class="plan">\n      <h3>Студент</h3>\n      <p class="price">0 ден./мес.</p>\n      <ul><li>5 проекти</li><li>1 GB простор</li><li>Поддршка по е-пошта</li></ul>\n      <a class="btn" href="#">Избери</a>\n    </article>\n    <article class="plan featured">\n      <h3>Про</h3>\n      <p class="price">299 ден./мес.</p>\n      <ul><li>Неограничени проекти</li><li>50 GB простор</li><li>Приоритетна поддршка</li></ul>\n      <a class="btn" href="#">Избери</a>\n    </article>\n    <article class="plan">\n      <h3>Тим</h3>\n      <p class="price">899 ден./мес.</p>\n      <ul><li>10 корисници</li><li>500 GB простор</li><li>Поддршка 24/7</li></ul>\n      <a class="btn" href="#">Избери</a>\n    </article>\n  </section>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\nbody {\n  background: #EEF1F5;\n  padding: 40px 16px;\n}\n.plans {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 24px;\n  max-width: 960px;\n  margin: 0 auto;\n}\n.plan {\n  background: #fff;\n  border-radius: 12px;\n  border: 1px solid #D9DEE7;\n  padding: 24px;\n}\n.plan.featured {\n  border: 2px solid #2747C9;\n}\n.price {\n  font-size: 24px;\n  font-weight: 700;\n}\n.btn {\n  display: inline-block;\n  background: #2747C9;\n  color: #fff;\n  text-decoration: none;\n  padding: 10px 18px;\n  border-radius: 8px;\n}\n@media (max-width: 700px) {\n  .plans { grid-template-columns: 1fr; }\n}\n<!-- file: script.js -->\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.382065	2026-10-27 21:19:15.382066	t	code	mk	{"en": {"title": "Pricing table with CSS Grid (HTML/CSS)", "description": "Make a **pricing table** with three plans.\\n\\n**Structure:** `<section class=\\"plans\\">` with **three** `<article class=\\"plan\\">`; each has an `<h3>` title, a price\\n`<p class=\\"price\\">`, a `<ul>` with at least **3** features and a link `<a class=\\"btn\\">` \\"Choose\\". The middle plan also\\nhas the class `featured`.\\n\\n**Look:** `.plans` is a **CSS Grid** with **3 columns** on a computer and **1 column** on screens narrower than\\n**700px**, with a `24px` gap; each plan: white background, `12px` rounded corners, border `1px solid #D9DEE7`;\\n`.featured` has the border `2px solid #2747C9`; `.btn` is blue (`#2747C9`) with white text, not underlined."}}	[]	e4abeed0-dfd0-47ee-a410-3a94255515e1	\N
89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	Форма за регистрација (HTML/CSS)	Направете **пристапна форма за регистрација**.\n\n**Структура:** `<form id="signup">` со три полиња, секое со своја ознака `<label for="…">`:\n- „Име“ — `<input id="name">`, задолжително;\n- „Е-пошта“ — `<input id="email" type="email">`, задолжително;\n- „Лозинка“ — `<input id="password" type="password">`, задолжително, најмалку **8** знаци (`minlength`);\n\nи копче `<button type="submit">` „Регистрирај се“.\n\n**Изглед:** формата е широка најмногу `360px` и е **центрирана**; ознаките и полињата се **еден под друг**\n(на пр. flexbox во колона); полињата имаат рамка `1px solid #D9DEE7` и заоблени агли `8px`; копчето е зелено\n(`#2B8A3E`) со бел текст.\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Регистрација</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Регистрација</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <form id="signup">\n    <h1>Регистрација</h1>\n    <label for="name">Име</label>\n    <input id="name" name="name" required>\n    <label for="email">Е-пошта</label>\n    <input id="email" name="email" type="email" required>\n    <label for="password">Лозинка</label>\n    <input id="password" name="password" type="password" minlength="8" required>\n    <button type="submit">Регистрирај се</button>\n  </form>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\nbody {\n  background: #EEF1F5;\n  padding: 40px 16px;\n}\n#signup {\n  box-sizing: border-box;\n  display: flex;\n  flex-direction: column;\n  gap: 8px;\n  max-width: 360px;\n  margin: 0 auto;\n  background: #fff;\n  padding: 24px;\n  border-radius: 12px;\n}\n#signup input {\n  border: 1px solid #D9DEE7;\n  border-radius: 8px;\n  padding: 10px 12px;\n  font-size: 15px;\n}\n#signup button {\n  margin-top: 8px;\n  background: #2B8A3E;\n  color: #fff;\n  border: 0;\n  border-radius: 8px;\n  padding: 12px;\n  font-size: 15px;\n}\n<!-- file: script.js -->\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.383866	2026-10-27 21:19:15.383868	t	code	mk	{"en": {"title": "Sign-up form (HTML/CSS)", "description": "Make an **accessible sign-up form**.\\n\\n**Structure:** `<form id=\\"signup\\">` with three fields, each with its own `<label for=\\"…\\">`: \\"Name\\" — `<input id=\\"name\\">`,\\nrequired; \\"E-mail\\" — `<input id=\\"email\\" type=\\"email\\">`, required; \\"Password\\" — `<input id=\\"password\\" type=\\"password\\">`,\\nrequired, at least **8** characters (`minlength`); and a `<button type=\\"submit\\">` \\"Sign up\\".\\n\\n**Look:** the form is at most `360px` wide and **centred**; labels and fields are **one under another**; the fields have\\na `1px solid #D9DEE7` border and `8px` rounded corners; the button is green (`#2B8A3E`) with white text."}}	[]	e4abeed0-dfd0-47ee-a410-3a94255515e1	\N
8685efdd-a1cd-4ae8-a70d-91482a195494	Листа на задачи (HTML/CSS/JS)	Направете **листа на задачи** (to-do).\n\n**Структура:** поле `<input id="new">`, копче `<button id="add">` „Додај“, листа `<ul id="list">` и\n`<p>` со `<span id="count">` — бројот на **незавршени** задачи.\n\n**Однесување** (во `script.js`):\n- клик на „Додај“ додава нова ставка `<li>` со текстот од полето (без празни места на почетокот и крајот) и го празни\n  полето; **празен** текст не се додава;\n- клик на ставка ја означува како завршена (класа `done`); нов клик го враќа назад;\n- `#count` секогаш го покажува бројот на ставки **без** класа `done`.\n\n**Изглед:** завршените ставки се **прецртани** (`text-decoration: line-through`) и сиви (`#868E96`).\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Задачи</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <h1>Мои задачи</h1>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Задачи</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <main class="todo">\n    <h1>Мои задачи</h1>\n    <div class="row">\n      <input id="new" placeholder="Нова задача…" aria-label="Нова задача">\n      <button id="add">Додај</button>\n    </div>\n    <ul id="list"></ul>\n    <p>Останати: <span id="count">0</span></p>\n  </main>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n.todo {\n  max-width: 420px;\n  margin: 40px auto;\n  padding: 0 16px;\n}\n.row {\n  display: flex;\n  gap: 8px;\n}\n#new {\n  flex: 1;\n  padding: 10px;\n  border: 1px solid #D9DEE7;\n  border-radius: 8px;\n}\n#add {\n  background: #2747C9;\n  color: #fff;\n  border: 0;\n  border-radius: 8px;\n  padding: 0 16px;\n}\n#list {\n  list-style: none;\n  padding: 0;\n}\n#list li {\n  padding: 10px 12px;\n  border-bottom: 1px solid #EEF1F5;\n  cursor: pointer;\n}\n#list li.done {\n  text-decoration: line-through;\n  color: #868E96;\n}\n<!-- file: script.js -->\nconst input = document.getElementById('new');\nconst list = document.getElementById('list');\nconst count = document.getElementById('count');\n\nfunction refresh() {\n  count.textContent = list.querySelectorAll('li:not(.done)').length;\n}\n\ndocument.getElementById('add').addEventListener('click', () => {\n  const text = input.value.trim();\n  if (!text) return;\n  const li = document.createElement('li');\n  li.textContent = text;\n  li.addEventListener('click', () => {\n    li.classList.toggle('done');\n    refresh();\n  });\n  list.appendChild(li);\n  input.value = '';\n  refresh();\n});\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.385819	2026-10-27 21:19:15.385821	t	code	mk	{"en": {"title": "To-do list (HTML/CSS/JS)", "description": "Make a **to-do list**.\\n\\n**Structure:** an `<input id=\\"new\\">`, a `<button id=\\"add\\">` \\"Add\\", a list `<ul id=\\"list\\">` and a `<p>` with\\n`<span id=\\"count\\">` — the number of **unfinished** tasks.\\n\\n**Behaviour** (`script.js`): clicking \\"Add\\" adds a new `<li>` with the text of the field (trimmed) and empties the field;\\n**empty** text is not added; clicking an item marks it done (class `done`), clicking again undoes it; `#count` always\\nshows the number of items **without** the class `done`.\\n\\n**Look:** done items are **struck through** (`text-decoration: line-through`) and grey (`#868E96`)."}}	[]	9f2089a0-09c0-473a-90a0-891e5bdccd6c	\N
9374c027-5641-4687-953e-5dc789329162	Калкулатор за бакшиш (HTML/CSS/JS)	Направете **калкулатор за бакшиш**.\n\n**Структура:** поле `<input id="bill" type="number">` за износот на сметката, избор `<select id="percent">` со\nопции **10**, **15** и **20** (вредностите се бројките, стандардно избрано **15**), и два резултати:\n`<output id="tip">` (бакшиш) и `<output id="total">` (вкупно).\n\n**Однесување:** штом ќе се смени износот или процентот, резултатите се пресметуваат одново и се прикажуваат со\n**точно две децимали** (на пр. `15.00`, `115.00`). Ако износот е празен или негативен, двата резултати се `0.00`.\n\n**Изглед:** калкулаторот е во картичка широка најмногу `340px`, центрирана, а `#total` е задебелен (`font-weight` барем 700).\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Бакшиш</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Бакшиш</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <main class="calc">\n    <h1>Бакшиш</h1>\n    <label for="bill">Сметка (ден.)</label>\n    <input id="bill" type="number" min="0" step="any" placeholder="0">\n    <label for="percent">Бакшиш</label>\n    <select id="percent">\n      <option value="10">10 %</option>\n      <option value="15" selected>15 %</option>\n      <option value="20">20 %</option>\n    </select>\n    <p>Бакшиш: <output id="tip">0.00</output></p>\n    <p>Вкупно: <output id="total">0.00</output></p>\n  </main>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\nbody {\n  background: #EEF1F5;\n}\n.calc {\n  box-sizing: border-box;\n  max-width: 340px;\n  margin: 40px auto;\n  background: #fff;\n  border-radius: 12px;\n  padding: 24px;\n  display: flex;\n  flex-direction: column;\n  gap: 6px;\n}\n.calc input, .calc select {\n  padding: 10px;\n  border: 1px solid #D9DEE7;\n  border-radius: 8px;\n  font-size: 15px;\n}\n#total {\n  font-weight: 800;\n  font-size: 20px;\n}\n<!-- file: script.js -->\nconst bill = document.getElementById('bill');\nconst percent = document.getElementById('percent');\nconst tip = document.getElementById('tip');\nconst total = document.getElementById('total');\n\nfunction update() {\n  const b = parseFloat(bill.value);\n  const amount = Number.isFinite(b) && b > 0 ? b : 0;\n  const t = amount * Number(percent.value) / 100;\n  tip.textContent = t.toFixed(2);\n  total.textContent = (amount + t).toFixed(2);\n}\n\nbill.addEventListener('input', update);\npercent.addEventListener('change', update);\nupdate();\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.387387	2026-10-27 21:19:15.387389	t	code	mk	{"en": {"title": "Tip calculator (HTML/CSS/JS)", "description": "Make a **tip calculator**.\\n\\n**Structure:** `<input id=\\"bill\\" type=\\"number\\">` for the bill, `<select id=\\"percent\\">` with options **10**, **15**, **20**\\n(the values are the numbers, **15** selected by default), and two results: `<output id=\\"tip\\">` and `<output id=\\"total\\">`.\\n\\n**Behaviour:** whenever the bill or the percentage changes, the results are recomputed and shown with **exactly two\\ndecimals** (e.g. `15.00`, `115.00`); an empty or negative bill gives `0.00` for both.\\n\\n**Look:** the calculator is a card at most `340px` wide, centred; `#total` is bold (`font-weight` at least 700)."}}	[]	9f2089a0-09c0-473a-90a0-891e5bdccd6c	\N
030e9a55-5465-411e-af39-9676d9c7786f	Profile Card (HTML/CSS)	Make a **profile card** page in `index.html`, `style.css` and `script.js`.\n\n**Structure** (inside `<div class="card">`):\n- an `<h2>` with a name and a `<p class="role">` with a role,\n- a list `<ul class="skills">` with **at least 3** `<li>` items,\n- a button `<button id="follow">Follow</button>`.\n\n**Style:**\n- `.card`: white background, rounded corners of `12px`, at most `320px` wide, centred on the page.\n- the button: background `#2747C9`, white text.\n- `.skills` shows its items **in a row** (flexbox); on screens narrower than **600px** they go **one under another**.\n\n**Behaviour:** clicking the button changes its text to `Following`; clicking again changes it back to `Follow`.\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Profile</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n<!-- file: script.js -->\n	<!-- file: index.html -->\n<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Profile</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <div class="card">\n    <h2>Ana Petrova</h2>\n    <p class="role">Web developer</p>\n    <ul class="skills">\n      <li>HTML</li>\n      <li>CSS</li>\n      <li>JavaScript</li>\n    </ul>\n    <button id="follow">Follow</button>\n  </div>\n  <script src="script.js"></script>\n</body>\n</html>\n<!-- file: style.css -->\nbody {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n  padding: 40px 16px;\n  background: #EEF1F5;\n}\n.card {\n  background: #fff;\n  border-radius: 12px;\n  max-width: 320px;\n  margin: 0 auto;\n  padding: 24px;\n  box-shadow: 0 8px 24px rgba(26, 34, 51, .12);\n}\n.card h2 { margin: 0; }\n.role { color: #6B7488; margin: 4px 0 16px; }\n.skills {\n  display: flex;\n  gap: 8px;\n  list-style: none;\n  padding: 0;\n}\n.skills li {\n  background: #E8EDFC;\n  color: #2747C9;\n  border-radius: 999px;\n  padding: 4px 10px;\n  font-size: 14px;\n}\n#follow {\n  background: #2747C9;\n  color: #fff;\n  border: 0;\n  border-radius: 8px;\n  padding: 10px 18px;\n  font-size: 15px;\n  cursor: pointer;\n}\n@media (max-width: 600px) {\n  .skills { flex-direction: column; }\n}\n<!-- file: script.js -->\nconst btn = document.getElementById('follow');\nbtn.addEventListener('click', () => {\n  btn.textContent = btn.textContent === 'Follow' ? 'Following' : 'Follow';\n});\n	web	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.270268	2026-10-27 21:19:15.390637	t	code	en	{"mk": {"title": "Картичка за профил (HTML/CSS)", "description": "Направете страница со **картичка за профил** во `index.html`, `style.css` и `script.js`.\\n\\n**Структура** (во `<div class=\\"card\\">`):\\n- `<h2>` со име и `<p class=\\"role\\">` со улога,\\n- листа `<ul class=\\"skills\\">` со **најмалку 3** ставки `<li>`,\\n- копче `<button id=\\"follow\\">Follow</button>`.\\n\\n**Стил:**\\n- `.card`: бела позадина, заоблени агли од `12px`, најмногу `320px` широка, центрирана на страницата.\\n- копчето: позадина `#2747C9`, бел текст.\\n- `.skills` ги прикажува ставките **во ред** (flexbox); на екрани потесни од **600px** се **една под друга**.\\n\\n**Однесување:** клик на копчето го менува текстот во `Following`; повторен клик го враќа во `Follow`.\\n"}}	[]	e4abeed0-dfd0-47ee-a410-3a94255515e1	\N
0a2e2c61-abfb-42c2-ae92-4ebd166bfed5	Array Sum (x86-64 Assembly)	Write in x86-64 NASM assembly the function\n\n```c\nlong array_sum(long *a, long n);\n```\n\nthat returns the sum of the `n` elements of the array `a`. Follow the System V calling convention:\n`a` is in `rdi`, `n` in `rsi`, and the result goes in `rax`. Mark it `global array_sum`.	global array_sum\nsection .text\n\narray_sum:\n    ; TODO\n    ret\n	global array_sum\nsection .text\n\narray_sum:\n    xor rax, rax\n.loop:\n    test rsi, rsi\n    jz .done\n    add rax, [rdi]\n    add rdi, 8\n    dec rsi\n    jmp .loop\n.done:\n    ret\n	asm	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.268965	2026-10-27 21:19:15.390639	t	code	en	{"mk": {"title": "Збир на низа (x86-64 асемблер)", "description": "Во x86-64 NASM асемблер напишете ја функцијата\\n\\n```c\\nlong array_sum(long *a, long n);\\n```\\n\\nшто го враќа збирот на `n`-те елементи од низата `a`. Следете ја System V конвенцијата за повикување:\\n`a` е во `rdi`, `n` во `rsi`, а резултатот оди во `rax`. Означете ја со `global array_sum`.\\n"}}	[]	629f33c6-62f8-46c6-8aee-0623706c441f	\N
112b7347-ef3f-4d94-a217-ac909ac9eb3e	Пакетен дијаграм — слоевита апликација	Нацртајте **пакетен дијаграм** за апликација во три слоја.\n\n- Пакетот **Презентација** ги содржи *Контролери* и *Погледи*.\n- Пакетот **Бизнис логика** ги содржи *Сервиси*.\n- Пакетот **Пристап до податоци** ги содржи *Репозиториуми*.\n- Презентацијата зависи од бизнис логиката, а бизнис логиката го *увезува* (`«import»`) пристапот до податоци.		{\n "kind": "package",\n "nodes": [\n  {\n   "id": "pres",\n   "name": "Презентација",\n   "type": "package",\n   "x": 60.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "Контролери",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "Controllers"\n     ]\n    },\n    {\n     "name": "Погледи",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "Views"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Presentation"\n   ],\n   "w": 240.0,\n   "h": 130.0\n  },\n  {\n   "id": "biz",\n   "name": "Бизнис логика",\n   "type": "package",\n   "x": 60.0,\n   "y": 260.0,\n   "attributes": [\n    {\n     "name": "Сервиси",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "Services"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Business logic"\n   ],\n   "w": 240.0,\n   "h": 110.0\n  },\n  {\n   "id": "dao",\n   "name": "Пристап до податоци",\n   "type": "package",\n   "x": 60.0,\n   "y": 460.0,\n   "attributes": [\n    {\n     "name": "Репозиториуми",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "Repositories"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Data access"\n   ],\n   "w": 240.0,\n   "h": 110.0\n  }\n ],\n "edges": [\n  {\n   "id": "p1",\n   "from": "pres",\n   "to": "biz",\n   "kind": "dependency",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "p2",\n   "from": "biz",\n   "to": "dao",\n   "kind": "import",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	package	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.374554	2026-10-27 21:19:15.390639	t	code	mk	{"en": {"title": "Package diagram — layered application", "description": "Draw a **package diagram** for a three-layer application.\\n\\n- **Presentation** (`Презентација`) contains *Controllers* and *Views*.\\n- **Business logic** (`Бизнис логика`) contains *Services*.\\n- **Data access** (`Пристап до податоци`) contains *Repositories*.\\n- Presentation depends on business logic; business logic *imports* (`«import»`) data access."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
128c63f9-4732-4f6b-a2bc-846b6cb58c82	Stack Implementation	Implement a generic stack data structure in C++ using a dynamic array.\n\n**Requirements:**\n1. Create a class `Stack` that stores `int` values.\n2. Implement `void push(int value)` — adds an element to the top.\n3. Implement `int pop()` — removes and returns the top element. Throw `std::underflow_error` if empty.\n4. Implement `int top() const` — returns the top element without removing it. Throw `std::underflow_error` if empty.\n5. Implement `bool isEmpty() const` — returns `true` if the stack is empty.\n6. Implement `int size() const` — returns the number of elements.\n7. Ensure proper memory management (destructor, no memory leaks).\n\n**Example:**\n```\nStack s;\ns.push(10);\ns.push(20);\ncout << s.top();   // 20\ncout << s.pop();   // 20\ncout << s.size();  // 1\n```\n	#include <stdexcept>\nusing namespace std;\n\n// TODO: implement Stack class\n	#include <stdexcept>\nusing namespace std;\n\nclass Stack {\n    int* data;\n    int capacity;\n    int count;\n\n    void resize() {\n        capacity *= 2;\n        int* newData = new int[capacity];\n        for (int i = 0; i < count; i++) newData[i] = data[i];\n        delete[] data;\n        data = newData;\n    }\n\npublic:\n    Stack() : capacity(8), count(0) {\n        data = new int[capacity];\n    }\n\n    ~Stack() { delete[] data; }\n\n    void push(int value) {\n        if (count == capacity) resize();\n        data[count++] = value;\n    }\n\n    int pop() {\n        if (isEmpty()) throw underflow_error("Stack is empty");\n        return data[--count];\n    }\n\n    int top() const {\n        if (isEmpty()) throw underflow_error("Stack is empty");\n        return data[count - 1];\n    }\n\n    bool isEmpty() const { return count == 0; }\n    int size() const { return count; }\n};\n	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.249543	2026-10-27 21:19:15.39064	t	code	en	{"mk": {"title": "Имплементација на стек", "description": "Имплементирајте податочна структура стек во C++ со динамичка низа.\\n\\n**Барања:**\\n1. Направете класа `Stack` што чува вредности од тип `int`.\\n2. Имплементирајте `void push(int value)` — додава елемент на врвот.\\n3. Имплементирајте `int pop()` — го отстранува и враќа елементот од врвот. Ако стекот е празен, фрлете `std::underflow_error`.\\n4. Имплементирајте `int top() const` — го враќа елементот од врвот без да го отстрани. Ако стекот е празен, фрлете `std::underflow_error`.\\n5. Имплементирајте `bool isEmpty() const` — враќа `true` ако стекот е празен.\\n6. Имплементирајте `int size() const` — го враќа бројот на елементи.\\n7. Внимавајте на меморијата (деструктор, без протекување меморија).\\n\\n**Пример:**\\n```\\nStack s;\\ns.push(10);\\ns.push(20);\\ncout << s.top();   // 20\\ncout << s.pop();   // 20\\ncout << s.size();  // 1\\n```\\n"}}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
1342f377-a292-4348-9dd3-59b233e43ffb	Sequence дијаграм — најава	Нацртајте **sequence дијаграм** за најава во студентски сервис.\n\nУчесници: актерот **Корисник** и објектите **:ФормаЗаНајава**, **:Контролер** и **:БазаНаКорисници**.\n\n1. Корисникот *внесува* корисничко име и лозинка во формата — `внеси(корисник, лозинка)`.\n2. Формата бара од контролерот да го *најави* — `најави(корисник, лозинка)`.\n3. Контролерот го *бара* корисникот во базата — `најди(корисник)`; базата враќа одговор `корисник`.\n4. Контролерот сам ја *проверува лозинката* — `провериЛозинка()`.\n5. Контролерот ѝ одговара `успех` на формата, а формата на корисникот му ја *прикажува почетната страница* — `прикажиПочетна()`.		{\n "kind": "sequence",\n "nodes": [\n  {\n   "id": "k",\n   "name": "Корисник",\n   "type": "actor",\n   "x": 40.0,\n   "y": 40.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "User"\n   ]\n  },\n  {\n   "id": "f",\n   "name": ":ФормаЗаНајава",\n   "type": "lifeline",\n   "x": 240.0,\n   "y": 40.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    ":LoginForm",\n    "ФормаЗаНајава"\n   ]\n  },\n  {\n   "id": "c",\n   "name": ":Контролер",\n   "type": "lifeline",\n   "x": 460.0,\n   "y": 40.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    ":Controller",\n    "Контролер"\n   ]\n  },\n  {\n   "id": "b",\n   "name": ":БазаНаКорисници",\n   "type": "lifeline",\n   "x": 680.0,\n   "y": 40.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    ":UserDatabase",\n    "БазаНаКорисници"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "m1",\n   "from": "k",\n   "to": "f",\n   "kind": "sync",\n   "fromMult": "",\n   "toMult": "",\n   "label": "внеси(корисник, лозинка)",\n   "y": 130.0\n  },\n  {\n   "id": "m2",\n   "from": "f",\n   "to": "c",\n   "kind": "sync",\n   "fromMult": "",\n   "toMult": "",\n   "label": "најави(корисник, лозинка)",\n   "y": 180.0\n  },\n  {\n   "id": "m3",\n   "from": "c",\n   "to": "b",\n   "kind": "sync",\n   "fromMult": "",\n   "toMult": "",\n   "label": "најди(корисник)",\n   "y": 230.0\n  },\n  {\n   "id": "m4",\n   "from": "b",\n   "to": "c",\n   "kind": "reply",\n   "fromMult": "",\n   "toMult": "",\n   "label": "корисник",\n   "y": 280.0\n  },\n  {\n   "id": "m5",\n   "from": "c",\n   "to": "c",\n   "kind": "sync",\n   "fromMult": "",\n   "toMult": "",\n   "label": "провериЛозинка()",\n   "y": 330.0\n  },\n  {\n   "id": "m6",\n   "from": "c",\n   "to": "f",\n   "kind": "reply",\n   "fromMult": "",\n   "toMult": "",\n   "label": "успех",\n   "y": 390.0\n  },\n  {\n   "id": "m7",\n   "from": "f",\n   "to": "k",\n   "kind": "sync",\n   "fromMult": "",\n   "toMult": "",\n   "label": "прикажиПочетна()",\n   "y": 440.0\n  }\n ]\n}	sequence	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.368445	2026-10-27 21:19:15.390641	t	code	mk	{"en": {"title": "Sequence diagram — logging in", "description": "Draw a **sequence diagram** of logging in to the student services.\\n\\nParticipants: the actor **User** (`Корисник`) and the objects **:LoginForm** (`:ФормаЗаНајава`), **:Controller** (`:Контролер`) and **:UserDatabase** (`:БазаНаКорисници`).\\n\\n1. The user *enters* (`внеси(корисник, лозинка)`) the user name and password in the form.\\n2. The form asks the controller to *log in* (`најави(корисник, лозинка)`).\\n3. The controller *finds* the user in the database (`најди(корисник)`); the database replies with the user (`корисник`).\\n4. The controller *checks the password* itself (`провериЛозинка()`).\\n5. The controller replies *success* (`успех`) to the form, and the form *shows the home page* to the user (`прикажиПочетна()`)."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
23bec27d-a91a-4582-a3c7-790469571996	Grades (Kotlin)	In Kotlin, write a `data class Student(val name: String, val grades: List<Int>)` with a property\n`average` (0.0 when there are no grades), and a function `best(students: List<Student>): String?` that returns the\nname of the student with the highest average (or `null` for an empty list).	data class Student(val name: String, val grades: List<Int>)\n\nfun best(students: List<Student>): String? {\n    TODO()\n}\n	data class Student(val name: String, val grades: List<Int>) {\n    val average: Double get() = if (grades.isEmpty()) 0.0 else grades.average()\n}\n\nfun best(students: List<Student>): String? = students.maxByOrNull { it.average }?.name\n	kotlin	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.265076	2026-10-27 21:19:15.390641	t	code	en	{"mk": {"title": "Оценки (Kotlin)", "description": "Во Kotlin напишете `data class Student(val name: String, val grades: List<Int>)` со својство\\n`average` (0.0 кога нема оценки) и функција `best(students: List<Student>): String?` што го враќа\\nимето на студентот со највисок просек (или `null` за празна листа).\\n"}}	[]	6bdb8d08-42fd-4b05-862a-3e1124e4d380	\N
34af459e-d75c-4123-821e-eec168e121d0	ER дијаграм — база за факултет	Дизајнирајте **ER дијаграм** за база на податоци на факултет.\n\n- **Студент** се идентификува со бројот на индекс и има име, презиме и е-пошта.\n- **Предмет** се идентификува со шифра и има назив и број на кредити.\n- **Професор** има ID и име.\n- Студентот запишува многу предмети, а предметот има многу студенти (`запишува`).\n- Секој предмет го предава точно еден професор; професорот предава многу предмети (`предава`).\n\nОзначете ги примарните клучеви и кардиналностите (1, N, M).		{\n "kind": "er",\n "nodes": [\n  {\n   "id": "student",\n   "name": "Студент",\n   "type": "entity",\n   "x": 40.0,\n   "y": 60.0,\n   "attributes": [\n    {\n     "name": "индекс",\n     "type": "",\n     "visibility": "-",\n     "pk": true,\n     "fk": false,\n     "aliases": [\n      "index",\n      "brIndeks"\n     ]\n    },\n    {\n     "name": "име",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "ime",\n      "firstName"\n     ]\n    },\n    {\n     "name": "презиме",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "prezime",\n      "lastName"\n     ]\n    },\n    {\n     "name": "email",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "е-пошта",\n      "eposta"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Student"\n   ]\n  },\n  {\n   "id": "predmet",\n   "name": "Предмет",\n   "type": "entity",\n   "x": 560.0,\n   "y": 60.0,\n   "attributes": [\n    {\n     "name": "шифра",\n     "type": "",\n     "visibility": "-",\n     "pk": true,\n     "fk": false,\n     "aliases": [\n      "code",\n      "sifra"\n     ]\n    },\n    {\n     "name": "назив",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "name",\n      "naziv"\n     ]\n    },\n    {\n     "name": "кредити",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "credits",\n      "ects"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Course",\n    "Subject"\n   ]\n  },\n  {\n   "id": "profesor",\n   "name": "Професор",\n   "type": "entity",\n   "x": 560.0,\n   "y": 380.0,\n   "attributes": [\n    {\n     "name": "id",\n     "type": "",\n     "visibility": "-",\n     "pk": true,\n     "fk": false\n    },\n    {\n     "name": "име",\n     "type": "",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "name",\n      "ime"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Professor"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "r1",\n   "from": "student",\n   "to": "predmet",\n   "kind": "relationship",\n   "fromMult": "N",\n   "toMult": "M",\n   "label": "запишува"\n  },\n  {\n   "id": "r2",\n   "from": "profesor",\n   "to": "predmet",\n   "kind": "relationship",\n   "fromMult": "1",\n   "toMult": "N",\n   "label": "предава"\n  }\n ]\n}	er	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.356667	2026-10-27 21:19:15.390642	t	code	mk	{"en": {"title": "ER diagram — faculty database", "description": "Design an **ER diagram** for a faculty database.\\n\\n- A **student** (`Студент`) is identified by the index number and has a first name, a last name and an e-mail.\\n- A **course** (`Предмет`) is identified by its code and has a name and a number of credits.\\n- A **professor** (`Професор`) has an ID and a name.\\n- A student enrols in many courses and a course has many students (`запишува`).\\n- Each course is taught by exactly one professor; a professor teaches many courses (`предава`).\\n\\nMark the primary keys and the cardinalities (1, N, M)."}}	[]	d3e9fc2c-8656-492d-9362-f7c24151b4a3	\N
40b82ec7-fd09-4361-8403-5035f0eacc91	Hello World Function	Write a C++ function `greet(string name)` that returns the string "Hello, <name>!".\n\n**Requirements:**\n- The function must take a `std::string` parameter called `name`.\n- The function must return a `std::string` in the format `"Hello, <name>!"`.\n- Do not print anything inside the function; just return the string.\n\n**Example:**\n```\ngreet("World")  →  "Hello, World!"\ngreet("Alice")  →  "Hello, Alice!"\n```\n	#include <string>\nusing namespace std;\n\n// TODO: implement greet()\n	#include <string>\nusing namespace std;\n\nstring greet(string name) {\n    return "Hello, " + name + "!";\n}\n	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.243639	2026-10-27 21:19:15.390643	t	code	en	{"mk": {"title": "Функција за поздрав", "description": "Напишете C++ функција `greet(string name)` што го враќа стрингот \\"Hello, <name>!\\".\\n\\n**Барања:**\\n- Функцијата прима параметар од тип `std::string` со име `name`.\\n- Функцијата враќа `std::string` во форматот `\\"Hello, <name>!\\"`.\\n- Во функцијата не печатете ништо; само вратете го стрингот.\\n\\n**Пример:**\\n```\\ngreet(\\"World\\")  →  \\"Hello, World!\\"\\ngreet(\\"Alice\\")  →  \\"Hello, Alice!\\"\\n```\\n"}}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
56536497-5111-4aac-9768-1d101259396d	Shapes (C#)	In C#, write an abstract class `Shape` with an abstract method `double Area()` and the classes\n`Circle(double r)` and `Rectangle(double w, double h)`. Add a static method `Shapes.TotalArea(List<Shape> shapes)`\nthat returns the sum of the areas.	public abstract class Shape\n{\n    // TODO\n}\n	public abstract class Shape { public abstract double Area(); }\npublic class Circle : Shape { private readonly double r; public Circle(double r) { this.r = r; } public override double Area() => Math.PI * r * r; }\npublic class Rectangle : Shape { private readonly double w, h; public Rectangle(double w, double h) { this.w = w; this.h = h; } public override double Area() => w * h; }\npublic static class Shapes { public static double TotalArea(List<Shape> shapes) => shapes.Sum(s => s.Area()); }\n	csharp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.263792	2026-10-27 21:19:15.390643	t	code	en	{"mk": {"title": "Геометриски форми (C#)", "description": "Во C# напишете апстрактна класа `Shape` со апстрактен метод `double Area()` и класите\\n`Circle(double r)` и `Rectangle(double w, double h)`. Додадете статички метод `Shapes.TotalArea(List<Shape> shapes)`\\nшто го враќа збирот на плоштините.\\n"}}	[]	f3528493-8622-4f52-8c64-8cd55f453dec	\N
5a4c0662-fe43-491c-b40c-0273119714fa	State дијаграм — нарачка	Нацртајте **дијаграм на состојби** за нарачка во онлајн продавница.\n\n- Новата нарачка е во состојба **Нова**.\n- Со настанот *плати* преминува во **Платена** (при влез се *испраќа потврда*), а со *откажи* во **Откажана**.\n- Платената нарачка со *испрати* станува **Испратена**, а со *достави* — **Доставена**.\n- Доставена и откажана нарачка завршуваат (крајна состојба).		{\n "kind": "state",\n "nodes": [\n  {\n   "id": "i",\n   "name": "",\n   "type": "initial",\n   "x": 140.0,\n   "y": 20.0,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "nova",\n   "name": "Нова",\n   "type": "state",\n   "x": 80.0,\n   "y": 100.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "New"\n   ]\n  },\n  {\n   "id": "plat",\n   "name": "Платена",\n   "type": "state",\n   "x": 80.0,\n   "y": 260.0,\n   "attributes": [\n    {\n     "name": "entry / испрати потврда",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Paid"\n   ]\n  },\n  {\n   "id": "otk",\n   "name": "Откажана",\n   "type": "state",\n   "x": 400.0,\n   "y": 100.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Cancelled",\n    "Canceled"\n   ]\n  },\n  {\n   "id": "ispr",\n   "name": "Испратена",\n   "type": "state",\n   "x": 80.0,\n   "y": 420.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Shipped"\n   ]\n  },\n  {\n   "id": "dost",\n   "name": "Доставена",\n   "type": "state",\n   "x": 80.0,\n   "y": 560.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Delivered"\n   ]\n  },\n  {\n   "id": "f",\n   "name": "",\n   "type": "final",\n   "x": 440.0,\n   "y": 590.0,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": [\n  {\n   "id": "t0",\n   "from": "i",\n   "to": "nova",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "t1",\n   "from": "nova",\n   "to": "plat",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": "плати"\n  },\n  {\n   "id": "t2",\n   "from": "nova",\n   "to": "otk",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": "откажи"\n  },\n  {\n   "id": "t3",\n   "from": "plat",\n   "to": "ispr",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": "испрати"\n  },\n  {\n   "id": "t4",\n   "from": "ispr",\n   "to": "dost",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": "достави"\n  },\n  {\n   "id": "t5",\n   "from": "dost",\n   "to": "f",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "t6",\n   "from": "otk",\n   "to": "f",\n   "kind": "transition",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	state	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.365502	2026-10-27 21:19:15.390644	t	code	mk	{"en": {"title": "State machine — an order", "description": "Draw a **state machine** for an order in an online shop.\\n\\n- A new order is **New** (`Нова`).\\n- The event *pay* (`плати`) takes it to **Paid** (`Платена`, on entry a confirmation is sent); *cancel* (`откажи`) to **Cancelled** (`Откажана`).\\n- *ship* (`испрати`) makes a paid order **Shipped** (`Испратена`); *deliver* (`достави`) — **Delivered** (`Доставена`).\\n- Delivered and cancelled orders end (final state)."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
5f57a182-42ec-4b17-9a58-597f74ecbe2e	Typed Stack (TypeScript)	Implement a generic class `Stack<T>` in TypeScript with `push(x: T): void`, `pop(): T | undefined`,\n`peek(): T | undefined` and a read-only property `size: number`.\n\nCode that uses it with the wrong type must **not compile**, e.g. pushing a string into a `Stack<number>`.	class Stack<T> {\n  // TODO\n}\n	class Stack<T> {\n  private items: T[] = [];\n  push(x: T): void { this.items.push(x); }\n  pop(): T | undefined { return this.items.pop(); }\n  peek(): T | undefined { return this.items[this.items.length - 1]; }\n  get size(): number { return this.items.length; }\n}\n	typescript	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.260161	2026-10-27 21:19:15.390645	t	code	en	{"mk": {"title": "Типизиран стек (TypeScript)", "description": "Имплементирајте генеричка класа `Stack<T>` во TypeScript со `push(x: T): void`, `pop(): T | undefined`,\\n`peek(): T | undefined` и својство само за читање `size: number`.\\n\\nКод што ја користи со погрешен тип **не смее да се компајлира**, на пр. ставање стринг во `Stack<number>`.\\n"}}	[]	9f2089a0-09c0-473a-90a0-891e5bdccd6c	\N
628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	Reverse Array (C)	Write a C program that reads `n` and then `n` integers, and prints them in **reverse order**,\nseparated by single spaces.\n\n**Input:** the first line contains `n` (1 ≤ n ≤ 1000), the second line `n` integers.\n\n**Output:** the numbers in reverse order on one line.\n\n**Example:**\n```\nInput:\n5\n1 2 3 4 5\nOutput:\n5 4 3 2 1\n```\n	#include <stdio.h>\n\nint main(void) {\n    // TODO\n    return 0;\n}\n	#include <stdio.h>\n\nint main(void) {\n    int n, a[1000];\n    scanf("%d", &n);\n    for (int i = 0; i < n; i++) scanf("%d", &a[i]);\n    for (int i = n - 1; i >= 0; i--) printf("%d%c", a[i], i ? ' ' : '\\n');\n    return 0;\n}\n	c	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.255236	2026-10-27 21:19:15.390645	t	code	en	{"mk": {"title": "Превртена низа (C)", "description": "Напишете C програма што чита `n`, а потоа `n` цели броеви, и ги печати во **обратен редослед**,\\nодделени со по едно празно место.\\n\\n**Влез:** првиот ред содржи `n` (1 ≤ n ≤ 1000), вториот ред `n` цели броеви.\\n\\n**Излез:** броевите во обратен редослед, во еден ред.\\n\\n**Пример:**\\n```\\nВлез:\\n5\\n1 2 3 4 5\\nИзлез:\\n5 4 3 2 1\\n```\\n"}}	[]	c6b22b4b-1a01-420e-8637-6414ac355c00	\N
683a9c81-7ceb-4991-b089-ebbd4e5a3e62	List Functions (Common Lisp)	In Common Lisp, write:\n\n- `(my-reverse lst)` — reverses a list **recursively** (without `reverse`)\n- `(count-if-even lst)` — how many elements are even\n- `(flatten tree)` — turns a nested list into a flat list, e.g. `(flatten '(1 (2 (3)) 4))` → `(1 2 3 4)`	(defun my-reverse (lst)\n  ;; TODO\n  )\n	(defun my-reverse (lst)\n  (if (null lst) nil (append (my-reverse (cdr lst)) (list (car lst)))))\n\n(defun count-if-even (lst)\n  (count-if #'evenp lst))\n\n(defun flatten (tree)\n  (cond ((null tree) nil)\n        ((atom tree) (list tree))\n        (t (append (flatten (car tree)) (flatten (cdr tree))))))\n	lisp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.267732	2026-10-27 21:19:15.390646	t	code	en	{"mk": {"title": "Функции за листи (Common Lisp)", "description": "Во Common Lisp напишете:\\n\\n- `(my-reverse lst)` — ја превртува листата **рекурзивно** (без `reverse`)\\n- `(count-if-even lst)` — колку елементи се парни\\n- `(flatten tree)` — вгнездена листа ја претвора во рамна, на пр. `(flatten '(1 (2 (3)) 4))` → `(1 2 3 4)`\\n"}}	[]	aff098bb-b566-4bab-a216-188f334d956e	\N
72eb8db0-6d99-415d-858d-8b58422026cb	Palindromes (JavaScript)	Write a JavaScript function `isPalindrome(text)` that returns `true` if `text` reads the same\nforwards and backwards, **ignoring letter case, spaces and punctuation**, and `false` otherwise.\n\nThen write `countPalindromes(words)` that returns how many strings in the array `words` are palindromes.\n\n**Example:**\n```js\nisPalindrome("Ana")                       // true\nisPalindrome("Never odd or even!")        // true\ncountPalindromes(["kayak", "ALE", "Oko"]) // 2\n```\n	function isPalindrome(text) {\n  // TODO\n}\n\nfunction countPalindromes(words) {\n  // TODO\n}\n	function isPalindrome(text) {\n  const t = text.toLowerCase().replace(/[^\\p{L}\\p{N}]/gu, "");\n  return t === [...t].reverse().join("");\n}\n\nfunction countPalindromes(words) {\n  return words.filter(isPalindrome).length;\n}\n	javascript	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.256506	2026-10-27 21:19:15.390647	t	code	en	{"mk": {"title": "Палиндроми (JavaScript)", "description": "Напишете JavaScript функција `isPalindrome(text)` што враќа `true` ако `text` се чита исто\\nод напред и од назад, **без разлика на мали/големи букви, празни места и интерпункција**, а инаку `false`.\\n\\nПотоа напишете `countPalindromes(words)` што враќа колку стрингови во низата `words` се палиндроми.\\n\\n**Пример:**\\n```js\\nisPalindrome(\\"Ana\\")                       // true\\nisPalindrome(\\"Never odd or even!\\")        // true\\ncountPalindromes([\\"kayak\\", \\"ALE\\", \\"Oko\\"]) // 2\\n```\\n"}}	[]	9f2089a0-09c0-473a-90a0-891e5bdccd6c	\N
73b0a1f2-d55a-4404-b80b-64480e2016b2	Word Counter (PHP)	Write a PHP function `countWords(string $text): array` that returns how many times each word appears,\nignoring case, as an array `word => count` sorted by count (descending) and then alphabetically.	<?php\nfunction countWords(string $text): array {\n    // TODO\n}\n	<?php\nfunction countWords(string $text): array {\n    $words = preg_split('/[^\\p{L}]+/u', mb_strtolower($text), -1, PREG_SPLIT_NO_EMPTY);\n    $c = array_count_values($words);\n    uksort($c, fn($a, $b) => [$c[$b], $a] <=> [$c[$a], $b]);\n    return $c;\n}\n	php	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.261416	2026-10-27 21:19:15.390647	t	code	en	{"mk": {"title": "Бројач на зборови (PHP)", "description": "Напишете PHP функција `countWords(string $text): array` што враќа колку пати се појавува секој збор,\\nбез разлика на мали/големи букви, како низа `збор => број`, подредена по број (опаѓачки), а потоа азбучно.\\n"}}	[]	9469cc9a-21d5-4aee-a436-a21097e815ff	\N
7a049050-c9ad-4aed-8aa2-4691c63fe52d	Enrolments per Course (PostgreSQL)	Tables (PostgreSQL):\n\n- `predmet(id SERIAL, ime TEXT, krediti INT)` — courses\n- `upis(student TEXT, predmet_id INT → predmet.id, datum DATE)` — enrolments\n\nWrite a query that returns **every** course (also those with no enrolments) with the **number of enrolled\nstudents**, as columns `ime` and `broj`, sorted by `broj` descending, then by `ime`.	SELECT\n  -- TODO\n;\n	SELECT p.ime, COUNT(u.student) AS broj\nFROM predmet p\nLEFT JOIN upis u ON u.predmet_id = p.id\nGROUP BY p.id, p.ime\nORDER BY broj DESC, p.ime;\n	postgresql	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.259043	2026-10-27 21:19:15.390648	t	code	en	{"mk": {"title": "Запишани по предмет (PostgreSQL)", "description": "Табели (PostgreSQL):\\n\\n- `predmet(id SERIAL, ime TEXT, krediti INT)` — предмети\\n- `upis(student TEXT, predmet_id INT → predmet.id, datum DATE)` — запишувања\\n\\nНапишете барање што го враќа **секој** предмет (и оние без запишани студенти) со **бројот на запишани\\nстуденти**, како колони `ime` и `broj`, подредени по `broj` опаѓачки, а потоа по `ime`.\\n"}}	[]	d3e9fc2c-8656-492d-9362-f7c24151b4a3	\N
7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	Deployment дијаграм — веб систем	Нацртајте **deployment дијаграм** за веб систем.\n\n- **Компјутерот на корисникот** (уред, со прелистувач) комуницира со **Веб сервер** преку *HTTPS*.\n- Веб серверот комуницира со **Апликациски сервер** преку *HTTP*.\n- Апликацискиот сервер комуницира со **Сервер за бази** преку *JDBC*.\n- Артефактот **app.jar** е распореден (`«deploy»`) на апликацискиот сервер.		{\n "kind": "deployment",\n "nodes": [\n  {\n   "id": "pc",\n   "name": "Компјутер на корисник",\n   "type": "device",\n   "x": 20.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "Прелистувач",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "Browser"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "User computer",\n    "Client"\n   ],\n   "w": 230.0,\n   "h": 110.0\n  },\n  {\n   "id": "web",\n   "name": "Веб сервер",\n   "type": "node",\n   "x": 330.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "Nginx",\n     "type": "",\n     "visibility": "",\n     "pk": false,\n     "fk": false\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Web server"\n   ],\n   "w": 200.0,\n   "h": 110.0\n  },\n  {\n   "id": "app",\n   "name": "Апликациски сервер",\n   "type": "node",\n   "x": 330.0,\n   "y": 260.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Application server",\n    "App server"\n   ],\n   "w": 200.0,\n   "h": 110.0\n  },\n  {\n   "id": "db",\n   "name": "Сервер за бази",\n   "type": "node",\n   "x": 330.0,\n   "y": 480.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Database server",\n    "DB server"\n   ],\n   "w": 200.0,\n   "h": 110.0\n  },\n  {\n   "id": "jar",\n   "name": "app.jar",\n   "type": "artifact",\n   "x": 40.0,\n   "y": 280.0,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": [\n  {\n   "id": "c1",\n   "from": "pc",\n   "to": "web",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": "HTTPS"\n  },\n  {\n   "id": "c2",\n   "from": "web",\n   "to": "app",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": "HTTP"\n  },\n  {\n   "id": "c3",\n   "from": "app",\n   "to": "db",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": "JDBC"\n  },\n  {\n   "id": "c4",\n   "from": "jar",\n   "to": "app",\n   "kind": "deploy",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	deployment	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.37634	2026-10-27 21:19:15.390648	t	code	mk	{"en": {"title": "Deployment diagram — web system", "description": "Draw a **deployment diagram** for a web system.\\n\\n- The **user's computer** (`Компјутер на корисник`, a device with a browser) talks to the **Web server** (`Веб сервер`) over *HTTPS*.\\n- The web server talks to the **Application server** (`Апликациски сервер`) over *HTTP*.\\n- The application server talks to the **Database server** (`Сервер за бази`) over *JDBC*.\\n- The artifact **app.jar** is deployed (`«deploy»`) on the application server."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
8fd3c66f-7a1f-4228-a88b-353a598f0b7a	UML класен дијаграм — библиотека	Нацртајте **UML класен дијаграм** за библиотека.\n\n- **Книга** има наслов, ISBN и автор, и метод што кажува дали е достапна.\n- **Член** има име и број на членска карта, и може да позајми книга.\n- **Позајмица** има датум и рок за враќање, и метод што кажува дали доцни.\n- Еден член прави произволен број позајмици; секоја позајмица е за точно една книга (една книга може да биде во многу позајмици).\n- **Вработен** (апстрактна класа) има име; **Библиотекар** е вработен.\n\nНацртајте го во уредувачот или прикачете слика / PDF (draw.io, StarUML, фотографија од цртеж).		{\n "kind": "uml",\n "nodes": [\n  {\n   "id": "kniga",\n   "name": "Книга",\n   "type": "class",\n   "x": 40.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "наслов",\n     "type": "String",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "title"\n     ]\n    },\n    {\n     "name": "isbn",\n     "type": "String",\n     "visibility": "-",\n     "pk": false,\n     "fk": false\n    },\n    {\n     "name": "автор",\n     "type": "String",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "author"\n     ]\n    }\n   ],\n   "methods": [\n    {\n     "name": "достапна",\n     "params": "",\n     "returns": "boolean",\n     "visibility": "+"\n    }\n   ],\n   "aliases": [\n    "Book"\n   ]\n  },\n  {\n   "id": "clen",\n   "name": "Член",\n   "type": "class",\n   "x": 620.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "име",\n     "type": "String",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "name"\n     ]\n    },\n    {\n     "name": "бројНаКарта",\n     "type": "int",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "cardNumber",\n      "brojKarta"\n     ]\n    }\n   ],\n   "methods": [\n    {\n     "name": "позајми",\n     "params": "к: Книга",\n     "returns": "Позајмица",\n     "visibility": "+"\n    }\n   ],\n   "aliases": [\n    "Member"\n   ]\n  },\n  {\n   "id": "pozajmica",\n   "name": "Позајмица",\n   "type": "class",\n   "x": 330.0,\n   "y": 300.0,\n   "attributes": [\n    {\n     "name": "датум",\n     "type": "Date",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "date"\n     ]\n    },\n    {\n     "name": "рок",\n     "type": "Date",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "dueDate",\n      "rokZaVrakjanje"\n     ]\n    }\n   ],\n   "methods": [\n    {\n     "name": "доцни",\n     "params": "",\n     "returns": "boolean",\n     "visibility": "+"\n    }\n   ],\n   "aliases": [\n    "Loan"\n   ]\n  },\n  {\n   "id": "vraboten",\n   "name": "Вработен",\n   "type": "abstract",\n   "x": 40.0,\n   "y": 520.0,\n   "attributes": [\n    {\n     "name": "име",\n     "type": "String",\n     "visibility": "#",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "name"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Employee"\n   ]\n  },\n  {\n   "id": "bibliotekar",\n   "name": "Библиотекар",\n   "type": "class",\n   "x": 620.0,\n   "y": 560.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Librarian"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "e1",\n   "from": "clen",\n   "to": "pozajmica",\n   "kind": "association",\n   "fromMult": "1",\n   "toMult": "0..*",\n   "label": "прави"\n  },\n  {\n   "id": "e2",\n   "from": "pozajmica",\n   "to": "kniga",\n   "kind": "association",\n   "fromMult": "0..*",\n   "toMult": "1",\n   "label": "за"\n  },\n  {\n   "id": "e3",\n   "from": "bibliotekar",\n   "to": "vraboten",\n   "kind": "inheritance",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	uml	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.350927	2026-10-27 21:19:15.390649	t	code	mk	{"en": {"title": "UML class diagram — library", "description": "Draw a **UML class diagram** for a library.\\n\\n- A **book** (`Книга`) has a title, an ISBN and an author, and a method that says whether it is available.\\n- A **member** (`Член`) has a name and a card number, and can borrow a book.\\n- A **loan** (`Позајмица`) has a date and a due date, and a method that says whether it is late.\\n- A member makes any number of loans; each loan is of exactly one book (a book can be in many loans).\\n- **Employees** (`Вработен`, abstract) have a name; a **librarian** (`Библиотекар`) is an employee.\\n\\nDraw it in the editor, or upload a picture / PDF (draw.io, StarUML, a photo of a drawing)."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
aaf44748-6b51-4706-a44b-3119186de257	Bank Account (Java)	Implement a class `BankAccount` in Java.\n\n**Requirements:**\n1. Constructor `BankAccount(String owner, double initialBalance)`.\n2. `void deposit(double amount)` — adds money; throw `IllegalArgumentException` if `amount <= 0`.\n3. `void withdraw(double amount)` — removes money; throw `IllegalArgumentException` if `amount <= 0`\n   and `IllegalStateException("Insufficient funds")` if the balance is too low.\n4. `double getBalance()` and `String getOwner()`.\n5. `String toString()` returns `"<owner>: <balance>"` with the balance to 2 decimals, e.g. `Ana: 150.00`.\n\n**Example:**\n```\nBankAccount a = new BankAccount("Ana", 100);\na.deposit(50);\nSystem.out.println(a);   // Ana: 150.00\n```\n	public class BankAccount {\n    // TODO: fields, constructor, methods\n}\n	public class BankAccount {\n    private final String owner;\n    private double balance;\n\n    public BankAccount(String owner, double initialBalance) {\n        this.owner = owner;\n        this.balance = initialBalance;\n    }\n\n    public void deposit(double amount) {\n        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");\n        balance += amount;\n    }\n\n    public void withdraw(double amount) {\n        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");\n        if (amount > balance) throw new IllegalStateException("Insufficient funds");\n        balance -= amount;\n    }\n\n    public double getBalance() { return balance; }\n    public String getOwner() { return owner; }\n\n    @Override\n    public String toString() {\n        return String.format(java.util.Locale.US, "%s: %.2f", owner, balance);\n    }\n}\n	java	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.253824	2026-10-27 21:19:15.39065	t	code	en	{"mk": {"title": "Банкарска сметка (Java)", "description": "Имплементирајте класа `BankAccount` во Java.\\n\\n**Барања:**\\n1. Конструктор `BankAccount(String owner, double initialBalance)`.\\n2. `void deposit(double amount)` — додава пари; ако `amount <= 0`, фрлете `IllegalArgumentException`.\\n3. `void withdraw(double amount)` — подига пари; ако `amount <= 0`, фрлете `IllegalArgumentException`,\\n   а ако нема доволно средства, фрлете `IllegalStateException(\\"Insufficient funds\\")`.\\n4. `double getBalance()` и `String getOwner()`.\\n5. `String toString()` враќа `\\"<owner>: <balance>\\"` со салдото на 2 децимали, на пр. `Ana: 150.00`.\\n\\n**Пример:**\\n```\\nBankAccount a = new BankAccount(\\"Ana\\", 100);\\na.deposit(50);\\nSystem.out.println(a);   // Ana: 150.00\\n```\\n"}}	[]	1eaa5ef5-23c2-47b0-92f1-7c5d9dcb0da9	\N
b5cb4216-6685-44e1-bc7c-fa4446a7073f	Word Frequency (Python)	Write a Python function `word_frequency(text)` that counts how many times each word appears in a text.\n\n**Requirements:**\n1. Words are separated by whitespace; ignore case (`"Code"` and `"code"` are the same word).\n2. Strip the punctuation `.,!?;:` from the start and end of each word.\n3. Return a `dict` mapping each word to its count. Empty text returns `{}`.\n4. Write a second function `top_words(text, n)` that returns the `n` most frequent words as a list of\n   `(word, count)` tuples, most frequent first; ties are ordered alphabetically.\n\n**Example:**\n```\nword_frequency("Code, code. Learn!")   →  {'code': 2, 'learn': 1}\ntop_words("b a b c a b", 2)            →  [('b', 3), ('a', 2)]\n```\n	def word_frequency(text):\n    # TODO\n    pass\n\n\ndef top_words(text, n):\n    # TODO\n    pass\n	def word_frequency(text):\n    counts = {}\n    for raw in text.split():\n        word = raw.strip(".,!?;:").lower()\n        if word:\n            counts[word] = counts.get(word, 0) + 1\n    return counts\n\n\ndef top_words(text, n):\n    counts = word_frequency(text)\n    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]\n	python	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.252458	2026-10-27 21:19:15.39065	t	code	en	{"mk": {"title": "Честота на зборови (Python)", "description": "Напишете Python функција `word_frequency(text)` што брои колку пати се појавува секој збор во текстот.\\n\\n**Барања:**\\n1. Зборовите се одделени со празни места; не се прави разлика меѓу мали и големи букви (`\\"Code\\"` и `\\"code\\"` се ист збор).\\n2. Отстранете ги интерпункциските знаци `.,!?;:` од почетокот и крајот на секој збор.\\n3. Вратете `dict` што секој збор го пресликува во неговиот број на појавувања. За празен текст вратете `{}`.\\n4. Напишете и втора функција `top_words(text, n)` што ги враќа `n` најчести зборови како листа од торки\\n   `(збор, број)`, од најчестиот; при ист број, зборовите се подредени азбучно.\\n\\n**Пример:**\\n```\\nword_frequency(\\"Code, code. Learn!\\")   →  {'code': 2, 'learn': 1}\\ntop_words(\\"b a b c a b\\", 2)            →  [('b', 3), ('a', 2)]\\n```\\n"}}	[]	4aeca440-512b-4623-8372-2c5cdb48cddd	\N
d513ea09-4d3c-41b6-a7f5-b728629303ac	Family Tree (Prolog)	Given facts `parent(Parent, Child)`, write the rules:\n\n- `grandparent(G, C)` — G is a grandparent of C\n- `sibling(A, B)` — A and B share a parent and are different people\n- `ancestor(A, D)` — A is a parent, grandparent, great-grandparent... of D\n\nThe facts are in the starter code — keep them.	parent(vera, ana).\nparent(vera, ivo).\nparent(ana, lea).\nparent(lea, mila).\n\n% TODO: grandparent/2, sibling/2, ancestor/2\n	parent(vera, ana).\nparent(vera, ivo).\nparent(ana, lea).\nparent(lea, mila).\n\ngrandparent(G, C) :- parent(G, P), parent(P, C).\nsibling(A, B) :- parent(P, A), parent(P, B), A \\== B.\nancestor(A, D) :- parent(A, D).\nancestor(A, D) :- parent(A, X), ancestor(X, D).\n	prolog	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.266369	2026-10-27 21:19:15.390651	t	code	en	{"mk": {"title": "Семејно стебло (Prolog)", "description": "Дадени се факти `parent(Parent, Child)`. Напишете ги правилата:\\n\\n- `grandparent(G, C)` — G е баба или дедо на C\\n- `sibling(A, B)` — A и B имаат заеднички родител и се различни лица\\n- `ancestor(A, D)` — A е родител, баба/дедо, прабаба/прадедо... на D\\n\\nФактите се во почетниот код — задржете ги.\\n"}}	[]	aff098bb-b566-4bab-a216-188f334d956e	\N
d9d6fe0c-ceec-4314-b841-0af653915f67	Тотално различни броеви	Од стандарден влез се внесуваат два цели броја N и Х. \n\nДа се најде најблискот број помал од N коj е **тотално различен** од бројот Х. \n\nЕден број е тотално различен од друг ако и само ако во него не се појавува ниту една од цифрите на другиот број.\n\n**Задачата да се реши без употреба на низи и матрици.**		#include <stdio.h>\n\nint main() {\n    int N, X;\n    scanf("%d %d", &N, &X);\n    while(1) {\n        --N;\n        int temp = N;\n        int td = 1;\n        while(temp != 0) {\n            int digit = temp % 10;\n            int x = X;\n            while(x != 0) {\n                if(digit == x % 10) {\n                    td = 0;\n                    break;\n                }\n                x /= 10;\n            }\n            if(!td) break;\n            temp /= 10;\n        }\n        if(td) break;\n    }\n    printf("%d", N);\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.27952	2026-10-28 11:16:05.279524	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
e71019b1-1019-4075-9a5b-a317aaf4dd0f	Релациона шема — библиотека	Нацртајте **релациона шема** за библиотека.\n\n- **Член**(id, име, email) — примарен клуч *id*.\n- **Книга**(isbn, наслов, автор) — примарен клуч *isbn*.\n- **Позајмица**(id, член_id, книга_isbn, датум) — примарен клуч *id*; *член_id* е надворешен клуч кон Член, *книга_isbn* кон Книга.		{\n "kind": "relational",\n "nodes": [\n  {\n   "id": "clen",\n   "name": "Член",\n   "type": "table",\n   "x": 40.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "id",\n     "type": "INT",\n     "visibility": "-",\n     "pk": true,\n     "fk": false\n    },\n    {\n     "name": "име",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "ime",\n      "name"\n     ]\n    },\n    {\n     "name": "email",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": false,\n     "fk": false\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Member",\n    "clen"\n   ]\n  },\n  {\n   "id": "kniga",\n   "name": "Книга",\n   "type": "table",\n   "x": 560.0,\n   "y": 40.0,\n   "attributes": [\n    {\n     "name": "isbn",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": true,\n     "fk": false\n    },\n    {\n     "name": "наслов",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "naslov",\n      "title"\n     ]\n    },\n    {\n     "name": "автор",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "avtor",\n      "author"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Book"\n   ]\n  },\n  {\n   "id": "poz",\n   "name": "Позајмица",\n   "type": "table",\n   "x": 300.0,\n   "y": 300.0,\n   "attributes": [\n    {\n     "name": "id",\n     "type": "INT",\n     "visibility": "-",\n     "pk": true,\n     "fk": false\n    },\n    {\n     "name": "член_id",\n     "type": "INT",\n     "visibility": "-",\n     "pk": false,\n     "fk": true,\n     "aliases": [\n      "clen_id",\n      "member_id"\n     ]\n    },\n    {\n     "name": "книга_isbn",\n     "type": "VARCHAR",\n     "visibility": "-",\n     "pk": false,\n     "fk": true,\n     "aliases": [\n      "kniga_isbn",\n      "book_isbn"\n     ]\n    },\n    {\n     "name": "датум",\n     "type": "DATE",\n     "visibility": "-",\n     "pk": false,\n     "fk": false,\n     "aliases": [\n      "datum",\n      "date"\n     ]\n    }\n   ],\n   "methods": [],\n   "aliases": [\n    "Loan"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "k1",\n   "from": "poz",\n   "to": "clen",\n   "kind": "foreign_key",\n   "fromMult": "N",\n   "toMult": "1",\n   "label": ""\n  },\n  {\n   "id": "k2",\n   "from": "poz",\n   "to": "kniga",\n   "kind": "foreign_key",\n   "fromMult": "N",\n   "toMult": "1",\n   "label": ""\n  }\n ]\n}	relational	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.378238	2026-10-27 21:19:15.390652	t	code	mk	{"en": {"title": "Relational schema — library", "description": "Draw a **relational schema** for a library.\\n\\n- **Member** (`Член`)(id, name, email) — primary key *id*.\\n- **Book** (`Книга`)(isbn, title, author) — primary key *isbn*.\\n- **Loan** (`Позајмица`)(id, член_id, книга_isbn, date) — primary key *id*; *член_id* is a foreign key to Member, *книга_isbn* to Book."}}	[]	d3e9fc2c-8656-492d-9362-f7c24151b4a3	\N
e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	Компонентен дијаграм — онлајн продавница	Нацртајте **компонентен дијаграм** за онлајн продавница.\n\n- Компонентата **Веб апликација** ја користи компонентата **Сервис за нарачки**.\n- **Сервис за плаќање** го нуди интерфејсот **IПлаќање** (реализација).\n- **Сервис за нарачки** го користи интерфејсот **IПлаќање** (зависност).		{\n "kind": "component",\n "nodes": [\n  {\n   "id": "web",\n   "name": "Веб апликација",\n   "type": "component",\n   "x": 40.0,\n   "y": 60.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Web app",\n    "Web application"\n   ]\n  },\n  {\n   "id": "nar",\n   "name": "Сервис за нарачки",\n   "type": "component",\n   "x": 360.0,\n   "y": 60.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Order service"\n   ]\n  },\n  {\n   "id": "ipl",\n   "name": "IПлаќање",\n   "type": "interface",\n   "x": 400.0,\n   "y": 260.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "IPayment",\n    "IPlakjanje"\n   ]\n  },\n  {\n   "id": "pl",\n   "name": "Сервис за плаќање",\n   "type": "component",\n   "x": 360.0,\n   "y": 400.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Payment service"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "d1",\n   "from": "web",\n   "to": "nar",\n   "kind": "dependency",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "d2",\n   "from": "nar",\n   "to": "ipl",\n   "kind": "dependency",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "r1",\n   "from": "pl",\n   "to": "ipl",\n   "kind": "realization",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	component	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.373028	2026-10-27 21:19:15.390652	t	code	mk	{"en": {"title": "Component diagram — online shop", "description": "Draw a **component diagram** for an online shop.\\n\\n- **Web app** (`Веб апликација`) uses **Order service** (`Сервис за нарачки`).\\n- **Payment service** (`Сервис за плаќање`) provides the interface **IPayment** (`IПлаќање`).\\n- **Order service** requires **IPayment**."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
ec94d5db-9cba-4310-bc65-63fdc44d6a38	Activity дијаграм — банкомат	Нацртајте **activity дијаграм** за подигање пари од банкомат.\n\n1. Корисникот *внесува картичка*, па *внесува PIN*.\n2. Одлука **PIN точен?** — ако не, повторно се внесува PIN; ако да, *избира износ*.\n3. Потоа паралелно (fork/join): *исплата на пари* и *печатење потврда*.\n4. На крај *враќање на картичката*.		{\n "kind": "activity",\n "nodes": [\n  {\n   "id": "i",\n   "name": "",\n   "type": "initial",\n   "x": 180.0,\n   "y": 20.0,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "kart",\n   "name": "Внеси картичка",\n   "type": "action",\n   "x": 100.0,\n   "y": 80.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Insert card"\n   ]\n  },\n  {\n   "id": "pin",\n   "name": "Внеси PIN",\n   "type": "action",\n   "x": 100.0,\n   "y": 180.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Enter PIN"\n   ]\n  },\n  {\n   "id": "dec",\n   "name": "PIN точен?",\n   "type": "decision",\n   "x": 140.0,\n   "y": 280.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "PIN correct?"\n   ]\n  },\n  {\n   "id": "iznos",\n   "name": "Избери износ",\n   "type": "action",\n   "x": 100.0,\n   "y": 380.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Choose amount"\n   ]\n  },\n  {\n   "id": "fork",\n   "name": "",\n   "type": "fork",\n   "x": 60.0,\n   "y": 480.0,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "isplata",\n   "name": "Исплати пари",\n   "type": "action",\n   "x": 0.0,\n   "y": 540.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Pay out",\n    "Dispense cash"\n   ]\n  },\n  {\n   "id": "potvrda",\n   "name": "Испечати потврда",\n   "type": "action",\n   "x": 240.0,\n   "y": 540.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Print receipt"\n   ]\n  },\n  {\n   "id": "join",\n   "name": "",\n   "type": "join",\n   "x": 60.0,\n   "y": 640.0,\n   "attributes": [],\n   "methods": []\n  },\n  {\n   "id": "vrati",\n   "name": "Врати картичка",\n   "type": "action",\n   "x": 100.0,\n   "y": 700.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Return card"\n   ]\n  },\n  {\n   "id": "f",\n   "name": "",\n   "type": "final",\n   "x": 180.0,\n   "y": 800.0,\n   "attributes": [],\n   "methods": []\n  }\n ],\n "edges": [\n  {\n   "id": "f0",\n   "from": "i",\n   "to": "kart",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f1",\n   "from": "kart",\n   "to": "pin",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f2",\n   "from": "pin",\n   "to": "dec",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f3",\n   "from": "dec",\n   "to": "iznos",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": "[да]"\n  },\n  {\n   "id": "f4",\n   "from": "dec",\n   "to": "pin",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": "[не]"\n  },\n  {\n   "id": "f5",\n   "from": "iznos",\n   "to": "fork",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f6",\n   "from": "fork",\n   "to": "isplata",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f7",\n   "from": "fork",\n   "to": "potvrda",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f8",\n   "from": "isplata",\n   "to": "join",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f9",\n   "from": "potvrda",\n   "to": "join",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f10",\n   "from": "join",\n   "to": "vrati",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "f11",\n   "from": "vrati",\n   "to": "f",\n   "kind": "flow",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	activity	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.370681	2026-10-27 21:19:15.390653	t	code	mk	{"en": {"title": "Activity diagram — ATM withdrawal", "description": "Draw an **activity diagram** for withdrawing money from an ATM.\\n\\n1. The user *inserts the card* (`Внеси картичка`), then *enters the PIN* (`Внеси PIN`).\\n2. Decision **PIN correct?** (`PIN точен?`) — if not, the PIN is entered again; if yes, the user *chooses the amount* (`Избери износ`).\\n3. Then in parallel (fork/join): *pay out* (`Исплати пари`) and *print a receipt* (`Испечати потврда`).\\n4. Finally *return the card* (`Врати картичка`)."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
ef07c143-c0e4-4278-919d-14d823b4a084	Average Grade per Student (SQL)	The database has two tables:\n\n| student | |\n|---|---|\n| `id` | INTEGER, primary key |\n| `ime` | TEXT — name |\n| `smer` | TEXT — study programme |\n\n| ocena | |\n|---|---|\n| `student_id` | INTEGER → `student.id` |\n| `predmet` | TEXT — course |\n| `ocena` | INTEGER — grade 5–10 |\n\nWrite a query that returns, for every student **who has at least one grade**, their **name** and their\n**average grade**, sorted from the **highest average to the lowest**.\n\nExpected columns: `ime`, `prosek`.\n	SELECT\n  -- TODO\n;\n	SELECT s.ime, AVG(o.ocena) AS prosek\nFROM student s\nJOIN ocena o ON o.student_id = s.id\nGROUP BY s.id, s.ime\nORDER BY prosek DESC;\n	sql	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.257802	2026-10-27 21:19:15.390654	t	code	en	{"mk": {"title": "Просечна оценка по студент (SQL)", "description": "Базата има две табели:\\n\\n| student | |\\n|---|---|\\n| `id` | INTEGER, примарен клуч |\\n| `ime` | TEXT — име |\\n| `smer` | TEXT — студиска програма |\\n\\n| ocena | |\\n|---|---|\\n| `student_id` | INTEGER → `student.id` |\\n| `predmet` | TEXT — предмет |\\n| `ocena` | INTEGER — оценка 5–10 |\\n\\nНапишете барање што за секој студент **што има барем една оценка** ги враќа неговото **име** и\\n**просечната оценка**, подредени од **највисокиот кон најнискиот просек**.\\n\\nОчекувани колони: `ime`, `prosek`.\\n"}}	[]	d3e9fc2c-8656-492d-9362-f7c24151b4a3	\N
fa8cca46-d302-42cb-9bdd-7ac52cf1e265	Shape Hierarchy (OOP)	Design a class hierarchy for geometric shapes.\n\n**Requirements:**\n\n1. Abstract base class `Shape` with:\n   - Pure virtual method `double area() const`\n   - Pure virtual method `double perimeter() const`\n   - Virtual method `void print() const` that prints: `Shape: area=<area>, perimeter=<perimeter>` (2 decimal places)\n\n2. Class `Circle` inheriting from `Shape`:\n   - Constructor `Circle(double radius)`\n   - Implement `area()` → π × r²\n   - Implement `perimeter()` → 2 × π × r\n   - Use `M_PI` for π\n\n3. Class `Rectangle` inheriting from `Shape`:\n   - Constructor `Rectangle(double width, double height)`\n   - Implement `area()` → width × height\n   - Implement `perimeter()` → 2 × (width + height)\n\n**Example output:**\n```\nShape: area=78.54, perimeter=31.42\nShape: area=12.00, perimeter=14.00\n```\n	#include <iostream>\n#include <cmath>\n#include <iomanip>\nusing namespace std;\n\n// TODO: implement Shape, Circle, Rectangle\n	#include <iostream>\n#include <cmath>\n#include <iomanip>\nusing namespace std;\n\nclass Shape {\npublic:\n    virtual double area() const = 0;\n    virtual double perimeter() const = 0;\n    virtual void print() const {\n        cout << fixed << setprecision(2)\n             << "Shape: area=" << area()\n             << ", perimeter=" << perimeter() << endl;\n    }\n    virtual ~Shape() {}\n};\n\nclass Circle : public Shape {\n    double radius;\npublic:\n    Circle(double r) : radius(r) {}\n    double area() const override { return M_PI * radius * radius; }\n    double perimeter() const override { return 2 * M_PI * radius; }\n};\n\nclass Rectangle : public Shape {\n    double width, height;\npublic:\n    Rectangle(double w, double h) : width(w), height(h) {}\n    double area() const override { return width * height; }\n    double perimeter() const override { return 2 * (width + height); }\n};\n	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.251099	2026-10-27 21:19:15.390654	t	code	en	{"mk": {"title": "Хиерархија на геометриски форми (ООП)", "description": "Дизајнирајте хиерархија на класи за геометриски форми.\\n\\n**Барања:**\\n\\n1. Апстрактна основна класа `Shape` со:\\n   - чисто виртуелен метод `double area() const`\\n   - чисто виртуелен метод `double perimeter() const`\\n   - виртуелен метод `void print() const` што печати: `Shape: area=<area>, perimeter=<perimeter>` (2 децимали)\\n\\n2. Класа `Circle` што наследува од `Shape`:\\n   - конструктор `Circle(double radius)`\\n   - `area()` → π × r²\\n   - `perimeter()` → 2 × π × r\\n   - за π користете `M_PI`\\n\\n3. Класа `Rectangle` што наследува од `Shape`:\\n   - конструктор `Rectangle(double width, double height)`\\n   - `area()` → width × height\\n   - `perimeter()` → 2 × (width + height)\\n\\n**Пример излез:**\\n```\\nShape: area=78.54, perimeter=31.42\\nShape: area=12.00, perimeter=14.00\\n```\\n"}}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
fed45caf-a572-4634-bdfc-389d091fe71c	Use case дијаграм — студентски сервис	Нацртајте **use case дијаграм** за студентски сервис.\n\n- **Студентот** може да се *пријави на испит* и да ги *прегледа оценките*.\n- **Референтот** ги *внесува оценките*.\n- Пријавата на испит секогаш вклучува *најава* (`«include»`).\n- При пријавата студентот може (но не мора) да *плати со картичка* (`«extend»`).\n- Случаите на употреба се во границата на системот **Студентски сервис**.		{\n "kind": "usecase",\n "nodes": [\n  {\n   "id": "sys",\n   "name": "Студентски сервис",\n   "type": "system",\n   "x": 220.0,\n   "y": 20.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Student services"\n   ],\n   "w": 620.0,\n   "h": 470.0\n  },\n  {\n   "id": "st",\n   "name": "Студент",\n   "type": "actor",\n   "x": 60.0,\n   "y": 120.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Student"\n   ]\n  },\n  {\n   "id": "ref",\n   "name": "Референт",\n   "type": "actor",\n   "x": 60.0,\n   "y": 360.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Clerk",\n    "Referent"\n   ]\n  },\n  {\n   "id": "prij",\n   "name": "Пријава на испит",\n   "type": "usecase",\n   "x": 300.0,\n   "y": 80.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Register for an exam",\n    "Exam registration"\n   ]\n  },\n  {\n   "id": "naj",\n   "name": "Најава",\n   "type": "usecase",\n   "x": 620.0,\n   "y": 80.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Log in",\n    "Login"\n   ]\n  },\n  {\n   "id": "kart",\n   "name": "Плаќање со картичка",\n   "type": "usecase",\n   "x": 520.0,\n   "y": 220.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Pay by card"\n   ]\n  },\n  {\n   "id": "pregled",\n   "name": "Преглед на оценки",\n   "type": "usecase",\n   "x": 300.0,\n   "y": 300.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "View grades"\n   ]\n  },\n  {\n   "id": "vnes",\n   "name": "Внес на оценки",\n   "type": "usecase",\n   "x": 300.0,\n   "y": 400.0,\n   "attributes": [],\n   "methods": [],\n   "aliases": [\n    "Enter grades"\n   ]\n  }\n ],\n "edges": [\n  {\n   "id": "e1",\n   "from": "st",\n   "to": "prij",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "e2",\n   "from": "st",\n   "to": "pregled",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "e3",\n   "from": "ref",\n   "to": "vnes",\n   "kind": "association",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "e4",\n   "from": "prij",\n   "to": "naj",\n   "kind": "include",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  },\n  {\n   "id": "e5",\n   "from": "kart",\n   "to": "prij",\n   "kind": "extend",\n   "fromMult": "",\n   "toMult": "",\n   "label": ""\n  }\n ]\n}	usecase	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 21:19:15.361219	2026-10-27 21:19:15.390656	t	code	mk	{"en": {"title": "Use case diagram — student services", "description": "Draw a **use case diagram** for student services.\\n\\n- A **student** can *register for an exam* and *view grades*.\\n- A **clerk** *enters grades*.\\n- Registering for an exam always includes *logging in* (`«include»`).\\n- While registering, the student may *pay by card* (`«extend»`).\\n- The use cases are inside the system boundary **Student services**."}}	[]	6af3c09a-d677-48ed-8426-08bc0cd302cc	\N
7deda453-9f15-447d-893c-6a1efcbe2b29	Git: прво складиште и commit	Напишете ги **git командите** што прават ново складиште.\n\n1. Направете складиште во тековната папка.\n2. Направете `README.md` со содржина `# ALE` и `.gitignore` со еден ред: `*.log`.\n3. Направете датотека `debug.log` (содржината не е важна) — таа **не** смее да влезе во складиштето.\n4. Направете **еден** commit со порака `Initial commit` во кој се `README.md` и `.gitignore`.\n\nНа крај работната папка треба да е „чиста“ (ништо неснимено, освен игнорираниот лог).\n	# твоите git команди\ngit init\n	git init\necho '# ALE' > README.md\necho '*.log' > .gitignore\necho 'debug' > debug.log\ngit add .\ngit commit -m 'Initial commit'\n	git	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.83188	2026-10-27 23:31:32.831883	t	code	mk	{"en": {"title": "Git: first repository and commit", "description": "Write the **git commands** that create a new repository.\\n\\n1. Create a repository in the current folder.\\n2. Create `README.md` containing `# ALE` and `.gitignore` with one line: `*.log`.\\n3. Create a file `debug.log` (any content) — it must **not** get into the repository.\\n4. Make **one** commit with the message `Initial commit` containing `README.md` and `.gitignore`.\\n\\nAt the end the working tree must be clean (nothing unsaved, except the ignored log).\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
47a54cea-9655-42a8-9dc5-e78f5d827b55	Git: гранка за нова функционалност и merge	Работа со **гранки**.\n\n1. Направете складиште со датотека `app.txt` (содржина `v1`) и commit `Start`.\n2. Направете гранка **`feature/login`**, во неа датотека `login.txt` (содржина `login`) и commit `Add login`.\n3. Вратете се на `main` и спојте ја гранката **со merge commit** (не fast-forward) со порака `Merge feature/login`.\n\nНа крај сте на `main`, гранката `feature/login` постои, а `login.txt` е на `main`.\n	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\n# продолжи…\n	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\ngit switch -c feature/login\necho login > login.txt\ngit add login.txt\ngit commit -m 'Add login'\ngit switch main\ngit merge --no-ff feature/login -m 'Merge feature/login'\n	git	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.839797	2026-10-27 23:31:32.8398	t	code	mk	{"en": {"title": "Git: a feature branch and a merge", "description": "Working with **branches**.\\n\\n1. Create a repository with a file `app.txt` (content `v1`) and a commit `Start`.\\n2. Create a branch **`feature/login`**, add `login.txt` (content `login`) there and commit `Add login`.\\n3. Go back to `main` and merge the branch **with a merge commit** (not fast-forward) with the message `Merge feature/login`.\\n\\nAt the end you are on `main`, the branch `feature/login` exists and `login.txt` is on `main`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
31f3e051-1bca-4de5-a3a5-0061316c09ee	Git: таг за издание и revert	Издание и поправка без бришење историја.\n\n1. Складиште со `app.txt` = `v1`, commit `Release 1.0`.\n2. **Анотиран** таг `v1.0` со порака `First release` на тој commit.\n3. Сменете `app.txt` во `broken` и commit `Experiment`.\n4. Експериментот не успеал: **поништете го со `git revert`** (не со `reset`), со стандардната порака.\n\nНа крај `app.txt` пак е `v1`, а во историјата има три commit-и.\n	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m 'Release 1.0'\n	git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m 'Release 1.0'\ngit tag -a v1.0 -m 'First release'\necho broken > app.txt\ngit commit -am Experiment\ngit revert --no-edit HEAD\n	git	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.841322	2026-10-27 23:31:32.841323	t	code	mk	{"en": {"title": "Git: a release tag and a revert", "description": "A release and a fix without rewriting history.\\n\\n1. A repository with `app.txt` = `v1`, commit `Release 1.0`.\\n2. An **annotated** tag `v1.0` with the message `First release` on that commit.\\n3. Change `app.txt` to `broken` and commit `Experiment`.\\n4. The experiment failed: **undo it with `git revert`** (not `reset`), with the default message.\\n\\nAt the end `app.txt` is `v1` again and the history has three commits.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
8c95a446-f74e-4c44-b6d2-4c562deb13eb	Git: решавање конфликт при merge	Двајца ја менуваат истата линија — решете го **конфликтот**.\n\n1. Складиште со `config.txt` = `port=8000`, commit `Base`.\n2. Гранка `dev`: сменете во `port=9000`, commit `Dev port`.\n3. На `main`: сменете во `port=8080`, commit `Main port`.\n4. Спојте `dev` во `main` — ќе има конфликт. Решете го така што `config.txt` ќе содржи **само** `port=9000`,\n   и завршете го merge-от со commit `Resolve port`.\n	git init\necho port=8000 > config.txt\ngit add config.txt\ngit commit -m Base\n	git init\necho port=8000 > config.txt\ngit add config.txt\ngit commit -m Base\ngit switch -c dev\necho port=9000 > config.txt\ngit commit -am 'Dev port'\ngit switch main\necho port=8080 > config.txt\ngit commit -am 'Main port'\ngit merge dev || true\necho port=9000 > config.txt\ngit add config.txt\ngit commit -m 'Resolve port'\n	git	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.842994	2026-10-27 23:31:32.842997	t	code	mk	{"en": {"title": "Git: resolving a merge conflict", "description": "Two people change the same line — resolve the **conflict**.\\n\\n1. A repository with `config.txt` = `port=8000`, commit `Base`.\\n2. Branch `dev`: change it to `port=9000`, commit `Dev port`.\\n3. On `main`: change it to `port=8080`, commit `Main port`.\\n4. Merge `dev` into `main` — there will be a conflict. Resolve it so that `config.txt` contains **only** `port=9000`,\\n   and finish the merge with the commit `Resolve port`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
909d3e02-e5fc-432e-b642-fe1ccae49b99	Bash: анализа на лог од веб-сервер	Скрипта што чита **лог од веб-сервер** од стандарден влез. Секоја линија е:\n`IP МЕТОД ПАТЕКА СТАТУС`, на пр. `10.0.0.1 GET /index.html 200`.\n\nИспечатете три линии:\n```\nrequests: <вкупно барања>\nerrors: <барања со статус 500 или повеќе>\ntop: <IP-адресата со најмногу барања>\n```\n(при еднаков број, помалата IP по абецеден ред). Празен влез: `requests: 0`, `errors: 0`, `top: -`.\n	#!/usr/bin/env bash\n# читај од stdin\n	#!/usr/bin/env bash\nawk '\n  NF >= 4 { n++; if ($4 >= 500) e++; c[$1]++ }\n  END {\n    top = "-"; best = 0\n    for (ip in c) if (c[ip] > best || (c[ip] == best && ip < top)) { best = c[ip]; top = ip }\n    printf "requests: %d\\nerrors: %d\\ntop: %s\\n", n, e, top\n  }'\n	bash	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.845549	2026-10-27 23:31:32.845551	t	code	mk	{"en": {"title": "Bash: analysing a web server log", "description": "A script that reads a **web server log** from standard input. Each line is:\\n`IP METHOD PATH STATUS`, e.g. `10.0.0.1 GET /index.html 200`.\\n\\nPrint three lines:\\n```\\nrequests: <total requests>\\nerrors: <requests with status 500 or more>\\ntop: <the IP with the most requests>\\n```\\n(on a tie, the alphabetically smaller IP). Empty input: `requests: 0`, `errors: 0`, `top: -`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
da92593b-6b0d-4f39-84f6-2ff4e820d9b2	Bash: функција за health check	Напишете функција **`health`** што добива HTTP статус-код и печати состојба на сервисот:\n- `200`–`299` → `UP`\n- `300`–`499` → `DEGRADED`\n- `500` и повеќе, или нешто што не е број → `DOWN`\n\nПотоа функција **`summary`** што добива повеќе кодови и печати колку се `UP`, `DEGRADED`, `DOWN`\nво формат `UP=2 DEGRADED=1 DOWN=0`.\n	health() {\n  :\n}\n\nsummary() {\n  :\n}\n	health() {\n  local c=$1\n  if ! [[ $c =~ ^[0-9]+$ ]]; then echo DOWN; return; fi\n  if (( c >= 200 && c < 300 )); then echo UP\n  elif (( c >= 300 && c < 500 )); then echo DEGRADED\n  else echo DOWN; fi\n}\n\nsummary() {\n  local up=0 deg=0 down=0 s\n  for c in "$@"; do\n    s=$(health "$c")\n    case $s in UP) ((up++)) ;; DEGRADED) ((deg++)) ;; *) ((down++)) ;; esac\n  done\n  echo "UP=$up DEGRADED=$deg DOWN=$down"\n}\n	bash	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.847025	2026-10-27 23:31:32.847027	t	code	mk	{"en": {"title": "Bash: a health-check function", "description": "Write a function **`health`** that gets an HTTP status code and prints the state of the service:\\n- `200`–`299` → `UP`\\n- `300`–`499` → `DEGRADED`\\n- `500` or more, or something that is not a number → `DOWN`\\n\\nThen a function **`summary`** that gets several codes and prints how many are `UP`, `DEGRADED`, `DOWN`\\nin the form `UP=2 DEGRADED=1 DOWN=0`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
7f87f39b-7e29-4c9e-bb37-4ab66877a897	Dockerfile за Python веб-апликација	Напишете **Dockerfile** за Flask апликација (`app.py`, зависности во `requirements.txt`).\n\n- основна слика **`python:3.12-slim`**, работна папка `/app`;\n- прво копирајте **само** `requirements.txt` и инсталирајте ги зависностите со `pip install --no-cache-dir`,\n  па дури потоа копирајте го остатокот од кодот (за подобар кеш на слоевите);\n- апликацијата **не** работи како `root`: направете корисник `app` и префрлете се на него;\n- `EXPOSE 8000`;\n- стартувајте со **gunicorn** во JSON форма: `["gunicorn", "-b", "0.0.0.0:8000", "app:app"]`.\n	FROM python:3.12-slim\n\n# …\n	FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nRUN useradd --create-home app\nUSER app\nEXPOSE 8000\nCMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]\n	dockerfile	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.848514	2026-10-27 23:31:32.848515	t	code	mk	{"en": {"title": "Dockerfile for a Python web app", "description": "Write a **Dockerfile** for a Flask app (`app.py`, dependencies in `requirements.txt`).\\n\\n- base image **`python:3.12-slim`**, working directory `/app`;\\n- first copy **only** `requirements.txt` and install the dependencies with `pip install --no-cache-dir`,\\n  and only then copy the rest of the code (better layer caching);\\n- the app does **not** run as `root`: create a user `app` and switch to it;\\n- `EXPOSE 8000`;\\n- start with **gunicorn** in JSON form: `[\\"gunicorn\\", \\"-b\\", \\"0.0.0.0:8000\\", \\"app:app\\"]`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	Хексадецимални цифри	Од стандарден влез се читаат непознат број на хексадецимални цифри се додека не се внесе точка (.). Ваша задача е да го пресметате декадниот збир на внесените хексадецимални цифри. Доколку добиениот декаден збир е делив со 16 се печати `Pogodok`. Доколку истиот тој збир покрај што е делив со 16 плус завршува на 16 (последните цифри му се 1 и 6\\), се печати `Poln pogodok` инаку се печати самиот збир. \n\n**Пример:**\n\nвлез: A 7 F 2 0 c A 5\n\nизлез: 61\n\n(61 \\= 10 \\+ 7 \\+ 15 \\+ 2 \\+ 0 \\+ 12 \\+ 10 \\+ 5, бројот не е делив со 16, ниту пак последните цифри му се 1,6\\)		#include <stdio.h>\n\nint main() {\n\tchar c;\n\tint n = 0;\n\twhile(scanf("%c",&c)) {\n        if(c == '.')\n            break;\n\t\tif(c >= '0'&&c <= '9') {\n\t\t\tn = n + c - '0';\n\t\t}\n\t\tif(c >= 'A'&&c <= 'F') {\n\t\t\tn = n + (10 + c - 'A');\n\t\t}\n\t\tif(c >= 'a'&&c <= 'f') {\n\t\t\tn = n + (10 + c - 'a');\n\t\t}\n\t}\n\n\tif(n % 16 == 0 && n % 100 == 16) {\n\t\tprintf("Poln pogodok\\n");\n\t} else if(n % 16 == 0) {\n\t\tprintf("Pogodok\\n");\n\t} else {\n\t\tprintf("%d\\n", n);\n\t}\n    //printf("%d\\n",n);\n\treturn 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.2815	2026-10-28 11:16:05.281504	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
8caaa947-5656-4014-b78a-cd573199ac32	Повеќестепен Dockerfile за фронтенд	**Multi-stage build** за React/Vite фронтенд: се гради во Node, а се служи со nginx.\n\n1. Прв степен со име **`build`**: `node:22-alpine`, `WORKDIR /app`, копирајте `package.json` и\n   `package-lock.json`, `npm ci` (не `npm install`), копирајте го кодот, `npm run build`.\n2. Втор степен: **`nginx:1.27-alpine`**; копирајте **од степенот `build`** папката `/app/dist` во\n   `/usr/share/nginx/html`; `EXPOSE 80`.\n\nВо конечната слика нема Node — само статичните датотеки и nginx.\n	FROM node:22-alpine\nWORKDIR /app\n	FROM node:22-alpine AS build\nWORKDIR /app\nCOPY package.json package-lock.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\n\nFROM nginx:1.27-alpine\nCOPY --from=build /app/dist /usr/share/nginx/html\nEXPOSE 80\n	dockerfile	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.849869	2026-10-27 23:31:32.84987	t	code	mk	{"en": {"title": "Multi-stage Dockerfile for a front end", "description": "A **multi-stage build** for a React/Vite front end: built in Node, served by nginx.\\n\\n1. First stage named **`build`**: `node:22-alpine`, `WORKDIR /app`, copy `package.json` and `package-lock.json`,\\n   `npm ci` (not `npm install`), copy the code, `npm run build`.\\n2. Second stage: **`nginx:1.27-alpine`**; copy **from the `build` stage** the folder `/app/dist` to\\n   `/usr/share/nginx/html`; `EXPOSE 80`.\\n\\nThe final image has no Node — only the static files and nginx.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
c3fed460-c356-44b9-8a49-ec90e1df2366	GitHub Actions: CI за Python проект	Напишете **GitHub Actions workflow** (`.github/workflows/ci.yml`) со име `CI`.\n\n- се стартува при **push** и **pull_request** на гранката `main`;\n- job **`test`** на `ubuntu-latest`;\n- чекори: `actions/checkout@v4`; `actions/setup-python@v5` со `python-version: "3.12"`;\n  `pip install -r requirements.txt`; `pytest`.\n	name: CI\n\n	name: CI\non:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n      - run: pip install -r requirements.txt\n      - run: pytest\n	yaml	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.85123	2026-10-27 23:31:32.851231	t	code	mk	{"en": {"title": "GitHub Actions: CI for a Python project", "description": "Write a **GitHub Actions workflow** (`.github/workflows/ci.yml`) named `CI`.\\n\\n- it runs on **push** and **pull_request** to the branch `main`;\\n- a job **`test`** on `ubuntu-latest`;\\n- steps: `actions/checkout@v4`; `actions/setup-python@v5` with `python-version: \\"3.12\\"`;\\n  `pip install -r requirements.txt`; `pytest`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
dac4643c-3dd9-4645-b325-4a0aae57b7e3	docker-compose: апликација и база	Напишете **`docker-compose.yml`** за веб-апликација и PostgreSQL.\n\n- сервис **`web`**: се гради од тековната папка (`build: .`), порта `8000:8000`, зависи од `db`,\n  околина `DATABASE_URL=postgresql://app:secret@db:5432/app`;\n- сервис **`db`**: слика `postgres:16`, околина `POSTGRES_USER=app`, `POSTGRES_PASSWORD=secret`, `POSTGRES_DB=app`,\n  податоците во именуван волумен **`db-data`** монтиран на `/var/lib/postgresql/data`;\n- волуменот `db-data` е деклариран на дното на датотеката.\n	services:\n  web:\n    build: .\n	services:\n  web:\n    build: .\n    ports:\n      - "8000:8000"\n    depends_on:\n      - db\n    environment:\n      DATABASE_URL: postgresql://app:secret@db:5432/app\n  db:\n    image: postgres:16\n    environment:\n      POSTGRES_USER: app\n      POSTGRES_PASSWORD: secret\n      POSTGRES_DB: app\n    volumes:\n      - db-data:/var/lib/postgresql/data\nvolumes:\n  db-data:\n	yaml	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.852552	2026-10-27 23:31:32.852554	t	code	mk	{"en": {"title": "docker-compose: an app and a database", "description": "Write a **`docker-compose.yml`** for a web app and PostgreSQL.\\n\\n- service **`web`**: built from the current folder (`build: .`), port `8000:8000`, depends on `db`,\\n  environment `DATABASE_URL=postgresql://app:secret@db:5432/app`;\\n- service **`db`**: image `postgres:16`, environment `POSTGRES_USER=app`, `POSTGRES_PASSWORD=secret`, `POSTGRES_DB=app`,\\n  its data in a named volume **`db-data`** mounted at `/var/lib/postgresql/data`;\\n- the volume `db-data` is declared at the bottom of the file.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
9bad1ab2-d43c-4c3f-902d-cdfacbd55e20	Kubernetes: Deployment и Service	Два Kubernetes објекти во **една** датотека (одделени со `---`).\n\n**Deployment** `ale-web`:\n- `replicas: 3`, селектор и ознака на подовите `app: ale-web`;\n- контејнер `web` со слика `ghcr.io/finki/ale-web:1.0`, `containerPort: 8000`;\n- ресурси: `requests` `cpu: 100m`, `memory: 128Mi`; `limits` `memory: 256Mi`;\n- `readinessProbe` со `httpGet` на патеката `/health`, порта `8000`.\n\n**Service** `ale-web`: тип `ClusterIP`, порта `80` → `targetPort: 8000`, селектор `app: ale-web`.\n	apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: ale-web\n	apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: ale-web\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: ale-web\n  template:\n    metadata:\n      labels:\n        app: ale-web\n    spec:\n      containers:\n        - name: web\n          image: ghcr.io/finki/ale-web:1.0\n          ports:\n            - containerPort: 8000\n          resources:\n            requests:\n              cpu: 100m\n              memory: 128Mi\n            limits:\n              memory: 256Mi\n          readinessProbe:\n            httpGet:\n              path: /health\n              port: 8000\n---\napiVersion: v1\nkind: Service\nmetadata:\n  name: ale-web\nspec:\n  type: ClusterIP\n  selector:\n    app: ale-web\n  ports:\n    - port: 80\n      targetPort: 8000\n	yaml	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.854026	2026-10-27 23:31:32.854028	t	code	mk	{"en": {"title": "Kubernetes: a Deployment and a Service", "description": "Two Kubernetes objects in **one** file (separated by `---`).\\n\\n**Deployment** `ale-web`:\\n- `replicas: 3`, selector and pod label `app: ale-web`;\\n- a container `web` with the image `ghcr.io/finki/ale-web:1.0`, `containerPort: 8000`;\\n- resources: `requests` `cpu: 100m`, `memory: 128Mi`; `limits` `memory: 256Mi`;\\n- a `readinessProbe` with `httpGet` on the path `/health`, port `8000`.\\n\\n**Service** `ale-web`: type `ClusterIP`, port `80` → `targetPort: 8000`, selector `app: ale-web`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
663df95a-04b2-45e8-8e0b-6f16f4594318	Цик-цак1	Цик\\-цак е број за кој што важи дека за секој пар соседни цифри, тие се наизменично поголеми односно помали една во однос на друга. На пример, ако бројот x е составен од цифрите a, b, c, d и е, тогаш за нив важи:\n\n```cpp\na>b, b<c, c>d, d<e или a<b, b>c, c<d, d>e\n\nПр. 343, 4624, 6231209\n\n```\n\nОд тастатура се читаат непознат број цели броеви поголеми од или еднакви на 10 (броевите помали од 10 се игнорираат). Читањето завршува во моментот кога ќе се прочита знак што не е цифра. Да се испечатат сите цик\\-цак броеви.		#include <stdio.h>\n\nint main() {\n    int x, br = 0, tmp, cifra1, cifra2, p, f;\n\n    while(scanf("%d", &x))\n    {\n        f=1;\n        if(x>=10){\n            tmp = x;\n            cifra1 = tmp%10;\n            tmp/=10;\n            cifra2 = tmp%10;\n            tmp/=10;\n            if(cifra1 > cifra2)\n            {\n                p=1;\n            }\n            else if(cifra1 < cifra2)\n            {\n                p=0;\n            }\n            else\n                f = 0;\n            cifra1 = cifra2;\n            if(f)\n            {\n                while(tmp) {\n                    cifra2 = tmp%10;\n                    if(p){\n                        if(cifra1>=cifra2){\n                            f=0;\n                            break;\n                        }\n                        else\n                            p = 0;\n                    }\n                    else{\n                    \tif(cifra1<=cifra2){\n                            f=0;\n                            break;\n                        }\n                        else\n                            p = 1;\n                    }\n                    tmp /= 10;\n                    cifra1 = cifra2;\n                }\n            }\n            if(f)\n                printf("%d\\n", x);\n        }\n\n    }\n\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.283544	2026-10-28 11:16:05.283548	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
0a0649ba-6176-4a9c-ae51-e1a98bf40585	Terraform: S3 bucket со верзии	Infrastructure as code: **S3 bucket** за логови во AWS.\n\n- провајдер `aws` во регионот од променливата **`region`** (тип `string`, стандардно `eu-central-1`);\n- променлива **`bucket_name`** (тип `string`, без стандардна вредност);\n- ресурс `aws_s3_bucket` со име **`logs`** чие име е `var.bucket_name` и ознака (tag) `Env = "dev"`;\n- ресурс `aws_s3_bucket_versioning` **`logs`** за тој bucket (`aws_s3_bucket.logs.id`) со\n  `versioning_configuration { status = "Enabled" }`;\n- излез **`bucket_arn`** = ARN на bucket-от.\n	provider "aws" {\n  region = "eu-central-1"\n}\n	variable "region" {\n  type    = string\n  default = "eu-central-1"\n}\n\nvariable "bucket_name" {\n  type = string\n}\n\nprovider "aws" {\n  region = var.region\n}\n\nresource "aws_s3_bucket" "logs" {\n  bucket = var.bucket_name\n  tags = {\n    Env = "dev"\n  }\n}\n\nresource "aws_s3_bucket_versioning" "logs" {\n  bucket = aws_s3_bucket.logs.id\n  versioning_configuration {\n    status = "Enabled"\n  }\n}\n\noutput "bucket_arn" {\n  value = aws_s3_bucket.logs.arn\n}\n	terraform	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.855521	2026-10-27 23:31:32.855522	t	code	mk	{"en": {"title": "Terraform: an S3 bucket with versioning", "description": "Infrastructure as code: an **S3 bucket** for logs in AWS.\\n\\n- provider `aws` in the region from the variable **`region`** (type `string`, default `eu-central-1`);\\n- a variable **`bucket_name`** (type `string`, no default);\\n- a resource `aws_s3_bucket` named **`logs`** whose name is `var.bucket_name` and a tag `Env = \\"dev\\"`;\\n- a resource `aws_s3_bucket_versioning` **`logs`** for that bucket (`aws_s3_bucket.logs.id`) with\\n  `versioning_configuration { status = \\"Enabled\\" }`;\\n- an output **`bucket_arn`** = the bucket's ARN.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
d2cb25c1-adc9-4799-b9e0-cb2bfe186082	Terraform: EC2 инстанца со security group	Веб-сервер во AWS.\n\n- променлива **`admin_cidr`** (тип `string`) — од каде е дозволен SSH;\n- `aws_security_group` **`web`** со два `ingress` блока: порта **22** (tcp) само од `var.admin_cidr`\n  и порта **80** (tcp) од `0.0.0.0/0`; и `egress` кон сè (`protocol = "-1"`, `0.0.0.0/0`);\n- `aws_instance` **`web`**: `ami = var.ami_id` (направете и таа променлива), `instance_type = "t3.micro"`,\n  `vpc_security_group_ids = [aws_security_group.web.id]`, ознака `Name = "ale-web"`;\n- излез **`public_ip`** = јавната IP-адреса на инстанцата.\n	resource "aws_instance" "web" {\n}\n	variable "admin_cidr" {\n  type = string\n}\n\nvariable "ami_id" {\n  type = string\n}\n\nresource "aws_security_group" "web" {\n  name = "ale-web"\n\n  ingress {\n    from_port   = 22\n    to_port     = 22\n    protocol    = "tcp"\n    cidr_blocks = [var.admin_cidr]\n  }\n\n  ingress {\n    from_port   = 80\n    to_port     = 80\n    protocol    = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n\n  egress {\n    from_port   = 0\n    to_port     = 0\n    protocol    = "-1"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n}\n\nresource "aws_instance" "web" {\n  ami                    = var.ami_id\n  instance_type          = "t3.micro"\n  vpc_security_group_ids = [aws_security_group.web.id]\n  tags = {\n    Name = "ale-web"\n  }\n}\n\noutput "public_ip" {\n  value = aws_instance.web.public_ip\n}\n	terraform	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.856819	2026-10-27 23:31:32.856821	t	code	mk	{"en": {"title": "Terraform: an EC2 instance with a security group", "description": "A web server in AWS.\\n\\n- a variable **`admin_cidr`** (type `string`) — where SSH is allowed from;\\n- `aws_security_group` **`web`** with two `ingress` blocks: port **22** (tcp) only from `var.admin_cidr`\\n  and port **80** (tcp) from `0.0.0.0/0`; and `egress` to everything (`protocol = \\"-1\\"`, `0.0.0.0/0`);\\n- `aws_instance` **`web`**: `ami = var.ami_id` (create that variable too), `instance_type = \\"t3.micro\\"`,\\n  `vpc_security_group_ids = [aws_security_group.web.id]`, tag `Name = \\"ale-web\\"`;\\n- an output **`public_ip`** = the instance's public IP.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
7bda006a-9575-483b-84ad-e41a1cde9779	Terraform: модул за мрежа и заеднички ознаки	Користење **модул** од Terraform Registry и `locals`.\n\n- `locals` со **`common_tags`** = `{ Project = "ale", Owner = "finki" }`;\n- модул **`vpc`** од `terraform-aws-modules/vpc/aws`, верзија `~> 5.0`, со `name = "ale"`,\n  `cidr = "10.0.0.0/16"`, `azs = ["eu-central-1a", "eu-central-1b"]`,\n  `public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]` и `tags = local.common_tags`;\n- излез **`vpc_id`** = `module.vpc.vpc_id`.\n	locals {\n}\n	locals {\n  common_tags = {\n    Project = "ale"\n    Owner   = "finki"\n  }\n}\n\nmodule "vpc" {\n  source  = "terraform-aws-modules/vpc/aws"\n  version = "~> 5.0"\n\n  name           = "ale"\n  cidr           = "10.0.0.0/16"\n  azs            = ["eu-central-1a", "eu-central-1b"]\n  public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]\n  tags           = local.common_tags\n}\n\noutput "vpc_id" {\n  value = module.vpc.vpc_id\n}\n	terraform	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-27 23:31:32.858195	2026-10-27 23:31:32.858196	t	code	mk	{"en": {"title": "Terraform: a network module and shared tags", "description": "Using a **module** from the Terraform Registry and `locals`.\\n\\n- `locals` with **`common_tags`** = `{ Project = \\"ale\\", Owner = \\"finki\\" }`;\\n- a module **`vpc`** from `terraform-aws-modules/vpc/aws`, version `~> 5.0`, with `name = \\"ale\\"`,\\n  `cidr = \\"10.0.0.0/16\\"`, `azs = [\\"eu-central-1a\\", \\"eu-central-1b\\"]`,\\n  `public_subnets = [\\"10.0.1.0/24\\", \\"10.0.2.0/24\\"]` and `tags = local.common_tags`;\\n- an output **`vpc_id`** = `module.vpc.vpc_id`.\\n"}}	[]	3d5d3c4d-e379-495a-857a-a5fb6a86c4cb	\N
62417491-324b-423f-85ad-f139d96f284b	Благ број	Благ број е број што е составен само од парни цифри (0, 2, 4, 6, 8\\). Во зададен опсег (почетокот m и крајот на опегот n се цели броеви чија вредност се внесува од тастатура), да се најде и испечати најмалиот „благ број“. Ако не постои таков број, да се испечати NE.		#include <stdio.h>\n\nint main() {\n    int m, n, i, pom, zname;\n    scanf("%d %d", &m, &n);\n    for(i = m; i <= n; i++) {\n        pom = i;\n        zname = 1;\n        while(pom > 0)\n        {\n            if((pom % 10) % 2)\n            {\n                zname = 0;\n                break;\n            }\n            pom = pom/10;\n        }\n        if(zname)\n        {\n            printf("%d", i);\n            break;\n        }\n    }\n    if(!zname)\n        printf("NE");\n    return 0;\n}	c	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.2587	2026-10-28 11:16:05.258703	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
c904fa4d-4ac1-4593-8edb-63ea197c5a69	Интересен број	Eден природен e „**интересен**“ ако неговиот **обратен број** е делив со неговиот број на цифри. Обратен број е бројот составен од истите цифри, но во обратен редослед (на пример, 653 е обратен број на бројот 356\\). Од тастатура се внесува природен број **n** ( **n \\> 9**). Да се најде и отпечати најголемиот природен број помал од **n** кој што е „интересен“. Ако внесениот број не е валиден, да се отпечати соодветна порака (Brojot ne e validen).		#include <stdio.h>\n#include<iostream>\n\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    if(n <= 9) {\n        printf("Brojot ne e validen\\n");\n        return 0;\n    }\n    while(n >= 0) {\n        int x = --n;\n        int ob = 0;\n        int c = 0;\n        while(x > 0) {\n            ob = 10 * ob + x % 10;\n            x /= 10;\n            ++c;\n        }\n        if(ob % c == 0) {\n            cout << n << endl;\n            break;\n        }\n    }\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.260883	2026-10-28 11:16:05.260886	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	Цик-цак2	Цик\\-цак е број за кој важи дека за секој пар соседни цифри во бројот важи дека едната е помала од 5, а другата е поголема или еднаква на 5\\. На пример, ако бројот x е составен од цифрите a, b, c и d, тогаш за нив важи:\n\n```cpp\na<5, b>=5, c<5, d>=5 или a>=5, b<5, c>=5, d<5\n\nПр.  508294, 2638, 81\n\n```\n\nОд тастатура се читаат непознат број на цели броеви поголеми од или еднакви на 10 (броевите помали од 10 се игнорираат). Читањето завршува во моментот кога ќе се прочита знак што не е цифра. Да се испечатат сите цик\\-цак броеви.		#include <stdio.h>\n\nint main() {\n    int x, br = 0, tmp, cifra1, cifra2, p, f;\n\n    while(scanf("%d", &x))\n    {\n        f=1;\n        if(x>=10){\n            tmp = x;\n            cifra1 = tmp%10;\n            tmp/=10;\n            cifra2 = tmp%10;\n            tmp/=10;\n            if(cifra1<5&&cifra2>=5)\n            {\n                p=1;\n            }\n            else if(cifra1>=5&&cifra2<5)\n            {\n                p=0;\n            }\n            else\n                f = 0;\n            cifra1 = cifra2;\n            if(f)\n            {\n                while(tmp) {\n                    cifra2 = tmp%10;\n                    if(p){\n                        if(!(cifra1>=5 && cifra2<5)){\n                            f=0;\n                            break;\n                        }\n                        else\n                            p = 0;\n                    }\n                    else{\n                    \tif(!(cifra1<5 && cifra2>=5)){\n                            f=0;\n                            break;\n                        }\n                        else\n                            p = 1;\n                    }\n                    tmp /= 10;\n                    cifra1 = cifra2;\n                }\n            }\n            if(f)\n                printf("%d\\n", x);\n        }\n\n    }\n\n    return 0;\n}	cpp	acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	2026-10-28 11:16:05.285699	2026-10-28 11:16:05.285701	t	code	en	{}	[]	a6937632-a996-41dc-8333-3792261b71e2	\N
\.


--
-- Data for Name: test_cases; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.test_cases (id, task_id, type, test_code, stdin, expected_output, is_hidden, "order") FROM stdin;
75e54d02-5c0e-4542-8006-8e2188ce9afc	40b82ec7-fd09-4361-8403-5035f0eacc91	code_sample	cout << greet("World") << endl;		Hello, World!\n	f	0
176b1943-0957-41bf-a89f-98254badd31d	40b82ec7-fd09-4361-8403-5035f0eacc91	code_sample	cout << greet("Alice") << endl;		Hello, Alice!\n	f	1
204833de-2aaf-4688-92c8-414918fc2c5b	40b82ec7-fd09-4361-8403-5035f0eacc91	code_sample	cout << greet("FINKI") << endl;		Hello, FINKI!\n	t	2
d3f83b0d-4a13-485c-ac0f-d3462192010c	128c63f9-4732-4f6b-a2bc-846b6cb58c82	code_sample	Stack s;\ns.push(10);\ncout << s.top() << endl;		10\n	f	0
506c192a-21aa-4456-add8-47dfe18d55b9	128c63f9-4732-4f6b-a2bc-846b6cb58c82	code_sample	Stack s;\ns.push(1); s.push(2); s.push(3);\ncout << s.pop() << endl;\ncout << s.size() << endl;		3\n2\n	f	1
fde11518-4992-407d-9077-75d71243bac7	128c63f9-4732-4f6b-a2bc-846b6cb58c82	code_sample	Stack s;\ncout << s.isEmpty() << endl;\ns.push(5);\ncout << s.isEmpty() << endl;		1\n0\n	f	2
cc10f39d-71c5-4bbb-9d95-813c9e80e609	128c63f9-4732-4f6b-a2bc-846b6cb58c82	code_sample	Stack s;\ntry { s.pop(); } catch (underflow_error& e) { cout << "caught" << endl; }		caught\n	t	3
1bf5864b-f1e6-4087-966a-3d8d3955da0b	fa8cca46-d302-42cb-9bdd-7ac52cf1e265	code_sample	Circle c(5);\ncout << fixed << setprecision(2) << c.area() << endl;		78.54\n	f	0
fdc43f57-5963-4386-b2cf-f5ccee6d5229	fa8cca46-d302-42cb-9bdd-7ac52cf1e265	code_sample	Rectangle r(3, 4);\ncout << fixed << setprecision(2) << r.area() << endl;\ncout << fixed << setprecision(2) << r.perimeter() << endl;		12.00\n14.00\n	f	1
2e2143f3-5dba-4d38-8647-6f2811874c4f	fa8cca46-d302-42cb-9bdd-7ac52cf1e265	code_sample	Circle c(5);\nc.print();		Shape: area=78.54, perimeter=31.42\n	f	2
429fd98b-73d0-43a3-b752-cc16b5a7f5bd	fa8cca46-d302-42cb-9bdd-7ac52cf1e265	code_sample	Shape* s = new Rectangle(3, 4);\ns->print();\ndelete s;		Shape: area=12.00, perimeter=14.00\n	t	3
7822314a-2a50-4ad6-9e54-d9cd5260d9ad	b5cb4216-6685-44e1-bc7c-fa4446a7073f	code_sample	print(word_frequency("Code, code. Learn!"))		{'code': 2, 'learn': 1}\n	f	0
cbeb0e3d-ccb0-46c5-a067-67d10319e138	b5cb4216-6685-44e1-bc7c-fa4446a7073f	code_sample	print(top_words("b a b c a b", 2))		[('b', 3), ('a', 2)]\n	f	1
11647555-60c1-45f1-82ef-1a7540055bcb	b5cb4216-6685-44e1-bc7c-fa4446a7073f	code_sample	print(word_frequency(""))\nprint(word_frequency("   "))		{}\n{}\n	t	2
dc04c5c6-4d06-427d-b6e1-d2a7fab7dcbb	b5cb4216-6685-44e1-bc7c-fa4446a7073f	code_sample	print(top_words("x y z y x", 3))		[('x', 2), ('y', 2), ('z', 1)]\n	t	3
e44bfff7-b5dc-4761-9a85-cf5634220590	aaf44748-6b51-4706-a44b-3119186de257	code_sample	BankAccount a = new BankAccount("Ana", 100);\na.deposit(50);\nSystem.out.println(a);		Ana: 150.00\n	f	0
8bee8154-39d2-47d1-8691-8674c84569c0	aaf44748-6b51-4706-a44b-3119186de257	code_sample	BankAccount a = new BankAccount("Marko", 20);\na.withdraw(5.5);\nSystem.out.println(a.getBalance());		14.5\n	f	1
1be78b83-ebb7-4620-ae0a-becf0b0d9cab	aaf44748-6b51-4706-a44b-3119186de257	code_sample	BankAccount a = new BankAccount("Ivo", 10);\ntry { a.withdraw(50); } catch (IllegalStateException e) { System.out.println(e.getMessage()); }\ntry { a.deposit(-1); } catch (IllegalArgumentException e) { System.out.println("invalid"); }		Insufficient funds\ninvalid\n	t	2
a2b7bc5a-d9fa-478c-9fbd-f8ef0edf8af5	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	stdin_stdout		5\n1 2 3 4 5\n	5 4 3 2 1\n	f	0
360765ad-ff49-422f-b8b0-8db0aa436da1	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	stdin_stdout		1\n42\n	42\n	f	1
9ad9d8aa-fc80-4de4-81fb-443b032788bb	628ca8cf-bfdd-4b2a-b9ec-d3888fd74b2e	stdin_stdout		4\n-3 0 7 -3\n	-3 7 0 -3\n	t	2
d6a2f8cb-96c3-4c62-9ef0-566ca24ac046	72eb8db0-6d99-415d-858d-8b58422026cb	code_sample	console.log(isPalindrome("Ana"));\nconsole.log(isPalindrome("Never odd or even!"));		true\ntrue\n	f	0
e4e63edc-a6f7-4e8e-b020-67128a5c1651	72eb8db0-6d99-415d-858d-8b58422026cb	code_sample	console.log(countPalindromes(["kayak", "ALE", "Oko"]));		2\n	f	1
cae161c3-6d42-4a52-b7d0-ec3196596f26	72eb8db0-6d99-415d-858d-8b58422026cb	code_sample	console.log(isPalindrome("abc"), isPalindrome(""), countPalindromes([]));		false true 0\n	t	2
11db6ff8-7928-4481-93b4-8e807416712e	ef07c143-c0e4-4278-919d-14d823b4a084	code_sample	CREATE TABLE student (id INTEGER PRIMARY KEY, ime TEXT, smer TEXT);\nCREATE TABLE ocena (student_id INTEGER REFERENCES student(id), predmet TEXT, ocena INTEGER);\nINSERT INTO student VALUES (1, 'Ана', 'СИИС'), (2, 'Марко', 'КНИ'), (3, 'Елена', 'СИИС');\nINSERT INTO ocena VALUES (1, 'БП', 10), (1, 'ОС', 9), (2, 'БП', 7), (3, 'БП', 8), (3, 'ОС', 8);\n-- ordered		ime | prosek\nАна | 9.5\nЕлена | 8\nМарко | 7\n	f	0
7e0427c5-0a7b-40dd-885d-81ef8cb1d3ea	ef07c143-c0e4-4278-919d-14d823b4a084	code_sample	CREATE TABLE student (id INTEGER PRIMARY KEY, ime TEXT, smer TEXT);\nCREATE TABLE ocena (student_id INTEGER REFERENCES student(id), predmet TEXT, ocena INTEGER);\nINSERT INTO student VALUES (1, 'Ана', 'СИИС'), (2, 'Ана', 'КНИ'), (3, 'Петар', 'ПИТ');\nINSERT INTO ocena VALUES (1, 'БП', 6), (2, 'БП', 10), (2, 'ВИ', 9);\n-- ordered		ime | prosek\nАна | 9.5\nАна | 6\n	t	1
c23266fe-cca8-404d-b2d6-139ad048e07a	7a049050-c9ad-4aed-8aa2-4691c63fe52d	code_sample	CREATE TABLE predmet (id SERIAL PRIMARY KEY, ime TEXT NOT NULL, krediti INT);\nCREATE TABLE upis (student TEXT, predmet_id INT REFERENCES predmet(id), datum DATE);\nINSERT INTO predmet (ime, krediti) VALUES ('Бази на податоци', 6), ('Оперативни системи', 6), ('Веб програмирање', 6);\nINSERT INTO upis VALUES ('Ана', 1, '2026-10-01'), ('Марко', 1, '2026-10-02'), ('Ана', 2, '2026-10-01'), ('Ива', 1, '2026-10-05');\n-- ordered		ime | broj\nБази на податоци | 3\nОперативни системи | 1\nВеб програмирање | 0\n	f	0
8062d28a-c455-45cb-a0fd-f30f30b3ee4a	7a049050-c9ad-4aed-8aa2-4691c63fe52d	code_sample	CREATE TABLE predmet (id SERIAL PRIMARY KEY, ime TEXT NOT NULL, krediti INT);\nCREATE TABLE upis (student TEXT, predmet_id INT REFERENCES predmet(id), datum DATE);\nINSERT INTO predmet (ime, krediti) VALUES ('Бази на податоци', 6), ('Оперативни системи', 6), ('Веб програмирање', 6);\nINSERT INTO upis VALUES ('Ана', 1, '2026-10-01'), ('Марко', 1, '2026-10-02'), ('Ана', 2, '2026-10-01'), ('Ива', 3, '2026-10-05'), ('Лео', 3, '2026-10-06');\n-- ordered		ime | broj\nБази на податоци | 2\nВеб програмирање | 2\nОперативни системи | 1\n	t	1
5bec8283-2c23-4012-9fb2-b7dc40007a19	5f57a182-42ec-4b17-9a58-597f74ecbe2e	code_sample	const s = new Stack<number>();\ns.push(1); s.push(2);\nconsole.log(s.pop(), s.size);		2 1\n	f	0
5fcd76dd-adb6-45b2-bf40-7cbebb5d664a	5f57a182-42ec-4b17-9a58-597f74ecbe2e	code_sample	const s = new Stack<string>();\nconsole.log(s.pop(), s.peek(), s.size);		undefined undefined 0\n	f	1
d91fc2e8-ef77-4efe-bb0b-5c3fe129d998	5f57a182-42ec-4b17-9a58-597f74ecbe2e	code_sample	const s = new Stack<number>();\nfor (let i = 0; i < 5; i++) s.push(i * i);\nconsole.log(s.peek(), s.size);		16 5\n	t	2
6343a96e-4cb4-4bc1-8318-6897f9d35e2e	73b0a1f2-d55a-4404-b80b-64480e2016b2	code_sample	foreach (countWords("a b A c b a") as $w => $n) echo "$w $n\\n";		a 3\nb 2\nc 1\n	f	0
d648df70-4ab8-46c6-b60b-3913a44a82e0	73b0a1f2-d55a-4404-b80b-64480e2016b2	code_sample	echo count(countWords("")), "\\n";		0\n	f	1
509862db-16b9-46db-924d-9a9fd7bccdab	73b0a1f2-d55a-4404-b80b-64480e2016b2	code_sample	print_r(countWords("Зошто да, зошто не"));		Array\n(\n    [зошто] => 2\n    [да] => 1\n    [не] => 1\n)\n	t	2
bdb9647e-71f9-4a5d-97df-5e8daa3a1517	fd196046-62cb-490e-a3ca-3a18829d7905	stdin_stdout		hello world\none two three\nx\n	3 6 13\n	f	0
9c916d06-b96a-4dca-9a56-e06ba144f123	fd196046-62cb-490e-a3ca-3a18829d7905	stdin_stdout			0 0 0\n	f	1
4c2171ee-5951-4e14-bedc-9c85863d84f1	fd196046-62cb-490e-a3ca-3a18829d7905	stdin_stdout		  spaced  \nlast\n	2 2 10\n	t	2
37063f6c-9458-481f-8f25-a86c9e67d035	56536497-5111-4aac-9768-1d101259396d	code_sample	Console.WriteLine(new Rectangle(2, 3).Area());		6\n	f	0
6267862c-5224-47c6-a15f-d45601ec1e90	56536497-5111-4aac-9768-1d101259396d	code_sample	Console.WriteLine(Shapes.TotalArea(new List<Shape> { new Circle(1), new Rectangle(1, 1) }).ToString("F3", System.Globalization.CultureInfo.InvariantCulture));		4.142\n	f	1
1b95b106-e7e0-4e61-a34a-bb02c90caced	56536497-5111-4aac-9768-1d101259396d	code_sample	Console.WriteLine(Shapes.TotalArea(new List<Shape>()));		0\n	t	2
b1a70015-bd81-45c2-88be-a7a522f5ecba	23bec27d-a91a-4582-a3c7-790469571996	code_sample	println(Student("Ана", listOf(10, 9)).average)		9.5\n	f	0
a6857371-041e-48d7-801e-20ea2dcf093f	23bec27d-a91a-4582-a3c7-790469571996	code_sample	println(best(listOf(Student("Ана", listOf(8)), Student("Иво", listOf(10, 9)))))\nprintln(best(emptyList()))		Иво\nnull\n	f	1
26307e82-dbbe-444d-8792-85234c8b7de2	d513ea09-4d3c-41b6-a7f5-b728629303ac	code_sample	forall(grandparent(vera, X), (write(X), nl))		lea\n	f	0
4ff36541-f21f-4d10-9fa1-da734e87bb8d	d513ea09-4d3c-41b6-a7f5-b728629303ac	code_sample	forall(sibling(ana, X), (write(X), nl))		ivo\n	f	1
abd7261a-9d9e-4cf8-ba14-84a22997f17f	d513ea09-4d3c-41b6-a7f5-b728629303ac	code_sample	findall(D, ancestor(vera, D), L), msort(L, S), write(S), nl		[ana,ivo,lea,mila]\n	t	2
1e3f28cc-1e88-4e3e-8dda-491a474c9344	683a9c81-7ceb-4991-b089-ebbd4e5a3e62	code_sample	(format t "~a~%" (my-reverse '(1 2 3)))		(3 2 1)\n	f	0
641a8863-1651-4b6c-8671-e059c2ac10db	683a9c81-7ceb-4991-b089-ebbd4e5a3e62	code_sample	(format t "~a ~a~%" (count-if-even '(1 2 3 4 6)) (flatten '(1 (2 (3)) 4)))		3 (1 2 3 4)\n	f	1
f4d86e04-084b-4e63-999c-b670e63fae14	683a9c81-7ceb-4991-b089-ebbd4e5a3e62	code_sample	(format t "~a ~a~%" (my-reverse nil) (flatten '((()))))		NIL NIL\n	t	2
477ed0c7-316b-4370-a47e-ca6be9774c88	0a2e2c61-abfb-42c2-ae92-4ebd166bfed5	code_sample	extern long array_sum(long *a, long n);\nlong a[] = {1, 2, 3, 4};\nprintf("%ld\\n", array_sum(a, 4));		10\n	f	0
f7a5ff92-ff5a-439b-a689-d51ffd98ccfd	0a2e2c61-abfb-42c2-ae92-4ebd166bfed5	code_sample	extern long array_sum(long *a, long n);\nlong a[] = {5};\nprintf("%ld %ld\\n", array_sum(a, 1), array_sum(a, 0));		5 0\n	f	1
075fe6cf-556f-481b-a8de-83540a52aeea	0a2e2c61-abfb-42c2-ae92-4ebd166bfed5	code_sample	extern long array_sum(long *a, long n);\nlong a[] = {-7, 1000000000000, 3};\nprintf("%ld\\n", array_sum(a, 3));		999999999996\n	t	2
439e556d-21a8-4841-acc1-4e6b4c414de2	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	print(exists('.card h2'), exists('.card .role'), exists('.card #follow'))		true true true	f	0
21772e26-3edb-4e43-aa00-2e6e791b7bf8	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	print(count('.skills li') >= 3)		true	f	1
6be11935-aad3-445a-9b6c-3694b84d8d0a	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	print(hex('#follow', 'background-color'), hex('#follow', 'color'))		#2747c9 #ffffff	f	2
d02ff512-4cd2-4a3e-b624-07ad016575a8	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	print(css('.card', 'border-radius'), css('.card', 'max-width'))		12px 320px	f	3
e7ec6495-46ae-4b1d-89fc-b53355a5db91	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	await click('#follow'); print(text('#follow'))\nawait click('#follow'); print(text('#follow'))		Following\nFollow	f	4
26902526-d834-410b-99a5-7cdd6c8f78b0	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	print(css('.skills', 'display'), css('.skills', 'flex-direction'))		flex row	t	5
0eb86a76-1eea-45f2-82b9-04bcb7caf8dc	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	// viewport: 375x667\nprint(css('.skills', 'flex-direction'))		column	t	6
857da81f-e52b-4399-af97-dcb6986bdb0d	030e9a55-5465-411e-af39-9676d9c7786f	code_sample	// visual: 80			f	7
12ab9555-c829-46a9-82e5-7aa0d0c6e090	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "node", "name": "Книга", "aliases": ["Book"]}		Постои „Книга“	f	0
a1b27522-2bc6-40c3-92eb-4160a49533df	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "node", "name": "Член", "aliases": ["Member"]}		Постои „Член“	f	1
30ecbcaf-be5a-4846-bf6a-9ddb1078e62b	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "node", "name": "Позајмица", "aliases": ["Loan"]}		Постои „Позајмица“	f	2
79f9d849-12c9-4e3f-8115-15eacca6580c	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "node", "name": "Вработен", "aliases": ["Employee"], "type": "abstract"}		„Вработен“ е апстрактна класа	f	3
b28d01ec-c29f-48ce-b159-ec5a53d6da78	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "node", "name": "Библиотекар", "aliases": ["Librarian"]}		Постои „Библиотекар“	f	4
ec6934af-c75d-4280-8586-d81af2ada3bf	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Книга", "name": "наслов", "aliases": ["title"], "node_aliases": ["Book"]}		„Книга“ има атрибут „наслов“	f	5
77a20d09-2541-49f0-ada6-bb46f7175d22	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Книга", "name": "isbn", "node_aliases": ["Book"]}		„Книга“ има атрибут „isbn“	f	6
b153f1ee-50bf-4990-9f68-10a45541a167	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Книга", "name": "автор", "aliases": ["author"], "node_aliases": ["Book"]}		„Книга“ има атрибут „автор“	f	7
d4a53a94-6cfb-445a-82f7-f6a9e115b13d	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "method", "node": "Книга", "name": "достапна", "node_aliases": ["Book"]}		„Книга“ има метод „достапна“	f	8
8e62a3c2-4925-489a-a8b8-29d8ca19eccf	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Член", "name": "име", "aliases": ["name"], "node_aliases": ["Member"]}		„Член“ има атрибут „име“	f	9
64b114f2-ddf5-4694-a4c6-d5ba103e50d5	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Член", "name": "бројНаКарта", "aliases": ["cardNumber", "brojKarta"], "node_aliases": ["Member"]}		„Член“ има атрибут „бројНаКарта“	f	10
e714c913-3a0c-45f5-aff0-892f9021a9c8	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "method", "node": "Член", "name": "позајми", "node_aliases": ["Member"]}		„Член“ има метод „позајми“	f	11
61d8e2e4-4d8f-40c2-be03-92349cca5281	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Позајмица", "name": "датум", "aliases": ["date"], "node_aliases": ["Loan"]}		„Позајмица“ има атрибут „датум“	f	12
342ba27e-ea4a-4aea-9ddb-f8442d568e6d	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Позајмица", "name": "рок", "aliases": ["dueDate", "rokZaVrakjanje"], "node_aliases": ["Loan"]}		„Позајмица“ има атрибут „рок“	f	13
7633a094-c5aa-482a-a60d-4bde37377823	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "method", "node": "Позајмица", "name": "доцни", "node_aliases": ["Loan"]}		„Позајмица“ има метод „доцни“	f	14
add47fcb-5754-4c16-9da2-50cd5e1dd8d4	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "attribute", "node": "Вработен", "name": "име", "aliases": ["name"], "node_aliases": ["Employee"]}		„Вработен“ има атрибут „име“	f	15
2dc48dd4-e550-491c-8947-e5aa9d69b48e	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "relation", "a": "Член", "b": "Позајмица", "kind": "association", "a_aliases": ["Member"], "b_aliases": ["Loan"], "mult_a": "1", "mult_b": "0..*"}		Асоцијација „Член“ (1) – „Позајмица“ (0..*)	f	16
3dd3f922-2ed4-4486-88d2-594e3942df15	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "relation", "a": "Позајмица", "b": "Книга", "kind": "association", "a_aliases": ["Loan"], "b_aliases": ["Book"], "mult_a": "0..*", "mult_b": "1"}		Асоцијација „Позајмица“ (0..*) – „Книга“ (1)	t	17
3c4449ab-d7c4-4b14-a7c6-c8b9e0262b0f	8fd3c66f-7a1f-4228-a88b-353a598f0b7a	diagram	{"check": "relation", "a": "Библиотекар", "b": "Вработен", "kind": "inheritance", "a_aliases": ["Librarian"], "b_aliases": ["Employee"]}		Наследување од „Библиотекар“ кон „Вработен“	t	18
7a82775a-365b-484d-ad9a-125f4bd938db	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "node", "name": "Студент", "aliases": ["Student"]}		Постои „Студент“	f	0
871bb779-f501-4ec2-8a3a-cc55048eac4f	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "node", "name": "Предмет", "aliases": ["Course", "Subject"]}		Постои „Предмет“	f	1
74a23b26-9de9-403e-a78f-d7245c86ed01	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "node", "name": "Професор", "aliases": ["Professor"]}		Постои „Професор“	f	2
896920c8-4dc9-46c0-8afe-7df19ab38e83	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Студент", "name": "индекс", "aliases": ["index", "brIndeks"], "node_aliases": ["Student"], "pk": true}		„Студент“ има примарен клуч „индекс“	f	3
a167971d-6ae3-48cf-86bf-a265068f2f71	9374c027-5641-4687-953e-5dc789329162	code_sample	await type('#bill', '100'); print(text('#tip'), text('#total'))		15.00 115.00	f	1
88f20483-9ea6-4018-b7f0-ecb3691b01e8	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Студент", "name": "име", "aliases": ["ime", "firstName"], "node_aliases": ["Student"]}		„Студент“ има атрибут „име“	f	4
f195e1da-dca0-4a6b-947c-a1984b97c050	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Студент", "name": "презиме", "aliases": ["prezime", "lastName"], "node_aliases": ["Student"]}		„Студент“ има атрибут „презиме“	f	5
42c699ac-bb1b-45c4-8cde-3d73fef95ba2	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Студент", "name": "email", "aliases": ["е-пошта", "eposta"], "node_aliases": ["Student"]}		„Студент“ има атрибут „email“	f	6
9e13b233-cc45-45fb-8179-0788db2aca66	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Предмет", "name": "шифра", "aliases": ["code", "sifra"], "node_aliases": ["Course", "Subject"], "pk": true}		„Предмет“ има примарен клуч „шифра“	f	7
be6c9a58-3307-4db5-b07b-764e4a62af75	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Предмет", "name": "назив", "aliases": ["name", "naziv"], "node_aliases": ["Course", "Subject"]}		„Предмет“ има атрибут „назив“	f	8
6b844c47-7207-4938-a710-9ee57c5737c5	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Предмет", "name": "кредити", "aliases": ["credits", "ects"], "node_aliases": ["Course", "Subject"]}		„Предмет“ има атрибут „кредити“	f	9
0ac52906-d9cf-4476-9efe-55783601aca2	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Професор", "name": "id", "node_aliases": ["Professor"], "pk": true}		„Професор“ има примарен клуч „id“	f	10
5bc13423-9f79-48c6-9e11-6232df49fa66	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "attribute", "node": "Професор", "name": "име", "aliases": ["name", "ime"], "node_aliases": ["Professor"]}		„Професор“ има атрибут „име“	f	11
5ba6e7d3-c8bb-46f6-93dd-c882b077b1de	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "relation", "a": "Студент", "b": "Предмет", "kind": "relationship", "a_aliases": ["Student"], "b_aliases": ["Course", "Subject"], "mult_a": "N", "mult_b": "M"}		Релација „Студент“ (N) – „Предмет“ (M)	t	12
46c71640-36ed-4c2f-923e-ed63601a92b7	34af459e-d75c-4123-821e-eec168e121d0	diagram	{"check": "relation", "a": "Професор", "b": "Предмет", "kind": "relationship", "a_aliases": ["Professor"], "b_aliases": ["Course", "Subject"], "mult_a": "1", "mult_b": "N"}		Релација „Професор“ (1) – „Предмет“ (N)	t	13
f79ac4c5-13dc-4ebe-ad20-34210fabd28a	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Студентски сервис", "aliases": ["Student services"], "type": "system"}		„Студентски сервис“ е граница на системот	f	0
5f88bd57-5412-4b80-8bee-a3ae8f61603f	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Студент", "aliases": ["Student"], "type": "actor"}		„Студент“ е актер	f	1
c890928e-d64a-4be9-b6b5-bec2feb42dca	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Референт", "aliases": ["Clerk", "Referent"], "type": "actor"}		„Референт“ е актер	f	2
affa0b53-af62-448d-9288-c8081dfc6896	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Пријава на испит", "aliases": ["Register for an exam", "Exam registration"]}		Постои „Пријава на испит“	f	3
088f4d70-3820-48db-8774-46b353912456	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Најава", "aliases": ["Log in", "Login"]}		Постои „Најава“	f	4
56d5f518-76e9-41ee-9d33-4f6c1baea331	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Плаќање со картичка", "aliases": ["Pay by card"]}		Постои „Плаќање со картичка“	f	5
f7b46903-3c6f-4b50-8b91-df154dabe565	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Преглед на оценки", "aliases": ["View grades"]}		Постои „Преглед на оценки“	f	6
c25b9e6b-5f51-4754-ac6b-1b3776c312c5	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "node", "name": "Внес на оценки", "aliases": ["Enter grades"]}		Постои „Внес на оценки“	f	7
3ebfcd58-bd41-4994-ac09-644118af7aba	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "relation", "a": "Студент", "b": "Пријава на испит", "kind": "association", "a_aliases": ["Student"], "b_aliases": ["Register for an exam", "Exam registration"]}		Асоцијација „Студент“ – „Пријава на испит“	f	8
c605972c-5a04-4046-abe4-4b3feea5255a	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "relation", "a": "Студент", "b": "Преглед на оценки", "kind": "association", "a_aliases": ["Student"], "b_aliases": ["View grades"]}		Асоцијација „Студент“ – „Преглед на оценки“	f	9
fa0e6cf7-5fd3-4ccb-92e3-7a1440d2df31	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "relation", "a": "Референт", "b": "Внес на оценки", "kind": "association", "a_aliases": ["Clerk", "Referent"], "b_aliases": ["Enter grades"]}		Асоцијација „Референт“ – „Внес на оценки“	f	10
614874c1-7b9c-4dd5-bb09-d79e265ae7ed	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "relation", "a": "Пријава на испит", "b": "Најава", "kind": "include", "a_aliases": ["Register for an exam", "Exam registration"], "b_aliases": ["Log in", "Login"]}		«include» од „Пријава на испит“ кон „Најава“	t	11
d6f05818-082e-4b7d-984c-0e52158b34c0	fed45caf-a572-4634-bdfc-389d091fe71c	diagram	{"check": "relation", "a": "Плаќање со картичка", "b": "Пријава на испит", "kind": "extend", "a_aliases": ["Pay by card"], "b_aliases": ["Register for an exam", "Exam registration"]}		«extend» од „Плаќање со картичка“ кон „Пријава на испит“	t	12
93d99c14-d650-4550-9299-cb74c921cbd7	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "node", "name": "Нова", "aliases": ["New"]}		Постои „Нова“	f	0
3dab06e6-92a1-4ad5-9e96-1d21ccb9383a	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "node", "name": "Платена", "aliases": ["Paid"]}		Постои „Платена“	f	1
fa407221-c5aa-4839-87dc-2ef23b7add39	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "node", "name": "Откажана", "aliases": ["Cancelled", "Canceled"]}		Постои „Откажана“	f	2
651613d3-0f0f-4235-a37f-eccb0ffe8478	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "node", "name": "Испратена", "aliases": ["Shipped"]}		Постои „Испратена“	f	3
107b99c4-6d59-4c71-9619-13897218d3d4	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "node", "name": "Доставена", "aliases": ["Delivered"]}		Постои „Доставена“	f	4
9884b2ad-0b7c-420d-9bbc-f00870114693	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "count", "type": "initial", "min": 1}		Има почеток (почетна состојба)	f	5
8e5f870f-6ca6-4e07-b796-c6dcd5b2ae78	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "count", "type": "final", "min": 1}		Има крај (крајна состојба)	f	6
8b0414d2-e43b-492e-bd35-d66a3a7e37f0	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "attribute", "node": "Платена", "name": "entry / испрати потврда", "node_aliases": ["Paid"]}		„Платена“ има внатрешна активност „entry / испрати потврда“	f	7
2a326bc3-3c08-49ba-9195-e324941a30e0	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "@initial", "b": "Нова", "kind": "transition", "b_aliases": ["New"]}		Премин од почетокот кон „Нова“	f	8
6fd91f9c-44bb-44ea-a913-ae1d0abc94ee	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Нова", "b": "Платена", "kind": "transition", "a_aliases": ["New"], "b_aliases": ["Paid"], "label": "плати"}		Премин од „Нова“ кон „Платена“: „плати“	f	9
09c55927-5e19-4b09-ae33-919577fa85a2	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Нова", "b": "Откажана", "kind": "transition", "a_aliases": ["New"], "b_aliases": ["Cancelled", "Canceled"], "label": "откажи"}		Премин од „Нова“ кон „Откажана“: „откажи“	f	10
d1fa6f02-4dc9-41bf-b208-bda3bcee2848	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Платена", "b": "Испратена", "kind": "transition", "a_aliases": ["Paid"], "b_aliases": ["Shipped"], "label": "испрати"}		Премин од „Платена“ кон „Испратена“: „испрати“	f	11
8d6aebd6-15ad-409d-b190-7b3b878cb64f	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Испратена", "b": "Доставена", "kind": "transition", "a_aliases": ["Shipped"], "b_aliases": ["Delivered"], "label": "достави"}		Премин од „Испратена“ кон „Доставена“: „достави“	f	12
9a0185ed-a40e-4872-8c1a-349809ce8358	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Доставена", "b": "@final", "kind": "transition", "a_aliases": ["Delivered"]}		Премин од „Доставена“ кон крајот	f	13
8e6256d3-2b00-4ff1-8609-a58bbc90cabe	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "relation", "a": "Откажана", "b": "@final", "kind": "transition", "a_aliases": ["Cancelled", "Canceled"]}		Премин од „Откажана“ кон крајот	t	14
339f7be4-1600-4958-afd0-19fa85810955	5a4c0662-fe43-491c-b40c-0273119714fa	diagram	{"check": "reachable"}		До секој елемент може да се стигне од почетокот	t	15
25a41982-f2ac-4d54-9490-c8051ab9760f	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "node", "name": "Корисник", "aliases": ["User"], "type": "actor"}		„Корисник“ е актер	f	0
f3e58167-6f19-4b42-8b46-9d048848300c	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "node", "name": ":ФормаЗаНајава", "aliases": [":LoginForm", "ФормаЗаНајава"]}		Постои „:ФормаЗаНајава“	f	1
f11084d8-d5bf-4cb1-bbf1-298a4e5bc20b	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "node", "name": ":Контролер", "aliases": [":Controller", "Контролер"]}		Постои „:Контролер“	f	2
cbe06c20-c24f-4302-b188-03e08206fcec	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "node", "name": ":БазаНаКорисници", "aliases": [":UserDatabase", "БазаНаКорисници"]}		Постои „:БазаНаКорисници“	f	3
dffb338c-81a6-4d91-a003-4695bc00ddaf	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": "Корисник", "b": ":ФормаЗаНајава", "kind": "sync", "a_aliases": ["User"], "b_aliases": [":LoginForm", "ФормаЗаНајава"], "label": "внеси(корисник, лозинка)"}		Порака од „Корисник“ кон „:ФормаЗаНајава“: „внеси(корисник, лозинка)“	f	4
6e5c4a95-3154-4e77-a5b6-ac362af6e69e	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":ФормаЗаНајава", "b": ":Контролер", "kind": "sync", "a_aliases": [":LoginForm", "ФормаЗаНајава"], "b_aliases": [":Controller", "Контролер"], "label": "најави(корисник, лозинка)"}		Порака од „:ФормаЗаНајава“ кон „:Контролер“: „најави(корисник, лозинка)“	f	5
03dc006a-8fa0-4c1f-8e56-243cff22f14a	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":Контролер", "b": ":БазаНаКорисници", "kind": "sync", "a_aliases": [":Controller", "Контролер"], "b_aliases": [":UserDatabase", "БазаНаКорисници"], "label": "најди(корисник)"}		Порака од „:Контролер“ кон „:БазаНаКорисници“: „најди(корисник)“	f	6
a0599f7d-e09b-463c-b125-f46efd716ea6	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":БазаНаКорисници", "b": ":Контролер", "kind": "reply", "a_aliases": [":UserDatabase", "БазаНаКорисници"], "b_aliases": [":Controller", "Контролер"], "label": "корисник"}		Одговор од „:БазаНаКорисници“ кон „:Контролер“: „корисник“	f	7
34addaa1-913d-49f2-9bd5-a7eb7a46a0b2	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":Контролер", "b": ":Контролер", "kind": "sync", "a_aliases": [":Controller", "Контролер"], "b_aliases": [":Controller", "Контролер"], "label": "провериЛозинка()"}		Порака од „:Контролер“ кон „:Контролер“: „провериЛозинка()“	f	8
075e757e-e765-4da0-8f76-07662a139076	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":Контролер", "b": ":ФормаЗаНајава", "kind": "reply", "a_aliases": [":Controller", "Контролер"], "b_aliases": [":LoginForm", "ФормаЗаНајава"], "label": "успех"}		Одговор од „:Контролер“ кон „:ФормаЗаНајава“: „успех“	f	9
ffca01fc-7b7f-4efc-8bff-31d9f44aa631	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "relation", "a": ":ФормаЗаНајава", "b": "Корисник", "kind": "sync", "a_aliases": [":LoginForm", "ФормаЗаНајава"], "b_aliases": ["User"], "label": "прикажиПочетна()"}		Порака од „:ФормаЗаНајава“ кон „Корисник“: „прикажиПочетна()“	f	10
bd46e364-d6c8-49c9-929e-5ee1d1aa7fdf	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": "Корисник", "b": ":ФормаЗаНајава", "label": "внеси(корисник, лозинка)"}, "then": {"a": ":ФормаЗаНајава", "b": ":Контролер", "label": "најави(корисник, лозинка)"}}		По „внеси(корисник, лозинка)“ доаѓа „најави(корисник, лозинка)“	f	11
45f28f68-e2fe-4b40-a8eb-4677f0ce482e	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": ":ФормаЗаНајава", "b": ":Контролер", "label": "најави(корисник, лозинка)"}, "then": {"a": ":Контролер", "b": ":БазаНаКорисници", "label": "најди(корисник)"}}		По „најави(корисник, лозинка)“ доаѓа „најди(корисник)“	f	12
bc94b862-62e9-4c3c-8ff9-59d8c5f66cf9	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": ":Контролер", "b": ":БазаНаКорисници", "label": "најди(корисник)"}, "then": {"a": ":БазаНаКорисници", "b": ":Контролер", "label": "корисник"}}		По „најди(корисник)“ доаѓа „корисник“	f	13
f9c51dea-1a2f-4248-b88a-cd17b12cbd02	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": ":БазаНаКорисници", "b": ":Контролер", "label": "корисник"}, "then": {"a": ":Контролер", "b": ":Контролер", "label": "провериЛозинка()"}}		По „корисник“ доаѓа „провериЛозинка()“	f	14
0e334872-851d-4f21-a8ae-ce72c13bb03e	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": ":Контролер", "b": ":Контролер", "label": "провериЛозинка()"}, "then": {"a": ":Контролер", "b": ":ФормаЗаНајава", "label": "успех"}}		По „провериЛозинка()“ доаѓа „успех“	t	15
5b7d296b-4d41-43d2-9147-0bbb70e09080	1342f377-a292-4348-9dd3-59b233e43ffb	diagram	{"check": "order", "first": {"a": ":Контролер", "b": ":ФормаЗаНајава", "label": "успех"}, "then": {"a": ":ФормаЗаНајава", "b": "Корисник", "label": "прикажиПочетна()"}}		По „успех“ доаѓа „прикажиПочетна()“	t	16
d19a3572-3443-4df5-ba39-a9927a45d81e	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Внеси картичка", "aliases": ["Insert card"]}		Постои „Внеси картичка“	f	0
f2dae967-3216-457d-86f4-30770e069f7c	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Внеси PIN", "aliases": ["Enter PIN"]}		Постои „Внеси PIN“	f	1
ee968662-6223-496d-83bc-02c76c2c770e	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "PIN точен?", "aliases": ["PIN correct?"], "type": "decision"}		„PIN точен?“ е одлука	f	2
5c944491-4137-4dd5-8dfd-6979abd19ce3	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Избери износ", "aliases": ["Choose amount"]}		Постои „Избери износ“	f	3
ab38249d-df78-44ac-a58b-9fe843634a0a	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Исплати пари", "aliases": ["Pay out", "Dispense cash"]}		Постои „Исплати пари“	f	4
f62804f6-9421-4600-bc44-5e8116cd2f1f	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Испечати потврда", "aliases": ["Print receipt"]}		Постои „Испечати потврда“	f	5
c523afab-7446-462e-ad0f-26e5a74a957a	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "node", "name": "Врати картичка", "aliases": ["Return card"]}		Постои „Врати картичка“	f	6
5f6a5c53-6b74-4e3a-8418-77d9ff754806	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "count", "type": "initial", "min": 1}		Има почеток (почетна состојба)	f	7
01d212af-42ab-4d26-8ae6-af2e5d45e8cf	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "count", "type": "final", "min": 1}		Има крај (крајна состојба)	f	8
5760d70c-9ab4-43d0-9371-45f448cf566e	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "@initial", "b": "Внеси картичка", "kind": "flow", "b_aliases": ["Insert card"]}		Тек од почетокот кон „Внеси картичка“	f	9
c319b486-a487-4e83-ad08-467305aa383f	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Внеси картичка", "b": "Внеси PIN", "kind": "flow", "a_aliases": ["Insert card"], "b_aliases": ["Enter PIN"]}		Тек од „Внеси картичка“ кон „Внеси PIN“	f	10
305d90dc-582a-41f0-8d08-7f1f6b4a72c7	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Внеси PIN", "b": "PIN точен?", "kind": "flow", "a_aliases": ["Enter PIN"], "b_aliases": ["PIN correct?"]}		Тек од „Внеси PIN“ кон „PIN точен?“	f	11
c679baea-a322-48a7-9ce6-eb1ca7e979c5	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "PIN точен?", "b": "Избери износ", "kind": "flow", "a_aliases": ["PIN correct?"], "b_aliases": ["Choose amount"], "label": "[да]"}		Тек од „PIN точен?“ кон „Избери износ“: „[да]“	f	12
9b0c048d-2e94-469d-ba4b-1a41adb92c4b	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "PIN точен?", "b": "Внеси PIN", "kind": "flow", "a_aliases": ["PIN correct?"], "b_aliases": ["Enter PIN"], "label": "[не]"}		Тек од „PIN точен?“ кон „Внеси PIN“: „[не]“	f	13
8eeb22a4-b20f-493e-8ff3-1f64eb61bb59	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Избери износ", "b": "@fork", "kind": "flow", "a_aliases": ["Choose amount"]}		Тек од „Избери износ“ кон разгранувањето	f	14
0d56057b-afe2-423b-846c-1c85886e1e80	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "@fork", "b": "Исплати пари", "kind": "flow", "b_aliases": ["Pay out", "Dispense cash"]}		Тек од разгранувањето кон „Исплати пари“	f	15
7f215f9f-7edf-4527-91bc-5bd0f10ea802	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "@fork", "b": "Испечати потврда", "kind": "flow", "b_aliases": ["Print receipt"]}		Тек од разгранувањето кон „Испечати потврда“	f	16
c558760f-590f-49d2-b2a6-eb1acb7971b7	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Исплати пари", "b": "@join", "kind": "flow", "a_aliases": ["Pay out", "Dispense cash"]}		Тек од „Исплати пари“ кон спојувањето	f	17
8f061ab2-58aa-42f0-8fe9-01ab14f5fd9a	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Испечати потврда", "b": "@join", "kind": "flow", "a_aliases": ["Print receipt"]}		Тек од „Испечати потврда“ кон спојувањето	f	18
2fca643a-10ae-4d9f-84f2-56746556c9f1	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "@join", "b": "Врати картичка", "kind": "flow", "b_aliases": ["Return card"]}		Тек од спојувањето кон „Врати картичка“	f	19
0c582f89-0faa-4a2d-b88e-9eb1b77ccc96	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "relation", "a": "Врати картичка", "b": "@final", "kind": "flow", "a_aliases": ["Return card"]}		Тек од „Врати картичка“ кон крајот	t	20
1eeb9795-7357-48e1-941e-6843071b8a62	ec94d5db-9cba-4310-bc65-63fdc44d6a38	diagram	{"check": "reachable"}		До секој елемент може да се стигне од почетокот	t	21
4012e619-a143-4d10-b3dc-430682dabd94	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "node", "name": "Веб апликација", "aliases": ["Web app", "Web application"]}		Постои „Веб апликација“	f	0
b688e6cb-0d55-43ae-b618-cd894adaa6fa	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "node", "name": "Сервис за нарачки", "aliases": ["Order service"]}		Постои „Сервис за нарачки“	f	1
9adba88e-a6a7-48f3-9f6f-3b6063d9b03e	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "node", "name": "IПлаќање", "aliases": ["IPayment", "IPlakjanje"], "type": "interface"}		„IПлаќање“ е интерфејс	f	2
74bfbd0e-661b-48e9-9280-dda0f699ebdf	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "node", "name": "Сервис за плаќање", "aliases": ["Payment service"]}		Постои „Сервис за плаќање“	f	3
c53e99ed-d1a1-4ee1-8233-b806d84ff4ff	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "relation", "a": "Веб апликација", "b": "Сервис за нарачки", "kind": "dependency", "a_aliases": ["Web app", "Web application"], "b_aliases": ["Order service"]}		Зависност од „Веб апликација“ кон „Сервис за нарачки“	f	4
8ab4a50b-b527-478b-8602-6cf0794f3fc8	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "relation", "a": "Сервис за нарачки", "b": "IПлаќање", "kind": "dependency", "a_aliases": ["Order service"], "b_aliases": ["IPayment", "IPlakjanje"]}		Зависност од „Сервис за нарачки“ кон „IПлаќање“	t	5
94186a63-f7eb-4735-8790-b6ff18599fcc	e86d90c4-a9c3-48a6-abfe-7a4c9fd76834	diagram	{"check": "relation", "a": "Сервис за плаќање", "b": "IПлаќање", "kind": "realization", "a_aliases": ["Payment service"], "b_aliases": ["IPayment", "IPlakjanje"]}		Реализација од „Сервис за плаќање“ кон „IПлаќање“	t	6
76680ec7-1f64-47f4-baf0-bc4d9676cd10	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "node", "name": "Презентација", "aliases": ["Presentation"]}		Постои „Презентација“	f	0
2aee65de-195e-4fa2-a278-e7817975d8c2	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "node", "name": "Бизнис логика", "aliases": ["Business logic"]}		Постои „Бизнис логика“	f	1
3812f4d0-bd8f-4036-942c-44e5b44267f9	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "node", "name": "Пристап до податоци", "aliases": ["Data access"]}		Постои „Пристап до податоци“	f	2
1645663d-b724-4600-aefb-f6b9bfcebc6a	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "attribute", "node": "Презентација", "name": "Контролери", "aliases": ["Controllers"], "node_aliases": ["Presentation"]}		„Презентација“ има елемент „Контролери“	f	3
17170b93-c493-4b59-a096-e007ccee8d5b	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "attribute", "node": "Презентација", "name": "Погледи", "aliases": ["Views"], "node_aliases": ["Presentation"]}		„Презентација“ има елемент „Погледи“	f	4
997b302a-4732-4f3f-b7ec-820022e3181a	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "attribute", "node": "Бизнис логика", "name": "Сервиси", "aliases": ["Services"], "node_aliases": ["Business logic"]}		„Бизнис логика“ има елемент „Сервиси“	f	5
9b39f3a1-da63-4929-9733-1016becfe0ac	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "attribute", "node": "Пристап до податоци", "name": "Репозиториуми", "aliases": ["Repositories"], "node_aliases": ["Data access"]}		„Пристап до податоци“ има елемент „Репозиториуми“	f	6
98a87ed0-e9b2-4c6d-ac9e-61898718c40c	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "relation", "a": "Презентација", "b": "Бизнис логика", "kind": "dependency", "a_aliases": ["Presentation"], "b_aliases": ["Business logic"]}		Зависност од „Презентација“ кон „Бизнис логика“	t	7
e2dd6f55-2b2c-4925-83e4-77c0913cdfaf	112b7347-ef3f-4d94-a217-ac909ac9eb3e	diagram	{"check": "relation", "a": "Бизнис логика", "b": "Пристап до податоци", "kind": "import", "a_aliases": ["Business logic"], "b_aliases": ["Data access"]}		«import» од „Бизнис логика“ кон „Пристап до податоци“	t	8
f0c35a9f-df67-4981-a173-cdf1bf363a21	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "node", "name": "Компјутер на корисник", "aliases": ["User computer", "Client"], "type": "device"}		„Компјутер на корисник“ е уред	f	0
1cfe0364-c757-49c4-92c4-27f3475d09c7	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "node", "name": "Веб сервер", "aliases": ["Web server"]}		Постои „Веб сервер“	f	1
9f0de8d5-ce88-4304-a920-1b93020ef6e5	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "node", "name": "Апликациски сервер", "aliases": ["Application server", "App server"]}		Постои „Апликациски сервер“	f	2
37ed4677-10ea-4077-9f15-d764d9e3f090	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "node", "name": "Сервер за бази", "aliases": ["Database server", "DB server"]}		Постои „Сервер за бази“	f	3
c2a4bcad-3714-416e-aa80-acdb3d6218f9	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "node", "name": "app.jar", "type": "artifact"}		„app.jar“ е артефакт	f	4
a8285796-28b3-4b8b-9f1d-dba95e2f6958	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "attribute", "node": "Компјутер на корисник", "name": "Прелистувач", "aliases": ["Browser"], "node_aliases": ["User computer", "Client"]}		„Компјутер на корисник“ има елемент „Прелистувач“	f	5
f7f65192-4f21-414f-824f-29e4473a8404	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "attribute", "node": "Веб сервер", "name": "Nginx", "node_aliases": ["Web server"]}		„Веб сервер“ има елемент „Nginx“	f	6
888faf97-6fa7-4426-8a31-155e497177f9	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "relation", "a": "Компјутер на корисник", "b": "Веб сервер", "kind": "association", "a_aliases": ["User computer", "Client"], "b_aliases": ["Web server"], "label": "HTTPS"}		Асоцијација „Компјутер на корисник“ – „Веб сервер“: „HTTPS“	f	7
e9324fce-0f21-46eb-a81a-d2415c606c39	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "relation", "a": "Веб сервер", "b": "Апликациски сервер", "kind": "association", "a_aliases": ["Web server"], "b_aliases": ["Application server", "App server"], "label": "HTTP"}		Асоцијација „Веб сервер“ – „Апликациски сервер“: „HTTP“	f	8
0938cfb7-580e-4889-bcbd-a017fd640b91	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "relation", "a": "Апликациски сервер", "b": "Сервер за бази", "kind": "association", "a_aliases": ["Application server", "App server"], "b_aliases": ["Database server", "DB server"], "label": "JDBC"}		Асоцијација „Апликациски сервер“ – „Сервер за бази“: „JDBC“	t	9
c60fbcd1-8ef1-4c49-be9b-858100d45fcf	7f03c665-6c0b-4430-9fb3-c9c0c16d3c6e	diagram	{"check": "relation", "a": "app.jar", "b": "Апликациски сервер", "kind": "deploy", "b_aliases": ["Application server", "App server"]}		«deploy» од „app.jar“ кон „Апликациски сервер“	t	10
fbfe89f1-b0c6-414b-a295-a3fd8831128e	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "node", "name": "Член", "aliases": ["Member", "clen"]}		Постои „Член“	f	0
9d838e67-5af7-4957-9bb7-46444c67f9e1	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "node", "name": "Книга", "aliases": ["Book"]}		Постои „Книга“	f	1
53e70669-a124-4f17-a81f-886e5f492d6e	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "node", "name": "Позајмица", "aliases": ["Loan"]}		Постои „Позајмица“	f	2
ae6f05b6-2559-406b-a3a7-3a59474a0415	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Член", "name": "id", "node_aliases": ["Member", "clen"], "pk": true}		„Член“ има примарен клуч „id“	f	3
a77aca2c-34cc-461f-850f-14a41b80731e	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Член", "name": "име", "aliases": ["ime", "name"], "node_aliases": ["Member", "clen"]}		„Член“ има колона „име“	f	4
93e85e74-b5bf-4679-9920-54c9fa59abbb	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Член", "name": "email", "node_aliases": ["Member", "clen"]}		„Член“ има колона „email“	f	5
dcb077dc-c283-43e3-b599-39bfcc049aba	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Книга", "name": "isbn", "node_aliases": ["Book"], "pk": true}		„Книга“ има примарен клуч „isbn“	f	6
bc9ae257-a3df-4571-8978-3b519696dd33	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Книга", "name": "наслов", "aliases": ["naslov", "title"], "node_aliases": ["Book"]}		„Книга“ има колона „наслов“	f	7
a64e0ad3-57cd-4f99-8ab4-2537dd418428	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Книга", "name": "автор", "aliases": ["avtor", "author"], "node_aliases": ["Book"]}		„Книга“ има колона „автор“	f	8
e89fbb98-971f-45d6-abfc-16a473ab3fac	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Позајмица", "name": "id", "node_aliases": ["Loan"], "pk": true}		„Позајмица“ има примарен клуч „id“	f	9
1bc53f0f-f4dd-4c92-9ac2-35a2a7322496	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Позајмица", "name": "член_id", "aliases": ["clen_id", "member_id"], "node_aliases": ["Loan"], "fk": true}		„Позајмица“ има надворешен клуч „член_id“	f	10
7a40e83b-c53f-4d4d-bfd9-c97c27107a9d	9374c027-5641-4687-953e-5dc789329162	code_sample	print(attr('#bill', 'type'), $$('#percent option').map(o => o.value).join(','), $('#percent').value, exists('output#tip'), exists('output#total'))		number 10,15,20 15 true true	f	0
34d42cb6-651a-4fa0-a56b-88cbdb34d9e9	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Позајмица", "name": "книга_isbn", "aliases": ["kniga_isbn", "book_isbn"], "node_aliases": ["Loan"], "fk": true}		„Позајмица“ има надворешен клуч „книга_isbn“	f	11
a3097880-0964-4de2-8e42-00272eef33b9	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "attribute", "node": "Позајмица", "name": "датум", "aliases": ["datum", "date"], "node_aliases": ["Loan"]}		„Позајмица“ има колона „датум“	f	12
3cb2c0ca-abc3-438b-bff1-b8401c197539	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "relation", "a": "Позајмица", "b": "Член", "kind": "foreign_key", "a_aliases": ["Loan"], "b_aliases": ["Member", "clen"], "mult_a": "N", "mult_b": "1"}		Надворешен клуч „Позајмица“ (N) – „Член“ (1)	t	13
3df57e2e-ea2d-467a-a600-df9731d491a5	e71019b1-1019-4075-9a5b-a317aaf4dd0f	diagram	{"check": "relation", "a": "Позајмица", "b": "Книга", "kind": "foreign_key", "a_aliases": ["Loan"], "b_aliases": ["Book"], "mult_a": "N", "mult_b": "1"}		Надворешен клуч „Позајмица“ (N) – „Книга“ (1)	t	14
4ef8fbe6-9817-4ccc-bc03-e0e7c88661b1	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(exists('nav.menu'), count('nav.menu ul > li'), count('nav.menu li > a[href]'))		true 4 4	f	0
bf4c7f75-fda9-45ca-b941-93ea86251828	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print($$('nav.menu a').map(a => a.textContent.trim()).join(', '))		Почетна, Студии, Вести, Контакт	f	1
c095180d-d1cf-4d30-8f31-aee7bbfe1139	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(count('nav.menu a.active'), text('nav.menu a.active'))		1 Почетна	f	2
b85d0c9d-281c-4e22-b830-ee23c5b04df2	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(css('nav.menu ul', 'display'), css('nav.menu ul', 'flex-direction'), css('nav.menu ul', 'list-style-type'))		flex row none	f	3
b499e44b-52e9-40b4-bbc8-53492b774055	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(hex('nav.menu', 'background-color'), hex('nav.menu a:not(.active)', 'color'), css('nav.menu a', 'text-decoration-line'))		#1a2233 #ffffff none	f	4
9221e211-50c9-4f30-9ece-9717adce39e1	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(hex('nav.menu a.active', 'background-color'), hex('nav.menu a.active', 'color'))		#fcc419 #1a2233	t	5
bf5def3f-9b0c-4840-ba3f-62484d5375c8	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	// viewport: 375x667\nconst a = rect('nav.menu li:nth-child(1)'), b = rect('nav.menu li:nth-child(2)')\nprint(b.y > a.y, a.x === b.x)		true true	t	6
84789e1a-0bda-4e10-bb4b-53fc867d70ff	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	print(exists('nav.menu + h1') || exists('h1'))		true	t	7
c9382be4-43e2-421c-ac14-e34e3bbba231	9a3dd9dd-e4b1-4bbf-805f-35124a03fb1b	code_sample	// visual: 85			f	8
7bb0d274-eb76-4376-909c-a2f339792f9a	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(count('section.plans > article.plan'), count('.plan h3'), count('.plan .price'), count('.plan a.btn'))		3 3 3 3	f	0
df58e6e3-92de-49e3-ae2f-df81a6a9ca66	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(count('.plan') === 3 && $$('.plan').every(p => p.querySelectorAll('ul li').length >= 3))		true	f	1
ebb813b5-e76e-4073-8f87-7fbf016cd426	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(count('.plan.featured'), $$('.plan').indexOf($('.plan.featured')))		1 1	f	2
2ef04336-f03c-4387-bf18-acc8bf038b79	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(css('.plans', 'display'), css('.plans', 'grid-template-columns').split(' ').length, css('.plans', 'column-gap'))		grid 3 24px	f	3
5ea4d36d-e4f4-4f2e-aa3e-66739ca27995	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(hex('.plan', 'background-color'), css('.plan', 'border-top-left-radius'), css('.plan:not(.featured)', 'border-top-width'), hex('.plan:not(.featured)', 'border-top-color'))		#ffffff 12px 1px #d9dee7	f	4
893c6f50-e5ab-43ce-abab-4b1fbadc9fce	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(css('.plan.featured', 'border-top-width'), hex('.plan.featured', 'border-top-color'))		2px #2747c9	t	5
f64fd72c-fefb-4e2f-9b3b-2393b2ba5c05	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	print(hex('.btn', 'background-color'), hex('.btn', 'color'), css('.btn', 'text-decoration-line'))		#2747c9 #ffffff none	t	6
a9e4b340-b04f-444d-b876-22ddd640b9e4	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	// viewport: 375x667\nprint(css('.plans', 'grid-template-columns').split(' ').length, rect('.plan:nth-child(2)').y > rect('.plan:nth-child(1)').y)		1 true	t	7
8f89ebcb-d1ce-47f4-989a-3f0e8e3a6cea	36932216-3ce4-4e93-91fc-f960b8524d5b	code_sample	// visual: 85			f	8
73960fce-3f95-4059-8ad5-4f8f60b31fce	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(exists('form#signup'), exists('#name'), exists('#email'), exists('#password'), exists('form#signup button[type=submit]'))		true true true true true	f	0
8c0c113e-a267-496e-9ce4-9fae2bf7c0a3	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(['name', 'email', 'password'].every(id => !!document.querySelector(`label[for=${id}]`)))		true	f	1
bd8050c9-f0ab-4020-a2a3-8a8b87765678	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(attr('#email', 'type'), attr('#password', 'type'), attr('#password', 'minlength'))		email password 8	f	2
e307f4fa-36da-43cd-8c20-688e89185a88	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(['#name', '#email', '#password'].every(s => $(s).required))		true	f	3
b448a2b6-3d51-4214-b27c-30f43bc643ff	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	await type('#email', 'ne-e-adresa'); print($('#email').checkValidity())\nawait type('#email', 'ana@finki.ukim.mk'); print($('#email').checkValidity())		false\ntrue	t	4
398096a6-6718-48de-942f-5d27f113447a	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	const f = rect('#signup'), w = document.documentElement.clientWidth\nprint(f.width <= 360, Math.abs(f.x - (w - f.x - f.width)) <= 4)		true true	f	5
6fc7efe3-dd94-41ba-a81a-39e812173f86	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(rect('#email').y > rect('#name').y, rect('#password').y > rect('#email').y)		true true	t	6
c8274504-8806-42b1-85bf-c6f9f32efae3	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(css('#name', 'border-top-width'), hex('#name', 'border-top-color'), css('#name', 'border-top-left-radius'))		1px #d9dee7 8px	t	7
e07ef076-03b7-4290-bacc-dca04736c3b4	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	print(hex('#signup button', 'background-color'), hex('#signup button', 'color'))		#2b8a3e #ffffff	f	8
0f140c2c-3cc0-4ac5-8c41-7a79037a454e	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	// viewport: 375x667\nconst f = rect('#signup')\nprint(f.x >= 0, f.x + f.width <= document.documentElement.clientWidth, rect('#email').width > 200)		true true true	t	9
29e8d946-b83e-4e4d-864a-a809021a58c2	89a2c16d-bf0e-45ed-96e9-5489bdb8b8ed	code_sample	// visual: 85			f	10
91f955a8-2059-4e5a-bce4-a507d3ef35d9	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	print(exists('input#new'), exists('button#add'), exists('ul#list'), text('#count'))		true true true 0	f	0
531a32f8-ec70-45d0-8dd4-7a47a0cb59f8	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	await type('#new', 'Купи леб'); await click('#add')\nprint(count('#list li'), text('#list li'), $('#new').value === '')		1 Купи леб true	f	1
c58e4d96-372d-4154-9cd4-e8d92571cd15	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	await type('#new', '   '); await click('#add'); print(count('#list li'))		0	f	2
64835fbc-5ff9-4d74-bddf-f334c546428d	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	await type('#new', '  Учи CSS  '); await click('#add'); print(text('#list li'))		Учи CSS	t	3
2357548a-ed5f-41db-a16f-3ffb4a11565c	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	for (const x of ['А', 'Б', 'В']) { await type('#new', x); await click('#add') }\nprint(text('#count'))		3	f	4
bf5eeb61-ade3-4220-aeb5-dc193b4d95e5	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	for (const x of ['А', 'Б']) { await type('#new', x); await click('#add') }\nawait click('#list li')\nprint($('#list li').classList.contains('done'), text('#count'))\nawait click('#list li')\nprint($('#list li').classList.contains('done'), text('#count'))		true 1\nfalse 2	t	5
8b987fe3-92bc-443f-9190-054515c5b0eb	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	await type('#new', 'Х'); await click('#add'); await click('#list li')\nprint(css('#list li.done', 'text-decoration-line'), hex('#list li.done', 'color'))		line-through #868e96	t	6
60ba7f8b-59c9-44b0-aa7b-ae13cc27446e	8685efdd-a1cd-4ae8-a70d-91482a195494	code_sample	// visual: 80			f	7
0ce4ae74-04dc-47c3-b3cc-bc5342525c68	9374c027-5641-4687-953e-5dc789329162	code_sample	await type('#bill', '100'); await type('#percent', '20'); print(text('#tip'), text('#total'))		20.00 120.00	f	2
32d65988-cf2b-4c3b-b825-7393010e4550	9374c027-5641-4687-953e-5dc789329162	code_sample	await type('#bill', '45.50'); await type('#percent', '10'); print(text('#tip'), text('#total'))		4.55 50.05	t	3
10d3fabf-a7eb-4f8e-bc98-88eb2989718e	9374c027-5641-4687-953e-5dc789329162	code_sample	await type('#bill', '-5'); print(text('#tip'), text('#total'))\nawait type('#bill', ''); print(text('#tip'), text('#total'))		0.00 0.00\n0.00 0.00	t	4
8337e250-2727-48c9-8ec0-4df5946b1160	9374c027-5641-4687-953e-5dc789329162	code_sample	const c = rect('main') || rect('.calc'); print(rect('#bill').width <= 340, Number(css('#total', 'font-weight')) >= 700)		true true	f	5
ebae9ebc-d65b-40eb-b3e8-0a2d328caa8a	9374c027-5641-4687-953e-5dc789329162	code_sample	// visual: 80			f	6
f803d998-c1b4-4822-8773-4e930065cb3f	7deda453-9f15-447d-893c-6a1efcbe2b29	code_sample	git rev-list --count HEAD		1	f	0
38e07613-279e-4303-8ddc-4dd55c9e875f	7deda453-9f15-447d-893c-6a1efcbe2b29	code_sample	git log -1 --format=%s		Initial commit	f	1
34085a5c-4928-4d60-b02b-00c8a48534f7	7deda453-9f15-447d-893c-6a1efcbe2b29	code_sample	git ls-files | sort		.gitignore\nREADME.md	f	2
6749883f-252b-4c6a-b9d5-e583b42e1050	7deda453-9f15-447d-893c-6a1efcbe2b29	code_sample	cat README.md; cat .gitignore		# ALE\n*.log	t	3
5e89ae92-1f1b-4d30-86a8-3fa8b3241000	7deda453-9f15-447d-893c-6a1efcbe2b29	code_sample	git status --porcelain | wc -l; test -f debug.log && echo log-exists		0\nlog-exists	t	4
1102de26-b4d2-45a2-aec9-7b9bd23c1aa5	47a54cea-9655-42a8-9dc5-e78f5d827b55	code_sample	git branch --show-current		main	f	0
45e5cb95-06f6-4e92-b1f9-8d003c134e20	47a54cea-9655-42a8-9dc5-e78f5d827b55	code_sample	git branch --list 'feature/login' | tr -d ' *'		feature/login	f	1
e0208366-981a-448c-b1f9-e16d32e24941	47a54cea-9655-42a8-9dc5-e78f5d827b55	code_sample	git log --merges --format=%s		Merge feature/login	f	2
f0a0c341-d8a8-4fda-b88d-ef342a516064	47a54cea-9655-42a8-9dc5-e78f5d827b55	code_sample	cat login.txt; git rev-list --count HEAD		login\n3	t	3
b24a9a41-ea69-4bb7-8373-6c249231014f	47a54cea-9655-42a8-9dc5-e78f5d827b55	code_sample	git log -1 --format=%s $(git rev-list --max-parents=0 HEAD)		Start	t	4
0b30beea-c8bc-4127-b785-9a083c509cbc	31f3e051-1bca-4de5-a3a5-0061316c09ee	code_sample	cat app.txt		v1	f	0
a07dc546-48e6-4302-ae9a-70f4636f9840	31f3e051-1bca-4de5-a3a5-0061316c09ee	code_sample	git rev-list --count HEAD; git log -1 --format=%s		3\nRevert "Experiment"	f	1
d830b6f0-ece5-47da-8b98-8be7c8478657	31f3e051-1bca-4de5-a3a5-0061316c09ee	code_sample	git cat-file -t v1.0; git tag -l --format='%(contents:subject)' v1.0		tag\nFirst release	f	2
a0cd4e7c-22b4-4eb7-984a-f5c6112e1e2f	31f3e051-1bca-4de5-a3a5-0061316c09ee	code_sample	[ "$(git rev-parse 'v1.0^{commit}')" = "$(git rev-list --max-parents=0 HEAD)" ] && echo same		same	t	3
eec23628-3e29-43b9-adb6-f25857e3231a	8c95a446-f74e-4c44-b6d2-4c562deb13eb	code_sample	cat config.txt		port=9000	f	0
e69c4435-d76c-4112-93c4-d1c3992c027a	8c95a446-f74e-4c44-b6d2-4c562deb13eb	code_sample	git log -1 --format=%s; git log -1 --format=%p | wc -w		Resolve port\n2	f	1
a32f491b-cbd0-4e0d-be71-50e4ac3f9873	8c95a446-f74e-4c44-b6d2-4c562deb13eb	code_sample	grep -c '<<<<<<<' config.txt || true		0	t	2
ca191930-9bc4-4660-b39d-81b25d0f2de9	8c95a446-f74e-4c44-b6d2-4c562deb13eb	code_sample	git status --porcelain | wc -l; git branch --show-current		0\nmain	t	3
51c9f7a5-6435-4cc8-9eea-2fb50050ab53	909d3e02-e5fc-432e-b642-fe1ccae49b99	stdin_stdout		10.0.0.1 GET / 200\n10.0.0.2 GET /a 500\n10.0.0.1 POST /login 302\n	requests: 3\nerrors: 1\ntop: 10.0.0.1	f	0
90aae602-fd25-4628-ad58-52273007d091	909d3e02-e5fc-432e-b642-fe1ccae49b99	stdin_stdout			requests: 0\nerrors: 0\ntop: -	f	1
4f0c2285-3b94-4cba-81ca-eee39c6db70b	909d3e02-e5fc-432e-b642-fe1ccae49b99	stdin_stdout		10.0.0.9 GET / 503\n10.0.0.3 GET / 200\n10.0.0.9 GET / 504\n10.0.0.3 GET / 404\n	requests: 4\nerrors: 2\ntop: 10.0.0.3	t	2
94887cf4-8652-48d9-a725-8df1b3367b14	909d3e02-e5fc-432e-b642-fe1ccae49b99	stdin_stdout		1.1.1.1 GET / 500\n	requests: 1\nerrors: 1\ntop: 1.1.1.1	t	3
641712e6-4601-40fc-8cad-e1d0bc3be508	da92593b-6b0d-4f39-84f6-2ff4e820d9b2	code_sample	health 200; health 404; health 503		UP\nDEGRADED\nDOWN	f	0
15824095-e4e5-4bc0-a7de-0aa20fde997f	da92593b-6b0d-4f39-84f6-2ff4e820d9b2	code_sample	health abc; health 301		DOWN\nDEGRADED	f	1
7db7e636-f549-4e34-9ad2-96cc550294e3	da92593b-6b0d-4f39-84f6-2ff4e820d9b2	code_sample	summary 200 201 404		UP=2 DEGRADED=1 DOWN=0	f	2
148da461-baad-4c5e-b775-8828f747b796	da92593b-6b0d-4f39-84f6-2ff4e820d9b2	code_sample	summary 500 x 299 300		UP=1 DEGRADED=1 DOWN=2	t	3
4fd5a9b9-9039-4491-a8d0-3b18f50895e0	da92593b-6b0d-4f39-84f6-2ff4e820d9b2	code_sample	summary		UP=0 DEGRADED=0 DOWN=0	t	4
c7555abe-88fa-4787-b23f-a48d8f7e48d4	7f87f39b-7e29-4c9e-bb37-4ab66877a897	code_sample	assert stages() == ['python:3.12-slim'], 'base image: python:3.12-slim'\nassert workdir() == '/app', 'WORKDIR /app'		OK	f	0
7f851592-f241-4844-8f73-4069d2978e8e	7f87f39b-7e29-4c9e-bb37-4ab66877a897	code_sample	c = copies()\nassert c and c[0][0] == 'requirements.txt', 'copy requirements.txt first'\nassert any(s == '.' for s, _ in c[1:]), 'then copy the rest of the code'\nassert has('RUN', '--no-cache-dir'), 'pip install --no-cache-dir'		OK	f	1
06af8dc7-e053-43ef-98c4-26d56c3210e6	7f87f39b-7e29-4c9e-bb37-4ab66877a897	code_sample	assert user() not in (None, 'root', '0'), 'switch to a non-root user'\nassert '8000' in exposed(), 'EXPOSE 8000'		OK	f	2
14476dc5-3ae9-4b6f-a4c3-a18408f17fdc	7f87f39b-7e29-4c9e-bb37-4ab66877a897	code_sample	assert last('CMD').strip().startswith('['), 'CMD in JSON form'\nassert cmd() == ['gunicorn', '-b', '0.0.0.0:8000', 'app:app']		OK	t	3
7f9f4835-fcb3-4448-add9-888fb7d6fbba	7f87f39b-7e29-4c9e-bb37-4ab66877a897	code_sample	order = [w for w, _ in D]\nassert order.index('USER') > max(i for i, w in enumerate(order) if w == 'RUN'), 'USER after the RUN steps'		OK	t	4
cdb81cb5-04e1-4d07-8dec-5b8c6374ad64	8caaa947-5656-4014-b78a-cd573199ac32	code_sample	assert len(stages()) == 2, 'two stages (two FROM lines)'\nassert instr('FROM')[0].lower().split()[-1] == 'build', 'name the first stage: AS build'		OK	f	0
5e50b1a5-a355-48ea-ba63-3c5d139d6442	8caaa947-5656-4014-b78a-cd573199ac32	code_sample	assert has('RUN', 'npm ci'), 'npm ci'\nassert not has('RUN', 'npm install'), 'npm ci, not npm install'\nassert has('RUN', 'npm run build')		OK	f	1
232c51dd-0b07-4d51-810a-18a89ca785a4	8caaa947-5656-4014-b78a-cd573199ac32	code_sample	assert stages()[-1] == 'nginx:1.27-alpine', 'final image: nginx:1.27-alpine'\nassert any('--from=build' in a and '/app/dist' in a and '/usr/share/nginx/html' in a for a in instr('COPY')), 'COPY --from=build /app/dist /usr/share/nginx/html'		OK	f	2
aa1578c5-3e0a-4239-83b7-bc86fb62e1ed	8caaa947-5656-4014-b78a-cd573199ac32	code_sample	assert exposed() == ['80'], 'EXPOSE 80'		OK	t	3
45f5a482-13ff-4eb6-ab9a-ae06e7dc287b	c3fed460-c356-44b9-8a49-ec90e1df2366	code_sample	assert y.get('name') == 'CI'\non = get(y, 'on')\nassert isinstance(on, dict) and set(on) >= {'push', 'pull_request'}, 'on: push and pull_request'\nassert 'main' in get(on, 'push.branches', []) and 'main' in get(on, 'pull_request.branches', []), 'only the main branch'		OK	f	0
c491d104-a8be-47c9-9935-f6720505cfb5	c3fed460-c356-44b9-8a49-ec90e1df2366	code_sample	assert get(y, 'jobs.test.runs-on') == 'ubuntu-latest', 'job test on ubuntu-latest'		OK	f	1
9947d936-aba8-44ca-be42-9e97f065d71f	c3fed460-c356-44b9-8a49-ec90e1df2366	code_sample	uses = find(y, 'uses')\nassert 'actions/checkout@v4' in uses and 'actions/setup-python@v5' in uses\nassert str(find(y, 'python-version')[0]) == '3.12', 'python-version "3.12" (in quotes!)'		OK	f	2
5c256dd8-a38c-49db-8030-d07817f038f7	c3fed460-c356-44b9-8a49-ec90e1df2366	code_sample	runs = ' | '.join(find(y, 'run'))\nassert 'pip install -r requirements.txt' in runs and 'pytest' in runs\nsteps = get(y, 'jobs.test.steps')\nassert steps[0].get('uses') == 'actions/checkout@v4', 'checkout first'		OK	t	3
fa30cde4-c53f-4795-82f6-278264cbb29b	dac4643c-3dd9-4645-b325-4a0aae57b7e3	code_sample	w = get(y, 'services.web')\nassert w and w.get('build') == '.', 'web: build: .'\nassert '8000:8000' in [str(p) for p in w.get('ports', [])], 'web: port 8000:8000'		OK	f	0
8551947a-8572-4412-887a-cee187d806df	dac4643c-3dd9-4645-b325-4a0aae57b7e3	code_sample	dep = get(y, 'services.web.depends_on')\nassert dep and 'db' in dep, 'web depends on db'\nenv = get(y, 'services.web.environment')\nenv = env if isinstance(env, dict) else dict(e.split('=', 1) for e in env)\nassert env.get('DATABASE_URL') == 'postgresql://app:secret@db:5432/app'		OK	f	1
f294d7bd-29eb-455e-abb5-715ccc508744	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		0 0\n	Invalid input	f	8
4c5bd057-f170-4014-92cd-1506c86f5209	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		5573 57\n	PAREN	f	9
2be92d23-fdef-4069-9103-30297eac5666	dac4643c-3dd9-4645-b325-4a0aae57b7e3	code_sample	db = get(y, 'services.db')\nassert db and db.get('image') == 'postgres:16'\nenv = db.get('environment') or {}\nenv = env if isinstance(env, dict) else dict(e.split('=', 1) for e in env)\nassert env.get('POSTGRES_USER') == 'app' and env.get('POSTGRES_PASSWORD') == 'secret' and env.get('POSTGRES_DB') == 'app'		OK	f	2
1c8fed30-1278-48b2-be8a-0460ff375064	dac4643c-3dd9-4645-b325-4a0aae57b7e3	code_sample	assert 'db-data:/var/lib/postgresql/data' in get(y, 'services.db.volumes', []), 'mount db-data'\nassert 'db-data' in (y.get('volumes') or {}), 'declare the volume db-data'		OK	t	3
ffa812f1-d651-4f17-8238-8449e1618c87	9bad1ab2-d43c-4c3f-902d-cdfacbd55e20	code_sample	kinds = {d.get('kind'): d for d in docs}\nassert set(kinds) >= {'Deployment', 'Service'}, 'a Deployment and a Service'\nd = kinds['Deployment']\nassert get(d, 'metadata.name') == 'ale-web' and get(d, 'spec.replicas') == 3		OK	f	0
99e495bc-75ce-41c8-81aa-a3a92f7adca1	9bad1ab2-d43c-4c3f-902d-cdfacbd55e20	code_sample	d = next(x for x in docs if x.get('kind') == 'Deployment')\nassert get(d, 'spec.selector.matchLabels.app') == 'ale-web' and get(d, 'spec.template.metadata.labels.app') == 'ale-web', 'labels app: ale-web'\nc = get(d, 'spec.template.spec.containers.0')\nassert c['image'] == 'ghcr.io/finki/ale-web:1.0' and get(c, 'ports.0.containerPort') == 8000		OK	f	1
6a1e51fe-c2cc-48d4-acf3-d90f80b32179	9bad1ab2-d43c-4c3f-902d-cdfacbd55e20	code_sample	d = next(x for x in docs if x.get('kind') == 'Deployment')\nc = get(d, 'spec.template.spec.containers.0')\nassert get(c, 'resources.limits.memory') == '256Mi' and get(c, 'resources.requests.cpu') == '100m'\nassert get(c, 'readinessProbe.httpGet.path') == '/health'		OK	t	2
233d600c-6e33-4111-a7f4-d5008fe77e3e	9bad1ab2-d43c-4c3f-902d-cdfacbd55e20	code_sample	s = next(x for x in docs if x.get('kind') == 'Service')\nassert get(s, 'spec.type', 'ClusterIP') == 'ClusterIP'\nassert get(s, 'spec.ports.0.port') == 80 and get(s, 'spec.ports.0.targetPort') == 8000 and get(s, 'spec.selector.app') == 'ale-web'		OK	f	3
964e676c-7fe5-4300-b040-2b9725c8ae01	0a0649ba-6176-4a9c-ae51-e1a98bf40585	code_sample	r = variable('region')\nassert ref(r.get('type')) == 'string' and r.get('default') == 'eu-central-1'\nb = variable('bucket_name')\nassert 'default' not in b, 'bucket_name has no default'\nassert ref(provider('aws').get('region')) == 'var.region', 'provider region = var.region'		OK	f	0
9ebfd273-0413-446c-99c3-f3860429c89d	0a0649ba-6176-4a9c-ae51-e1a98bf40585	code_sample	b = resource('aws_s3_bucket', 'logs')\nassert ref(b.get('bucket')) == 'var.bucket_name', 'bucket = var.bucket_name'\nassert (b.get('tags') or {}).get('Env') == 'dev', 'tag Env = "dev"'		OK	f	1
a43126a4-3f52-4a07-8d42-8eaf9242953e	0a0649ba-6176-4a9c-ae51-e1a98bf40585	code_sample	v = resource('aws_s3_bucket_versioning', 'logs')\nassert ref(v.get('bucket')) == 'aws_s3_bucket.logs.id'\nassert block(v, 'versioning_configuration').get('status') == 'Enabled'		OK	f	2
3de44e18-95da-469c-a982-c9b5e34954ec	0a0649ba-6176-4a9c-ae51-e1a98bf40585	code_sample	assert ref(output('bucket_arn').get('value')) == 'aws_s3_bucket.logs.arn'		OK	t	3
7c3437f8-99be-4086-aa9b-6ed7b863afd8	d2cb25c1-adc9-4799-b9e0-cb2bfe186082	code_sample	sg = resource('aws_security_group', 'web')\nrules = {int(r['from_port']): r for r in sg.get('ingress', [])}\nassert set(rules) == {22, 80}, 'ingress on ports 22 and 80'\nassert [ref(c) for c in rules[22]['cidr_blocks']] == ['var.admin_cidr'], 'SSH only from var.admin_cidr'\nassert rules[80]['cidr_blocks'] == ['0.0.0.0/0']		OK	f	0
40a05c9c-995e-46f8-9c84-8f18e2fd0b3f	d2cb25c1-adc9-4799-b9e0-cb2bfe186082	code_sample	sg = resource('aws_security_group', 'web')\neg = sg.get('egress', [])\nassert eg and str(eg[0]['protocol']) == '-1', 'egress to everything'		OK	f	1
69371744-7b56-4369-a0a6-dc398c40d43f	d2cb25c1-adc9-4799-b9e0-cb2bfe186082	code_sample	i = resource('aws_instance', 'web')\nassert ref(i['ami']) == 'var.ami_id' and i['instance_type'] == 't3.micro'\nassert [ref(x) for x in i['vpc_security_group_ids']] == ['aws_security_group.web.id']\nassert i.get('tags', {}).get('Name') == 'ale-web'		OK	f	2
ba0d491a-b16a-447c-923e-fd118977e0f6	d2cb25c1-adc9-4799-b9e0-cb2bfe186082	code_sample	variable('admin_cidr'); variable('ami_id')\nassert ref(output('public_ip')['value']) == 'aws_instance.web.public_ip'		OK	t	3
fcc50b72-79ab-4d59-9d18-1050739086a5	7bda006a-9575-483b-84ad-e41a1cde9779	code_sample	assert locals_().get('common_tags') == {'Project': 'ale', 'Owner': 'finki'}, 'common_tags'		OK	f	0
b305d9f3-ae25-4a4a-996b-f68c09d87eff	7bda006a-9575-483b-84ad-e41a1cde9779	code_sample	m = module('vpc')\nassert m['source'] == 'terraform-aws-modules/vpc/aws' and m['version'] == '~> 5.0'\nassert m['cidr'] == '10.0.0.0/16' and m['name'] == 'ale'		OK	f	1
f3f05d1b-4813-47eb-82ee-af66a8313a75	7bda006a-9575-483b-84ad-e41a1cde9779	code_sample	m = module('vpc')\nassert m['azs'] == ['eu-central-1a', 'eu-central-1b']\nassert m['public_subnets'] == ['10.0.1.0/24', '10.0.2.0/24']\nassert ref(m['tags']) == 'local.common_tags'		OK	t	2
61b46e0a-5ffd-4055-8e8f-14e5bf6ba083	7bda006a-9575-483b-84ad-e41a1cde9779	code_sample	assert ref(output('vpc_id')['value']) == 'module.vpc.vpc_id'		OK	f	3
267a9d24-27c5-4a86-b89d-02d99441fb76	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		99 500\n	200	f	0
ee80b8a3-afac-4d57-9b7b-67835e6cd646	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		10 19\n	NE	f	1
5f76dbed-1a38-47cb-826c-a9d1d9da8173	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		1230 25000\n	2000	f	2
f1d44cd2-03fe-4658-9f27-ab8c87fb58ea	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		1 2\n	2	f	3
199dc209-1761-4921-9054-ea4f656fa3a2	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		1000 5000\n	2000	f	4
26c2324f-839e-4d4e-9832-f6b0b3b1655b	62417491-324b-423f-85ad-f139d96f284b	stdin_stdout		99 199\n	NE	f	5
19f91d00-3cee-469c-9acc-6cb99132e0fa	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		5\n	Brojot ne e validen	f	0
4d21e1d1-389c-4a75-8161-50b65214af52	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		50\n	49	f	1
68d43ca1-a2c1-4d95-aabb-afccbe90ffa6	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		100\n	89	f	2
8a2291d1-97c2-48bf-b5d6-97c4c1ad392e	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		17\n	9	f	3
25d67bed-dad3-4709-abdd-1941342afe10	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		-5\n	Brojot ne e validen	f	4
f398b1d7-73bd-4bc6-a50f-1cd8a1b0aae4	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		990\n	987	f	5
42268ec9-48ac-45e5-926d-eeb7cef19818	c904fa4d-4ac1-4593-8edb-63ea197c5a69	stdin_stdout		10\n	9	f	6
4ef121ca-8a80-49ad-bd50-d5a3e427c418	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		10\n	8	f	0
479bab0a-a945-43b3-afaa-382fb3b6569f	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		50\n	48	f	1
97348134-93a3-4889-a061-b914f472edd9	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		1000\n	960	f	2
c6855ae3-a40f-4e7b-8c18-ec2dc7663f96	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		11\n	10	f	3
46a6cb19-97ee-4a10-8fe0-1f3b15af52e7	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		30\n	24	f	4
6e477d75-03ff-4235-b12d-d69e3bd9ee44	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		40\n	36	f	5
41ebad83-d95a-45fd-88b5-6700950c6909	5b54df3c-259d-41ad-be90-be985d43a701	stdin_stdout		20\n	18	f	6
cb541cfd-b144-4398-b911-72f3f000ab58	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		ako34D neka12em bashka41mewr20!\n	107	f	0
19e4dcdc-f898-4e0f-8952-5529d723b258	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		1ako fdsfsfD ne 12 ka10em bashka10mewr5!\n	38	f	1
77ee6987-72b9-429a-87f1-289b69c3343e	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		Weiur23j sdlkj22lkadad 21kjs 20sdkjsd!\n	86	f	2
da25fa47-350e-4edc-ab2a-48961b9bce52	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		ako34D neka12em bashka41mewr!\n	87	f	3
ee166ada-0f1e-4712-8b86-195c6f1fe22e	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		ako3 1 4D4 ne 88 ka12em ba12shka41mewr!\n	165	f	4
19827bdf-ec92-43f3-80ca-bc62d3cc612e	f24d9543-4edb-4eb0-9de3-46e328b56f2d	stdin_stdout		9Ako D1me ima 12 evra, za 9 dena, kje kupi 10ka!\n	41	f	5
30e4df1d-b2f7-4b82-ba01-e07e7a3b0e86	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		12345678 1357\n	PAREN	f	0
20737e79-96bd-47c4-ac09-213c73f4f487	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		15370 57\n	PAREN	f	1
4e00a4b5-4ec0-4d6f-8a83-2ee498867cf1	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		1537 57\n	NE	f	2
401c9600-dce6-48af-997d-c2c16c71dd46	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		-6 99\n	Invalid input	f	3
c7f70634-5273-4e64-b357-e8a5b2d7f25d	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		5573 58\n	NE	f	4
6577401f-0a1f-4f0e-b3f7-d1d330e81c5e	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		1234 13\n	PAREN	f	5
786aeced-fa4a-4b57-a734-42d89430e318	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		567890 7\n	NE	f	6
9ca8ab79-103b-4315-a7ff-5b4b62624c64	e2ca494b-a8e9-45ff-879e-72d937b03d7d	stdin_stdout		45 14456\n	PAREN	f	7
dbdd3737-450f-4737-8b18-f68744808b40	4b264492-51c6-4123-ab54-80d2ed44bab7	stdin_stdout		100\n50 50\n-50 -50\n-99 199\n32 98\n0 0\n	Vnesovte 2 parovi od broevi chij zbir e 100\nProcentot na parovi so zbir 100 e 50%\n	f	0
401a5bd0-0f9b-46d7-947d-f42b419f0ffe	4b264492-51c6-4123-ab54-80d2ed44bab7	stdin_stdout		100\n12 78\n100 1\n0 99\n13 12\n21 12\n-5 90\n9 -2\n0 0\n	Vnesovte 0 parovi od broevi chij zbir e 100\nProcentot na parovi so zbir 100 e 0%\n	f	1
240d4831-3316-4602-962d-fda66d64b6d9	4b264492-51c6-4123-ab54-80d2ed44bab7	stdin_stdout		26\n14 12\n4 23\n5 20\n0 0\n	Vnesovte 1 parovi od broevi chij zbir e 26\nProcentot na parovi so zbir 26 e 33.3333%\n	f	2
e405fd7f-d0b0-4f22-909d-2035d5281188	4b264492-51c6-4123-ab54-80d2ed44bab7	stdin_stdout		21\n42 -21\n-20 41\n2 19\n3 17\n6 54\n0 0\n	Vnesovte 3 parovi od broevi chij zbir e 21\nProcentot na parovi so zbir 21 e 60%\n	f	3
f1ab7f4a-056c-4b42-9bb5-fda53128022e	4b264492-51c6-4123-ab54-80d2ed44bab7	stdin_stdout		1\n-2 3\n15 -14\n1 0\n0 1\n0 0\n	Vnesovte 4 parovi od broevi chij zbir e 1\nProcentot na parovi so zbir 1 e 100%\n	f	4
a3b3687e-3397-4980-915f-fb68fd5fdfbf	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		11\n	%@@@@@@@@@%\n%.........%\n%.........%\n%.........%\n%.........%\n%.........%\n%.........%\n%.........%\n%.........%\n%.........%\n%@@@@@@@@@%	f	0
a7f3ca2f-f8f8-4b4f-92d3-1e2489815556	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		4\n	%@@%\n%..%\n%..%\n%@@%	f	1
d9b4e16f-6716-4a58-ae02-06799aadc691	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		9\n	%@@@@@@@%\n%.......%\n%.......%\n%.......%\n%.......%\n%.......%\n%.......%\n%.......%\n%@@@@@@@%	f	2
d3bb6141-7b2b-4055-961c-909bea53cc79	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		5\n	%@@@%\n%...%\n%...%\n%...%\n%@@@%	f	3
612e56f9-6c4e-4c1a-8603-c6da42898d71	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		3\n	%@%\n%.%\n%@%	f	4
f97d887f-c710-43bb-8e84-6413951b9f89	f9c379c6-91f3-4005-9d5a-32a8eb262bec	stdin_stdout		10\n	%@@@@@@@@%\n%........%\n%........%\n%........%\n%........%\n%........%\n%........%\n%........%\n%........%\n%@@@@@@@@%	f	5
d1666e63-81e9-459f-897b-3e72a0a97ce4	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		88 7\n	86	f	0
30348b21-996b-4787-8d5b-90dbe262ea47	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		123456789 5\n	123449999	f	1
1e67af10-4e8a-48d7-a3df-3bc09e819d33	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		56 98\n	55	f	2
f58716fd-9a6c-4c5c-bdaa-4995bb207b9f	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		9 123456789\n	0	f	3
17b488a7-6938-4e1c-8481-a42d1352c1f8	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		45 8\n	44	f	4
bc1571be-6eed-48b1-ad8f-a0a33fe311b4	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		12 819\n	7	f	5
7bded83e-514f-4041-8012-c7ef2342e701	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		12 111\n	9	f	6
b8d3a28f-2956-4709-8211-d2b8f0da0d12	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		64 123456\n	9	f	7
02e5dcce-6b5c-44a3-8731-eba295531622	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		400 897\n	366	f	8
7149d622-233c-45aa-bd76-52e16970d61b	d9d6fe0c-ceec-4314-b841-0af653915f67	stdin_stdout		2 1\n	0	f	9
68c301b4-c3a3-426f-aac9-04b8d8f34bf2	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		0\n1\n0\n0\n0\n1\nd\n0\n0\n0\n1\n.\n	Poln pogodok	f	0
4ed4e7c0-5970-42dd-a085-f2e5077e7e25	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		A\n7\nF\n2\n0\nc\nA\n5\nA\na\nA\na\nA\n5\n.\n	116	f	1
5d016ce6-6bcb-4693-a5a2-ac51fb7d0a64	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		5\n7\ne\n8\n0\n0\nF\n6\nC\n2\n2\n0\nA\n9\nb\n.\n	101	f	2
bbce0942-115a-46be-b19f-19cea6aeb0ff	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		A\n7\nF\n2\n0\nc\nA\n5\n.\n	61	f	3
bbdcb775-3512-491c-8079-4feb1d7b2b4c	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		A\n7\n3\nF\n2\n0\nc\nA\n5\n.\n	Pogodok	f	4
7b8c4a28-6474-4ce4-a601-a17c1337033c	a24deeaf-7da6-4f0f-8f95-a62ecd0de7a4	stdin_stdout		7\ne\n8\n0\n0\nF\n6\nC\n2\n2\n0\nA\n9\nb\n.\n	Pogodok	f	5
4b00dae5-aa0a-4de4-b871-11722f504f5b	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		343\n22\n4624\n123456\n6231209\n9\nk\n	343\n4624\n6231209	f	0
2c43b735-b058-4767-b88b-38250e3b257a	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		10\n11\n123\n9876\n12345\n543210\nk\n	10	f	1
f8b6823e-ddf4-4dd4-ae9a-d7518a61769a	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		5\n-10\n-9261\n9\n12\nk\n	12	f	2
fb9954d8-3e01-4fe3-ad47-e537e049ca3c	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		1221\n3266\n11111\n98776\n12231\n55661\n22\n777\n31\nk\n	31	f	3
277ee301-6224-4a5b-9d5e-2244fdceace2	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		120\n3241\n31425\n36475\nk\n	120\n3241\n31425\n36475	f	4
9a247c4d-714a-44e3-985b-6214de29566e	663df95a-04b2-45e8-8e0b-6f16f4594318	stdin_stdout		-12065\n12065\n13269\n9876\n6545\n12321\nk\n	12065	f	5
8ed29c3a-de47-4794-8780-0799968a7e17	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		5005\n5050\n60619\n21365\n12345\n8045\n8050\nk\n	5050\n60619\n8050	f	0
2995a83d-940b-4f5e-8f78-2beeffbe7088	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		12345\n54321\n12063\n70819\nk\n	70819	f	1
8fe13a7b-5d81-4a93-8255-2b97a733f198	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		-9016\n-5\n-91\n5\n19\n50\n10\nk\n	19\n50	f	2
6f0bf8b8-a483-4f35-9ba4-969b17a3f86e	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		508294\n2\n2638\n889\n81\n10\n16\n927\nk\n	508294\n2638\n81\n16\n927	f	3
1ef72458-f125-4005-be88-f6793578e90d	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		19\nk\n	19	f	4
fb6ce2b1-973e-4f9d-b77d-ad9f848751bd	2b4bc70f-6d82-4f2f-a23d-830ae0275bf4	stdin_stdout		-15\n15\n5509\n505\n50619\n1928370\nk\n	15\n505\n50619\n1928370	f	5
\.


--
-- Data for Name: user_ai_keys; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.user_ai_keys (user_id, provider, model, base_url, api_key_encrypted, key_hint, updated_at) FROM stdin;
\.


--
-- Data for Name: user_profiles; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.user_profiles (user_id, avatar, avatar_type, title, bio, office, consultation_hours, website, index_number, study_program, study_year, show_email, updated_at, email_reminders) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: ale
--

COPY public.users (id, email, password_hash, name, role, created_at, auth_provider, avatar_version) FROM stdin;
acd51be1-b161-43b4-9fa6-5cd4dd7b55dc	admin@example.com	$pbkdf2-sha256$29000$v3euFeJcSynF.J8zxvhf6w$rAskmpzE6dlJy5U4XJO1VUhBSw3JnuIh1OVwZf9WWZc	Admin	admin	2026-10-27 21:19:15.233421	password	\N
856aefa8-f9b0-436c-a1b2-26ab0e2997f7	profesor1@finki.mk	$pbkdf2-sha256$29000$7x3D2JtTKuV8T4nRGmMMgQ$xbIc8MN.q0wEMJEz9KbzxKsFTNQh.UqfBnIgu4RCiLQ	profesor1	professor	2026-10-27 21:39:44.500493	password	\N
92485f51-e2ab-4aea-9b03-720c1a4f4421	student1@students.finki.mk	$pbkdf2-sha256$29000$IqSUknKutbbWWut9TwlhjA$5CVmGx4t.mPVRI08wdJeOJmXLSs4QnFI49H1OA.drco	student1	student	2026-10-27 21:40:59.691345	password	\N
426bbbba-3b70-4a0a-b950-21978ec3ab3f	demo.profesor@finki.ukim.mk	$pbkdf2-sha256$29000$9r7Xeg/h3Lv3vtf63/s/Zw$uUVlChDUvT8kEB2/NxLednhasRaowl42FAWQl3YayoY	demo.profesor	student	2026-10-27 23:33:32.405465	password	\N
ef9d51a2-8ed1-45ea-a026-6f2cd1ee13a2	student2@students.finki.mk	$pbkdf2-sha256$29000$A4DwHuMc43yvVaqV0vpf6w$hO.2c.C0Y8z4LJ4f58s7CZgADWXZhS4LL2CeqkkhEnA	student2	student	2026-10-27 23:35:21.662165	password	\N
5fc24293-643d-4d5d-8ae0-095ea03d3cb1	student3@students.finki.ukim.mk	$pbkdf2-sha256$29000$xphzDgHg/N.7t3aO0drbew$sfS8.zcOj41STKk4zBtTC2slo1FHCv7sTX321Z4blAo	student3	student	2026-10-27 23:35:49.303063	password	\N
67cb57de-f667-4643-b18a-b135070bb2e5	student4@students.finki.ukim.mk	$pbkdf2-sha256$29000$pBRiLCWkdG7tHcPYm7O2Ng$YzMHsk/RDuUUYq2pdTu1RWpwvZrsaF32aYNzaOyoUfw	student4	student	2026-10-27 23:36:18.963563	password	\N
788e299a-5aed-4d68-84cd-de6b55ff5369	demo.asistent@finki.ukim.mk	$pbkdf2-sha256$29000$OwdAyJkTIgSA8L7Xei9lbA$zihYG3exdl0VAOBItlZ44MjB83P8ApStyb2nr20Vjvk	demo.asistent	assistant	2026-10-27 23:34:04.778912	password	\N
a6e4546c-b906-4a1a-9229-e10633019f6d	demo.laborant@finki.ukim.mk	$pbkdf2-sha256$29000$WMsZQ2gthfCeM4ZQ6n2v1Q$GdXz9NB8MJ.2a6./dOXOo.Derk3m2whbYz3RWUSP56k	demo.laborant	assistant	2026-10-27 23:34:33.150862	password	\N
\.


--
-- Name: ai_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ale
--

SELECT pg_catalog.setval('public.ai_settings_id_seq', 1, false);


--
-- Name: events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ale
--

SELECT pg_catalog.setval('public.events_id_seq', 56, true);


--
-- Name: exam_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ale
--

SELECT pg_catalog.setval('public.exam_events_id_seq', 1, false);


--
-- Name: ai_settings ai_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.ai_settings
    ADD CONSTRAINT ai_settings_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: assignment_attempts assignment_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_attempts
    ADD CONSTRAINT assignment_attempts_pkey PRIMARY KEY (id);


--
-- Name: assignment_tasks assignment_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_tasks
    ADD CONSTRAINT assignment_tasks_pkey PRIMARY KEY (id);


--
-- Name: assignments assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_pkey PRIMARY KEY (id);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);


--
-- Name: code_comments code_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.code_comments
    ADD CONSTRAINT code_comments_pkey PRIMARY KEY (id);


--
-- Name: course_groups course_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_groups
    ADD CONSTRAINT course_groups_pkey PRIMARY KEY (id);


--
-- Name: course_materials course_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_materials
    ADD CONSTRAINT course_materials_pkey PRIMARY KEY (id);


--
-- Name: course_members course_members_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_members
    ADD CONSTRAINT course_members_pkey PRIMARY KEY (id);


--
-- Name: courses courses_join_code_key; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_join_code_key UNIQUE (join_code);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: diagram_uploads diagram_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.diagram_uploads
    ADD CONSTRAINT diagram_uploads_pkey PRIMARY KEY (id);


--
-- Name: elective_choices elective_choices_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_choices
    ADD CONSTRAINT elective_choices_pkey PRIMARY KEY (id);


--
-- Name: elective_plans elective_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_plans
    ADD CONSTRAINT elective_plans_pkey PRIMARY KEY (user_id);


--
-- Name: elective_requests elective_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_requests
    ADD CONSTRAINT elective_requests_pkey PRIMARY KEY (id);


--
-- Name: email_deliveries email_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.email_deliveries
    ADD CONSTRAINT email_deliveries_pkey PRIMARY KEY (id);


--
-- Name: emails emails_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: exam_events exam_events_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.exam_events
    ADD CONSTRAINT exam_events_pkey PRIMARY KEY (id);


--
-- Name: lti_contexts lti_contexts_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_contexts
    ADD CONSTRAINT lti_contexts_pkey PRIMARY KEY (id);


--
-- Name: lti_line_items lti_line_items_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_line_items
    ADD CONSTRAINT lti_line_items_pkey PRIMARY KEY (id);


--
-- Name: lti_nonces lti_nonces_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_nonces
    ADD CONSTRAINT lti_nonces_pkey PRIMARY KEY (nonce);


--
-- Name: lti_platforms lti_platforms_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_platforms
    ADD CONSTRAINT lti_platforms_pkey PRIMARY KEY (id);


--
-- Name: lti_registrations lti_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_registrations
    ADD CONSTRAINT lti_registrations_pkey PRIMARY KEY (token);


--
-- Name: lti_tool_keys lti_tool_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_tool_keys
    ADD CONSTRAINT lti_tool_keys_pkey PRIMARY KEY (kid);


--
-- Name: lti_users lti_users_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_users
    ADD CONSTRAINT lti_users_pkey PRIMARY KEY (id);


--
-- Name: material_files material_files_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.material_files
    ADD CONSTRAINT material_files_pkey PRIMARY KEY (material_id);


--
-- Name: reminder_log reminder_log_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.reminder_log
    ADD CONSTRAINT reminder_log_pkey PRIMARY KEY (id);


--
-- Name: session_steps session_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.session_steps
    ADD CONSTRAINT session_steps_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: step_attempts step_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.step_attempts
    ADD CONSTRAINT step_attempts_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_code_key; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_code_key UNIQUE (code);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: submission_files submission_files_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submission_files
    ADD CONSTRAINT submission_files_pkey PRIMARY KEY (submission_id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- Name: task_files task_files_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_files
    ADD CONSTRAINT task_files_pkey PRIMARY KEY (task_id);


--
-- Name: task_grades task_grades_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT task_grades_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (id);


--
-- Name: assignment_tasks uq_assignment_task; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_tasks
    ADD CONSTRAINT uq_assignment_task UNIQUE (assignment_id, task_id);


--
-- Name: assignment_attempts uq_attempt; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_attempts
    ADD CONSTRAINT uq_attempt UNIQUE (assignment_id, user_id);


--
-- Name: attendance uq_attendance; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT uq_attendance UNIQUE (assignment_id, user_id);


--
-- Name: course_members uq_course_member; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_members
    ADD CONSTRAINT uq_course_member UNIQUE (course_id, user_id);


--
-- Name: elective_choices uq_elective_choice; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_choices
    ADD CONSTRAINT uq_elective_choice UNIQUE (user_id, subject_id);


--
-- Name: lti_contexts uq_lti_context; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_contexts
    ADD CONSTRAINT uq_lti_context UNIQUE (platform_id, context_id);


--
-- Name: lti_line_items uq_lti_line_item; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_line_items
    ADD CONSTRAINT uq_lti_line_item UNIQUE (context_id, assignment_id);


--
-- Name: lti_platforms uq_lti_platform; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_platforms
    ADD CONSTRAINT uq_lti_platform UNIQUE (issuer, client_id);


--
-- Name: lti_users uq_lti_user; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_users
    ADD CONSTRAINT uq_lti_user UNIQUE (platform_id, sub);


--
-- Name: reminder_log uq_reminder; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.reminder_log
    ADD CONSTRAINT uq_reminder UNIQUE (assignment_id, user_id);


--
-- Name: subjects uq_subjects_finki_code; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT uq_subjects_finki_code UNIQUE (finki_code);


--
-- Name: task_grades uq_task_grade; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT uq_task_grade UNIQUE (assignment_id, task_id, user_id);


--
-- Name: user_ai_keys user_ai_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.user_ai_keys
    ADD CONSTRAINT user_ai_keys_pkey PRIMARY KEY (user_id);


--
-- Name: user_profiles user_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (user_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_assignments_course; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_assignments_course ON public.assignments USING btree (course_id);


--
-- Name: ix_code_comments_submission_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_code_comments_submission_id ON public.code_comments USING btree (submission_id);


--
-- Name: ix_course_materials_course_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_course_materials_course_id ON public.course_materials USING btree (course_id);


--
-- Name: ix_course_members_user; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_course_members_user ON public.course_members USING btree (user_id);


--
-- Name: ix_diagram_uploads_user_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_diagram_uploads_user_id ON public.diagram_uploads USING btree (user_id);


--
-- Name: ix_elective_choices_user_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_elective_choices_user_id ON public.elective_choices USING btree (user_id);


--
-- Name: ix_elective_requests_user_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_elective_requests_user_id ON public.elective_requests USING btree (user_id);


--
-- Name: ix_email_deliveries_email_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_email_deliveries_email_id ON public.email_deliveries USING btree (email_id);


--
-- Name: ix_email_deliveries_user_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_email_deliveries_user_id ON public.email_deliveries USING btree (user_id);


--
-- Name: ix_emails_course_id; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_emails_course_id ON public.emails USING btree (course_id);


--
-- Name: ix_events_course_created; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_events_course_created ON public.events USING btree (course_id, created_at);


--
-- Name: ix_events_created_at; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_events_created_at ON public.events USING btree (created_at);


--
-- Name: ix_events_kind_created; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_events_kind_created ON public.events USING btree (kind, created_at);


--
-- Name: ix_events_user_created; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_events_user_created ON public.events USING btree (user_id, created_at);


--
-- Name: ix_exam_events_lookup; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_exam_events_lookup ON public.exam_events USING btree (assignment_id, user_id, created_at);


--
-- Name: ix_lti_contexts_course; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_lti_contexts_course ON public.lti_contexts USING btree (course_id);


--
-- Name: ix_submissions_lookup; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_submissions_lookup ON public.submissions USING btree (assignment_id, user_id, task_id);


--
-- Name: ix_submissions_queue; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_submissions_queue ON public.submissions USING btree (status, submitted_at) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying])::text[]));


--
-- Name: ix_tasks_generated_for; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_tasks_generated_for ON public.tasks USING btree (generated_for);


--
-- Name: ix_tasks_subject; Type: INDEX; Schema: public; Owner: ale
--

CREATE INDEX ix_tasks_subject ON public.tasks USING btree (subject_id);


--
-- Name: ai_settings ai_settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.ai_settings
    ADD CONSTRAINT ai_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: assignment_attempts assignment_attempts_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_attempts
    ADD CONSTRAINT assignment_attempts_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: assignment_attempts assignment_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_attempts
    ADD CONSTRAINT assignment_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: assignment_tasks assignment_tasks_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_tasks
    ADD CONSTRAINT assignment_tasks_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: assignment_tasks assignment_tasks_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignment_tasks
    ADD CONSTRAINT assignment_tasks_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: assignments assignments_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: assignments assignments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: assignments assignments_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.course_groups(id) ON DELETE SET NULL;


--
-- Name: attendance attendance_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: attendance attendance_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: attendance attendance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: code_comments code_comments_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.code_comments
    ADD CONSTRAINT code_comments_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: code_comments code_comments_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.code_comments
    ADD CONSTRAINT code_comments_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id) ON DELETE CASCADE;


--
-- Name: course_groups course_groups_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_groups
    ADD CONSTRAINT course_groups_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_materials course_materials_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_materials
    ADD CONSTRAINT course_materials_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_materials course_materials_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_materials
    ADD CONSTRAINT course_materials_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: course_members course_members_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_members
    ADD CONSTRAINT course_members_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_members course_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_members
    ADD CONSTRAINT course_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.course_groups(id) ON DELETE SET NULL;


--
-- Name: course_members course_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.course_members
    ADD CONSTRAINT course_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: courses courses_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: courses courses_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE SET NULL;


--
-- Name: diagram_uploads diagram_uploads_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.diagram_uploads
    ADD CONSTRAINT diagram_uploads_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: diagram_uploads diagram_uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.diagram_uploads
    ADD CONSTRAINT diagram_uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: elective_choices elective_choices_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_choices
    ADD CONSTRAINT elective_choices_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: elective_choices elective_choices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_choices
    ADD CONSTRAINT elective_choices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: elective_plans elective_plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_plans
    ADD CONSTRAINT elective_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: elective_requests elective_requests_add_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_requests
    ADD CONSTRAINT elective_requests_add_subject_id_fkey FOREIGN KEY (add_subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: elective_requests elective_requests_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_requests
    ADD CONSTRAINT elective_requests_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: elective_requests elective_requests_remove_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_requests
    ADD CONSTRAINT elective_requests_remove_subject_id_fkey FOREIGN KEY (remove_subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: elective_requests elective_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.elective_requests
    ADD CONSTRAINT elective_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: email_deliveries email_deliveries_email_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.email_deliveries
    ADD CONSTRAINT email_deliveries_email_id_fkey FOREIGN KEY (email_id) REFERENCES public.emails(id) ON DELETE CASCADE;


--
-- Name: email_deliveries email_deliveries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.email_deliveries
    ADD CONSTRAINT email_deliveries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: emails emails_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: emails emails_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE SET NULL;


--
-- Name: emails emails_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: emails emails_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: emails emails_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.course_groups(id) ON DELETE SET NULL;


--
-- Name: exam_events exam_events_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.exam_events
    ADD CONSTRAINT exam_events_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: exam_events exam_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.exam_events
    ADD CONSTRAINT exam_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: lti_contexts lti_contexts_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_contexts
    ADD CONSTRAINT lti_contexts_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE SET NULL;


--
-- Name: lti_contexts lti_contexts_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_contexts
    ADD CONSTRAINT lti_contexts_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.lti_platforms(id) ON DELETE CASCADE;


--
-- Name: lti_line_items lti_line_items_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_line_items
    ADD CONSTRAINT lti_line_items_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: lti_line_items lti_line_items_context_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_line_items
    ADD CONSTRAINT lti_line_items_context_id_fkey FOREIGN KEY (context_id) REFERENCES public.lti_contexts(id) ON DELETE CASCADE;


--
-- Name: lti_registrations lti_registrations_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_registrations
    ADD CONSTRAINT lti_registrations_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: lti_registrations lti_registrations_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_registrations
    ADD CONSTRAINT lti_registrations_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.lti_platforms(id) ON DELETE SET NULL;


--
-- Name: lti_users lti_users_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_users
    ADD CONSTRAINT lti_users_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.lti_platforms(id) ON DELETE CASCADE;


--
-- Name: lti_users lti_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.lti_users
    ADD CONSTRAINT lti_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: material_files material_files_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.material_files
    ADD CONSTRAINT material_files_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.course_materials(id) ON DELETE CASCADE;


--
-- Name: reminder_log reminder_log_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.reminder_log
    ADD CONSTRAINT reminder_log_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: reminder_log reminder_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.reminder_log
    ADD CONSTRAINT reminder_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_steps session_steps_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.session_steps
    ADD CONSTRAINT session_steps_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: step_attempts step_attempts_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.step_attempts
    ADD CONSTRAINT step_attempts_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: step_attempts step_attempts_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.step_attempts
    ADD CONSTRAINT step_attempts_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.session_steps(id) ON DELETE CASCADE;


--
-- Name: submission_files submission_files_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submission_files
    ADD CONSTRAINT submission_files_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: task_files task_files_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_files
    ADD CONSTRAINT task_files_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_grades task_grades_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT task_grades_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: task_grades task_grades_graded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT task_grades_graded_by_fkey FOREIGN KEY (graded_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_grades task_grades_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT task_grades_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_grades task_grades_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.task_grades
    ADD CONSTRAINT task_grades_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: tasks tasks_generated_for_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_generated_for_fkey FOREIGN KEY (generated_for) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE SET NULL;


--
-- Name: test_cases test_cases_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: user_ai_keys user_ai_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.user_ai_keys
    ADD CONSTRAINT user_ai_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_profiles user_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ale
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict BhRvJ5xDyO7Sy5FQ2joBFEVSv2VJRdNehfLm26gQMiqPG7I94gQFc2YLwdJeh9I

