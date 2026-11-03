from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "library.db"
app = Flask(__name__)
app.secret_key = "change-this-secret-key"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            isbn TEXT UNIQUE,
            total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
            available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0)
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES books(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO books(title,author,category,isbn,total_copies,available_copies) VALUES(?,?,?,?,?,?)",
                [
                    ("The Alchemist", "Paulo Coelho", "Fiction", "9780061122415", 4, 4),
                    ("Clean Code", "Robert C. Martin", "Technology", "9780132350884", 3, 3),
                    ("Database System Concepts", "Silberschatz et al.", "Technology", "9780078022159", 2, 2),
                    ("Atomic Habits", "James Clear", "Self-help", "9780735211292", 5, 5),
                    ("The Hobbit", "J. R. R. Tolkien", "Fantasy", "9780547928227", 2, 2),
                ],
            )
        count = db.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO members(name,email,phone) VALUES(?,?,?)",
                [
                    ("Aarav Sharma", "aarav@example.com", "9876543210"),
                    ("Meera Singh", "meera@example.com", "9876501234"),
                    ("Kabir Verma", "kabir@example.com", "9123456780"),
                ],
            )


@app.route("/")
def index():
    with get_db() as db:
        stats = {
            "books": db.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
            "titles": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "members": db.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "issued": db.execute("SELECT COUNT(*) FROM loans WHERE return_date IS NULL").fetchone()[0],
            "overdue": db.execute("SELECT COUNT(*) FROM loans WHERE return_date IS NULL AND due_date < ?", (date.today().isoformat(),)).fetchone()[0],
        }
        recent = db.execute("""
            SELECT l.id, b.title, m.name, l.issue_date, l.due_date, l.return_date
            FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
            ORDER BY l.id DESC LIMIT 6
        """).fetchall()
    return render_template("index.html", stats=stats, recent=recent, today=date.today().isoformat())


@app.route("/books", methods=["GET", "POST"])
def books():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        isbn = request.form.get("isbn", "").strip() or None
        try:
            copies = max(0, int(request.form.get("copies", "1")))
            if not title or not author:
                raise ValueError("Title and author are required.")
            with get_db() as db:
                db.execute(
                    "INSERT INTO books(title,author,category,isbn,total_copies,available_copies) VALUES(?,?,?,?,?,?)",
                    (title, author, category, isbn, copies, copies),
                )
                db.execute("INSERT INTO audit_log(action,details) VALUES('ADD_BOOK',?)", (title,))
            flash("Book added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("ISBN already exists. Please use a unique ISBN.", "error")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("books"))
    q = request.args.get("q", "").strip()
    with get_db() as db:
        if q:
            rows = db.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ? ORDER BY title",
                              (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    return render_template("books.html", books=rows, q=q)


@app.route("/members", methods=["GET", "POST"])
def members():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            if not name or not email:
                raise ValueError("Name and email are required.")
            with get_db() as db:
                db.execute("INSERT INTO members(name,email,phone) VALUES(?,?,?)", (name, email, phone))
            flash("Member registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("members"))
    with get_db() as db:
        rows = db.execute("SELECT * FROM members ORDER BY name").fetchall()
    return render_template("members.html", members=rows)


@app.route("/loans", methods=["GET", "POST"])
def loans():
    if request.method == "POST":
        book_id = request.form.get("book_id", type=int)
        member_id = request.form.get("member_id", type=int)
        action = request.form.get("action", "issue")
        with get_db() as db:
            if action == "issue":
                book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
                if not book or not member_id:
                    flash("Choose a valid book and member.", "error")
                elif book["available_copies"] < 1:
                    flash("No available copies of this book.", "error")
                else:
                    issued = date.today()
                    due = issued + timedelta(days=14)
                    db.execute("INSERT INTO loans(book_id,member_id,issue_date,due_date) VALUES(?,?,?,?)",
                               (book_id, member_id, issued.isoformat(), due.isoformat()))
                    db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
                    db.execute("INSERT INTO audit_log(action,details) VALUES('ISSUE_BOOK',?)", (f"book={book_id}; member={member_id}",))
                    flash(f"Book issued. Due date: {due.isoformat()}.", "success")
            elif action == "return":
                loan_id = request.form.get("loan_id", type=int)
                loan = db.execute("SELECT * FROM loans WHERE id=? AND return_date IS NULL", (loan_id,)).fetchone()
                if not loan:
                    flash("Active loan not found.", "error")
                else:
                    returned = date.today()
                    due = date.fromisoformat(loan["due_date"])
                    overdue_days = max(0, (returned - due).days)
                    fine = overdue_days * 5.0
                    db.execute("UPDATE loans SET return_date=?, fine=? WHERE id=?", (returned.isoformat(), fine, loan_id))
                    db.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=?", (loan["book_id"],))
                    db.execute("INSERT INTO audit_log(action,details) VALUES('RETURN_BOOK',?)", (f"loan={loan_id}; fine={fine:.2f}",))
                    flash(f"Book returned. Fine: ₹{fine:.2f}", "success")
        return redirect(url_for("loans"))
    with get_db() as db:
        available_books = db.execute("SELECT id,title,available_copies FROM books WHERE available_copies>0 ORDER BY title").fetchall()
        members_list = db.execute("SELECT id,name FROM members ORDER BY name").fetchall()
        active = db.execute("""
            SELECT l.id, b.title, m.name, l.issue_date, l.due_date,
                   CASE WHEN l.due_date < ? THEN 1 ELSE 0 END AS overdue
            FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
            WHERE l.return_date IS NULL ORDER BY l.due_date
        """, (date.today().isoformat(),)).fetchall()
        history = db.execute("""
            SELECT l.id,b.title,m.name,l.issue_date,l.due_date,l.return_date,l.fine
            FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
            WHERE l.return_date IS NOT NULL ORDER BY l.id DESC LIMIT 10
        """).fetchall()
    return render_template("loans.html", available_books=available_books, members=members_list, active=active, history=history)


@app.route("/overdue")
def overdue():
    with get_db() as db:
        rows = db.execute("""
            SELECT l.id,b.title,m.name,m.email,l.due_date,
                   CAST(julianday(?) - julianday(l.due_date) AS INTEGER) AS days_late
            FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
            WHERE l.return_date IS NULL AND l.due_date < ? ORDER BY l.due_date
        """, (date.today().isoformat(), date.today().isoformat())).fetchall()
    return render_template("overdue.html", rows=rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
