from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
import sqlite3
from markupsafe import escape
from datetime import datetime, timedelta
import re
import csv
import io
import os
import time
import shutil
app = Flask(__name__)
app.config["SECRET_KEY"] = "hospital_secret_key_123"
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)
load_dotenv()
csrf = CSRFProtect(app)
MANAGER_SECRET = os.getenv("MANAGER_SECRET")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_COOKIE_NAME"] = "basrah_lab_session"
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

socketio = SocketIO(

    app,

    cors_allowed_origins="*",

    async_mode="threading"

)


DB_NAME = "database.db"
# ===== حماية تسجيل الدخول =====

login_attempts = {}

MAX_TRIES = 12

BLOCK_TIME = 60

# ===== صفحة الأرشيف العام =====

@app.route("/archive")
def archive_page():

    if "role" not in session:
        return redirect("/")

    return render_template(
        "archive.html"
    )


# ===== صفحة أرشيف الشفت =====

@app.route("/shift_archive_page")
def shift_archive_page():

    if "role" not in session:
        return redirect("/")

    return render_template(
        "shift_archive.html"
    )

# ===== API الأرشيف العام =====

@app.route("/api/archive")
def api_archive():

    if "role" not in session:
        return jsonify([])

    search = request.args.get(
        "search",
        ""
    ).strip()

    date = request.args.get(
        "date",
        ""
    ).strip()

    section = request.args.get(
        "section",
        "all"
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    query = "SELECT * FROM archive WHERE 1=1"

    params = []

    if search:

        query += " AND name LIKE ?"

        params.append(f"%{search}%")

    if date:

        query += " AND date=?"

        params.append(date)

    if section != "all":

        query += " AND section=?"

        params.append(section)

    query += " ORDER BY id DESC"

    c.execute(query, params)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])


# ===== API أرشيف الشفت =====

@app.route("/api/shift_archive")
def api_shift_archive():

    if "role" not in session:
        return jsonify([])

    shift = request.args.get(
        "shift",
        "all"
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    if shift == "all":

        c.execute("""

        SELECT *

        FROM shift_archive

        ORDER BY id DESC

        """)

    else:

        c.execute("""

        SELECT *

        FROM shift_archive

        WHERE shift_type=?

        ORDER BY id DESC

        """, (shift,))

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])
# ===== إنشاء/تجهيز قاعدة البيانات =====
def init_db():

    conn = sqlite3.connect(DB_NAME)

    c = conn.cursor()

    # ===== إنشاء جدول المرضى =====
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        age TEXT NOT NULL,

        section TEXT NOT NULL,

        status TEXT NOT NULL,

        time TEXT NOT NULL,

        date TEXT NOT NULL,

        extra TEXT DEFAULT '',

        tests TEXT DEFAULT ''

    )
    """)
    # ===== إنشاء جدول السجلات =====
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs
               (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        action TEXT,

        time TEXT

    )
    """)
        # ===== أرشيف الشفتات =====

    c.execute("""

    CREATE TABLE IF NOT EXISTS shift_archive (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        patient_id INTEGER,

        name TEXT,

        age TEXT,

        section TEXT,

        status TEXT,

        time TEXT,

        date TEXT,

        extra TEXT,

        shift_type TEXT,
        tests TEXT,
        archived_at TEXT

    )

    """)
    # ===== الأرشيف العام =====

    c.execute("""

    CREATE TABLE IF NOT EXISTS archive (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    patient_id INTEGER,

    name TEXT,

    age TEXT,

    section TEXT,

    status TEXT,

    time TEXT,

    date TEXT,

    extra TEXT DEFAULT '',

    tests TEXT DEFAULT '',

    archived_at TEXT

)
""")
    # ===== تحسين سرعة البحث =====
    
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_patient_date
    ON patients(date)
    """)

    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_patient_status
    ON patients(status)
    """)

    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_patient_name
    ON patients(name)
    """)

    # ===== فحص الأعمدة =====
    c.execute("PRAGMA table_info(patients)")

    cols = [row[1] for row in c.fetchall()]

    # ===== إضافة عمود التحاليل إذا غير موجود =====

    if "tests" not in cols:

       try:

         c.execute("""
        ALTER TABLE patients
        ADD COLUMN tests TEXT DEFAULT ''
        """)

       except sqlite3.OperationalError:

        pass
       # ===== فحص أعمدة shift_archive =====

    c.execute("PRAGMA table_info(shift_archive)")

    archive_cols = [row[1] for row in c.fetchall()]

    if "tests" not in archive_cols:

        try:

         c.execute("""

        ALTER TABLE shift_archive

        ADD COLUMN tests TEXT DEFAULT ''

        """)

        except sqlite3.OperationalError:

          pass
       

    # ===== إضافة عمود الملاحظات إذا غير موجود =====
    if "extra" not in cols:

        try:

            c.execute("""
            ALTER TABLE patients
            ADD COLUMN extra TEXT DEFAULT ''
            """)

        except sqlite3.OperationalError:

            pass
# ===== جدول طلبات التغيير =====

    c.execute("""

CREATE TABLE IF NOT EXISTS change_requests (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT,

    new_username TEXT,

    new_password TEXT,

    status TEXT DEFAULT 'pending',

    created_at TEXT

    )

     """)
    # ===== جدول المستخدمين =====

    c.execute("""

    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE,

        password TEXT,

        role TEXT,

        approved INTEGER DEFAULT 0,

        blocked INTEGER DEFAULT 0

    )

    """)

    # ===== إنشاء الأدمن الأساسي =====

    c.execute(
        "SELECT * FROM users WHERE username=?",
        ("Admin1",)
    )

    admin = c.fetchone()

    if not admin:

        c.execute("""

        INSERT INTO users
        (username, password, role, approved, blocked)

        VALUES (?, ?, ?, ?, ?)

        """, (

            "Admin1",

            generate_password_hash(
    os.getenv("ADMIN1_PASSWORD")
),

            "x1",

            1,

            0

        ))
            # ===== إنشاء Admin2 =====

    c.execute(
        "SELECT * FROM users WHERE username=?",
        ("Admin2",)
    )

    admin2 = c.fetchone()

    if not admin2:

        c.execute("""

        INSERT INTO users
        (username, password, role, approved, blocked)

        VALUES (?, ?, ?, ?, ?)

        """, (

            "Admin2",

            generate_password_hash(
    os.getenv("ADMIN2_PASSWORD")
),

            "x2",

            1,

            0

        ))

    conn.commit()

    conn.close()

# ===== النسخ الاحتياطي =====
def backup_database():

    # إنشاء مجلد النسخ الاحتياطية
    os.makedirs("backups", exist_ok=True)

    # اسم النسخة
    now = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup_file = (
        f"backups/backup_{now}.db"
    )

    try:

        shutil.copy(
            DB_NAME,
            backup_file
        )

        print(
            f"✅ Backup created: {backup_file}"
        )

    except Exception as e:

        print(
            f"❌ Backup failed: {e}"
        )
# ===== تشغيل التهيئة =====
init_db()

backup_database()


# ===== تحويل الحالات القديمة =====

conn = sqlite3.connect(DB_NAME)

c = conn.cursor()

c.execute("""

UPDATE patients

SET status='قيد العمل'

WHERE status='جار العمل'

""")

conn.commit()

conn.close()

# ===== تسجيل العمليات =====
def add_log(username, action):

    conn = db_connect()

    c = conn.cursor()

    c.execute("""
    INSERT INTO logs
    (username, action, time)
    VALUES (?, ?, ?)
    """, (

        username,

        action,

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    ))

    conn.commit()

    conn.close()
# ===== الاتصال بقاعدة البيانات =====
def db_connect():

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row

    return conn
# ===== حماية الصفحات =====
@app.before_request
def protect_routes():
    allowed_routes = [
        "login",
        "register",
        "static",
        "check_result"
    ]

    if request.endpoint in allowed_routes:
        return

    if "role" not in session:
        return redirect("/")
# ===== تسجيل الدخول =====
@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    ip = request.remote_addr

    # ===== فحص الحظر =====
    if ip in login_attempts:

        tries, last_time = login_attempts[ip]

        if tries >= MAX_TRIES:

            passed = time.time() - last_time

            if passed < BLOCK_TIME:

                remain = int(BLOCK_TIME - passed)

                error = f"🚫 تم حظرك مؤقتاً، حاول بعد {remain} ثانية"

                return render_template(
                    "login.html",
                    error=error
                )

            else:

                login_attempts[ip] = [0, time.time()]

    # ===== تسجيل الدخول =====
    if request.method == "POST":

        u = request.form.get(
            "username",
            ""
        ).strip()

        p = request.form.get(
            "password",
            ""
        ).strip()

        conn = db_connect()

        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE username=?",
            (u,)
        )

        user = c.fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            p
        ):

            # 🚫 الحساب محظور
            if user["blocked"]:

                error = (
                    "🚫 تم تعطيل الحساب "
                    "بواسطة الإدارة"
                )

                return render_template(
                    "login.html",
                    error=error
                )

            # ⏳ الحساب بانتظار الموافقة
            if not user["approved"]:

                error = (
                    "📨 طلبك مرفوع إلى الإدارة "
                    "وهو قيد المعالجة حالياً"
                )

                return render_template(
                    "login.html",
                    error=error
                )

            # ✅ تصفير المحاولات
            login_attempts[ip] = [
                0,
                time.time()
            ]

            # ✅ حفظ الجلسة
            session["role"] = user["role"]

            session["username"] = (
                user["username"]
            )

            session.permanent = True

            return redirect(
                "/dashboard?success=1"
            )

        # ❌ محاولة فاشلة
        if ip not in login_attempts:

            login_attempts[ip] = [1, time.time()]

        else:

            login_attempts[ip][0] += 1

            login_attempts[ip][1] = time.time()

        remain_tries = MAX_TRIES - login_attempts[ip][0]

        error = (
            f"❌ اسم المستخدم أو كلمة المرور غير صحيحة "
            f"(متبقي {remain_tries} محاولات)"
        )

    return render_template(
        "login.html",
        error=error
    )
# ===== جلب بيانات اليوم =====
@app.route("/api/patients")
def get_patients():

    if "role" not in session:
        return jsonify([]), 401

    conn = db_connect()
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    section = request.args.get("section", "all")

    if section == "all":

        c.execute(
            "SELECT * FROM patients WHERE date=? ORDER BY id ASC",
            (today,)
        )

    else:

        c.execute(
            "SELECT * FROM patients WHERE date=? AND section=? ORDER BY id ASC",
            (today, section)
        )

    data = c.fetchall()

    conn.close()

    return jsonify([dict(row) for row in data])

# ===== لوحة التحكم =====
@app.route("/dashboard")
def dashboard():

    if "role" not in session:
        return redirect("/")

    return render_template(
        "dashboard.html",
        role=session["role"],
        username=session["username"]
    )
# ===== إضافة مريض =====
@app.route("/add", methods=["POST"])
def add():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    name = escape(
        request.form.get("name", "").strip()
    )

    age = escape(
        request.form.get("age", "").strip()
    )

    section = escape(
        request.form.get("section", "").strip()
    )

    # 🔥 الملاحظات
    extra = escape(
        request.form.get("extra", "").strip()
    )
    # 🧪 التحاليل

    tests = request.form.getlist("tests")

    if not name or not age or not section:
        return "Missing data", 400

    now = datetime.now()

    conn = db_connect()

    c = conn.cursor()

    c.execute("""
        INSERT INTO patients
        (name, age, tests, section, status, time, date, extra)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
    name,
    age,
    ",".join(tests),
    section,
    "تم استلام عينة التحليل",
    now.strftime("%H:%M:%S"),
    now.strftime("%Y-%m-%d"),
    extra
))
    

    conn.commit()

    # 🔥 تحديث فوري
    socketio.emit("refresh", {})

    conn.close()

    return "OK"


# ===== تحديث الحالة =====
@app.route("/update", methods=["POST"])
def update():
    if "role" not in session:
        return "Unauthorized", 401

    pid = request.form.get("id", "").strip()
    status = request.form.get("status", "").strip()

    if not pid or not status:
        return "Missing data", 400

    conn = db_connect()
    c = conn.cursor()
    c.execute("UPDATE patients SET status=? WHERE id=?", (status, pid))

    conn.commit()

    socketio.emit("refresh", {})  # 🔥

    conn.close()
    return "OK"


# ===== حذف =====
@app.route("/delete", methods=["POST"])
def delete():
    if session.get("role") != "x1":
        return "Unauthorized", 401

    pid = request.form.get("id", "").strip()
    if not pid.isdigit():

      return "Invalid ID", 400
    if not pid:
        return "Missing data", 400

    conn = db_connect()
    c = conn.cursor()
    c.execute("DELETE FROM patients WHERE id=?", (pid,))

    conn.commit()

    socketio.emit("refresh", {})  # 🔥

    conn.close()
    return "OK"


@app.route("/edit", methods=["POST"])
def edit():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    pid = request.form.get("id", "").strip()

    if not pid.isdigit():
        return "Invalid ID", 400

    name = escape(
        request.form.get("name", "").strip()
    )

    age = escape(
        request.form.get("age", "").strip()
    )

    section = escape(
        request.form.get("section", "").strip()
    )

    # 🧪 التحاليل
    tests = request.form.getlist("tests")

    # 📝 الملاحظات
    extra = escape(
        request.form.get("extra", "").strip()
    )

    if not pid or not name or not age or not section:
        return "Missing data", 400

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    UPDATE patients

    SET
    name=?,
    age=?,
    tests=?,
    section=?,
    extra=?

    WHERE id=?

    """, (

        name,
        age,
        ",".join(tests),
        section,
        extra,
        pid

    ))

    conn.commit()

    # 🔥 تحديث مباشر
    socketio.emit("refresh", {})

    conn.close()

    return "OK"

# ===== تنبيه =====
@app.route("/alert", methods=["POST"])
def alert():

    role = session.get("role")

    # 🔒 فقط x1 و x2
    if role not in ["x1", "x2"]:

        return "Unauthorized", 401

    pid = request.form.get(
        "id",
        ""
    ).strip()
    if not pid.isdigit():

     return "Invalid ID", 400

    if not pid:

        return "Missing data", 400

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "UPDATE patients SET status=? WHERE id=?",
        ("تنبيه 🔔", pid)
    )

    conn.commit()

    conn.close()

    socketio.emit(
        "new_alert",
        {"id": pid}
    )

    return "OK"


# ===== تنزيل التقارير CSV =====

@app.route("/download")
def download():

    if "role" not in session:
        return "Unauthorized", 401

    mode = request.args.get("mode")

    shift_type = request.args.get(
        "shift",
        "all"
    )

    date_str = request.args.get("date")

    conn = db_connect()

    c = conn.cursor()

    # ===== جدول المصدر =====

    table_name = "archive"

    if shift_type != "all":
        table_name = "shift_archive"

    # ===== تقرير يومي =====

    if mode == "day":

        target = datetime.now().strftime(
            "%Y-%m-%d"
        )

        if shift_type == "all":

            c.execute(f"""

            SELECT *

            FROM {table_name}

            WHERE date=?

            """, (target,))

        else:

            c.execute("""

            SELECT *

            FROM shift_archive

            WHERE date=?
            AND shift_type=?

            """, (

                target,
                shift_type

            ))

    # ===== تقرير أسبوعي =====

    elif mode == "week":

        today = datetime.now()

        start = today - timedelta(days=7)

        if shift_type == "all":

            c.execute(f"""

            SELECT *

            FROM {table_name}

            WHERE date BETWEEN ? AND ?

            """, (

                start.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d")

            ))

        else:

            c.execute("""

            SELECT *

            FROM shift_archive

            WHERE date BETWEEN ? AND ?
            AND shift_type=?

            """, (

                start.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d"),
                shift_type

            ))

    # ===== تقرير شهري =====

    elif mode == "month":

        today = datetime.now()

        start = today - timedelta(days=30)

        if shift_type == "all":

            c.execute(f"""

            SELECT *

            FROM {table_name}

            WHERE date BETWEEN ? AND ?

            """, (

                start.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d")

            ))

        else:

            c.execute("""

            SELECT *

            FROM shift_archive

            WHERE date BETWEEN ? AND ?
            AND shift_type=?

            """, (

                start.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d"),
                shift_type

            ))

    # ===== تقرير بتاريخ محدد =====

    elif mode == "custom" and date_str:

        if shift_type == "all":

            c.execute(f"""

            SELECT *

            FROM {table_name}

            WHERE date=?

            """, (date_str,))

        else:

            c.execute("""

            SELECT *

            FROM shift_archive

            WHERE date=?
            AND shift_type=?

            """, (

                date_str,
                shift_type

            ))

    # ===== تقرير من تاريخ إلى تاريخ =====

    elif mode == "range":

        from_date = request.args.get("from")

        to_date = request.args.get("to")

        if shift_type == "all":

            c.execute(f"""

            SELECT *

            FROM {table_name}

            WHERE date BETWEEN ? AND ?

            """, (

                from_date,
                to_date

            ))

        else:

            c.execute("""

            SELECT *

            FROM shift_archive

            WHERE date BETWEEN ? AND ?
            AND shift_type=?

            """, (

                from_date,
                to_date,
                shift_type

            ))

    # ===== طلب غير صحيح =====

    else:

        conn.close()

        return "Invalid request", 400

    rows = c.fetchall()

    conn.close()

    # ===== إنشاء ملف CSV =====

    output = io.StringIO()

    writer = csv.writer(output)

    # ===== استخراج كل التحاليل =====

    all_tests = set()

    for r in rows:

        if r["tests"]:

            for t in r["tests"].split(","):

                all_tests.add(t.strip())

    all_tests = sorted(list(all_tests))

    # ===== عناوين الأعمدة =====

    writer.writerow([
        "ID",
        "الاسم",
        "العمر",
        *all_tests,
        "القسم",
        "الحالة",
        "الوقت",
        "التاريخ",
        "ملاحظات"
    ])

    # ===== عداد التحاليل =====

    test_counter = {
        test: 0
        for test in all_tests
    }

    # ===== كتابة البيانات =====

    for r in rows:

        patient_tests = []

        if r["tests"]:

            patient_tests = [
                t.strip()
                for t in r["tests"].split(",")
            ]

        row_tests = []

        for test in all_tests:

            if test in patient_tests:

                row_tests.append("✓")

                test_counter[test] += 1

            else:

                row_tests.append("")

        writer.writerow([

            r["id"],
            r["name"],
            r["age"],

            *row_tests,

            r["section"],
            r["status"],
            r["time"],
            r["date"],
            r["extra"]

        ])

    # ===== إحصائية التحاليل =====

    writer.writerow([])

    writer.writerow(["إحصائية التحاليل"])

    for test, count in test_counter.items():

        writer.writerow([test, count])

    output_val = output.getvalue()

    csv_data = "\ufeff" + output_val

    return send_file(
        io.BytesIO(
            csv_data.encode("utf-8")
        ),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"report_{mode}_{datetime.now().strftime('%Y%m%d')}.csv"
    )

@app.route("/save_note", methods=["POST"])
def save_note():

    if "role" not in session:
        return "Unauthorized", 401

    patient_id = request.form.get("id", "").strip()

    if not patient_id.isdigit():
        return "Invalid ID", 400

    note = escape(
        request.form.get("note", "").strip()
    )

    if not patient_id:
        return "Missing data", 400

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "UPDATE patients SET extra=? WHERE id=?",
        (note, patient_id)
    )

    conn.commit()

    conn.close()

    return "OK"
@app.route("/check", methods=["GET", "POST"])
def check_result():

    patient = None

    if request.method == "POST":

        query = request.form.get(
            "query",
            ""
        ).strip().lower()

        age = request.form.get(
            "age",
            ""
        ).strip()

        # إزالة التشكيل
        query = re.sub(
            r'[\u0617-\u061A\u064B-\u0652]',
            '',
            query
        )

        # توحيد الأحرف
        query = (
            query
            .replace("ة", "ه")
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ى", "ي")
            .replace("ؤ", "و")
            .replace("ئ", "ي")
        )

        query = " ".join(query.split())

        conn = db_connect()

        c = conn.cursor()

        c.execute("""

        SELECT *

        FROM patients

        WHERE LOWER(
        REPLACE(
        REPLACE(
        REPLACE(
        REPLACE(
        REPLACE(
        REPLACE(
        REPLACE(name,'ة','ه'),
        'أ','ا'),
        'إ','ا'),
        'آ','ا'),
        'ى','ي'),
        'ؤ','و'),
        'ئ','ي')
        )

        LIKE ?

        AND age=?

        ORDER BY id DESC

        LIMIT 1

        """, (

            f"%{query}%",

            age

        ))

        patient = c.fetchone()

        conn.close()

    return render_template(
        "check.html",
        patient=patient
    )
# ===== تسجيل خروج =====
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")
# ===== تشغيل =====
@app.route("/register", methods=["POST"])
def register():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    confirm = request.form.get(
        "confirm",
        ""
    ).strip()

    secret = request.form.get(
        "secret",
        ""
    ).strip()

    captcha = request.form.get(
        "captcha",
        ""
    ).strip()

    # ===== رمز الإدارة =====

    if secret != MANAGER_SECRET:

        return (
            "رمز الإدارة غير صحيح"
        ), 400

    # ===== تطابق كلمة المرور =====

    if password != confirm:

        return (
            "كلمتا المرور غير متطابقتين"
        ), 400

    # ===== اسم المستخدم قصير =====

    if len(username) < 4:

        return (
            "اسم المستخدم قصير"
        ), 400

    # ===== كلمة المرور قوية =====

    import re

    pattern = (
    r"^.{6,}$"
)

    if not re.match(pattern, password):

        return (
            "كلمة المرور يجب أن "
"تحتوي 6 خانات على الأقل"
        ), 400

        # ===== منع التكرار =====

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE LOWER(username)=?",
        (username.lower(),)
    )

    exists = c.fetchone()

    if exists:

        conn.close()

        return (
            "اسم المستخدم مستخدم"
        ), 400

        # ===== إنشاء الحساب =====

    c.execute("""

    INSERT INTO users
    (username, password, role, approved, blocked)

    VALUES (?, ?, ?, ?, ?)

    """, (

        username,

        generate_password_hash(password),

        "pending",

        0,

        0

    ))

    conn.commit()

    # 🔥 إشعار مباشر للإدارة
    socketio.emit(
        "admin_notification",
        {
            "message":
            f"👤 مستخدم جديد سجل: {username}"
        }
    )

    conn.close()

    return "OK"

@app.route("/pending_users")
def pending_users():

    if session.get("role") != "x1":

        return jsonify([])

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    SELECT username

    FROM users

    WHERE approved=0

    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])


@app.route(
    "/approve_user",
    methods=["POST"]
)
def approve_user():

    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username"
    )

    role = request.form.get(
        "role"
    )

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    UPDATE users

    SET
    approved=1,
    role=?

    WHERE username=?

    """, (

        role,
        username

    ))

    conn.commit()

    conn.close()

    return "OK"


@app.route(
    "/reject_user",
    methods=["POST"]
)
def reject_user():

    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username"
    )

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "DELETE FROM users WHERE username=?",
        (username,)
    )

    conn.commit()

    conn.close()

    return "OK"
@app.route(
    "/block_user",
    methods=["POST"]
)
def block_user():

    # 🔒 فقط x1
    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username"
    )

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT role FROM users WHERE username=?",
        (username,)
    )

    user = c.fetchone()

    if not user:

        conn.close()

        return "User not found", 404

    # 🚫 منع حظر x1
    if user["role"] == "x1":

        conn.close()

        return (
            "لا يمكن حظر مدير النظام"
        ), 400

    c.execute(
        "UPDATE users SET blocked=1 WHERE username=?",
        (username,)
    )

    conn.commit()

    conn.close()

    return "OK"
@app.route("/all_users")
def all_users():

    if session.get("role") != "x1":

        return jsonify([])

    conn = db_connect()

    c = conn.cursor()

    c.execute("""
    SELECT
    username,
    role,
    approved,
    blocked
    FROM users
    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])
@app.route(
    "/delete_user",
    methods=["POST"]
)
def delete_user():

    # 🔒 فقط x1
    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username"
    )

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT role FROM users WHERE username=?",
        (username,)
    )

    user = c.fetchone()

    if not user:

        conn.close()

        return "User not found", 404

    # 🚫 منع حذف x1
    if user["role"] == "x1":

        conn.close()

        return (
            "لا يمكن حذف مدير النظام"
        ), 400

    c.execute(
        "DELETE FROM users WHERE username=?",
        (username,)
    )

    conn.commit()

    conn.close()

    return "OK"
@app.route(
    "/unblock_user",
    methods=["POST"]
)
def unblock_user():

    # 🔒 فقط x1
    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username"
    )

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "UPDATE users SET blocked=0 WHERE username=?",
        (username,)
    )

    conn.commit()

    conn.close()

    return "OK"
@app.route("/users_panel")
def users_panel():

    if session.get("role") != "x1":

        return redirect("/dashboard")

    return render_template(
        "users_panel.html"
    )
@app.route(
    "/change_role",
    methods=["POST"]
)
def change_role():

    if session.get("role") != "x1":

        return "Unauthorized", 401

    username = request.form.get(
        "username",
        ""
    ).strip()

    role = request.form.get(
        "role",
        ""
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    )

    user = c.fetchone()

    if not user:

        conn.close()

        return "User not found", 404

    c.execute(
        "UPDATE users SET role=? WHERE username=?",
        (role, username)
    )

    conn.commit()

    conn.close()

    return "OK"
# ===== طلب تغيير الحساب =====

@app.route(
"/request_account_change",
methods=["POST"]
)
def request_account_change():

    if "username" not in session:

        return "غير مسجل دخول"

    new_username = request.form.get(
        "new_username",
        ""
    ).strip()

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    if len(new_password) < 6:

        return "كلمة المرور قصيرة"

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    INSERT INTO change_requests
    (

    username,

    new_username,

    new_password,

    created_at

    )

    VALUES (?, ?, ?, ?)

    """, (

        session["username"],

        new_username,

        generate_password_hash(
            new_password
        ),

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    ))

    conn.commit()

    conn.close()

    return "OK"

# ===== طلب تغيير اسم المستخدم =====

@app.route(
"/request_username_change",
methods=["POST"]
)
def request_username_change():

    if "username" not in session:

        return "غير مسجل دخول"

    new_username = request.form.get(
        "new_username",
        ""
    ).strip()

    current_password = request.form.get(
        "current_password",
        ""
    ).strip()

    if not new_username:

        return "اكتب اسم المستخدم الجديد"

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE username=?",
        (session["username"],)
    )

    user = c.fetchone()

    if not user:

        conn.close()

        return "المستخدم غير موجود"

    if not check_password_hash(
        user["password"],
        current_password
    ):

        conn.close()

        return "كلمة المرور الحالية غير صحيحة"

    c.execute("""

    INSERT INTO change_requests
    (

    username,

    new_username,

    created_at

    )

    VALUES (?, ?, ?)

    """, (

        session["username"],

        new_username,

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    ))

    conn.commit()

    # 🔥 إشعار مباشر للإدارة
    socketio.emit(
        "admin_notification",
        {
            "message":
            f"📨 طلب تغيير اسم من {session['username']}"
        }
    )

    conn.close()

    return "OK"
# ===== جلب طلبات تغيير الاسم =====

@app.route("/username_requests")
def username_requests():

    if session.get("role") != "x1":
        return jsonify([])

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    SELECT *

    FROM change_requests

    WHERE
    status='pending'

    AND new_username IS NOT NULL

    ORDER BY id DESC

    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])

# ===== طلب تغيير كلمة المرور =====

@app.route(
"/request_password_change",
methods=["POST"]
)
def request_password_change():

    if "username" not in session:

        return "غير مسجل دخول"

    current_password = request.form.get(
        "current_password",
        ""
    ).strip()

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    if len(new_password) < 6:

        return "كلمة المرور قصيرة"

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE username=?",
        (session["username"],)
    )

    user = c.fetchone()

    if not user:

        conn.close()

        return "المستخدم غير موجود"

    if not check_password_hash(
        user["password"],
        current_password
    ):

        conn.close()

        return "كلمة المرور الحالية غير صحيحة"

    c.execute("""

    INSERT INTO change_requests
    (

    username,

    new_password,

    created_at

    )

    VALUES (?, ?, ?)

    """, (

        session["username"],

        generate_password_hash(
            new_password
        ),

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    ))

    conn.commit()

    # 🔥 إشعار مباشر للإدارة
    socketio.emit(
        "admin_notification",
        {
            "message":
            f"🔑 طلب تغيير كلمة مرور من {session['username']}"
        }
    )

    conn.close()

    return "OK"
# ===== الموافقة على تغيير الاسم =====

@app.route(
    "/approve_username_request",
    methods=["POST"]
)
def approve_username_request():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    request_id = request.form.get(
        "id",
        ""
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    # جلب الطلب
    c.execute(
        "SELECT * FROM change_requests WHERE id=?",
        (request_id,)
    )

    req = c.fetchone()

    if not req:

        conn.close()

        return "Request not found", 404

    # تحديث اسم المستخدم
    c.execute(
        """

        UPDATE users

        SET username=?

        WHERE username=?

        """,
        (
            req["new_username"],
            req["username"]
        )
    )

    # تحديث حالة الطلب
    c.execute(
        """

        UPDATE change_requests

        SET status='approved'

        WHERE id=?

        """,
        (request_id,)
    )

    conn.commit()

    conn.close()

    return "OK"


# ===== رفض طلب تغيير الاسم =====

@app.route(
    "/reject_username_request",
    methods=["POST"]
)
def reject_username_request():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    request_id = request.form.get(
        "id",
        ""
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        """

        UPDATE change_requests

        SET status='rejected'

        WHERE id=?

        """,
        (request_id,)
    )

    conn.commit()

    conn.close()

    return "OK"
# ===== جلب طلبات تغيير كلمة المرور =====

@app.route("/password_requests")
def password_requests():

    if session.get("role") != "x1":
        return jsonify([])

    conn = db_connect()

    c = conn.cursor()

    c.execute("""

    SELECT *

    FROM change_requests

    WHERE
    status='pending'

    AND new_password IS NOT NULL

    ORDER BY id DESC

    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])
# ===== الموافقة على تغيير كلمة المرور =====

@app.route(
    "/approve_password_request",
    methods=["POST"]
)
def approve_password_request():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    request_id = request.form.get(
        "id",
        ""
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    # جلب الطلب
    c.execute(
        "SELECT * FROM change_requests WHERE id=?",
        (request_id,)
    )

    req = c.fetchone()

    if not req:

        conn.close()

        return "Request not found", 404

    # تحديث كلمة المرور
    c.execute(
        """

        UPDATE users

        SET password=?

        WHERE username=?

        """,
        (
            req["new_password"],
            req["username"]
        )
    )

    # تحديث حالة الطلب
    c.execute(
        """

        UPDATE change_requests

        SET status='approved'

        WHERE id=?

        """,
        (request_id,)
    )

    conn.commit()

    conn.close()

    return "OK"


# ===== رفض طلب تغيير كلمة المرور =====

@app.route(
    "/reject_password_request",
    methods=["POST"]
)
def reject_password_request():

    if session.get("role") != "x1":
        return "Unauthorized", 401

    request_id = request.form.get(
        "id",
        ""
    ).strip()

    conn = db_connect()

    c = conn.cursor()

    c.execute(
        """

        UPDATE change_requests

        SET status='rejected'

        WHERE id=?

        """,
        (request_id,)
    )

    conn.commit()

    conn.close()

    return "OK"
csrf.exempt(request_username_change)
csrf.exempt(request_password_change)
csrf.exempt(register)
csrf.exempt(login)
csrf.exempt(add)
csrf.exempt(check_result)
csrf.exempt(update)
csrf.exempt(delete)
csrf.exempt(edit)
csrf.exempt(alert)
csrf.exempt(save_note)
csrf.exempt(change_role)
csrf.exempt(approve_username_request)
csrf.exempt(reject_username_request)
csrf.exempt(approve_password_request)
csrf.exempt(reject_password_request)
csrf.exempt(request_account_change)
csrf.exempt(approve_user)
csrf.exempt(reject_user)
csrf.exempt(block_user)
csrf.exempt(unblock_user)
csrf.exempt(delete_user)
@csrf.exempt
@app.route("/reset_shift", methods=["POST"])
def reset_shift():

    if session.get("role") != "x1":
        return jsonify({
            "success": False,
            "message": "غير مصرح"
        }), 401

    data = request.get_json()

    shift_type = data.get(
        "shift",
        ""
    ).strip()

    if not shift_type:

        return jsonify({
            "success": False,
            "message": "لم يتم تحديد الشفت"
        }), 400

    conn = db_connect()

    c = conn.cursor()

    # ===== جلب المرضى الحاليين =====

    c.execute(
        "SELECT * FROM patients"
    )

    patients = c.fetchall()

    # ===== إذا لا توجد بيانات =====

    if not patients:

        conn.close()

        return jsonify({
            "success": False,
            "message": "لا توجد بيانات للتصفير"
        })

    # ===== نقل المرضى =====

    for p in patients:

        archived_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ===== الأرشيف العام =====

        c.execute("""

        INSERT INTO archive (

            patient_id,
            name,
            age,
            section,
            status,
            time,
            date,
            extra,
            tests,
            archived_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            p["id"],
            p["name"],
            p["age"],
            p["section"],
            p["status"],
            p["time"],
            p["date"],
            p["extra"],
            p["tests"],
            archived_time

        ))

        # ===== أرشيف الشفت =====

        c.execute("""

        INSERT INTO shift_archive (

            patient_id,
            name,
            age,
            section,
            status,
            time,
            date,
            extra,
            tests,
            shift_type,
            archived_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            p["id"],
            p["name"],
            p["age"],
            p["section"],
            p["status"],
            p["time"],
            p["date"],
            p["extra"],
            p["tests"],
            shift_type,
            archived_time

        ))

    # ===== حذف المرضى الحاليين =====

    c.execute(
        "DELETE FROM patients"
    )

    conn.commit()

    conn.close()

    # ===== تحديث مباشر =====

    socketio.emit("refresh", {})

    return jsonify({

        "success": True,

        "message":
        f"تم تصفير شفت {shift_type} بنجاح"

    })
init_db()
@app.route("/pending_notifications_count")
def pending_notifications_count():

    if session.get("role") != "x1":

        return jsonify({
            "count": 0
        })

    conn = db_connect()

    c = conn.cursor()

    # ===== مستخدمون بانتظار الموافقة =====

    c.execute("""

    SELECT COUNT(*)

    FROM users

    WHERE approved=0

    """)

    users_count = c.fetchone()[0]

    # ===== طلبات تغيير الاسم =====

    c.execute("""

    SELECT COUNT(*)

    FROM change_requests

    WHERE
    status='pending'
    AND new_username IS NOT NULL

    """)

    username_count = c.fetchone()[0]

    # ===== طلبات تغيير كلمة المرور =====

    c.execute("""

    SELECT COUNT(*)

    FROM change_requests

    WHERE
    status='pending'
    AND new_password IS NOT NULL

    """)

    password_count = c.fetchone()[0]

    conn.close()

    total = (

        users_count +

        username_count +

        password_count

    )

    return jsonify({

        "count": total

    })


import os

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    
    socketio.run(
    app,
    host="0.0.0.0",
    port=port,
    debug=False,
    allow_unsafe_werkzeug=True
)