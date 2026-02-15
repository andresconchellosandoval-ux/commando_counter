# ... (dentro de la función contar o index)
                # 1. Leer sin importar el formato
                df = pd.read_excel(ruta) if archivo.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(ruta, encoding="latin1")
                
                # 2. Convertir TODO a minúsculas y quitar espacios locos
                df.columns = [str(c).strip().lower() for c in df.columns]

                # 3. Buscar columnas por palabras clave (más flexible todavía)
                c_prod = next((c for c in df.columns if any(p in c for p in ["prod", "item", "nombre", "articulo"])), None)
                c_cant = next((c for c in df.columns if any(p in c for p in ["qty", "cant", "total", "unid"])), None)

                if c_prod and c_cant:
                    # Limpiar números (quitar comas de miles si existen)
                    df[c_cant] = pd.to_numeric(df[c_cant].astype(str).str.replace('[^0-9.]', '', regex=True), errors='coerce').fillna(0)
                    
                    shakes = ["amino juice", "banana boost", "berry mango", "berry oat", "blue lemonade", "caramel", "cha cha matcha", "chai chai", "dark acai", "double berry", "fresas y machos", "hazzelino", "manito", "la manita", "mr reeses", "original", "simple", "canelita", "mango coco", "silvestre", "quaker", "vital vainilla latte"]
                    
                    # Comparación a prueba de errores
                    def limpiar(t): return re.sub(r'[^a-z0-9]', '', str(t).lower())
                    sk_limpios = [limpiar(s) for s in shakes]

                    # Filtramos: Si el shake limpio está contenido en el nombre del producto limpio
                    mask = df[c_prod].apply(lambda x: any(s in limpiar(x) for s in sk_limpios))
                    total_vasos = int(df[mask][c_cant].sum())
