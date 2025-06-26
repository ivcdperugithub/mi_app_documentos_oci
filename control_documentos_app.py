# control_documentos_app.py
import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
import streamlit as st  # type: ignore
import gspread  # type: ignore
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE SESIÓN ---
TIMEOUT = 20  # segundos
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.rol = None
    st.session_state.last_active = datetime.now()
    st.session_state.usuario_actual = None
    st.session_state.bloqueo = False

# --- LOGIN ---
usuarios = {
    "administrador": {"password": "admin123", "rol": "admin"},
    "usuario_01": {"password": "user123", "rol": "usuario"}
}

def login():
    st.title("🔐 Inicio de sesión")

    if st.session_state.bloqueo:
        st.error("Ya hay un usuario conectado. Intenta más tarde.")
        return

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        if usuario in usuarios and usuarios[usuario]["password"] == password:
            st.session_state.authenticated = True
            st.session_state.rol = usuarios[usuario]["rol"]
            st.session_state.last_active = datetime.now()
            st.session_state.usuario_actual = usuario
            st.session_state.bloqueo = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# --- DESCONECTAR POR INACTIVIDAD ---
def verificar_inactividad():
    if datetime.now() - st.session_state.last_active > timedelta(seconds=TIMEOUT):
        st.warning("Sesión cerrada por inactividad")
        st.session_state.bloqueo = False
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    else:
        st.session_state.last_active = datetime.now()

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_hoja():
    creds = None
    creds_file = os.path.join(os.path.dirname(__file__), "client_secret.json")
    token_file = os.path.join(os.path.dirname(__file__), "token.json")

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        creds = flow.run_console()
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    client = gspread.authorize(creds)
    return client.open("documentos_registrados")

def obtener_lista_personas1(sheet):
    datos = sheet.worksheet("Remitentes").get_all_values()[1:]  # omitimos encabezado
    return [f"{fila[0]}_{fila[1]}" for fila in datos]

def obtener_lista_personas2(sheet):
    datos = sheet.worksheet("Destinatarios").get_all_values()[1:]  # omitimos encabezado
    return [f"{fila[0]}_{fila[1]}" for fila in datos]

# --- FORMULARIO ---
def mostrar_formulario(sheet, tipo_doc):
    st.subheader(f"📄 Registro de {tipo_doc.upper()}")
    ws = sheet.worksheet(tipo_doc)
    personas1 = obtener_lista_personas1(sheet)
    personas2 = obtener_lista_personas2(sheet)
    nro = str(len(ws.get_all_values())).zfill(3)  # correlativo
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M")

    with st.form("formulario"):
        st.write(f"**Nro:** {nro}")
        st.write(f"**Fecha y Hora:** {fecha_hora}")
        remitente = st.selectbox("Remitente", personas1)
        destinatario = st.selectbox("Destinatario", personas2)
        asunto = st.text_area("Asunto")
        enviado = st.form_submit_button("Guardar")

    if enviado:
        ws.append_row([nro, fecha_hora, remitente, destinatario, asunto])
        st.success("Documento registrado correctamente ✅")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ingresar otro documento"):
                st.rerun()
        with col2:
            if st.button("Salir"):
                st.session_state.bloqueo = False
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        return

    st.markdown("---")
    st.subheader("📚 Documentos registrados")
    st.dataframe(ws.get_all_records())

# --- INTERFAZ PRINCIPAL ---
def main():
    verificar_inactividad()
    sheet = conectar_hoja()

    st.sidebar.title("Menú")
    opcion = st.sidebar.radio("Selecciona una opción", ["Oficios", "HojasInformativas"])

    if opcion == "Oficios":
        mostrar_formulario(sheet, "Oficios")
    elif opcion == "HojasInformativas":
        mostrar_formulario(sheet, "HojasInformativas")

    if st.session_state.rol == "admin":
        st.sidebar.success("Acceso: Administrador")
    else:
        st.sidebar.info("Acceso: Usuario")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.bloqueo = False
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- INICIO ---
if not st.session_state.authenticated:
    login()
else:
    main()
