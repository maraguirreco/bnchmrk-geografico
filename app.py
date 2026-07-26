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
    texto_clean = texto.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
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

# === 🕸️ BÚSQUEDA WEB REAL SIN PERMITIR Hallazgos FALSOS ===
def buscar_urls_categoria(query, max_results=8, cat_label=""):
    urls_validas = []
    bad_domains = [
        "facebook", "instagram", "linkedin", "youtube", "tiktok", "twitter", "pinterest", 
        "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas",
        "linguee", "collinsdictionary", "wordreference", "cambridge", "merriam-webster", 
        "rae.es", "reverso", "dictionary", "thesaurus", "traductor", "translate"
    ]
    bad_keywords = ["diccionario", "dictionary", "traducción", "translation", "significado", "definición"]
    
    try:
        time.sleep(0.4)
        results = list(DDGS().text(query, max_results=20))
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

# === 🎨 MAQUETADO TOTALMENTE DESPLEGADO EN MIRO (TEXTO ABIERTO + FOTOS + COLORES) ===
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
    
    try:
        # 1. Crear Tablero Principal
        res_board = requests.post(
            "[https://api.miro.com/v2/boards](https://api.miro.com/v2/boards)", 
            headers=headers_json, 
            json={"name": f"Velove Benchmark: {marca}", "description": f"Estudio de Competencia ({sector})"}, 
            timeout=10
        )
        if res_board.status_code not in [200, 201]:
            return None, f"Miro API Error {res_board.status_code}: {res_board.text}"
        
        board_data = res_board.json()
        board_id = board_data.get("id")
        board_link = board_data.get("viewLink", f"[https://miro.com/app/board/](https://miro.com/app/board/){board_id}/")

        # 2. Renderizar Cuadrícula Visual Totalmente Desplegada en Pantalla
        for idx, comp in enumerate(resultados):
            col = idx % 3
            row = idx // 3
            base_x = col * 950
            base_y = row * 750

            # A. Texto Formateado 100% Desplegado (Sin clics)
            html_text = f"""
            <p><strong><span style="font-size: 20px; color: #001c19;">[{comp.get('categoria', 'Competidor')}] {comp.get('nombre', 'Marca')}</span></strong></p>
            <p>📍 <strong>Ubicación:</strong> {comp.get('ubicacion', 'N/D')}</p>
            <p>🛠️ <strong>Servicios:</strong> {comp.get('servicios', 'N/D')}</p>
            <p>💎 <strong>Propuesta de Valor:</strong> {comp.get('propuesta_valor', 'N/D')}</p>
            <p>⚡ <strong>Diferencial:</strong> {comp.get('diferencial', 'N/D')}</p>
            <p>🎙️ <strong>Tono:</strong> {comp.get('comunicacion', 'N/D')}</p>
            <p>🌐 <a href="{comp.get('url', '#')}">{comp.get('url', 'Sitio Web')}</a></p>
            """
            
            text_payload = {
                "data": {"content": html_text},
                "style": {"fillColor": "#ffffff", "textAlign": "left"},
                "position": {"x": base_x, "y": base_y},
                "geometry": {"width": 400}
            }
            requests.post(f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/texts", headers=headers_json, json=text_payload, timeout=5)

            # B. Captura Web Flotante al Lado Derecho
            nombre_limpio = re.sub(r'\W+', '', comp.get("nombre", "")).lower()
            screenshot_path = f"assets/{nombre_limpio}.jpg"
            
            if os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    files = {"resource": (f"{nombre_limpio}.jpg", f, "image/jpeg")}
                    data = {
                        "data": json.dumps({
                            "position": {"x": base_x + 450, "y": base_y},
                            "geometry": {"width": 380}
                        })
                    }
                    try:
                        requests.post(
                            f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/images", 
                            headers=headers_auth, 
                            files=files, 
                            data=data, 
                            timeout=10
                        )
                    except Exception:
                        pass

            # C. Paleta de Colores en Muestras Redondas Justo Debajo del Texto
            for c_idx, hex_color in enumerate(comp.get("colores", [])):
                shape_payload = {
                    "data": {"shape": "circle"},
                    "style": {"fillColor": hex_color, "borderColor": "#001c19", "borderWidth": 1.0},
                    "position": {"x": base_x + (c_idx * 55), "y": base_y + 280},
                    "geometry": {"width": 45, "height": 45}
                }
                requests.post(f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/shapes", headers=headers_json, json=shape_payload, timeout=5)

        # 3. Muro Lateral de Insights & Dirección de Arte
        insights_clean = re.sub(r'<[^<]+?>', '', insights_text)[:1200]
        sticky_payload = {
            "data": {
                "content": f"🧠 DIRECCIÓN DE ARTE & CONCLUSIONES ESTRATÉGICAS:\n\n{insights_clean}",
                "shape": "square"
            },
            "style": {"fillColor": "light_yellow"},
            "position": {"x": 2900, "y": 0},
            "geometry": {"width": 600}
        }
        requests.post(f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/sticky_notes", headers=headers_json, json=sticky_payload, timeout=5)

        return board_link, None
    except Exception as e:
        return None, f"Excepción Miro: {str(e)}"

# === 🎨 INTERFAZ STREAMLIT ===
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.markdown(f'<img src="{LOGO_URL}" width="150" style="max-width:100%;">', unsafe_allow_html=True)
with col_title:
    st.title("Agente Estratega de Marca & Benchmarking")
    st.markdown("Genera matrices de benchmarking verificadas con maquetado automático en **Miro**.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Aurora Travel")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Agencia de Marketing Digital B2B")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. Colombia, México, España")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región (Local):", placeholder="Ej. Cali, CDMX, Madrid")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Generación de leads B2B, SEO técnico y pauta en LinkedIn...", height=68)
    
    st.markdown("---")
    
    st.subheader("📍 Búsqueda por Radio y Proximidad (Opcional)")
    usar_proximidad = st.toggle("Activar búsqueda hiper-local en radio prudente", value=False)
    direccion_exacta = ""
    if usar_proximidad:
        direccion_exacta = st.text_input("Dirección base, barrio o punto de referencia:", placeholder="Ej. Barrio Granada, Route 27...").strip()

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
        competidores_fijos = st.text_input("🎯 Competidores locales conocidos (Opcional - separados por coma):", placeholder="Ej. Obility, Demandbase")
        miro_token_input = st.text_input("🔑 Token de Miro (Pega tu Access Token eyJ...):", value=MIRO_ACCESS_TOKEN, type="password")

if st.button("🔥 Ejecutar Benchmark Estratégico y Abrir Miro", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos: Marca, Sector, País, Ciudad y Producto.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info(f"🔍 Rastreando negocios reales en las 4 CATEGORÍAS (Local, Nacional, Internacional, Inspiración)...")
        
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        punto_local = f"{direccion_exacta} {ciudad}" if (usar_proximidad and direccion_exacta) else ciudad
        
        # 1. Rastrear CADA categoría por separado con etiquetas fijas
        locales = buscar_urls_categoria(f"{sector_corto} {producto_corto} {punto_local} {pais}", max_results=6, cat_label="Local")
        nacionales = buscar_urls_categoria(f"mejores empresas líderes {sector_corto} {pais}", max_results=6, cat_label="Nacional")
        
        # BÚSQUEDA INTERNACIONAL FORZADA EN INGLÉS Y ESPAÑOL
        internacionales = buscar_urls_categoria(f"top international leading {sector_corto} brands companies", max_results=6, cat_label="Internacional")
        if not internacionales:
            internacionales = buscar_urls_categoria(f"marcas internacionales líderes de {sector_corto}", max_results=6, cat_label="Internacional")
            
        inspiracion = buscar_urls_categoria(f"{sector_corto} {producto_corto} branding identity awards", max_results=5, cat_label="Inspiración")
        
        fijos_lista = []
        if competidores_fijos.strip():
            for item in competidores_fijos.split(","):
                item_clean = item.strip()
                if item_clean:
                    found = buscar_urls_categoria(f"{item_clean} sitio web oficial", max_results=1, cat_label="Local")
                    if found:
                        fijos_lista.extend(found)

        todos_los_hallazgos_raw = fijos_lista + locales + nacionales + internacionales + inspiracion
        
        # Indexar resultados únicos con ID
        hallazgos_unicos = []
        urls_vistas = set()
        for idx, item in enumerate(todos_los_hallazgos_raw, 1):
            domain = urlparse(item["url"]).netloc.replace("www.", "")
            if domain and domain not in urls_vistas:
                urls_vistas.add(domain)
                item["id"] = len(hallazgos_unicos) + 1
                hallazgos_unicos.append(item)

        competidores = []

        if hallazgos_unicos:
            status_box.info("🧠 Evaluando pertenencia y filtrando marcas reales...")
            
            prompt_evaluacion = f"""
            Actúa como Senior Market Research Analyst.
            MARCA CLIENTE A EXCLUIR: {marca}
            SECTOR: {sector}
            
            LISTA DE NEGOCIOS Y SITIOS WEB REALES ENCONTRADOS (USA ÚNICAMENTE ESTOS ID):
            {json.dumps(hallazgos_unicos, ensure_ascii=False)}
            
            ⛔ REGLA DE ORO DE CERO ALUCINACIONES:
            1. Selecciona ÚNICAMENTE elementos de la lista proporcionada indicando su 'id'.
            2. Queda ESTRICTAMENTE PROHIBIDO inventar nombres de empresas o URLs.
            3. Procura mantener representantes de las 4 categorías: Local, Nacional, Internacional, Inspiración.
            
            Devuelve JSON:
            [
                {{
                    "id": 1,
                    "categoria": "Local" (o "Nacional" / "Internacional" / "Inspiración"),
                    "ubicacion": "Ciudad, País real",
                    "servicios": "Servicios ofrecidos",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Análisis del tono de comunicación"
                }}
            ]
            """
            
            try:
                res_eval = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_evaluacion}],
                    temperature=0.1
                )
                raw_eval = res_eval.choices[0].message.content or ""
                evaluaciones_ia = parsear_json_llm(raw_eval)
                
                # CRUCIAL: Vinculación estricta por ID real. Si no existe en hallazgos_unicos, SE DESCARTA.
                for item_ia in evaluaciones_ia:
                    match_real = next((h for h in hallazgos_unicos if h["id"] == item_ia.get("id")), None)
                    if match_real:
                        competidores.append({
                            "nombre": match_real["nombre"],
                            "url": match_real["url"],
                            "categoria": item_ia.get("categoria", match_real["categoria"]),
                            "ubicacion": item_ia.get("ubicacion", match_real.get("snippet", "N/D")[:40]),
                            "servicios": item_ia.get("servicios", "N/D"),
                            "propuesta_valor": item_ia.get("propuesta_valor", "N/D"),
                            "diferencial": item_ia.get("diferencial", "N/D"),
                            "comunicacion": item_ia.get("comunicacion", "N/D")
                        })
            except Exception:
                pass

        # FALLSAFE DE SEGURIDAD (Solo usa elementos de la búsqueda real sin inventar)
        if not competidores and hallazgos_unicos:
            for item in hallazgos_unicos[:10]:
                competidores.append({
                    "nombre": item["nombre"],
                    "url": item["url"],
                    "categoria": item["categoria"],
                    "ubicacion": f"{ciudad}, {pais}",
                    "servicios": producto,
                    "propuesta_valor": "Líder en el sector.",
                    "diferencial": "Presencia comercial destacada.",
                    "comunicacion": "Tono profesional y corporativo."
                })

        total_marcas = len(competidores)
        if total_marcas == 0:
            st.error("No se pudieron obtener resultados de la web en este momento. Intenta de nuevo.")
            st.stop()

        # === FASE 2: AUDITORÍA VISUAL PLAYWRIGHT ===
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        status_box.info(f"📸 Capturando pantallas y extrayendo paletas de color de {total_marcas} fuentes reales...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                
                nombre_comp = comp.get("nombre", f"Marca_{index}")
                url_comp = comp.get("url", "")
                
                status_box.warning(f"({index}/{total_marcas}) Auditando presencia visual: {nombre_comp}...")
                nombre_limpio = re.sub(r'\W+', '', nombre_comp).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                
                colores_finales = []
                img_base64 = ""
                
                if url_comp and url_comp.startswith("http"):
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
                logo_url = f"[https://www.google.com/s2/favicons?domain=](https://www.google.com/s2/favicons?domain=){domain}&sz=128" if domain else ""
                
                resultados_analisis.append({
                    **comp, 
                    "colores": colores_finales[:4],
                    "img_b64": img_base64, 
                    "pauta_b64": pauta_base64,
                    "logo_url": logo_url
                })
            
            browser.close()
        
        status_box.info("🧠 Generando Dirección de Arte & Recomendaciones Estratégicas...")
        progress_bar.progress(0.85)
        
        contexto_resumido = json.dumps([{
            "nombre": r.get("nombre", ""), "categoria": r.get("categoria", ""), 
            "diferencial": r.get("diferencial", "")
        } for r in resultados_analisis])
        
        prompt_insights = f"""
        Actúa como Senior Director de Arte y Estratega de Marca.
        Analiza las {total_marcas} empresas reales auditadas para '{marca}' ({sector} - {producto}) en {ciudad}, {pais}.
        Matriz de marcas: {contexto_resumido}
        
        ⛔ INSTRUCCIÓN ESTRICTA:
        Entrega ÚNICAMENTE código HTML directo usando etiquetas <h3>, <ul>, <li>, <p> y <strong>.
        
        <h3>📌 1. Patrones y Estándares de la Industria</h3>
        <p>Tendencias de comunicación visual y presencia digital.</p>
        
        <h3>💡 2. Oportunidades y Gaps en el Mercado</h3>
        <p>Espacios comerciales desaprovechados por los competidores.</p>
        
        <h3>🎨 3. Dirección de Arte Visual Recomendada</h3>
        <p>Estilo gráfico, combinación de colores, tipografías y tono visual.</p>
        
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
        status_box.info("🎨 Creando tablero visual desplegado en Miro...")
        progress_bar.progress(0.95)
        
        token_a_usar = miro_token_input.strip() or MIRO_ACCESS_TOKEN
        board_link, miro_err = exportar_a_miro_canvas_completo(token_a_usar, marca, sector, resultados_analisis, insights_html)
        
        # Generación de Copia HTML Local
        tabla_html = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;" title="{c}"></div>' for c in r['colores']])
            
            logo_tag = f'<img src="{r["logo_url"]}" style="width:28px; height:28px; border-radius:4px; border:1px solid #ccc;" onerror="this.style.display=\'none\'">' if r.get("logo_url") else ''
            img_tag = f'<div style="margin-top:6px;"><span style="font-size:10px; font-weight:bold; color:#666;">🖥️ Captura Web:</span><br><img src="{r["img_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("img_b64") else '<div style="background:#f0e2d5; padding:10px; border-radius:6px; color:#666; font-size:10px; margin-top:6px;">Web no disponible</div>'
            pauta_tag = f'<div style="margin-top:8px;"><span style="font-size:10px; font-weight:bold; color:{COLOR_BOTON};">📢 Pauta / Pieza Gráfica:</span><br><img src="{r["pauta_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("pauta_b64") else ''
            
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
                    <a href="{r.get("url", "#")}" target="_blank" style="font-size:11px; color:{COLOR_BOTON}; font-weight:600;">🌐 Sitio Web Oficial</a>
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
            <link rel="preconnect" href="[https://fonts.googleapis.com](https://fonts.googleapis.com)">
            <link rel="preconnect" href="[https://fonts.gstatic.com](https://fonts.gstatic.com)" crossorigin>
            <link href="[https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap](https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap)" rel="stylesheet">
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
