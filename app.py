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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------------
# الصفحة الرئيسية → اختيار الموقع (من أسماء الملفات)
# ----------------------------------
@app.route('/')
def select_site():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xlsx', '.xls'))]
    sites = []
    for f in files:
        # نشيل الامتداد
        name = os.path.splitext(f)[0]
        # نخلي الاسم أنضف (نشيل - أو _ ونخليها مسافات)
        clean_name = name.replace("-", " ").replace("_", " ")
        sites.append({"file": name, "display": clean_name})

    return render_template('select_site.html', sites=sites)


# ----------------------------------
# رفع ملف جديد
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
        # تحديث البيانات من الفورم
        updated_data = []
        for i in range(len(df)):
            row = {}
            for h in df.columns:
                row[h] = request.form.get(f"{h}_{i}", "")
            updated_data.append(row)

        # تحويلها DataFrame وحفظها
        new_df = pd.DataFrame(updated_data)
        new_df.to_excel(filepath, index=False)

        return f"✅ تم حفظ التعديلات للموقع: {site} في {filename}"

    headers = df.columns.tolist()
    data = df.to_dict(orient="records")
    return render_template("attendance_edit.html",
                           site=site,
                           headers=headers,
                           data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
