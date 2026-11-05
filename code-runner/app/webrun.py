"""
Runs the tests of one HTML/CSS/JS submission in headless Chromium. Started by app/web.py as the sandbox user:

    python -m app.webrun <job.json>

job.json: {"dir": ..., "has_reference": bool, "tests": [{"code": ..., "expected": ...}]}
The student's files are in <dir>/student, the model solution's in <dir>/reference.
Prints one JSON line: a list of {passed, actual_output, expected_output, error, images}.
"""
import asyncio
import base64
import io
import json
import re
import sys

from playwright.async_api import async_playwright

DEFAULT_VIEWPORT = (1280, 800)
LOAD_TIMEOUT = 6.0   # seconds to load the page
TEST_TIMEOUT = 5.0   # seconds for one test's code
TOLERANCE = 40       # colour difference (0..255) still counted as "the same pixel"
SHOT_WIDTH = 560     # width of the screenshots sent back for display

ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions", "--mute-audio",
        "--no-first-run", "--disable-background-networking", "--disable-component-update", "--disable-sync",
        "--font-render-hinting=none", "--force-color-profile=srgb", "--hide-scrollbars"]

# The test's code runs as the body of an async function with these helpers as parameters.
RUN_TEST = r"""
async (code) => {
  const out = [];
  const fmt = (v) => typeof v === 'string' ? v : (v === undefined ? 'undefined' : JSON.stringify(v));
  const print = (...a) => { out.push(a.map(fmt).join(' ')); };
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const exists = (s) => !!$(s);
  const count = (s) => $$(s).length;
  const text = (s) => { const e = $(s); return e ? e.textContent.replace(/\s+/g, ' ').trim() : null; };
  const attr = (s, a) => { const e = $(s); return e ? e.getAttribute(a) : null; };
  const css = (s, p) => { const e = $(s); return e ? getComputedStyle(e).getPropertyValue(p).trim() : null; };
  const hex = (s, p) => {
    const v = css(s, p); const m = v && v.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m ? '#' + [m[1], m[2], m[3]].map((x) => (+x).toString(16).padStart(2, '0')).join('') : v;
  };
  const visible = (s) => {
    const e = $(s); if (!e) return false;
    const r = e.getBoundingClientRect(); const st = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none' && +st.opacity > 0;
  };
  const rect = (s) => { const e = $(s); if (!e) return null; const r = e.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) }; };
  const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));
  const click = async (s) => { const e = $(s); if (!e) throw new Error('No element ' + s); e.click(); await sleep(60); };
  const type = async (s, v) => {
    const e = $(s); if (!e) throw new Error('No element ' + s);
    e.focus(); e.value = v;
    e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true }));
    await sleep(60);
  };
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  try {
    const fn = new AsyncFunction('print', '$', '$$', 'exists', 'count', 'text', 'attr', 'css', 'hex', 'visible', 'rect',
                                 'sleep', 'click', 'type', code);
    await fn(print, $, $$, exists, count, text, attr, css, hex, visible, rect, sleep, click, type);
    return { out: out.join('\n') };
  } catch (e) {
    return { out: out.join('\n'), error: (e && e.message) ? e.message : String(e) };
  }
}
"""


def normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in (s or "").splitlines()).strip()


def directives(code: str) -> tuple[tuple[int, int], int | None]:
    viewport, visual = DEFAULT_VIEWPORT, None
    m = re.search(r"^\s*//\s*viewport\s*:\s*(\d{2,4})\s*[x×]\s*(\d{2,4})", code, re.M | re.I)
    if m:
        viewport = (max(200, min(int(m.group(1)), 2560)), max(200, min(int(m.group(2)), 2000)))
    m = re.search(r"^\s*//\s*visual\s*:\s*(\d{1,3})", code, re.M | re.I)
    if m:
        visual = max(1, min(int(m.group(1)), 100))
    return viewport, visual


class Browser:
    def __init__(self, pw):
        self.pw, self.browser = pw, None

    async def get(self):
        if self.browser is None or not self.browser.is_connected():
            self.browser = await self.pw.chromium.launch(args=ARGS, timeout=20_000)
        return self.browser

    async def reset(self):
        try:
            if self.browser:
                await asyncio.wait_for(self.browser.close(), 3)
        except Exception:
            pass
        self.browser = None


async def open_page(browser: Browser, folder: str, viewport):
    """A fresh page with the files of `folder` loaded; nothing outside the folder can be fetched."""
    b = await browser.get()
    ctx = await b.new_context(viewport={"width": viewport[0], "height": viewport[1]}, bypass_csp=True,
                              device_scale_factor=1, locale="mk-MK", reduced_motion="reduce")
    errors: list[str] = []

    allowed = f"file://{folder}/"

    async def only_local(route):  # only this page's own files (not the model solution, not the rest of the disk)
        url = route.request.url
        if url.startswith(allowed) and "/../" not in url and "%2e" not in url.lower():
            await route.continue_()
        else:
            await route.abort()
    await ctx.route("**/*", only_local)
    page = await ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))
    await asyncio.wait_for(page.goto(f"file://{folder}/index.html", wait_until="load"), LOAD_TIMEOUT)
    # no animations / blinking caret in screenshots
    await page.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}")
    return ctx, page, errors


def similarity(a_png: bytes, b_png: bytes) -> float:
    """How much the student's page looks like the teacher's, in % — a forgiving, "human" comparison:

    colour (60 %): both screenshots are shrunk and blurred, so a shift of a few pixels or a slightly different shade
                   costs only a little; each drawn pixel scores by how close its colour is (not just same / different);
    layout (40 %): where things are drawn at all — the drawn areas of the two pages, each allowed to be a few pixels
                   off, must cover each other.
    Only drawn pixels count (not the empty page background), so a small page isn't "90 % the same" because both
    are mostly white."""
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    a = Image.open(io.BytesIO(a_png)).convert("RGB")
    b = Image.open(io.BytesIO(b_png)).convert("RGB")
    if a.size != b.size:
        a = a.resize(b.size)
    size = (max(8, b.size[0] // 4), max(8, b.size[1] // 4))  # quarter size: anti-aliasing and 1-2 px shifts fade out
    a, b = a.resize(size, Image.BOX), b.resize(size, Image.BOX)
    bg = max(b.resize((64, 40)).getcolors(64 * 40))[1]
    solid = Image.new("RGB", size, bg)

    def channel_max(d):  # the biggest difference of the three colour channels, per pixel
        r, g, bl = d.split()
        return ImageChops.lighter(ImageChops.lighter(r, g), bl)

    def drawn(im):
        return channel_max(ImageChops.difference(im, solid)).point(lambda v: 255 if v > TOLERANCE // 2 else 0)

    ma, mb = drawn(a), drawn(b)
    content = ImageChops.lighter(ma, mb)
    n_content = content.histogram()[255]
    if n_content == 0:
        return 100.0
    # colour: blurred, scored continuously (difference 0 -> 1, >= 120 of 255 -> 0)
    blur = ImageFilter.GaussianBlur(1.5)
    d = channel_max(ImageChops.difference(a.filter(blur), b.filter(blur)))
    score = d.point(lambda v: max(0, 255 - round(v * 255 / 120)))
    colour = ImageStat.Stat(score, mask=content).mean[0] / 255
    # layout: each drawn area may be ~2 px (quarter size) off
    grow = ImageFilter.MaxFilter(5)
    na, nb = ma.histogram()[255], mb.histogram()[255]
    covered = ImageChops.multiply(ma, mb.filter(grow)).histogram()[255] + ImageChops.multiply(mb, ma.filter(grow)).histogram()[255]
    layout = covered / (na + nb) if na + nb else 1.0
    return round(100 * (0.6 * colour + 0.4 * layout), 1)


def content_box(pngs: list[bytes], pad: int = 24):
    """The part of the screenshots where something is drawn (both together), so the pictures shown to the student
    are not mostly empty page."""
    from PIL import Image, ImageChops
    box = None
    for png in pngs:
        im = Image.open(io.BytesIO(png)).convert("RGB")
        bg = max(im.resize((64, 40)).getcolors(64 * 40))[1]
        b = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        return None
    w, h = Image.open(io.BytesIO(pngs[0])).size
    return (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))


def thumb(png: bytes, box=None) -> str:
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if box:
        im = im.crop(box)
    if im.width > SHOT_WIDTH:
        im = im.resize((SHOT_WIDTH, round(im.height * SHOT_WIDTH / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


async def screenshot(browser: Browser, folder: str, viewport) -> bytes:
    ctx, page, _ = await open_page(browser, folder, viewport)
    try:
        await asyncio.sleep(0.15)
        return await asyncio.wait_for(page.screenshot(type="png"), TEST_TIMEOUT)
    finally:
        await asyncio.wait_for(ctx.close(), 3)


async def run_test(browser: Browser, job: dict, t: dict) -> dict:
    code, expected = t["code"], t["expected"]
    viewport, visual = directives(code)
    student = f"{job['dir']}/student"
    if visual is not None:
        want = f"≥ {visual}%"
        if not job["has_reference"]:
            return {"passed": False, "actual_output": "", "expected_output": want,
                    "error": "RUNTIME ERROR\nThe task has no model solution to compare with."}
        mine = await screenshot(browser, student, viewport)
        ref = await screenshot(browser, f"{job['dir']}/reference", viewport)
        sim = similarity(mine, ref)
        box = content_box([mine, ref])
        return {"passed": sim >= visual, "actual_output": f"{sim}%", "expected_output": want, "error": None,
                "images": {"actual": thumb(mine, box), "expected": thumb(ref, box), "viewport": f"{viewport[0]}x{viewport[1]}"}}
    ctx, page, errors = await open_page(browser, student, viewport)
    try:
        r = await asyncio.wait_for(page.evaluate(RUN_TEST, code), TEST_TIMEOUT)
    finally:
        try:
            await asyncio.wait_for(ctx.close(), 3)
        except Exception:
            await browser.reset()
    out = r.get("out", "")
    if r.get("error"):
        msg = r["error"]
        if errors:
            msg += "\nJavaScript errors on the page:\n" + "\n".join(errors[:5])
        return {"passed": False, "actual_output": out, "expected_output": expected, "error": f"RUNTIME ERROR\n{msg[:3000]}"}
    passed = normalize(out) == normalize(expected)
    err = None
    if not passed and errors:
        err = "RUNTIME ERROR\nJavaScript errors on the page:\n" + "\n".join(e[:500] for e in errors[:5])
    return {"passed": passed, "actual_output": out[:10_000], "expected_output": expected, "error": err}


async def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        job = json.load(f)
    rows = []
    async with async_playwright() as pw:
        browser = Browser(pw)
        for t in job["tests"]:
            try:
                rows.append(await run_test(browser, job, t))
            except asyncio.TimeoutError:
                await browser.reset()
                rows.append({"passed": False, "actual_output": "", "expected_output": t["expected"],
                             "error": "TIME LIMIT EXCEEDED"})
            except Exception as e:
                await browser.reset()
                rows.append({"passed": False, "actual_output": "", "expected_output": t["expected"],
                             "error": f"RUNTIME ERROR\n{type(e).__name__}: {str(e)[:1500]}"})
        await browser.reset()
    sys.stdout.write(json.dumps(rows) + "\n")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
