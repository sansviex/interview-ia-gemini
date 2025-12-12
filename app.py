import streamlit as st
import google.generativeai as genai
import os
import tempfile
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(page_title="Interview-Me con Gemini", page_icon="🤖")

st.title("🤖 Interview-Me: Simulador con Gemini")
st.markdown("Sube tu perfil, recibe una pregunta y **responde con tu voz**.")

# 1. Configuración de API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("Falta la API Key de Google. Configúrala en .env o Secrets.")
        st.stop()

genai.configure(api_key=api_key)

# Usamos el modelo nuevo que confirmaste que funciona
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

    # Input de audio
    audio_value = st.audio_input("Presiona el micrófono para responder")

    if audio_value:
        st.audio(audio_value)
        
        with st.spinner("Gemini está escuchando y analizando..."):
            try:
                # Guardamos el audio temporalmente
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_value.getvalue())
                    tmp_path = tmp_file.name

                # Subimos el archivo a la API de Google
                myfile = genai.upload_file(tmp_path)

                # Prompt multimodal
                prompt_analisis = f"""
                Escucha el audio adjunto. Es la respuesta de un candidato a la pregunta: "{st.session_state['question']}".
                
                Realiza las siguientes tareas:
                1. Transcribe exactamente lo que dijo el candidato.
                2. Evalúa la respuesta (del 1 al 10).
                3. Dime si sonó seguro o nervioso.
                4. Dame un consejo breve para mejorar.
                """

                # Generamos el análisis
                result = model.generate_content([prompt_analisis, myfile])
                
                # Mostramos el resultado
                st.markdown("### 📝 Análisis de Gemini")
                st.write(result.text)

                # Limpieza archivo temporal
                os.remove(tmp_path)
                
                # --- NUEVA SECCIÓN: BOTÓN DE REINICIAR ---
                st.markdown("---")
                if st.button("🔄 Reiniciar Entrevista (Nueva Pregunta)"):
                    # Borramos la memoria de la sesión
                    st.session_state.clear()
                    # Recargamos la página
                    st.rerun()

            except Exception as e:
                st.error(f"Ocurrió un error: {e}")