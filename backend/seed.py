"""Seed initial admin user and sample tasks. Idempotent — safe to run multiple times."""
import asyncio
import uuid
from sqlalchemy import select
from app.database import AsyncSessionLocal
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
]


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

        # Sample tasks
        for task_data in SAMPLE_TASKS:
            existing = await db.execute(select(Task).where(Task.title == task_data["title"]))
            if existing.scalar_one_or_none():
                continue

            task = Task(
                id=uuid.uuid4(),
                title=task_data["title"],
                description=task_data["description"],
                starter_code=task_data["starter_code"],
                model_solution=task_data["model_solution"],
                language=task_data["language"],
                created_by=admin.id,
            )
            db.add(task)
            await db.flush()

            for tc_data in task_data["test_cases"]:
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

        await db.commit()
        print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
