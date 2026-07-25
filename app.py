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

# === 🕸️ BÚSQUEDA WEB RESISTENTE ===
def buscar_urls_reales(query, max_results=10, categoria_etiqueta="", marca_excluir=""):
    urls_validas = []
    bad_domains = [
        "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas", 
        "linguee", "wordreference", "translate", "foursquare", "microsoft.com", "office.com", 
        "office365.com", "live.com", "outlook.com", "apple.com", "amazon.com", "cambridge.org", 
        "merriam-webster.com", "dictionary.com", "tuempleo.com", "tuempleoenusa.com", "indeed.com", 
        "glassdoor.com", "xbox.com", "tophat.com", "zara.com", "thesaurus.com"
    ]
    
    excluir_clean = marca_excluir.strip().lower() if marca_excluir else ""
    
    try:
        time.sleep(0.3)
        results = list(DDGS().text(query, max_results=15))
        if results:
            for r in results:
                url = r.get("href", "").lower()
                title = r.get("title", "").split("-")[0].split("|")[0].strip()
                snippet = r.get("body", "")
                title_clean = title.lower()
                
                if not url or any(bad in url for bad in bad_domains): continue
                if excluir_clean and (excluir_clean in title_clean or excluir_clean in url): continue
                
                if "facebook.com" in url or "instagram.com" in url:
                    parsed_path = urlparse(url).path.strip("/")
                    if not parsed_path or parsed_path in ["search", "explore", "reels", "p", "stories"]:
                        continue
                
                item = {
                    "nombre": title, 
                    "url": r.get("href", ""),
                    "snippet": snippet,
                    "categoria": categoria_etiqueta or "Local"
                }
                urls_validas.append(item)
                if len(urls_validas) >= max_results: break
    except Exception:
        pass
    return urls_validas

def buscar_pauta_o_grafico(nombre_brand, sector):
    try:
        results = list(DDGS().images(f"{nombre_brand} {sector} publicidad", max_results=1))
        if results and results[0].get("image"):
            img_url = results[0]["image"]
            resp = requests.get(img_url, timeout=2.5)
            if resp.status_code == 200:
                return f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode('utf-8')}"
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
            img.save(buffered, format="JPEG", quality=60)
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
    st.markdown("Genera matrices de benchmarking con datos reales e inteligencia de mercado local.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Calima Bakery")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Panadería y Restaurante Colombiano")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. USA, Colombia, México")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región:", placeholder="Ej. Edison NJ, Cali, CDMX")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Pandebonos, arepas, empanadas y comida típica", height=68)
    
    st.markdown("---")
    
    st.subheader("📍 Búsqueda por Radio y Proximidad (Opcional)")
    usar_proximidad = st.toggle("Activar búsqueda hiper-local en radio prudente", value=False)
    
    direccion_exacta = ""
    if usar_proximidad:
        direccion_exacta = st.text_input("Dirección base, barrio o punto de referencia:", placeholder="Ej. Route 27, Edison NJ")
        st.info(f"Rastrearemos competidores en {ciudad} y radio cercano.")

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
        
        status_box.info("🔍 Fase 1/3: Rastreando negocios reales en la web...")
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        punto_ref = direccion_exacta if (usar_proximidad and direccion_exacta) else ciudad
        
        # BÚSQUEDAS WEB FLEXIBLES
        hallazgos_crudos = []
        
        queries = [
            f"{sector_corto} {ciudad} {pais}",
            f"{producto_corto} {ciudad} {pais}",
            f"mejores {sector_corto} {ciudad}"
        ]
        
        for q in queries:
            res_q = buscar_urls_reales(q, max_results=6, categoria_etiqueta="Local (Proximidad)", marca_excluir=marca)
            hallazgos_crudos.extend(res_q)

        # Competidores ingresados manualmente por el usuario
        if competidores_fijos.strip():
            for c in competidores_fijos.split(","):
                c_clean = c.strip()
                if c_clean:
                    res_fijo = buscar_urls_reales(f"{c_clean} {ciudad}", max_results=1, categoria_etiqueta="Local")
                    if res_fijo:
                        hallazgos_crudos.extend(res_fijo)
                    else:
                        hallazgos_crudos.append({
                            "nombre": c_clean,
                            "url": f"https://www.google.com/search?q={c_clean}",
                            "snippet": f"Negocio en {ciudad}",
                            "categoria": "Local"
                        })

        # Mapeo de hallazgos únicos
        hallazgos_unicos = []
        urls_vistas = set()
        for idx, item in enumerate(hallazgos_crudos, 1):
            url_norm = item["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
            if url_norm and url_norm not in urls_vistas:
                urls_vistas.add(url_norm)
                item["search_id"] = len(hallazgos_unicos) + 1
                hallazgos_unicos.append(item)

        competidores = []
        
        # CASO A: Se encontraron URLs en el rastreo web
        if hallazgos_unicos:
            status_box.info("🧠 Evaluando marcas reales encontradas...")
            lista_para_ia = [
                {
                    "search_id": h["search_id"],
                    "nombre_encontrado": h["nombre"],
                    "url": h["url"],
                    "fragmento_web": h["snippet"]
                }
                for h in hallazgos_unicos
            ]

            prompt = f"""
            Actúa como Senior Market Research Analyst.
            MARCA CLIENTE A EXCLUIR: {marca}
            SECTOR REQUERIDO: {sector}
            UBICACIÓN OBJETIVO: {ciudad}, {pais}
            
            BASE DE DATOS DE RESULTADOS ENCONTRADOS EN INTERNET:
            {json.dumps(lista_para_ia, ensure_ascii=False)}
            
            ⛔ REGLAS DE ORO:
            1. Selecciona ÚNICAMENTE elementos de la BASE DE DATOS DE RESULTADOS ENCONTRADOS.
            2. Queda PROHIBIDO inventar nombres de empresas o URLs.
            3. Devuelve el 'search_id' exacto para cada competidor seleccionado.
            
            Devuelve ÚNICAMENTE un arreglo JSON:
            [
                {{
                    "search_id": 1,
                    "ubicacion_verificada": "Ciudad/Estado real extraído del texto o sitio",
                    "justificacion": "Por qué es un competidor relevante dentro del sector",
                    "servicios": "Servicios o productos ofrecidos",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Análisis del tono de comunicación (2-3 oraciones)"
                }}
            ]
            """
            try:
                res = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt}], temperature=0.1)
                evaluacion_ia = parsear_json_llm(res.choices[0].message.content or "")
                
                for item_ia in evaluacion_ia:
                    sid = item_ia.get("search_id")
                    match_real = next((h for h in hallazgos_unicos if h["search_id"] == sid), None)
                    if match_real:
                        competidores.append({
                            "nombre": match_real["nombre"],
                            "url": match_real["url"],
                            "categoria": match_real["categoria"],
                            "ubicacion": item_ia.get("ubicacion_verificada", f"{ciudad}, {pais}"),
                            "colores_estimados": ["#001c19", "#ff1d4e"],
                            "justificacion": item_ia.get("justificacion", ""),
                            "servicios": item_ia.get("servicios", "N/D"),
                            "propuesta_valor": item_ia.get("propuesta_valor", "N/D"),
                            "diferencial": item_ia.get("diferencial", "N/D"),
                            "comunicacion": item_ia.get("comunicacion", "N/D")
                        })
            except Exception: pass

        # CASO B: Si DuckDuckGo fue bloqueado o devolvió < 2 resultados -> PROTOCOLO DE RESCATE POR CONOCIMIENTO REAL
        if len(competidores) < 2:
            status_box.warning(f"⚡ Conectando con Inteligencia de Mercado para identificar negocios REALES en {ciudad}...")
            prompt_rescue = f"""
            Actúa como Senior Market Research Analyst.
            Genera un estudio de competencia para la marca '{marca}' en el sector '{sector}' ({producto}) en {ciudad}, {pais}.
            
            ⛔ REGLAS DE RESCATE OBLIGATORIAS:
            1. Devuelve ÚNICAMENTE negocios, restaurantes o marcas REALES, EXISTENTES Y VERIFICABLES que operen en {ciudad}, {pais} o municipios cercanos en el estado/región.
            2. NO inventes nombres ficticios ni inventes páginas web falsas.
            3. Si un negocio no tiene web propia, pon en el campo 'url' la búsqueda oficial: "https://www.google.com/search?q=Nombre+del+negocio+{ciudad}".
            4. EXCLUYE a la propia marca cliente '{marca}'.
            
            Devuelve ÚNICAMENTE un arreglo JSON empezando por '[' y terminando por ']':
            [
                {{
                    "nombre": "Nombre Comercial Real Existente",
                    "url": "https://www.google.com/search?q=Nombre+Real+{ciudad}",
                    "categoria": "Local (Proximidad)",
                    "ubicacion": "Ciudad/Estado Real",
                    "colores_estimados": ["#001c19", "#ff1d4e"],
                    "justificacion": "Por qué es un competidor real en la zona",
                    "servicios": "Servicios principales",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Análisis del tono de comunicación (2-3 oraciones)"
                }}
            ]
            """
            try:
                res_r = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt_rescue}], temperature=0.2)
                res_rescue = parsear_json_llm(res_r.choices[0].message.content or "")
                for r_comp in res_rescue:
                    if marca.lower() not in r_comp.get("nombre", "").lower():
                        if not any(c.get("nombre", "").lower() == r_comp.get("nombre", "").lower() for c in competidores):
                            competidores.append(r_comp)
            except Exception: pass

        total_marcas = len(competidores)
        if total_marcas == 0:
            st.error("No se pudieron verificar competidores. Por favor intenta ajustar levemente el nombre del sector o la ciudad.")
            st.stop()
            
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        
        status_box.info(f"📸 Fase 2/3: Capturando {total_marcas} fuentes reales y paletas...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                url_comp = comp.get("url", "")
                nombre_comp = comp.get("nombre", f"M_{index}")
                nombre_limpio = re.sub(r'\W+', '', nombre_comp).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                colores_finales, img_base64 = [], ""
                
                status_box.warning(f"({index}/{total_marcas}) Auditando: {nombre_comp}...")
                
                if url_comp and "google.com" not in url_comp and url_comp.startswith("http"):
                    try:
                        page.goto(url_comp, timeout=6000, wait_until="commit")
                        time.sleep(1)
                        colores_css = extraer_colores_css(page)
                        page.screenshot(path=screenshot_path, full_page=False, type="jpeg", quality=50)
                        colores_finales = list(dict.fromkeys(colores_css + extraer_colores_de_imagen(screenshot_path)))
                        img_base64 = comprimir_y_convertir_base64(screenshot_path)
                    except Exception:
                        pass
                
                if len(colores_finales) < 2: 
                    colores_finales = comp.get("colores_estimados", ["#001c19", "#ff1d4e"])
                    
                domain = urlparse(url_comp).netloc
                
                if "instagram.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/174/174855.png"
                elif "facebook.com" in domain:
                    logo_url = "https://cdn-icons-png.flaticon.com/512/124/124010.png"
                elif domain and "google" not in domain:
                    logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                else:
                    logo_url = ""
                
                resultados_analisis.append({
                    **comp, 
                    "colores": colores_finales[:4], 
                    "img_b64": img_base64, 
                    "pauta_b64": buscar_pauta_o_grafico(nombre_comp, sector_corto),
                    "logo_url": logo_url
                })
            browser.close()
            
        status_box.info("🧠 Fase 3/3: Generando Dirección de Arte y Conclusiones Estratégicas...")
        progress_bar.progress(0.9)
        
        contexto_resumido = json.dumps([{
            "nombre": r.get("nombre", ""), "categoria": r.get("categoria", ""), 
            "diferencial": r.get("diferencial", ""), "ubicacion": r.get("ubicacion", "")
        } for r in resultados_analisis])
        
        prompt_insights = f"""
        Actúa como Senior Director de Arte y Estratega de Marca.
        Analiza las {total_marcas} empresas REALES auditadas para la marca '{marca}' ({sector} - {producto}) en {ciudad}, {pais}.
        Matriz de competidores analizados: {contexto_resumido}
        
        ⛔ INSTRUCCIÓN DE SALIDA ESTRICTA:
        Entrega ÚNICAMENTE código HTML directo usando exclusivamente las etiquetas <h3>, <ul>, <li>, <p> y <strong>.
        NO incluyas ninguna frase introductiva, markdown como ```html, meta-comentario ni texto fuera del HTML.
        
        <h3>📌 1. Patrones y Estándares del Sector Local</h3>
        <p>Análisis de tendencias de comunicación y presencia digital común en los negocios de {ciudad} y alrededores.</p>
        
        <h3>💡 2. Gaps y Oportunidades en la Zona</h3>
        <p>Espacios estratégicos no aprovechados por la competencia en el radio comercial.</p>
        
        <h3>🎨 3. Dirección de Arte Visual Recomendada</h3>
        <p>Pautas para estilo gráfico, colores y tipografía para destacar frente a los competidores de la zona.</p>
        
        <h3>🚀 4. Posicionamiento Estratégico y Tono de Voz</h3>
        <p>Estrategia de diferenciación comercial para liderar en la ciudad y su área de influencia.</p>
        """
        
        try:
            res_insights = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt_insights}], temperature=0.2)
            insights_raw = res_insights.choices[0].message.content or ""
            if "<h3>" in insights_raw:
                insights_html = insights_raw[insights_raw.find("<h3>"):].replace("```html", "").replace("```", "")
            else:
                insights_html = insights_raw
        except Exception:
            insights_html = "<p>No se pudieron generar los insights estratégicos.</p>"

        # === GENERACIÓN DE TABLA Y HTML FINAL COMPLETO ===
        tabla_html = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;" title="{c}"></div>' for c in r['colores']])
            logo_tag = f'<img src="{r["logo_url"]}" style="width:28px; height:28px; border-radius:4px; border:1px solid #ccc;" onerror="this.style.display=\'none\'">' if r.get("logo_url") else ''
            img_tag = f'<div style="margin-top:6px;"><span style="font-size:10px; font-weight:bold; color:#666;">🖥️ Captura / Presencia Digital:</span><br><img src="{r["img_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("img_b64") else '<div style="background:#f0e2d5; padding:10px; border-radius:6px; color:#666; font-size:10px; margin-top:6px;">Sin captura disponible</div>'
            pauta_tag = f'<div style="margin-top:8px;"><span style="font-size:10px; font-weight:bold; color:{COLOR_BOTON};">📢 Pauta / Pieza Gráfica:</span><br><img src="{r["pauta_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("pauta_b64") else ''
            
            url_display = r.get("url", "#")
            if "instagram.com" in url_display:
                link_text = "📸 Perfil de Instagram"
            elif "facebook.com" in url_display:
                link_text = "📘 Página de Facebook"
            else:
                link_text = "🌐 Sitio Web Oficial"
            
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
                    <a href="{url_display}" target="_blank" style="font-size:11px; color:{COLOR_BOTON}; font-weight:600; text-decoration:none;">{link_text}</a>
                    <p style="font-size:11px; color:#555; margin-top:6px; line-height:1.3;"><i>"{r.get("justificacion", "")}"</i></p>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.5;">
                    <p style="margin:0 0 6px 0;"><strong>🛠️ Servicios / Productos:</strong><br>{r.get("servicios", "N/D")}</p>
                    <p style="margin:0 0 6px 0;"><strong>💎 Propuesta de Valor:</strong><br>{r.get("propuesta_valor", "N/D")}</p>
                    <p style="margin:0;"><strong>⚡ Factor Diferencial:</strong><br>{r.get("diferencial", "N/D")}</p>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top; text-align:center;">
                    <div style="margin-bottom:6px;">{color_html}</div>
                    {img_tag}
                    {pauta_tag}
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.5;">
                    <p style="margin:0;"><strong>🎙️ Tono & Estilo Comunicativo:</strong><br>{r.get("comunicacion", "N/D")}</p>
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
                        <h1>📊 Matriz de Benchmarking Local ({total_marcas} Marcas Reales Verificadas)</h1>
                        <p><strong>Cliente:</strong> {marca} &nbsp;|&nbsp; <strong>Sector:</strong> {sector} &nbsp;|&nbsp; <strong>Punto Focal / Zona:</strong> {punto_ref}, {pais}</p>
                    </div>
                    <img src="{LOGO_URL}" class="logo-img" alt="Logo Velove">
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th width="25%">Marca & Presencia Digital</th>
                            <th width="30%">Análisis Estratégico</th>
                            <th width="25%">Identidad Visual (Web / Redes)</th>
                            <th width="20%">Tono & Comunicación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabla_html}
                    </tbody>
                </table>
                
                <h2 style="font-size: 22px; color: {COLOR_TEXTO}; margin-bottom: 15px;">🧠 Dirección de Arte & Conclusiones Estratégicas</h2>
                <div class="insights-card">
                    {insights_html}
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("reporte_local.html", "w", encoding="utf-8") as f: f.write(html_final)
        
        progress_bar.progress(1.0)
        status_box.success(f"🎉 ¡Benchmark Completo de {total_marcas} Marcas REALES verificado y generado!")
        
        with open("reporte_local.html", "rb") as file:
            st.download_button(f"📥 Descargar Reporte Velove ({total_marcas} Marcas)", data=file, file_name=f"Benchmark_Velove_{marca.replace(' ', '_')}.html", mime="text/html")
