"""
Process sandbox for student code.

Every submission gets one *slot*. A slot is a numeric Linux user (10001, 10002, ...) that owns nothing
except the submission's own work directory. Everything the student code does (compiling included)
runs as that user, so it cannot:
  - read the runner's secret or source files of other submissions (directories are 0700, other owners),
  - kill or trace the runner (different uid, no capabilities),
  - leave processes behind (after every run all processes of the slot user are killed),
  - fork-bomb, eat all memory/disk or print gigabytes (per-process resource limits below).

The container adds the outer wall (docker-compose.yml): read-only filesystem, no internet,
all capabilities dropped except the few the runner needs to switch users, pids/memory/CPU limits.

The number of slots is the number of submissions that run at the same time; the rest wait in a queue.
When the runner is not root (local development) it still applies the limits but cannot switch users.
"""
import os
import queue
import resource
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

WORKERS = max(1, int(os.getenv("RUNNER_WORKERS", "4")))
QUEUE_TIMEOUT = float(os.getenv("RUNNER_QUEUE_TIMEOUT", "60"))  # seconds a submission may wait for a slot
BASE_UID = int(os.getenv("SANDBOX_BASE_UID", "10000"))
WORK_ROOT = os.getenv("RUNNER_WORK_ROOT", tempfile.gettempdir())

IS_ROOT = os.geteuid() == 0
SWITCH_USER = IS_ROOT and os.getenv("SANDBOX_SWITCH_USER", "1") != "0"

MB = 1024 * 1024
OUTPUT_LIMIT = 2 * MB  # max bytes a program may write (stdout + any file)
SANDBOX_PATH = os.getenv("SANDBOX_PATH", "/usr/local/bin:/usr/bin:/bin")  # where compilers / runtimes are


class RunnerBusy(Exception):
    """No free slot within QUEUE_TIMEOUT."""


@dataclass(frozen=True)
class Limits:
    cpu_seconds: int
    memory_bytes: int | None  # address-space limit; None for the JVM (it reserves huge virtual ranges)
    file_bytes: int
    processes: int = 64
    open_files: int = 256


COMPILE_LIMITS = Limits(cpu_seconds=30, memory_bytes=1024 * MB, file_bytes=64 * MB)
RUN_LIMITS = Limits(cpu_seconds=6, memory_bytes=512 * MB, file_bytes=OUTPUT_LIMIT)
JVM_COMPILE_LIMITS = Limits(cpu_seconds=30, memory_bytes=None, file_bytes=64 * MB)
JVM_RUN_LIMITS = Limits(cpu_seconds=6, memory_bytes=None, file_bytes=OUTPUT_LIMIT)


# ---------------------------------------------------------------------------
# Slots (the queue)
# ---------------------------------------------------------------------------

_free: "queue.Queue[int]" = queue.Queue()
for _i in range(1, WORKERS + 1):
    _free.put(BASE_UID + _i)
_waiting = 0
_lock = threading.Lock()


def stats() -> dict:
    return {"workers": WORKERS, "busy": WORKERS - _free.qsize(), "waiting": _waiting, "isolated": SWITCH_USER}


@dataclass
class Slot:
    uid: int
    workdir: str

    def new_dir(self, name: str) -> str:
        path = os.path.join(self.workdir, name)
        os.mkdir(path, 0o700)
        if SWITCH_USER:
            os.chown(path, self.uid, self.uid)
        return path


@contextmanager
def slot(wait: bool = True):
    """Wait for a free slot (FIFO-ish queue), give it a private work directory, clean everything up after.
    wait=False: only take a slot that is free right now and nobody is waiting for (editor checks must never
    delay submissions); otherwise RunnerBusy at once."""
    global _waiting
    if not wait:
        with _lock:
            if _waiting:
                raise RunnerBusy()
            try:
                uid = _free.get_nowait()
            except queue.Empty:
                raise RunnerBusy()
    else:
        with _lock:
            _waiting += 1
        try:
            uid = _free.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            raise RunnerBusy()
        finally:
            with _lock:
                _waiting -= 1
    workdir = tempfile.mkdtemp(prefix=f"sub-{uid}-", dir=WORK_ROOT)
    try:
        if SWITCH_USER:
            os.chown(workdir, uid, uid)
        yield Slot(uid=uid, workdir=workdir)
    finally:
        _kill_user(uid)
        shutil.rmtree(workdir, ignore_errors=True)
        _free.put(uid)


def _kill_user(uid: int) -> None:
    """Kill every process that runs as the slot user (catches anything that escaped its process group)."""
    if not SWITCH_USER:
        return
    for _ in range(5):
        found = False
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/status") as f:
                    uid_line = next(line for line in f if line.startswith("Uid:"))
                if int(uid_line.split()[1]) == uid:
                    found = True
                    os.kill(int(pid), signal.SIGKILL)
            except (OSError, StopIteration, ValueError):
                continue
        if not found:
            return
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Running one command
# ---------------------------------------------------------------------------

@dataclass
class Proc:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    output_limit: bool = False  # killed for writing too much (SIGXFSZ)


def _preexec(limits: Limits):
    def apply():
        os.setsid()  # own process group, so a timeout can kill children too
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
        if limits.memory_bytes:
            resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
        if SWITCH_USER:  # per-user limit; only meaningful for the slot user (root ignores it)
            resource.setrlimit(resource.RLIMIT_NPROC, (limits.processes, limits.processes))
    return apply


def _read(path: str, limit: int = OUTPUT_LIMIT) -> str:
    with open(path, "rb") as f:
        return f.read(limit).decode("utf-8", errors="replace")


def run(cmd: list[str], *, slot: Slot, cwd: str, limits: Limits, timeout: float, stdin: str = "",
        env_extra: dict[str, str] | None = None) -> Proc:
    """Run cmd as the slot user with the given limits. Output goes to files, so it can't flood memory."""
    out_path, err_path = os.path.join(cwd, ".stdout"), os.path.join(cwd, ".stderr")
    env = {
        "PATH": SANDBOX_PATH,
        "LANG": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": cwd,
        "TMPDIR": cwd,
        **(env_extra or {}),
    }
    extra = {"user": slot.uid, "group": slot.uid, "extra_groups": []} if SWITCH_USER else {}
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        if SWITCH_USER:
            os.fchown(out.fileno(), slot.uid, slot.uid)
            os.fchown(err.fileno(), slot.uid, slot.uid)
        p = subprocess.Popen(
            cmd, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=out, stderr=err,
            preexec_fn=_preexec(limits), close_fds=True, **extra,
        )
        timed_out = False
        try:
            p.communicate(input=stdin.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except BrokenPipeError:  # program exited without reading stdin
            pass
        finally:
            _kill_group(p.pid)
            if SWITCH_USER:
                _kill_user(slot.uid)
            p.wait()
    rc = p.returncode
    cpu_killed = rc == -signal.SIGXCPU  # CPU-time limit (busy loop) — same meaning as a timeout
    return Proc(
        returncode=rc,
        stdout=_read(out_path),
        stderr=_read(err_path, 64 * 1024),
        timed_out=timed_out or cpu_killed,
        output_limit=rc == -signal.SIGXFSZ,
    )


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
