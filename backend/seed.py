"""Seed initial admin user and sample tasks. Idempotent — safe to run multiple times."""
import asyncio
import uuid
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.data.task_translations_mk import MK
from app.models.user import User
from app.models.task import Task, TestCase
from app.core.security import hash_password
from app.config import settings

SAMPLE_TASKS = [
    {
        "title": "Hello World Function",
        "description": """Write a C++ function `greet(string name)` that returns the string "Hello, <name>!".

**Requirements:**
- The function must take a `std::string` parameter called `name`.
- The function must return a `std::string` in the format `"Hello, <name>!"`.
- Do not print anything inside the function; just return the string.

**Example:**
```
greet("World")  →  "Hello, World!"
greet("Alice")  →  "Hello, Alice!"
```
""",
        "starter_code": '#include <string>\nusing namespace std;\n\n// TODO: implement greet()\n',
        "model_solution": '#include <string>\nusing namespace std;\n\nstring greet(string name) {\n    return "Hello, " + name + "!";\n}\n',
        "language": "cpp",
        "test_cases": [
            {"type": "code_sample", "test_code": 'cout << greet("World") << endl;', "stdin": "", "expected_output": "Hello, World!\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": 'cout << greet("Alice") << endl;', "stdin": "", "expected_output": "Hello, Alice!\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": 'cout << greet("FINKI") << endl;', "stdin": "", "expected_output": "Hello, FINKI!\n", "is_hidden": True, "order": 2},
        ],
    },
    {
        "title": "Stack Implementation",
        "description": """Implement a generic stack data structure in C++ using a dynamic array.

**Requirements:**
1. Create a class `Stack` that stores `int` values.
2. Implement `void push(int value)` — adds an element to the top.
3. Implement `int pop()` — removes and returns the top element. Throw `std::underflow_error` if empty.
4. Implement `int top() const` — returns the top element without removing it. Throw `std::underflow_error` if empty.
5. Implement `bool isEmpty() const` — returns `true` if the stack is empty.
6. Implement `int size() const` — returns the number of elements.
7. Ensure proper memory management (destructor, no memory leaks).

**Example:**
```
Stack s;
s.push(10);
s.push(20);
cout << s.top();   // 20
cout << s.pop();   // 20
cout << s.size();  // 1
```
""",
        "starter_code": '#include <stdexcept>\nusing namespace std;\n\n// TODO: implement Stack class\n',
        "model_solution": '''#include <stdexcept>
using namespace std;

class Stack {
    int* data;
    int capacity;
    int count;

    void resize() {
        capacity *= 2;
        int* newData = new int[capacity];
        for (int i = 0; i < count; i++) newData[i] = data[i];
        delete[] data;
        data = newData;
    }

public:
    Stack() : capacity(8), count(0) {
        data = new int[capacity];
    }

    ~Stack() { delete[] data; }

    void push(int value) {
        if (count == capacity) resize();
        data[count++] = value;
    }

    int pop() {
        if (isEmpty()) throw underflow_error("Stack is empty");
        return data[--count];
    }

    int top() const {
        if (isEmpty()) throw underflow_error("Stack is empty");
        return data[count - 1];
    }

    bool isEmpty() const { return count == 0; }
    int size() const { return count; }
};
''',
        "language": "cpp",
        "test_cases": [
            {"type": "code_sample", "test_code": "Stack s;\ns.push(10);\ncout << s.top() << endl;", "stdin": "", "expected_output": "10\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": "Stack s;\ns.push(1); s.push(2); s.push(3);\ncout << s.pop() << endl;\ncout << s.size() << endl;", "stdin": "", "expected_output": "3\n2\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": "Stack s;\ncout << s.isEmpty() << endl;\ns.push(5);\ncout << s.isEmpty() << endl;", "stdin": "", "expected_output": "1\n0\n", "is_hidden": False, "order": 2},
            {"type": "code_sample", "test_code": 'Stack s;\ntry { s.pop(); } catch (underflow_error& e) { cout << "caught" << endl; }', "stdin": "", "expected_output": "caught\n", "is_hidden": True, "order": 3},
        ],
    },
    {
        "title": "Shape Hierarchy (OOP)",
        "description": """Design a class hierarchy for geometric shapes.

**Requirements:**

1. Abstract base class `Shape` with:
   - Pure virtual method `double area() const`
   - Pure virtual method `double perimeter() const`
   - Virtual method `void print() const` that prints: `Shape: area=<area>, perimeter=<perimeter>` (2 decimal places)

2. Class `Circle` inheriting from `Shape`:
   - Constructor `Circle(double radius)`
   - Implement `area()` → π × r²
   - Implement `perimeter()` → 2 × π × r
   - Use `M_PI` for π

3. Class `Rectangle` inheriting from `Shape`:
   - Constructor `Rectangle(double width, double height)`
   - Implement `area()` → width × height
   - Implement `perimeter()` → 2 × (width + height)

**Example output:**
```
Shape: area=78.54, perimeter=31.42
Shape: area=12.00, perimeter=14.00
```
""",
        "starter_code": '#include <iostream>\n#include <cmath>\n#include <iomanip>\nusing namespace std;\n\n// TODO: implement Shape, Circle, Rectangle\n',
        "model_solution": '''#include <iostream>
#include <cmath>
#include <iomanip>
using namespace std;

class Shape {
public:
    virtual double area() const = 0;
    virtual double perimeter() const = 0;
    virtual void print() const {
        cout << fixed << setprecision(2)
             << "Shape: area=" << area()
             << ", perimeter=" << perimeter() << endl;
    }
    virtual ~Shape() {}
};

class Circle : public Shape {
    double radius;
public:
    Circle(double r) : radius(r) {}
    double area() const override { return M_PI * radius * radius; }
    double perimeter() const override { return 2 * M_PI * radius; }
};

class Rectangle : public Shape {
    double width, height;
public:
    Rectangle(double w, double h) : width(w), height(h) {}
    double area() const override { return width * height; }
    double perimeter() const override { return 2 * (width + height); }
};
''',
        "language": "cpp",
        "test_cases": [
            {"type": "code_sample", "test_code": "Circle c(5);\ncout << fixed << setprecision(2) << c.area() << endl;", "stdin": "", "expected_output": "78.54\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": "Rectangle r(3, 4);\ncout << fixed << setprecision(2) << r.area() << endl;\ncout << fixed << setprecision(2) << r.perimeter() << endl;", "stdin": "", "expected_output": "12.00\n14.00\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": "Circle c(5);\nc.print();", "stdin": "", "expected_output": "Shape: area=78.54, perimeter=31.42\n", "is_hidden": False, "order": 2},
            {"type": "code_sample", "test_code": "Shape* s = new Rectangle(3, 4);\ns->print();\ndelete s;", "stdin": "", "expected_output": "Shape: area=12.00, perimeter=14.00\n", "is_hidden": True, "order": 3},
        ],
    },
    {
        "title": "Word Frequency (Python)",
        "description": """Write a Python function `word_frequency(text)` that counts how many times each word appears in a text.

**Requirements:**
1. Words are separated by whitespace; ignore case (`"Code"` and `"code"` are the same word).
2. Strip the punctuation `.,!?;:` from the start and end of each word.
3. Return a `dict` mapping each word to its count. Empty text returns `{}`.
4. Write a second function `top_words(text, n)` that returns the `n` most frequent words as a list of
   `(word, count)` tuples, most frequent first; ties are ordered alphabetically.

**Example:**
```
word_frequency("Code, code. Learn!")   →  {'code': 2, 'learn': 1}
top_words("b a b c a b", 2)            →  [('b', 3), ('a', 2)]
```
""",
        "starter_code": "def word_frequency(text):\n    # TODO\n    pass\n\n\ndef top_words(text, n):\n    # TODO\n    pass\n",
        "model_solution": """def word_frequency(text):
    counts = {}
    for raw in text.split():
        word = raw.strip(".,!?;:").lower()
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts


def top_words(text, n):
    counts = word_frequency(text)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
""",
        "language": "python",
        "test_cases": [
            {"type": "code_sample", "test_code": 'print(word_frequency("Code, code. Learn!"))', "stdin": "", "expected_output": "{'code': 2, 'learn': 1}\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": 'print(top_words("b a b c a b", 2))', "stdin": "", "expected_output": "[('b', 3), ('a', 2)]\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": 'print(word_frequency(""))\nprint(word_frequency("   "))', "stdin": "", "expected_output": "{}\n{}\n", "is_hidden": True, "order": 2},
            {"type": "code_sample", "test_code": 'print(top_words("x y z y x", 3))', "stdin": "", "expected_output": "[('x', 2), ('y', 2), ('z', 1)]\n", "is_hidden": True, "order": 3},
        ],
    },
    {
        "title": "Bank Account (Java)",
        "description": """Implement a class `BankAccount` in Java.

**Requirements:**
1. Constructor `BankAccount(String owner, double initialBalance)`.
2. `void deposit(double amount)` — adds money; throw `IllegalArgumentException` if `amount <= 0`.
3. `void withdraw(double amount)` — removes money; throw `IllegalArgumentException` if `amount <= 0`
   and `IllegalStateException("Insufficient funds")` if the balance is too low.
4. `double getBalance()` and `String getOwner()`.
5. `String toString()` returns `"<owner>: <balance>"` with the balance to 2 decimals, e.g. `Ana: 150.00`.

**Example:**
```
BankAccount a = new BankAccount("Ana", 100);
a.deposit(50);
System.out.println(a);   // Ana: 150.00
```
""",
        "starter_code": "public class BankAccount {\n    // TODO: fields, constructor, methods\n}\n",
        "model_solution": """public class BankAccount {
    private final String owner;
    private double balance;

    public BankAccount(String owner, double initialBalance) {
        this.owner = owner;
        this.balance = initialBalance;
    }

    public void deposit(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");
        balance += amount;
    }

    public void withdraw(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");
        if (amount > balance) throw new IllegalStateException("Insufficient funds");
        balance -= amount;
    }

    public double getBalance() { return balance; }
    public String getOwner() { return owner; }

    @Override
    public String toString() {
        return String.format(java.util.Locale.US, "%s: %.2f", owner, balance);
    }
}
""",
        "language": "java",
        "test_cases": [
            {"type": "code_sample", "test_code": 'BankAccount a = new BankAccount("Ana", 100);\na.deposit(50);\nSystem.out.println(a);', "stdin": "", "expected_output": "Ana: 150.00\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": 'BankAccount a = new BankAccount("Marko", 20);\na.withdraw(5.5);\nSystem.out.println(a.getBalance());', "stdin": "", "expected_output": "14.5\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": 'BankAccount a = new BankAccount("Ivo", 10);\ntry { a.withdraw(50); } catch (IllegalStateException e) { System.out.println(e.getMessage()); }\ntry { a.deposit(-1); } catch (IllegalArgumentException e) { System.out.println("invalid"); }', "stdin": "", "expected_output": "Insufficient funds\ninvalid\n", "is_hidden": True, "order": 2},
        ],
    },
    {
        "title": "Reverse Array (C)",
        "description": """Write a C program that reads `n` and then `n` integers, and prints them in **reverse order**,
separated by single spaces.

**Input:** the first line contains `n` (1 ≤ n ≤ 1000), the second line `n` integers.

**Output:** the numbers in reverse order on one line.

**Example:**
```
Input:
5
1 2 3 4 5
Output:
5 4 3 2 1
```
""",
        "starter_code": "#include <stdio.h>\n\nint main(void) {\n    // TODO\n    return 0;\n}\n",
        "model_solution": """#include <stdio.h>

int main(void) {
    int n, a[1000];
    scanf("%d", &n);
    for (int i = 0; i < n; i++) scanf("%d", &a[i]);
    for (int i = n - 1; i >= 0; i--) printf("%d%c", a[i], i ? ' ' : '\\n');
    return 0;
}
""",
        "language": "c",
        "test_cases": [
            {"type": "stdin_stdout", "test_code": "", "stdin": "5\n1 2 3 4 5\n", "expected_output": "5 4 3 2 1\n", "is_hidden": False, "order": 0},
            {"type": "stdin_stdout", "test_code": "", "stdin": "1\n42\n", "expected_output": "42\n", "is_hidden": False, "order": 1},
            {"type": "stdin_stdout", "test_code": "", "stdin": "4\n-3 0 7 -3\n", "expected_output": "-3 7 0 -3\n", "is_hidden": True, "order": 2},
        ],
    },
    {
        "title": "Palindromes (JavaScript)",
        "description": """Write a JavaScript function `isPalindrome(text)` that returns `true` if `text` reads the same
forwards and backwards, **ignoring letter case, spaces and punctuation**, and `false` otherwise.

Then write `countPalindromes(words)` that returns how many strings in the array `words` are palindromes.

**Example:**
```js
isPalindrome("Ana")                       // true
isPalindrome("Never odd or even!")        // true
countPalindromes(["kayak", "ALE", "Oko"]) // 2
```
""",
        "starter_code": "function isPalindrome(text) {\n  // TODO\n}\n\nfunction countPalindromes(words) {\n  // TODO\n}\n",
        "model_solution": """function isPalindrome(text) {
  const t = text.toLowerCase().replace(/[^\\p{L}\\p{N}]/gu, "");
  return t === [...t].reverse().join("");
}

function countPalindromes(words) {
  return words.filter(isPalindrome).length;
}
""",
        "language": "javascript",
        "test_cases": [
            {"type": "code_sample", "test_code": 'console.log(isPalindrome("Ana"));\nconsole.log(isPalindrome("Never odd or even!"));', "stdin": "", "expected_output": "true\ntrue\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": 'console.log(countPalindromes(["kayak", "ALE", "Oko"]));', "stdin": "", "expected_output": "2\n", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": 'console.log(isPalindrome("abc"), isPalindrome(""), countPalindromes([]));', "stdin": "", "expected_output": "false true 0\n", "is_hidden": True, "order": 2},
        ],
    },
    {
        "title": "Average Grade per Student (SQL)",
        "description": """The database has two tables:

| student | |
|---|---|
| `id` | INTEGER, primary key |
| `ime` | TEXT — name |
| `smer` | TEXT — study programme |

| ocena | |
|---|---|
| `student_id` | INTEGER → `student.id` |
| `predmet` | TEXT — course |
| `ocena` | INTEGER — grade 5–10 |

Write a query that returns, for every student **who has at least one grade**, their **name** and their
**average grade**, sorted from the **highest average to the lowest**.

Expected columns: `ime`, `prosek`.
""",
        "starter_code": "SELECT\n  -- TODO\n;\n",
        "model_solution": """SELECT s.ime, AVG(o.ocena) AS prosek
FROM student s
JOIN ocena o ON o.student_id = s.id
GROUP BY s.id, s.ime
ORDER BY prosek DESC;
""",
        "language": "sql",
        "test_cases": [
            {"type": "code_sample", "test_code": """CREATE TABLE student (id INTEGER PRIMARY KEY, ime TEXT, smer TEXT);
CREATE TABLE ocena (student_id INTEGER REFERENCES student(id), predmet TEXT, ocena INTEGER);
INSERT INTO student VALUES (1, 'Ана', 'СИИС'), (2, 'Марко', 'КНИ'), (3, 'Елена', 'СИИС');
INSERT INTO ocena VALUES (1, 'БП', 10), (1, 'ОС', 9), (2, 'БП', 7), (3, 'БП', 8), (3, 'ОС', 8);
-- ordered""", "stdin": "", "expected_output": "ime | prosek\nАна | 9.5\nЕлена | 8\nМарко | 7\n", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": """CREATE TABLE student (id INTEGER PRIMARY KEY, ime TEXT, smer TEXT);
CREATE TABLE ocena (student_id INTEGER REFERENCES student(id), predmet TEXT, ocena INTEGER);
INSERT INTO student VALUES (1, 'Ана', 'СИИС'), (2, 'Ана', 'КНИ'), (3, 'Петар', 'ПИТ');
INSERT INTO ocena VALUES (1, 'БП', 6), (2, 'БП', 10), (2, 'ВИ', 9);
-- ordered""", "stdin": "", "expected_output": "ime | prosek\nАна | 9.5\nАна | 6\n", "is_hidden": True, "order": 1},
        ],
    },
    {'title': 'Enrolments per Course (PostgreSQL)',
     'language': 'postgresql',
     'description': 'Tables (PostgreSQL):\n'
                    '\n'
                    '- `predmet(id SERIAL, ime TEXT, krediti INT)` — courses\n'
                    '- `upis(student TEXT, predmet_id INT → predmet.id, datum DATE)` — enrolments\n'
                    '\n'
                    'Write a query that returns **every** course (also those with no enrolments) with the **number of '
                    'enrolled\n'
                    'students**, as columns `ime` and `broj`, sorted by `broj` descending, then by `ime`.',
     'starter_code': 'SELECT\n  -- TODO\n;\n',
     'model_solution': 'SELECT p.ime, COUNT(u.student) AS broj\n'
                       'FROM predmet p\n'
                       'LEFT JOIN upis u ON u.predmet_id = p.id\n'
                       'GROUP BY p.id, p.ime\n'
                       'ORDER BY broj DESC, p.ime;\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'CREATE TABLE predmet (id SERIAL PRIMARY KEY, ime TEXT NOT NULL, krediti INT);\n'
                                  'CREATE TABLE upis (student TEXT, predmet_id INT REFERENCES predmet(id), datum DATE);\n'
                                  "INSERT INTO predmet (ime, krediti) VALUES ('Бази на податоци', 6), ('Оперативни "
                                  "системи', 6), ('Веб програмирање', 6);\n"
                                  "INSERT INTO upis VALUES ('Ана', 1, '2026-10-01'), ('Марко', 1, '2026-10-02'), ('Ана', "
                                  "2, '2026-10-01'), ('Ива', 1, '2026-10-05');\n"
                                  '-- ordered',
                     'stdin': '',
                     'expected_output': 'ime | broj\nБази на податоци | 3\nОперативни системи | 1\nВеб програмирање | 0\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'CREATE TABLE predmet (id SERIAL PRIMARY KEY, ime TEXT NOT NULL, krediti INT);\n'
                                  'CREATE TABLE upis (student TEXT, predmet_id INT REFERENCES predmet(id), datum DATE);\n'
                                  "INSERT INTO predmet (ime, krediti) VALUES ('Бази на податоци', 6), ('Оперативни "
                                  "системи', 6), ('Веб програмирање', 6);\n"
                                  "INSERT INTO upis VALUES ('Ана', 1, '2026-10-01'), ('Марко', 1, '2026-10-02'), ('Ана', "
                                  "2, '2026-10-01'), ('Ива', 3, '2026-10-05'), ('Лео', 3, '2026-10-06');\n"
                                  '-- ordered',
                     'stdin': '',
                     'expected_output': 'ime | broj\nБази на податоци | 2\nВеб програмирање | 2\nОперативни системи | 1\n',
                     'is_hidden': True,
                     'order': 1}]},
    {'title': 'Typed Stack (TypeScript)',
     'language': 'typescript',
     'description': 'Implement a generic class `Stack<T>` in TypeScript with `push(x: T): void`, `pop(): T | undefined`,\n'
                    '`peek(): T | undefined` and a read-only property `size: number`.\n'
                    '\n'
                    'Code that uses it with the wrong type must **not compile**, e.g. pushing a string into a '
                    '`Stack<number>`.',
     'starter_code': 'class Stack<T> {\n  // TODO\n}\n',
     'model_solution': 'class Stack<T> {\n'
                       '  private items: T[] = [];\n'
                       '  push(x: T): void { this.items.push(x); }\n'
                       '  pop(): T | undefined { return this.items.pop(); }\n'
                       '  peek(): T | undefined { return this.items[this.items.length - 1]; }\n'
                       '  get size(): number { return this.items.length; }\n'
                       '}\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'const s = new Stack<number>();\ns.push(1); s.push(2);\nconsole.log(s.pop(), s.size);',
                     'stdin': '',
                     'expected_output': '2 1\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'const s = new Stack<string>();\nconsole.log(s.pop(), s.peek(), s.size);',
                     'stdin': '',
                     'expected_output': 'undefined undefined 0\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': 'const s = new Stack<number>();\n'
                                  'for (let i = 0; i < 5; i++) s.push(i * i);\n'
                                  'console.log(s.peek(), s.size);',
                     'stdin': '',
                     'expected_output': '16 5\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'Word Counter (PHP)',
     'language': 'php',
     'description': 'Write a PHP function `countWords(string $text): array` that returns how many times each word '
                    'appears,\n'
                    'ignoring case, as an array `word => count` sorted by count (descending) and then alphabetically.',
     'starter_code': '<?php\nfunction countWords(string $text): array {\n    // TODO\n}\n',
     'model_solution': '<?php\n'
                       'function countWords(string $text): array {\n'
                       "    $words = preg_split('/[^\\p{L}]+/u', mb_strtolower($text), -1, PREG_SPLIT_NO_EMPTY);\n"
                       '    $c = array_count_values($words);\n'
                       '    uksort($c, fn($a, $b) => [$c[$b], $a] <=> [$c[$a], $b]);\n'
                       '    return $c;\n'
                       '}\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'foreach (countWords("a b A c b a") as $w => $n) echo "$w $n\\n";',
                     'stdin': '',
                     'expected_output': 'a 3\nb 2\nc 1\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'echo count(countWords("")), "\\n";',
                     'stdin': '',
                     'expected_output': '0\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': 'print_r(countWords("Зошто да, зошто не"));',
                     'stdin': '',
                     'expected_output': 'Array\n(\n    [зошто] => 2\n    [да] => 1\n    [не] => 1\n)\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'Line Statistics (Bash)',
     'language': 'bash',
     'description': 'Write a Bash script that reads lines from standard input and prints three numbers on one line:\n'
                    'the number of lines, the number of words and the length of the longest line.',
     'starter_code': '#!/bin/bash\n# TODO\n',
     'model_solution': '#!/bin/bash\n'
                       'lines=0; words=0; longest=0\n'
                       'while IFS= read -r line || [ -n "$line" ]; do\n'
                       '  lines=$((lines + 1))\n'
                       '  set -- $line\n'
                       '  words=$((words + $#))\n'
                       '  [ ${#line} -gt $longest ] && longest=${#line}\n'
                       'done\n'
                       'echo "$lines $words $longest"\n',
     'test_cases': [{'type': 'stdin_stdout',
                     'test_code': '',
                     'stdin': 'hello world\none two three\nx\n',
                     'expected_output': '3 6 13\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'stdin_stdout',
                     'test_code': '',
                     'stdin': '',
                     'expected_output': '0 0 0\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'stdin_stdout',
                     'test_code': '',
                     'stdin': '  spaced  \nlast\n',
                     'expected_output': '2 2 10\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'Shapes (C#)',
     'language': 'csharp',
     'description': 'In C#, write an abstract class `Shape` with an abstract method `double Area()` and the classes\n'
                    '`Circle(double r)` and `Rectangle(double w, double h)`. Add a static method '
                    '`Shapes.TotalArea(List<Shape> shapes)`\n'
                    'that returns the sum of the areas.',
     'starter_code': 'public abstract class Shape\n{\n    // TODO\n}\n',
     'model_solution': 'public abstract class Shape { public abstract double Area(); }\n'
                       'public class Circle : Shape { private readonly double r; public Circle(double r) { this.r = r; } '
                       'public override double Area() => Math.PI * r * r; }\n'
                       'public class Rectangle : Shape { private readonly double w, h; public Rectangle(double w, double '
                       'h) { this.w = w; this.h = h; } public override double Area() => w * h; }\n'
                       'public static class Shapes { public static double TotalArea(List<Shape> shapes) => shapes.Sum(s => '
                       's.Area()); }\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'Console.WriteLine(new Rectangle(2, 3).Area());',
                     'stdin': '',
                     'expected_output': '6\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'Console.WriteLine(Shapes.TotalArea(new List<Shape> { new Circle(1), new Rectangle(1, 1) '
                                  '}).ToString("F3", System.Globalization.CultureInfo.InvariantCulture));',
                     'stdin': '',
                     'expected_output': '4.142\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': 'Console.WriteLine(Shapes.TotalArea(new List<Shape>()));',
                     'stdin': '',
                     'expected_output': '0\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'Grades (Kotlin)',
     'language': 'kotlin',
     'description': 'In Kotlin, write a `data class Student(val name: String, val grades: List<Int>)` with a property\n'
                    '`average` (0.0 when there are no grades), and a function `best(students: List<Student>): String?` '
                    'that returns the\n'
                    'name of the student with the highest average (or `null` for an empty list).',
     'starter_code': 'data class Student(val name: String, val grades: List<Int>)\n'
                     '\n'
                     'fun best(students: List<Student>): String? {\n'
                     '    TODO()\n'
                     '}\n',
     'model_solution': 'data class Student(val name: String, val grades: List<Int>) {\n'
                       '    val average: Double get() = if (grades.isEmpty()) 0.0 else grades.average()\n'
                       '}\n'
                       '\n'
                       'fun best(students: List<Student>): String? = students.maxByOrNull { it.average }?.name\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'println(Student("Ана", listOf(10, 9)).average)',
                     'stdin': '',
                     'expected_output': '9.5\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'println(best(listOf(Student("Ана", listOf(8)), Student("Иво", listOf(10, 9)))))\n'
                                  'println(best(emptyList()))',
                     'stdin': '',
                     'expected_output': 'Иво\nnull\n',
                     'is_hidden': False,
                     'order': 1}]},
    {'title': 'Family Tree (Prolog)',
     'language': 'prolog',
     'description': 'Given facts `parent(Parent, Child)`, write the rules:\n'
                    '\n'
                    '- `grandparent(G, C)` — G is a grandparent of C\n'
                    '- `sibling(A, B)` — A and B share a parent and are different people\n'
                    '- `ancestor(A, D)` — A is a parent, grandparent, great-grandparent... of D\n'
                    '\n'
                    'The facts are in the starter code — keep them.',
     'starter_code': 'parent(vera, ana).\n'
                     'parent(vera, ivo).\n'
                     'parent(ana, lea).\n'
                     'parent(lea, mila).\n'
                     '\n'
                     '% TODO: grandparent/2, sibling/2, ancestor/2\n',
     'model_solution': 'parent(vera, ana).\n'
                       'parent(vera, ivo).\n'
                       'parent(ana, lea).\n'
                       'parent(lea, mila).\n'
                       '\n'
                       'grandparent(G, C) :- parent(G, P), parent(P, C).\n'
                       'sibling(A, B) :- parent(P, A), parent(P, B), A \\== B.\n'
                       'ancestor(A, D) :- parent(A, D).\n'
                       'ancestor(A, D) :- parent(A, X), ancestor(X, D).\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'forall(grandparent(vera, X), (write(X), nl))',
                     'stdin': '',
                     'expected_output': 'lea\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'forall(sibling(ana, X), (write(X), nl))',
                     'stdin': '',
                     'expected_output': 'ivo\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': 'findall(D, ancestor(vera, D), L), msort(L, S), write(S), nl',
                     'stdin': '',
                     'expected_output': '[ana,ivo,lea,mila]\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'List Functions (Common Lisp)',
     'language': 'lisp',
     'description': 'In Common Lisp, write:\n'
                    '\n'
                    '- `(my-reverse lst)` — reverses a list **recursively** (without `reverse`)\n'
                    '- `(count-if-even lst)` — how many elements are even\n'
                    "- `(flatten tree)` — turns a nested list into a flat list, e.g. `(flatten '(1 (2 (3)) 4))` → `(1 2 3 "
                    '4)`',
     'starter_code': '(defun my-reverse (lst)\n  ;; TODO\n  )\n',
     'model_solution': '(defun my-reverse (lst)\n'
                       '  (if (null lst) nil (append (my-reverse (cdr lst)) (list (car lst)))))\n'
                       '\n'
                       '(defun count-if-even (lst)\n'
                       "  (count-if #'evenp lst))\n"
                       '\n'
                       '(defun flatten (tree)\n'
                       '  (cond ((null tree) nil)\n'
                       '        ((atom tree) (list tree))\n'
                       '        (t (append (flatten (car tree)) (flatten (cdr tree))))))\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': '(format t "~a~%" (my-reverse \'(1 2 3)))',
                     'stdin': '',
                     'expected_output': '(3 2 1)\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': '(format t "~a ~a~%" (count-if-even \'(1 2 3 4 6)) (flatten \'(1 (2 (3)) 4)))',
                     'stdin': '',
                     'expected_output': '3 (1 2 3 4)\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': '(format t "~a ~a~%" (my-reverse nil) (flatten \'((()))))',
                     'stdin': '',
                     'expected_output': 'NIL NIL\n',
                     'is_hidden': True,
                     'order': 2}]},
    {'title': 'Array Sum (x86-64 Assembly)',
     'language': 'asm',
     'description': 'Write in x86-64 NASM assembly the function\n'
                    '\n'
                    '```c\n'
                    'long array_sum(long *a, long n);\n'
                    '```\n'
                    '\n'
                    'that returns the sum of the `n` elements of the array `a`. Follow the System V calling convention:\n'
                    '`a` is in `rdi`, `n` in `rsi`, and the result goes in `rax`. Mark it `global array_sum`.',
     'starter_code': 'global array_sum\nsection .text\n\narray_sum:\n    ; TODO\n    ret\n',
     'model_solution': 'global array_sum\n'
                       'section .text\n'
                       '\n'
                       'array_sum:\n'
                       '    xor rax, rax\n'
                       '.loop:\n'
                       '    test rsi, rsi\n'
                       '    jz .done\n'
                       '    add rax, [rdi]\n'
                       '    add rdi, 8\n'
                       '    dec rsi\n'
                       '    jmp .loop\n'
                       '.done:\n'
                       '    ret\n',
     'test_cases': [{'type': 'code_sample',
                     'test_code': 'extern long array_sum(long *a, long n);\n'
                                  'long a[] = {1, 2, 3, 4};\n'
                                  'printf("%ld\\n", array_sum(a, 4));',
                     'stdin': '',
                     'expected_output': '10\n',
                     'is_hidden': False,
                     'order': 0},
                    {'type': 'code_sample',
                     'test_code': 'extern long array_sum(long *a, long n);\n'
                                  'long a[] = {5};\n'
                                  'printf("%ld %ld\\n", array_sum(a, 1), array_sum(a, 0));',
                     'stdin': '',
                     'expected_output': '5 0\n',
                     'is_hidden': False,
                     'order': 1},
                    {'type': 'code_sample',
                     'test_code': 'extern long array_sum(long *a, long n);\n'
                                  'long a[] = {-7, 1000000000000, 3};\n'
                                  'printf("%ld\\n", array_sum(a, 3));',
                     'stdin': '',
                     'expected_output': '999999999996\n',
                     'is_hidden': True,
                     'order': 2}]},
    {
        "title": "Profile Card (HTML/CSS)",
        "description": """Make a **profile card** page in `index.html`, `style.css` and `script.js`.

**Structure** (inside `<div class="card">`):
- an `<h2>` with a name and a `<p class="role">` with a role,
- a list `<ul class="skills">` with **at least 3** `<li>` items,
- a button `<button id="follow">Follow</button>`.

**Style:**
- `.card`: white background, rounded corners of `12px`, at most `320px` wide, centred on the page.
- the button: background `#2747C9`, white text.
- `.skills` shows its items **in a row** (flexbox); on screens narrower than **600px** they go **one under another**.

**Behaviour:** clicking the button changes its text to `Following`; clicking again changes it back to `Follow`.
""",
        "starter_code": """<!-- file: index.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Profile</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <script src="script.js"></script>
</body>
</html>
<!-- file: style.css -->
body {
  font-family: system-ui, sans-serif;
  margin: 0;
}
<!-- file: script.js -->
""",
        "model_solution": """<!-- file: index.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Profile</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="card">
    <h2>Ana Petrova</h2>
    <p class="role">Web developer</p>
    <ul class="skills">
      <li>HTML</li>
      <li>CSS</li>
      <li>JavaScript</li>
    </ul>
    <button id="follow">Follow</button>
  </div>
  <script src="script.js"></script>
</body>
</html>
<!-- file: style.css -->
body {
  font-family: system-ui, sans-serif;
  margin: 0;
  padding: 40px 16px;
  background: #EEF1F5;
}
.card {
  background: #fff;
  border-radius: 12px;
  max-width: 320px;
  margin: 0 auto;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(26, 34, 51, .12);
}
.card h2 { margin: 0; }
.role { color: #6B7488; margin: 4px 0 16px; }
.skills {
  display: flex;
  gap: 8px;
  list-style: none;
  padding: 0;
}
.skills li {
  background: #E8EDFC;
  color: #2747C9;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 14px;
}
#follow {
  background: #2747C9;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 15px;
  cursor: pointer;
}
@media (max-width: 600px) {
  .skills { flex-direction: column; }
}
<!-- file: script.js -->
const btn = document.getElementById('follow');
btn.addEventListener('click', () => {
  btn.textContent = btn.textContent === 'Follow' ? 'Following' : 'Follow';
});
""",
        "language": "web",
        "test_cases": [
            {"type": "code_sample", "test_code": "print(exists('.card h2'), exists('.card .role'), exists('.card #follow'))", "stdin": "", "expected_output": "true true true", "is_hidden": False, "order": 0},
            {"type": "code_sample", "test_code": "print(count('.skills li') >= 3)", "stdin": "", "expected_output": "true", "is_hidden": False, "order": 1},
            {"type": "code_sample", "test_code": "print(hex('#follow', 'background-color'), hex('#follow', 'color'))", "stdin": "", "expected_output": "#2747c9 #ffffff", "is_hidden": False, "order": 2},
            {"type": "code_sample", "test_code": "print(css('.card', 'border-radius'), css('.card', 'max-width'))", "stdin": "", "expected_output": "12px 320px", "is_hidden": False, "order": 3},
            {"type": "code_sample", "test_code": "await click('#follow'); print(text('#follow'))\nawait click('#follow'); print(text('#follow'))", "stdin": "", "expected_output": "Following\nFollow", "is_hidden": False, "order": 4},
            {"type": "code_sample", "test_code": "print(css('.skills', 'display'), css('.skills', 'flex-direction'))", "stdin": "", "expected_output": "flex row", "is_hidden": True, "order": 5},
            {"type": "code_sample", "test_code": "// viewport: 375x667\nprint(css('.skills', 'flex-direction'))", "stdin": "", "expected_output": "column", "is_hidden": True, "order": 6},
            {"type": "code_sample", "test_code": "// visual: 80", "stdin": "", "expected_output": "", "is_hidden": False, "order": 7},
        ],
    },
    {
        "title": "UML класен дијаграм — библиотека",
        "content_lang": "mk",
        "translations": {"en": {"title": "UML class diagram — library", "description": """Draw a **UML class diagram** for a library.

- A **book** (`Книга`) has a title, an ISBN and an author, and a method that says whether it is available.
- A **member** (`Член`) has a name and a card number, and can borrow a book.
- A **loan** (`Позајмица`) has a date and a due date, and a method that says whether it is late.
- A member makes any number of loans; each loan is of exactly one book (a book can be in many loans).
- **Employees** (`Вработен`, abstract) have a name; a **librarian** (`Библиотекар`) is an employee.

Draw it in the editor, or upload a picture / PDF (draw.io, StarUML, a photo of a drawing)."""}},
        "description": """Нацртајте **UML класен дијаграм** за библиотека.

- **Книга** има наслов, ISBN и автор, и метод што кажува дали е достапна.
- **Член** има име и број на членска карта, и може да позајми книга.
- **Позајмица** има датум и рок за враќање, и метод што кажува дали доцни.
- Еден член прави произволен број позајмици; секоја позајмица е за точно една книга (една книга може да биде во многу позајмици).
- **Вработен** (апстрактна класа) има име; **Библиотекар** е вработен.

Нацртајте го во уредувачот или прикачете слика / PDF (draw.io, StarUML, фотографија од цртеж).""",
        "starter_code": "",
        "model_solution": "@diagram:uml:library",
        "language": "uml",
        "test_cases": "@checks",
    },
    {
        "title": "ER дијаграм — база за факултет",
        "content_lang": "mk",
        "translations": {"en": {"title": "ER diagram — faculty database", "description": """Design an **ER diagram** for a faculty database.

- A **student** (`Студент`) is identified by the index number and has a first name, a last name and an e-mail.
- A **course** (`Предмет`) is identified by its code and has a name and a number of credits.
- A **professor** (`Професор`) has an ID and a name.
- A student enrols in many courses and a course has many students (`запишува`).
- Each course is taught by exactly one professor; a professor teaches many courses (`предава`).

Mark the primary keys and the cardinalities (1, N, M)."""}},
        "description": """Дизајнирајте **ER дијаграм** за база на податоци на факултет.

- **Студент** се идентификува со бројот на индекс и има име, презиме и е-пошта.
- **Предмет** се идентификува со шифра и има назив и број на кредити.
- **Професор** има ID и име.
- Студентот запишува многу предмети, а предметот има многу студенти (`запишува`).
- Секој предмет го предава точно еден професор; професорот предава многу предмети (`предава`).

Означете ги примарните клучеви и кардиналностите (1, N, M).""",
        "starter_code": "",
        "model_solution": "@diagram:er:faculty",
        "language": "er",
        "test_cases": "@checks",
    },
    {
        "title": 'Use case дијаграм — студентски сервис',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Use case diagram — student services', "description": 'Draw a **use case diagram** for student services.\n\n- A **student** can *register for an exam* and *view grades*.\n- A **clerk** *enters grades*.\n- Registering for an exam always includes *logging in* (`«include»`).\n- While registering, the student may *pay by card* (`«extend»`).\n- The use cases are inside the system boundary **Student services**.'}},
        "description": 'Нацртајте **use case дијаграм** за студентски сервис.\n\n- **Студентот** може да се *пријави на испит* и да ги *прегледа оценките*.\n- **Референтот** ги *внесува оценките*.\n- Пријавата на испит секогаш вклучува *најава* (`«include»`).\n- При пријавата студентот може (но не мора) да *плати со картичка* (`«extend»`).\n- Случаите на употреба се во границата на системот **Студентски сервис**.',
        "starter_code": "",
        "model_solution": "@diagram:usecase:services",
        "language": "usecase",
        "test_cases": "@checks",
    },
    {
        "title": 'State дијаграм — нарачка',
        "content_lang": "mk",
        "translations": {"en": {"title": 'State machine — an order', "description": 'Draw a **state machine** for an order in an online shop.\n\n- A new order is **New** (`Нова`).\n- The event *pay* (`плати`) takes it to **Paid** (`Платена`, on entry a confirmation is sent); *cancel* (`откажи`) to **Cancelled** (`Откажана`).\n- *ship* (`испрати`) makes a paid order **Shipped** (`Испратена`); *deliver* (`достави`) — **Delivered** (`Доставена`).\n- Delivered and cancelled orders end (final state).'}},
        "description": 'Нацртајте **дијаграм на состојби** за нарачка во онлајн продавница.\n\n- Новата нарачка е во состојба **Нова**.\n- Со настанот *плати* преминува во **Платена** (при влез се *испраќа потврда*), а со *откажи* во **Откажана**.\n- Платената нарачка со *испрати* станува **Испратена**, а со *достави* — **Доставена**.\n- Доставена и откажана нарачка завршуваат (крајна состојба).',
        "starter_code": "",
        "model_solution": "@diagram:state:order",
        "language": "state",
        "test_cases": "@checks",
    },
    {
        "title": 'Sequence дијаграм — најава',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Sequence diagram — logging in', "description": 'Draw a **sequence diagram** of logging in to the student services.\n\nParticipants: the actor **User** (`Корисник`) and the objects **:LoginForm** (`:ФормаЗаНајава`), **:Controller** (`:Контролер`) and **:UserDatabase** (`:БазаНаКорисници`).\n\n1. The user *enters* (`внеси(корисник, лозинка)`) the user name and password in the form.\n2. The form asks the controller to *log in* (`најави(корисник, лозинка)`).\n3. The controller *finds* the user in the database (`најди(корисник)`); the database replies with the user (`корисник`).\n4. The controller *checks the password* itself (`провериЛозинка()`).\n5. The controller replies *success* (`успех`) to the form, and the form *shows the home page* to the user (`прикажиПочетна()`).'}},
        "description": 'Нацртајте **sequence дијаграм** за најава во студентски сервис.\n\nУчесници: актерот **Корисник** и објектите **:ФормаЗаНајава**, **:Контролер** и **:БазаНаКорисници**.\n\n1. Корисникот *внесува* корисничко име и лозинка во формата — `внеси(корисник, лозинка)`.\n2. Формата бара од контролерот да го *најави* — `најави(корисник, лозинка)`.\n3. Контролерот го *бара* корисникот во базата — `најди(корисник)`; базата враќа одговор `корисник`.\n4. Контролерот сам ја *проверува лозинката* — `провериЛозинка()`.\n5. Контролерот ѝ одговара `успех` на формата, а формата на корисникот му ја *прикажува почетната страница* — `прикажиПочетна()`.',
        "starter_code": "",
        "model_solution": "@diagram:sequence:login",
        "language": "sequence",
        "test_cases": "@checks",
    },
    {
        "title": 'Activity дијаграм — банкомат',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Activity diagram — ATM withdrawal', "description": 'Draw an **activity diagram** for withdrawing money from an ATM.\n\n1. The user *inserts the card* (`Внеси картичка`), then *enters the PIN* (`Внеси PIN`).\n2. Decision **PIN correct?** (`PIN точен?`) — if not, the PIN is entered again; if yes, the user *chooses the amount* (`Избери износ`).\n3. Then in parallel (fork/join): *pay out* (`Исплати пари`) and *print a receipt* (`Испечати потврда`).\n4. Finally *return the card* (`Врати картичка`).'}},
        "description": 'Нацртајте **activity дијаграм** за подигање пари од банкомат.\n\n1. Корисникот *внесува картичка*, па *внесува PIN*.\n2. Одлука **PIN точен?** — ако не, повторно се внесува PIN; ако да, *избира износ*.\n3. Потоа паралелно (fork/join): *исплата на пари* и *печатење потврда*.\n4. На крај *враќање на картичката*.',
        "starter_code": "",
        "model_solution": "@diagram:activity:atm",
        "language": "activity",
        "test_cases": "@checks",
    },
    {
        "title": 'Компонентен дијаграм — онлајн продавница',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Component diagram — online shop', "description": 'Draw a **component diagram** for an online shop.\n\n- **Web app** (`Веб апликација`) uses **Order service** (`Сервис за нарачки`).\n- **Payment service** (`Сервис за плаќање`) provides the interface **IPayment** (`IПлаќање`).\n- **Order service** requires **IPayment**.'}},
        "description": 'Нацртајте **компонентен дијаграм** за онлајн продавница.\n\n- Компонентата **Веб апликација** ја користи компонентата **Сервис за нарачки**.\n- **Сервис за плаќање** го нуди интерфејсот **IПлаќање** (реализација).\n- **Сервис за нарачки** го користи интерфејсот **IПлаќање** (зависност).',
        "starter_code": "",
        "model_solution": "@diagram:component:shop",
        "language": "component",
        "test_cases": "@checks",
    },
    {
        "title": 'Пакетен дијаграм — слоевита апликација',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Package diagram — layered application', "description": 'Draw a **package diagram** for a three-layer application.\n\n- **Presentation** (`Презентација`) contains *Controllers* and *Views*.\n- **Business logic** (`Бизнис логика`) contains *Services*.\n- **Data access** (`Пристап до податоци`) contains *Repositories*.\n- Presentation depends on business logic; business logic *imports* (`«import»`) data access.'}},
        "description": 'Нацртајте **пакетен дијаграм** за апликација во три слоја.\n\n- Пакетот **Презентација** ги содржи *Контролери* и *Погледи*.\n- Пакетот **Бизнис логика** ги содржи *Сервиси*.\n- Пакетот **Пристап до податоци** ги содржи *Репозиториуми*.\n- Презентацијата зависи од бизнис логиката, а бизнис логиката го *увезува* (`«import»`) пристапот до податоци.',
        "starter_code": "",
        "model_solution": "@diagram:package:layers",
        "language": "package",
        "test_cases": "@checks",
    },
    {
        "title": 'Deployment дијаграм — веб систем',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Deployment diagram — web system', "description": "Draw a **deployment diagram** for a web system.\n\n- The **user's computer** (`Компјутер на корисник`, a device with a browser) talks to the **Web server** (`Веб сервер`) over *HTTPS*.\n- The web server talks to the **Application server** (`Апликациски сервер`) over *HTTP*.\n- The application server talks to the **Database server** (`Сервер за бази`) over *JDBC*.\n- The artifact **app.jar** is deployed (`«deploy»`) on the application server."}},
        "description": 'Нацртајте **deployment дијаграм** за веб систем.\n\n- **Компјутерот на корисникот** (уред, со прелистувач) комуницира со **Веб сервер** преку *HTTPS*.\n- Веб серверот комуницира со **Апликациски сервер** преку *HTTP*.\n- Апликацискиот сервер комуницира со **Сервер за бази** преку *JDBC*.\n- Артефактот **app.jar** е распореден (`«deploy»`) на апликацискиот сервер.',
        "starter_code": "",
        "model_solution": "@diagram:deployment:web",
        "language": "deployment",
        "test_cases": "@checks",
    },
    {
        "title": 'Релациона шема — библиотека',
        "content_lang": "mk",
        "translations": {"en": {"title": 'Relational schema — library', "description": 'Draw a **relational schema** for a library.\n\n- **Member** (`Член`)(id, name, email) — primary key *id*.\n- **Book** (`Книга`)(isbn, title, author) — primary key *isbn*.\n- **Loan** (`Позајмица`)(id, член_id, книга_isbn, date) — primary key *id*; *член_id* is a foreign key to Member, *книга_isbn* to Book.'}},
        "description": 'Нацртајте **релациона шема** за библиотека.\n\n- **Член**(id, име, email) — примарен клуч *id*.\n- **Книга**(isbn, наслов, автор) — примарен клуч *isbn*.\n- **Позајмица**(id, член_id, книга_isbn, датум) — примарен клуч *id*; *член_id* е надворешен клуч кон Член, *книга_isbn* кон Книга.',
        "starter_code": "",
        "model_solution": "@diagram:relational:library",
        "language": "relational",
        "test_cases": "@checks",
    },
]


def _attr(name, typ="", vis="-", pk=False, aliases=()):
    return {"name": name, "type": typ, "visibility": vis, "pk": pk, "fk": False, **({"aliases": list(aliases)} if aliases else {})}


SAMPLE_DIAGRAMS = {
    "uml:library": {"kind": "uml", "nodes": [
        {"id": "kniga", "name": "Книга", "aliases": ["Book"], "type": "class", "x": 40, "y": 40,
         "attributes": [_attr("наслов", "String", aliases=["title"]), _attr("isbn", "String"), _attr("автор", "String", aliases=["author"])],
         "methods": [{"name": "достапна", "params": "", "returns": "boolean", "visibility": "+"}]},
        {"id": "clen", "name": "Член", "aliases": ["Member"], "type": "class", "x": 620, "y": 40,
         "attributes": [_attr("име", "String", aliases=["name"]), _attr("бројНаКарта", "int", aliases=["cardNumber", "brojKarta"])],
         "methods": [{"name": "позајми", "params": "к: Книга", "returns": "Позајмица", "visibility": "+"}]},
        {"id": "pozajmica", "name": "Позајмица", "aliases": ["Loan"], "type": "class", "x": 330, "y": 300,
         "attributes": [_attr("датум", "Date", aliases=["date"]), _attr("рок", "Date", aliases=["dueDate", "rokZaVrakjanje"])],
         "methods": [{"name": "доцни", "params": "", "returns": "boolean", "visibility": "+"}]},
        {"id": "vraboten", "name": "Вработен", "aliases": ["Employee"], "type": "abstract", "x": 40, "y": 520,
         "attributes": [_attr("име", "String", "#", aliases=["name"])], "methods": []},
        {"id": "bibliotekar", "name": "Библиотекар", "aliases": ["Librarian"], "type": "class", "x": 620, "y": 560,
         "attributes": [], "methods": []}],
     "edges": [
        {"id": "e1", "from": "clen", "to": "pozajmica", "kind": "association", "fromMult": "1", "toMult": "0..*", "label": "прави"},
        {"id": "e2", "from": "pozajmica", "to": "kniga", "kind": "association", "fromMult": "0..*", "toMult": "1", "label": "за"},
        {"id": "e3", "from": "bibliotekar", "to": "vraboten", "kind": "inheritance", "fromMult": "", "toMult": "", "label": ""}]},
    "er:faculty": {"kind": "er", "nodes": [
        {"id": "student", "name": "Студент", "aliases": ["Student"], "type": "entity", "x": 40, "y": 60,
         "attributes": [_attr("индекс", pk=True, aliases=["index", "brIndeks"]), _attr("име", aliases=["ime", "firstName"]),
                        _attr("презиме", aliases=["prezime", "lastName"]), _attr("email", aliases=["е-пошта", "eposta"])], "methods": []},
        {"id": "predmet", "name": "Предмет", "aliases": ["Course", "Subject"], "type": "entity", "x": 560, "y": 60,
         "attributes": [_attr("шифра", pk=True, aliases=["code", "sifra"]), _attr("назив", aliases=["name", "naziv"]),
                        _attr("кредити", aliases=["credits", "ects"])], "methods": []},
        {"id": "profesor", "name": "Професор", "aliases": ["Professor"], "type": "entity", "x": 560, "y": 380,
         "attributes": [_attr("id", pk=True), _attr("име", aliases=["name", "ime"])], "methods": []}],
     "edges": [
        {"id": "r1", "from": "student", "to": "predmet", "kind": "relationship", "fromMult": "N", "toMult": "M", "label": "запишува"},
        {"id": "r2", "from": "profesor", "to": "predmet", "kind": "relationship", "fromMult": "1", "toMult": "N", "label": "предава"}]},
}


def _n(id, name, typ, x, y, attrs=(), aliases=(), **extra):
    return {"id": id, "name": name, "type": typ, "x": x, "y": y, "attributes": list(attrs), "methods": [],
            **({"aliases": list(aliases)} if aliases else {}), **extra}


def _e(id, a, b, kind, label="", fm="", tm=""):
    return {"id": id, "from": a, "to": b, "kind": kind, "fromMult": fm, "toMult": tm, "label": label}


SAMPLE_DIAGRAMS.update({
    "usecase:services": {"kind": "usecase", "nodes": [
        _n("sys", "Студентски сервис", "system", 220, 20, aliases=["Student services"], w=620, h=470),
        _n("st", "Студент", "actor", 60, 120, aliases=["Student"]),
        _n("ref", "Референт", "actor", 60, 360, aliases=["Clerk", "Referent"]),
        _n("prij", "Пријава на испит", "usecase", 300, 80, aliases=["Register for an exam", "Exam registration"]),
        _n("naj", "Најава", "usecase", 620, 80, aliases=["Log in", "Login"]),
        _n("kart", "Плаќање со картичка", "usecase", 520, 220, aliases=["Pay by card"]),
        _n("pregled", "Преглед на оценки", "usecase", 300, 300, aliases=["View grades"]),
        _n("vnes", "Внес на оценки", "usecase", 300, 400, aliases=["Enter grades"])],
     "edges": [_e("e1", "st", "prij", "association"), _e("e2", "st", "pregled", "association"),
               _e("e3", "ref", "vnes", "association"), _e("e4", "prij", "naj", "include"),
               _e("e5", "kart", "prij", "extend")]},
    "sequence:login": {"kind": "sequence", "nodes": [
        _n("k", "Корисник", "actor", 40, 40, aliases=["User"]),
        _n("f", ":ФормаЗаНајава", "lifeline", 240, 40, aliases=[":LoginForm", "ФормаЗаНајава"]),
        _n("c", ":Контролер", "lifeline", 460, 40, aliases=[":Controller", "Контролер"]),
        _n("b", ":БазаНаКорисници", "lifeline", 680, 40, aliases=[":UserDatabase", "БазаНаКорисници"])],
     "edges": [{**_e("m1", "k", "f", "sync", "внеси(корисник, лозинка)"), "y": 130},
               {**_e("m2", "f", "c", "sync", "најави(корисник, лозинка)"), "y": 180},
               {**_e("m3", "c", "b", "sync", "најди(корисник)"), "y": 230},
               {**_e("m4", "b", "c", "reply", "корисник"), "y": 280},
               {**_e("m5", "c", "c", "sync", "провериЛозинка()"), "y": 330},
               {**_e("m6", "c", "f", "reply", "успех"), "y": 390},
               {**_e("m7", "f", "k", "sync", "прикажиПочетна()"), "y": 440}]},
    "state:order": {"kind": "state", "nodes": [
        _n("i", "", "initial", 140, 20),
        _n("nova", "Нова", "state", 80, 100, aliases=["New"]),
        _n("plat", "Платена", "state", 80, 260, [_attr("entry / испрати потврда", vis="")], aliases=["Paid"]),
        _n("otk", "Откажана", "state", 400, 100, aliases=["Cancelled", "Canceled"]),
        _n("ispr", "Испратена", "state", 80, 420, aliases=["Shipped"]),
        _n("dost", "Доставена", "state", 80, 560, aliases=["Delivered"]),
        _n("f", "", "final", 440, 590)],
     "edges": [_e("t0", "i", "nova", "transition"), _e("t1", "nova", "plat", "transition", "плати"),
               _e("t2", "nova", "otk", "transition", "откажи"), _e("t3", "plat", "ispr", "transition", "испрати"),
               _e("t4", "ispr", "dost", "transition", "достави"), _e("t5", "dost", "f", "transition"),
               _e("t6", "otk", "f", "transition")]},
    "activity:atm": {"kind": "activity", "nodes": [
        _n("i", "", "initial", 180, 20),
        _n("kart", "Внеси картичка", "action", 100, 80, aliases=["Insert card"]),
        _n("pin", "Внеси PIN", "action", 100, 180, aliases=["Enter PIN"]),
        _n("dec", "PIN точен?", "decision", 140, 280, aliases=["PIN correct?"]),
        _n("iznos", "Избери износ", "action", 100, 380, aliases=["Choose amount"]),
        _n("fork", "", "fork", 60, 480),
        _n("isplata", "Исплати пари", "action", 0, 540, aliases=["Pay out", "Dispense cash"]),
        _n("potvrda", "Испечати потврда", "action", 240, 540, aliases=["Print receipt"]),
        _n("join", "", "join", 60, 640),
        _n("vrati", "Врати картичка", "action", 100, 700, aliases=["Return card"]),
        _n("f", "", "final", 180, 800)],
     "edges": [_e("f0", "i", "kart", "flow"), _e("f1", "kart", "pin", "flow"), _e("f2", "pin", "dec", "flow"),
               _e("f3", "dec", "iznos", "flow", "[да]"), _e("f4", "dec", "pin", "flow", "[не]"),
               _e("f5", "iznos", "fork", "flow"), _e("f6", "fork", "isplata", "flow"), _e("f7", "fork", "potvrda", "flow"),
               _e("f8", "isplata", "join", "flow"), _e("f9", "potvrda", "join", "flow"), _e("f10", "join", "vrati", "flow"),
               _e("f11", "vrati", "f", "flow")]},
    "component:shop": {"kind": "component", "nodes": [
        _n("web", "Веб апликација", "component", 40, 60, aliases=["Web app", "Web application"]),
        _n("nar", "Сервис за нарачки", "component", 360, 60, aliases=["Order service"]),
        _n("ipl", "IПлаќање", "interface", 400, 260, aliases=["IPayment", "IPlakjanje"]),
        _n("pl", "Сервис за плаќање", "component", 360, 400, aliases=["Payment service"])],
     "edges": [_e("d1", "web", "nar", "dependency"), _e("d2", "nar", "ipl", "dependency"), _e("r1", "pl", "ipl", "realization")]},
    "package:layers": {"kind": "package", "nodes": [
        _n("pres", "Презентација", "package", 60, 40, [_attr("Контролери", vis="", aliases=["Controllers"]), _attr("Погледи", vis="", aliases=["Views"])],
           aliases=["Presentation"], w=240, h=130),
        _n("biz", "Бизнис логика", "package", 60, 260, [_attr("Сервиси", vis="", aliases=["Services"])], aliases=["Business logic"], w=240, h=110),
        _n("dao", "Пристап до податоци", "package", 60, 460, [_attr("Репозиториуми", vis="", aliases=["Repositories"])],
           aliases=["Data access"], w=240, h=110)],
     "edges": [_e("p1", "pres", "biz", "dependency"), _e("p2", "biz", "dao", "import")]},
    "deployment:web": {"kind": "deployment", "nodes": [
        _n("pc", "Компјутер на корисник", "device", 20, 40, [_attr("Прелистувач", vis="", aliases=["Browser"])], aliases=["User computer", "Client"], w=230, h=110),
        _n("web", "Веб сервер", "node", 330, 40, [_attr("Nginx", vis="")], aliases=["Web server"], w=200, h=110),
        _n("app", "Апликациски сервер", "node", 330, 260, aliases=["Application server", "App server"], w=200, h=110),
        _n("db", "Сервер за бази", "node", 330, 480, aliases=["Database server", "DB server"], w=200, h=110),
        _n("jar", "app.jar", "artifact", 40, 280)],
     "edges": [_e("c1", "pc", "web", "association", "HTTPS"), _e("c2", "web", "app", "association", "HTTP"),
               _e("c3", "app", "db", "association", "JDBC"), _e("c4", "jar", "app", "deploy")]},
    "relational:library": {"kind": "relational", "nodes": [
        _n("clen", "Член", "table", 40, 40, [_attr("id", "INT", pk=True), _attr("име", "VARCHAR", aliases=["ime", "name"]),
                                           _attr("email", "VARCHAR")], aliases=["Member", "clen"]),
        _n("kniga", "Книга", "table", 560, 40, [_attr("isbn", "VARCHAR", pk=True), _attr("наслов", "VARCHAR", aliases=["naslov", "title"]),
                                              _attr("автор", "VARCHAR", aliases=["avtor", "author"])], aliases=["Book"]),
        _n("poz", "Позајмица", "table", 300, 300, [_attr("id", "INT", pk=True), {**_attr("член_id", "INT", aliases=["clen_id", "member_id"]), "fk": True},
                                                 {**_attr("книга_isbn", "VARCHAR", aliases=["kniga_isbn", "book_isbn"]), "fk": True},
                                                 _attr("датум", "DATE", aliases=["datum", "date"])], aliases=["Loan"])],
     "edges": [_e("k1", "poz", "clen", "foreign_key", fm="N", tm="1"), _e("k2", "poz", "kniga", "foreign_key", fm="N", tm="1")]},
})


def _web_tasks():
    """The sample web tasks (app/data/web_tasks.py) in the form of SAMPLE_TASKS."""
    from app.data.web_tasks import WEB_TASKS
    return [{"title": w["title"], "description": w["description"], "starter_code": w["starter_code"],
             "model_solution": w["model_solution"], "language": "web", "content_lang": "mk",
             "translations": w["translations"], "subject": w["subject"],
             "test_cases": [{**tc, "order": i} for i, tc in enumerate(w["tests"])]} for w in WEB_TASKS]


SAMPLE_TASKS.extend(_web_tasks())


def _devops_tasks():
    """DevOps tasks (app/data/devops_tasks.py): Git, Bash, Dockerfile, YAML, Terraform."""
    from app.data.devops_tasks import DEVOPS, DEVOPS_TASKS
    return [{"title": d["title"], "description": d["description"], "starter_code": d["starter_code"],
             "model_solution": d["model_solution"], "language": d["language"], "content_lang": "mk",
             "translations": d["translations"], "subject": DEVOPS,
             "test_cases": [{**tc, "order": i} for i, tc in enumerate(d["tests"])]} for d in DEVOPS_TASKS]


SAMPLE_TASKS.extend(_devops_tasks())


def _diagram_task(task_data):
    """Sample diagram tasks: the model solution is one of SAMPLE_DIAGRAMS; the tests are made from it."""
    from app.services import diagrams
    key = task_data["model_solution"].split(":", 1)[1]
    d = diagrams.parse(SAMPLE_DIAGRAMS[key], SAMPLE_DIAGRAMS[key]["kind"])
    checks = diagrams.generate_checks(d, task_data.get("content_lang", "en"), methods=d["kind"] == "uml")
    hidden = {len(checks) - 1, len(checks) - 2}  # the last two (relationships) are hidden
    return diagrams.dump(d), [{"type": "diagram", "test_code": c["test_code"], "stdin": "", "expected_output": c["expected_output"],
                               "is_hidden": i in hidden, "order": i} for i, c in enumerate(checks)]


async def merge_finki_catalogue(db, have: dict):
    """Once: the whole FINKI catalogue (app/data/finki_subjects.csv). Known subjects get their FINKI code and
    recommended semester; the others are added. Later the admin edits subjects — a deleted one is not brought back."""
    from app.data.subjects import FINKI_CODE, finki_catalogue
    from app.models.task import Subject
    if (await db.execute(select(Subject.id).where(Subject.finki_code.is_not(None)).limit(1))).first():
        return
    by_finki = {fc: have[c] for c, fc in FINKI_CODE.items() if c in have}
    taken = set(have)
    pos = max([s.position for s in have.values()] + [0])
    for row in finki_catalogue():
        s = by_finki.get(row["code"])
        if s is not None:
            s.finki_code, s.semester, s.elective = row["code"], row["semester"], row["elective"]
            continue
        if row["code"] in taken:
            continue
        pos += 1
        s = Subject(id=uuid.uuid4(), code=row["code"], finki_code=row["code"], name=row["name"], name_en=row["name_en"],
                    semester=row["semester"], elective=row["elective"], languages=row["languages"], icon=row["icon"],
                    color=row["color"], position=pos)
        db.add(s)
        have[row["code"]] = s
    await db.flush()


async def seed_subjects(db):
    """FINKI subjects (app/data/subjects.py), added the first time (later the admin edits them); tasks without a
    subject get the one for their language. Courses are never changed."""
    from app.data.subjects import SUBJECTS, DEFAULT_FOR
    from app.models.task import Subject
    have = {x.code: x for x in (await db.execute(select(Subject))).scalars()}
    if not have:
        for pos, (code, name, name_en, sem, langs, icon, color) in enumerate(SUBJECTS):
            have[code] = Subject(id=uuid.uuid4(), code=code, name=name, name_en=name_en, semester=sem, languages=langs,
                                 icon=icon, color=color, position=pos, elective=sem is None)
            db.add(have[code])
        await db.flush()
    await merge_finki_catalogue(db, have)
    unsorted = (await db.execute(select(Task).where(Task.subject_id.is_(None), Task.generated_for.is_(None)))).scalars().all()
    for t in unsorted:
        code = DEFAULT_FOR.get(t.language)
        if code in have:
            t.subject_id = have[code].id


async def seed():
    async with AsyncSessionLocal() as db:
        # Admin user
        result = await db.execute(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                id=uuid.uuid4(),
                email=settings.FIRST_ADMIN_EMAIL,
                password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
                name=settings.FIRST_ADMIN_NAME,
                role="admin",
            )
            db.add(admin)
            await db.flush()
            print(f"Created admin: {admin.email}")

        await seed_subjects(db)
        from app.models.task import Subject
        subject_ids = {x.code: x.id for x in (await db.execute(select(Subject))).scalars()}

        # Sample tasks
        for task_data in SAMPLE_TASKS:
            existing = await db.execute(select(Task).where(Task.title == task_data["title"]))
            if existing.scalar_one_or_none():
                continue

            model_solution, test_cases = task_data["model_solution"], task_data["test_cases"]
            if model_solution.startswith("@diagram:"):
                model_solution, test_cases = _diagram_task(task_data)
            task = Task(
                id=uuid.uuid4(),
                title=task_data["title"],
                description=task_data["description"],
                starter_code=task_data["starter_code"],
                model_solution=model_solution,
                language=task_data["language"],
                created_by=admin.id,
                content_lang=task_data.get("content_lang", "en"),
                translations=task_data.get("translations") or ({"mk": MK[task_data["title"]]} if task_data["title"] in MK else {}),
                subject_id=subject_ids.get(task_data.get("subject")),
            )
            db.add(task)
            await db.flush()

            for tc_data in test_cases:
                tc = TestCase(
                    id=uuid.uuid4(),
                    task_id=task.id,
                    type=tc_data["type"],
                    test_code=tc_data["test_code"],
                    stdin=tc_data["stdin"],
                    expected_output=tc_data["expected_output"],
                    is_hidden=tc_data["is_hidden"],
                    order=tc_data["order"],
                )
                db.add(tc)

            print(f"Created task: {task.title}")

        await seed_subjects(db)
        from app.services import spaces
        await db.flush()
        made = await spaces.ensure_all(db)      # every subject has its space (labs, points, materials…)
        await spaces.sync_students(db)
        await db.commit()
        print(f"Seeding complete ({made} new subject spaces).")


if __name__ == "__main__":
    asyncio.run(seed())
