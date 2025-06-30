import hashlib
import io
import pathlib
import sqlite3

import pdfkit
from flask import (Flask, flash, make_response, redirect, render_template,
                   request, send_file, url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # jika belum pakai HTTPS lokal
DB_PATH = pathlib.Path('cv.db')

@app.after_request
def remove_frame_options(response):
    response.headers.pop('X-Frame-Options', None)
    return response

# ─── Flask‑Login Setup ───────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute('SELECT id, username FROM user WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return User(*row) if row else None

# ─── DB Helpers ──────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── Auth Routes ─────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_pw(request.form['password'])
        conn = get_db()
        try:
            conn.execute('INSERT INTO user (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Registrasi berhasil. Silakan login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username sudah dipakai!', 'danger')
        finally:
            conn.close()
    return render_template('register.html', hide_nav=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        raw_password = request.form['password']
        hashed_password = hash_pw(raw_password)  # hanya sekali hashing

        conn = get_db()
        cur = conn.execute('SELECT id, username FROM user WHERE username=? AND password=?', (username, hashed_password))
        row = cur.fetchone()
        conn.close()

        if row:
            user = User(*row)
            login_user(user)
            return redirect(url_for('home'))

        flash('Username / Password salah', 'danger')
    return render_template('login.html', hide_nav=True)


@app.route('/logout')
def logout():
    logout_user()
    response = make_response(redirect(url_for('login')))
    response.set_cookie('session', '', expires=0)  # hapus cookie secara eksplisit
    return response

# ─── CV Routes ───────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/form', methods=['GET', 'POST'])  # ✅ tambahkan metode POST
@login_required
def index():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']

        # Simpan data sederhana (hanya name & email)
        conn = get_db()
        conn.execute(
            'INSERT INTO cv (user_id, name, email) VALUES (?, ?, ?)',
            (current_user.id, name, email)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('list_cv'))

    return render_template('index.html')


@app.route('/generate', methods=['POST'])
@login_required
def generate_cv():
    data = {
        'user_id': current_user.id,
        'name': request.form['name'],
        'email': request.form['email'],
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'linkedin': request.form.get('linkedin'),
        'github': request.form.get('github'),
        'summary': request.form.get('summary'),
        'education': request.form.get('education'),
        'experience': request.form.get('experience'),
        'projects': request.form.get('projects'),
        'certifications': request.form.get('certifications'),
        'skills': request.form.get('skills'),
        'languages': request.form.get('languages'),
        'photo_url': request.form.get('photo'),
    }

    conn = get_db()
    query = '''
        INSERT INTO cv (
            user_id, name, email, phone, address, linkedin, github, summary,
            education, experience, projects, certifications, skills, languages, photo_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    conn.execute(query, tuple(data.values()))
    cv_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return redirect(url_for('view_cv', cv_id=cv_id))

@app.route('/cv/<int:cv_id>')
@login_required
def view_cv(cv_id):
    conn = get_db()
    cv = conn.execute('SELECT * FROM cv WHERE id=? AND user_id=?', (cv_id, current_user.id)).fetchone()
    conn.close()
    if not cv:
        return 'CV Tidak ditemukan atau bukan milik Anda', 404
    return render_template('cv_preview.html', data=cv)

@app.route('/cv/<int:cv_id>/edit', methods=['GET'])
@login_required
def edit_cv(cv_id):
    conn = get_db()
    cv = conn.execute('SELECT * FROM cv WHERE id=? AND user_id=?', (cv_id, current_user.id)).fetchone()
    conn.close()
    if not cv:
        return 'CV tidak ditemukan atau bukan milik Anda', 404
    return render_template('cv_edit.html', data=cv)

@app.route('/cv/<int:cv_id>/edit', methods=['POST'])
@login_required
def update_cv(cv_id):
    data = {
        'name': request.form['name'],
        'email': request.form['email'],
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'linkedin': request.form.get('linkedin'),
        'github': request.form.get('github'),
        'summary': request.form.get('summary'),
        'education': request.form.get('education'),
        'experience': request.form.get('experience'),
        'projects': request.form.get('projects'),
        'certifications': request.form.get('certifications'),
        'skills': request.form.get('skills'),
        'languages': request.form.get('languages'),
        'photo_url': request.form.get('photo')
    }

    conn = get_db()
    query = '''
        UPDATE cv SET
            name=?, email=?, phone=?, address=?, linkedin=?, github=?, summary=?,
            education=?, experience=?, projects=?, certifications=?, skills=?, languages=?, photo_url=?
        WHERE id=? AND user_id=?
    '''
    conn.execute(query, (*data.values(), cv_id, current_user.id))
    conn.commit()
    conn.close()
    flash('CV berhasil diperbarui ✅', 'success')
    return redirect(url_for('view_cv', cv_id=cv_id))

@app.route('/list')
@login_required
def list_cv():
    conn = get_db()
    cvs = conn.execute('SELECT id,name,email FROM cv WHERE user_id=? ORDER BY id DESC', (current_user.id,)).fetchall()
    conn.close()
    return render_template('cv_list.html', cvs=cvs)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm = request.form['confirm']

        if new_password != confirm:
            flash('Password tidak cocok!', 'danger')
            return redirect(url_for('change_password'))

        conn = get_db()
        user = conn.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone()
        if not user:
            flash('Username tidak ditemukan', 'danger')
            conn.close()
            return redirect(url_for('change_password'))

        hashed_pw = hash_pw(new_password)
        conn.execute('UPDATE user SET password = ? WHERE username = ?', (hashed_pw, username))
        conn.commit()
        conn.close()

        flash('Password berhasil diubah! Silakan login kembali.', 'success')
        return redirect(url_for('login'))  # ✅ Arahkan ke halaman login

    return render_template('change_password.html', hide_nav=True)



# ─── PDF Export ──────────────────────────────────────────────────────────────
@app.route('/cv/<int:cv_id>/pdf')
@login_required
def download_pdf(cv_id):
    conn = get_db()
    cv = conn.execute('SELECT * FROM cv WHERE id=? AND user_id=?', (cv_id, current_user.id)).fetchone()
    conn.close()
    if not cv:
        return 'CV tidak ditemukan', 404

    rendered = render_template('cv_preview.html', data=cv, pdf_mode=True)
    options = {
        'enable-local-file-access': None,
        'quiet': ''
    }
    pdf = pdfkit.from_string(rendered, False, options=options)
    return send_file(io.BytesIO(pdf), as_attachment=True,
                     download_name=f"{cv['name']}.pdf", mimetype='application/pdf')

@app.route('/delete-user/<username>')
def delete_user(username):
    conn = get_db()
    conn.execute('DELETE FROM user WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    return f'Akun dengan username "{username}" telah dihapus.'

if __name__ == '__main__':
    app.run(debug=True)
