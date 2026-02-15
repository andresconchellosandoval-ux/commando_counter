from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def encontrar_columna(df, posibles):
    for col in df.columns:
        if any(p in str(col).lower() for p in posibles):
            return col
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    total_vasos = None
    error = None

    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo and archivo.filename != "":
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)
            try:
                # Leer archivo
                if archivo.filename.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(ruta)
                else:
                    df = pd.read_csv(ruta, encoding="latin1")

                # Detectar columnas (Producto y Cantidad)
                c_prod = encontrar_columna(df, ["producto", "product", "item", "nombre", "artículo"])
                c_cant = encontrar_columna(df, ["cantidad", "qty", "total", "unid", "vta", "vendidos"])

                if c_prod and c_cant:
                    # Convertir cantidad a número (por si vienen espacios o texto)
                    df[c_cant] = pd.to_numeric(df[c_cant], errors='coerce').fillna(0)
                    
                    # LISTA NEGRA: Lo que NO lleva vaso
                    excluir = ["extra", "electrolife", "cafe", "quest", "zoe"]
                    
                    def es_valido(nombre):
                        n = str(nombre).lower().strip()
                        if not n or n in ["nan", "total", "subtotal"]: return False
                        if any(p in n for p in excluir): return False
                        return True

                    # Filtrar productos que SÍ son shakes
                    df_final = df[df[c_prod].apply(es_valido)]
                    
                    # SUMA REAL: Sumamos los valores de la columna de cantidad
                    total_vasos = int(df_final[c_cant].sum())
                else:
                    error = f"No encontré las columnas. Columnas detectadas: {list(df.columns)}"
            except Exception as e:
                error = f"Error: {str(e)}"

    return render_template("index.html", total_vasos=total_vasos, error=error)

if __name__ == "__main__":
    app.run(port=5050, debug=True)