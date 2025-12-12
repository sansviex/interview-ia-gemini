import streamlit as st
import google.generativeai as genai
import os
import tempfile
import json
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN DE PÁGINA (Solo una vez) ---
st.set_page_config(page_title="Interview-Me Pro", page_icon="📊")

st.title("📊 Interview-Me: Análisis Profesional")
st.markdown("Sube tu perfil, recibe una pregunta y **mide tus habilidades**.")

# 1. Configuración de API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("Falta la API Key de Google. Configúrala en .env o Secrets.")
        st.stop()

genai.configure(api_key=api_key)

# --- CARGA DEL MODELO (Con Caché para ahorrar recursos) ---
# Usamos el 1.5-flash porque es el más estable para cuentas gratuitas
@st.cache_resource
def load_model():
    return genai.GenerativeModel('models/gemini-flash-latest')

model = load_model()

# 2. Input del Usuario
col1, col2 = st.columns(2)
with col1:
    job_role = st.text_input("Rol al que aplicas", "Data Scientist Junior")
with col2:
    experience = st.selectbox("Nivel de experiencia", ["Sin experiencia", "Junior", "Mid", "Senior"])

# --- FUNCIÓN SEGURA PARA GENERAR PREGUNTA ---
def generar_pregunta_segura(rol, exp):
    prompt = f"Actúa como un reclutador experto. Genera una sola pregunta de entrevista difícil pero justa para un puesto de {rol} nivel {exp}. Solo dame la pregunta, sin saludos."
    try:
        response = model.generate_content(prompt)
        return response.text
    except ResourceExhausted:
        return "⚠️ Error: Cuota excedida. Por favor espera 1 minuto."
    except Exception as e:
        return f"Error al generar pregunta: {e}"

# Botón Generar Pregunta
if st.button("Generar Pregunta"):
    with st.spinner("Creando pregunta..."):
        st.session_state['question'] = generar_pregunta_segura(job_role, experience)

# --- FUNCIÓN DE ANÁLISIS (Con Caché) ---
@st.cache_data(show_spinner=False)
def analyze_audio(audio_bytes, question_text):
    # Guardar audio temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        myfile = genai.upload_file(tmp_path)

        prompt_analisis = f"""
        Escucha el audio. Es una respuesta a: "{question_text}".
        
        Analiza al candidato y devuelve la respuesta ÚNICAMENTE en formato JSON válido. 
        Usa esta estructura exacta:
        {{
            "transcripcion": "Texto exacto de lo que dijo el usuario",
            "feedback_corto": "Un consejo de 2 lineas para mejorar",
            "scores": {{
                "Tecnicismo": (Valor del 1 al 10),
                "Claridad": (Valor del 1 al 10),
                "Seguridad": (Valor del 1 al 10),
                "Vocabulario": (Valor del 1 al 10),
                "Empatía": (Valor del 1 al 10)
            }}
        }}
        NO añadas texto antes ni después del JSON.
        """

        result = model.generate_content([prompt_analisis, myfile])
        text_limpio = result.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_limpio)

    except ResourceExhausted:
        return {"error": "quota", "feedback_corto": "Cuota excedida. Espera un momento."}
    except Exception as e:
        return {"error": "other", "feedback_corto": f"Error: {str(e)}"}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# Mostrar pregunta y grabar respuesta
if 'question' in st.session_state:
    st.info(f"🧑‍💼 **Entrevistador:** {st.session_state['question']}")
    
    st.markdown("---")
    st.write("🔴 **Graba tu respuesta:**")

    audio_value = st.audio_input("Presiona el micrófono para responder")

    if audio_value:
        with st.spinner("Analizando métricas de voz y contenido..."):
            data = analyze_audio(audio_value.getvalue(), st.session_state['question'])
            
            if "error" in data:
                st.error(f"Error: {data['feedback_corto']}")
            else:
                st.success("✅ Análisis Completado")
                st.write(f"**🗣️ Transcripción:** _{data['transcripcion']}_")
                st.info(f"💡 **Consejo:** {data['feedback_corto']}")
                
                # Gráfico
                st.markdown("### 🕸️ Tus Métricas")
                categories = list(data["scores"].keys())
                values = list(data["scores"].values())
                
                df = pd.DataFrame(dict(r=values, theta=categories))
                fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,10], title="Evaluación de Habilidades")
                fig.update_traces(fill='toself', line_color='#00CC96')
                
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                if st.button("🔄 Nueva Entrevista"):
                    st.session_state.clear()
                    st.rerun()