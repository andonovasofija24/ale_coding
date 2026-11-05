"""
DevOps tasks for "Континуирана интеграција и испорака (DevOps)" (F23L3S118): Git, Bash, Dockerfile, YAML (GitHub
Actions, docker-compose, Kubernetes) and Terraform. The code runner checks them (code-runner/app/devops.py):
Git scripts run in a fresh folder and the tests inspect the repository; Dockerfile / YAML / Terraform files are
parsed and the tests are Python asserts with small helpers. Every task can also be used in other courses
(e.g. Инфраструктурно програмирање) — assignments take tasks from the whole bank.
"""

DEVOPS = "F23L3S118"


def t(code: str, out: str = "OK", hidden: bool = False) -> dict:
    return {"type": "code_sample", "test_code": code, "stdin": "", "expected_output": out, "is_hidden": hidden}


def io(stdin: str, out: str, hidden: bool = False) -> dict:
    return {"type": "stdin_stdout", "test_code": "", "stdin": stdin, "expected_output": out, "is_hidden": hidden}


DEVOPS_TASKS = [
    # ================================================================== Git
    {
        "title": "Git: прво складиште и commit",
        "language": "git",
        "description": """Напишете ги **git командите** што прават ново складиште.

1. Направете складиште во тековната папка.
2. Направете `README.md` со содржина `# ALE` и `.gitignore` со еден ред: `*.log`.
3. Направете датотека `debug.log` (содржината не е важна) — таа **не** смее да влезе во складиштето.
4. Направете **еден** commit со порака `Initial commit` во кој се `README.md` и `.gitignore`.

На крај работната папка треба да е „чиста“ (ништо неснимено, освен игнорираниот лог).
""",
        "translations": {"en": {"title": "Git: first repository and commit", "description": """Write the **git commands** that create a new repository.

1. Create a repository in the current folder.
2. Create `README.md` containing `# ALE` and `.gitignore` with one line: `*.log`.
3. Create a file `debug.log` (any content) — it must **not** get into the repository.
4. Make **one** commit with the message `Initial commit` containing `README.md` and `.gitignore`.

At the end the working tree must be clean (nothing unsaved, except the ignored log).
"""}},
        "starter_code": "# твоите git команди\ngit init\n",
        "model_solution": "git init\necho '# ALE' > README.md\necho '*.log' > .gitignore\necho 'debug' > debug.log\ngit add .\ngit commit -m 'Initial commit'\n",
        "tests": [
            t("git rev-list --count HEAD", "1"),
            t("git log -1 --format=%s", "Initial commit"),
            t("git ls-files | sort", ".gitignore\nREADME.md"),
            t("cat README.md; cat .gitignore", "# ALE\n*.log", hidden=True),
            t("git status --porcelain | wc -l; test -f debug.log && echo log-exists", "0\nlog-exists", hidden=True),
        ],
    },
    {
        "title": "Git: гранка за нова функционалност и merge",
        "language": "git",
        "description": """Работа со **гранки**.

1. Направете складиште со датотека `app.txt` (содржина `v1`) и commit `Start`.
2. Направете гранка **`feature/login`**, во неа датотека `login.txt` (содржина `login`) и commit `Add login`.
3. Вратете се на `main` и спојте ја гранката **со merge commit** (не fast-forward) со порака `Merge feature/login`.

На крај сте на `main`, гранката `feature/login` постои, а `login.txt` е на `main`.
""",
        "translations": {"en": {"title": "Git: a feature branch and a merge", "description": """Working with **branches**.

1. Create a repository with a file `app.txt` (content `v1`) and a commit `Start`.
2. Create a branch **`feature/login`**, add `login.txt` (content `login`) there and commit `Add login`.
3. Go back to `main` and merge the branch **with a merge commit** (not fast-forward) with the message `Merge feature/login`.

At the end you are on `main`, the branch `feature/login` exists and `login.txt` is on `main`.
"""}},
        "starter_code": "git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\n# продолжи…\n",
        "model_solution": "git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m Start\ngit switch -c feature/login\necho login > login.txt\ngit add login.txt\ngit commit -m 'Add login'\ngit switch main\ngit merge --no-ff feature/login -m 'Merge feature/login'\n",
        "tests": [
            t("git branch --show-current", "main"),
            t("git branch --list 'feature/login' | tr -d ' *'", "feature/login"),
            t("git log --merges --format=%s", "Merge feature/login"),
            t("cat login.txt; git rev-list --count HEAD", "login\n3", hidden=True),
            t("git log -1 --format=%s $(git rev-list --max-parents=0 HEAD)", "Start", hidden=True),
        ],
    },
    {
        "title": "Git: таг за издание и revert",
        "language": "git",
        "description": """Издание и поправка без бришење историја.

1. Складиште со `app.txt` = `v1`, commit `Release 1.0`.
2. **Анотиран** таг `v1.0` со порака `First release` на тој commit.
3. Сменете `app.txt` во `broken` и commit `Experiment`.
4. Експериментот не успеал: **поништете го со `git revert`** (не со `reset`), со стандардната порака.

На крај `app.txt` пак е `v1`, а во историјата има три commit-и.
""",
        "translations": {"en": {"title": "Git: a release tag and a revert", "description": """A release and a fix without rewriting history.

1. A repository with `app.txt` = `v1`, commit `Release 1.0`.
2. An **annotated** tag `v1.0` with the message `First release` on that commit.
3. Change `app.txt` to `broken` and commit `Experiment`.
4. The experiment failed: **undo it with `git revert`** (not `reset`), with the default message.

At the end `app.txt` is `v1` again and the history has three commits.
"""}},
        "starter_code": "git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m 'Release 1.0'\n",
        "model_solution": "git init\necho v1 > app.txt\ngit add app.txt\ngit commit -m 'Release 1.0'\ngit tag -a v1.0 -m 'First release'\necho broken > app.txt\ngit commit -am Experiment\ngit revert --no-edit HEAD\n",
        "tests": [
            t("cat app.txt", "v1"),
            t("git rev-list --count HEAD; git log -1 --format=%s", '3\nRevert "Experiment"'),
            t("git cat-file -t v1.0; git tag -l --format='%(contents:subject)' v1.0", "tag\nFirst release"),
            t("[ \"$(git rev-parse 'v1.0^{commit}')\" = \"$(git rev-list --max-parents=0 HEAD)\" ] && echo same", "same", hidden=True),
        ],
    },
    {
        "title": "Git: решавање конфликт при merge",
        "language": "git",
        "description": """Двајца ја менуваат истата линија — решете го **конфликтот**.

1. Складиште со `config.txt` = `port=8000`, commit `Base`.
2. Гранка `dev`: сменете во `port=9000`, commit `Dev port`.
3. На `main`: сменете во `port=8080`, commit `Main port`.
4. Спојте `dev` во `main` — ќе има конфликт. Решете го така што `config.txt` ќе содржи **само** `port=9000`,
   и завршете го merge-от со commit `Resolve port`.
""",
        "translations": {"en": {"title": "Git: resolving a merge conflict", "description": """Two people change the same line — resolve the **conflict**.

1. A repository with `config.txt` = `port=8000`, commit `Base`.
2. Branch `dev`: change it to `port=9000`, commit `Dev port`.
3. On `main`: change it to `port=8080`, commit `Main port`.
4. Merge `dev` into `main` — there will be a conflict. Resolve it so that `config.txt` contains **only** `port=9000`,
   and finish the merge with the commit `Resolve port`.
"""}},
        "starter_code": "git init\necho port=8000 > config.txt\ngit add config.txt\ngit commit -m Base\n",
        "model_solution": "git init\necho port=8000 > config.txt\ngit add config.txt\ngit commit -m Base\ngit switch -c dev\necho port=9000 > config.txt\ngit commit -am 'Dev port'\ngit switch main\necho port=8080 > config.txt\ngit commit -am 'Main port'\ngit merge dev || true\necho port=9000 > config.txt\ngit add config.txt\ngit commit -m 'Resolve port'\n",
        "tests": [
            t("cat config.txt", "port=9000"),
            t("git log -1 --format=%s; git log -1 --format=%p | wc -w", "Resolve port\n2"),
            t("grep -c '<<<<<<<' config.txt || true", "0", hidden=True),
            t("git status --porcelain | wc -l; git branch --show-current", "0\nmain", hidden=True),
        ],
    },
    # ================================================================== Bash
    {
        "title": "Bash: анализа на лог од веб-сервер",
        "language": "bash",
        "description": """Скрипта што чита **лог од веб-сервер** од стандарден влез. Секоја линија е:
`IP МЕТОД ПАТЕКА СТАТУС`, на пр. `10.0.0.1 GET /index.html 200`.

Испечатете три линии:
```
requests: <вкупно барања>
errors: <барања со статус 500 или повеќе>
top: <IP-адресата со најмногу барања>
```
(при еднаков број, помалата IP по абецеден ред). Празен влез: `requests: 0`, `errors: 0`, `top: -`.
""",
        "translations": {"en": {"title": "Bash: analysing a web server log", "description": """A script that reads a **web server log** from standard input. Each line is:
`IP METHOD PATH STATUS`, e.g. `10.0.0.1 GET /index.html 200`.

Print three lines:
```
requests: <total requests>
errors: <requests with status 500 or more>
top: <the IP with the most requests>
```
(on a tie, the alphabetically smaller IP). Empty input: `requests: 0`, `errors: 0`, `top: -`.
"""}},
        "starter_code": "#!/usr/bin/env bash\n# читај од stdin\n",
        "model_solution": "#!/usr/bin/env bash\nawk '\n  NF >= 4 { n++; if ($4 >= 500) e++; c[$1]++ }\n  END {\n    top = \"-\"; best = 0\n    for (ip in c) if (c[ip] > best || (c[ip] == best && ip < top)) { best = c[ip]; top = ip }\n    printf \"requests: %d\\nerrors: %d\\ntop: %s\\n\", n, e, top\n  }'\n",
        "tests": [
            io("10.0.0.1 GET / 200\n10.0.0.2 GET /a 500\n10.0.0.1 POST /login 302\n", "requests: 3\nerrors: 1\ntop: 10.0.0.1"),
            io("", "requests: 0\nerrors: 0\ntop: -"),
            io("10.0.0.9 GET / 503\n10.0.0.3 GET / 200\n10.0.0.9 GET / 504\n10.0.0.3 GET / 404\n", "requests: 4\nerrors: 2\ntop: 10.0.0.3", hidden=True),
            io("1.1.1.1 GET / 500\n", "requests: 1\nerrors: 1\ntop: 1.1.1.1", hidden=True),
        ],
    },
    {
        "title": "Bash: функција за health check",
        "language": "bash",
        "description": """Напишете функција **`health`** што добива HTTP статус-код и печати состојба на сервисот:
- `200`–`299` → `UP`
- `300`–`499` → `DEGRADED`
- `500` и повеќе, или нешто што не е број → `DOWN`

Потоа функција **`summary`** што добива повеќе кодови и печати колку се `UP`, `DEGRADED`, `DOWN`
во формат `UP=2 DEGRADED=1 DOWN=0`.
""",
        "translations": {"en": {"title": "Bash: a health-check function", "description": """Write a function **`health`** that gets an HTTP status code and prints the state of the service:
- `200`–`299` → `UP`
- `300`–`499` → `DEGRADED`
- `500` or more, or something that is not a number → `DOWN`

Then a function **`summary`** that gets several codes and prints how many are `UP`, `DEGRADED`, `DOWN`
in the form `UP=2 DEGRADED=1 DOWN=0`.
"""}},
        "starter_code": "health() {\n  :\n}\n\nsummary() {\n  :\n}\n",
        "model_solution": "health() {\n  local c=$1\n  if ! [[ $c =~ ^[0-9]+$ ]]; then echo DOWN; return; fi\n  if (( c >= 200 && c < 300 )); then echo UP\n  elif (( c >= 300 && c < 500 )); then echo DEGRADED\n  else echo DOWN; fi\n}\n\nsummary() {\n  local up=0 deg=0 down=0 s\n  for c in \"$@\"; do\n    s=$(health \"$c\")\n    case $s in UP) ((up++)) ;; DEGRADED) ((deg++)) ;; *) ((down++)) ;; esac\n  done\n  echo \"UP=$up DEGRADED=$deg DOWN=$down\"\n}\n",
        "tests": [
            t("health 200; health 404; health 503", "UP\nDEGRADED\nDOWN"),
            t("health abc; health 301", "DOWN\nDEGRADED"),
            t("summary 200 201 404", "UP=2 DEGRADED=1 DOWN=0"),
            t("summary 500 x 299 300", "UP=1 DEGRADED=1 DOWN=2", hidden=True),
            t("summary", "UP=0 DEGRADED=0 DOWN=0", hidden=True),
        ],
    },
    # ================================================================== Dockerfile
    {
        "title": "Dockerfile за Python веб-апликација",
        "language": "dockerfile",
        "description": """Напишете **Dockerfile** за Flask апликација (`app.py`, зависности во `requirements.txt`).

- основна слика **`python:3.12-slim`**, работна папка `/app`;
- прво копирајте **само** `requirements.txt` и инсталирајте ги зависностите со `pip install --no-cache-dir`,
  па дури потоа копирајте го остатокот од кодот (за подобар кеш на слоевите);
- апликацијата **не** работи како `root`: направете корисник `app` и префрлете се на него;
- `EXPOSE 8000`;
- стартувајте со **gunicorn** во JSON форма: `["gunicorn", "-b", "0.0.0.0:8000", "app:app"]`.
""",
        "translations": {"en": {"title": "Dockerfile for a Python web app", "description": """Write a **Dockerfile** for a Flask app (`app.py`, dependencies in `requirements.txt`).

- base image **`python:3.12-slim`**, working directory `/app`;
- first copy **only** `requirements.txt` and install the dependencies with `pip install --no-cache-dir`,
  and only then copy the rest of the code (better layer caching);
- the app does **not** run as `root`: create a user `app` and switch to it;
- `EXPOSE 8000`;
- start with **gunicorn** in JSON form: `["gunicorn", "-b", "0.0.0.0:8000", "app:app"]`.
"""}},
        "starter_code": "FROM python:3.12-slim\n\n# …\n",
        "model_solution": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nRUN useradd --create-home app\nUSER app\nEXPOSE 8000\nCMD [\"gunicorn\", \"-b\", \"0.0.0.0:8000\", \"app:app\"]\n",
        "tests": [
            t("assert stages() == ['python:3.12-slim'], 'base image: python:3.12-slim'\nassert workdir() == '/app', 'WORKDIR /app'"),
            t("c = copies()\nassert c and c[0][0] == 'requirements.txt', 'copy requirements.txt first'\n"
              "assert any(s == '.' for s, _ in c[1:]), 'then copy the rest of the code'\n"
              "assert has('RUN', '--no-cache-dir'), 'pip install --no-cache-dir'"),
            t("assert user() not in (None, 'root', '0'), 'switch to a non-root user'\nassert '8000' in exposed(), 'EXPOSE 8000'"),
            t("assert last('CMD').strip().startswith('['), 'CMD in JSON form'\nassert cmd() == ['gunicorn', '-b', '0.0.0.0:8000', 'app:app']", hidden=True),
            t("order = [w for w, _ in D]\nassert order.index('USER') > max(i for i, w in enumerate(order) if w == 'RUN'), 'USER after the RUN steps'", hidden=True),
        ],
    },
    {
        "title": "Повеќестепен Dockerfile за фронтенд",
        "language": "dockerfile",
        "description": """**Multi-stage build** за React/Vite фронтенд: се гради во Node, а се служи со nginx.

1. Прв степен со име **`build`**: `node:22-alpine`, `WORKDIR /app`, копирајте `package.json` и
   `package-lock.json`, `npm ci` (не `npm install`), копирајте го кодот, `npm run build`.
2. Втор степен: **`nginx:1.27-alpine`**; копирајте **од степенот `build`** папката `/app/dist` во
   `/usr/share/nginx/html`; `EXPOSE 80`.

Во конечната слика нема Node — само статичните датотеки и nginx.
""",
        "translations": {"en": {"title": "Multi-stage Dockerfile for a front end", "description": """A **multi-stage build** for a React/Vite front end: built in Node, served by nginx.

1. First stage named **`build`**: `node:22-alpine`, `WORKDIR /app`, copy `package.json` and `package-lock.json`,
   `npm ci` (not `npm install`), copy the code, `npm run build`.
2. Second stage: **`nginx:1.27-alpine`**; copy **from the `build` stage** the folder `/app/dist` to
   `/usr/share/nginx/html`; `EXPOSE 80`.

The final image has no Node — only the static files and nginx.
"""}},
        "starter_code": "FROM node:22-alpine\nWORKDIR /app\n",
        "model_solution": "FROM node:22-alpine AS build\nWORKDIR /app\nCOPY package.json package-lock.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\n\nFROM nginx:1.27-alpine\nCOPY --from=build /app/dist /usr/share/nginx/html\nEXPOSE 80\n",
        "tests": [
            t("assert len(stages()) == 2, 'two stages (two FROM lines)'\nassert instr('FROM')[0].lower().split()[-1] == 'build', 'name the first stage: AS build'"),
            t("assert has('RUN', 'npm ci'), 'npm ci'\nassert not has('RUN', 'npm install'), 'npm ci, not npm install'\nassert has('RUN', 'npm run build')"),
            t("assert stages()[-1] == 'nginx:1.27-alpine', 'final image: nginx:1.27-alpine'\n"
              "assert any('--from=build' in a and '/app/dist' in a and '/usr/share/nginx/html' in a for a in instr('COPY')), 'COPY --from=build /app/dist /usr/share/nginx/html'"),
            t("assert exposed() == ['80'], 'EXPOSE 80'", hidden=True),
        ],
    },
    # ================================================================== YAML
    {
        "title": "GitHub Actions: CI за Python проект",
        "language": "yaml",
        "description": """Напишете **GitHub Actions workflow** (`.github/workflows/ci.yml`) со име `CI`.

- се стартува при **push** и **pull_request** на гранката `main`;
- job **`test`** на `ubuntu-latest`;
- чекори: `actions/checkout@v4`; `actions/setup-python@v5` со `python-version: "3.12"`;
  `pip install -r requirements.txt`; `pytest`.
""",
        "translations": {"en": {"title": "GitHub Actions: CI for a Python project", "description": """Write a **GitHub Actions workflow** (`.github/workflows/ci.yml`) named `CI`.

- it runs on **push** and **pull_request** to the branch `main`;
- a job **`test`** on `ubuntu-latest`;
- steps: `actions/checkout@v4`; `actions/setup-python@v5` with `python-version: "3.12"`;
  `pip install -r requirements.txt`; `pytest`.
"""}},
        "starter_code": "name: CI\n\n",
        "model_solution": "name: CI\non:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"\n      - run: pip install -r requirements.txt\n      - run: pytest\n",
        "tests": [
            t("assert y.get('name') == 'CI'\non = get(y, 'on')\nassert isinstance(on, dict) and set(on) >= {'push', 'pull_request'}, 'on: push and pull_request'\n"
              "assert 'main' in get(on, 'push.branches', []) and 'main' in get(on, 'pull_request.branches', []), 'only the main branch'"),
            t("assert get(y, 'jobs.test.runs-on') == 'ubuntu-latest', 'job test on ubuntu-latest'"),
            t("uses = find(y, 'uses')\nassert 'actions/checkout@v4' in uses and 'actions/setup-python@v5' in uses\n"
              "assert str(find(y, 'python-version')[0]) == '3.12', 'python-version \"3.12\" (in quotes!)'"),
            t("runs = ' | '.join(find(y, 'run'))\nassert 'pip install -r requirements.txt' in runs and 'pytest' in runs\n"
              "steps = get(y, 'jobs.test.steps')\nassert steps[0].get('uses') == 'actions/checkout@v4', 'checkout first'", hidden=True),
        ],
    },
    {
        "title": "docker-compose: апликација и база",
        "language": "yaml",
        "description": """Напишете **`docker-compose.yml`** за веб-апликација и PostgreSQL.

- сервис **`web`**: се гради од тековната папка (`build: .`), порта `8000:8000`, зависи од `db`,
  околина `DATABASE_URL=postgresql://app:secret@db:5432/app`;
- сервис **`db`**: слика `postgres:16`, околина `POSTGRES_USER=app`, `POSTGRES_PASSWORD=secret`, `POSTGRES_DB=app`,
  податоците во именуван волумен **`db-data`** монтиран на `/var/lib/postgresql/data`;
- волуменот `db-data` е деклариран на дното на датотеката.
""",
        "translations": {"en": {"title": "docker-compose: an app and a database", "description": """Write a **`docker-compose.yml`** for a web app and PostgreSQL.

- service **`web`**: built from the current folder (`build: .`), port `8000:8000`, depends on `db`,
  environment `DATABASE_URL=postgresql://app:secret@db:5432/app`;
- service **`db`**: image `postgres:16`, environment `POSTGRES_USER=app`, `POSTGRES_PASSWORD=secret`, `POSTGRES_DB=app`,
  its data in a named volume **`db-data`** mounted at `/var/lib/postgresql/data`;
- the volume `db-data` is declared at the bottom of the file.
"""}},
        "starter_code": "services:\n  web:\n    build: .\n",
        "model_solution": "services:\n  web:\n    build: .\n    ports:\n      - \"8000:8000\"\n    depends_on:\n      - db\n    environment:\n      DATABASE_URL: postgresql://app:secret@db:5432/app\n  db:\n    image: postgres:16\n    environment:\n      POSTGRES_USER: app\n      POSTGRES_PASSWORD: secret\n      POSTGRES_DB: app\n    volumes:\n      - db-data:/var/lib/postgresql/data\nvolumes:\n  db-data:\n",
        "tests": [
            t("w = get(y, 'services.web')\nassert w and w.get('build') == '.', 'web: build: .'\nassert '8000:8000' in [str(p) for p in w.get('ports', [])], 'web: port 8000:8000'"),
            t("dep = get(y, 'services.web.depends_on')\nassert dep and 'db' in dep, 'web depends on db'\n"
              "env = get(y, 'services.web.environment')\nenv = env if isinstance(env, dict) else dict(e.split('=', 1) for e in env)\n"
              "assert env.get('DATABASE_URL') == 'postgresql://app:secret@db:5432/app'"),
            t("db = get(y, 'services.db')\nassert db and db.get('image') == 'postgres:16'\n"
              "env = db.get('environment') or {}\nenv = env if isinstance(env, dict) else dict(e.split('=', 1) for e in env)\n"
              "assert env.get('POSTGRES_USER') == 'app' and env.get('POSTGRES_PASSWORD') == 'secret' and env.get('POSTGRES_DB') == 'app'"),
            t("assert 'db-data:/var/lib/postgresql/data' in get(y, 'services.db.volumes', []), 'mount db-data'\nassert 'db-data' in (y.get('volumes') or {}), 'declare the volume db-data'", hidden=True),
        ],
    },
    {
        "title": "Kubernetes: Deployment и Service",
        "language": "yaml",
        "description": """Два Kubernetes објекти во **една** датотека (одделени со `---`).

**Deployment** `ale-web`:
- `replicas: 3`, селектор и ознака на подовите `app: ale-web`;
- контејнер `web` со слика `ghcr.io/finki/ale-web:1.0`, `containerPort: 8000`;
- ресурси: `requests` `cpu: 100m`, `memory: 128Mi`; `limits` `memory: 256Mi`;
- `readinessProbe` со `httpGet` на патеката `/health`, порта `8000`.

**Service** `ale-web`: тип `ClusterIP`, порта `80` → `targetPort: 8000`, селектор `app: ale-web`.
""",
        "translations": {"en": {"title": "Kubernetes: a Deployment and a Service", "description": """Two Kubernetes objects in **one** file (separated by `---`).

**Deployment** `ale-web`:
- `replicas: 3`, selector and pod label `app: ale-web`;
- a container `web` with the image `ghcr.io/finki/ale-web:1.0`, `containerPort: 8000`;
- resources: `requests` `cpu: 100m`, `memory: 128Mi`; `limits` `memory: 256Mi`;
- a `readinessProbe` with `httpGet` on the path `/health`, port `8000`.

**Service** `ale-web`: type `ClusterIP`, port `80` → `targetPort: 8000`, selector `app: ale-web`.
"""}},
        "starter_code": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: ale-web\n",
        "model_solution": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: ale-web\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: ale-web\n  template:\n    metadata:\n      labels:\n        app: ale-web\n    spec:\n      containers:\n        - name: web\n          image: ghcr.io/finki/ale-web:1.0\n          ports:\n            - containerPort: 8000\n          resources:\n            requests:\n              cpu: 100m\n              memory: 128Mi\n            limits:\n              memory: 256Mi\n          readinessProbe:\n            httpGet:\n              path: /health\n              port: 8000\n---\napiVersion: v1\nkind: Service\nmetadata:\n  name: ale-web\nspec:\n  type: ClusterIP\n  selector:\n    app: ale-web\n  ports:\n    - port: 80\n      targetPort: 8000\n",
        "tests": [
            t("kinds = {d.get('kind'): d for d in docs}\nassert set(kinds) >= {'Deployment', 'Service'}, 'a Deployment and a Service'\n"
              "d = kinds['Deployment']\nassert get(d, 'metadata.name') == 'ale-web' and get(d, 'spec.replicas') == 3"),
            t("d = next(x for x in docs if x.get('kind') == 'Deployment')\n"
              "assert get(d, 'spec.selector.matchLabels.app') == 'ale-web' and get(d, 'spec.template.metadata.labels.app') == 'ale-web', 'labels app: ale-web'\n"
              "c = get(d, 'spec.template.spec.containers.0')\nassert c['image'] == 'ghcr.io/finki/ale-web:1.0' and get(c, 'ports.0.containerPort') == 8000"),
            t("d = next(x for x in docs if x.get('kind') == 'Deployment')\nc = get(d, 'spec.template.spec.containers.0')\n"
              "assert get(c, 'resources.limits.memory') == '256Mi' and get(c, 'resources.requests.cpu') == '100m'\n"
              "assert get(c, 'readinessProbe.httpGet.path') == '/health'", hidden=True),
            t("s = next(x for x in docs if x.get('kind') == 'Service')\nassert get(s, 'spec.type', 'ClusterIP') == 'ClusterIP'\n"
              "assert get(s, 'spec.ports.0.port') == 80 and get(s, 'spec.ports.0.targetPort') == 8000 and get(s, 'spec.selector.app') == 'ale-web'"),
        ],
    },
    # ================================================================== Terraform
    {
        "title": "Terraform: S3 bucket со верзии",
        "language": "terraform",
        "description": """Infrastructure as code: **S3 bucket** за логови во AWS.

- провајдер `aws` во регионот од променливата **`region`** (тип `string`, стандардно `eu-central-1`);
- променлива **`bucket_name`** (тип `string`, без стандардна вредност);
- ресурс `aws_s3_bucket` со име **`logs`** чие име е `var.bucket_name` и ознака (tag) `Env = "dev"`;
- ресурс `aws_s3_bucket_versioning` **`logs`** за тој bucket (`aws_s3_bucket.logs.id`) со
  `versioning_configuration { status = "Enabled" }`;
- излез **`bucket_arn`** = ARN на bucket-от.
""",
        "translations": {"en": {"title": "Terraform: an S3 bucket with versioning", "description": """Infrastructure as code: an **S3 bucket** for logs in AWS.

- provider `aws` in the region from the variable **`region`** (type `string`, default `eu-central-1`);
- a variable **`bucket_name`** (type `string`, no default);
- a resource `aws_s3_bucket` named **`logs`** whose name is `var.bucket_name` and a tag `Env = "dev"`;
- a resource `aws_s3_bucket_versioning` **`logs`** for that bucket (`aws_s3_bucket.logs.id`) with
  `versioning_configuration { status = "Enabled" }`;
- an output **`bucket_arn`** = the bucket's ARN.
"""}},
        "starter_code": "provider \"aws\" {\n  region = \"eu-central-1\"\n}\n",
        "model_solution": "variable \"region\" {\n  type    = string\n  default = \"eu-central-1\"\n}\n\nvariable \"bucket_name\" {\n  type = string\n}\n\nprovider \"aws\" {\n  region = var.region\n}\n\nresource \"aws_s3_bucket\" \"logs\" {\n  bucket = var.bucket_name\n  tags = {\n    Env = \"dev\"\n  }\n}\n\nresource \"aws_s3_bucket_versioning\" \"logs\" {\n  bucket = aws_s3_bucket.logs.id\n  versioning_configuration {\n    status = \"Enabled\"\n  }\n}\n\noutput \"bucket_arn\" {\n  value = aws_s3_bucket.logs.arn\n}\n",
        "tests": [
            t("r = variable('region')\nassert ref(r.get('type')) == 'string' and r.get('default') == 'eu-central-1'\n"
              "b = variable('bucket_name')\nassert 'default' not in b, 'bucket_name has no default'\nassert ref(provider('aws').get('region')) == 'var.region', 'provider region = var.region'"),
            t("b = resource('aws_s3_bucket', 'logs')\nassert ref(b.get('bucket')) == 'var.bucket_name', 'bucket = var.bucket_name'\nassert (b.get('tags') or {}).get('Env') == 'dev', 'tag Env = \"dev\"'"),
            t("v = resource('aws_s3_bucket_versioning', 'logs')\nassert ref(v.get('bucket')) == 'aws_s3_bucket.logs.id'\nassert block(v, 'versioning_configuration').get('status') == 'Enabled'"),
            t("assert ref(output('bucket_arn').get('value')) == 'aws_s3_bucket.logs.arn'", hidden=True),
        ],
    },
    {
        "title": "Terraform: EC2 инстанца со security group",
        "language": "terraform",
        "description": """Веб-сервер во AWS.

- променлива **`admin_cidr`** (тип `string`) — од каде е дозволен SSH;
- `aws_security_group` **`web`** со два `ingress` блока: порта **22** (tcp) само од `var.admin_cidr`
  и порта **80** (tcp) од `0.0.0.0/0`; и `egress` кон сè (`protocol = "-1"`, `0.0.0.0/0`);
- `aws_instance` **`web`**: `ami = var.ami_id` (направете и таа променлива), `instance_type = "t3.micro"`,
  `vpc_security_group_ids = [aws_security_group.web.id]`, ознака `Name = "ale-web"`;
- излез **`public_ip`** = јавната IP-адреса на инстанцата.
""",
        "translations": {"en": {"title": "Terraform: an EC2 instance with a security group", "description": """A web server in AWS.

- a variable **`admin_cidr`** (type `string`) — where SSH is allowed from;
- `aws_security_group` **`web`** with two `ingress` blocks: port **22** (tcp) only from `var.admin_cidr`
  and port **80** (tcp) from `0.0.0.0/0`; and `egress` to everything (`protocol = "-1"`, `0.0.0.0/0`);
- `aws_instance` **`web`**: `ami = var.ami_id` (create that variable too), `instance_type = "t3.micro"`,
  `vpc_security_group_ids = [aws_security_group.web.id]`, tag `Name = "ale-web"`;
- an output **`public_ip`** = the instance's public IP.
"""}},
        "starter_code": "resource \"aws_instance\" \"web\" {\n}\n",
        "model_solution": "variable \"admin_cidr\" {\n  type = string\n}\n\nvariable \"ami_id\" {\n  type = string\n}\n\nresource \"aws_security_group\" \"web\" {\n  name = \"ale-web\"\n\n  ingress {\n    from_port   = 22\n    to_port     = 22\n    protocol    = \"tcp\"\n    cidr_blocks = [var.admin_cidr]\n  }\n\n  ingress {\n    from_port   = 80\n    to_port     = 80\n    protocol    = \"tcp\"\n    cidr_blocks = [\"0.0.0.0/0\"]\n  }\n\n  egress {\n    from_port   = 0\n    to_port     = 0\n    protocol    = \"-1\"\n    cidr_blocks = [\"0.0.0.0/0\"]\n  }\n}\n\nresource \"aws_instance\" \"web\" {\n  ami                    = var.ami_id\n  instance_type          = \"t3.micro\"\n  vpc_security_group_ids = [aws_security_group.web.id]\n  tags = {\n    Name = \"ale-web\"\n  }\n}\n\noutput \"public_ip\" {\n  value = aws_instance.web.public_ip\n}\n",
        "tests": [
            t("sg = resource('aws_security_group', 'web')\nrules = {int(r['from_port']): r for r in sg.get('ingress', [])}\nassert set(rules) == {22, 80}, 'ingress on ports 22 and 80'\n"
              "assert [ref(c) for c in rules[22]['cidr_blocks']] == ['var.admin_cidr'], 'SSH only from var.admin_cidr'\nassert rules[80]['cidr_blocks'] == ['0.0.0.0/0']"),
            t("sg = resource('aws_security_group', 'web')\neg = sg.get('egress', [])\nassert eg and str(eg[0]['protocol']) == '-1', 'egress to everything'"),
            t("i = resource('aws_instance', 'web')\nassert ref(i['ami']) == 'var.ami_id' and i['instance_type'] == 't3.micro'\n"
              "assert [ref(x) for x in i['vpc_security_group_ids']] == ['aws_security_group.web.id']\nassert i.get('tags', {}).get('Name') == 'ale-web'"),
            t("variable('admin_cidr'); variable('ami_id')\nassert ref(output('public_ip')['value']) == 'aws_instance.web.public_ip'", hidden=True),
        ],
    },
    {
        "title": "Terraform: модул за мрежа и заеднички ознаки",
        "language": "terraform",
        "description": """Користење **модул** од Terraform Registry и `locals`.

- `locals` со **`common_tags`** = `{ Project = "ale", Owner = "finki" }`;
- модул **`vpc`** од `terraform-aws-modules/vpc/aws`, верзија `~> 5.0`, со `name = "ale"`,
  `cidr = "10.0.0.0/16"`, `azs = ["eu-central-1a", "eu-central-1b"]`,
  `public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]` и `tags = local.common_tags`;
- излез **`vpc_id`** = `module.vpc.vpc_id`.
""",
        "translations": {"en": {"title": "Terraform: a network module and shared tags", "description": """Using a **module** from the Terraform Registry and `locals`.

- `locals` with **`common_tags`** = `{ Project = "ale", Owner = "finki" }`;
- a module **`vpc`** from `terraform-aws-modules/vpc/aws`, version `~> 5.0`, with `name = "ale"`,
  `cidr = "10.0.0.0/16"`, `azs = ["eu-central-1a", "eu-central-1b"]`,
  `public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]` and `tags = local.common_tags`;
- an output **`vpc_id`** = `module.vpc.vpc_id`.
"""}},
        "starter_code": "locals {\n}\n",
        "model_solution": "locals {\n  common_tags = {\n    Project = \"ale\"\n    Owner   = \"finki\"\n  }\n}\n\nmodule \"vpc\" {\n  source  = \"terraform-aws-modules/vpc/aws\"\n  version = \"~> 5.0\"\n\n  name           = \"ale\"\n  cidr           = \"10.0.0.0/16\"\n  azs            = [\"eu-central-1a\", \"eu-central-1b\"]\n  public_subnets = [\"10.0.1.0/24\", \"10.0.2.0/24\"]\n  tags           = local.common_tags\n}\n\noutput \"vpc_id\" {\n  value = module.vpc.vpc_id\n}\n",
        "tests": [
            t("assert locals_().get('common_tags') == {'Project': 'ale', 'Owner': 'finki'}, 'common_tags'"),
            t("m = module('vpc')\nassert m['source'] == 'terraform-aws-modules/vpc/aws' and m['version'] == '~> 5.0'\nassert m['cidr'] == '10.0.0.0/16' and m['name'] == 'ale'"),
            t("m = module('vpc')\nassert m['azs'] == ['eu-central-1a', 'eu-central-1b']\nassert m['public_subnets'] == ['10.0.1.0/24', '10.0.2.0/24']\nassert ref(m['tags']) == 'local.common_tags'", hidden=True),
            t("assert ref(output('vpc_id')['value']) == 'module.vpc.vpc_id'"),
        ],
    },
]
