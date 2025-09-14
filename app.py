from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = "secret123"  # غيره لما ترفع السيرفر

# فولدر التخزين
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# -----------------------
# تحميل بيانات المستخدمين
# -----------------------
def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)


# التحقق من الامتداد
def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
                session["sites"] = user["sites"]
                return redirect(url_for("select_site"))

        return render_template("login.html", error="❌ اسم المستخدم أو كلمة المرور غير صحيحة")
    return render_template("login.html")


# تسجيل الخروج
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
    allowed_sites = session.get("sites", [])
    sites = []

    for s in allowed_sites:
        filename_xlsx = f"{s}.xlsx"
        filename_xls = f"{s}.xls"

        if os.path.exists(os.path.join(UPLOAD_FOLDER, filename_xlsx)) or os.path.exists(os.path.join(UPLOAD_FOLDER, filename_xls)):
            clean_name = s.replace("-", " ").replace("_", " ")
            sites.append({"file": s, "display": clean_name})

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
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            return redirect(url_for('select_site'))
        else:
            return "❌ مسموح فقط برفع ملفات Excel (.xlsx أو .xls)"

    return render_template('upload.html')


# -----------------------
# صفحة تعديل الحضور
# -----------------------
@app.route('/attendance/<site>', methods=['GET', 'POST'])
@login_required
def attendance(site):
    if site not in session.get("sites", []):
        return "❌ غير مسموح بالدخول لهذا الموقع"

    filename = f"{site}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=[
            "الاسم", "الرقم القومي", "الموقع", "الوظيفة", "عدد الساعات"
        ])
        df.to_excel(filepath, index=False)

    df = pd.read_excel(filepath).fillna("")

    if request.method == 'POST':
        updated_data = []
        for i in range(len(df)):
            row = {h: request.form.get(f"{h}_{i}", "") for h in df.columns}
            updated_data.append(row)

        new_index = 0
        while True:
            row = {h: request.form.get(f"{h}_new{new_index}", "") for h in df.columns}
            if any(val.strip() for val in row.values()):
                updated_data.append(row)
                new_index += 1
            else:
                break

        new_df = pd.DataFrame(updated_data, columns=df.columns)
        new_df.to_excel(filepath, index=False)
        return redirect(url_for('attendance', site=site))

    return render_template("attendance_edit.html",
                           site=site,
                           headers=df.columns.tolist(),
                           data=df.to_dict(orient="records"))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
