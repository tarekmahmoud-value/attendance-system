from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance_form.html')

if __name__ == '__main__':
    app.run(debug=True)
