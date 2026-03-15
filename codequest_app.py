"""
╔══════════════════════════════════════════════════════╗
║           CODEQUEST — SINGLE FILE APP                ║
║  Flask backend + full frontend, everything included  ║
╠══════════════════════════════════════════════════════╣
║  HOW TO RUN:                                         ║
║    pip install flask flask-cors werkzeug             ║
║    python codequest_app.py                           ║
║  Then open: http://localhost:5000                    ║
╚══════════════════════════════════════════════════════╝
"""

# ════════════════════════════════════════════════════════
#  IMPORTS
# ════════════════════════════════════════════════════════
import sqlite3, subprocess, tempfile, os, sys, re
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, g, Response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ════════════════════════════════════════════════════════
#  FLASK APP
# ════════════════════════════════════════════════════════
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-long-random-secret-here'
app.config['DATABASE']   = 'codequest.db'

CORS(app, supports_credentials=True, origins=["*"])

# ════════════════════════════════════════════════════════
#  DATABASE
# ════════════════════════════════════════════════════════
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            xp          INTEGER DEFAULT 0,
            level       INTEGER DEFAULT 1,
            streak      INTEGER DEFAULT 0,
            last_active TEXT,
            title       TEXT    DEFAULT "Newbie",
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS challenges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,
            description     TEXT    NOT NULL,
            language        TEXT    NOT NULL,
            difficulty      TEXT    NOT NULL,
            xp_reward       INTEGER NOT NULL,
            starter_code    TEXT,
            test_input      TEXT,
            expected_output TEXT,
            hint            TEXT
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            code         TEXT    NOT NULL,
            passed       INTEGER NOT NULL DEFAULT 0,
            xp_earned    INTEGER DEFAULT 0,
            submitted_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS completed_challenges (
            user_id      INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            completed_at TEXT    DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, challenge_id)
        );
    ''')
    db.commit()

    if c.execute('SELECT COUNT(*) FROM challenges').fetchone()[0] == 0:
        _seed(c)
        db.commit()
    db.close()

def _seed(c):
    rows = [
        # ═══════════════════════════════════════════════
        #  HTML  (13 challenges)
        # ═══════════════════════════════════════════════
        ('Fix the Broken Tag',
         'The closing </h1> tag is missing. Add it to fix the heading.',
         'html','easy',150,
         '<h1>Hello World\n<p>Welcome to CodeQuest.</p>',
         None,'<h1>Hello World</h1>\n<p>Welcome to CodeQuest.</p>',
         'Every opening tag needs a matching closing tag.'),

        ('Add a Hyperlink',
         'Wrap the text "Click me" in an anchor tag pointing to https://example.com.',
         'html','easy',150,'Click me',
         None,'<a href="https://example.com">Click me</a>',
         'Use the <a href="..."> element.'),

        ('Build a Form',
         'Create a form with a text input named "username" and a submit button.',
         'html','medium',200,'',
         None,'<form>\n  <input type="text" name="username">\n  <button type="submit">Submit</button>\n</form>',
         'Use <form>, <input>, and <button> elements.'),

        ('Create an Image Tag',
         'Write an <img> tag that displays an image from "logo.png" with alt text "Logo".',
         'html','easy',150,'',
         None,'<img src="logo.png" alt="Logo">',
         'The <img> tag uses src= and alt= attributes.'),

        ('Build an Unordered List',
         'Create an unordered list with three items: Apple, Banana, Cherry.',
         'html','easy',150,'',
         None,'<ul>\n  <li>Apple</li>\n  <li>Banana</li>\n  <li>Cherry</li>\n</ul>',
         'Use <ul> for the list and <li> for each item.'),

        ('Create a Table',
         'Build a 2-row, 2-column HTML table with headers "Name" and "Age", and one data row: "Alice", "25".',
         'html','medium',220,'',
         None,'<table>\n  <tr><th>Name</th><th>Age</th></tr>\n  <tr><td>Alice</td><td>25</td></tr>\n</table>',
         'Use <th> for headers and <td> for data cells inside <tr> rows.'),

        ('Semantic Section',
         'Wrap the text "Welcome to my site" in an <h1> inside a <header> element.',
         'html','easy',160,'',
         None,'<header>\n  <h1>Welcome to my site</h1>\n</header>',
         'Use the semantic <header> element to wrap page headers.'),

        ('Add a Video',
         'Embed a video file "movie.mp4" with controls using the HTML5 <video> tag.',
         'html','medium',200,'',
         None,'<video src="movie.mp4" controls></video>',
         'The <video> tag uses src= and the controls attribute.'),

        ('Meta Description',
         'Write a <meta> tag in the <head> that sets the page description to "Learn HTML".',
         'html','easy',160,'',
         None,'<meta name="description" content="Learn HTML">',
         'Use <meta name="description" content="...">'),

        ('Input Types',
         'Create an email input field with placeholder "Enter your email" and a required attribute.',
         'html','medium',200,'',
         None,'<input type="email" placeholder="Enter your email" required>',
         'Set type="email" and add the required attribute.'),

        ('Definition List',
         'Build a definition list with term "HTML" and definition "HyperText Markup Language".',
         'html','medium',210,'',
         None,'<dl>\n  <dt>HTML</dt>\n  <dd>HyperText Markup Language</dd>\n</dl>',
         'Use <dl>, <dt> for term, <dd> for definition.'),

        ('Iframe Embed',
         'Embed https://example.com in an <iframe> with width 600 and height 400.',
         'html','medium',210,'',
         None,'<iframe src="https://example.com" width="600" height="400"></iframe>',
         'Use the <iframe> tag with src, width, height attributes.'),

        ('HTML5 Doctype + Structure',
         'Write a minimal valid HTML5 document with DOCTYPE, <html>, <head> with <title>My Page</title>, and an empty <body>.',
         'html','hard',300,'',
         None,'<!DOCTYPE html>\n<html>\n  <head>\n    <title>My Page</title>\n  </head>\n  <body></body>\n</html>',
         'Every HTML5 doc starts with <!DOCTYPE html>.'),

        # ═══════════════════════════════════════════════
        #  CSS  (12 challenges)
        # ═══════════════════════════════════════════════
        ('Center a Div',
         'Write CSS to center .box horizontally using flexbox on its parent .container.',
         'css','easy',180,
         '.container { }\n.box { width: 100px; height: 100px; }',
         None,'.container { display: flex; justify-content: center; }\n.box { width: 100px; height: 100px; }',
         'display:flex + justify-content:center on the parent'),

        ('Neon Glow Effect',
         'Add a cyan text-shadow glow to the .title element.',
         'css','medium',200,
         '.title { color: #00f5ff; }',
         None,'.title { color: #00f5ff; text-shadow: 0 0 10px #00f5ff, 0 0 20px #00f5ff; }',
         'Use multiple text-shadow values for a stronger glow.'),

        ('Button Hover Color',
         'Write CSS so that a .btn has background #264de4, and on hover changes to #1a34a0.',
         'css','easy',180,
         '.btn { }',
         None,'.btn { background: #264de4; }\n.btn:hover { background: #1a34a0; }',
         'Use :hover pseudo-class for hover states.'),

        ('Responsive Font Size',
         'Set .headline font-size to 4vw so it scales with viewport width.',
         'css','easy',170,
         '.headline { }',
         None,'.headline { font-size: 4vw; }',
         'Use viewport units: vw = viewport width percentage.'),

        ('CSS Grid 3 Columns',
         'Make .grid display as a 3-column CSS grid with a 20px gap.',
         'css','medium',220,
         '.grid { }',
         None,'.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }',
         'Use grid-template-columns: repeat(3, 1fr) for equal columns.'),

        ('Box Shadow Card',
         'Give .card a white background, 12px border-radius, and a subtle box-shadow: 0 4px 20px rgba(0,0,0,0.15).',
         'css','easy',180,
         '.card { }',
         None,'.card { background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }',
         'Combine background, border-radius, and box-shadow.'),

        ('CSS Variable',
         'Define a CSS variable --primary: #00f5ff on :root, then apply it as the color of .link.',
         'css','medium',210,
         ':root { }\n.link { }',
         None,':root { --primary: #00f5ff; }\n.link { color: var(--primary); }',
         'Define vars on :root and use var(--name) to apply them.'),

        ('Transition Animation',
         'Add a 0.3s ease transition on background-color to .btn.',
         'css','easy',180,
         '.btn { background: blue; }',
         None,'.btn { background: blue; transition: background-color 0.3s ease; }',
         'Use transition: property duration timing-function.'),

        ('Fixed Navbar',
         'Make .navbar fixed to the top of the screen with full width.',
         'css','medium',200,
         '.navbar { }',
         None,'.navbar { position: fixed; top: 0; width: 100%; }',
         'Use position:fixed with top:0 and width:100%.'),

        ('Hide Element',
         'Write CSS to completely hide .popup from the page (not just invisible — remove from layout).',
         'css','easy',160,
         '.popup { }',
         None,'.popup { display: none; }',
         'display:none removes the element from the layout entirely.'),

        ('Flexbox Space Between',
         'Make .nav a flex container with items spaced to opposite ends (space-between) and vertically centered.',
         'css','medium',210,
         '.nav { }',
         None,'.nav { display: flex; justify-content: space-between; align-items: center; }',
         'Use justify-content:space-between and align-items:center.'),

        ('CSS Keyframe Animation',
         'Write a @keyframes rule named "pulse" that goes from opacity 1 to opacity 0.4 at 50%, back to 1.',
         'css','hard',320,
         '',
         None,'@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }',
         'Use @keyframes with percentage-based stops.'),

        # ═══════════════════════════════════════════════
        #  JAVASCRIPT  (13 challenges)
        # ═══════════════════════════════════════════════
        ('Hello World Function',
         'Write a function greet(name) that returns "Hello, <name>!".',
         'javascript','easy',180,
         'function greet(name) {\n  // your code here\n}',
         'greet("CodeQuest")','Hello, CodeQuest!',
         'Use template literals: `Hello, ${name}!`'),

        ('FizzBuzz',
         'Write fizzbuzz(n): return "Fizz" divisible by 3, "Buzz" by 5, "FizzBuzz" by both, else number as string.',
         'javascript','medium',250,
         'function fizzbuzz(n) {\n  // your code here\n}',
         'fizzbuzz(15)','FizzBuzz',
         'Check divisibility by 15 first, then 3, then 5.'),

        ('Reverse a String',
         'Write reverseStr(s) that returns the string reversed.',
         'javascript','easy',180,
         'function reverseStr(s) {\n  // your code here\n}',
         'reverseStr("quest")','tseuq',
         'Try: s.split("").reverse().join("")'),

        ('Array Max',
         'Write maxVal(arr) that returns the largest number in an array.',
         'javascript','easy',190,
         'function maxVal(arr) {\n  // your code here\n}',
         'maxVal([3, 7, 2, 9, 1])','9',
         'Use Math.max(...arr) or reduce().'),

        ('Count Occurrences',
         'Write countChar(str, char) that returns how many times char appears in str.',
         'javascript','medium',240,
         'function countChar(str, char) {\n  // your code here\n}',
         'countChar("banana", "a")','3',
         'Split by char and count the pieces minus 1, or use filter.'),

        ('Flatten Array',
         'Write flatten(arr) that flattens one level of nesting: [[1,2],[3,4]] → [1,2,3,4].',
         'javascript','medium',260,
         'function flatten(arr) {\n  // your code here\n}',
         'flatten([[1,2],[3,4]])','1,2,3,4',
         'Use arr.flat() or [].concat(...arr).'),

        ('Capitalize Words',
         'Write capitalizeWords(str) that capitalizes the first letter of every word.',
         'javascript','medium',250,
         'function capitalizeWords(str) {\n  // your code here\n}',
         'capitalizeWords("hello world")','Hello World',
         'Split by space, map each word, then join.'),

        ('Check Prime',
         'Write isPrime(n) that returns true if n is a prime number, false otherwise.',
         'javascript','hard',350,
         'function isPrime(n) {\n  // your code here\n}',
         'isPrime(7)','true',
         'Check divisibility from 2 up to Math.sqrt(n).'),

        ('Deep Clone Object',
         'Write deepClone(obj) that returns a deep copy of a plain object (no functions).',
         'javascript','hard',380,
         'function deepClone(obj) {\n  // your code here\n}',
         'JSON.stringify(deepClone({a:1,b:{c:2}}))','{"a":1,"b":{"c":2}}',
         'Use JSON.parse(JSON.stringify(obj)) for plain objects.'),

        ('Sum Array with Reduce',
         'Write sumArr(nums) using Array.reduce() that returns the total sum.',
         'javascript','medium',240,
         'function sumArr(nums) {\n  // your code here\n}',
         'sumArr([1,2,3,4,5])','15',
         'Use arr.reduce((acc, val) => acc + val, 0)'),

        ('Remove Duplicates',
         'Write unique(arr) that removes duplicate values from an array.',
         'javascript','medium',250,
         'function unique(arr) {\n  // your code here\n}',
         'unique([1,2,2,3,3,4]).join(",")','1,2,3,4',
         'Use [...new Set(arr)] to remove duplicates.'),

        ('Debounce Function',
         'Write debounce(fn, delay) that returns a debounced version of fn.',
         'javascript','hard',450,
         'function debounce(fn, delay) {\n  // your code here\n}',
         None,None,
         'Use setTimeout and clearTimeout inside a closure.'),

        ('Promise Chain',
         'Write fetchData() that returns a Promise resolving to "data loaded".',
         'javascript','hard',400,
         'function fetchData() {\n  // your code here\n}',
         None,None,
         'Return new Promise((resolve, reject) => { resolve("data loaded"); })'),

        # ═══════════════════════════════════════════════
        #  PYTHON  (13 challenges)
        # ═══════════════════════════════════════════════
        ('Hello World',
         'Write a function greet(name) that returns "Hello, <name>!".',
         'python','easy',150,
         'def greet(name):\n    # your code here\n    pass',
         'greet("CodeQuest")','Hello, CodeQuest!',
         'Use an f-string: f"Hello, {name}!"'),

        ('Sum of List',
         'Write sum_list(nums) that returns the sum of all numbers in the list.',
         'python','easy',150,
         'def sum_list(nums):\n    # your code here\n    pass',
         'sum_list([1, 2, 3, 4, 5])','15',
         'Python has a built-in sum() function.'),

        ('Palindrome Check',
         'Write is_palindrome(s) that returns True if s reads the same forwards and backwards.',
         'python','medium',250,
         'def is_palindrome(s):\n    # your code here\n    pass',
         'is_palindrome("racecar")','True',
         'Compare s with s reversed: s == s[::-1]'),

        ('Count Vowels',
         'Write count_vowels(s) that returns how many vowels are in the string.',
         'python','easy',180,
         'def count_vowels(s):\n    # your code here\n    pass',
         'count_vowels("CodeQuest")','4',
         'Loop through each character and check if it is in "aeiouAEIOU".'),

        ('Factorial',
         'Write factorial(n) that returns the factorial of n (e.g. factorial(5) = 120).',
         'python','medium',240,
         'def factorial(n):\n    # your code here\n    pass',
         'factorial(5)','120',
         'Use recursion: factorial(n) = n * factorial(n-1), base case n==0 returns 1.'),

        ('Fibonacci',
         'Write fib(n) that returns the nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1, fib(7)=13).',
         'python','medium',260,
         'def fib(n):\n    # your code here\n    pass',
         'fib(7)','13',
         'Use a loop or recursion. Build up: a,b = 0,1 then swap.'),

        ('List Comprehension',
         'Write squares(n) that returns a list of squares from 1 to n using a list comprehension.',
         'python','medium',230,
         'def squares(n):\n    # your code here\n    pass',
         'squares(5)','[1, 4, 9, 16, 25]',
         'Use [x**2 for x in range(1, n+1)]'),

        ('Word Frequency',
         'Write word_freq(sentence) that returns a dict of each word and its count.',
         'python','medium',280,
         'def word_freq(sentence):\n    # your code here\n    pass',
         'word_freq("the cat sat on the cat")','{"the": 2, "cat": 2, "sat": 1, "on": 1}',
         'Split the sentence and use a dict to count occurrences.'),

        ('Flatten Nested List',
         'Write flatten(lst) that flattens one level of nesting: [[1,2],[3,4]] → [1,2,3,4].',
         'python','medium',260,
         'def flatten(lst):\n    # your code here\n    pass',
         'flatten([[1,2],[3,4]])','[1, 2, 3, 4]',
         'Use a list comprehension with two for loops.'),

        ('Find Second Largest',
         'Write second_largest(nums) that returns the second largest unique number in a list.',
         'python','hard',350,
         'def second_largest(nums):\n    # your code here\n    pass',
         'second_largest([4, 1, 7, 3, 7, 9])','7',
         'Convert to a set, sort descending, pick index 1.'),

        ('Caesar Cipher',
         'Write caesar(text, shift) that shifts each letter by shift positions (wrap a-z, preserve case).',
         'python','hard',400,
         'def caesar(text, shift):\n    # your code here\n    pass',
         'caesar("Hello", 3)','Khoor',
         'Use ord() and chr() with modulo 26 to wrap around the alphabet.'),

        ('Decorator Basics',
         'Write a decorator timer that prints "Function called" before calling the wrapped function. Apply it to say_hi() that returns "hi".',
         'python','hard',420,
         'def timer(func):\n    # your code here\n    pass\n\n@timer\ndef say_hi():\n    return "hi"',
         'say_hi()','hi',
         'A decorator takes a function and returns a wrapper function.'),

        ('Generator Function',
         'Write countdown(n) as a generator that yields n, n-1, ..., 1.',
         'python','hard',380,
         'def countdown(n):\n    # your code here\n    pass',
         'list(countdown(5))','[5, 4, 3, 2, 1]',
         'Use yield inside a while or for loop.'),

        # ═══════════════════════════════════════════════
        #  C  (12 challenges)
        # ═══════════════════════════════════════════════
        ('Print Hello',
         'Fix the C program so it prints "Hello, World!" (the printf statement is incomplete).',
         'c','easy',200,
         '#include <stdio.h>\nint main() {\n    printf("Hello, ___!");\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    printf("Hello, World!");\n    return 0;\n}',
         'Replace ___ with World'),

        ('Pointer Basics',
         'Declare an int variable x = 42, then print its value using a pointer.',
         'c','hard',500,
         '#include <stdio.h>\nint main() {\n    // your code\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int x = 42;\n    int *p = &x;\n    printf("%d", *p);\n    return 0;\n}',
         'Use & to get address, * to dereference.'),

        ('For Loop Sum',
         'Write a C program that uses a for loop to sum 1 through 5 and prints the result (15).',
         'c','easy',210,
         '#include <stdio.h>\nint main() {\n    int sum = 0;\n    // your for loop here\n    printf("%d", sum);\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int sum = 0;\n    for(int i = 1; i <= 5; i++) { sum += i; }\n    printf("%d", sum);\n    return 0;\n}',
         'Use for(int i=1; i<=5; i++) and sum += i.'),

        ('Swap Two Variables',
         'Write a C program that swaps int a=5 and int b=10 using a temp variable and prints "10 5".',
         'c','easy',220,
         '#include <stdio.h>\nint main() {\n    int a = 5, b = 10;\n    // swap here\n    printf("%d %d", a, b);\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int a = 5, b = 10;\n    int temp = a; a = b; b = temp;\n    printf("%d %d", a, b);\n    return 0;\n}',
         'Use a third temporary variable: temp = a; a = b; b = temp;'),

        ('String Length',
         'Use strlen() from string.h to print the length of "CodeQuest".',
         'c','medium',260,
         '#include <stdio.h>\n#include <string.h>\nint main() {\n    // your code\n    return 0;\n}',
         None,'#include <stdio.h>\n#include <string.h>\nint main() {\n    printf("%lu", strlen("CodeQuest"));\n    return 0;\n}',
         'Include <string.h> and use strlen(str).'),

        ('Array Average',
         'Compute and print the average of int arr[] = {2, 4, 6, 8, 10} as a float.',
         'c','medium',280,
         '#include <stdio.h>\nint main() {\n    int arr[] = {2, 4, 6, 8, 10};\n    // compute average\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int arr[] = {2, 4, 6, 8, 10};\n    float sum = 0;\n    for(int i=0;i<5;i++) sum += arr[i];\n    printf("%.1f", sum/5);\n    return 0;\n}',
         'Sum all elements and divide by count. Cast to float.'),

        ('Recursive Factorial',
         'Write a recursive function int factorial(int n) and print factorial(5).',
         'c','hard',400,
         '#include <stdio.h>\n// write factorial here\nint main() {\n    printf("%d", factorial(5));\n    return 0;\n}',
         None,'#include <stdio.h>\nint factorial(int n) { if(n<=1) return 1; return n * factorial(n-1); }\nint main() {\n    printf("%d", factorial(5));\n    return 0;\n}',
         'Base case: if(n<=1) return 1; recursive: return n * factorial(n-1).'),

        ('Struct Definition',
         'Define a struct Point with int x and int y. Create a Point p = {3, 7} and print "3 7".',
         'c','hard',420,
         '#include <stdio.h>\n// define struct here\nint main() {\n    // use the struct\n    return 0;\n}',
         None,'#include <stdio.h>\nstruct Point { int x; int y; };\nint main() {\n    struct Point p = {3, 7};\n    printf("%d %d", p.x, p.y);\n    return 0;\n}',
         'Use struct TypeName { ... }; then access members with dot notation.'),

        ('Dynamic Memory',
         'Use malloc to allocate memory for 3 ints, set them to 10,20,30, print them, then free.',
         'c','hard',500,
         '#include <stdio.h>\n#include <stdlib.h>\nint main() {\n    // malloc, fill, print, free\n    return 0;\n}',
         None,'#include <stdio.h>\n#include <stdlib.h>\nint main() {\n    int *arr = malloc(3 * sizeof(int));\n    arr[0]=10; arr[1]=20; arr[2]=30;\n    for(int i=0;i<3;i++) printf("%d ", arr[i]);\n    free(arr);\n    return 0;\n}',
         'Use malloc(count * sizeof(type)) and always call free().'),

        ('File Write',
         'Write a C program that creates/opens "out.txt" for writing and writes "Hello File" to it.',
         'c','hard',460,
         '#include <stdio.h>\nint main() {\n    // open, write, close\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    FILE *f = fopen("out.txt", "w");\n    fprintf(f, "Hello File");\n    fclose(f);\n    return 0;\n}',
         'Use fopen("file","w"), fprintf(f,...), fclose(f).'),

        ('Bit Flags',
         'Use bitwise OR to combine READ=1, WRITE=2, EXEC=4 and print the result (7).',
         'c','hard',480,
         '#include <stdio.h>\nint main() {\n    int READ=1, WRITE=2, EXEC=4;\n    // combine with OR\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int READ=1, WRITE=2, EXEC=4;\n    int perms = READ | WRITE | EXEC;\n    printf("%d", perms);\n    return 0;\n}',
         'Use the | bitwise OR operator to combine flags.'),

        ('Pointer Arithmetic',
         'Create an int array {5,10,15}, use a pointer to iterate and print all values with a space.',
         'c','hard',500,
         '#include <stdio.h>\nint main() {\n    int arr[] = {5,10,15};\n    // use pointer arithmetic\n    return 0;\n}',
         None,'#include <stdio.h>\nint main() {\n    int arr[] = {5,10,15};\n    int *p = arr;\n    for(int i=0;i<3;i++) printf("%d ", *(p+i));\n    return 0;\n}',
         'Point to arr, then use *(p+i) to dereference each element.'),
    ]
    c.executemany('''INSERT INTO challenges
        (title,description,language,difficulty,xp_reward,starter_code,test_input,expected_output,hint)
        VALUES (?,?,?,?,?,?,?,?,?)''', rows)

# ════════════════════════════════════════════════════════
#  UTILS
# ════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

def calculate_level(xp):
    level = 1
    while True:
        if xp < int(500 * (level ** 1.5)):
            break
        level += 1
    return level

TITLES = [
    (1,  'Newbie'),
    (5,  'Script Kiddie'),
    (10, 'Bug Hunter'),
    (15, 'Code Warrior'),
    (20, 'Syntax Slayer'),
    (25, 'Algorithm Ace'),
    (30, 'Stack Overflow'),
    (35, 'Pointer Punisher'),
    (40, 'Async Avenger'),
    (45, 'Full Stack Phantom'),
    (50, 'CodeQuest Legend'),
]

def level_title(level):
    t = 'Newbie'
    for threshold, name in TITLES:
        if level >= threshold:
            t = name
    return t

def xp_threshold(level):
    return 0 if level <= 1 else int(500 * ((level - 1) ** 1.5))

# ════════════════════════════════════════════════════════
#  AUTH HELPERS
# ════════════════════════════════════════════════════════
def _pub(user):
    return {
        'id':       user['id'],
        'username': user['username'],
        'email':    user['email'],
        'xp':       user['xp'],
        'level':    user['level'],
        'streak':   user['streak'],
        'title':    user['title'],
    }

def _update_streak(db, user_id):
    user  = db.execute('SELECT last_active, streak FROM users WHERE id=?', (user_id,)).fetchone()
    today = datetime.utcnow().date()
    if user['last_active']:
        last = datetime.fromisoformat(user['last_active']).date()
        if last == today:
            return
        new_streak = user['streak'] + 1 if last == today - timedelta(days=1) else 1
    else:
        new_streak = 1
    db.execute('UPDATE users SET streak=?, last_active=? WHERE id=?',
               (new_streak, datetime.utcnow().isoformat(), user_id))
    db.commit()

@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.get_json()
    username = (d.get('username') or '').strip()
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '')
    if not username or not email or not password:
        return jsonify({'error':'username, email and password are required'}),400
    if len(username)<3: return jsonify({'error':'Username must be at least 3 characters'}),400
    if len(password)<6: return jsonify({'error':'Password must be at least 6 characters'}),400
    db = get_db()
    try:
        db.execute('INSERT INTO users (username,email,password) VALUES (?,?,?)',
                   (username,email,generate_password_hash(password)))
        db.commit()
    except Exception:
        return jsonify({'error':'Username or email already taken'}),409
    user = db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    session['user_id'] = user['id']
    return jsonify(_pub(user)),201

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.get_json()
    username = (d.get('username') or '').strip()
    password = (d.get('password') or '')
    if not username or not password:
        return jsonify({'error':'username and password are required'}),400
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    if not user or not check_password_hash(user['password'],password):
        return jsonify({'error':'Invalid username or password'}),401
    _update_streak(db, user['id'])
    session['user_id'] = user['id']
    user = db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
    return jsonify(_pub(user)),200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message':'Logged out successfully'}),200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone()
    if not user: return jsonify({'error':'User not found'}),404
    completed = db.execute('SELECT COUNT(*) as cnt FROM completed_challenges WHERE user_id=?',
                           (user['id'],)).fetchone()['cnt']
    lvl = user['level']
    xp_into = user['xp'] - xp_threshold(lvl)
    xp_need  = xp_threshold(lvl+1) - xp_threshold(lvl)
    return jsonify({**_pub(user),'completed_challenges':completed,
                    'xp_to_next_level': xp_need,
                    'progress_percent': round((xp_into/xp_need)*100,1) if xp_need else 100}),200

# ════════════════════════════════════════════════════════
#  XP ROUTES  /api/xp/...
# ════════════════════════════════════════════════════════
def award_xp(db, user_id, base_xp, streak):
    bonus = 1.5 if streak>=30 else (1.25 if streak>=7 else (1.1 if streak>=3 else 1.0))
    total = int(base_xp * bonus)
    user  = db.execute('SELECT xp,level FROM users WHERE id=?',(user_id,)).fetchone()
    new_xp    = user['xp'] + total
    new_level = calculate_level(new_xp)
    new_title = level_title(new_level)
    leveled   = new_level > user['level']
    db.execute('UPDATE users SET xp=?,level=?,title=? WHERE id=?',(new_xp,new_level,new_title,user_id))
    db.commit()
    return {'xp_earned':total,'streak_bonus':bonus,'new_xp':new_xp,
            'new_level':new_level,'leveled_up':leveled,'new_title':new_title if leveled else None}

@app.route('/api/xp/status', methods=['GET'])
@login_required
def xp_status():
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone()
    lvl  = user['level']
    xp_into = user['xp'] - xp_threshold(lvl)
    xp_need  = xp_threshold(lvl+1) - xp_threshold(lvl)
    return jsonify({'xp':user['xp'],'level':lvl,'title':user['title'],
                    'xp_into_level':xp_into,'xp_for_next':xp_need,
                    'progress_percent':round((xp_into/xp_need)*100,1) if xp_need else 100,
                    'streak':user['streak']}),200

@app.route('/api/xp/history', methods=['GET'])
@login_required
def xp_history():
    db   = get_db()
    rows = db.execute('''SELECT s.xp_earned,s.submitted_at,c.title as challenge,c.language
        FROM submissions s JOIN challenges c ON s.challenge_id=c.id
        WHERE s.user_id=? AND s.passed=1 ORDER BY s.submitted_at DESC LIMIT 20''',
        (session['user_id'],)).fetchall()
    return jsonify([dict(r) for r in rows]),200

# ════════════════════════════════════════════════════════
#  CHALLENGE ROUTES  /api/challenges/...
# ════════════════════════════════════════════════════════
@app.route('/api/challenges/', methods=['GET'])
def list_challenges():
    language   = request.args.get('language')
    difficulty = request.args.get('difficulty')
    db         = get_db()
    q,p = 'SELECT id,title,description,language,difficulty,xp_reward,starter_code,hint FROM challenges WHERE 1=1',[]
    if language:   q+=' AND language=?';   p.append(language.lower())
    if difficulty: q+=' AND difficulty=?'; p.append(difficulty.lower())
    q += ' ORDER BY CASE difficulty WHEN \'easy\' THEN 1 WHEN \'medium\' THEN 2 WHEN \'hard\' THEN 3 ELSE 4 END, id ASC'
    rows = db.execute(q,p).fetchall()
    done = set()
    if 'user_id' in session:
        done = {r['challenge_id'] for r in db.execute(
            'SELECT challenge_id FROM completed_challenges WHERE user_id=?',(session['user_id'],)).fetchall()}
    result = []
    for r in rows:
        c = dict(r); c['completed'] = c['id'] in done; result.append(c)
    return jsonify(result),200

@app.route('/api/challenges/<int:cid>', methods=['GET'])
def get_challenge(cid):
    db  = get_db()
    row = db.execute('SELECT id,title,description,language,difficulty,xp_reward,starter_code,hint FROM challenges WHERE id=?',(cid,)).fetchone()
    if not row: return jsonify({'error':'Challenge not found'}),404
    return jsonify(dict(row)),200

@app.route('/api/challenges/<int:cid>/submit', methods=['POST'])
@login_required
def submit_solution(cid):
    code = (request.get_json().get('code') or '').strip()
    if not code: return jsonify({'error':'No code submitted'}),400
    db   = get_db()
    ch   = db.execute('SELECT * FROM challenges WHERE id=?',(cid,)).fetchone()
    if not ch: return jsonify({'error':'Challenge not found'}),404
    uid  = session['user_id']
    done = db.execute('SELECT 1 FROM completed_challenges WHERE user_id=? AND challenge_id=?',(uid,cid)).fetchone()
    passed, feedback = _grade(ch, code)
    xp_result = None
    if passed and not done:
        user = db.execute('SELECT streak FROM users WHERE id=?',(uid,)).fetchone()
        xp_result = award_xp(db, uid, ch['xp_reward'], user['streak'])
        db.execute('INSERT INTO completed_challenges (user_id,challenge_id) VALUES (?,?)',(uid,cid))
        db.commit()
    elif passed and done:
        feedback = 'Correct! (You already earned XP for this challenge.)'
    xp_earned = xp_result['xp_earned'] if xp_result else 0
    db.execute('INSERT INTO submissions (user_id,challenge_id,code,passed,xp_earned) VALUES (?,?,?,?,?)',
               (uid,cid,code,1 if passed else 0,xp_earned))
    db.commit()
    resp = {'passed':passed,'feedback':feedback}
    if xp_result: resp['xp_result'] = xp_result
    return jsonify(resp),200

# ── Graders ────────────────────────────────────────────
def _grade(ch, code):
    lang = ch['language']
    exp  = (ch['expected_output'] or '').strip()
    inp  = ch['test_input']
    if lang=='python':     return _grade_python(code,inp,exp)
    elif lang=='javascript': return _grade_js(code,inp,exp)
    else:                   return _grade_static(code,exp)

def _grade_python(code,test_input,expected):
    runner = code+'\n'
    if test_input: runner += f'\nprint({test_input})\n'
    fname = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.py',delete=False) as f:
            f.write(runner); fname=f.name
        r = subprocess.run(timeout=5, [sys.executable,fname],capture_output=True,text=True,timeout=5)
        actual = r.stdout.strip()
        if r.returncode!=0:
            return False, f'Runtime error: {r.stderr.strip().split(chr(10))[-1]}'
        if actual==expected: return True, f'✅ Correct! Output: {actual}'
        return False, f'❌ Expected "{expected}" but got "{actual}"'
    except subprocess.TimeoutExpired: return False,'⏱ Time limit exceeded (5s)'
    except Exception as e: return False,f'Grader error: {e}'
    finally:
        if fname and os.path.exists(fname):
            try: os.unlink(fname)
            except: pass

def _grade_js(code,test_input,expected):
    runner = code+'\n'
    if test_input: runner += f'\nconsole.log({test_input});\n'
    fname = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.js',delete=False) as f:
            f.write(runner); fname=f.name
        r = subprocess.run(timeout=5, ['node',fname],capture_output=True,text=True,timeout=5)
        if r.returncode!=0: return _grade_static(code,expected)
        actual = r.stdout.strip()
        if actual==expected: return True,f'✅ Correct! Output: {actual}'
        return False,f'❌ Expected "{expected}" but got "{actual}"'
    except (FileNotFoundError,subprocess.TimeoutExpired): return _grade_static(code,expected)
    except Exception as e: return False,f'Grader error: {e}'
    finally:
        if fname and os.path.exists(fname):
            try: os.unlink(fname)
            except: pass

def _grade_static(code,expected):
    norm = lambda s: re.sub(r'\s+',' ',s.strip().lower())
    if norm(code)==norm(expected): return True,'✅ Correct!'
    return False,'❌ Your code does not match the expected output. Check spacing and syntax.'

# ════════════════════════════════════════════════════════
#  LEADERBOARD ROUTES  /api/leaderboard/...
# ════════════════════════════════════════════════════════
@app.route('/api/leaderboard/', methods=['GET'])
def global_leaderboard():
    limit  = min(int(request.args.get('limit',10)),50)
    offset = int(request.args.get('offset',0))
    db     = get_db()
    rows   = db.execute('''SELECT u.id,u.username,u.xp,u.level,u.streak,u.title,
        COUNT(cc.challenge_id) as challenges_completed
        FROM users u LEFT JOIN completed_challenges cc ON u.id=cc.user_id
        GROUP BY u.id ORDER BY u.xp DESC LIMIT ? OFFSET ?''',(limit,offset)).fetchall()
    lb = [dict(r)|{'rank':offset+i+1} for i,r in enumerate(rows)]
    my_rank = None
    if 'user_id' in session:
        my_rank = db.execute('SELECT COUNT(*)+1 as rank FROM users WHERE xp>(SELECT xp FROM users WHERE id=?)',
                             (session['user_id'],)).fetchone()['rank']
    return jsonify({'leaderboard':lb,'my_rank':my_rank,
                    'total':db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']}),200

@app.route('/api/leaderboard/language/<language>', methods=['GET'])
def language_leaderboard(language):
    limit = min(int(request.args.get('limit',10)),50)
    db    = get_db()
    rows  = db.execute('''SELECT u.id,u.username,u.level,u.title,
        COALESCE(SUM(s.xp_earned),0) as lang_xp, COUNT(s.id) as submissions
        FROM users u
        LEFT JOIN submissions s ON u.id=s.user_id AND s.passed=1
        LEFT JOIN challenges c ON s.challenge_id=c.id AND c.language=?
        GROUP BY u.id ORDER BY lang_xp DESC LIMIT ?''',(language.lower(),limit)).fetchall()
    lb = [dict(r)|{'rank':i+1} for i,r in enumerate(rows)]
    return jsonify({'language':language,'leaderboard':lb}),200

@app.route('/api/stats', methods=['GET'])
def stats():
    db = get_db()
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    return jsonify({'active_players': total_users}), 200

# ════════════════════════════════════════════════════════
#  FRONTEND ROUTE — serves the full HTML page
# ════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeQuest — Learn to Code by Playing</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#060912;--bg2:#0c1220;--panel:#0f1929;--border:#1a2a45;
    --glow-cyan:#00f5ff;--glow-purple:#bf00ff;--glow-green:#39ff14;
    --glow-pink:#ff007f;--text:#c8d8f0;--text-dim:#5a7090;--gold:#ffd700;
    --html-color:#e34c26;--css-color:#264de4;--js-color:#f7df1e;
    --py-color:#3572a5;--c-color:#888;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{font-family:'Rajdhani',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;cursor:pointer}
  .cursor{position:fixed;width:16px;height:16px;border:2px solid var(--glow-cyan);border-radius:50%;pointer-events:none;z-index:9999;transform:translate(-50%,-50%);transition:.1s;box-shadow:0 0 10px var(--glow-cyan)}
  .cursor-dot{position:fixed;width:4px;height:4px;background:var(--glow-cyan);border-radius:50%;pointer-events:none;z-index:9999;transform:translate(-50%,-50%)}
  #starfield{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
  body::after{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px);pointer-events:none;z-index:1}

  /* NAV */
  nav{position:fixed;top:0;width:100%;z-index:100;padding:18px 60px;display:flex;align-items:center;justify-content:space-between;background:rgba(6,9,18,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
  .nav-logo{font-family:'Orbitron',monospace;font-size:1.4rem;font-weight:900;letter-spacing:3px;color:var(--glow-cyan);text-shadow:0 0 20px var(--glow-cyan);animation:logoPulse 3s ease-in-out infinite}
  @keyframes logoPulse{0%,100%{text-shadow:0 0 20px var(--glow-cyan)}50%{text-shadow:0 0 40px var(--glow-cyan),0 0 60px var(--glow-cyan)}}
  .nav-links{display:flex;gap:36px}
  .nav-links a{font-family:'Share Tech Mono',monospace;font-size:.8rem;letter-spacing:2px;color:var(--text-dim);text-decoration:none;text-transform:uppercase;transition:.3s}
  .nav-links a:hover{color:var(--glow-cyan);text-shadow:0 0 10px var(--glow-cyan)}
  .nav-right{display:flex;align-items:center;gap:16px}
  .nav-xp{font-family:'Orbitron',monospace;font-size:.75rem;color:var(--gold);display:flex;align-items:center;gap:10px}
  .xp-bar{width:100px;height:6px;background:var(--border);border-radius:3px;overflow:hidden}
  .xp-fill{height:100%;background:linear-gradient(90deg,var(--gold),#ffa500);width:0%;border-radius:3px;transition:width .5s}
  .nav-auth-btn{font-family:'Orbitron',monospace;font-size:.65rem;letter-spacing:2px;padding:8px 18px;border-radius:4px;border:1px solid var(--glow-cyan);background:transparent;color:var(--glow-cyan);cursor:pointer;text-transform:uppercase;transition:.3s}
  .nav-auth-btn:hover{background:rgba(0,245,255,.1);box-shadow:0 0 15px rgba(0,245,255,.3)}
  .nav-auth-btn.logout{border-color:var(--glow-pink);color:var(--glow-pink)}
  .nav-auth-btn.logout:hover{background:rgba(255,0,127,.1)}

  /* HERO */
  .hero{position:relative;z-index:2;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:100px 40px 60px}
  .hero-badge{font-family:'Share Tech Mono',monospace;font-size:.75rem;letter-spacing:4px;color:var(--glow-purple);text-transform:uppercase;border:1px solid var(--glow-purple);padding:6px 20px;border-radius:30px;margin-bottom:30px;animation:fadeSlideDown .8s ease both;box-shadow:0 0 15px rgba(191,0,255,.2)}
  .hero-title{font-family:'Orbitron',monospace;font-size:clamp(3rem,8vw,7rem);font-weight:900;line-height:1;animation:fadeSlideDown .9s .1s ease both;margin-bottom:10px}
  .hero-title .line1{display:block;color:#fff}
  .hero-title .line2{display:block;background:linear-gradient(135deg,var(--glow-cyan),var(--glow-purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;animation:gradientShift 4s ease-in-out infinite}
  @keyframes gradientShift{0%,100%{filter:drop-shadow(0 0 20px rgba(0,245,255,.5))}50%{filter:drop-shadow(0 0 30px rgba(191,0,255,.6))}}
  .hero-sub{font-size:1.3rem;font-weight:300;letter-spacing:2px;color:var(--text-dim);max-width:600px;margin:20px auto 50px;line-height:1.6}
  .hero-sub em{color:var(--glow-cyan);font-style:normal}
  .hero-btns{display:flex;gap:20px;animation:fadeSlideDown 1s .35s ease both}
  .btn-primary,.btn-secondary{font-family:'Orbitron',monospace;font-size:.8rem;letter-spacing:2px;padding:16px 40px;border-radius:4px;border:none;cursor:pointer;text-decoration:none;text-transform:uppercase;transition:.3s;position:relative;overflow:hidden}
  .btn-primary{background:linear-gradient(135deg,var(--glow-cyan),#0090aa);color:#000;font-weight:700;box-shadow:0 0 25px rgba(0,245,255,.4)}
  .btn-primary:hover{box-shadow:0 0 50px rgba(0,245,255,.7);transform:translateY(-2px) scale(1.02)}
  .btn-secondary{background:transparent;color:var(--glow-purple);border:1px solid var(--glow-purple)}
  .btn-secondary:hover{background:rgba(191,0,255,.1);box-shadow:0 0 30px rgba(191,0,255,.5);transform:translateY(-2px)}
  .lang-orbit{position:absolute;inset:0;pointer-events:none;overflow:hidden}
  .orbit-tag{position:absolute;font-family:'Orbitron',monospace;font-size:.7rem;letter-spacing:2px;padding:6px 14px;border-radius:3px;border:1px solid;animation:floatTag linear infinite;opacity:.7}
  .orbit-tag.html{top:15%;left:8%;color:var(--html-color);border-color:var(--html-color);animation-duration:6s}
  .orbit-tag.css{top:30%;right:6%;color:var(--css-color);border-color:var(--css-color);animation-duration:8s;animation-delay:-2s}
  .orbit-tag.js{top:70%;left:5%;color:var(--js-color);border-color:var(--js-color);animation-duration:7s;animation-delay:-1s}
  .orbit-tag.py{top:75%;right:8%;color:var(--py-color);border-color:var(--py-color);animation-duration:9s;animation-delay:-3s}
  .orbit-tag.c{top:55%;left:3%;color:#aaa;border-color:#555;animation-duration:10s;animation-delay:-4s}
  @keyframes floatTag{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-18px) rotate(1deg)}}
  .scroll-hint{position:absolute;bottom:40px;left:50%;transform:translateX(-50%);animation:bounce 2s ease-in-out infinite;opacity:.5}
  .scroll-hint span{display:block;width:24px;height:38px;border:2px solid var(--glow-cyan);border-radius:12px;position:relative}
  .scroll-hint span::before{content:'';width:4px;height:8px;background:var(--glow-cyan);border-radius:2px;position:absolute;top:6px;left:50%;transform:translateX(-50%);animation:scrollDot 2s ease-in-out infinite}
  @keyframes scrollDot{0%,100%{top:6px;opacity:1}80%{top:18px;opacity:0}}
  @keyframes bounce{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(6px)}}

  /* STATS */
  .stats-bar{position:relative;z-index:2;display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border)}
  .stat-item{background:var(--bg2);padding:28px 20px;text-align:center;transition:.3s}
  .stat-item:hover{background:var(--panel)}
  .stat-num{font-family:'Orbitron',monospace;font-size:2.5rem;font-weight:900;color:var(--glow-cyan);text-shadow:0 0 20px rgba(0,245,255,.4);display:block}
  .stat-label{font-size:.85rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;margin-top:4px}
  .stat-item:nth-child(2) .stat-num{color:var(--glow-purple)}
  .stat-item:nth-child(3) .stat-num{color:var(--glow-green)}
  .stat-item:nth-child(4) .stat-num{color:var(--gold)}

  /* SECTIONS */
  section{position:relative;z-index:2;padding:100px 60px}
  .section-header{text-align:center;margin-bottom:70px}
  .section-tag{font-family:'Share Tech Mono',monospace;font-size:.75rem;letter-spacing:4px;color:var(--glow-cyan);text-transform:uppercase;margin-bottom:14px;display:block}
  .section-title{font-family:'Orbitron',monospace;font-size:clamp(1.8rem,4vw,3rem);font-weight:700;color:#fff}
  .section-title .accent{color:var(--glow-cyan)}

  /* LANGUAGE CARDS */
  .lang-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px;max-width:1400px;margin:0 auto}
  .lang-card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:36px 28px;cursor:pointer;position:relative;overflow:hidden;transition:transform .4s cubic-bezier(.175,.885,.32,1.275),border-color .3s,box-shadow .3s}
  .lang-card:hover{transform:translateY(-8px) scale(1.02);border-color:var(--card-color,var(--glow-cyan));box-shadow:0 10px 40px rgba(0,0,0,.4)}
  .lang-card.html-card{--card-color:var(--html-color)}.lang-card.css-card{--card-color:var(--css-color)}.lang-card.js-card{--card-color:var(--js-color)}.lang-card.py-card{--card-color:var(--py-color)}.lang-card.c-card{--card-color:#888}
  .card-icon{width:64px;height:64px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-family:'Orbitron',monospace;font-size:1.1rem;font-weight:900;margin-bottom:24px}
  .html-card .card-icon{background:rgba(227,76,38,.15);color:var(--html-color);border:1px solid rgba(227,76,38,.3)}
  .css-card .card-icon{background:rgba(38,77,228,.15);color:var(--css-color);border:1px solid rgba(38,77,228,.3)}
  .js-card .card-icon{background:rgba(247,223,30,.15);color:var(--js-color);border:1px solid rgba(247,223,30,.3)}
  .py-card .card-icon{background:rgba(53,114,165,.15);color:var(--py-color);border:1px solid rgba(53,114,165,.3)}
  .c-card .card-icon{background:rgba(136,136,136,.15);color:#aaa;border:1px solid rgba(136,136,136,.3)}
  .card-lang-name{font-family:'Orbitron',monospace;font-size:1.2rem;font-weight:700;margin-bottom:10px;color:#fff}
  .card-desc{font-size:.95rem;line-height:1.6;color:var(--text-dim);margin-bottom:24px}
  .card-progress-label{font-family:'Share Tech Mono',monospace;font-size:.7rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;display:flex;justify-content:space-between;margin-bottom:8px}
  .card-progress-bar{height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-bottom:24px}
  .card-progress-fill{height:100%;border-radius:2px;background:var(--card-color,var(--glow-cyan));transition:width .6s ease}
  .card-badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}
  .badge{font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:1px;padding:4px 10px;border-radius:2px;background:rgba(255,255,255,.04);border:1px solid var(--border);color:var(--text-dim)}
  .card-play-btn{width:100%;background:transparent;border:1px solid var(--card-color,var(--glow-cyan));color:var(--card-color,var(--glow-cyan));font-family:'Orbitron',monospace;font-size:.7rem;letter-spacing:3px;padding:14px;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s}
  .card-play-btn:hover{background:rgba(255,255,255,.06)}

  /* GAMES */
  .games-section{background:var(--bg2)}
  .games-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px;max-width:1400px;margin:0 auto}
  .game-card{background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden;cursor:pointer;transition:transform .3s,box-shadow .3s}
  .game-card:hover{transform:translateY(-6px);box-shadow:0 20px 50px rgba(0,0,0,.6)}
  .game-thumb{height:180px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}
  .game-thumb-bg{position:absolute;inset:0}
  .thumb-html{background:linear-gradient(135deg,#1a0800,#3d1200)}.thumb-css{background:linear-gradient(135deg,#00081a,#001240)}.thumb-js{background:linear-gradient(135deg,#1a1600,#332c00)}.thumb-py{background:linear-gradient(135deg,#001220,#003366)}.thumb-c{background:linear-gradient(135deg,#0a0a0a,#1a1a1a)}.thumb-mixed{background:linear-gradient(135deg,#0a001a,#001a14)}
  .thumb-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px);background-size:30px 30px}
  .thumb-icon{position:relative;z-index:2;font-family:'Orbitron',monospace;font-size:2.5rem;font-weight:900;text-align:center}
  .thumb-particles{position:absolute;inset:0;pointer-events:none}
  .tp{position:absolute;width:4px;height:4px;border-radius:50%;animation:tpFloat linear infinite}
  @keyframes tpFloat{0%{transform:translateY(180px) scale(0);opacity:0}10%{opacity:1;transform:translateY(160px) scale(1)}90%{opacity:1}100%{transform:translateY(-20px) scale(.5);opacity:0}}
  .game-difficulty{position:absolute;top:12px;right:12px;font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:2px;padding:4px 12px;border-radius:2px;text-transform:uppercase}
  .diff-easy{background:rgba(57,255,20,.15);color:var(--glow-green);border:1px solid rgba(57,255,20,.3)}.diff-med{background:rgba(255,165,0,.15);color:#ffa500;border:1px solid rgba(255,165,0,.3)}.diff-hard{background:rgba(255,0,127,.15);color:var(--glow-pink);border:1px solid rgba(255,0,127,.3)}
  .game-info{padding:24px}
  .game-name{font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;color:#fff;margin-bottom:8px}
  .game-desc{font-size:.9rem;color:var(--text-dim);line-height:1.5;margin-bottom:16px}
  .game-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
  .game-lang-tag{font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:2px;padding:4px 10px;border-radius:2px;text-transform:uppercase}
  .tag-html{background:rgba(227,76,38,.15);color:var(--html-color);border:1px solid rgba(227,76,38,.3)}.tag-css{background:rgba(38,77,228,.15);color:var(--css-color);border:1px solid rgba(38,77,228,.3)}.tag-js{background:rgba(247,223,30,.15);color:var(--js-color);border:1px solid rgba(247,223,30,.3)}.tag-py{background:rgba(53,114,165,.15);color:var(--py-color);border:1px solid rgba(53,114,165,.3)}.tag-c{background:rgba(136,136,136,.1);color:#aaa;border:1px solid rgba(136,136,136,.3)}
  .game-xp{font-family:'Orbitron',monospace;font-size:.75rem;color:var(--gold)}
  .game-play-btn{width:100%;background:transparent;border:1px solid var(--border);color:var(--text);font-family:'Orbitron',monospace;font-size:.65rem;letter-spacing:3px;padding:12px;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s}
  .game-play-btn:hover{border-color:var(--glow-cyan);color:var(--glow-cyan);box-shadow:0 0 15px rgba(0,245,255,.2)}

  /* ══════════════════════════════════════
     CHEAT SHEET SECTION
  ══════════════════════════════════════ */
  .cheatsheet-section{background:var(--bg)}
  .cs-tabs{display:flex;gap:0;max-width:900px;margin:0 auto 40px;border:1px solid var(--border);border-radius:8px;overflow:hidden}
  .cs-tab{flex:1;padding:14px 10px;background:transparent;border:none;color:var(--text-dim);font-family:'Orbitron',monospace;font-size:.65rem;letter-spacing:2px;cursor:pointer;text-transform:uppercase;transition:.2s;border-right:1px solid var(--border)}
  .cs-tab:last-child{border-right:none}
  .cs-tab.active{background:rgba(0,245,255,.08);color:var(--glow-cyan)}
  .cs-tab:hover:not(.active){background:rgba(255,255,255,.03);color:var(--text)}
  .cs-panel{display:none;max-width:1200px;margin:0 auto;animation:fadeSlideDown .3s ease}
  .cs-panel.active{display:block}
  .cs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
  .cs-card{background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden}
  .cs-card-header{padding:14px 18px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
  .cs-card-header span{font-family:'Orbitron',monospace;font-size:.75rem;font-weight:700;letter-spacing:2px;text-transform:uppercase}
  .cs-card-body{padding:16px 18px}
  .cs-item{display:flex;align-items:flex-start;gap:10px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04)}
  .cs-item:last-child{border-bottom:none}
  .cs-code{font-family:'Share Tech Mono',monospace;font-size:.78rem;color:var(--glow-cyan);background:rgba(0,245,255,.06);padding:2px 8px;border-radius:3px;white-space:nowrap;flex-shrink:0;border:1px solid rgba(0,245,255,.15)}
  .cs-desc{font-size:.82rem;color:var(--text-dim);line-height:1.4;padding-top:2px}
  .cs-badge-row{display:flex;gap:8px;flex-wrap:wrap;padding:6px 0}
  .cs-badge{font-family:'Share Tech Mono',monospace;font-size:.7rem;padding:3px 10px;border-radius:3px;border:1px solid;cursor:pointer;transition:.2s}
  .cs-badge:hover{opacity:.7}
  .cs-source{font-family:'Share Tech Mono',monospace;font-size:.7rem;color:var(--text-dim);text-align:right;padding:10px 18px 12px;border-top:1px solid var(--border)}
  .cs-source a{color:var(--glow-purple);text-decoration:none}
  .cs-source a:hover{color:var(--glow-cyan)}

  /* LEADERBOARD */
  .leaderboard-section{background:var(--bg2)}
  .leaderboard-table{max-width:800px;margin:0 auto;background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden}
  .lb-header{display:grid;grid-template-columns:60px 1fr 120px 100px 100px;padding:16px 24px;background:var(--bg2);border-bottom:1px solid var(--border);font-family:'Share Tech Mono',monospace;font-size:.7rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase}
  .lb-row{display:grid;grid-template-columns:60px 1fr 120px 100px 100px;padding:16px 24px;border-bottom:1px solid var(--border);align-items:center;transition:.2s}
  .lb-row:hover{background:rgba(255,255,255,.02)}.lb-row:last-child{border-bottom:none}
  .lb-rank{font-family:'Orbitron',monospace;font-size:1.1rem;font-weight:700}
  .rank-1{color:var(--gold);text-shadow:0 0 15px rgba(255,215,0,.5)}.rank-2{color:#c0c0c0}.rank-3{color:#cd7f32}
  .lb-player{display:flex;align-items:center;gap:12px}
  .player-avatar{width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-family:'Orbitron',monospace;font-size:.8rem;font-weight:700}
  .player-name{font-family:'Share Tech Mono',monospace;font-size:.9rem;color:#fff}
  .player-title{font-size:.75rem;color:var(--text-dim);margin-top:2px}
  .lb-xp{font-family:'Orbitron',monospace;font-size:.85rem;color:var(--gold)}
  .lb-level{font-family:'Share Tech Mono',monospace;font-size:.8rem;color:var(--glow-purple)}
  .lb-streak{font-family:'Share Tech Mono',monospace;font-size:.8rem;color:var(--glow-green)}

  /* HOW IT WORKS */
  .how-section{background:var(--bg2)}
  .steps-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:36px;max-width:1200px;margin:0 auto}
  .step-card{text-align:center;padding:40px 24px;background:var(--panel);border:1px solid var(--border);border-radius:8px;position:relative;transition:.3s}
  .step-card:hover{transform:translateY(-6px);border-color:var(--glow-cyan);box-shadow:0 10px 40px rgba(0,0,0,.4)}
  .step-num{font-family:'Orbitron',monospace;font-size:3.5rem;font-weight:900;color:rgba(0,245,255,.08);position:absolute;top:10px;right:16px;line-height:1}
  .step-icon-wrap{width:72px;height:72px;border-radius:12px;background:rgba(0,245,255,.07);border:1px solid rgba(0,245,255,.2);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;font-size:1.8rem}
  .step-title{font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;color:#fff;margin-bottom:12px}
  .step-desc{font-size:.9rem;color:var(--text-dim);line-height:1.6}

  /* CTA */
  .cta-section{background:var(--bg);text-align:center;padding:120px 40px;position:relative;overflow:hidden}
  .cta-glow{position:absolute;width:600px;height:400px;border-radius:50%;background:radial-gradient(ellipse,rgba(0,245,255,.06) 0%,transparent 70%);top:50%;left:50%;transform:translate(-50%,-50%);animation:ctaGlow 4s ease-in-out infinite}
  @keyframes ctaGlow{0%,100%{opacity:.7;transform:translate(-50%,-50%) scale(1)}50%{opacity:1;transform:translate(-50%,-50%) scale(1.15)}}
  .cta-title{font-family:'Orbitron',monospace;font-size:clamp(2rem,5vw,4rem);font-weight:900;color:#fff;margin-bottom:20px;position:relative;z-index:1}
  .cta-title span{color:var(--glow-cyan)}
  .cta-sub{font-size:1.1rem;color:var(--text-dim);max-width:500px;margin:0 auto 50px;position:relative;z-index:1}

  /* FOOTER */
  footer{position:relative;z-index:2;background:var(--bg2);border-top:1px solid var(--border);padding:50px 60px 30px}
  .footer-top{display:flex;justify-content:space-between;flex-wrap:wrap;gap:30px;margin-bottom:40px}
  .footer-logo{font-family:'Orbitron',monospace;font-size:1.5rem;font-weight:900;color:var(--glow-cyan);margin-bottom:12px}
  .footer-tagline{font-size:.9rem;color:var(--text-dim);max-width:260px}
  .footer-links-group h4{font-family:'Share Tech Mono',monospace;font-size:.75rem;letter-spacing:3px;color:var(--text-dim);text-transform:uppercase;margin-bottom:16px}
  .footer-links-group a{display:block;color:var(--text-dim);text-decoration:none;font-size:.9rem;margin-bottom:10px;transition:.2s}
  .footer-links-group a:hover{color:var(--glow-cyan)}
  .footer-bottom{border-top:1px solid var(--border);padding-top:24px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
  .footer-copy{font-family:'Share Tech Mono',monospace;font-size:.75rem;color:var(--text-dim)}
  .footer-langs{display:flex;gap:16px}
  .footer-lang-dot{width:10px;height:10px;border-radius:50%;animation:dotPulse 2s ease-in-out infinite}
  .footer-lang-dot:nth-child(1){background:var(--html-color)}.footer-lang-dot:nth-child(2){background:var(--css-color);animation-delay:.4s}.footer-lang-dot:nth-child(3){background:var(--js-color);animation-delay:.8s}.footer-lang-dot:nth-child(4){background:var(--py-color);animation-delay:1.2s}.footer-lang-dot:nth-child(5){background:#888;animation-delay:1.6s}
  @keyframes dotPulse{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.4);opacity:1}}

  /* TERMINAL */
  .terminal-demo{max-width:700px;margin:60px auto 0;background:#0a0f1a;border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.6),0 0 40px rgba(0,245,255,.05)}
  .terminal-bar{background:#0f1620;padding:12px 18px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border)}
  .dot{width:12px;height:12px;border-radius:50%}.dot-red{background:#ff5f57}.dot-yellow{background:#febc2e}.dot-green{background:#28c840}
  .terminal-title{font-family:'Share Tech Mono',monospace;font-size:.75rem;color:var(--text-dim);margin-left:10px}
  .terminal-body{padding:24px;font-family:'Share Tech Mono',monospace;font-size:.9rem;min-height:160px}
  .t-line{margin-bottom:8px;line-height:1.6}.t-prompt{color:var(--glow-cyan)}.t-comment{color:#5a7090}.t-string{color:#ffd700}.t-keyword{color:var(--glow-purple)}.t-fn{color:var(--glow-green)}.t-output{color:var(--glow-cyan);opacity:.8}
  .t-cursor{display:inline-block;width:8px;height:15px;background:var(--glow-cyan);animation:blink 1.1s step-end infinite;vertical-align:middle}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

  /* MODALS */
  .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(6px)}
  .modal-overlay.active{display:flex}
  .modal{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:40px;width:90%;max-width:480px;position:relative;box-shadow:0 0 60px rgba(0,245,255,.1);animation:modalIn .3s ease}
  @keyframes modalIn{from{opacity:0;transform:scale(.95) translateY(-20px)}to{opacity:1;transform:scale(1) translateY(0)}}
  .modal-close{position:absolute;top:16px;right:20px;background:none;border:none;color:var(--text-dim);font-size:1.4rem;cursor:pointer;transition:.2s}
  .modal-close:hover{color:#fff}
  .modal-title{font-family:'Orbitron',monospace;font-size:1.4rem;font-weight:700;color:#fff;margin-bottom:8px}
  .modal-sub{font-size:.9rem;color:var(--text-dim);margin-bottom:28px}
  .modal-tabs{display:flex;margin-bottom:28px;border:1px solid var(--border);border-radius:6px;overflow:hidden}
  .modal-tab{flex:1;padding:10px;background:transparent;border:none;color:var(--text-dim);font-family:'Orbitron',monospace;font-size:.7rem;letter-spacing:2px;cursor:pointer;text-transform:uppercase;transition:.2s}
  .modal-tab.active{background:rgba(0,245,255,.1);color:var(--glow-cyan)}
  .form-group{margin-bottom:18px}
  .form-label{display:block;font-family:'Share Tech Mono',monospace;font-size:.75rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;margin-bottom:8px}
  .form-input{width:100%;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px 16px;color:#fff;font-family:'Share Tech Mono',monospace;font-size:.9rem;outline:none;transition:.3s}
  .form-input:focus{border-color:var(--glow-cyan);box-shadow:0 0 0 2px rgba(0,245,255,.1)}
  .form-submit{width:100%;padding:14px;background:linear-gradient(135deg,var(--glow-cyan),#0090aa);color:#000;font-family:'Orbitron',monospace;font-size:.8rem;letter-spacing:2px;font-weight:700;border:none;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s;margin-top:8px}
  .form-submit:hover{box-shadow:0 0 25px rgba(0,245,255,.5);transform:translateY(-1px)}
  .form-error{color:var(--glow-pink);font-family:'Share Tech Mono',monospace;font-size:.8rem;margin-top:12px;min-height:20px}

  /* CHALLENGE MODAL */
  .challenge-modal{max-width:720px}
  .challenge-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px}
  .challenge-title{font-family:'Orbitron',monospace;font-size:1.2rem;color:#fff}
  .challenge-desc{font-size:.95rem;color:var(--text-dim);line-height:1.6;margin-bottom:20px}
  .challenge-hint{background:rgba(0,245,255,.05);border:1px solid rgba(0,245,255,.15);border-radius:6px;padding:12px 16px;font-size:.85rem;color:var(--glow-cyan);margin-bottom:20px}
  .challenge-hint::before{content:'💡 Hint: '}
  .code-editor{width:100%;min-height:180px;background:#0a0f1a;border:1px solid var(--border);border-radius:6px;padding:16px;color:#c8d8f0;font-family:'Share Tech Mono',monospace;font-size:.88rem;outline:none;resize:vertical;transition:.3s;line-height:1.6}
  .code-editor:focus{border-color:var(--glow-cyan)}
  .challenge-actions{display:flex;gap:12px;margin-top:14px}
  .btn-run{flex:1;padding:12px;background:linear-gradient(135deg,var(--glow-cyan),#0090aa);color:#000;font-family:'Orbitron',monospace;font-size:.75rem;letter-spacing:2px;font-weight:700;border:none;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s}
  .btn-run:hover{box-shadow:0 0 20px rgba(0,245,255,.4)}
  .btn-next{flex:1;padding:12px;background:linear-gradient(135deg,var(--glow-green),#1a8a00);color:#000;font-family:'Orbitron',monospace;font-size:.75rem;letter-spacing:2px;font-weight:700;border:none;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s;animation:nextPulse 1.5s ease-in-out infinite}
  .btn-next:hover{box-shadow:0 0 20px rgba(57,255,20,.6);transform:translateY(-1px)}
  @keyframes nextPulse{0%,100%{box-shadow:0 0 10px rgba(57,255,20,.3)}50%{box-shadow:0 0 25px rgba(57,255,20,.7)}}
  .btn-reset{padding:12px 20px;background:transparent;border:1px solid var(--border);color:var(--text-dim);font-family:'Orbitron',monospace;font-size:.7rem;letter-spacing:2px;border-radius:4px;cursor:pointer;text-transform:uppercase;transition:.3s}
  .btn-reset:hover{border-color:var(--text-dim);color:#fff}
  .result-box{margin-top:14px;padding:14px 16px;border-radius:6px;font-family:'Share Tech Mono',monospace;font-size:.88rem;display:none}
  .result-box.pass{background:rgba(57,255,20,.08);border:1px solid rgba(57,255,20,.3);color:var(--glow-green);display:block}
  .result-box.fail{background:rgba(255,0,127,.08);border:1px solid rgba(255,0,127,.3);color:var(--glow-pink);display:block}
  .result-box.loading{background:rgba(0,245,255,.05);border:1px solid rgba(0,245,255,.2);color:var(--glow-cyan);display:block}

  /* TOAST */
  .toast{position:fixed;bottom:30px;right:30px;z-index:2000;background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px 24px;font-family:'Share Tech Mono',monospace;font-size:.85rem;max-width:320px;box-shadow:0 10px 40px rgba(0,0,0,.4);transform:translateY(100px);opacity:0;transition:all .4s cubic-bezier(.175,.885,.32,1.275)}
  .toast.show{transform:translateY(0);opacity:1}
  .toast.xp{border-color:var(--gold);color:var(--gold)}.toast.level{border-color:var(--glow-purple);color:var(--glow-purple)}.toast.error{border-color:var(--glow-pink);color:var(--glow-pink)}

  @keyframes fadeSlideDown{from{opacity:0;transform:translateY(-20px)}to{opacity:1;transform:translateY(0)}}
  @media(max-width:900px){nav{padding:14px 24px}.nav-links{display:none}section{padding:70px 24px}.stats-bar{grid-template-columns:repeat(2,1fr)}footer{padding:40px 24px 24px}.lb-header,.lb-row{grid-template-columns:40px 1fr 80px 80px}.lb-header>*:nth-child(4),.lb-row>*:nth-child(4){display:none}.cs-tabs{flex-wrap:wrap}}
</style>
</head>
<body>
<canvas id="starfield"></canvas>
<div class="cursor" id="cursor"></div>
<div class="cursor-dot" id="cursorDot"></div>
<div class="toast" id="toast"></div>

<!-- AUTH MODAL -->
<div class="modal-overlay" id="authModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('authModal')">✕</button>
    <div class="modal-title">Welcome Back</div>
    <div class="modal-sub">Sign in to track XP and climb the leaderboard.</div>
    <div class="modal-tabs">
      <button class="modal-tab active" onclick="switchTab('login')">Login</button>
      <button class="modal-tab" onclick="switchTab('register')">Register</button>
    </div>
    <div id="loginForm">
      <div class="form-group"><label class="form-label">Username</label><input class="form-input" id="loginUser" placeholder="xShadow_dev"></div>
      <div class="form-group"><label class="form-label">Password</label><input class="form-input" type="password" id="loginPass" placeholder="••••••••"></div>
      <button class="form-submit" onclick="doLogin()">Enter the Arena</button>
      <div class="form-error" id="loginErr"></div>
    </div>
    <div id="registerForm" style="display:none">
      <div class="form-group"><label class="form-label">Username</label><input class="form-input" id="regUser" placeholder="xShadow_dev"></div>
      <div class="form-group"><label class="form-label">Email</label><input class="form-input" type="email" id="regEmail" placeholder="you@example.com"></div>
      <div class="form-group"><label class="form-label">Password</label><input class="form-input" type="password" id="regPass" placeholder="Min 6 characters"></div>
      <button class="form-submit" onclick="doRegister()">Create Account</button>
      <div class="form-error" id="regErr"></div>
    </div>
  </div>
</div>

<!-- CHALLENGE MODAL -->
<div class="modal-overlay" id="challengeModal">
  <div class="modal challenge-modal">
    <button class="modal-close" onclick="closeModal('challengeModal')">✕</button>
    <div class="challenge-header">
      <div><div class="challenge-title" id="chalTitle">Challenge</div><div style="margin-top:6px;display:flex;gap:8px" id="chalMeta"></div></div>
      <div class="game-xp" id="chalXP">★ 0 XP</div>
    </div>
    <div class="challenge-desc" id="chalDesc"></div>
    <div class="challenge-hint" id="chalHint"></div>
    <textarea class="code-editor" id="codeEditor" spellcheck="false"></textarea>
    <div class="challenge-actions">
      <button class="btn-run" onclick="runCode()">▶ Run &amp; Submit</button>
      <button class="btn-next" id="btnNext" onclick="nextChallenge()" style="display:none">→ Next Quest</button>
      <button class="btn-reset" onclick="resetCode()">↺ Reset</button>
    </div>
    <div class="result-box" id="resultBox"></div>
  </div>
</div>

<!-- NAV -->
<nav>
  <div class="nav-logo">CODE<span style="color:#fff">QUEST</span></div>
  <div class="nav-links">
    <a href="#languages">Languages</a>
    <a href="#games">Games</a>
    <a href="#cheatsheet">Cheat Sheets</a>
    <a href="#leaderboard">Leaderboard</a>
    <a href="#howto">How It Works</a>
  </div>
  <div class="nav-right">
    <div class="nav-xp" id="navXP" style="display:none">
      <span id="navLevel">LVL 1</span>
      <div class="xp-bar"><div class="xp-fill" id="navXPBar"></div></div>
      <span style="color:var(--text-dim)" id="navXPVal">0 XP</span>
    </div>
    <button class="nav-auth-btn" id="navAuthBtn" onclick="openModal('authModal')">Sign In</button>
    <button class="nav-auth-btn logout" id="navLogoutBtn" style="display:none" onclick="doLogout()">Logout</button>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="lang-orbit">
    <div class="orbit-tag html">HTML</div><div class="orbit-tag css">CSS</div>
    <div class="orbit-tag js">JS</div><div class="orbit-tag py">Python</div>
    <div class="orbit-tag c">C</div>
  </div>
  <div class="hero-badge">⚡ GAMIFIED LEARNING PLATFORM</div>
  <h1 class="hero-title"><span class="line1">LEVEL UP YOUR</span><span class="line2">CODE SKILLS</span></h1>
  <p class="hero-sub">Learn <em>HTML, CSS, Python, JavaScript &amp; C</em> by defeating coding challenges, solving puzzles, and climbing the leaderboard.</p>
  <div class="hero-btns">
    <a href="#languages" class="btn-primary">Start Playing</a>
    <a href="#cheatsheet" class="btn-secondary">Cheat Sheets</a>
  </div>
  <div class="terminal-demo" style="position:relative;z-index:5">
    <div class="terminal-bar"><div class="dot dot-red"></div><div class="dot dot-yellow"></div><div class="dot dot-green"></div><span class="terminal-title">codequest_terminal.py — bash</span></div>
    <div class="terminal-body" id="typingTerminal">
      <div class="t-line"><span class="t-comment"># CodeQuest — 51 challenges across 5 languages</span></div>
      <div class="t-line"><span class="t-comment"># + Full cheat sheets from OverAPI.com</span></div>
    </div>
  </div>
  <div class="scroll-hint"><span></span></div>
</section>

<!-- STATS -->
<div class="stats-bar">
  <div class="stat-item"><span class="stat-num" id="activePlayersCount">0</span><div class="stat-label">Active Players</div></div>
  <div class="stat-item"><span class="stat-num" data-target="51">0</span><div class="stat-label">Coding Challenges</div></div>
  <div class="stat-item"><span class="stat-num" data-target="5">0</span><div class="stat-label">Languages</div></div>
  <div class="stat-item"><span class="stat-num" data-target="5">0</span><div class="stat-label">Cheat Sheets</div></div>
</div>

<!-- LANGUAGE CARDS -->
<section id="languages">
  <div class="section-header"><span class="section-tag">// choose your weapon</span><h2 class="section-title">Pick a <span class="accent">Language</span></h2></div>
  <div class="lang-grid">
    <div class="lang-card html-card">
      <div class="card-icon">HTML</div><div class="card-lang-name">HTML5</div>
      <div class="card-desc">Build the skeleton of the web. Structure pages, create forms, embed media, and write semantic code that search engines love.</div>
      <div class="card-progress-label"><span>Your Progress</span><span id="prog-html">0%</span></div>
      <div class="card-progress-bar"><div class="card-progress-fill" id="fill-html" style="width:0%"></div></div>
      <div class="card-badges"><span class="badge">Beginner Friendly</span><span class="badge">13 Challenges</span><span class="badge">2580 XP</span></div>
      <button class="card-play-btn" onclick="openLangChallenges('html')">Play Now</button>
    </div>
    <div class="lang-card css-card">
      <div class="card-icon">CSS</div><div class="card-lang-name">CSS3</div>
      <div class="card-desc">Style the web with flair. Master layouts, animations, responsive design, and make websites look like magic.</div>
      <div class="card-progress-label"><span>Your Progress</span><span id="prog-css">0%</span></div>
      <div class="card-progress-bar"><div class="card-progress-fill" id="fill-css" style="width:0%"></div></div>
      <div class="card-badges"><span class="badge">Beginner Friendly</span><span class="badge">12 Challenges</span><span class="badge">2550 XP</span></div>
      <button class="card-play-btn" onclick="openLangChallenges('css')">Play Now</button>
    </div>
    <div class="lang-card js-card">
      <div class="card-icon">JS</div><div class="card-lang-name">JavaScript</div>
      <div class="card-desc">Bring the web to life. Control behavior, handle events, fetch data, and build interactive experiences users can't put down.</div>
      <div class="card-progress-label"><span>Your Progress</span><span id="prog-javascript">0%</span></div>
      <div class="card-progress-bar"><div class="card-progress-fill" id="fill-javascript" style="width:0%"></div></div>
      <div class="card-badges"><span class="badge">Intermediate</span><span class="badge">13 Challenges</span><span class="badge">3480 XP</span></div>
      <button class="card-play-btn" onclick="openLangChallenges('javascript')">Play Now</button>
    </div>
    <div class="lang-card py-card">
      <div class="card-icon">PY</div><div class="card-lang-name">Python</div>
      <div class="card-desc">The snake that eats problems whole. Automate tasks, analyze data, build AI models, and write clean elegant code.</div>
      <div class="card-progress-label"><span>Your Progress</span><span id="prog-python">0%</span></div>
      <div class="card-progress-bar"><div class="card-progress-fill" id="fill-python" style="width:0%"></div></div>
      <div class="card-badges"><span class="badge">Beginner Friendly</span><span class="badge">13 Challenges</span><span class="badge">3490 XP</span></div>
      <button class="card-play-btn" onclick="openLangChallenges('python')">Play Now</button>
    </div>
    <div class="lang-card c-card">
      <div class="card-icon" style="font-size:1.8rem">C</div><div class="card-lang-name">C Language</div>
      <div class="card-desc">The grandfather of all languages. Go low-level, manage memory manually, and understand how computers really work.</div>
      <div class="card-progress-label"><span>Your Progress</span><span id="prog-c">0%</span></div>
      <div class="card-progress-bar"><div class="card-progress-fill" id="fill-c" style="width:0%"></div></div>
      <div class="card-badges"><span class="badge">Hard Mode</span><span class="badge">12 Challenges</span><span class="badge">4620 XP</span></div>
      <button class="card-play-btn" onclick="openLangChallenges('c')">Play Now</button>
    </div>
  </div>
</section>

<!-- FEATURED GAMES -->
<section id="games" class="games-section">
  <div class="section-header"><span class="section-tag">// featured missions</span><h2 class="section-title">Choose Your <span class="accent">Mission</span></h2></div>
  <div class="games-grid">
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-html"><div class="thumb-grid"></div><div class="thumb-particles" id="p1"></div></div><div class="thumb-icon" style="color:var(--html-color);text-shadow:0 0 30px rgba(227,76,38,.7)">&lt;/&gt;</div><span class="game-difficulty diff-easy">Easy</span></div><div class="game-info"><div class="game-name">Tag Tyrant</div><div class="game-desc">Fix broken HTML tags against the clock. Build valid document structure to rescue the broken webpage.</div><div class="game-meta"><span class="game-lang-tag tag-html">HTML</span><span class="game-xp">★ 150 XP</span></div><button class="game-play-btn" onclick="openChallenge(1)">Launch Mission</button></div></div>
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-css"><div class="thumb-grid"></div><div class="thumb-particles" id="p2"></div></div><div class="thumb-icon" style="color:var(--css-color);text-shadow:0 0 30px rgba(38,77,228,.7)">{ }</div><span class="game-difficulty diff-med">Medium</span></div><div class="game-info"><div class="game-name">Flexbox Dungeon</div><div class="game-desc">Navigate through puzzle rooms using only CSS Flexbox properties. Each level unlocks a new dimension of layout power.</div><div class="game-meta"><span class="game-lang-tag tag-css">CSS</span><span class="game-xp">★ 220 XP</span></div><button class="game-play-btn" onclick="openChallenge(16)">Launch Mission</button></div></div>
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-js"><div class="thumb-grid"></div><div class="thumb-particles" id="p3"></div></div><div class="thumb-icon" style="color:var(--js-color);text-shadow:0 0 30px rgba(247,223,30,.7)">( )</div><span class="game-difficulty diff-hard">Hard</span></div><div class="game-info"><div class="game-name">Async Abyss</div><div class="game-desc">Dive deep into callbacks, promises, and async/await. Survive the asynchronous void without losing your mind.</div><div class="game-meta"><span class="game-lang-tag tag-js">JavaScript</span><span class="game-xp">★ 350 XP</span></div><button class="game-play-btn" onclick="openChallenge(26)">Launch Mission</button></div></div>
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-py"><div class="thumb-grid"></div><div class="thumb-particles" id="p4"></div></div><div class="thumb-icon" style="color:var(--py-color);text-shadow:0 0 30px rgba(53,114,165,.7)">🐍</div><span class="game-difficulty diff-easy">Easy</span></div><div class="game-info"><div class="game-name">Snake Puzzle</div><div class="game-desc">Decode Python logic puzzles. Loops, lists, and comprehensions await the brave.</div><div class="game-meta"><span class="game-lang-tag tag-py">Python</span><span class="game-xp">★ 150 XP</span></div><button class="game-play-btn" onclick="openChallenge(39)">Launch Mission</button></div></div>
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-c"><div class="thumb-grid"></div><div class="thumb-particles" id="p5"></div></div><div class="thumb-icon" style="color:#aaa;text-shadow:0 0 30px rgba(170,170,170,.5);font-size:3rem">C</div><span class="game-difficulty diff-hard">Hard</span></div><div class="game-info"><div class="game-name">Pointer Pandemonium</div><div class="game-desc">Navigate the treacherous world of C pointers and memory. One wrong move = segfault.</div><div class="game-meta"><span class="game-lang-tag tag-c">C</span><span class="game-xp">★ 500 XP</span></div><button class="game-play-btn" onclick="openChallenge(53)">Launch Mission</button></div></div>
    <div class="game-card"><div class="game-thumb"><div class="game-thumb-bg thumb-mixed"><div class="thumb-grid"></div><div class="thumb-particles" id="p6"></div></div><div class="thumb-icon" style="font-size:1.5rem;color:var(--glow-cyan);text-shadow:0 0 30px rgba(0,245,255,.7)">ALL<br>STAR</div><span class="game-difficulty diff-hard">Legend</span></div><div class="game-info"><div class="game-name">Caesar Cipher</div><div class="game-desc">Encode a secret message using the classic Caesar cipher. Shift letters, wrap the alphabet, crack the code.</div><div class="game-meta"><span class="game-lang-tag tag-py">Python</span><span class="game-xp">★ 400 XP</span></div><button class="game-play-btn" onclick="openChallenge(50)">Launch Mission</button></div></div>
  </div>
</section>

<!-- ════════════════════════════════════════════
     CHEAT SHEET SECTION (data from OverAPI.com)
════════════════════════════════════════════ -->
<section id="cheatsheet" class="cheatsheet-section">
  <div class="section-header">
    <span class="section-tag">// quick reference · source: overapi.com</span>
    <h2 class="section-title">Cheat <span class="accent">Sheets</span></h2>
  </div>

  <!-- TAB BAR -->
  <div class="cs-tabs">
    <button class="cs-tab active" onclick="showCS('cs-python')">🐍 Python</button>
    <button class="cs-tab" onclick="showCS('cs-js')">⚡ JavaScript</button>
    <button class="cs-tab" onclick="showCS('cs-html')">🌐 HTML</button>
    <button class="cs-tab" onclick="showCS('cs-css')">🎨 CSS</button>
    <button class="cs-tab" onclick="showCS('cs-c')">⚙ C</button>
  </div>

  <!-- ── PYTHON ── -->
  <div class="cs-panel active" id="cs-python">
    <div class="cs-grid">

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">String Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.upper()</span><span class="cs-desc">Convert string to uppercase</span></div>
          <div class="cs-item"><span class="cs-code">.lower()</span><span class="cs-desc">Convert string to lowercase</span></div>
          <div class="cs-item"><span class="cs-code">.strip()</span><span class="cs-desc">Remove leading/trailing whitespace</span></div>
          <div class="cs-item"><span class="cs-code">.split(sep)</span><span class="cs-desc">Split string into list by separator</span></div>
          <div class="cs-item"><span class="cs-code">.join(iter)</span><span class="cs-desc">Join iterable into string</span></div>
          <div class="cs-item"><span class="cs-code">.replace(a,b)</span><span class="cs-desc">Replace all occurrences of a with b</span></div>
          <div class="cs-item"><span class="cs-code">.find(sub)</span><span class="cs-desc">Return lowest index where sub found</span></div>
          <div class="cs-item"><span class="cs-code">.startswith(p)</span><span class="cs-desc">Return True if string starts with p</span></div>
          <div class="cs-item"><span class="cs-code">.endswith(s)</span><span class="cs-desc">Return True if string ends with s</span></div>
          <div class="cs-item"><span class="cs-code">.format(*a)</span><span class="cs-desc">Format string with arguments</span></div>
          <div class="cs-item"><span class="cs-code">.count(sub)</span><span class="cs-desc">Count non-overlapping occurrences</span></div>
          <div class="cs-item"><span class="cs-code">.isdigit()</span><span class="cs-desc">True if all characters are digits</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">List Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.append(x)</span><span class="cs-desc">Add item x to end of list</span></div>
          <div class="cs-item"><span class="cs-code">.extend(it)</span><span class="cs-desc">Extend list by appending iterable</span></div>
          <div class="cs-item"><span class="cs-code">.insert(i,x)</span><span class="cs-desc">Insert x before index i</span></div>
          <div class="cs-item"><span class="cs-code">.remove(x)</span><span class="cs-desc">Remove first occurrence of x</span></div>
          <div class="cs-item"><span class="cs-code">.pop([i])</span><span class="cs-desc">Remove and return item at index i</span></div>
          <div class="cs-item"><span class="cs-code">.sort()</span><span class="cs-desc">Sort list in place</span></div>
          <div class="cs-item"><span class="cs-code">.reverse()</span><span class="cs-desc">Reverse list in place</span></div>
          <div class="cs-item"><span class="cs-code">.index(x)</span><span class="cs-desc">Return index of first occurrence of x</span></div>
          <div class="cs-item"><span class="cs-code">.count(x)</span><span class="cs-desc">Count occurrences of x</span></div>
          <div class="cs-item"><span class="cs-code">.copy()</span><span class="cs-desc">Return shallow copy of list</span></div>
          <div class="cs-item"><span class="cs-code">.clear()</span><span class="cs-desc">Remove all items from list</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">Dict Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.keys()</span><span class="cs-desc">Return view of all keys</span></div>
          <div class="cs-item"><span class="cs-code">.values()</span><span class="cs-desc">Return view of all values</span></div>
          <div class="cs-item"><span class="cs-code">.items()</span><span class="cs-desc">Return view of (key, value) pairs</span></div>
          <div class="cs-item"><span class="cs-code">.get(k,d)</span><span class="cs-desc">Return value for k, or default d</span></div>
          <div class="cs-item"><span class="cs-code">.update(d2)</span><span class="cs-desc">Update dict with key/value pairs from d2</span></div>
          <div class="cs-item"><span class="cs-code">.pop(k)</span><span class="cs-desc">Remove key k and return its value</span></div>
          <div class="cs-item"><span class="cs-code">.setdefault(k,v)</span><span class="cs-desc">Set key k to v if not present</span></div>
          <div class="cs-item"><span class="cs-code">.copy()</span><span class="cs-desc">Return shallow copy of dictionary</span></div>
          <div class="cs-item"><span class="cs-code">.clear()</span><span class="cs-desc">Remove all items from dictionary</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">Built-in Functions</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">len(s)</span><span class="cs-desc">Return length of object</span></div>
          <div class="cs-item"><span class="cs-code">range(n)</span><span class="cs-desc">Generate range of numbers</span></div>
          <div class="cs-item"><span class="cs-code">type(x)</span><span class="cs-desc">Return type of object x</span></div>
          <div class="cs-item"><span class="cs-code">print(*a)</span><span class="cs-desc">Print to standard output</span></div>
          <div class="cs-item"><span class="cs-code">input(p)</span><span class="cs-desc">Read input from user with prompt</span></div>
          <div class="cs-item"><span class="cs-code">int(x)</span><span class="cs-desc">Convert x to integer</span></div>
          <div class="cs-item"><span class="cs-code">str(x)</span><span class="cs-desc">Convert x to string</span></div>
          <div class="cs-item"><span class="cs-code">list(it)</span><span class="cs-desc">Convert iterable to list</span></div>
          <div class="cs-item"><span class="cs-code">sorted(it)</span><span class="cs-desc">Return sorted list from iterable</span></div>
          <div class="cs-item"><span class="cs-code">enumerate(it)</span><span class="cs-desc">Return (index, value) pairs</span></div>
          <div class="cs-item"><span class="cs-code">zip(a,b)</span><span class="cs-desc">Zip two iterables together</span></div>
          <div class="cs-item"><span class="cs-code">map(fn,it)</span><span class="cs-desc">Apply function to each item</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">File Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">open(f,mode)</span><span class="cs-desc">Open file — modes: r, w, a, rb, wb</span></div>
          <div class="cs-item"><span class="cs-code">.read()</span><span class="cs-desc">Read entire file as string</span></div>
          <div class="cs-item"><span class="cs-code">.readline()</span><span class="cs-desc">Read one line from file</span></div>
          <div class="cs-item"><span class="cs-code">.readlines()</span><span class="cs-desc">Read all lines into a list</span></div>
          <div class="cs-item"><span class="cs-code">.write(s)</span><span class="cs-desc">Write string s to file</span></div>
          <div class="cs-item"><span class="cs-code">.close()</span><span class="cs-desc">Close the file handle</span></div>
          <div class="cs-item"><span class="cs-code">with open() as f</span><span class="cs-desc">Context manager — auto closes file</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--py-color)"><span style="color:var(--py-color)">Set Operations</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.add(x)</span><span class="cs-desc">Add element x to set</span></div>
          <div class="cs-item"><span class="cs-code">.remove(x)</span><span class="cs-desc">Remove x from set (KeyError if missing)</span></div>
          <div class="cs-item"><span class="cs-code">.discard(x)</span><span class="cs-desc">Remove x if present (no error)</span></div>
          <div class="cs-item"><span class="cs-code">.union(s2)</span><span class="cs-desc">Return new set with all elements</span></div>
          <div class="cs-item"><span class="cs-code">.intersection(s2)</span><span class="cs-desc">Return elements common to both sets</span></div>
          <div class="cs-item"><span class="cs-code">.difference(s2)</span><span class="cs-desc">Return elements in set but not s2</span></div>
          <div class="cs-item"><span class="cs-code">.issubset(s2)</span><span class="cs-desc">True if all elements are in s2</span></div>
          <div class="cs-item"><span class="cs-code">x in s</span><span class="cs-desc">Test membership in set</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/python" target="_blank">overapi.com/python ↗</a></div>
      </div>

    </div>
  </div>

  <!-- ── JAVASCRIPT ── -->
  <div class="cs-panel" id="cs-js">
    <div class="cs-grid">

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--js-color)"><span style="color:var(--js-color)">Array Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.push(x)</span><span class="cs-desc">Add x to end, return new length</span></div>
          <div class="cs-item"><span class="cs-code">.pop()</span><span class="cs-desc">Remove and return last element</span></div>
          <div class="cs-item"><span class="cs-code">.shift()</span><span class="cs-desc">Remove and return first element</span></div>
          <div class="cs-item"><span class="cs-code">.unshift(x)</span><span class="cs-desc">Add x to beginning, return new length</span></div>
          <div class="cs-item"><span class="cs-code">.map(fn)</span><span class="cs-desc">Create new array from return values of fn</span></div>
          <div class="cs-item"><span class="cs-code">.filter(fn)</span><span class="cs-desc">Create new array of elements where fn is true</span></div>
          <div class="cs-item"><span class="cs-code">.reduce(fn,v)</span><span class="cs-desc">Reduce array to single value</span></div>
          <div class="cs-item"><span class="cs-code">.find(fn)</span><span class="cs-desc">Return first element where fn is true</span></div>
          <div class="cs-item"><span class="cs-code">.indexOf(x)</span><span class="cs-desc">Return index of x, -1 if not found</span></div>
          <div class="cs-item"><span class="cs-code">.includes(x)</span><span class="cs-desc">True if array contains x</span></div>
          <div class="cs-item"><span class="cs-code">.sort(fn)</span><span class="cs-desc">Sort array in place</span></div>
          <div class="cs-item"><span class="cs-code">.splice(i,n)</span><span class="cs-desc">Remove n elements starting at index i</span></div>
          <div class="cs-item"><span class="cs-code">.slice(a,b)</span><span class="cs-desc">Return new array from index a to b</span></div>
          <div class="cs-item"><span class="cs-code">.flat(d)</span><span class="cs-desc">Flatten nested array to depth d</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/javascript" target="_blank">overapi.com/javascript ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--js-color)"><span style="color:var(--js-color)">String Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">.charAt(i)</span><span class="cs-desc">Return character at index i</span></div>
          <div class="cs-item"><span class="cs-code">.indexOf(s)</span><span class="cs-desc">Return position of first s found</span></div>
          <div class="cs-item"><span class="cs-code">.includes(s)</span><span class="cs-desc">True if string contains s</span></div>
          <div class="cs-item"><span class="cs-code">.slice(a,b)</span><span class="cs-desc">Extract characters from a to b</span></div>
          <div class="cs-item"><span class="cs-code">.split(sep)</span><span class="cs-desc">Split string into array by sep</span></div>
          <div class="cs-item"><span class="cs-code">.replace(a,b)</span><span class="cs-desc">Replace a with b</span></div>
          <div class="cs-item"><span class="cs-code">.toUpperCase()</span><span class="cs-desc">Convert to uppercase</span></div>
          <div class="cs-item"><span class="cs-code">.toLowerCase()</span><span class="cs-desc">Convert to lowercase</span></div>
          <div class="cs-item"><span class="cs-code">.trim()</span><span class="cs-desc">Remove whitespace from both ends</span></div>
          <div class="cs-item"><span class="cs-code">.padStart(n,c)</span><span class="cs-desc">Pad start with character c to length n</span></div>
          <div class="cs-item"><span class="cs-code">.repeat(n)</span><span class="cs-desc">Return string repeated n times</span></div>
          <div class="cs-item"><span class="cs-code">.match(rx)</span><span class="cs-desc">Match string against a RegExp</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/javascript" target="_blank">overapi.com/javascript ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--js-color)"><span style="color:var(--js-color)">Math Methods</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">Math.abs(x)</span><span class="cs-desc">Absolute value of x</span></div>
          <div class="cs-item"><span class="cs-code">Math.ceil(x)</span><span class="cs-desc">Round x up to nearest integer</span></div>
          <div class="cs-item"><span class="cs-code">Math.floor(x)</span><span class="cs-desc">Round x down to nearest integer</span></div>
          <div class="cs-item"><span class="cs-code">Math.round(x)</span><span class="cs-desc">Round x to nearest integer</span></div>
          <div class="cs-item"><span class="cs-code">Math.max(...n)</span><span class="cs-desc">Return the highest value</span></div>
          <div class="cs-item"><span class="cs-code">Math.min(...n)</span><span class="cs-desc">Return the lowest value</span></div>
          <div class="cs-item"><span class="cs-code">Math.pow(x,y)</span><span class="cs-desc">Return x to the power of y</span></div>
          <div class="cs-item"><span class="cs-code">Math.sqrt(x)</span><span class="cs-desc">Return square root of x</span></div>
          <div class="cs-item"><span class="cs-code">Math.random()</span><span class="cs-desc">Return random number 0 to 1</span></div>
          <div class="cs-item"><span class="cs-code">Math.PI</span><span class="cs-desc">Pi constant (~3.14159)</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/javascript" target="_blank">overapi.com/javascript ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--js-color)"><span style="color:var(--js-color)">Object &amp; JSON</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">Object.keys(o)</span><span class="cs-desc">Return array of object's own keys</span></div>
          <div class="cs-item"><span class="cs-code">Object.values(o)</span><span class="cs-desc">Return array of object's own values</span></div>
          <div class="cs-item"><span class="cs-code">Object.entries(o)</span><span class="cs-desc">Return array of [key, value] pairs</span></div>
          <div class="cs-item"><span class="cs-code">Object.assign(t,s)</span><span class="cs-desc">Copy s properties into target t</span></div>
          <div class="cs-item"><span class="cs-code">{...obj}</span><span class="cs-desc">Spread / shallow clone an object</span></div>
          <div class="cs-item"><span class="cs-code">JSON.stringify(o)</span><span class="cs-desc">Convert object to JSON string</span></div>
          <div class="cs-item"><span class="cs-code">JSON.parse(s)</span><span class="cs-desc">Parse JSON string to object</span></div>
          <div class="cs-item"><span class="cs-code">delete obj.k</span><span class="cs-desc">Remove property k from object</span></div>
          <div class="cs-item"><span class="cs-code">'k' in obj</span><span class="cs-desc">Check if key k exists in object</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/javascript" target="_blank">overapi.com/javascript ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--js-color)"><span style="color:var(--js-color)">ES6+ Features</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">const / let</span><span class="cs-desc">Block-scoped variable declarations</span></div>
          <div class="cs-item"><span class="cs-code">x => x * 2</span><span class="cs-desc">Arrow function syntax</span></div>
          <div class="cs-item"><span class="cs-code">`${x}`</span><span class="cs-desc">Template literal string interpolation</span></div>
          <div class="cs-item"><span class="cs-code">...arr</span><span class="cs-desc">Spread operator — expand array/object</span></div>
          <div class="cs-item"><span class="cs-code">async / await</span><span class="cs-desc">Handle promises with cleaner syntax</span></div>
          <div class="cs-item"><span class="cs-code">class Name{}</span><span class="cs-desc">ES6 class declaration</span></div>
          <div class="cs-item"><span class="cs-code">import / export</span><span class="cs-desc">ES module import/export syntax</span></div>
          <div class="cs-item"><span class="cs-code">?? (nullish)</span><span class="cs-desc">Return right side if left is null/undefined</span></div>
          <div class="cs-item"><span class="cs-code">?. (optional)</span><span class="cs-desc">Access property only if object exists</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/javascript" target="_blank">overapi.com/javascript ↗</a></div>
      </div>

    </div>
  </div>

  <!-- ── HTML ── -->
  <div class="cs-panel" id="cs-html">
    <div class="cs-grid">

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--html-color)"><span style="color:var(--html-color)">Basic Tags</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">&lt;!DOCTYPE html&gt;</span><span class="cs-desc">Defines document type — always first</span></div>
          <div class="cs-item"><span class="cs-code">&lt;html&gt;</span><span class="cs-desc">Root element of HTML page</span></div>
          <div class="cs-item"><span class="cs-code">&lt;head&gt;</span><span class="cs-desc">Container for meta data</span></div>
          <div class="cs-item"><span class="cs-code">&lt;body&gt;</span><span class="cs-desc">Contains visible page content</span></div>
          <div class="cs-item"><span class="cs-code">&lt;h1&gt;–&lt;h6&gt;</span><span class="cs-desc">Heading levels 1 (largest) to 6</span></div>
          <div class="cs-item"><span class="cs-code">&lt;p&gt;</span><span class="cs-desc">Paragraph element</span></div>
          <div class="cs-item"><span class="cs-code">&lt;br&gt;</span><span class="cs-desc">Line break (self-closing)</span></div>
          <div class="cs-item"><span class="cs-code">&lt;hr&gt;</span><span class="cs-desc">Horizontal rule / divider line</span></div>
          <div class="cs-item"><span class="cs-code">&lt;div&gt;</span><span class="cs-desc">Generic block container</span></div>
          <div class="cs-item"><span class="cs-code">&lt;span&gt;</span><span class="cs-desc">Generic inline container</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/html" target="_blank">overapi.com/html ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--html-color)"><span style="color:var(--html-color)">Links &amp; Media</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">&lt;a href=""&gt;</span><span class="cs-desc">Anchor / hyperlink element</span></div>
          <div class="cs-item"><span class="cs-code">&lt;img src="" alt=""&gt;</span><span class="cs-desc">Embed image with alt description</span></div>
          <div class="cs-item"><span class="cs-code">&lt;video src="" controls&gt;</span><span class="cs-desc">Embed HTML5 video with controls</span></div>
          <div class="cs-item"><span class="cs-code">&lt;audio src="" controls&gt;</span><span class="cs-desc">Embed audio player</span></div>
          <div class="cs-item"><span class="cs-code">&lt;iframe src=""&gt;</span><span class="cs-desc">Embed another webpage inline</span></div>
          <div class="cs-item"><span class="cs-code">target="_blank"</span><span class="cs-desc">Open link in new tab</span></div>
          <div class="cs-item"><span class="cs-code">rel="noopener"</span><span class="cs-desc">Security attr for external links</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/html" target="_blank">overapi.com/html ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--html-color)"><span style="color:var(--html-color)">Lists &amp; Tables</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">&lt;ul&gt; / &lt;ol&gt;</span><span class="cs-desc">Unordered / ordered list</span></div>
          <div class="cs-item"><span class="cs-code">&lt;li&gt;</span><span class="cs-desc">List item inside ul or ol</span></div>
          <div class="cs-item"><span class="cs-code">&lt;dl&gt;</span><span class="cs-desc">Definition list</span></div>
          <div class="cs-item"><span class="cs-code">&lt;dt&gt; / &lt;dd&gt;</span><span class="cs-desc">Definition term / description</span></div>
          <div class="cs-item"><span class="cs-code">&lt;table&gt;</span><span class="cs-desc">HTML table element</span></div>
          <div class="cs-item"><span class="cs-code">&lt;tr&gt;</span><span class="cs-desc">Table row</span></div>
          <div class="cs-item"><span class="cs-code">&lt;th&gt; / &lt;td&gt;</span><span class="cs-desc">Header cell / data cell</span></div>
          <div class="cs-item"><span class="cs-code">colspan="2"</span><span class="cs-desc">Span cell across 2 columns</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/html" target="_blank">overapi.com/html ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--html-color)"><span style="color:var(--html-color)">Forms &amp; Inputs</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">&lt;form action method&gt;</span><span class="cs-desc">HTML form — action=URL, method=GET/POST</span></div>
          <div class="cs-item"><span class="cs-code">&lt;input type="text"&gt;</span><span class="cs-desc">Text input field</span></div>
          <div class="cs-item"><span class="cs-code">&lt;input type="email"&gt;</span><span class="cs-desc">Email input with validation</span></div>
          <div class="cs-item"><span class="cs-code">&lt;input type="password"&gt;</span><span class="cs-desc">Password input (masked)</span></div>
          <div class="cs-item"><span class="cs-code">&lt;input type="checkbox"&gt;</span><span class="cs-desc">Checkbox toggle</span></div>
          <div class="cs-item"><span class="cs-code">&lt;select&gt; / &lt;option&gt;</span><span class="cs-desc">Dropdown select list</span></div>
          <div class="cs-item"><span class="cs-code">&lt;textarea&gt;</span><span class="cs-desc">Multi-line text input</span></div>
          <div class="cs-item"><span class="cs-code">&lt;button type="submit"&gt;</span><span class="cs-desc">Form submit button</span></div>
          <div class="cs-item"><span class="cs-code">placeholder=""</span><span class="cs-desc">Hint text inside empty input</span></div>
          <div class="cs-item"><span class="cs-code">required</span><span class="cs-desc">Field must be filled before submit</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/html" target="_blank">overapi.com/html ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--html-color)"><span style="color:var(--html-color)">Semantic HTML5</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">&lt;header&gt;</span><span class="cs-desc">Page or section header</span></div>
          <div class="cs-item"><span class="cs-code">&lt;nav&gt;</span><span class="cs-desc">Navigation links container</span></div>
          <div class="cs-item"><span class="cs-code">&lt;main&gt;</span><span class="cs-desc">Main content of the document</span></div>
          <div class="cs-item"><span class="cs-code">&lt;section&gt;</span><span class="cs-desc">Thematic section of content</span></div>
          <div class="cs-item"><span class="cs-code">&lt;article&gt;</span><span class="cs-desc">Self-contained piece of content</span></div>
          <div class="cs-item"><span class="cs-code">&lt;aside&gt;</span><span class="cs-desc">Tangentially related content / sidebar</span></div>
          <div class="cs-item"><span class="cs-code">&lt;footer&gt;</span><span class="cs-desc">Footer of document or section</span></div>
          <div class="cs-item"><span class="cs-code">&lt;figure&gt;</span><span class="cs-desc">Self-contained image/diagram with caption</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/html" target="_blank">overapi.com/html ↗</a></div>
      </div>

    </div>
  </div>

  <!-- ── CSS ── -->
  <div class="cs-panel" id="cs-css">
    <div class="cs-grid">

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Box Model</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">margin</span><span class="cs-desc">Space outside the border — shorthand for all 4 sides</span></div>
          <div class="cs-item"><span class="cs-code">padding</span><span class="cs-desc">Space inside the border — shorthand for all 4 sides</span></div>
          <div class="cs-item"><span class="cs-code">border</span><span class="cs-desc">Border around element — width style color</span></div>
          <div class="cs-item"><span class="cs-code">border-radius</span><span class="cs-desc">Round corners — px or % value</span></div>
          <div class="cs-item"><span class="cs-code">box-shadow</span><span class="cs-desc">Shadow — x y blur spread color</span></div>
          <div class="cs-item"><span class="cs-code">width / height</span><span class="cs-desc">Set element dimensions</span></div>
          <div class="cs-item"><span class="cs-code">max-width</span><span class="cs-desc">Maximum width constraint</span></div>
          <div class="cs-item"><span class="cs-code">box-sizing: border-box</span><span class="cs-desc">Include padding/border in width/height</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Selectors</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">*</span><span class="cs-desc">Universal selector — targets everything</span></div>
          <div class="cs-item"><span class="cs-code">.class</span><span class="cs-desc">Class selector</span></div>
          <div class="cs-item"><span class="cs-code">#id</span><span class="cs-desc">ID selector</span></div>
          <div class="cs-item"><span class="cs-code">a b</span><span class="cs-desc">Descendant — b inside any a</span></div>
          <div class="cs-item"><span class="cs-code">a > b</span><span class="cs-desc">Direct child — b directly inside a</span></div>
          <div class="cs-item"><span class="cs-code">a + b</span><span class="cs-desc">Adjacent sibling — b immediately after a</span></div>
          <div class="cs-item"><span class="cs-code">:hover</span><span class="cs-desc">Element on mouse hover</span></div>
          <div class="cs-item"><span class="cs-code">:focus</span><span class="cs-desc">Element currently focused</span></div>
          <div class="cs-item"><span class="cs-code">:nth-child(n)</span><span class="cs-desc">nth child element</span></div>
          <div class="cs-item"><span class="cs-code">::before / ::after</span><span class="cs-desc">Insert generated content before/after element</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Flexbox</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">display: flex</span><span class="cs-desc">Enable flexbox on container</span></div>
          <div class="cs-item"><span class="cs-code">flex-direction</span><span class="cs-desc">row | column | row-reverse | column-reverse</span></div>
          <div class="cs-item"><span class="cs-code">justify-content</span><span class="cs-desc">Align items on main axis</span></div>
          <div class="cs-item"><span class="cs-code">align-items</span><span class="cs-desc">Align items on cross axis</span></div>
          <div class="cs-item"><span class="cs-code">flex-wrap</span><span class="cs-desc">wrap | nowrap — allow items to wrap</span></div>
          <div class="cs-item"><span class="cs-code">gap</span><span class="cs-desc">Space between flex items</span></div>
          <div class="cs-item"><span class="cs-code">flex: 1</span><span class="cs-desc">Flex grow, shrink, and basis shorthand</span></div>
          <div class="cs-item"><span class="cs-code">align-self</span><span class="cs-desc">Override align-items for single item</span></div>
          <div class="cs-item"><span class="cs-code">order</span><span class="cs-desc">Change visual order of flex item</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Grid</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">display: grid</span><span class="cs-desc">Enable CSS grid on container</span></div>
          <div class="cs-item"><span class="cs-code">grid-template-columns</span><span class="cs-desc">Define column sizes — e.g. repeat(3, 1fr)</span></div>
          <div class="cs-item"><span class="cs-code">grid-template-rows</span><span class="cs-desc">Define row sizes</span></div>
          <div class="cs-item"><span class="cs-code">gap</span><span class="cs-desc">Space between grid cells</span></div>
          <div class="cs-item"><span class="cs-code">grid-column</span><span class="cs-desc">Span item across columns — e.g. 1 / 3</span></div>
          <div class="cs-item"><span class="cs-code">grid-row</span><span class="cs-desc">Span item across rows</span></div>
          <div class="cs-item"><span class="cs-code">place-items</span><span class="cs-desc">Shorthand for align + justify items</span></div>
          <div class="cs-item"><span class="cs-code">1fr</span><span class="cs-desc">Fractional unit — share available space</span></div>
          <div class="cs-item"><span class="cs-code">minmax(200px,1fr)</span><span class="cs-desc">Column min 200px, max fills space</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Typography</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">font-family</span><span class="cs-desc">Set font — use quotes for multi-word names</span></div>
          <div class="cs-item"><span class="cs-code">font-size</span><span class="cs-desc">Size in px, rem, em, vw, %</span></div>
          <div class="cs-item"><span class="cs-code">font-weight</span><span class="cs-desc">100–900 or bold / normal</span></div>
          <div class="cs-item"><span class="cs-code">line-height</span><span class="cs-desc">Space between lines — unitless recommended</span></div>
          <div class="cs-item"><span class="cs-code">letter-spacing</span><span class="cs-desc">Space between characters</span></div>
          <div class="cs-item"><span class="cs-code">text-align</span><span class="cs-desc">left | center | right | justify</span></div>
          <div class="cs-item"><span class="cs-code">text-decoration</span><span class="cs-desc">none | underline | line-through</span></div>
          <div class="cs-item"><span class="cs-code">text-transform</span><span class="cs-desc">uppercase | lowercase | capitalize</span></div>
          <div class="cs-item"><span class="cs-code">text-shadow</span><span class="cs-desc">x y blur color</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--css-color)"><span style="color:var(--css-color)">Positioning &amp; Display</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">position: static</span><span class="cs-desc">Default — normal document flow</span></div>
          <div class="cs-item"><span class="cs-code">position: relative</span><span class="cs-desc">Offset from normal position</span></div>
          <div class="cs-item"><span class="cs-code">position: absolute</span><span class="cs-desc">Remove from flow, relative to nearest positioned ancestor</span></div>
          <div class="cs-item"><span class="cs-code">position: fixed</span><span class="cs-desc">Fixed relative to viewport</span></div>
          <div class="cs-item"><span class="cs-code">position: sticky</span><span class="cs-desc">Scroll then stick at threshold</span></div>
          <div class="cs-item"><span class="cs-code">z-index</span><span class="cs-desc">Stack order — higher = on top</span></div>
          <div class="cs-item"><span class="cs-code">display: none</span><span class="cs-desc">Hide element, remove from layout</span></div>
          <div class="cs-item"><span class="cs-code">visibility: hidden</span><span class="cs-desc">Hide element but keep space</span></div>
          <div class="cs-item"><span class="cs-code">overflow</span><span class="cs-desc">visible | hidden | scroll | auto</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/css" target="_blank">overapi.com/css ↗</a></div>
      </div>

    </div>
  </div>

  <!-- ── C ── -->
  <div class="cs-panel" id="cs-c">
    <div class="cs-grid">

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">Data Types</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">int</span><span class="cs-desc">Integer — typically 4 bytes</span></div>
          <div class="cs-item"><span class="cs-code">float</span><span class="cs-desc">Single-precision floating point</span></div>
          <div class="cs-item"><span class="cs-code">double</span><span class="cs-desc">Double-precision floating point</span></div>
          <div class="cs-item"><span class="cs-code">char</span><span class="cs-desc">Single character — 1 byte</span></div>
          <div class="cs-item"><span class="cs-code">long</span><span class="cs-desc">Long integer — at least 4 bytes</span></div>
          <div class="cs-item"><span class="cs-code">short</span><span class="cs-desc">Short integer — at least 2 bytes</span></div>
          <div class="cs-item"><span class="cs-code">void</span><span class="cs-desc">No type — used for functions returning nothing</span></div>
          <div class="cs-item"><span class="cs-code">unsigned</span><span class="cs-desc">Non-negative integers only</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">Operators</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">+ - * / %</span><span class="cs-desc">Arithmetic operators</span></div>
          <div class="cs-item"><span class="cs-code">== != &lt; &gt; &lt;= &gt;=</span><span class="cs-desc">Comparison operators</span></div>
          <div class="cs-item"><span class="cs-code">&amp;&amp; || !</span><span class="cs-desc">Logical AND, OR, NOT</span></div>
          <div class="cs-item"><span class="cs-code">&amp; | ^ ~ &lt;&lt; &gt;&gt;</span><span class="cs-desc">Bitwise AND, OR, XOR, NOT, shifts</span></div>
          <div class="cs-item"><span class="cs-code">++ --</span><span class="cs-desc">Increment / Decrement</span></div>
          <div class="cs-item"><span class="cs-code">+= -= *= /=</span><span class="cs-desc">Compound assignment operators</span></div>
          <div class="cs-item"><span class="cs-code">? :</span><span class="cs-desc">Ternary operator — cond ? a : b</span></div>
          <div class="cs-item"><span class="cs-code">sizeof(x)</span><span class="cs-desc">Return size of type or variable in bytes</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">Pointers &amp; Memory</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">int *p</span><span class="cs-desc">Declare pointer to int</span></div>
          <div class="cs-item"><span class="cs-code">p = &amp;x</span><span class="cs-desc">Assign address of x to pointer p</span></div>
          <div class="cs-item"><span class="cs-code">*p</span><span class="cs-desc">Dereference pointer — access value at address</span></div>
          <div class="cs-item"><span class="cs-code">p++</span><span class="cs-desc">Pointer arithmetic — advance to next element</span></div>
          <div class="cs-item"><span class="cs-code">malloc(n)</span><span class="cs-desc">Allocate n bytes on heap — returns void*</span></div>
          <div class="cs-item"><span class="cs-code">calloc(n,size)</span><span class="cs-desc">Allocate n elements, zero-initialized</span></div>
          <div class="cs-item"><span class="cs-code">realloc(p,n)</span><span class="cs-desc">Resize previously allocated block</span></div>
          <div class="cs-item"><span class="cs-code">free(p)</span><span class="cs-desc">Free dynamically allocated memory</span></div>
          <div class="cs-item"><span class="cs-code">NULL</span><span class="cs-desc">Null pointer constant</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">Standard Library (stdio.h)</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">printf(fmt,...)</span><span class="cs-desc">Print formatted output to stdout</span></div>
          <div class="cs-item"><span class="cs-code">scanf(fmt,...)</span><span class="cs-desc">Read formatted input from stdin</span></div>
          <div class="cs-item"><span class="cs-code">fopen(f,mode)</span><span class="cs-desc">Open file — modes: r, w, a, rb</span></div>
          <div class="cs-item"><span class="cs-code">fclose(fp)</span><span class="cs-desc">Close file pointer</span></div>
          <div class="cs-item"><span class="cs-code">fprintf(fp,fmt)</span><span class="cs-desc">Write formatted text to file</span></div>
          <div class="cs-item"><span class="cs-code">fgets(buf,n,fp)</span><span class="cs-desc">Read line from file into buffer</span></div>
          <div class="cs-item"><span class="cs-code">sprintf(buf,fmt)</span><span class="cs-desc">Write formatted string into buffer</span></div>
          <div class="cs-item"><span class="cs-code">%d %f %c %s</span><span class="cs-desc">Format specifiers: int, float, char, string</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">string.h Functions</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">strlen(s)</span><span class="cs-desc">Return length of string s</span></div>
          <div class="cs-item"><span class="cs-code">strcpy(dst,src)</span><span class="cs-desc">Copy src into dst</span></div>
          <div class="cs-item"><span class="cs-code">strncpy(d,s,n)</span><span class="cs-desc">Copy at most n chars from s to d</span></div>
          <div class="cs-item"><span class="cs-code">strcat(dst,src)</span><span class="cs-desc">Concatenate src onto end of dst</span></div>
          <div class="cs-item"><span class="cs-code">strcmp(a,b)</span><span class="cs-desc">Compare two strings — 0 if equal</span></div>
          <div class="cs-item"><span class="cs-code">strstr(s,sub)</span><span class="cs-desc">Find substring sub in s</span></div>
          <div class="cs-item"><span class="cs-code">memset(p,v,n)</span><span class="cs-desc">Set n bytes starting at p to value v</span></div>
          <div class="cs-item"><span class="cs-code">memcpy(d,s,n)</span><span class="cs-desc">Copy n bytes from s to d</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

      <div class="cs-card">
        <div class="cs-card-header" style="border-left:3px solid var(--c-color)"><span style="color:#aaa">Control Flow</span></div>
        <div class="cs-card-body">
          <div class="cs-item"><span class="cs-code">if / else if / else</span><span class="cs-desc">Conditional branching</span></div>
          <div class="cs-item"><span class="cs-code">switch(x) { case n: }</span><span class="cs-desc">Multi-way branch on integer/char</span></div>
          <div class="cs-item"><span class="cs-code">for(init;cond;inc)</span><span class="cs-desc">Count-controlled loop</span></div>
          <div class="cs-item"><span class="cs-code">while(cond)</span><span class="cs-desc">Condition-controlled loop</span></div>
          <div class="cs-item"><span class="cs-code">do { } while(cond)</span><span class="cs-desc">Execute body at least once</span></div>
          <div class="cs-item"><span class="cs-code">break</span><span class="cs-desc">Exit innermost loop or switch</span></div>
          <div class="cs-item"><span class="cs-code">continue</span><span class="cs-desc">Skip to next iteration of loop</span></div>
          <div class="cs-item"><span class="cs-code">return val</span><span class="cs-desc">Return value from function</span></div>
          <div class="cs-item"><span class="cs-code">goto label</span><span class="cs-desc">Jump to label (use sparingly)</span></div>
        </div>
        <div class="cs-source"><a href="https://overapi.com/c" target="_blank">overapi.com/c ↗</a></div>
      </div>

    </div>
  </div>

</section>

<!-- LEADERBOARD -->
<section id="leaderboard" class="leaderboard-section">
  <div class="section-header"><span class="section-tag">// global rankings</span><h2 class="section-title">Hall of <span class="accent">Fame</span></h2></div>
  <div class="leaderboard-table">
    <div class="lb-header"><span>Rank</span><span>Player</span><span>XP</span><span>Streak</span><span>Level</span></div>
    <div id="lbBody">
      <div class="lb-row"><div class="lb-rank rank-1">🥇</div><div class="lb-player"><div class="player-avatar" style="background:rgba(227,76,38,.15);color:var(--html-color);border:1px solid rgba(227,76,38,.3)">XS</div><div><div class="player-name">xShadow_dev</div><div class="player-title">Full Stack Legend</div></div></div><div class="lb-xp">48,200</div><div class="lb-streak">🔥 142</div><div class="lb-level">LVL 50</div></div>
      <div class="lb-row"><div class="lb-rank rank-2">🥈</div><div class="lb-player"><div class="player-avatar" style="background:rgba(53,114,165,.15);color:var(--py-color);border:1px solid rgba(53,114,165,.3)">PQ</div><div><div class="player-name">PyQueen</div><div class="player-title">Python Master</div></div></div><div class="lb-xp">41,500</div><div class="lb-streak">🔥 89</div><div class="lb-level">LVL 44</div></div>
      <div class="lb-row"><div class="lb-rank rank-3">🥉</div><div class="lb-player"><div class="player-avatar" style="background:rgba(247,223,30,.1);color:var(--js-color);border:1px solid rgba(247,223,30,.3)">NX</div><div><div class="player-name">NullX</div><div class="player-title">JS Wizard</div></div></div><div class="lb-xp">38,900</div><div class="lb-streak">🔥 67</div><div class="lb-level">LVL 41</div></div>
    </div>
  </div>
</section>

<!-- HOW IT WORKS -->
<section id="howto" class="how-section">
  <div class="section-header"><span class="section-tag">// game mechanics</span><h2 class="section-title">How to <span class="accent">Play</span></h2></div>
  <div class="steps-grid">
    <div class="step-card"><div class="step-num">01</div><div class="step-icon-wrap">🎯</div><div class="step-title">Pick a Quest</div><div class="step-desc">Choose from 5 programming languages. Each has 10–13 challenges of increasing difficulty.</div></div>
    <div class="step-card"><div class="step-num">02</div><div class="step-icon-wrap" style="background:rgba(191,0,255,.07);border-color:rgba(191,0,255,.2)">⚔️</div><div class="step-title">Code &amp; Battle</div><div class="step-desc">Write real code in the in-browser editor. Submit to run against automated test cases.</div></div>
    <div class="step-card"><div class="step-num">03</div><div class="step-icon-wrap" style="background:rgba(57,255,20,.07);border-color:rgba(57,255,20,.2)">⚡</div><div class="step-title">Earn XP &amp; Level Up</div><div class="step-desc">Every solved challenge earns XP with streak multipliers. Unlock titles from Newbie to CodeQuest Legend.</div></div>
    <div class="step-card"><div class="step-num">04</div><div class="step-icon-wrap" style="background:rgba(255,215,0,.07);border-color:rgba(255,215,0,.2)">🏆</div><div class="step-title">Dominate Rankings</div><div class="step-desc">Compete globally on the live leaderboard. Use the cheat sheets to study between battles.</div></div>
  </div>
</section>

<!-- CTA -->
<section class="cta-section">
  <div class="cta-glow"></div>
  <div class="hero-badge" style="display:inline-block;margin-bottom:30px">FREE TO PLAY · NO CREDIT CARD</div>
  <h2 class="cta-title">Ready to <span>Level Up?</span></h2>
  <p class="cta-sub">Join developers turning free time into coding superpowers. 51 challenges + 5 full cheat sheets.</p>
  <a href="#" class="btn-primary" style="display:inline-block;position:relative;z-index:1" onclick="openModal('authModal');return false">Create Free Account</a>
</section>

<!-- FOOTER -->
<footer>
  <div class="footer-top">
    <div><div class="footer-logo">CODE<span style="color:#fff">QUEST</span></div><div class="footer-tagline">Learn programming by playing games. Level up your career one line of code at a time.</div></div>
    <div class="footer-links-group"><h4>Languages</h4><a href="#" onclick="openLangChallenges('html');return false">HTML5</a><a href="#" onclick="openLangChallenges('css');return false">CSS3</a><a href="#" onclick="openLangChallenges('javascript');return false">JavaScript</a><a href="#" onclick="openLangChallenges('python');return false">Python</a><a href="#" onclick="openLangChallenges('c');return false">C Language</a></div>
    <div class="footer-links-group"><h4>Cheat Sheets</h4><a href="#" onclick="showCS('cs-python');document.getElementById('cheatsheet').scrollIntoView();return false">Python</a><a href="#" onclick="showCS('cs-js');document.getElementById('cheatsheet').scrollIntoView();return false">JavaScript</a><a href="#" onclick="showCS('cs-html');document.getElementById('cheatsheet').scrollIntoView();return false">HTML</a><a href="#" onclick="showCS('cs-css');document.getElementById('cheatsheet').scrollIntoView();return false">CSS</a><a href="#" onclick="showCS('cs-c');document.getElementById('cheatsheet').scrollIntoView();return false">C</a></div>
    <div class="footer-links-group"><h4>Platform</h4><a href="#leaderboard">Leaderboard</a><a href="#howto">How It Works</a><a href="#" onclick="openModal('authModal');return false">Sign In</a></div>
  </div>
  <div class="footer-bottom">
    <div class="footer-copy">© 2025 CODEQUEST. CHEAT SHEET DATA: OVERAPI.COM</div>
    <div class="footer-langs"><div class="footer-lang-dot"></div><div class="footer-lang-dot"></div><div class="footer-lang-dot"></div><div class="footer-lang-dot"></div><div class="footer-lang-dot"></div></div>
  </div>
</footer>

<script>
const API = '';

// ── CURSOR ──────────────────────────────────────────────────────
const cursor=document.getElementById('cursor'),cursorDot=document.getElementById('cursorDot');
let mx=0,my=0,cx=0,cy=0;
document.addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;cursorDot.style.left=mx+'px';cursorDot.style.top=my+'px';});
(function animCursor(){cx+=(mx-cx)*.15;cy+=(my-cy)*.15;cursor.style.left=cx+'px';cursor.style.top=cy+'px';requestAnimationFrame(animCursor);})();
document.querySelectorAll('button,a,.lang-card,.game-card,.step-card,.cs-card').forEach(el=>{
  el.addEventListener('mouseenter',()=>{cursor.style.width='40px';cursor.style.height='40px';cursor.style.borderColor='#bf00ff';cursor.style.boxShadow='0 0 15px #bf00ff';});
  el.addEventListener('mouseleave',()=>{cursor.style.width='16px';cursor.style.height='16px';cursor.style.borderColor='var(--glow-cyan)';cursor.style.boxShadow='0 0 10px var(--glow-cyan)';});
});

// ── STARFIELD ───────────────────────────────────────────────────
const canvas=document.getElementById('starfield'),ctx=canvas.getContext('2d');
let W,H,stars=[];
function resize(){W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight;}
resize();window.addEventListener('resize',resize);
for(let i=0;i<180;i++)stars.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.5+.2,speed:Math.random()*.3+.05,opacity:Math.random()*.6+.1});
(function drawStars(){ctx.clearRect(0,0,W,H);stars.forEach(s=>{ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fillStyle=`rgba(200,220,255,${s.opacity})`;ctx.fill();s.y+=s.speed;if(s.y>H){s.y=0;s.x=Math.random()*W;}});requestAnimationFrame(drawStars);})();

// ── COUNTERS ────────────────────────────────────────────────────
const obs=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){const t=parseInt(e.target.dataset.target);let s=0;const step=ts=>{if(!s)s=ts;const p=Math.min((ts-s)/2000,1);e.target.textContent=Math.floor(p*t).toLocaleString();if(p<1)requestAnimationFrame(step);else e.target.textContent=t.toLocaleString();};requestAnimationFrame(step);obs.unobserve(e.target);}});},{threshold:.5});
document.querySelectorAll('[data-target]').forEach(el=>obs.observe(el));

// ── PARTICLES ───────────────────────────────────────────────────
const tc={'p1':'#e34c26','p2':'#264de4','p3':'#f7df1e','p4':'#3572a5','p5':'#888','p6':'#00f5ff'};
Object.entries(tc).forEach(([id,color])=>{const c=document.getElementById(id);if(!c)return;for(let i=0;i<12;i++){const p=document.createElement('div');p.className='tp';p.style.cssText=`left:${Math.random()*100}%;background:${color};box-shadow:0 0 6px ${color};animation-duration:${3+Math.random()*4}s;animation-delay:${-Math.random()*5}s;`;c.appendChild(p);}});

// ── TERMINAL ────────────────────────────────────────────────────
const term=document.getElementById('typingTerminal');
[{text:'<span class="t-prompt">>>> </span><span class="t-keyword">def</span> <span class="t-fn">caesar</span>(text, shift):',delay:600},{text:'&nbsp;&nbsp;&nbsp;&nbsp;<span class="t-keyword">return</span> <span class="t-string">"".join</span>(...)',delay:1600},{text:'<span class="t-prompt">>>> </span><span class="t-fn">caesar</span>(<span class="t-string">"Hello"</span>, 3)',delay:2800},{text:'<span class="t-output">\'Khoor\'</span>',delay:3600},{text:'<span class="t-output">⚡ +400 XP Earned! Level Up!</span>',delay:4400}].forEach(({text,delay})=>{setTimeout(()=>{const l=document.createElement('div');l.className='t-line';l.innerHTML=text;term.appendChild(l);},delay);});
setTimeout(()=>{const l=document.createElement('div');l.className='t-line';l.innerHTML='<span class="t-prompt">>>> </span><span class="t-cursor"></span>';term.appendChild(l);},5300);

// ── SCROLL FADE ─────────────────────────────────────────────────
const fObs=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){e.target.style.opacity='1';e.target.style.transform='translateY(0)';}});},{threshold:.1});
document.querySelectorAll('.lang-card,.game-card,.step-card,.cs-card').forEach((el,i)=>{el.style.opacity='0';el.style.transform='translateY(30px)';el.style.transition=`opacity .6s ${i*.05}s ease,transform .6s ${i*.05}s ease,border-color .3s,box-shadow .3s`;fObs.observe(el);});

// ── CHEAT SHEET TABS ────────────────────────────────────────────
function showCS(id) {
  document.querySelectorAll('.cs-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.cs-tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  const order = ['cs-python','cs-js','cs-html','cs-css','cs-c'];
  document.querySelectorAll('.cs-tab')[order.indexOf(id)].classList.add('active');
}

// ── STATE ───────────────────────────────────────────────────────
let currentUser=null,currentChallenge=null,currentStarterCode='';

// ── TOAST ───────────────────────────────────────────────────────
function showToast(msg,type='',dur=3500){const t=document.getElementById('toast');t.textContent=msg;t.className=`toast ${type} show`;setTimeout(()=>t.classList.remove('show'),dur);}

// ── MODALS ──────────────────────────────────────────────────────
function openModal(id){document.getElementById(id).classList.add('active');}
function closeModal(id){document.getElementById(id).classList.remove('active');}
document.querySelectorAll('.modal-overlay').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('active');}));
function switchTab(tab){document.getElementById('loginForm').style.display=tab==='login'?'block':'none';document.getElementById('registerForm').style.display=tab==='register'?'block':'none';document.querySelectorAll('.modal-tab').forEach((t,i)=>t.classList.toggle('active',(tab==='login'&&i===0)||(tab==='register'&&i===1)));}

// ── API HELPERS ─────────────────────────────────────────────────
async function apiPost(url,body){const r=await fetch(url,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json();}
async function apiGet(url){const r=await fetch(url,{credentials:'include'});return r.json();}

// ── AUTH ────────────────────────────────────────────────────────
async function doLogin(){
  const user=document.getElementById('loginUser').value.trim(),pass=document.getElementById('loginPass').value;
  document.getElementById('loginErr').textContent='';
  const res=await apiPost('/api/auth/login',{username:user,password:pass});
  if(res.error){document.getElementById('loginErr').textContent=res.error;return;}
  currentUser=res;closeModal('authModal');updateNavUser();showToast(`⚡ Welcome back, ${res.username}!`,'xp');loadLeaderboard();loadProgress();
}
async function doRegister(){
  const user=document.getElementById('regUser').value.trim(),email=document.getElementById('regEmail').value.trim(),pass=document.getElementById('regPass').value;
  document.getElementById('regErr').textContent='';
  const res=await apiPost('/api/auth/register',{username:user,email,password:pass});
  if(res.error){document.getElementById('regErr').textContent=res.error;return;}
  currentUser=res;closeModal('authModal');updateNavUser();showToast(`🎉 Welcome, ${res.username}! Let's code!`,'xp');loadLeaderboard();
}
async function doLogout(){await apiPost('/api/auth/logout',{});currentUser=null;updateNavUser();showToast('Logged out. See you next time!');resetProgress();}

function updateNavUser(){
  const ab=document.getElementById('navAuthBtn'),lb=document.getElementById('navLogoutBtn'),xpEl=document.getElementById('navXP');
  if(currentUser){
    ab.style.display='none';lb.style.display='block';xpEl.style.display='flex';
    document.getElementById('navLevel').textContent=`LVL ${currentUser.level}`;
    document.getElementById('navXPVal').textContent=`${currentUser.xp} XP`;
    // update progress bar
    const lvl=currentUser.level,base=Math.floor(500*Math.pow(lvl-1,1.5)),next=Math.floor(500*Math.pow(lvl,1.5));
    const pct=next>base?Math.round(((currentUser.xp-base)/(next-base))*100):100;
    document.getElementById('navXPBar').style.width=Math.min(pct,100)+'%';
  } else {
    ab.style.display='block';lb.style.display='none';xpEl.style.display='none';
  }
}

// ── LEADERBOARD ─────────────────────────────────────────────────
async function loadLeaderboard(){
  const data=await apiGet('/api/leaderboard/?limit=10');
  if(!data.leaderboard)return;
  const emo=['🥇','🥈','🥉'],cls=['rank-1','rank-2','rank-3'];
  document.getElementById('lbBody').innerHTML=data.leaderboard.map((p,i)=>`
    <div class="lb-row" style="animation-delay:${i*.1}s">
      <div class="lb-rank ${cls[i]||''}">${emo[i]||p.rank}</div>
      <div class="lb-player"><div class="player-avatar" style="background:rgba(0,245,255,.1);color:var(--glow-cyan);border:1px solid rgba(0,245,255,.3)">${p.username.slice(0,2).toUpperCase()}</div><div><div class="player-name">${p.username}</div><div class="player-title">${p.title}</div></div></div>
      <div class="lb-xp">${p.xp.toLocaleString()}</div>
      <div class="lb-streak">🔥 ${p.streak}</div>
      <div class="lb-level">LVL ${p.level}</div>
    </div>`).join('');
}

// ── PROGRESS BARS ───────────────────────────────────────────────
async function loadProgress(){
  if(!currentUser)return;
  for(const lang of ['html','css','javascript','python','c']){
    const data=await apiGet(`/api/challenges/?language=${lang}`);
    if(!Array.isArray(data))continue;
    const pct=data.length?Math.round((data.filter(c=>c.completed).length/data.length)*100):0;
    const pe=document.getElementById(`prog-${lang}`),fe=document.getElementById(`fill-${lang}`);
    if(pe)pe.textContent=pct+'%';if(fe)fe.style.width=pct+'%';
  }
}
function resetProgress(){['html','css','javascript','python','c'].forEach(l=>{const p=document.getElementById(`prog-${l}`),f=document.getElementById(`fill-${l}`);if(p)p.textContent='0%';if(f)f.style.width='0%';});}

// ── CHALLENGE MODAL ─────────────────────────────────────────────
async function openChallenge(id){
  const ch=await apiGet(`/api/challenges/${id}`);
  if(ch.error){showToast('Challenge not found','error');return;}
  _showChallenge(ch);
}
async function openLangChallenges(lang){
  const list=await apiGet(`/api/challenges/?language=${lang}`);
  if(!list.length){showToast('No challenges found','error');return;}
  _showChallenge(list.find(c=>!c.completed)||list[0]);
}
function _showChallenge(ch){
  currentChallenge=ch;currentStarterCode=ch.starter_code||'';
  document.getElementById('chalTitle').textContent=ch.title;
  document.getElementById('chalDesc').textContent=ch.description;
  document.getElementById('chalXP').textContent=`★ ${ch.xp_reward} XP`;
  document.getElementById('chalHint').textContent=ch.hint||'';
  document.getElementById('chalHint').style.display=ch.hint?'block':'none';
  document.getElementById('codeEditor').value=ch.starter_code||'';
  document.getElementById('resultBox').className='result-box';
  document.getElementById('resultBox').textContent='';
  document.getElementById('btnNext').style.display='none';
  const dm={easy:'diff-easy',medium:'diff-med',hard:'diff-hard',legend:'diff-hard'};
  document.getElementById('chalMeta').innerHTML=`<span class="game-lang-tag tag-${ch.language}">${ch.language.toUpperCase()}</span><span class="game-difficulty ${dm[ch.difficulty]||'diff-med'}" style="position:static">${ch.difficulty}</span>`;
  openModal('challengeModal');
}
function resetCode(){document.getElementById('codeEditor').value=currentStarterCode;document.getElementById('resultBox').className='result-box';document.getElementById('resultBox').textContent='';document.getElementById('btnNext').style.display='none';}
async function runCode(){
  if(!currentUser){showToast('⚠ Sign in to submit and earn XP!','error');openModal('authModal');return;}
  const code=document.getElementById('codeEditor').value;
  const rb=document.getElementById('resultBox');
  rb.className='result-box loading';rb.textContent='⏳ Running your code...';
  const res=await apiPost(`/api/challenges/${currentChallenge.id}/submit`,{code});
  if(res.passed){
    rb.className='result-box pass';rb.textContent=res.feedback;
    document.getElementById('btnNext').style.display='flex';
    if(res.xp_result){
      currentUser.xp=res.xp_result.new_xp;currentUser.level=res.xp_result.new_level;
      updateNavUser();
      showToast(`⚡ +${res.xp_result.xp_earned} XP! (×${res.xp_result.streak_bonus} streak)`,'xp');
      if(res.xp_result.leveled_up) setTimeout(()=>showToast(`🏆 LEVEL UP! Level ${res.xp_result.new_level} — ${res.xp_result.new_title}!`,'level',5000),1500);
    }
    loadProgress();loadLeaderboard();loadActivePlayers();
  } else {
    rb.className='result-box fail';rb.textContent=res.feedback||res.error;
  }
}

// ── NEXT CHALLENGE ───────────────────────────────────────────────
let _langChallengeList=[];
async function nextChallenge(){
  const lang=currentChallenge.language;
  const list=await apiGet(`/api/challenges/?language=${lang}`);
  if(!list.length)return;
  const currentIdx=list.findIndex(c=>c.id===currentChallenge.id);
  const next=list.slice(currentIdx+1).find(c=>!c.completed)||list.find(c=>!c.completed&&c.id!==currentChallenge.id);
  if(next){
    _showChallenge(next);
  } else {
    showToast(`🎉 All ${lang.toUpperCase()} challenges complete!`,'level',4000);
    closeModal('challengeModal');
  }
}

// ── ACTIVE PLAYERS ───────────────────────────────────────────────
async function loadActivePlayers(){
  try{
    const data=await apiGet('/api/stats');
    const el=document.getElementById('activePlayersCount');
    if(!el)return;
    const target=data.active_players||0;
    let start=parseInt(el.textContent.replace(/,/g,''))||0;
    if(start===target){el.textContent=target.toLocaleString();return;}
    const duration=800,startTime=performance.now();
    function tick(now){
      const p=Math.min((now-startTime)/duration,1);
      el.textContent=Math.floor(start+(target-start)*p).toLocaleString();
      if(p<1)requestAnimationFrame(tick);else el.textContent=target.toLocaleString();
    }
    requestAnimationFrame(tick);
  }catch(e){}
}

// ── INIT ────────────────────────────────────────────────────────
(async function init(){
  try{const me=await apiGet('/api/auth/me');if(me.id){currentUser=me;updateNavUser();loadProgress();}}catch(e){}
  loadLeaderboard();
  loadActivePlayers();
})();
</script>
</body>
</html>"""

# ════════════════════════════════════════════════════════
#  SERVE THE FRONTEND
# ════════════════════════════════════════════════════════
@app.route('/')
def index():
    return Response(HTML, mimetype='text/html')


# ════════════════════════════════════════════════════════
#  STARTUP (Render / Production Ready)
# ════════════════════════════════════════════════════════
with app.app_context():
    init_db()

if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════╗")
    print("║        CODEQUEST IS STARTING         ║")
    print("╠══════════════════════════════════════╣")
    print("║  Running Flask production mode       ║")
    print("╚══════════════════════════════════════╝")
    print()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
