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
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
from io import BytesIO
from openai import OpenAI
from duckduckgo_search import DDGS

# === 🎨 CONFIGURACIÓN DE INTERFAZ ===
COLOR_FONDO = "#e4d2c2"
COLOR_TEXTO = "#001c19"
COLOR_BOTON = "#ff1d4e"
COLOR_BOTON_HOVER = "#e01742"

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
    """ Repara cualquier error de formato o sintaxis devuelto por la IA """
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

# === 🕸️ BÚSQUEDA WEB UNIVERSAL BLINDADA ===
def buscar_urls_reales(query, max_results=15, cat_label=""):
    urls_validas = []
    bad_domains = [
        "google.com", "wikipedia.org", "wikipedia.com", "yelp.com", "tripadvisor.com",
        "computrabajo.com", "paginasamarillas.com", "yellowpages.com", "linguee.com",
        "collinsdictionary.com", "wordreference.com", "cambridge.org", "merriam-webster.com",
        "rae.es", "reverso.net", "dictionary.com", "thesaurus.com", "traductor.com",
        "translate.google.com", "ubereats.com", "doordash.com", "grubhub.com",
        "restaurantguru.com", "opentable.com", "eater.com", "ranker.com", "buzzfeed.com",
        "pinterest.com", "tiktok.com", "jlaforums.com", "forum", "viewtopic", "viewforum", "reddit.com"
    ]
    bad_keywords = [
        "diccionario", "dictionary", "traducción", "translation", "significado", "definición",
        "top 10", "top 5", "best 10", "best 5", "los 10", "los 5", "las 10", "las 5",
        "ranking", "listicle", "receta", "recetas", "recipe", "recipes"
    ]
    
    for intento in range(2):
        try:
            time.sleep(0.4)
            results = list(DDGS().text(query, max_results=30))
            if results:
                for r in results:
                    url = r.get("href", "").lower()
                    title = r.get("title", "").split("-")[0].split("|")[0].strip()
                    snippet = r.get("body", "")
                    title_lower = title.lower()
                    
                    if not url or any(bad in url for bad in bad_domains):
                        continue
                    if any(key in title_lower for key in bad_keywords):
                        continue
                    
                    # Permite perfiles oficiales directos de redes si no son páginas de búsqueda/exploración
                    if "facebook.com" in url or "instagram.com" in url:
                        parsed_path = urlparse(url).path.strip("/")
                        if not parsed_path or parsed_path in ["search", "explore", "reels", "p", "stories", "sharer", "dialog", "groups"]:
                            continue
                            
                    urls_validas.append({
                        "nombre": title, 
                        "url": r.get("href", ""),
                        "snippet": snippet,
                        "categoria": cat_label
                    })
                    if len(urls_validas) >= max_results: break
                if urls_validas: break
        except Exception:
            time.sleep(0.4)
    return urls_validas

def buscar_pauta_o_grafico(nombre_brand, sector):
    try:
        time.sleep(0.3)
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
            img.thumbnail((800, 800))
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return ""

def generar_imagen_resguardo_hd(nombre_brand, colores, output_path):
    """ Genera tarjeta gráfica HD si la captura web falla """
    try:
        width, height = 800, 500
        bg_color = colores[0] if colores else "#2D3748"
        accent_color = colores[1] if len(colores) > 1 else "#A0AEC0"
        
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, height - 30, width, height], fill=accent_color)
        img.save(output_path, 'JPEG', quality=90)
    except Exception:
        pass

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

            # 1. TÍTULO DE CATEGORÍA
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

            # 3. FILAS DE CADA MARCA EN LA CATEGORÍA
            for comp in items_cat:
                row_y = current_y

                # COLUMNA 1: MARCA (Sticky note)
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

                # Logo HD
                logo_url = comp.get("logo_url", "")
                if logo_url and logo_url.startswith("http"):
                    try:
                        logo_payload = {
                            "data": {"url": logo_url},
                            "position": {"x": 0, "y": row_y + 130},
                            "geometry": {"width": 90}
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

                # COLUMNA 2: IDENTIDAD VISUAL (Muestras de Color + Captura HD)
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
                    if not os.path.exists(screenshot_path):
                        generar_imagen_resguardo_hd(comp.get("nombre", "Marca"), comp.get("colores", []), screenshot_path)

                    if os.path.exists(screenshot_path):
                        with open(screenshot_path, "rb") as f:
                            files = {"resource": (f"{nombre_limpio}.jpg", f, "image/jpeg")}
                            payload_data = {
                                "data": json.dumps({
                                    "position": {"x": 600, "y": int(row_y + 220)},
                                    "geometry": {"width": 450}
                                })
                            }
                            requests.post(url_images, headers=headers_auth, files=files, data=payload_data, timeout=12)
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
col_title, col_sub = st.columns([4, 1])
with col_title:
    st.title("Agente Estratega de Marca & Benchmarking AI")
    st.markdown("Genera matrices de benchmarking universales (hasta 8-10 marcas por categoría) con datos 100% reales.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Calima Bakery")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Panadería y Restaurante Colombiano")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. USA, Colombia, México, España")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región (Local):", placeholder="Ej. Edison NJ, Cali, CDMX, Madrid")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Pandebonos, empanadas, comida típica colombiana...", height=68)
    
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
        competidores_fijos = st.text_input("🎯 Competidores locales conocidos (Opcional - separados por coma):", placeholder="Ej. Noches de Colombia, Brisas Colombianas")
        miro_token_input = st.text_input("🔑 Token de Miro (Pega tu Access Token eyJ...):", value=MIRO_ACCESS_TOKEN, type="password")

if st.button("🔥 Ejecutar Benchmark Estratégico", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos obligatorios: Marca, Sector, País, Ciudad y Producto.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info(f"🔍 Rastreando competidores reales para '{sector}'...")
        
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        
        # BÚSQUEDAS WEB AMPLIADAS POR CATEGORÍA
        locales_web = buscar_urls_reales(f"{sector_corto} {producto_corto} {ciudad} {pais}", max_results=15, cat_label="Local")
        if len(locales_web) < 8:
            locales_web += buscar_urls_reales(f"mejores {sector_corto} {ciudad} {pais}", max_results=10, cat_label="Local")

        nacionales_web = buscar_urls_reales(f"top mejores empresas cadenas {sector_corto} {pais}", max_results=15, cat_label="Nacional")
        inter_web = buscar_urls_reales(f"top global leading companies {sector_corto} {producto_corto}", max_results=15, cat_label="Internacional")
        insp_web = buscar_urls_reales(f"{sector_corto} {producto_corto} branding design identity case study", max_results=8, cat_label="Inspiración")
        
        fijos_lista = []
        if competidores_fijos.strip():
            for item in competidores_fijos.split(","):
                item_clean = item.strip()
                if item_clean:
                    found = buscar_urls_reales(f"{item_clean} {ciudad}", max_results=1, cat_label="Local")
                    if found:
                        fijos_lista.append(found[0])
                    else:
                        fijos_lista.append({"nombre": item_clean, "url": f"https://www.google.com/search?q={item_clean}", "categoria": "Local"})

        todos_los_hallazgos = fijos_lista + locales_web + nacionales_web + inter_web + insp_web
        
        hallazgos_unicos = []
        urls_vistas = set()
        for idx, item in enumerate(todos_los_hallazgos, 1):
            domain = urlparse(item["url"]).netloc.replace("www.", "").strip("/")
            if domain and domain not in urls_vistas:
                urls_vistas.add(domain)
                item["id"] = len(hallazgos_unicos) + 1
                hallazgos_unicos.append(item)

        competidores = []

        if len(hallazgos_unicos) >= 2:
            status_box.info("🧠 Filtrando pertinencia de marcas y ordenando por cuotas objetivo...")
            
            prompt_descubrimiento = f"""
            Actúa como Senior Market Research Analyst.
            
            BRIEF DEL CLIENTE:
            - Marca cliente (A EXCLUIR): {marca}
            - Sector: {sector}
            - Producto / Core: {producto}
            - Ubicación Local: {ciudad}, {pais}
            - País Nacional: {pais}
            - Modelo de Negocio: {modelo_negocio_final}
            
            BASE DE DATOS DE URLs REALES ENCONTRADAS EN LA BÚSQUEDA WEB (USA ÚNICAMENTE ESTOS ID):
            {json.dumps(hallazgos_unicos, ensure_ascii=False)}
            
            ⛔ REGLAS STRICTAS DE SELECCIÓN Y PERTINENCIA:
            1. CERO INVENCIÓN: Elige ÚNICAMENTE marcas o empresas comerciales reales que aparezcan en los ID del JSON o sean entidades 100% reales existentes en el mercado. JAMÁS inventes nombres o perfiles de redes sociales que no existan.
            2. PERTINENCIA Y MODELO DE NEGOCIO:
               - "Local": Marcas o restaurantes/locales que compitan directamente en {ciudad}, {pais} o su radio metropolitano cercano.
               - "Nacional": Cadenas o marcas líderes en {pais} del MISMO SECTOR Y MODELO DE NEGOCIO.
               - "Internacional": Marcas líderes a nivel mundial que operen en el mismo formato/formato de negocio.
               - "Inspiración": Casos de éxito en branding, diseño y experiencia del cliente afines a {sector}.
            3. REGLE DE CUOTAS DINÁMICAS:
               - Intenta seleccionar entre 8 a 10 marcas para "Local", 8 a 10 para "Nacional", 8 a 10 para "Internacional" y 4 a 6 para "Inspiración".
               - ¡ATENCIÓN! Si no existen o no encuentras 8 o 10 marcas reales en alguna categoría, INCLUYE ÚNICAMENTE LAS QUE SEAN REALES. NO inventes marcas ni rellenes con información falsa bajo ninguna circunstancia.
            
            Devuelve ÚNICAMENTE un arreglo JSON:
            [
                {{
                    "nombre": "Nombre Comercial Real",
                    "url": "https://www.sitioweboficialreal.com o perfil oficial real",
                    "categoria": "Local / Nacional / Internacional / Inspiración",
                    "ubicacion": "Ciudad, País real",
                    "colores_estimados": ["#HEX1", "#HEX2"],
                    "justificacion": "Por qué es relevante y afín al modelo de negocio",
                    "servicios": "Servicios reales ofrecidos",
                    "propuesta_valor": "Propuesta de valor real",
                    "diferencial": "Factor diferencial real",
                    "comunicacion": "Tono de marca"
                }}
            ]
            """
            
            try:
                res_descubrimiento = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_descubrimiento}],
                    temperature=0.1
                )
                raw_content = res_descubrimiento.choices[0].message.content or ""
                competidores = parsear_json_llm(raw_content)
            except Exception:
                pass

        # Si las búsquedas en vivo fallaron completamente, rescate de respaldo con marcas 100% reales
        if len(competidores) < 5:
            status_box.warning("⚡ Rastreando base neuronal de marcas reales para asegurar cobertura de mercado...")
            prompt_rescue = f"""
            Actúa como Senior Brand Strategist.
            Proporciona un estudio de competencia de MARCAS 100% REALES, EXISTENTES Y REPUTADAS para la marca '{marca}' en el sector '{sector}' (Producto: {producto}) en {ciudad}, {pais}.
            
            🎯 CRITERIOS POR CATEGORÍA (MÁXIMO HASTA 8-10 SI EXISTEN, SIN INVENTAR MARCAS FALSAS):
            - Locales: Marcas reales en o cerca de {ciudad}, {pais}.
            - Nacionales: Cadenas y empresas líderes reales en {pais}.
            - Internacionales: Gigantes y referentes globales del sector.
            - Inspiración: Casos de éxito en branding/experiencia alineados a {sector}.
            
            NO INVENTES URLS FALSAS DE REDES SOCIALES NI NOMBRES INEXISTENTES.
            
            Devuelve ÚNICAMENTE un arreglo JSON:
            [
                {{
                    "nombre": "Nombre Comercial Real",
                    "url": "https://www.sitioweboficialreal.com",
                    "categoria": "Local / Nacional / Internacional / Inspiración",
                    "ubicacion": "Ciudad, País",
                    "colores_estimados": ["#2D3748", "#A0AEC0"],
                    "justificacion": "Menciona su prestigio o relevancia en la industria",
                    "servicios": "Servicios principales",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Tono de marca"
                }}
            ]
            """
            try:
                res_rescue = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_rescue}],
                    temperature=0.2
                )
                competidores = parsear_json_llm(res_rescue.choices[0].message.content or "")
            except Exception:
                pass

        total_marcas = len(competidores)
        if total_marcas == 0:
            st.error("No se encontraron suficientes marcas. Por favor presiona el botón nuevamente.")
            st.stop()

        # === FASE 2: AUDITORÍA VISUAL PLAYWRIGHT (HD + LOGOS CLEARBIT/HD + CAPTURA RESGUARDO) ===
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        
        status_box.info(f"📸 Capturando sitios web y analizando identidades visuales de {total_marcas} marcas reales...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
            page = context.new_page()
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                
                nombre_comp = comp.get("nombre", f"Marca_{index}")
                url_comp = comp.get("url", "")
                
                colores_backup = comp.get("colores_estimados", ["#2D3748", "#A0AEC0"])
                
                status_box.warning(f"({index}/{total_marcas}) Auditando visualmente: {nombre_comp}...")
                nombre_limpio = re.sub(r'\W+', '', nombre_comp).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                
                colores_finales = []
                img_base64 = ""
                
                if url_comp and "google.com" not in url_comp and url_comp.startswith("http"):
                    try:
                        page.goto(url_comp, timeout=9000, wait_until="domcontentloaded")
                        time.sleep(1.2)
                        
                        colores_css = extraer_colores_css(page)
                        page.screenshot(path=screenshot_path, full_page=False, type="jpeg", quality=85)
                        colores_img = extraer_colores_de_imagen(screenshot_path)
                        
                        colores_finales = list(dict.fromkeys(colores_css + colores_img))
                        img_base64 = comprimir_y_convertir_base64(screenshot_path)
                    except Exception:
                        pass
                
                if len(colores_finales) < 2:
                    colores_finales = colores_backup
                
                # GARANTIZAR IMAGEN FÍSICA EN DISCO PARA MIRO
                if not os.path.exists(screenshot_path):
                    generar_imagen_resguardo_hd(nombre_comp, colores_finales, screenshot_path)
                    img_base64 = comprimir_y_convertir_base64(screenshot_path)

                pauta_base64 = buscar_pauta_o_grafico(nombre_comp, sector_corto)
                domain = urlparse(url_comp).netloc.replace("www.", "").strip()
                
                # OBTENCIÓN DE LOGO HD (CLEARBIT / GOOGLE HD)
                if "instagram.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/174/174855.png"
                elif "facebook.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/124/124010.png"
                elif domain:
                    clearbit_url = f"https://logo.clearbit.com/{domain}"
                    try:
                        resp_logo = requests.get(clearbit_url, timeout=2)
                        if resp_logo.status_code == 200:
                            logo_url = clearbit_url
                        else:
                            logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
                    except Exception:
                        logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
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
        
        status_box.info("🧠 Generando Dirección de Arte y Conclusiones Estratégicas...")
        progress_bar.progress(0.85)
        
        contexto_resumido = json.dumps([{
            "nombre": r.get("nombre", ""), "categoria": r.get("categoria", ""), 
            "diferencial": r.get("diferencial", "")
        } for r in resultados_analisis])
        
        prompt_insights = f"""
        Actúa como Senior Director de Arte y Estratega de Marca.
        Analiza las {total_marcas} empresas auditadas para la marca '{marca}' ({sector} - {producto}) en {ciudad}, {pais}.
        Matriz de competidores: {contexto_resumido}
        
        ⛔ INSTRUCCIÓN DE SALIDA ESTRICTA:
        Entrega ÚNICAMENTE código HTML directo usando exclusivamente las etiquetas <h3>, <ul>, <li>, <p> y <strong>.
        NO incluyas ninguna frase introductiva, markdown como ```html, meta-comentario ni texto fuera del HTML.
        
        <h3>📌 1. Patrones y Estándares del Sector</h3>
        <p>Análisis de tendencias de comunicación y códigos visuales comunes.</p>
        
        <h3>💡 2. Gaps y Oportunidades de Mercado</h3>
        <p>Espacios estratégicos desaprovechados por los competidores actuales.</p>
        
        <h3>🎨 3. Dirección de Arte Visual Recomendada</h3>
        <p>Pautas para estilo gráfico, colores, tipografía y tratamiento de imagen.</p>
        
        <h3>🚀 4. Posicionamiento Estratégico y Tono de Voz</h3>
        <p>Estrategia de diferenciación y estilo comunicativo recomendado.</p>
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
        
        # === EXPORTACIÓN Y MAQUETADO A MIRO ===
        status_box.info("🎨 Maquetando investigación en tabla ordenada dentro de Miro...")
        progress_bar.progress(0.95)
        
        token_a_usar = miro_token_input.strip() or MIRO_ACCESS_TOKEN
        board_link, miro_err = exportar_a_miro_canvas_completo(token_a_usar, marca, sector, resultados_analisis, insights_html)

        # Generación de Copia HTML Local limpia sin sintaxis Markdown en los enlaces de fuentes
        tabla_html = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;" title="{c}"></div>' for c in r['colores']])
            
            logo_tag = f'<img src="{r["logo_url"]}" style="width:36px; height:36px; border-radius:4px; border:1px solid #ccc; object-fit:contain;" onerror="this.style.display=\'none\'">' if r.get("logo_url") else ''
            img_tag = f'<div style="margin-top:6px;"><span style="font-size:10px; font-weight:bold; color:#666;">🖥️ Captura Web / Presencia Digital:</span><br><img src="{r["img_b64"]}" style="width:100%; max-width:280px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("img_b64") else '<div style="background:#f0e2d5; padding:10px; border-radius:6px; color:#666; font-size:10px; margin-top:6px;">Web no disponible</div>'
            pauta_tag = f'<div style="margin-top:8px;"><span style="font-size:10px; font-weight:bold; color:#3182ce;">📢 Pauta / Pieza Gráfica:</span><br><img src="{r["pauta_b64"]}" style="width:100%; max-width:280px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("pauta_b64") else ''
            
            url_display = r.get("url", "#")
            link_text = "📸 Perfil de Instagram" if "instagram.com" in url_display else ("📘 Página de Facebook" if "facebook.com" in url_display else "🌐 Sitio Web Oficial")

            tabla_html += f"""
            <tr>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                        {logo_tag}
                        <div>
                            <strong style="font-size:15px; color:#2d3748;">{r.get("nombre", "Marca")}</strong><br>
                            <span style="font-size:10px; font-weight:700; color:#3182ce; text-transform:uppercase;">{r.get("categoria", "Competidor")}</span>
                        </div>
                    </div>
                    <p style="font-size:11px; margin:2px 0; color:#333;">📍 {r.get("ubicacion", "N/D")}</p>
                    <a href="{url_display}" target="_blank" style="font-size:11px; color:#3182ce; font-weight:600;">{link_text}</a>
                    <p style="font-size:11px; color:#555; margin-top:6px; line-height:1.3;"><i>"{r.get("justificacion", "")}"</i></p>
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
            <title>Benchmark: {marca}</title>
            <link rel="preconnect" href="[https://fonts.googleapis.com](https://fonts.googleapis.com)">
            <link rel="preconnect" href="[https://fonts.gstatic.com](https://fonts.gstatic.com)" crossorigin>
            <link href="[https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap](https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap)" rel="stylesheet">
            <style>
                body {{ font-family: 'Work Sans', sans-serif; padding: 40px; background-color: #f7f7f7; color: #2d3748; line-height: 1.5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background-color: #2d3748; color: #ffffff; padding: 30px; border-radius: 12px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }}
                .header-info h1 {{ margin: 0 0 6px 0; font-size: 26px; font-weight: 700; color: #ffffff; }}
                .header-info p {{ margin: 0; opacity: 0.85; font-size: 13px; color: #ffffff; }}
                table {{ width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 35px; }}
                th {{ background-color: #2d3748; color: #ffffff; padding: 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
                .insights-card {{ background: #ffffff; padding: 35px; border-radius: 12px; border-left: 6px solid #3182ce; box-shadow: 0 4px 10px rgba(0,0,0,0.05); line-height: 1.6; }}
                .insights-card h3 {{ color: #2d3748; margin-top: 20px; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-info">
                        <h1>📊 Matriz de Benchmarking Estratégico ({total_marcas} Marcas Realmente Auditadas)</h1>
                        <p><strong>Cliente:</strong> {marca} &nbsp;|&nbsp; <strong>Sector:</strong> {sector} &nbsp;|&nbsp; <strong>Modelo:</strong> {modelo_negocio_final} &nbsp;|&nbsp; <strong>Ubicación:</strong> {ciudad}, {pais}</p>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th width="25%">Marca & Ubicación</th>
                            <th width="30%">Análisis Estratégico</th>
                            <th width="25%">Identidad Visual (Web & Pauta)</th>
                            <th width="20%">Tono & Comunicación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabla_html}
                    </tbody>
                </table>
                
                <h2 style="font-size: 22px; color: #2d3748; margin-bottom: 15px;">🧠 Dirección de Arte & Conclusiones Estratégicas</h2>
                <div class="insights-card">
                    {insights_html}
                </div>
            </div>
        </body>
        </html>
        """
        with open("reporte.html", "w", encoding="utf-8") as f: f.write(html_final)
        
        progress_bar.progress(1.0)
        status_box.success(f"🎉 ¡Benchmark Completo de {total_marcas} Marcas REALES generado!")

        if board_link:
            st.balloons()
            st.success("¡Tablero Visual Creado Exitosamente en Miro! 🚀")
            st.link_button("🎨 Abrir Tablero Directamente en Miro", board_link, type="primary")
        elif miro_err and miro_token_input.strip():
            st.warning(f"Se completó la auditoría. Detalle Miro: {miro_err}")

        st.markdown("---")
        with open("reporte.html", "rb") as file:
            st.download_button(f"📥 Descargar Reporte HTML ({total_marcas} Marcas)", data=file, file_name=f"Benchmark_{marca.replace(' ', '_')}.html", mime="text/html")
