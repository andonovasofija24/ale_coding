"""Macedonian versions of the sample tasks (by their English title). Used by the seed and by the migration that
adds translations, so both new and existing installations get them. Code, identifiers and outputs stay as they are."""

MK = {
    "Hello World Function": {
        "title": "Функција за поздрав",
        "description": """Напишете C++ функција `greet(string name)` што го враќа стрингот "Hello, <name>!".

**Барања:**
- Функцијата прима параметар од тип `std::string` со име `name`.
- Функцијата враќа `std::string` во форматот `"Hello, <name>!"`.
- Во функцијата не печатете ништо; само вратете го стрингот.

**Пример:**
```
greet("World")  →  "Hello, World!"
greet("Alice")  →  "Hello, Alice!"
```
""",
    },
    "Stack Implementation": {
        "title": "Имплементација на стек",
        "description": """Имплементирајте податочна структура стек во C++ со динамичка низа.

**Барања:**
1. Направете класа `Stack` што чува вредности од тип `int`.
2. Имплементирајте `void push(int value)` — додава елемент на врвот.
3. Имплементирајте `int pop()` — го отстранува и враќа елементот од врвот. Ако стекот е празен, фрлете `std::underflow_error`.
4. Имплементирајте `int top() const` — го враќа елементот од врвот без да го отстрани. Ако стекот е празен, фрлете `std::underflow_error`.
5. Имплементирајте `bool isEmpty() const` — враќа `true` ако стекот е празен.
6. Имплементирајте `int size() const` — го враќа бројот на елементи.
7. Внимавајте на меморијата (деструктор, без протекување меморија).

**Пример:**
```
Stack s;
s.push(10);
s.push(20);
cout << s.top();   // 20
cout << s.pop();   // 20
cout << s.size();  // 1
```
""",
    },
    "Shape Hierarchy (OOP)": {
        "title": "Хиерархија на геометриски форми (ООП)",
        "description": """Дизајнирајте хиерархија на класи за геометриски форми.

**Барања:**

1. Апстрактна основна класа `Shape` со:
   - чисто виртуелен метод `double area() const`
   - чисто виртуелен метод `double perimeter() const`
   - виртуелен метод `void print() const` што печати: `Shape: area=<area>, perimeter=<perimeter>` (2 децимали)

2. Класа `Circle` што наследува од `Shape`:
   - конструктор `Circle(double radius)`
   - `area()` → π × r²
   - `perimeter()` → 2 × π × r
   - за π користете `M_PI`

3. Класа `Rectangle` што наследува од `Shape`:
   - конструктор `Rectangle(double width, double height)`
   - `area()` → width × height
   - `perimeter()` → 2 × (width + height)

**Пример излез:**
```
Shape: area=78.54, perimeter=31.42
Shape: area=12.00, perimeter=14.00
```
""",
    },
    "Word Frequency (Python)": {
        "title": "Честота на зборови (Python)",
        "description": """Напишете Python функција `word_frequency(text)` што брои колку пати се појавува секој збор во текстот.

**Барања:**
1. Зборовите се одделени со празни места; не се прави разлика меѓу мали и големи букви (`"Code"` и `"code"` се ист збор).
2. Отстранете ги интерпункциските знаци `.,!?;:` од почетокот и крајот на секој збор.
3. Вратете `dict` што секој збор го пресликува во неговиот број на појавувања. За празен текст вратете `{}`.
4. Напишете и втора функција `top_words(text, n)` што ги враќа `n` најчести зборови како листа од торки
   `(збор, број)`, од најчестиот; при ист број, зборовите се подредени азбучно.

**Пример:**
```
word_frequency("Code, code. Learn!")   →  {'code': 2, 'learn': 1}
top_words("b a b c a b", 2)            →  [('b', 3), ('a', 2)]
```
""",
    },
    "Bank Account (Java)": {
        "title": "Банкарска сметка (Java)",
        "description": """Имплементирајте класа `BankAccount` во Java.

**Барања:**
1. Конструктор `BankAccount(String owner, double initialBalance)`.
2. `void deposit(double amount)` — додава пари; ако `amount <= 0`, фрлете `IllegalArgumentException`.
3. `void withdraw(double amount)` — подига пари; ако `amount <= 0`, фрлете `IllegalArgumentException`,
   а ако нема доволно средства, фрлете `IllegalStateException("Insufficient funds")`.
4. `double getBalance()` и `String getOwner()`.
5. `String toString()` враќа `"<owner>: <balance>"` со салдото на 2 децимали, на пр. `Ana: 150.00`.

**Пример:**
```
BankAccount a = new BankAccount("Ana", 100);
a.deposit(50);
System.out.println(a);   // Ana: 150.00
```
""",
    },
    "Reverse Array (C)": {
        "title": "Превртена низа (C)",
        "description": """Напишете C програма што чита `n`, а потоа `n` цели броеви, и ги печати во **обратен редослед**,
одделени со по едно празно место.

**Влез:** првиот ред содржи `n` (1 ≤ n ≤ 1000), вториот ред `n` цели броеви.

**Излез:** броевите во обратен редослед, во еден ред.

**Пример:**
```
Влез:
5
1 2 3 4 5
Излез:
5 4 3 2 1
```
""",
    },
    "Palindromes (JavaScript)": {
        "title": "Палиндроми (JavaScript)",
        "description": """Напишете JavaScript функција `isPalindrome(text)` што враќа `true` ако `text` се чита исто
од напред и од назад, **без разлика на мали/големи букви, празни места и интерпункција**, а инаку `false`.

Потоа напишете `countPalindromes(words)` што враќа колку стрингови во низата `words` се палиндроми.

**Пример:**
```js
isPalindrome("Ana")                       // true
isPalindrome("Never odd or even!")        // true
countPalindromes(["kayak", "ALE", "Oko"]) // 2
```
""",
    },
    "Average Grade per Student (SQL)": {
        "title": "Просечна оценка по студент (SQL)",
        "description": """Базата има две табели:

| student | |
|---|---|
| `id` | INTEGER, примарен клуч |
| `ime` | TEXT — име |
| `smer` | TEXT — студиска програма |

| ocena | |
|---|---|
| `student_id` | INTEGER → `student.id` |
| `predmet` | TEXT — предмет |
| `ocena` | INTEGER — оценка 5–10 |

Напишете барање што за секој студент **што има барем една оценка** ги враќа неговото **име** и
**просечната оценка**, подредени од **највисокиот кон најнискиот просек**.

Очекувани колони: `ime`, `prosek`.
""",
    },
    "Enrolments per Course (PostgreSQL)": {
        "title": "Запишани по предмет (PostgreSQL)",
        "description": """Табели (PostgreSQL):

- `predmet(id SERIAL, ime TEXT, krediti INT)` — предмети
- `upis(student TEXT, predmet_id INT → predmet.id, datum DATE)` — запишувања

Напишете барање што го враќа **секој** предмет (и оние без запишани студенти) со **бројот на запишани
студенти**, како колони `ime` и `broj`, подредени по `broj` опаѓачки, а потоа по `ime`.
""",
    },
    "Typed Stack (TypeScript)": {
        "title": "Типизиран стек (TypeScript)",
        "description": """Имплементирајте генеричка класа `Stack<T>` во TypeScript со `push(x: T): void`, `pop(): T | undefined`,
`peek(): T | undefined` и својство само за читање `size: number`.

Код што ја користи со погрешен тип **не смее да се компајлира**, на пр. ставање стринг во `Stack<number>`.
""",
    },
    "Word Counter (PHP)": {
        "title": "Бројач на зборови (PHP)",
        "description": """Напишете PHP функција `countWords(string $text): array` што враќа колку пати се појавува секој збор,
без разлика на мали/големи букви, како низа `збор => број`, подредена по број (опаѓачки), а потоа азбучно.
""",
    },
    "Line Statistics (Bash)": {
        "title": "Статистика за редови (Bash)",
        "description": """Напишете Bash скрипта што чита редови од стандардниот влез и печати три броја во еден ред:
бројот на редови, бројот на зборови и должината на најдолгиот ред.
""",
    },
    "Shapes (C#)": {
        "title": "Геометриски форми (C#)",
        "description": """Во C# напишете апстрактна класа `Shape` со апстрактен метод `double Area()` и класите
`Circle(double r)` и `Rectangle(double w, double h)`. Додадете статички метод `Shapes.TotalArea(List<Shape> shapes)`
што го враќа збирот на плоштините.
""",
    },
    "Grades (Kotlin)": {
        "title": "Оценки (Kotlin)",
        "description": """Во Kotlin напишете `data class Student(val name: String, val grades: List<Int>)` со својство
`average` (0.0 кога нема оценки) и функција `best(students: List<Student>): String?` што го враќа
името на студентот со највисок просек (или `null` за празна листа).
""",
    },
    "Family Tree (Prolog)": {
        "title": "Семејно стебло (Prolog)",
        "description": """Дадени се факти `parent(Parent, Child)`. Напишете ги правилата:

- `grandparent(G, C)` — G е баба или дедо на C
- `sibling(A, B)` — A и B имаат заеднички родител и се различни лица
- `ancestor(A, D)` — A е родител, баба/дедо, прабаба/прадедо... на D

Фактите се во почетниот код — задржете ги.
""",
    },
    "List Functions (Common Lisp)": {
        "title": "Функции за листи (Common Lisp)",
        "description": """Во Common Lisp напишете:

- `(my-reverse lst)` — ја превртува листата **рекурзивно** (без `reverse`)
- `(count-if-even lst)` — колку елементи се парни
- `(flatten tree)` — вгнездена листа ја претвора во рамна, на пр. `(flatten '(1 (2 (3)) 4))` → `(1 2 3 4)`
""",
    },
    "Array Sum (x86-64 Assembly)": {
        "title": "Збир на низа (x86-64 асемблер)",
        "description": """Во x86-64 NASM асемблер напишете ја функцијата

```c
long array_sum(long *a, long n);
```

што го враќа збирот на `n`-те елементи од низата `a`. Следете ја System V конвенцијата за повикување:
`a` е во `rdi`, `n` во `rsi`, а резултатот оди во `rax`. Означете ја со `global array_sum`.
""",
    },
    "Profile Card (HTML/CSS)": {
        "title": "Картичка за профил (HTML/CSS)",
        "description": """Направете страница со **картичка за профил** во `index.html`, `style.css` и `script.js`.

**Структура** (во `<div class="card">`):
- `<h2>` со име и `<p class="role">` со улога,
- листа `<ul class="skills">` со **најмалку 3** ставки `<li>`,
- копче `<button id="follow">Follow</button>`.

**Стил:**
- `.card`: бела позадина, заоблени агли од `12px`, најмногу `320px` широка, центрирана на страницата.
- копчето: позадина `#2747C9`, бел текст.
- `.skills` ги прикажува ставките **во ред** (flexbox); на екрани потесни од **600px** се **една под друга**.

**Однесување:** клик на копчето го менува текстот во `Following`; повторен клик го враќа во `Follow`.
""",
    },
}
