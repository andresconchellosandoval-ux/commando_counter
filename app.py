from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import re
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_llave_secreta_aqui' # Cambia esto por algo seguro

# Configuración de Base de Datos (SQLite)
app.config['SQLALCHEMY_DATABASE_DATABASE_URI'] = 'sqlite:///conciliacion.db'
db = SQLAlchemy(app)

# --- MODELOS DE BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    records = db.relationship('Record', backref='owner', lazy=True)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_vasos = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- LÓGICA DE PROCESAMIENTO (Tu código adaptado) ---
def procesar_archivo(ruta, filename):
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

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return '''<form method="post">User: <input name="username"> Pass: <input type="password" name="password"> <button>Registro</button></form>'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Login fallido')
    return '''<form method="post">User: <input name="username"> Pass: <input type="password" name="password"> <button>Entrar</button></form>'''

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        file = request.files['file']
        if file:
            path = os.path.join('uploads', file.filename)
            file.save(path)
            resultado = procesar_archivo(path, file.filename)
            
            # Guardar en la cuenta del usuario
            nuevo_registro = Record(total_vasos=resultado, user_id=user.id)
            db.session.add(nuevo_registro)
            db.session.commit()
            
    # Obtener historial del usuario
    historial = Record.query.filter_by(user_id=user.id).order_by(Record.date.desc()).all()
    return f"Hola {user.username}! Has conciliado {len(historial)} veces. <br> " + \
           '<form method="post" enctype="multipart/form-data"><input type="file" name="file"><button>Cargar</button></form>'

if __name__ == '__main__':
    if not os.path.exists('uploads'): os.makedirs('uploads')
    with app.app_context():
        db.create_all()
    app.run(debug=True)
