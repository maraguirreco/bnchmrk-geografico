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

st.set_page_config(page_title="Velove | Local Benchmark AI", page_icon="📍", layout="wide")

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
except Exception:
    st.error("Falta la credencial de OpenRouter en .streamlit/secrets.toml")
    st.stop()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

def parsear_json_llm(texto):
    match = re.search(r'\[.*\]', texto, re.DOTALL)
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

# === 🕸️ BÚSQUEDA WEB BLINDADA ===
def buscar_urls_reales(query, max_results=12, categoria_etiqueta=""):
    urls_validas = []
    bad_domains = ["facebook", "instagram", "linkedin", "youtube", "tiktok", "twitter", "pinterest", "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas", "linguee", "wordreference", "translate", "foursquare"]
    for _ in range(2):
        try:
            time.sleep(1)
            results = list(DDGS().text(query, max_results=20))
            if results:
                for r in results:
                    url = r.get("href", "").lower()
                    title = r.get("title", "").split("-")[0].split("|")[0].strip()
                    if not url or any(bad in url for bad in bad_domains): continue
                    
                    item = {"nombre": title, "url": r.get("href", "")}
                    if categoria_etiqueta: 
                        item["categoria"] = categoria_etiqueta
                        
                    urls_validas.append(item)
                    if len(urls_validas) >= max_results: break
                if urls_validas: break
        except Exception: time.sleep(1)
    return urls_validas

# Funciones de imagen (Pillow / Playwright)
def buscar_pauta_o_grafico(nombre_brand, sector):
    try:
        time.sleep(0.5)
        results = list(DDGS().images(f"{nombre_brand} {sector} publicidad", max_results=1))
        if results and results[0].get("image"):
            resp = requests.get(results[0]["image"], timeout=4)
            if resp.status_code == 200:
                return f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode('utf-8')}"
    except Exception: pass
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
            return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
    except Exception: return ""

def extraer_colores_css(page):
    try:
        js_script = "() => { const colors = new Set(); const theme = document.querySelector('meta[name=\"theme-color\"]'); if (theme && theme.content) colors.add(theme.content); document.querySelectorAll('header, nav, button, a.btn, .button, h1, .primary, .bg-primary').forEach(el => { const style = window.getComputedStyle(el); if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') colors.add(style.backgroundColor); if (style.color && style.color !== 'rgba(0, 0, 0, 0)') colors.add(style.color); }); return Array.from(colors); }"
        raw_colors = page.evaluate(js_script)
        hex_colors = []
        for c in raw_colors:
            if 'rgb' in c:
                nums = [int(n) for n in re.findall(r'\d+', c)[:3]]
                if len(nums) == 3 and 50 <= sum(nums) <= 700:
                    if not (abs(nums[0]-nums[1]) < 10 and abs(nums[1]-nums[2]) < 10):
                        hx = '#{:02x}{:02x}{:02x}'.format(*nums)
                        if hx not in hex_colors: hex_colors.append(hx)
            elif c.startswith('#') and len(c) in [4, 7] and c not in hex_colors:
                hex_colors.append(c)
            if len(hex_colors) >= 5: break
        return hex_colors
    except Exception: return []

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
                r, g, b = palette[index*3], palette[index*3+1], palette[index*3+2]
                if (r > 235 and g > 235 and b > 235) or (r < 25 and g < 25 and b < 25): continue
                if abs(r - g) < 15 and abs(g - b) < 15 and abs(r - b) < 15: continue
                hx = f"#{r:02x}{g:02x}{b:02x}"
                if hx not in hex_colors: hex_colors.append(hx)
                if len(hex_colors) >= num_colores: break
            return hex_colors
    except Exception: return []

# === 🎨 INTERFAZ ===
col_logo, col_title = st.columns([1, 4])
with col_logo: st.image(LOGO_URL, width=150)
with col_title:
    st.title("Radar Local & Benchmarking AI")
    st.markdown("Genera matrices de benchmarking priorizando negocios por cercanía.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Odontología Sonrisa")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Clínica Odontológica")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. Colombia, México")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región:", placeholder="Ej. Cali, CDMX")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Ortodoncia invisible y diseño de sonrisa", height=68)
    
    st.markdown("---")
    
    # 📍 SECCIÓN HIPER-LOCAL SIN MAPS
    st.subheader("📍 Búsqueda de Proximidad (Opcional)")
    usar_proximidad = st.toggle("Activar búsqueda hiper-local (Ideal para priorizar negocios de tu misma zona)", value=False)
    
    direccion_exacta = ""
    if usar_proximidad:
        direccion_exacta = st.text_input("Dirección base, barrio o punto de referencia:", placeholder="Ej. Parque de los Perros, San Fernando")
        st.info(f"Le pediremos a la IA que busque competidores directamente cerca de esta ubicación.")

    st.markdown("---")
    st.subheader("💼 Detalles adicionales")
    col3, col4 = st.columns(2)
    with col3:
        modelo_negocio_opt = st.selectbox("Modelo de Negocio:", ["Local Físico / Retail", "General", "B2B", "B2C", "Otro"])
    with col4:
        competidores_fijos = st.text_input("🎯 Competidores locales conocidos (Opcional - separados por coma):")

if st.button("🔥 Ejecutar Benchmark Estratégico", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos principales.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info("🔍 Fase 1/3: Rastreando líderes de mercado en la web...")
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        
        # 1. EJECUTAR BÚSQUEDA DE PROXIMIDAD (Si está activo)
        proximidad_web = []
        if usar_proximidad and direccion_exacta:
            status_box.warning(f"📍 Rastreando la zona de {direccion_exacta}...")
            # Simulamos proximidad en DuckDuckGo
            query_local = f"mejores empresas agencias locales {sector_corto} cerca de {direccion_exacta} {ciudad} {pais}"
            proximidad_web = buscar_urls_reales(query_local, max_results=6, categoria_etiqueta="Local (Proximidad)")
            
        # 2. EJECUTAR WEB TRADICIONAL
        locales_web = buscar_urls_reales(f"mejores agencias empresas {sector_corto} {ciudad} {pais}", max_results=8)
        nacionales_web = buscar_urls_reales(f"top empresas líderes {sector_corto} {pais}", max_results=8)
        insp_web = buscar_urls_reales(f"{sector_corto} {producto_corto} branding identity design (site:awwwards.com OR site:thedieline.com)", max_results=5)
        
        fijos_lista = [{"nombre": c.strip(), "url": f"https://www.google.com/search?q={c.strip()}"} for c in competidores_fijos.split(",") if c.strip()]
        
        # Unimos todo, priorizando los de proximidad si existen
        todos_los_hallazgos = fijos_lista + proximidad_web + locales_web + nacionales_web + insp_web
        hallazgos_unicos = []
        urls_vistas = set()
        for item in todos_los_hallazgos:
            domain = urlparse(item["url"]).netloc.replace("www.", "")
            if domain and domain not in urls_vistas:
                urls_vistas.add(domain)
                hallazgos_unicos.append(item)

        competidores = []
        if len(hallazgos_unicos) >= 3:
            status_box.info("🧠 Evaluando marcas y filtrando los mejores...")
            
            punto_focal = f"Punto focal cercano a: {direccion_exacta}" if (usar_proximidad and direccion_exacta) else "Sin punto focal."
            
            prompt = f"""
            Actúa como Senior Market Research Analyst.
            MARCA: {marca} | SECTOR: {sector} | UBICACIÓN: {ciudad}, {pais} ({punto_focal})
            BASE DE URLs: {json.dumps(hallazgos_unicos)}
            
            1. SELECCIONA marcas reales de {sector}. Si hay empresas marcadas como "Local (Proximidad)", dales muchísima prioridad para tu análisis.
            2. Descarta diccionarios o redes sociales.
            3. Devuelve 15 competidores estructurados (Locales, Nacionales y de Inspiración).
            
            Devuelve ÚNICAMENTE JSON:
            [
                {{
                    "nombre": "Nombre", "url": "URL Exacta", "categoria": "Local / Nacional / Inspiración",
                    "ubicacion": "Barrio/Ciudad, País", "colores_estimados": ["#111111", "#ff0000"],
                    "justificacion": "Por qué es relevante y si está cerca", "servicios": "Servicios",
                    "propuesta_valor": "Propuesta", "diferencial": "Diferencial", "comunicacion": "Tono"
                }}
            ]
            """
            try:
                res = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt}], temperature=0.1)
                competidores = parsear_json_llm(res.choices[0].message.content or "")
                
                # Sincronizamos las URLs de la IA con nuestras URLs reales para evitar alucinaciones
                for comp in competidores:
                    domain_ia = urlparse(comp.get("url", "")).netloc.replace("www.", "")
                    match = next((h for h in hallazgos_unicos if urlparse(h["url"]).netloc.replace("www.", "") == domain_ia), None)
                    if match: comp["url"] = match["url"]
            except Exception: pass

        # === PROTOCOLO DE RESCATE ===
        if len(competidores) < 3:
            status_box.warning("⚡ Generando desde Memoria Neuronal (Fallback)...")
            res = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt.replace("BASE DE URLs:", "IGNORA ESTO, USA TU MEMORIA:")}], temperature=0.2)
            competidores = parsear_json_llm(res.choices[0].message.content or "")

        total_marcas = len(competidores)
        if total_marcas == 0:
            st.error("No se pudieron generar competidores. Intenta cambiar los términos de búsqueda.")
            st.stop()
            
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        
        status_box.info(f"📸 Fase 2/3: Capturando {total_marcas} webs y paletas...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                url_comp = comp.get("url", "")
                nombre_limpio = re.sub(r'\W+', '', comp.get("nombre", f"M_{index}")).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                colores_finales, img_base64 = [], ""
                
                if url_comp and "google.com" not in url_comp and url_comp.startswith("http"):
                    try:
                        page.goto(url_comp, timeout=8000, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        colores_css = extraer_colores_css(page)
                        page.screenshot(path=screenshot_path, full_page=False, type="jpeg", quality=60)
                        colores_finales = list(dict.fromkeys(colores_css + extraer_colores_de_imagen(screenshot_path)))
                        img_base64 = comprimir_y_convertir_base64(screenshot_path)
                    except Exception: pass
                
                if len(colores_finales) < 2: colores_finales = comp.get("colores_estimados", ["#001c19", "#ff1d4e"])
                domain = urlparse(url_comp).netloc
                
                resultados_analisis.append({
                    **comp, "colores": colores_finales[:4], "img_b64": img_base64, 
                    "pauta_b64": buscar_pauta_o_grafico(comp.get("nombre", ""), sector_corto),
                    "logo_url": f"https://www.google.com/s2/favicons?domain={domain}&sz=128" if domain and "google" not in domain else ""
                })
            browser.close()
            
        status_box.info("🧠 Fase 3/3: Generando Reporte Final...")
        progress_bar.progress(0.9)
        
        # Generar HTML Final y Descargable
        html_rows = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;"></div>' for c in r['colores']])
            logo = f'<img src="{r["logo_url"]}" style="width:28px; border-radius:4px;">' if r.get("logo_url") else ''
            img = f'<br><img src="{r["img_b64"]}" style="width:100%; max-width:240px; border-radius:6px; margin-top:5px;">' if r.get("img_b64") else ''
            html_rows += f'<tr><td style="padding:14px; border-bottom:1px solid #ddd;">{logo} <strong>{r.get("nombre", "")}</strong><br><small style="color:{COLOR_BOTON};">{r.get("categoria", "")}</small><br><small>{r.get("ubicacion", "")}</small></td><td style="padding:14px; border-bottom:1px solid #ddd; font-size:12px;"><strong>Dif:</strong> {r.get("diferencial", "")}</td><td style="padding:14px; border-bottom:1px solid #ddd; text-align:center;">{color_html}{img}</td><td style="padding:14px; border-bottom:1px solid #ddd; font-size:12px;">{r.get("comunicacion", "")}</td></tr>'

        html_final = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Benchmark Local: {marca}</title><style>body{{font-family:sans-serif; padding:40px; background:{COLOR_FONDO}; color:{COLOR_TEXTO};}} table{{width:100%; background:#fff; border-collapse:collapse; border-radius:8px; overflow:hidden;}} th{{background:{COLOR_TEXTO}; color:#fff; padding:12px; text-align:left;}}</style></head><body><h1>📍 Local Benchmark: {marca}</h1><table><thead><tr><th>Marca & Origen</th><th>Estrategia</th><th>Visuales</th><th>Tono</th></tr></thead><tbody>{html_rows}</tbody></table></body></html>'
        
        with open("reporte_local.html", "w", encoding="utf-8") as f: f.write(html_final)
        
        progress_bar.progress(1.0)
        status_box.success("🎉 ¡Benchmark Local completado exitosamente!")
        
        with open("reporte_local.html", "rb") as file:
            st.download_button("📥 Descargar Reporte Local HTML", data=file, file_name=f"Benchmark_Local_{marca.replace(' ', '_')}.html", mime="text/html")
