import streamlit as st
import google.generativeai as genai
import os
import tempfile
import json
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
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

# Usamos el modelo Gemini 2.5 Flash
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. Input del Usuario
col1, col2 = st.columns(2)
with col1:
    job_role = st.text_input("Rol al que aplicas", "Data Scientist Junior")
with col2:
    experience = st.selectbox("Nivel de experiencia", ["Sin experiencia", "Junior", "Mid", "Senior"])

# 3. Generar Pregunta
if st.button("Generar Pregunta"):
    prompt_pregunta = f"Actúa como un reclutador experto. Genera una sola pregunta de entrevista difícil pero justa para un puesto de {job_role} nivel {experience}. Solo dame la pregunta, sin saludos."
    
    with st.spinner("Creando pregunta..."):
        response = model.generate_content(prompt_pregunta)
        st.session_state['question'] = response.text

# Mostrar pregunta y grabar respuesta
if 'question' in st.session_state:
    st.info(f"🧑‍💼 **Entrevistador:** {st.session_state['question']}")
    
    st.markdown("---")
    st.write("🔴 **Graba tu respuesta:**")

    audio_value = st.audio_input("Presiona el micrófono para responder")

    if audio_value:
        st.audio(audio_value)
        
        with st.spinner("Analizando métricas de voz y contenido..."):
            try:
                # Guardar audio temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_value.getvalue())
                    tmp_path = tmp_file.name

                myfile = genai.upload_file(tmp_path)

                # --- PROMPT AVANZADO PARA JSON ---
                # Le pedimos a la IA que no escriba texto libre, sino una estructura de datos estricta.
                prompt_analisis = f"""
                Escucha el audio. Es una respuesta a: "{st.session_state['question']}".
                
                Analiza al candidato y devuelve la respuesta ÚNICAMENTE en formato JSON válido. 
                Usa esta estructura exacta:
                {{
                    "transcripcion": "Texto exacto de lo que dijo el usuario",
                    "feedback_corto": "Un consejo de 2 lineas para mejorar",
                    "scores": {{
                        "Tecnicismo": (Valor del 1 al 10, basándote en el uso de términos correctos),
                        "Claridad": (Valor del 1 al 10, que tan bien se entiende la idea),
                        "Seguridad": (Valor del 1 al 10, basado en el tono de voz y titubeos),
                        "Vocabulario": (Valor del 1 al 10, riqueza de palabras),
                        "Empatía": (Valor del 1 al 10, conexión humana)
                    }}
                }}
                NO añadas texto antes ni después del JSON.
                """

                result = model.generate_content([prompt_analisis, myfile])
                
                # --- PROCESAMIENTO DE RESPUESTA ---
                # Limpiamos la respuesta por si Gemini pone ```json ... ```
                text_limpio = result.text.replace("```json", "").replace("```", "").strip()
                
                # Convertimos el texto a Diccionario de Python
                data = json.loads(text_limpio)
                
                # 1. Mostrar Feedback Escrito
                st.success("✅ Análisis Completado")
                st.write(f"**🗣️ Transcripción:** _{data['transcripcion']}_")
                st.info(f"💡 **Consejo:** {data['feedback_corto']}")
                
                # 2. CREAR GRÁFICO DE RADAR
                st.markdown("### 🕸️ Tus Métricas")
                
                # Preparamos los datos para Plotly
                categories = list(data["scores"].keys())
                values = list(data["scores"].values())
                
                # Creamos el DataFrame
                df = pd.DataFrame(dict(
                    r=values,
                    theta=categories
                ))
                
                # Generamos el gráfico
                fig = px.line_polar(df, r='r', theta='theta', line_close=True,
                                    range_r=[0,10], # Escala fija de 0 a 10
                                    title="Evaluación de Habilidades")
                
                # Personalizamos el color para que se vea "tech"
                fig.update_traces(fill='toself', line_color='#00CC96')
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                
                st.plotly_chart(fig, use_container_width=True)

                # Limpieza
                os.remove(tmp_path)
                
                # Botón de reinicio
                st.markdown("---")
                if st.button("🔄 Nueva Entrevista"):
                    st.session_state.clear()
                    st.rerun()

            except Exception as e:
                st.error(f"Error al procesar el análisis: {e}")
                # En caso de error, mostramos el texto crudo para depurar
                if 'result' in locals():
                    st.write("Respuesta cruda de la IA:", result.text)