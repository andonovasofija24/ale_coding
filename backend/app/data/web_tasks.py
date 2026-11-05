"""
Sample web tasks for the bank: HTML + CSS (Основи на веб дизајн) and HTML + CSS + JavaScript (Интернет програмирање
на клиентска страна), with tests a web teacher would write: structure and semantics, accessibility (labels, alt
texts), computed styles, the layout on a phone and on a computer, behaviour after clicks / typing, and one visual
comparison with the model solution. The tests check facts, not one exact way of writing the code.
"""

HEAD = """<!-- file: index.html -->
<!doctype html>
<html lang="mk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
{body}
  <script src="script.js"></script>
</body>
</html>
<!-- file: style.css -->
{css}<!-- file: script.js -->
{js}"""

BASE_CSS = "body {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n"


def page(title: str, body: str = "", css: str = BASE_CSS, js: str = "") -> str:
    return HEAD.format(title=title, body=body, css=css, js=js)


def t(code: str, out: str, hidden: bool = False) -> dict:
    return {"type": "code_sample", "test_code": code, "stdin": "", "expected_output": out, "is_hidden": hidden}


WEB_TASKS = [
    # ---------------------------------------------------------------------------------------------------------------
    {
        "title": "Навигациско мени (HTML/CSS)",
        "subject": "ONVD",
        "description": """Направете **навигациско мени** за веб-страница на факултет.

**Структура** (во `index.html`):
- елемент `<nav class="menu">` со листа `<ul>` и **4** ставки `<li>`, во секоја по една врска `<a>` со атрибут `href`:
  „Почетна“, „Студии“, „Вести“, „Контакт“;
- врската на тековната страница („Почетна“) има класа `active`;
- под менито, наслов `<h1>` со текст по ваш избор.

**Изглед** (во `style.css`):
- ставките на менито се **во ред** (flexbox), листата нема точки (`list-style: none`);
- позадина на менито: `#1A2233`, врските се бели и **без подвлекување**;
- активната врска има позадина `#FCC419` и темен текст (`#1A2233`);
- на екран потесен од **600px** ставките се **една под друга**.
""",
        "translations": {"en": {"title": "Navigation menu (HTML/CSS)", "description": """Make a **navigation menu** for a faculty website.

**Structure** (`index.html`): a `<nav class="menu">` with a `<ul>` of **4** `<li>` items, each with one link `<a href>`:
"Home", "Studies", "News", "Contact"; the link of the current page ("Home") has the class `active`; under the menu an
`<h1>` with any text.

**Look** (`style.css`): the items are **in a row** (flexbox), the list has no bullets; menu background `#1A2233`, white
links **without underline**; the active link has the background `#FCC419` and dark text (`#1A2233`); on screens
narrower than **600px** the items are **one under another**."""}},
        "starter_code": page("Мени"),
        "model_solution": page("Мени", """  <nav class="menu">
    <ul>
      <li><a href="index.html" class="active">Почетна</a></li>
      <li><a href="studii.html">Студии</a></li>
      <li><a href="vesti.html">Вести</a></li>
      <li><a href="kontakt.html">Контакт</a></li>
    </ul>
  </nav>
  <h1>Добредојдовте на ФИНКИ</h1>""", BASE_CSS + """.menu {
  background: #1A2233;
}
.menu ul {
  display: flex;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 8px;
}
.menu a {
  display: block;
  color: #fff;
  text-decoration: none;
  padding: 10px 16px;
  border-radius: 6px;
}
.menu a.active {
  background: #FCC419;
  color: #1A2233;
}
h1 {
  padding: 0 16px;
}
@media (max-width: 600px) {
  .menu ul { flex-direction: column; }
}
"""),
        "tests": [
            t("print(exists('nav.menu'), count('nav.menu ul > li'), count('nav.menu li > a[href]'))", "true 4 4"),
            t("print($$('nav.menu a').map(a => a.textContent.trim()).join(', '))", "Почетна, Студии, Вести, Контакт"),
            t("print(count('nav.menu a.active'), text('nav.menu a.active'))", "1 Почетна"),
            t("print(css('nav.menu ul', 'display'), css('nav.menu ul', 'flex-direction'), css('nav.menu ul', 'list-style-type'))", "flex row none"),
            t("print(hex('nav.menu', 'background-color'), hex('nav.menu a:not(.active)', 'color'), css('nav.menu a', 'text-decoration-line'))",
              "#1a2233 #ffffff none"),
            t("print(hex('nav.menu a.active', 'background-color'), hex('nav.menu a.active', 'color'))", "#fcc419 #1a2233", True),
            t("// viewport: 375x667\nconst a = rect('nav.menu li:nth-child(1)'), b = rect('nav.menu li:nth-child(2)')\nprint(b.y > a.y, a.x === b.x)",
              "true true", True),
            t("print(exists('nav.menu + h1') || exists('h1'))", "true", True),
            t("// visual: 85", ""),
        ],
    },
    # ---------------------------------------------------------------------------------------------------------------
    {
        "title": "Ценовник со CSS Grid (HTML/CSS)",
        "subject": "ONVD",
        "description": """Направете **ценовник** со три пакети.

**Структура:** `<section class="plans">` со **три** `<article class="plan">`. Секој пакет има:
наслов `<h3>`, цена `<p class="price">` (на пр. `9 ден./мес.`), листа `<ul>` со барем **3** можности и врска
`<a class="btn">` „Избери“. Средниот пакет има и класа `featured`.

**Изглед:**
- `.plans` е **CSS Grid** со **3 колони** на компјутер и **1 колона** на екран потесен од **700px**, со растојание
  (`gap`) од `24px`;
- секој пакет: бела позадина, заоблени агли `12px`, рамка `1px solid #D9DEE7`;
- `.featured` има рамка `2px solid #2747C9`;
- `.btn` е син (`#2747C9`) со бел текст, без подвлекување.
""",
        "translations": {"en": {"title": "Pricing table with CSS Grid (HTML/CSS)", "description": """Make a **pricing table** with three plans.

**Structure:** `<section class="plans">` with **three** `<article class="plan">`; each has an `<h3>` title, a price
`<p class="price">`, a `<ul>` with at least **3** features and a link `<a class="btn">` "Choose". The middle plan also
has the class `featured`.

**Look:** `.plans` is a **CSS Grid** with **3 columns** on a computer and **1 column** on screens narrower than
**700px**, with a `24px` gap; each plan: white background, `12px` rounded corners, border `1px solid #D9DEE7`;
`.featured` has the border `2px solid #2747C9`; `.btn` is blue (`#2747C9`) with white text, not underlined."""}},
        "starter_code": page("Ценовник"),
        "model_solution": page("Ценовник", """  <section class="plans">
    <article class="plan">
      <h3>Студент</h3>
      <p class="price">0 ден./мес.</p>
      <ul><li>5 проекти</li><li>1 GB простор</li><li>Поддршка по е-пошта</li></ul>
      <a class="btn" href="#">Избери</a>
    </article>
    <article class="plan featured">
      <h3>Про</h3>
      <p class="price">299 ден./мес.</p>
      <ul><li>Неограничени проекти</li><li>50 GB простор</li><li>Приоритетна поддршка</li></ul>
      <a class="btn" href="#">Избери</a>
    </article>
    <article class="plan">
      <h3>Тим</h3>
      <p class="price">899 ден./мес.</p>
      <ul><li>10 корисници</li><li>500 GB простор</li><li>Поддршка 24/7</li></ul>
      <a class="btn" href="#">Избери</a>
    </article>
  </section>""", BASE_CSS + """body {
  background: #EEF1F5;
  padding: 40px 16px;
}
.plans {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 960px;
  margin: 0 auto;
}
.plan {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #D9DEE7;
  padding: 24px;
}
.plan.featured {
  border: 2px solid #2747C9;
}
.price {
  font-size: 24px;
  font-weight: 700;
}
.btn {
  display: inline-block;
  background: #2747C9;
  color: #fff;
  text-decoration: none;
  padding: 10px 18px;
  border-radius: 8px;
}
@media (max-width: 700px) {
  .plans { grid-template-columns: 1fr; }
}
"""),
        "tests": [
            t("print(count('section.plans > article.plan'), count('.plan h3'), count('.plan .price'), count('.plan a.btn'))", "3 3 3 3"),
            t("print(count('.plan') === 3 && $$('.plan').every(p => p.querySelectorAll('ul li').length >= 3))", "true"),
            t("print(count('.plan.featured'), $$('.plan').indexOf($('.plan.featured')))", "1 1"),
            t("print(css('.plans', 'display'), css('.plans', 'grid-template-columns').split(' ').length, css('.plans', 'column-gap'))", "grid 3 24px"),
            t("print(hex('.plan', 'background-color'), css('.plan', 'border-top-left-radius'), css('.plan:not(.featured)', 'border-top-width'), hex('.plan:not(.featured)', 'border-top-color'))",
              "#ffffff 12px 1px #d9dee7"),
            t("print(css('.plan.featured', 'border-top-width'), hex('.plan.featured', 'border-top-color'))", "2px #2747c9", True),
            t("print(hex('.btn', 'background-color'), hex('.btn', 'color'), css('.btn', 'text-decoration-line'))", "#2747c9 #ffffff none", True),
            t("// viewport: 375x667\nprint(css('.plans', 'grid-template-columns').split(' ').length, rect('.plan:nth-child(2)').y > rect('.plan:nth-child(1)').y)",
              "1 true", True),
            t("// visual: 85", ""),
        ],
    },
    # ---------------------------------------------------------------------------------------------------------------
    {
        "title": "Форма за регистрација (HTML/CSS)",
        "subject": "ONVD",
        "description": """Направете **пристапна форма за регистрација**.

**Структура:** `<form id="signup">` со три полиња, секое со своја ознака `<label for="…">`:
- „Име“ — `<input id="name">`, задолжително;
- „Е-пошта“ — `<input id="email" type="email">`, задолжително;
- „Лозинка“ — `<input id="password" type="password">`, задолжително, најмалку **8** знаци (`minlength`);

и копче `<button type="submit">` „Регистрирај се“.

**Изглед:** формата е широка најмногу `360px` и е **центрирана**; ознаките и полињата се **еден под друг**
(на пр. flexbox во колона); полињата имаат рамка `1px solid #D9DEE7` и заоблени агли `8px`; копчето е зелено
(`#2B8A3E`) со бел текст.
""",
        "translations": {"en": {"title": "Sign-up form (HTML/CSS)", "description": """Make an **accessible sign-up form**.

**Structure:** `<form id="signup">` with three fields, each with its own `<label for="…">`: "Name" — `<input id="name">`,
required; "E-mail" — `<input id="email" type="email">`, required; "Password" — `<input id="password" type="password">`,
required, at least **8** characters (`minlength`); and a `<button type="submit">` "Sign up".

**Look:** the form is at most `360px` wide and **centred**; labels and fields are **one under another**; the fields have
a `1px solid #D9DEE7` border and `8px` rounded corners; the button is green (`#2B8A3E`) with white text."""}},
        "starter_code": page("Регистрација"),
        "model_solution": page("Регистрација", """  <form id="signup">
    <h1>Регистрација</h1>
    <label for="name">Име</label>
    <input id="name" name="name" required>
    <label for="email">Е-пошта</label>
    <input id="email" name="email" type="email" required>
    <label for="password">Лозинка</label>
    <input id="password" name="password" type="password" minlength="8" required>
    <button type="submit">Регистрирај се</button>
  </form>""", BASE_CSS + """body {
  background: #EEF1F5;
  padding: 40px 16px;
}
#signup {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 360px;
  margin: 0 auto;
  background: #fff;
  padding: 24px;
  border-radius: 12px;
}
#signup input {
  border: 1px solid #D9DEE7;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 15px;
}
#signup button {
  margin-top: 8px;
  background: #2B8A3E;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 12px;
  font-size: 15px;
}
"""),
        "tests": [
            t("print(exists('form#signup'), exists('#name'), exists('#email'), exists('#password'), exists('form#signup button[type=submit]'))",
              "true true true true true"),
            t("print(['name', 'email', 'password'].every(id => !!document.querySelector(`label[for=${id}]`)))", "true"),
            t("print(attr('#email', 'type'), attr('#password', 'type'), attr('#password', 'minlength'))", "email password 8"),
            t("print(['#name', '#email', '#password'].every(s => $(s).required))", "true"),
            t("await type('#email', 'ne-e-adresa'); print($('#email').checkValidity())\nawait type('#email', 'ana@finki.ukim.mk'); print($('#email').checkValidity())",
              "false\ntrue", True),
            t("const f = rect('#signup'), w = document.documentElement.clientWidth\nprint(f.width <= 360, Math.abs(f.x - (w - f.x - f.width)) <= 4)", "true true"),
            t("print(rect('#email').y > rect('#name').y, rect('#password').y > rect('#email').y)", "true true", True),
            t("print(css('#name', 'border-top-width'), hex('#name', 'border-top-color'), css('#name', 'border-top-left-radius'))", "1px #d9dee7 8px", True),
            t("print(hex('#signup button', 'background-color'), hex('#signup button', 'color'))", "#2b8a3e #ffffff"),
            t("// viewport: 375x667\nconst f = rect('#signup')\nprint(f.x >= 0, f.x + f.width <= document.documentElement.clientWidth, rect('#email').width > 200)",
              "true true true", True),
            t("// visual: 85", ""),
        ],
    },
    # ---------------------------------------------------------------------------------------------------------------
    {
        "title": "Листа на задачи (HTML/CSS/JS)",
        "subject": "IPNKS",
        "description": """Направете **листа на задачи** (to-do).

**Структура:** поле `<input id="new">`, копче `<button id="add">` „Додај“, листа `<ul id="list">` и
`<p>` со `<span id="count">` — бројот на **незавршени** задачи.

**Однесување** (во `script.js`):
- клик на „Додај“ додава нова ставка `<li>` со текстот од полето (без празни места на почетокот и крајот) и го празни
  полето; **празен** текст не се додава;
- клик на ставка ја означува како завршена (класа `done`); нов клик го враќа назад;
- `#count` секогаш го покажува бројот на ставки **без** класа `done`.

**Изглед:** завршените ставки се **прецртани** (`text-decoration: line-through`) и сиви (`#868E96`).
""",
        "translations": {"en": {"title": "To-do list (HTML/CSS/JS)", "description": """Make a **to-do list**.

**Structure:** an `<input id="new">`, a `<button id="add">` "Add", a list `<ul id="list">` and a `<p>` with
`<span id="count">` — the number of **unfinished** tasks.

**Behaviour** (`script.js`): clicking "Add" adds a new `<li>` with the text of the field (trimmed) and empties the field;
**empty** text is not added; clicking an item marks it done (class `done`), clicking again undoes it; `#count` always
shows the number of items **without** the class `done`.

**Look:** done items are **struck through** (`text-decoration: line-through`) and grey (`#868E96`)."""}},
        "starter_code": page("Задачи", """  <h1>Мои задачи</h1>"""),
        "model_solution": page("Задачи", """  <main class="todo">
    <h1>Мои задачи</h1>
    <div class="row">
      <input id="new" placeholder="Нова задача…" aria-label="Нова задача">
      <button id="add">Додај</button>
    </div>
    <ul id="list"></ul>
    <p>Останати: <span id="count">0</span></p>
  </main>""", BASE_CSS + """.todo {
  max-width: 420px;
  margin: 40px auto;
  padding: 0 16px;
}
.row {
  display: flex;
  gap: 8px;
}
#new {
  flex: 1;
  padding: 10px;
  border: 1px solid #D9DEE7;
  border-radius: 8px;
}
#add {
  background: #2747C9;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 0 16px;
}
#list {
  list-style: none;
  padding: 0;
}
#list li {
  padding: 10px 12px;
  border-bottom: 1px solid #EEF1F5;
  cursor: pointer;
}
#list li.done {
  text-decoration: line-through;
  color: #868E96;
}
""", """const input = document.getElementById('new');
const list = document.getElementById('list');
const count = document.getElementById('count');

function refresh() {
  count.textContent = list.querySelectorAll('li:not(.done)').length;
}

document.getElementById('add').addEventListener('click', () => {
  const text = input.value.trim();
  if (!text) return;
  const li = document.createElement('li');
  li.textContent = text;
  li.addEventListener('click', () => {
    li.classList.toggle('done');
    refresh();
  });
  list.appendChild(li);
  input.value = '';
  refresh();
});
"""),
        "tests": [
            t("print(exists('input#new'), exists('button#add'), exists('ul#list'), text('#count'))", "true true true 0"),
            t("await type('#new', 'Купи леб'); await click('#add')\nprint(count('#list li'), text('#list li'), $('#new').value === '')", "1 Купи леб true"),
            t("await type('#new', '   '); await click('#add'); print(count('#list li'))", "0"),
            t("await type('#new', '  Учи CSS  '); await click('#add'); print(text('#list li'))", "Учи CSS", True),
            t("for (const x of ['А', 'Б', 'В']) { await type('#new', x); await click('#add') }\nprint(text('#count'))", "3"),
            t("for (const x of ['А', 'Б']) { await type('#new', x); await click('#add') }\nawait click('#list li')\n"
              "print($('#list li').classList.contains('done'), text('#count'))\nawait click('#list li')\nprint($('#list li').classList.contains('done'), text('#count'))",
              "true 1\nfalse 2", True),
            t("await type('#new', 'Х'); await click('#add'); await click('#list li')\nprint(css('#list li.done', 'text-decoration-line'), hex('#list li.done', 'color'))",
              "line-through #868e96", True),
            t("// visual: 80", ""),
        ],
    },
    # ---------------------------------------------------------------------------------------------------------------
    {
        "title": "Калкулатор за бакшиш (HTML/CSS/JS)",
        "subject": "IPNKS",
        "description": """Направете **калкулатор за бакшиш**.

**Структура:** поле `<input id="bill" type="number">` за износот на сметката, избор `<select id="percent">` со
опции **10**, **15** и **20** (вредностите се бројките, стандардно избрано **15**), и два резултати:
`<output id="tip">` (бакшиш) и `<output id="total">` (вкупно).

**Однесување:** штом ќе се смени износот или процентот, резултатите се пресметуваат одново и се прикажуваат со
**точно две децимали** (на пр. `15.00`, `115.00`). Ако износот е празен или негативен, двата резултати се `0.00`.

**Изглед:** калкулаторот е во картичка широка најмногу `340px`, центрирана, а `#total` е задебелен (`font-weight` барем 700).
""",
        "translations": {"en": {"title": "Tip calculator (HTML/CSS/JS)", "description": """Make a **tip calculator**.

**Structure:** `<input id="bill" type="number">` for the bill, `<select id="percent">` with options **10**, **15**, **20**
(the values are the numbers, **15** selected by default), and two results: `<output id="tip">` and `<output id="total">`.

**Behaviour:** whenever the bill or the percentage changes, the results are recomputed and shown with **exactly two
decimals** (e.g. `15.00`, `115.00`); an empty or negative bill gives `0.00` for both.

**Look:** the calculator is a card at most `340px` wide, centred; `#total` is bold (`font-weight` at least 700)."""}},
        "starter_code": page("Бакшиш"),
        "model_solution": page("Бакшиш", """  <main class="calc">
    <h1>Бакшиш</h1>
    <label for="bill">Сметка (ден.)</label>
    <input id="bill" type="number" min="0" step="any" placeholder="0">
    <label for="percent">Бакшиш</label>
    <select id="percent">
      <option value="10">10 %</option>
      <option value="15" selected>15 %</option>
      <option value="20">20 %</option>
    </select>
    <p>Бакшиш: <output id="tip">0.00</output></p>
    <p>Вкупно: <output id="total">0.00</output></p>
  </main>""", BASE_CSS + """body {
  background: #EEF1F5;
}
.calc {
  box-sizing: border-box;
  max-width: 340px;
  margin: 40px auto;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.calc input, .calc select {
  padding: 10px;
  border: 1px solid #D9DEE7;
  border-radius: 8px;
  font-size: 15px;
}
#total {
  font-weight: 800;
  font-size: 20px;
}
""", """const bill = document.getElementById('bill');
const percent = document.getElementById('percent');
const tip = document.getElementById('tip');
const total = document.getElementById('total');

function update() {
  const b = parseFloat(bill.value);
  const amount = Number.isFinite(b) && b > 0 ? b : 0;
  const t = amount * Number(percent.value) / 100;
  tip.textContent = t.toFixed(2);
  total.textContent = (amount + t).toFixed(2);
}

bill.addEventListener('input', update);
percent.addEventListener('change', update);
update();
"""),
        "tests": [
            t("print(attr('#bill', 'type'), $$('#percent option').map(o => o.value).join(','), $('#percent').value, exists('output#tip'), exists('output#total'))",
              "number 10,15,20 15 true true"),
            t("await type('#bill', '100'); print(text('#tip'), text('#total'))", "15.00 115.00"),
            t("await type('#bill', '100'); await type('#percent', '20'); print(text('#tip'), text('#total'))", "20.00 120.00"),
            t("await type('#bill', '45.50'); await type('#percent', '10'); print(text('#tip'), text('#total'))", "4.55 50.05", True),
            t("await type('#bill', '-5'); print(text('#tip'), text('#total'))\nawait type('#bill', ''); print(text('#tip'), text('#total'))",
              "0.00 0.00\n0.00 0.00", True),
            t("const c = rect('main') || rect('.calc'); print(rect('#bill').width <= 340, Number(css('#total', 'font-weight')) >= 700)", "true true"),
            t("// visual: 80", ""),
        ],
    },
]
