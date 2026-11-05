/**
 * Programming languages a task can use. Each language has its own highlighter colour ("marker"):
 * the marker still means "you are here" everywhere, its colour tells you which language you are in.
 * The colours are applied with the CSS class `lang-<id>` (see index.css), which sets --marker variables.
 */
import type { DiagramKind } from './diagram'

export type ProgLang =
  | 'cpp' | 'c' | 'java' | 'python' | 'javascript' | 'sql'
  | 'postgresql' | 'typescript' | 'php' | 'bash' | 'csharp' | 'kotlin' | 'prolog' | 'lisp' | 'asm' | 'web' | 'uml' | 'er'
  | 'usecase' | 'state' | 'activity' | 'component' | 'package' | 'deployment' | 'relational' | 'sequence'
  | 'git' | 'dockerfile' | 'yaml' | 'terraform'
export type TaskKind = 'function' | 'program' | 'query'

interface LangInfo {
  label: string
  monaco: string
  /** File name shown above the editor. */
  file: (kind: TaskKind) => string
  /** Placeholder for a test snippet in the admin form. */
  snippetPlaceholder: string
  /** Outputs are result tables (SQL): shown as tables, tests only have "test data" code. */
  tables?: boolean
  /** Several files (HTML/CSS/JS) in one text, with a live preview; tests run in a browser. */
  web?: boolean
  /** A diagram drawn in the diagram editor (kept as JSON); tests are checks of the drawing. */
  diagram?: DiagramKind
}

function diagramLang(label: string, snippetPlaceholder: string, diagram: DiagramKind): LangInfo {
  return { label, monaco: 'json', file: () => 'diagram', snippetPlaceholder, diagram }
}

export const PROG_LANGS: Record<ProgLang, LangInfo> = {
  cpp: {
    label: 'C++',
    monaco: 'cpp',
    file: () => 'solution.cpp',
    snippetPlaceholder: 'Stack s;\ns.push(1);\ncout << s.top() << endl;',
  },
  c: {
    label: 'C',
    monaco: 'c',
    file: () => 'solution.c',
    snippetPlaceholder: 'printf("%d\\n", sum(2, 3));',
  },
  java: {
    label: 'Java',
    monaco: 'java',
    file: (kind) => (kind === 'program' ? 'Main.java' : 'Solution.java'),
    snippetPlaceholder: 'BankAccount a = new BankAccount("Ana", 100);\nSystem.out.println(a);',
  },
  python: {
    label: 'Python',
    monaco: 'python',
    file: () => 'solution.py',
    snippetPlaceholder: 'print(word_frequency("a b a"))',
  },
  javascript: {
    label: 'JavaScript',
    monaco: 'javascript',
    file: () => 'solution.js',
    snippetPlaceholder: 'console.log(isPalindrome("Ana"));',
  },
  sql: {
    label: 'SQL',
    monaco: 'sql',
    file: () => 'query.sql',
    snippetPlaceholder:
      "CREATE TABLE student (id INTEGER PRIMARY KEY, ime TEXT);\nINSERT INTO student VALUES (1, 'Ана'), (2, 'Марко');\n-- ordered   (optional: row order matters)\n-- check     (optional: what follows runs after the student's INSERT/UPDATE/DELETE)",
    tables: true,
  },
  postgresql: {
    label: 'PostgreSQL',
    monaco: 'pgsql',
    file: () => 'query.sql',
    snippetPlaceholder: "CREATE TABLE student (id SERIAL PRIMARY KEY, ime TEXT);\nINSERT INTO student (ime) VALUES ('Ана'), ('Марко');\n-- ordered   (optional: row order matters)\n-- check     (optional: what follows runs after the student's INSERT/UPDATE/DELETE)",
    tables: true,
  },
  typescript: {
    label: 'TypeScript',
    monaco: 'typescript',
    file: () => 'solution.ts',
    snippetPlaceholder: "const s = new Stack<number>();\ns.push(1);\nconsole.log(s.pop());",
  },
  php: {
    label: 'PHP',
    monaco: 'php',
    file: () => 'solution.php',
    snippetPlaceholder: "echo countWords(\"a b a\")[\"a\"], \"\\n\";",
  },
  bash: {
    label: 'Bash',
    monaco: 'shell',
    file: () => 'solution.sh',
    snippetPlaceholder: "greet Ана",
  },
  git: {
    label: 'Git',
    monaco: 'shell',
    file: () => 'commands.sh',
    snippetPlaceholder: "git log --oneline | wc -l\ngit branch --show-current",
  },
  dockerfile: {
    label: 'Dockerfile',
    monaco: 'dockerfile',
    file: () => 'Dockerfile',
    snippetPlaceholder: "assert stages()[-1].startswith('python:3.12'), 'the image is python:3.12-…'\nassert user() not in (None, 'root'), 'run as a non-root user'",
  },
  yaml: {
    label: 'YAML',
    monaco: 'yaml',
    file: () => 'config.yaml',
    snippetPlaceholder: "assert get(y, 'jobs.test.runs-on') == 'ubuntu-latest'\nassert 'pytest' in ' '.join(find(y, 'run'))",
  },
  terraform: {
    label: 'Terraform',
    monaco: 'hcl',
    file: () => 'main.tf',
    snippetPlaceholder: "b = resource('aws_s3_bucket', 'logs')\nassert b['bucket'] == 'ale-logs'\nassert block(resource('aws_s3_bucket_versioning', 'logs'), 'versioning_configuration')['status'] == 'Enabled'",
  },
  csharp: {
    label: 'C#',
    monaco: 'csharp',
    file: (kind) => (kind === 'program' ? 'Program.cs' : 'Solution.cs'),
    snippetPlaceholder: "Console.WriteLine(new Rectangle(2, 3).Area());",
  },
  kotlin: {
    label: 'Kotlin',
    monaco: 'kotlin',
    file: (kind) => (kind === 'program' ? 'Main.kt' : 'Solution.kt'),
    snippetPlaceholder: "println(best(listOf(Student(\"Ана\", listOf(10)))))",
  },
  prolog: {
    label: 'Prolog',
    monaco: 'plaintext',
    file: () => 'solution.pl',
    snippetPlaceholder: "forall(grandparent(vera, X), (write(X), nl))",
  },
  lisp: {
    label: 'Lisp',
    monaco: 'scheme',
    file: () => 'solution.lisp',
    snippetPlaceholder: "(format t \"~a~%\" (my-reverse '(1 2 3)))",
  },
  asm: {
    label: 'Assembly',
    monaco: 'plaintext',
    file: () => 'solution.asm',
    snippetPlaceholder: "extern long array_sum(long *a, long n);\nlong a[] = {1, 2, 3};\nprintf(\"%ld\\n\", array_sum(a, 3));",
  },
  web: {
    label: 'HTML/CSS',
    monaco: 'html',
    file: () => 'index.html',
    snippetPlaceholder: "print(count('nav a'))\n// or: print(hex('h1', 'color'))   await click('#add'); print(count('li'))\n// first line '// viewport: 375x667' = phone width;  '// visual: 90' = looks ≥ 90 % like the model solution",
    web: true,
  },
  uml: {
    label: 'UML',
    monaco: 'json',
    file: () => 'diagram',
    snippetPlaceholder: '{"check": "attribute", "node": "Книга", "name": "isbn"}',
    diagram: 'uml',
  },
  er: {
    label: 'ER',
    monaco: 'json',
    file: () => 'diagram',
    snippetPlaceholder: '{"check": "relation", "a": "Студент", "b": "Предмет", "kind": "relationship", "mult_a": "N", "mult_b": "M"}',
    diagram: 'er',
  },
  usecase: diagramLang('Use case', '{"check": "relation", "a": "Студент", "b": "Пријава на испит", "kind": "association"}', 'usecase'),
  state: diagramLang('State', '{"check": "relation", "a": "Нова", "b": "Платена", "kind": "transition", "label": "плати"}', 'state'),
  activity: diagramLang('Activity', '{"check": "path", "a": "@initial", "b": "Исплати пари"}', 'activity'),
  component: diagramLang('Component', '{"check": "relation", "a": "Сервис за плаќање", "b": "IПлаќање", "kind": "realization"}', 'component'),
  package: diagramLang('Package', '{"check": "relation", "a": "Презентација", "b": "Бизнис логика", "kind": "dependency"}', 'package'),
  deployment: diagramLang('Deployment', '{"check": "relation", "a": "app.jar", "b": "Апликациски сервер", "kind": "deploy"}', 'deployment'),
  sequence: diagramLang('Sequence', '{"check": "order", "first": {"a": "Корисник", "b": ":Форма", "label": "внеси()"}, "then": {"a": ":Форма", "b": ":Контролер", "label": "најави()"}}', 'sequence'),
  relational: diagramLang('Relational', '{"check": "attribute", "node": "Позајмица", "name": "член_id", "fk": true}', 'relational'),
}

export const LANG_ORDER: ProgLang[] = [
  'cpp', 'c', 'java', 'python', 'javascript', 'typescript', 'csharp', 'kotlin', 'php',
  'sql', 'postgresql', 'bash', 'git', 'dockerfile', 'yaml', 'terraform', 'prolog', 'lisp', 'asm', 'web', 'uml', 'er',
  'usecase', 'sequence', 'state', 'activity', 'component', 'package', 'deployment', 'relational',
]

export function langInfo(id: string): LangInfo {
  return PROG_LANGS[(id as ProgLang)] ?? PROG_LANGS.cpp
}

export function langClass(id: string): string {
  return `lang-${id in PROG_LANGS ? id : 'cpp'}`
}

/** SQL tasks are "query" tasks; otherwise a task is a "program" task when every test feeds stdin to a whole program. */
export function taskKind(tests: { type: string }[], language?: string): TaskKind {
  if (language === 'sql' || language === 'postgresql') return 'query'
  return tests.length > 0 && tests.every((t) => t.type === 'stdin_stdout') ? 'program' : 'function'
}
