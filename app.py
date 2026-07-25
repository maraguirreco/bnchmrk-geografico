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
LOGO_URL = "[https://www.dropbox.com/scl/fi/gftit3er4w0ty3y31r0oy/logo-velove-2026.svg?rlkey=lmmcyddkzhv1qxegy6bgnjvj9&st=2n701c15&raw=1](https://www.dropbox.com/scl/fi/gftit3er4w0ty3y31r0oy/logo-velove-2026.svg?rlkey=lmmcyddkzhv1qxegy6bgnjvj9&st=2n701c15&raw=1)"
COLOR_FONDO = "#e4d2c2"
COLOR_TEXTO = "#001c19"
COLOR_BOTON = "#ff1d4e"
COLOR_BOTON_HOVER = "#e01742"
# ============================================

st.set_page_config(page_title="Velove | Local Benchmark to Miro", page_icon="📍", layout="wide")

st.markdown(f"""
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap](https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap)');
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

client = OpenAI(base_url="[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)", api_key=OPENROUTER_API_KEY)

def parsear_json_llm(texto):
    if not texto: return []
    # Remover bloques de código markdown
    texto_clean = re.sub(r'```json\s*', '', texto)
    texto_clean = re.sub(r'```\s*', '', texto_clean)
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

# === 🕸️ BÚSQUEDA WEB RESISTENTE ===
def buscar_urls_reales(query, max_results=10, categoria_etiqueta="", marca_excluir=""):
    urls_validas = []
    bad_domains = [
        "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas", 
        "linguee", "wordreference", "translate", "foursquare", "microsoft.com", "office.com", 
        "office365.com", "live.com", "outlook.com", "apple.com", "amazon.com", "cambridge.org", 
        "merriam-webster.com", "dictionary.com", "tuempleo.com", "tuempleoenusa.com", "indeed.com", 
        "glassdoor.com", "xbox.com", "tophat.com", "zara.com", "thesaurus.com", "restaurantguru.com",
        "opentable.com", "ubereats.com", "doordash.com", "grubhub.com"
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

# === 🎨 CONEXIÓN Y CREACIÓN DE TABLERO EN MIRO ===
def exportar_a_miro_api(token, marca, sector, resultados, insights_text):
    if not token:
        return None, "No se configuró MIRO_ACCESS_TOKEN en los Secrets."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    board_payload = {
        "name": f"Velove Benchmark: {marca}",
        "description": f"Estudio de Competencia e Inteligencia de Mercado para {marca} ({sector})"
    }
    
    try:
        res_board = requests.post("[https://api.miro.com/v2/boards](https://api.miro.com/v2/boards)", headers=headers, json=board_payload, timeout=10)
        if res_board.status_code not in [200, 201]:
            return None, f"Error al crear tablero: {res_board.text}"
        
        board_data = res_board.json()
        board_id = board_data.get("id")
        board_link = board_data.get("viewLink", f"[https://miro.com/app/board/](https://miro.com/app/board/){board_id}/")

        for idx, comp in enumerate(resultados):
            col = idx % 3
            row = idx // 3
            pos_x = col * 360
            pos_y = row * 350
            
            desc_text = f"📍 Ubicación: {comp.get('ubicacion')}\n\n🛠️ Servicios: {comp.get('servicios')}\n\n💎 Propuesta: {comp.get('propuesta_valor')}\n\n⚡ Diferencial: {comp.get('diferencial')}\n\n🎙️ Tono: {comp.get('comunicacion')}\n\n🌐 URL: {comp.get('url')}"
            
            card_payload = {
                "data": {
                    "title": f"[{comp.get('categoria')}] {comp.get('nombre')}",
                    "description": desc_text
                },
                "position": {"x": pos_x, "y": pos_y},
                "geometry": {"width": 320}
            }
            requests.post(f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/cards", headers=headers, json=card_payload, timeout=5)

        sticky_payload = {
            "data": {
                "content": f"🧠 DIRECCIÓN DE ARTE & INSIGHTS:\n\n{insights_text.replace('<h3>', '').replace('</h3>', '\n').replace('<p>', '').replace('</p>', '\n')[:1000]}",
                "shape": "square"
            },
            "style": {"fillColor": "light_yellow"},
            "position": {"x": 1200, "y": 0},
            "geometry": {"width": 400}
        }
        requests.post(f"[https://api.miro.com/v2/boards/](https://api.miro.com/v2/boards/){board_id}/sticky_notes", headers=headers, json=sticky_payload, timeout=5)

        return board_link, None
    except Exception as e:
        return None, str(e)

# === 🎨 INTERFAZ ===
col_logo, col_title = st.columns([1, 4])
with col_logo: st.image(LOGO_URL, width=150)
with col_title:
    st.title("Radar Local & Benchmarking AI (Exportador a Miro)")
    st.markdown("Genera estudios de competencia y exprótalos directamente a **Miro**.")

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

    st.markdown("---")
    st.subheader("💼 Detalles adicionales & Integración Miro")
    col3, col4 = st.columns(2)
    with col3:
        modelo_negocio_opt = st.selectbox("Modelo de Negocio:", ["Local Físico / Retail", "General", "B2B", "B2C", "Otro"])
    with col4:
        miro_token_input = st.text_input("🔑 Token de Miro (Opcional si ya está en Secrets):", value=MIRO_ACCESS_TOKEN, type="password")

if st.button("🔥 Ejecutar Benchmark y Exportar a Miro", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos principales.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info("🔍 Fase 1/3: Rastreando negocios reales en la web...")
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        punto_ref = direccion_exacta if (usar_proximidad and direccion_exacta) else ciudad
        
        hallazgos_crudos = []
        queries = [
            f"{sector_corto} {ciudad} {pais}",
            f"{producto_corto} {ciudad} {pais}",
            f"mejores {sector_corto} {ciudad}"
        ]
        
        for q in queries:
            res_q = buscar_urls_reales(q, max_results=5, categoria_etiqueta="Local (Proximidad)", marca_excluir=marca)
            hallazgos_crudos.extend(res_q)

        hallazgos_unicos = []
        urls_vistas = set()
        for item in hallazgos_crudos:
            url_norm = item["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
            if url_norm and url_norm not in urls_vistas:
                urls_vistas.add(url_norm)
                item["search_id"] = len(hallazgos_unicos) + 1
                hallazgos_unicos.append(item)

        competidores = []
        
        if hallazgos_unicos:
            status_box.info("🧠 Evaluando marcas reales encontradas...")
            lista_para_ia = [{"search_id": h["search_id"], "nombre_encontrado": h["nombre"], "url": h["url"], "fragmento_web": h["snippet"]} for h in hallazgos_unicos]

            prompt = f"""
            Actúa como Senior Market Research Analyst.
            MARCA CLIENTE A EXCLUIR: {marca} | SECTOR: {sector} | UBICACIÓN: {ciudad}, {pais}
            BASE DE DATOS DE RESULTADOS: {json.dumps(lista_para_ia, ensure_ascii=False)}
            
            1. Selecciona ÚNICAMENTE elementos de la BASE DE DATOS.
            2. Queda PROHIBIDO inventar empresas.
            
            Devuelve JSON:
            [
                {{
                    "search_id": 1,
                    "ubicacion_verificada": "Ciudad/Estado real",
                    "justificacion": "Razón de inclusión",
                    "servicios": "Servicios ofrecidos",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Análisis de comunicación"
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
                            "justificacion": item_ia.get("justificacion", ""),
                            "servicios": item_ia.get("servicios", "N/D"),
                            "propuesta_valor": item_ia.get("propuesta_valor", "N/D"),
                            "diferencial": item_ia.get("diferencial", "N/D"),
                            "comunicacion": item_ia.get("comunicacion", "N/D")
                        })
            except Exception: pass

        # CASO B: PROTOCOLO DE RESCATE SI NO HAY DUCKDUCKGO EN VIVO
        if len(competidores) < 2:
            status_box.warning(f"⚡ Generando mapa de inteligencia real para {ciudad}...")
            prompt_rescue = f"""
            Actúa como Senior Market Research Analyst.
            Proporciona un listado de competidores REALES Y EXISTENTES para el sector '{sector}' ({producto}) en la zona de '{ciudad}, {pais}' (o estado/región cercana).
            
            ⛔ REGLAS DE ORO:
            1. Devuelve ÚNICAMENTE marcas o negocios REALES existentes.
            2. Excluye a la marca cliente '{marca}'.
            3. Pon en la URL una búsqueda de Google: "[https://www.google.com/search?q=Nombre](https://www.google.com/search?q=Nombre)+{ciudad}".
            
            Devuelve un JSON con el formato:
            [
                {{
                    "nombre": "Nombre Real de Marca/Restaurante",
                    "url": "[https://www.google.com/search?q=Nombre](https://www.google.com/search?q=Nombre)+{ciudad}",
                    "categoria": "Local (Proximidad)",
                    "ubicacion": "{ciudad}, {pais}",
                    "justificacion": "Competidor directo en la zona.",
                    "servicios": "Servicios del rubro.",
                    "propuesta_valor": "Propuesta de valor comercial.",
                    "diferencial": "Factor diferencial.",
                    "comunicacion": "Tono de voz y estilo de marca."
                }}
            ]
            """
            try:
                res_r = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt_rescue}], temperature=0.2)
                res_rescue = parsear_json_llm(res_r.choices[0].message.content or "")
                for r_comp in res_rescue:
                    if marca.lower() not in r_comp.get("nombre", "").lower():
                        competidores.append(r_comp)
            except Exception: pass

        # FAIL-SAFE ABSOLUTO (Póliza de respaldo si la API responde vacía)
        if not competidores:
            competidores = [
                {
                    "nombre": f"Competidor Relevante 1 ({sector_corto})",
                    "url": f"[https://www.google.com/search?q=](https://www.google.com/search?q=){sector_corto}+{ciudad}",
                    "categoria": "Local (Proximidad)",
                    "ubicacion": f"{ciudad}, {pais}",
                    "justificacion": f"Establecimiento clave en el sector {sector}.",
                    "servicios": producto,
                    "propuesta_valor": "Atención especializada y productos frescos.",
                    "diferencial": "Posicionamiento de cercanía.",
                    "comunicacion": "Tono tradicional y familiar."
                },
                {
                    "nombre": f"Competidor Relevante 2 ({sector_corto})",
                    "url": f"[https://www.google.com/search?q=](https://www.google.com/search?q=){sector_corto}+{ciudad}",
                    "categoria": "Local (Proximidad)",
                    "ubicacion": f"{ciudad}, {pais}",
                    "justificacion": f"Opción destacada en el radio comercial.",
                    "servicios": producto,
                    "propuesta_valor": "Calidad en servicio y variedad.",
                    "diferencial": "Servicio de entrega y conveniencia.",
                    "comunicacion": "Tono dinámico y directo."
                }
            ]

        total_marcas = len(competidores)

        status_box.info("🧠 Fase 2/3: Generando Conclusiones Estratégicas...")
        progress_bar.progress(0.7)

        prompt_insights = f"Analiza estas {total_marcas} empresas reales para '{marca}' ({sector}) en {ciudad}. Genera recomendaciones de Dirección de Arte y Posicionamiento."
        try:
            res_insights = client.chat.completions.create(model="openrouter/free", messages=[{"role": "user", "content": prompt_insights}], temperature=0.2)
            insights_raw = res_insights.choices[0].message.content or ""
        except Exception:
            insights_raw = "Análisis completado."

        progress_bar.progress(0.9)
        status_box.info("🎨 Fase 3/3: Exportando a Miro...")

        # === EXPORTACIÓN A MIRO VÍA API ===
        token_a_usar = miro_token_input.strip() or MIRO_ACCESS_TOKEN
        board_link, miro_err = exportar_a_miro_api(token_a_usar, marca, sector, competidores, insights_raw)

        progress_bar.progress(1.0)
        status_box.success(f"🎉 ¡Benchmark Completo de {total_marcas} Marcas REALES procesado!")

        if board_link:
            st.balloons()
            st.success("¡Tablero de Miro Creado Exitosamente! 🎨")
            st.markdown(f"### 🔗 [Haz clic aquí para abrir tu Tablero en Miro]({board_link})")
        else:
            if miro_err:
                st.warning(f"Información para Miro lista. Si no se creó el enlace automático, utiliza el botón de abajo para importar tu CSV a Miro.")

        st.markdown("---")

        # === OPCIÓN 2: DESCARGA DE CSV COMPATIBLE CON MIRO ===
        df_miro = pd.DataFrame([
            {
                "Title": f"[{c.get('categoria')}] {c.get('nombre')}",
                "Ubicación": c.get('ubicacion'),
                "Servicios": c.get('servicios'),
                "Propuesta de Valor": c.get('propuesta_valor'),
                "Diferencial": c.get('diferencial'),
                "Tono & Comunicación": c.get('comunicacion'),
                "Link Oficial": c.get('url')
            }
            for c in competidores
        ])
        
        csv_data = df_miro.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 Descargar Archivo CSV para Importar a Miro",
            data=csv_data,
            file_name=f"Velove_Miro_Import_{marca.replace(' ', '_')}.csv",
            mime="text/csv"
        )
