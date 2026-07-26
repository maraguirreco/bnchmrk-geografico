import os
# --- INSTALACIÓN DE NAVEGADOR PARA LA NUBE ---
os.system("playwright install chromium")
# ---------------------------------------------

import streamlit as st
import json
import re
import ast
import base64
import time
import requests
import pandas as pd
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image
from openai import OpenAI
from duckduckgo_search import DDGS

# === 🎨 CONFIGURACIÓN DE IDENTIDAD VELOVE ===
LOGO_URL = "https://www.dropbox.com/scl/fi/gftit3er4w0ty3y31r0oy/logo-velove-2026.svg?rlkey=lmmcyddkzhv1qxegy6bgnjvj9&st=2n701c15&raw=1"
COLOR_FONDO = "#e4d2c2"
COLOR_TEXTO = "#001c19"
COLOR_BOTON = "#ff1d4e"
COLOR_BOTON_HOVER = "#e01742"
# ============================================

st.set_page_config(page_title="Velove | Benchmarking AI & Miro", page_icon="🎨", layout="wide")

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Work Sans', sans-serif !important; background-color: {COLOR_FONDO} !important; color: {COLOR_TEXTO} !important; }}
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {{ background-color: #ffffff !important; color: {COLOR_TEXTO} !important; border-radius: 8px !important; border: 1px solid {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    div.stButton > button:first-child {{ background-color: {COLOR_BOTON} !important; color: #ffffff !important; border-radius: 8px !important; border: none !important; font-weight: 600 !important; font-family: 'Work Sans', sans-serif !important; padding: 12px 24px !important; transition: all 0.3s ease !important; }}
    div.stButton > button:first-child:hover {{ background-color: {COLOR_BOTON_HOVER} !important; color: #ffffff !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label {{ color: {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_BOTON} !important; }}
    </style>
""", unsafe_allow_html=True)

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
    MIRO_ACCESS_TOKEN = st.secrets.get("MIRO_ACCESS_TOKEN", "")
except Exception:
    st.error("Falta la credencial de OpenRouter en .streamlit/secrets.toml")
    st.stop()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

def parsear_json_llm(texto):
    if not texto: return []
    texto_clean = re.sub(r'```json\s*', '', texto, flags=re.IGNORECASE)
    texto_clean = re.sub(r'```\s*', '', texto_clean).strip()
    match = re.search(r'\[.*\]', texto_clean, re.DOTALL)
    if not match: return []
    raw_json = match.group(0)
    raw_json_clean = re.sub(r',\s*([\]}])', r'\1', raw_json)
    try: return json.loads(raw_json_clean)
    except Exception: pass
    try: return ast.literal_eval(raw_json_clean)
    except Exception: pass
    try:
        raw_json_fix = raw_json_clean.replace("'", '"')
        raw_json_fix = re.sub(r',\s*([\]}])', r'\1', raw_json_fix)
        return json.loads(raw_json_fix)
    except Exception:
        return []

# === 🕸️ BÚSQUEDA WEB REAL CON FILTRADO ESTRICTO ANTI-LISTAS/BLOGS ===
def buscar_urls_categoria(query, max_results=10, cat_label=""):
    urls_validas = []
    bad_domains = [
        "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas",
        "linguee", "collinsdictionary", "wordreference", "cambridge", "merriam-webster", 
        "rae.es", "reverso", "dictionary", "thesaurus", "traductor", "translate", "ubereats.com",
        "doordash.com", "grubhub.com", "restaurantguru.com", "opentable.com", "eater.com",
        "ranker.com", "buzzfeed.com", "pinterest.com", "tiktok.com"
    ]
    bad_keywords = [
        "diccionario", "dictionary", "traducción", "translation", "significado", "definición",
        "top 10", "top 5", "best 10", "best 5", "los 10", "los 5", "las 10", "las 5",
        "ranking", "listicle", "receta", "recetas", "recipe", "recipes", "comidas tipicas",
        "platillos", "historia de", "history of"
    ]
    
    try:
        time.sleep(0.3)
        results = list(DDGS().text(query, max_results=30))
        if results:
            for r in results:
                url = r.get("href", "").lower()
                title = r.get("title", "").split("-")[0].split("|")[0].strip()
                snippet = r.get("body", "")
                title_lower = title.lower()
                snippet_lower = snippet.lower()
                
                if not url or any(bad in url for bad in bad_domains):
                    continue
                if any(key in title_lower for key in bad_keywords) or any(key in snippet_lower for key in ["10 best", "top 10", "list of", "receta"]):
                    continue
                
                if "facebook.com" in url or "instagram.com" in url:
                    parsed_path = urlparse(url).path.strip("/")
                    if not parsed_path or parsed_path in ["search", "explore", "reels", "p", "stories", "sharer", "dialog"]:
                        continue
                    
                urls_validas.append({
                    "nombre": title, 
                    "url": r.get("href", ""),
                    "snippet": snippet,
                    "categoria": cat_label
                })
                if len(urls_validas) >= max_results: break
    except Exception:
        pass
    return urls_validas

def buscar_pauta_o_grafico(nombre_brand, sector):
    try:
        time.sleep(0.2)
        query = f"{nombre_brand} {sector} publicidad pauta redes sociales"
        results = list(DDGS().images(query, max_results=1))
        for r in results:
            img_url = r.get("image", "")
            if img_url:
                resp = requests.get(img_url, timeout=3)
                if resp.status_code == 200:
                    encoded = base64.b64encode(resp.content).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        pass
    return ""

def comprimir_y_convertir_base64(img_path):
    try:
        if not os.path.exists(img_path): return ""
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            img.thumbnail((400, 400))
            from io import BytesIO
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=65)
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return ""

def extraer_colores_css(page):
    try:
        js_script = """
        () => {
            const colors = new Set();
            const theme = document.querySelector('meta[name="theme-color"]');
            if (theme && theme.content) colors.add(theme.content);
            const elementos = document.querySelectorAll('header, nav, button, a.btn, .button, h1, .primary, .bg-primary');
            elementos.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') colors.add(style.backgroundColor);
                if (style.color && style.color !== 'rgba(0, 0, 0, 0)') colors.add(style.color);
            });
            return Array.from(colors);
        }
        """
        raw_colors = page.evaluate(js_script)
        hex_colors = []
        for c in raw_colors:
            if 'rgb' in c:
                nums = [int(n) for n in re.findall(r'\d+', c)[:3]]
                if len(nums) == 3:
                    r, g, b = nums
                    if sum(nums) > 700 or sum(nums) < 50: continue
                    if abs(r - g) < 10 and abs(g - b) < 10: continue
                    hex_code = '#{:02x}{:02x}{:02x}'.format(r, g, b)
                    if hex_code not in hex_colors: hex_colors.append(hex_code)
            elif c.startswith('#') and len(c) in [4, 7]:
                if c not in hex_colors: hex_colors.append(c)
            if len(hex_colors) >= 5: break
        return hex_colors
    except Exception:
        return []

def extraer_colores_de_imagen(img_path, num_colores=4):
    try:
        if not os.path.exists(img_path): return []
        with Image.open(img_path) as img:
            img = img.convert('RGB').resize((150, 150))
            result = img.quantize(colors=15)
            palette = result.getpalette()
            color_counts = sorted(result.getcolors(), reverse=True, key=lambda x: x[0])
            
            hex_colors = []
            for count, index in color_counts:
                r = palette[index*3]
                g = palette[index*3+1]
                b = palette[index*3+2]
                
                if (r > 235 and g > 235 and b > 235) or (r < 25 and g < 25 and b < 25): continue
                if abs(r - g) < 15 and abs(g - b) < 15 and abs(r - b) < 15: continue
                    
                hex_code = f"#{r:02x}{g:02x}{b:02x}"
                if hex_code not in hex_colors: hex_colors.append(hex_code)
                if len(hex_colors) >= num_colores: break
            return hex_colors
    except Exception:
        return []

# === 🎨 MAQUETADO EN MIRO POR TABLA Y CATEGORÍA ===
def exportar_a_miro_canvas_completo(token, marca, sector, resultados, insights_text):
    if not token or not str(token).strip():
        return None, "No se proporcionó Token de Miro."
    
    token_clean = re.sub(r'[^\x20-\x7E]', '', str(token)).strip()
    headers_json = {
        "Authorization": f"Bearer {token_clean}",
        "Content-Type": "application/json"
    }
    headers_auth = {
        "Authorization": f"Bearer {token_clean}"
    }
    
    def purify_url(path):
        url_base = f"https://api.miro.com/v2{path}"
        return url_base.encode("ascii", "ignore").decode("ascii").strip()

    try:
        url_boards = purify_url("/boards")
        res_board = requests.post(
            url_boards, 
            headers=headers_json, 
            json={"name": f"Velove Benchmark: {marca}", "description": f"Estudio de Competencia ({sector})"}, 
            timeout=10
        )
        if res_board.status_code not in [200, 201]:
            return None, f"Miro API Error {res_board.status_code}: {res_board.text}"
        
        board_data = res_board.json()
        board_id = board_data.get("id")
        board_link = board_data.get("viewLink", f"https://miro.com/app/board/{board_id}/")

        url_texts = purify_url(f"/boards/{board_id}/texts")
        url_images = purify_url(f"/boards/{board_id}/images")
        url_shapes = purify_url(f"/boards/{board_id}/shapes")
        url_stickies = purify_url(f"/boards/{board_id}/sticky_notes")

        categorias_ordenadas = ["Local", "Nacional", "Internacional", "Inspiración"]
        current_y = 0

        for cat_name in categorias_ordenadas:
            items_cat = [c for c in resultados if c.get("categoria", "").lower() == cat_name.lower()]
            if not items_cat:
                continue

            # 1. TÍTULO GRANDE DE CATEGORÍA
            try:
                title_payload = {
                    "data": {"content": f'<p><strong><span style="font-size: 48px; color: #001c19;">{cat_name.upper()}</span></strong></p>'},
                    "style": {"textAlign": "center"},
                    "position": {"x": 800, "y": current_y},
                    "geometry": {"width": 800}
                }
                requests.post(url_texts, headers=headers_json, json=title_payload, timeout=5)
            except Exception: pass

            current_y += 120

            # 2. ENCABEZADOS DE COLUMNA
            try:
                col_headers = [
                    ("Marca", 0),
                    ("Identidad visual", 600),
                    ("Tono y comunicación", 1200)
                ]
                for col_title, x_pos in col_headers:
                    h_payload = {
                        "data": {"content": f'<p><strong><span style="font-size: 22px; color: #333333;">{col_title}</span></strong></p>'},
                        "style": {"textAlign": "center"},
                        "position": {"x": x_pos, "y": current_y},
                        "geometry": {"width": 400}
                    }
                    requests.post(url_texts, headers=headers_json, json=h_payload, timeout=5)
            except Exception: pass

            current_y += 100

            # 3. FILAS DE CADA MARCA
            for comp in items_cat:
                row_y = current_y

                # COLUMNA 1: MARCA
                try:
                    sticky_payload = {
                        "data": {
                            "content": f"<strong>{comp.get('nombre', 'Marca')}</strong>",
                            "shape": "square"
                        },
                        "style": {"fillColor": "light_green", "textAlign": "center"},
                        "position": {"x": 0, "y": row_y},
                        "geometry": {"width": 180}
                    }
                    requests.post(url_stickies, headers=headers_json, json=sticky_payload, timeout=5)
                except Exception: pass

                logo_url = comp.get("logo_url", "")
                if logo_url and logo_url.startswith("http"):
                    try:
                        logo_payload = {
                            "data": {"url": logo_url},
                            "position": {"x": 0, "y": row_y + 130},
                            "geometry": {"width": 70}
                        }
                        requests.post(url_images, headers=headers_json, json=logo_payload, timeout=5)
                    except Exception: pass

                try:
                    url_display = comp.get('url', '#')
                    link_label = "📸 Instagram" if "instagram.com" in url_display else ("📘 Facebook" if "facebook.com" in url_display else url_display)
                    
                    details_html = f"""
                    <p>📍 <strong>Ubicación:</strong> {comp.get('ubicacion', 'N/D')}</p>
                    <p>🌐 <a href="{url_display}">{link_label}</a></p>
                    <p>🛠️ <strong>Servicios:</strong> {comp.get('servicios', 'N/D')}</p>
                    <p>💎 <strong>Propuesta de Valor:</strong> {comp.get('propuesta_valor', 'N/D')}</p>
                    <p>⚡ <strong>Diferencial:</strong> {comp.get('diferencial', 'N/D')}</p>
                    """
                    details_payload = {
                        "data": {"content": details_html},
                        "style": {"fillColor": "#ffffff", "textAlign": "left"},
                        "position": {"x": 0, "y": row_y + 280},
                        "geometry": {"width": 380}
                    }
                    requests.post(url_texts, headers=headers_json, json=details_payload, timeout=5)
                except Exception: pass

                # COLUMNA 2: IDENTIDAD VISUAL
                for c_idx, hex_color in enumerate(comp.get("colores", [])):
                    try:
                        shape_payload = {
                            "data": {"shape": "circle"},
                            "style": {"fillColor": hex_color, "borderColor": "#001c19", "borderWidth": 1.0},
                            "position": {"x": 520 + (c_idx * 55), "y": row_y + 20},
                            "geometry": {"width": 45, "height": 45}
                        }
                        requests.post(url_shapes, headers=headers_json, json=shape_payload, timeout=5)
                    except Exception: pass

                try:
                    nombre_limpio = re.sub(r'\W+', '', comp.get("nombre", "")).lower()
                    screenshot_path = f"assets/{nombre_limpio}.jpg"
                    if os.path.exists(screenshot_path):
                        with open(screenshot_path, "rb") as f:
                            files = {"resource": (f"{nombre_limpio}.jpg", f, "image/jpeg")}
                            data = {
                                "data": json.dumps({
                                    "position": {"x": 600, "y": row_y + 220},
                                    "geometry": {"width": 420}
                                })
                            }
                            requests.post(url_images, headers=headers_auth, files=files, data=data, timeout=10)
                except Exception: pass

                # COLUMNA 3: TONO Y COMUNICACIÓN
                try:
                    tone_html = f"""
                    <p>🎙️ <strong>Tono:</strong> {comp.get('comunicacion', 'N/D')}</p>
                    """
                    tone_payload = {
                        "data": {"content": tone_html},
                        "style": {"fillColor": "#ffffff", "textAlign": "left"},
                        "position": {"x": 1200, "y": row_y + 80},
                        "geometry": {"width": 380}
                    }
                    requests.post(url_texts, headers=headers_json, json=tone_payload, timeout=5)
                except Exception: pass

                current_y += 580

            current_y += 180

        # MURO FINAL DE DIRECCIÓN DE ARTE
        try:
            insights_clean = re.sub(r'<[^<]+?>', '', insights_text)[:1200]
            sticky_payload = {
                "data": {
                    "content": f"🧠 DIRECCIÓN DE ARTE & CONCLUSIONES ESTRATÉGICAS:\n\n{insights_clean}",
                    "shape": "square"
                },
                "style": {"fillColor": "light_yellow"},
                "position": {"x": 1800, "y": 0},
                "geometry": {"width": 600}
            }
            requests.post(url_stickies, headers=headers_json, json=sticky_payload, timeout=5)
        except Exception: pass

        return board_link, None
    except Exception as e:
        return None, f"Excepción Miro: {str(e)}"

# === 🎨 INTERFAZ STREAMLIT ===
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.markdown(f'<img src="{LOGO_URL}" width="150" style="max-width:100%;">', unsafe_allow_html=True)
with col_title:
    st.title("Agente Estratega de Marca & Benchmarking")
    st.markdown("Genera matrices de benchmarking con marcas y negocios reales filtrados en **Miro**.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Calima Bakery")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Panadería y Restaurante Colombiano")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. USA, Colombia, México")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región (Local):", placeholder="Ej. Edison NJ, Cali, CDMX")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Pandebonos, arepas, empanadas y comida típica...", height=68)
    
    st.markdown("---")
    
    st.subheader("📍 Búsqueda por Radio y Proximidad (Opcional)")
    usar_proximidad = st.toggle("Activar búsqueda hiper-local en radio prudente", value=True)
    direccion_exacta = ""
    if usar_proximidad:
        direccion_exacta = st.text_input("Dirección base, barrio o punto de referencia:", placeholder="Ej. Route 27, Edison NJ...").strip()

    st.markdown("---")
    
    col3, col4 = st.columns(2)
    with col3:
        modelo_negocio_opt = st.selectbox(
            "💼 Modelo de Negocio (Opcional):",
            ["General / No especificar (Búsqueda amplia)", "B2B (Empresa a Empresa)", "B2C (Empresa a Consumidor)", "B2B2C", "D2C (Directo al Consumidor)", "Marketplace", "SaaS (Software como Servicio)", "ONG / Sin Ánimo de Lucro", "Gobierno / Sector Público", "Otro (Escribir personalizado)"]
        )
        if modelo_negocio_opt == "Otro (Escribir personalizado)":
            modelo_negocio_final = st.text_input("Especifica el modelo de negocio:", placeholder="Ej. Franquicias").strip() or "General"
        elif "General" in modelo_negocio_opt:
            modelo_negocio_final = "General / No especificado"
        else:
            modelo_negocio_final = modelo_negocio_opt

    with col4:
        competidores_fijos = st.text_input("🎯 Competidores locales conocidos (Opcional - separados por coma):", placeholder="Ej. Noches de Colombia, Colombia Bakery")
        miro_token_input = st.text_input("🔑 Token de Miro (Pega tu Access Token eyJ...):", value=MIRO_ACCESS_TOKEN, type="password")

if st.button("🔥 Ejecutar Benchmark Estratégico y Abrir Miro", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos principales: Marca, Sector, País, Ciudad y Producto.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info(f"🔍 Rastreando marcas comerciales reales en las 4 CATEGORÍAS...")
        
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:20]
        estado = "New Jersey" if "NJ" in ciudad or "Edison" in ciudad else pais
        
        # BÚSQUEDAS ENFOCADAS EN NEGOCIOS (Evitando listicles y noticias)
        locales = buscar_urls_categoria(f"{sector_corto} {ciudad} NJ menu", max_results=8, cat_label="Local")
        locales_prod = buscar_urls_categoria(f"{producto_corto} {ciudad} NJ address", max_results=8, cat_label="Local")
        locales_ig = buscar_urls_categoria(f"{sector_corto} {ciudad} site:instagram.com", max_results=6, cat_label="Local")
        locales_fb = buscar_urls_categoria(f"{sector_corto} {ciudad} site:facebook.com", max_results=6, cat_label="Local")

        nacionales = buscar_urls_categoria(f"panaderia colombiana franquicia {pais}", max_results=8, cat_label="Nacional")
        nacionales_ext = buscar_urls_categoria(f"restaurante colombiano cadena {pais}", max_results=8, cat_label="Nacional")

        internacionales = buscar_urls_categoria(f"global coffee bakery chain", max_results=8, cat_label="Internacional")
        internacionales_ext = buscar_urls_categoria(f"international bakery cafe brand", max_results=8, cat_label="Internacional")

        inspiracion = buscar_urls_categoria(f"artisan bakery brand identity design", max_results=6, cat_label="Inspiración")
        inspiracion_ext = buscar_urls_categoria(f"coffee shop branding design", max_results=6, cat_label="Inspiración")
        
        fijos_lista = []
        if competidores_fijos.strip():
            for item in competidores_fijos.split(","):
                item_clean = item.strip()
                if item_clean:
                    found = buscar_urls_categoria(f"{item_clean} {ciudad}", max_results=1, cat_label="Local")
                    if found:
                        fijos_lista.extend(found)

        todos_los_hallazgos_raw = (
            fijos_lista + locales + locales_prod + locales_ig + locales_fb + 
            nacionales + nacionales_ext + internacionales + 
            internacionales_ext + inspiracion + inspiracion_ext
        )
        
        hallazgos_unicos = []
        urls_vistas = set()
        for idx, item in enumerate(todos_los_hallazgos_raw, 1):
            url_norm = item["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
            if url_norm and url_norm not in urls_vistas:
                urls_vistas.add(url_norm)
                item["id"] = len(hallazgos_unicos) + 1
                hallazgos_unicos.append(item)

        competidores = []

        if hallazgos_unicos:
            status_box.info("🧠 Filtrando marcas comerciales reales (Eliminando blogs, recetas y rankings)...")
            
            prompt_evaluacion = f"""
            Actúa como Senior Market Research Analyst.
            MARCA CLIENTE A EXCLUIR: {marca}
            SECTOR: {sector} ({producto})
            UBICACIÓN: {ciudad}, {pais}
            
            LISTA DE NEGOCIOS REALES ENCONTRADOS EN INTERNET (ID + TITULO + RESUMEN):
            {json.dumps(hallazgos_unicos, ensure_ascii=False)}
            
            ⛔ REGLA DE ORO STRICTA:
            1. ELIMINA Y RECHAZA cualquier resultado que sea un artículo de blog, una lista/ranking ('Los 10 mejores...', 'Top 5...'), una receta o una noticia.
            2. SELECCIONA ÚNICAMENTE MARCAS Y NEGOCIOS COMERCIALES REALES (Establecimientos, restaurantes, cafeterías, marcas).
            3. Selecciona entre 18 y 24 marcas en total repartidas en las 4 categorías: Local, Nacional, Internacional, Inspiración.
            
            Devuelve JSON:
            [
                {{
                    "id": 1,
                    "categoria": "Local" (o "Nacional" / "Internacional" / "Inspiración"),
                    "ubicacion": "Ciudad, País real del negocio",
                    "servicios": "Servicios o productos ofrecidos",
                    "propuesta_valor": "Propuesta comercial del negocio",
                    "diferencial": "Diferencial de la marca",
                    "comunicacion": "Estilo comunicativo de la marca"
                }}
            ]
            """
            
            try:
                res_eval = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_evaluacion}],
                    temperature=0.1
                )
                evaluaciones_ia = parsear_json_llm(res_eval.choices[0].message.content or "")
                
                for item_ia in evaluaciones_ia:
                    match_real = next((h for h in hallazgos_unicos if h["id"] == item_ia.get("id")), None)
                    if match_real:
                        competidores.append({
                            "nombre": match_real["nombre"],
                            "url": match_real["url"],
                            "categoria": item_ia.get("categoria", match_real["categoria"]),
                            "ubicacion": item_ia.get("ubicacion", f"{ciudad}, {pais}"),
                            "servicios": item_ia.get("servicios", "N/D"),
                            "propuesta_valor": item_ia.get("propuesta_valor", "N/D"),
                            "diferencial": item_ia.get("diferencial", "N/D"),
                            "comunicacion": item_ia.get("comunicacion", "N/D")
                        })
            except Exception:
                pass

        # RESPALDO DIRECTO SI LA IA RESTRINGE DEMASIADO
        if len(competidores) < 12 and hallazgos_unicos:
            for item in hallazgos_unicos:
                if not any(c["url"] == item["url"] for c in competidores):
                    competidores.append({
                        "nombre": item["nombre"],
                        "url": item["url"],
                        "categoria": item["categoria"],
                        "ubicacion": f"{ciudad}, {pais}",
                        "servicios": producto,
                        "propuesta_valor": "Marca destacada en el sector.",
                        "diferencial": "Presencia comercial comprobada.",
                        "comunicacion": "Tono de marca comercial."
                    })
                if len(competidores) >= 20:
                    break

        total_marcas = len(competidores)
        if total_marcas == 0:
            st.error("No se pudieron obtener resultados de la web en este momento. Intenta hacer clic nuevamente.")
            st.stop()

        # === FASE 2: AUDITORÍA VISUAL PLAYWRIGHT ===
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        status_box.info(f"📸 Capturando pantallas y extrayendo paletas de color de {total_marcas} marcas reales...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                
                nombre_comp = comp.get("nombre", f"Marca_{index}")
                url_comp = comp.get("url", "")
                
                status_box.warning(f"({index}/{total_marcas}) Auditando presencia digital: {nombre_comp}...")
                nombre_limpio = re.sub(r'\W+', '', nombre_comp).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                
                colores_finales = []
                img_base64 = ""
                
                if url_comp and url_comp.startswith("http") and "google.com" not in url_comp:
                    try:
                        page.goto(url_comp, timeout=8000, wait_until="domcontentloaded")
                        time.sleep(1.2)
                        
                        colores_css = extraer_colores_css(page)
                        page.screenshot(path=screenshot_path, full_page=False, type="jpeg", quality=60)
                        colores_img = extraer_colores_de_imagen(screenshot_path)
                        
                        colores_finales = list(dict.fromkeys(colores_css + colores_img))
                        img_base64 = comprimir_y_convertir_base64(screenshot_path)
                    except Exception:
                        pass
                
                if len(colores_finales) < 2:
                    colores_finales = ["#001c19", "#ff1d4e", "#e4d2c2"]
                
                pauta_base64 = buscar_pauta_o_grafico(nombre_comp, sector_corto)
                domain = urlparse(url_comp).netloc
                
                if "instagram.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/174/174855.png"
                elif "facebook.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/124/124010.png"
                elif domain:
                    logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                else:
                    logo_url = ""
                
                resultados_analisis.append({
                    **comp, 
                    "colores": colores_finales[:4],
                    "img_b64": img_base64, 
                    "pauta_b64": pauta_base64,
                    "logo_url": logo_url
                })
            
            browser.close()
        
        status_box.info("🧠 Generando Dirección de Arte & Conclusiones Estratégicas...")
        progress_bar.progress(0.85)
        
        contexto_resumido = json.dumps([{
            "nombre": r.get("nombre", ""), "categoria": r.get("categoria", ""), 
            "diferencial": r.get("diferencial", "")
        } for r in resultados_analisis])
        
        prompt_insights = f"""
        Actúa como Senior Director de Arte y Estratega de Marca.
        Analiza las {total_marcas} empresas reales auditadas para '{marca}' ({sector} - {producto}) en {ciudad}, {pais}.
        Matriz de marcas: {contexto_resumido}
        
        Entrega ÚNICAMENTE código HTML directo usando etiquetas <h3>, <ul>, <li>, <p> y <strong>.
        
        <h3>📌 1. Patrones y Estándares de la Industria</h3>
        <p>Tendencias de comunicación visual y presencia digital en la zona.</p>
        
        <h3>💡 2. Oportunidades y Gaps en el Mercado</h3>
        <p>Espacios comerciales desaprovechados por los competidores.</p>
        
        <h3>🎨 3. Dirección de Arte Visual Recomendada</h3>
        <p>Estilo gráfico, combinación de colores, tipografías y tratamiento visual.</p>
        
        <h3>🚀 4. Posicionamiento Estratégico y Tono de Voz</h3>
        <p>Estrategia de marca para diferenciarse y liderar.</p>
        """
        
        try:
            res_insights = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt_insights}],
                temperature=0.2
            )
            insights_raw = res_insights.choices[0].message.content or ""
        except Exception:
            insights_raw = "Análisis completado."
        
        if "<h3>" in insights_raw:
            insights_html = insights_raw[insights_raw.find("<h3>"):]
            insights_html = insights_html.replace("```html", "").replace("```", "")
        else:
            insights_html = insights_raw

        # === MAQUETADO TOTALMENTE DESPLEGADO EN MIRO ===
        status_box.info(f"🎨 Creando tablero estructurado por tabla en Miro para las {total_marcas} marcas...")
        progress_bar.progress(0.95)
        
        token_a_usar = miro_token_input.strip() or MIRO_ACCESS_TOKEN
        board_link, miro_err = exportar_a_miro_canvas_completo(token_a_usar, marca, sector, resultados_analisis, insights_html)
        
        # Generación de Copia HTML Local
        tabla_html = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;" title="{c}"></div>' for c in r['colores']])
            
            logo_tag = f'<img src="{r["logo_url"]}" style="width:28px; height:28px; border-radius:4px; border:1px solid #ccc;" onerror="this.style.display=\'none\'">' if r.get("logo_url") else ''
            img_tag = f'<div style="margin-top:6px;"><span style="font-size:10px; font-weight:bold; color:#666;">🖥️ Captura / Presencia Digital:</span><br><img src="{r["img_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("img_b64") else '<div style="background:#f0e2d5; padding:10px; border-radius:6px; color:#666; font-size:10px; margin-top:6px;">Web no disponible</div>'
            pauta_tag = f'<div style="margin-top:8px;"><span style="font-size:10px; font-weight:bold; color:{COLOR_BOTON};">📢 Pauta / Pieza Gráfica:</span><br><img src="{r["pauta_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("pauta_b64") else ''
            
            url_display = r.get("url", "#")
            link_text = "📸 Perfil de Instagram" if "instagram.com" in url_display else ("📘 Página de Facebook" if "facebook.com" in url_display else "🌐 Sitio Web Oficial")
            
            tabla_html += f"""
            <tr>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        {logo_tag}
                        <div>
                            <strong style="font-size:14px; color:{COLOR_TEXTO};">{r.get("nombre", "Marca")}</strong><br>
                            <span style="font-size:10px; font-weight:700; color:{COLOR_BOTON}; text-transform:uppercase;">{r.get("categoria", "Competidor")}</span>
                        </div>
                    </div>
                    <p style="font-size:11px; margin:2px 0; color:#333;">📍 {r.get("ubicacion", "N/D")}</p>
                    <a href="{url_display}" target="_blank" style="font-size:11px; color:{COLOR_BOTON}; font-weight:600;">{link_text}</a>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.4;">
                    <p style="margin:0 0 6px 0;"><strong>Servicios:</strong> {r.get("servicios", "N/D")}</p>
                    <p style="margin:0 0 6px 0;"><strong>Propuesta:</strong> {r.get("propuesta_valor", "N/D")}</p>
                    <p style="margin:0;"><strong>Diferencial:</strong> {r.get("diferencial", "N/D")}</p>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top; text-align:center;">
                    <div style="margin-bottom:6px;">{color_html}</div>
                    {img_tag}
                    {pauta_tag}
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.4;">
                    {r.get("comunicacion", "N/D")}
                </td>
            </tr>
            """
        
        html_final = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Benchmark Velove: {marca}</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Work Sans', sans-serif; padding: 40px; background-color: {COLOR_FONDO}; color: {COLOR_TEXTO}; line-height: 1.5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background-color: {COLOR_TEXTO}; color: {COLOR_FONDO}; padding: 30px; border-radius: 12px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }}
                .header-info h1 {{ margin: 0 0 6px 0; font-size: 26px; font-weight: 700; color: {COLOR_FONDO}; }}
                .header-info p {{ margin: 0; opacity: 0.85; font-size: 13px; color: {COLOR_FONDO}; }}
                .logo-img {{ height: 50px; object-fit: contain; }}
                table {{ width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 35px; }}
                th {{ background-color: {COLOR_TEXTO}; color: {COLOR_FONDO}; padding: 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
                .insights-card {{ background: #ffffff; padding: 35px; border-radius: 12px; border-left: 6px solid {COLOR_BOTON}; box-shadow: 0 4px 10px rgba(0,0,0,0.05); line-height: 1.6; }}
                .insights-card h3 {{ color: {COLOR_TEXTO}; margin-top: 20px; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-info">
                        <h1>📊 Matriz de Benchmarking Estratégico ({total_marcas} Marcas Auditadas)</h1>
                        <p><strong>Cliente:</strong> {marca} &nbsp;|&nbsp; <strong>Sector:</strong> {sector} &nbsp;|&nbsp; <strong>Ubicación:</strong> {ciudad}, {pais}</p>
                    </div>
                    <img src="{LOGO_URL}" class="logo-img" alt="Logo Velove">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th width="25%">Marca & Ubicación</th>
                            <th width="30%">Análisis Estratégico</th>
                            <th width="25%">Identidad Visual</th>
                            <th width="20%">Tono & Comunicación</th>
                        </tr>
                    </thead>
                    <tbody>{tabla_html}</tbody>
                </table>
                <h2 style="font-size: 22px; color: {COLOR_TEXTO}; margin-bottom: 15px;">🧠 Dirección de Arte & Conclusiones Estratégicas</h2>
                <div class="insights-card">{insights_html}</div>
            </div>
        </body>
        </html>
        """
        with open("reporte.html", "w", encoding="utf-8") as f: f.write(html_final)
        
        progress_bar.progress(1.0)
        status_box.success(f"🎉 ¡Benchmark Completo de {total_marcas} Marcas REALES auditado!")

        if board_link:
            st.balloons()
            st.success("¡Tablero Visual Creado Exitosamente en Miro! 🚀")
            st.link_button("🎨 Abrir Tablero Directamente en Miro", board_link, type="primary")
        elif miro_err and miro_token_input.strip():
            st.warning(f"Se completó la auditoría. Detalle Miro: {miro_err}")

        st.markdown("---")
        with open("reporte.html", "rb") as file:
            st.download_button(f"📥 Descargar Reporte HTML Velove ({total_marcas} Marcas)", data=file, file_name=f"Benchmark_Velove_{marca.replace(' ', '_')}.html", mime="text/html")
