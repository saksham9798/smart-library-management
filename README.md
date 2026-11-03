# Smart Library Management System

A small Flask web application for a library circulation desk. The web app runs locally with SQLite so it can be extracted and started without installing Oracle. The `oracle/` folder contains equivalent Oracle schema and PL/SQL examples for your PL/SQL coursework.

## Features
- Dashboard with book, member, active-loan, and overdue counts
- Add/search books
- Register members
- Issue books (14-day loan period)
- Return books and calculate overdue fine at ₹5/day
- Overdue list with estimated fines
- Basic audit log in the demo database
- Responsive sidebar/dashboard UI

## Run on Windows
1. Install Python 3.10 or newer.
2. Extract the ZIP.
3. Double-click `run_windows.bat` (or open a terminal in this folder and run it).
4. Open **http://127.0.0.1:5000** in your browser.

The first run installs Flask, creates `library.db`, and inserts sample books and members. To reset the demo data, stop the app and delete `library.db`; it will be recreated on the next run.

## Run on macOS/Linux
```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

## Oracle PL/SQL scripts
Use Oracle SQL Developer or SQL*Plus:
1. Connect to your Oracle schema.
2. Run `oracle/schema.sql`.
3. Run `oracle/library_pkg.sql`.
4. Run `oracle/audit_trigger.sql`.
5. Optionally run `oracle/sample_data.sql`.

Package examples:
- `LIBRARY_PKG.CALCULATE_FINE`: fine calculation function
- `LIBRARY_PKG.ISSUE_BOOK`: issues a book and updates availability
- `LIBRARY_PKG.RETURN_BOOK`: returns a book and calculates fine
- `LIBRARY_PKG.LIST_OVERDUE`: explicit cursor for overdue loans
- `TRG_LIB_LOAN_AUDIT`: audit trigger

**Note:** The included Flask UI uses SQLite by default for one-click local execution. The Oracle scripts are a separate PL/SQL implementation intended for SQL Developer/viva demonstration; this starter project does not connect Flask to Oracle.

## Project structure
```text
smart_library_management/
├── app.py
├── requirements.txt
├── run_windows.bat
├── run_mac_linux.sh
├── templates/
├── static/style.css
└── oracle/
    ├── schema.sql
    ├── library_pkg.sql
    ├── audit_trigger.sql
    └── sample_data.sql
```

## Demo login
No login is configured in this classroom demo. Do not deploy it publicly without adding authentication, CSRF protection, and production configuration.
