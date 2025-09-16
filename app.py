from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import pandas as pd
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"  # ضع هنا مفتاح قوي في بيئة Production

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# -----------------------
# تحميل بيانات المستخدمين
# -----------------------
def load_users():
    if not os.path.exists("users.json"):
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)

    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)

    # لو الملف فاضي → نضيف بيانات تجريبية
    if not users:
        sample_users = [{
            "username": "admin",
            "password": "1234",
            "sites": [],
            "last_login": None,
            "completion": 0
        }, {
            "username": "mohamed",
            "password": "5678",
            "sites": ["MB3.xlsx", "الالفى.xlsx"],
            "last_login": None,
            "completion": 0
        }]
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(sample_users, f, ensure_ascii=False, indent=4)
        return sample_users

    return users


def save_users(users):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


# التحقق من الامتداد
def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        ".", 1)[1].lower() in ALLOWED_EXTENSIONS


# التحقق من تسجيل الدخول
def login_required(func):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# -----------------------
# صفحة تسجيل الدخول
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        users = load_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                session["logged_in"] = True
                session["username"] = username
                session["sites"] = user.get("sites", [])

                # تحديث آخر تسجيل دخول
                user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_users(users)

                return redirect(url_for("select_site"))

        return render_template("login.html",
                               error="❌ اسم المستخدم أو كلمة المرور غير صحيحة")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------
# الصفحة الرئيسية
# -----------------------
@app.route('/')
@login_required
def select_site():
    user = session.get("username")
    sites = []

    if user == "admin":
        # الادمن يشوف كل ملفات Excel في فولدر uploads
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                display_name = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ")
                sites.append({"file": filename, "display": display_name})
    else:
        # باقي المستخدمين يشوفوا الملفات المسموح لهم
        allowed_sites = session.get("sites", [])
        for s in allowed_sites:
            for ext in ['.xlsx', '.xls']:
                filename = f"{s}{ext}" if not s.endswith(ext) else s
                if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                    clean_name = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ")
                    sites.append({"file": filename, "display": clean_name})

    return render_template('select_site.html', sites=sites)


# -----------------------
# رفع ملف جديد
# -----------------------
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "❌ مفيش ملف مرفوع"

        file = request.files['file']
        if file.filename == '':
            return "❌ مفيش اسم ملف"

        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('select_site'))
        else:
            return "❌ مسموح فقط برفع ملفات Excel (.xlsx أو .xls)"

    return render_template('upload.html')


# -----------------------
# صفحة تعديل الحضور
# -----------------------
@app.route('/attendance/<path:site>', methods=['GET', 'POST'])
@login_required
def attendance(site):
    user = session.get("username")
    upload_files = os.listdir(UPLOAD_FOLDER)

    # التحقق من الصلاحية
    if user == "admin":
        if site not in upload_files:
            return "❌ هذا الملف غير موجود"
    else:
        allowed_sites = session.get("sites", [])
        valid = False
        for s in allowed_sites:
            for ext in ['.xlsx', '.xls']:
                filename = f"{s}{ext}" if not s.endswith(ext) else s
                if filename == site:
                    valid = True
                    break
            if valid:
                break
        if not valid:
            return "❌ غير مسموح بالدخول لهذا الموقع"

    filepath = os.path.join(UPLOAD_FOLDER, site)

    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=["الاسم", "الرقم القومي", "الموقع", "الوظيفة", "عدد الساعات"])
        df.to_excel(filepath, index=False)

    df = pd.read_excel(filepath).fillna("")

    if request.method == 'POST':
        updated_data = []

        for i in range(len(df)):
            row = {h: request.form.get(f"{h}_{i}", "") for h in df.columns}
            updated_data.append(row)

        new_rows = {}
        for key, value in request.form.items():
            if "_new" in key and value.strip():
                col, idx = key.rsplit("_new", 1)
                if idx not in new_rows:
                    new_rows[idx] = {}
                new_rows[idx][col] = value

        for row in new_rows.values():
            updated_data.append(row)

        new_df = pd.DataFrame(updated_data, columns=df.columns)
        new_df.to_excel(filepath, index=False)
        return redirect(url_for('attendance', site=site))

    return render_template("attendance_edit.html",
                           site=site,
                           headers=df.columns.tolist(),
                           data=df.to_dict(orient="records"))


# -----------------------
# صفحة الادمن داشبورد
# -----------------------
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if session.get("username") != "admin":
        return "❌ غير مسموح بالدخول", 403

    users = load_users()
    for u in users:
        u.setdefault("completion_percent", int(u.get("completion", 0)))

    uploads = sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.xlsx', '.xls'))])

    return render_template("admin_dashboard.html",
                           users=users,
                           uploads=uploads)


# -----------------------
# إنشاء مستخدم جديد
# -----------------------
@app.route("/admin/add_user", methods=["POST"])
@login_required
def add_user():
    if session.get("username") != "admin":
        flash("❌ غير مسموح", "danger")
        return redirect(url_for("select_site"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("⚠️ لازم تكتب اسم مستخدم وكلمة مرور", "danger")
        return redirect(url_for("admin_dashboard"))

    users = load_users()
    if any(u["username"] == username for u in users):
        flash("⚠️ المستخدم موجود بالفعل", "warning")
        return redirect(url_for("admin_dashboard"))

    users.append({
        "username": username,
        "password": password,
        "sites": [],
        "last_login": None,
        "completion": 0
    })
    save_users(users)
    flash(f"✅ تم إضافة المستخدم {username}", "success")
    return redirect(url_for("admin_dashboard"))


# -----------------------
# عرض تفاصيل المستخدم
# -----------------------
@app.route("/admin/user/<string:username>")
@login_required
def view_user(username):
    if session.get("username") != "admin":
        return "❌ غير مسموح بالدخول", 403

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)

    if not user:
        return "❌ المستخدم غير موجود", 404

    user["completion_rate"] = int(user.get("completion", 0))
    return render_template("view_user.html", user=user)


# -----------------------
# إضافة موقع لمستخدم
# -----------------------
@app.route('/add_site', methods=['POST'])
@login_required
def add_site():
    username = request.form.get("username")
    site_file = request.form.get("site_file")
    details = request.form.get("details", "")

    if not username or not site_file:
        flash("⚠️ لازم تختار يوزر وملف", "danger")
        return redirect(url_for("admin_dashboard"))

    uploads = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.xlsx', '.xls'))]
    if site_file not in uploads:
        flash("❌ الملف المختار غير موجود في uploads", "danger")
        return redirect(url_for("admin_dashboard"))

    users = load_users()
    for user in users:
        if user.get("username") == username:
            if "sites" not in user:
                user["sites"] = []
            if site_file not in user["sites"]:
                user["sites"].append(site_file)
                flash(f"✅ تم إضافة الموقع '{site_file}' للمستخدم {username}", "success")
            else:
                flash("⚠️ الملف موجود بالفعل عند هذا المستخدم", "warning")
            break
    else:
        flash("❌ المستخدم غير موجود", "danger")

    save_users(users)
    return redirect(url_for("admin_dashboard"))


# -----------------------
# تحديث كلمة المرور
# -----------------------
@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    if session.get("username") != "admin":
        flash("❌ غير مسموح", "danger")
        return redirect(url_for("select_site"))

    username = request.form.get("username")
    new_password = request.form.get("new_password", "").strip()

    if not username or new_password == "":
        flash("⚠️ لازم تكتب كلمة مرور جديدة", "danger")
        return redirect(url_for("admin_dashboard"))

    users = load_users()
    for u in users:
        if u.get("username") == username:
            u["password"] = new_password
            flash(f"✅ تم تحديث كلمة المرور للمستخدم {username}", "success")
            break
    else:
        flash("❌ المستخدم غير موجود", "danger")

    save_users(users)
    return redirect(url_for("admin_dashboard"))


# -----------------------
# حذف مستخدم
# -----------------------
@app.route('/delete_user/<string:username>', methods=['GET', 'POST'])
@login_required
def delete_user(username):
    if session.get("username") != "admin":
        return redirect(url_for("select_site"))

    users = load_users()
    new_users = [u for u in users if u.get("username") != username]

    if len(new_users) != len(users):
        save_users(new_users)
        flash(f"✅ تم حذف المستخدم {username} بنجاح", "success")
    else:
        flash("❌ المستخدم غير موجود", "danger")

    return redirect(url_for("admin_dashboard"))


# -----------------------
# حذف موقع من مستخدم
# -----------------------
@app.route('/delete_site/<username>/<site>', methods=['POST'])
@login_required
def delete_site(username, site):
    if session.get("username") != "admin":
        flash("❌ غير مسموح", "danger")
        return redirect(url_for("select_site"))

    users = load_users()
    for u in users:
        if u["username"] == username:
            if "sites" in u and site in u["sites"]:
                u["sites"].remove(site)
                flash(f"✅ تم حذف الموقع {site} من {username}", "success")
            else:
                flash(f"⚠️ الموقع {site} غير موجود لدى المستخدم {username}", "warning")
            break
    else:
        flash("❌ المستخدم غير موجود", "danger")

    save_users(users)
    return redirect(url_for("admin_dashboard"))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
