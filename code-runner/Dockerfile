# ---- Toolchains that are not (or not recent enough) in Debian, taken from their official images ----

# Node.js 22 (JavaScript) + the TypeScript compiler and Node's type definitions
FROM node:22-bookworm-slim AS node
RUN npm install --prefix /opt/ts --no-audit --no-fund typescript@5.6.3 @types/node@22.9.0

# Kotlin compiler (runs on the JDK installed below)
FROM debian:bookworm-slim AS kotlin
ARG KOTLIN_VERSION=2.1.20
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && curl -fsSL -o /tmp/kotlin.zip \
       "https://github.com/JetBrains/kotlin/releases/download/v${KOTLIN_VERSION}/kotlin-compiler-${KOTLIN_VERSION}.zip" \
    && unzip -q /tmp/kotlin.zip -d /opt && rm /tmp/kotlin.zip

# .NET 8 for C#: only what the runner needs — the runtime, the reference assemblies and the Roslyn compiler
# (the full SDK is ~3x bigger)
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS dotnet
RUN mkdir -p /out/sdk/current \
    && cp -r /usr/share/dotnet/sdk/*/Roslyn /out/sdk/current/ \
    && cp -r /usr/share/dotnet/dotnet /usr/share/dotnet/host /usr/share/dotnet/shared /usr/share/dotnet/packs /out/

# ---- The code runner ----
FROM python:3.12-slim

# gcc/g++ (C, C++), JDK (Java, Kotlin), PHP, SWI-Prolog, SBCL (Common Lisp), NASM (x86-64 assembly), git (DevOps).
# Python 3 comes with the base image; SQL tasks use Python's built-in SQLite; PostgreSQL tasks use the
# separate sql-sandbox service. (The man1 folder is missing on slim images and the JDK install needs it.)
RUN mkdir -p /usr/share/man/man1 && apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-jdk-headless \
    php-cli \
    swi-prolog-nox \
    sbcl \
    nasm \
    git \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /opt/ts /opt/ts
COPY --from=kotlin /opt/kotlinc /opt/kotlinc
COPY --from=dotnet /out /usr/share/dotnet

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# HTML/CSS/JS tasks are tested in headless Chromium (Playwright); only the small "headless shell" build is installed,
# readable by the sandbox users.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps --only-shell chromium \
    && chmod -R a+rX /ms-playwright && rm -rf /var/lib/apt/lists/*

COPY app/ ./app/
RUN python -m compileall -q app  # the container filesystem is read-only at run time

# Sandbox (see app/sandbox.py): the server starts as root only so it can switch every submission to its own
# unprivileged user; docker-compose.yml drops all other capabilities, makes the filesystem read-only,
# keeps the container off the internet and limits processes / memory / CPU.
ENV RUNNER_WORKERS=4 \
    RUNNER_QUEUE_TIMEOUT=60 \
    RUNNER_WORK_ROOT=/sandbox \
    PYTHONDONTWRITEBYTECODE=1 \
    SANDBOX_PATH=/opt/kotlinc/bin:/usr/local/bin:/usr/bin:/bin \
    TS_HOME=/opt/ts \
    WEB_PYTHON=/usr/local/bin/python \
    DOTNET_ROOT=/usr/share/dotnet

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
