from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# SECRET KEY wajib ada untuk fitur keamanan (Login & Session)
app.config['SECRET_KEY'] = 'kunci_rahasia_habit_tracker_super_aman'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- SETUP SATPAM (LOGIN MANAGER) ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Jika belum login, lempar ke halaman /login

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CETAK BIRU DATABASE BARU ---
# 1. Tabel Pengguna (User)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Relasi: 1 User bisa punya banyak Habit
    habits = db.relationship('Habit', backref='pemilik', lazy=True)

# 2. Tabel Kebiasaan (Habit)
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Belum")
    tanggal_selesai = db.Column(db.String(20), nullable=True)
    streak = db.Column(db.Integer, default=0)
    # Kunci Tamu (Foreign Key): Menandakan habit ini milik siapa
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

# --- RUTE AKUN (LOGIN & REGISTER) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username_baru = request.form.get('username')
        password_baru = request.form.get('password')
        
        # Cek apakah username sudah dipakai
        user_ada = User.query.filter_by(username=username_baru).first()
        if user_ada:
            return "Username sudah terpakai, coba yang lain!"
            
        # Acak password demi keamanan
        password_acak = generate_password_hash(password_baru)
        user_baru = User(username=username_baru, password=password_acak)
        db.session.add(user_baru)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_input = request.form.get('username')
        password_input = request.form.get('password')
        
        user = User.query.filter_by(username=username_input).first()
        # Cek apakah user ada dan password cocok
        if user and check_password_hash(user.password, password_input):
            login_user(user)
            return redirect(url_for('beranda'))
        else:
            return "Username atau Password salah!"
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- RUTE UTAMA (DILINDUNGI @login_required) ---

@app.route('/')
@login_required # <-- BARU: Harus login untuk melihat halaman ini
def beranda():
    hari_ini = date.today()
    # PENTING: Hanya tarik habit milik user yang sedang login!
    habit_ku = Habit.query.filter_by(user_id=current_user.id).all()

    for habit in habit_ku:
        if habit.tanggal_selesai:
            tgl_selesai_obj = datetime.strptime(habit.tanggal_selesai, "%Y-%m-%d").date()
            selisih_hari = (hari_ini - tgl_selesai_obj).days
            
            if selisih_hari > 0 and habit.status == 'Selesai':
                habit.status = 'Belum'
            if selisih_hari > 1:
                habit.streak = 0
                
            db.session.commit()

    return render_template('index.html', habits=habit_ku)

@app.route('/tambah', methods=['POST'])
@login_required
def tambah():
    nama_baru = request.form.get('nama_habit')
    if nama_baru:
        # Masukkan user_id saat membuat habit baru
        habit_baru = Habit(nama=nama_baru, user_id=current_user.id)
        db.session.add(habit_baru)
        db.session.commit()
    return redirect(url_for('beranda'))

@app.route('/hapus/<int:id_habit>')
@login_required
def hapus(id_habit):
    habit_yang_mau_dihapus = Habit.query.get(id_habit)
    # Pastikan habit itu benar-benar milik user ini (keamanan tambahan)
    if habit_yang_mau_dihapus and habit_yang_mau_dihapus.user_id == current_user.id:
        db.session.delete(habit_yang_mau_dihapus)
        db.session.commit()
    return redirect(url_for('beranda'))

@app.route('/selesai/<int:id_habit>')
@login_required
def selesai(id_habit):
    habit_yang_selesai = Habit.query.get(id_habit)
    if habit_yang_selesai and habit_yang_selesai.user_id == current_user.id:
        habit_yang_selesai.status = 'Selesai'
        habit_yang_selesai.tanggal_selesai = date.today().strftime("%Y-%m-%d")
        habit_yang_selesai.streak += 1 
        db.session.commit()
    return redirect(url_for('beranda'))

if __name__ == '__main__':
    app.run(debug=True)