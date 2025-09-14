from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd

app = Flask(__name__)

# فولدر التخزين
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# دالة التحقق من الامتداد
def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------------
# الصفحة الرئيسية → اختيار الموقع (من أسماء الملفات)
# ----------------------------------
@app.route('/')
def select_site():
    files = [
        f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xlsx', '.xls'))
    ]
    sites = []
    for f in files:
        # نشيل الامتداد
        name = os.path.splitext(f)[0]
        # نخلي الاسم أنضف (نشيل - أو _ ونخليها مسافات)
        clean_name = name.replace("-", " ").replace("_", " ")
        sites.append({"file": name, "display": clean_name})

    return render_template('select_site.html', sites=sites)


# ----------------------------------
# رفع ملف جديد / استبدال القديم
# ----------------------------------
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "❌ مفيش ملف مرفوع"

        file = request.files['file']

        if file.filename == '':
            return "❌ مفيش اسم ملف"

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)

            # استبدال الملف لو موجود
            file.save(filepath)

            return redirect(url_for('select_site'))
        else:
            return "❌ مسموح فقط برفع ملفات Excel (.xlsx أو .xls)"

    return render_template('upload.html')


# ----------------------------------
# صفحة تسجيل / تعديل الحضور
# ----------------------------------
@app.route('/attendance/<site>', methods=['GET', 'POST'])
def attendance(site):
    # الملف على أساس الاسم الأصلي (من غير التنظيف)
    filename = f"{site}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # لو الملف مش موجود، نعمل ملف جديد فاضي
    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=[
            "الاسم", "الرقم القومي", "الموقع", "الوظيفة", "عدد الساعات"
        ])
        df.to_excel(filepath, index=False)

    # قراءة الملف
    df = pd.read_excel(filepath)
    df = df.fillna("")  # استبدال NaN بفاضي

    if request.method == 'POST':
        updated_data = []

        # تحديث البيانات القديمة
        for i in range(len(df)):
            row = {}
            for h in df.columns:
                row[h] = request.form.get(f"{h}_{i}", "")
            updated_data.append(row)

        # إضافة الصفوف الجديدة (لو فيها بيانات)
        new_index = 0
        while True:
            row = {}
            empty_row = True
            for h in df.columns:
                val = request.form.get(f"{h}_new{new_index}", "")
                if val.strip():  # لو فيه أي قيمة
                    empty_row = False
                row[h] = val
            if not empty_row:
                updated_data.append(row)
                new_index += 1
            else:
                break

        # تحويلها DataFrame وحفظها
        new_df = pd.DataFrame(updated_data, columns=df.columns)
        new_df.to_excel(filepath, index=False)

        return redirect(url_for('attendance', site=site))

    headers = df.columns.tolist()
    data = df.to_dict(orient="records")
    return render_template("attendance_edit.html",
                           site=site,
                           headers=headers,
                           data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
