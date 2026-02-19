from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import re
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'commando_secret_123')

# --- CONFIGURACIÓN DE BASE DE DATOS ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///commando.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    records = db.relationship('Record', backref='owner', lazy=True)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now)
    total_vasos = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_archivo(ruta, filename):
    try:
        df = pd.read_excel(ruta) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(ruta, encoding="latin1")
        df.columns = [str(c).strip().lower() for c in df.columns]
        c_prod = next((c for c in df.columns if any(p in c for p in ["prod", "item", "nombre", "articulo"])), None)
        c_cant = next((c for c in df.columns if any(p in c for p in ["qty", "cant", "total", "unid"])), None)
        if c_prod and c_cant:
            df[c_cant] = pd.to_numeric(df[c_cant].astype(str).str.replace('[^0-9.]', '', regex=True), errors='coerce').fillna(0)
            shakes = ["amino juice", "banana boost", "berry mango", "berry oat", "blue lemonade", "caramel", "cha cha matcha", "chai chai", "dark acai", "double berry", "fresas y machos", "hazzelino", "manito", "la manita", "mr reeses", "original", "simple", "canelita", "mango coco", "silvestre", "quaker", "vital vainilla latte"]
            def limpiar(t): return re.sub(r'[^a-z0-9]', '', str(t).lower())
            sk_limpios = [limpiar(s) for s in shakes]
            mask = df[c_prod].apply(lambda x: any(s in limpiar(x) for s in sk_limpios))
            return int(df[mask][c_cant].sum())
        return 0
    except: return 0

# --- RUTAS ---
@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'].strip()).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username'].strip()).first():
            flash('El usuario ya existe')
        else:
            hashed_pw = generate_password_hash(request.form['password'])
            db.session.add(User(username=request.form['username'].strip(), password=hashed_pw))
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    total_vasos = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            if not os.path.exists('uploads'): os.makedirs('uploads')
            path = os.path.join('uploads', file.filename)
            file.save(path)
            total_vasos = procesar_archivo(path, file.filename)
            db.session.add(Record(total_vasos=total_vasos, user_id=user.id))
            db.session.commit()
            if os.path.exists(path): os.remove(path)
    historial = Record.query.filter_by(user_id=user.id).order_by(Record.date.desc()).limit(10).all()
    return render_template('dashboard.html', user=user, total_vasos=total_vasos, historial=historial)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
