# 1. INSTALACIÓN DE LIBRERÍAS DE ÉLITE
!pip install fpdf requests

import requests
import base64
import json
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE TUS CREDENCIALES HOTMART (LA LLAVE MAESTRA) ---
# Ve a Hotmart Developers > Credenciales para obtener esto
CLIENT_ID = "PON_AQUI_TU_CLIENT_ID"
CLIENT_SECRET = "PON_AQUI_TU_CLIENT_SECRET"
BASIC_TOKEN = "PON_AQUI_TU_BASIC_TOKEN"  # (Base64 de ID:Secret si ya lo tienes, si no el script intenta generarlo)

# --- PARTE 1: GENERADOR AUTOMÁTICO DE ACTIVOS (EL PDF PARA VENDER) ---
def generar_ebook_elite():
    print(">>> Iniciando Protocolo de Generación de Activo Digital...")
    
    pdf = FPDF()
    pdf.add_page()
    
    # Portada
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(200, 20, txt="ARQUITECTURA DE SUPREMACÍA IA", ln=1, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(200, 10, txt="Guía Estratégica 2026 - Generado por Agente Autónomo", ln=1, align='C')
    
    # Contenido de Valor (La "Carne")
    pdf.ln(20)
    pdf.set_font("Arial", size=12)
    contenido = [
        "1. La Era Agéntica: Dejar de operar y empezar a orquestar.",
        "2. El Stack Tecnológico: NVIDIA Blackwell y Google Gemini.",
        "3. Automatización de Ingresos: Cómo usar Python para vender.",
        "4. El Futuro: Agentes que se pagan a sí mismos.",
        "",
        "Este documento es un activo digital generado automáticamente.",
        f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d')}"
    ]
    
    for linea in contenido:
        pdf.cell(200, 10, txt=linea, ln=1, align='L')
        
    nombre_archivo = "Supremacia_IA_Elite_2026.pdf"
    pdf.output(nombre_archivo)
    print(f">>> ¡ÉXITO! Documento '{nombre_archivo}' generado. Descárgalo de la carpeta de archivos a la izquierda.")
    return nombre_archivo

# --- PARTE 2: CONEXIÓN A LA BÓVEDA (API HOTMART) ---
def conectar_hotmart():
    print("\n>>> Estableciendo enlace seguro con Hotmart...")
    
    auth_url = "https://api-sec-vlc.hotmart.com/security/oauth/token"
    
    # Si no tienes el token Basic listo, intentamos crearlo (ID:Secret en base64)
    if "PON_AQUI" in BASIC_TOKEN:
        credenciales = f"{CLIENT_ID}:{CLIENT_SECRET}"
        token_b64 = base64.b64encode(credenciales.encode()).decode()
        header_auth = f"Basic {token_b64}"
    else:
        header_auth = f"Basic {BASIC_TOKEN}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": header_auth
    }
    
    # Solicitud de acceso
    try:
        response = requests.post(auth_url, params={"grant_type": "client_credentials"}, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data['access_token']
            print(">>> CONEXIÓN ESTABLECIDA: Acceso de Élite concedido.")
            print(f">>> Token Temporal: {access_token[:10]}... (Oculto por seguridad)")
            return access_token
        else:
            print(f"!!! ERROR DE CONEXIÓN: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"!!! ERROR CRÍTICO: {e}")
        return None

# --- EJECUCIÓN DEL PROTOCOLO ---
# 1. Crear el producto
generar_ebook_elite()

# 2. Probar la conexión (Solo funcionará si pones tus credenciales reales arriba)
if "PON_AQUI" not in CLIENT_ID:
    token = conectar_hotmart()
else:
    print("\n[ALERTA] Para conectar con Hotmart, debes reemplazar 'PON_AQUI_TU_CLIENT_ID' con tus datos reales.")
