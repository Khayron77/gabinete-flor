import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import pandas as pd
import urllib.parse 
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gabinete De Flor", page_icon="🌸", layout="wide") 
TIEMPO_MARGEN = 15 
NUMERO_FLOR = "543425282667" 

# --- FUNCIÓN PARA CARGAR LOGO.PNG COMO FONDO ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def aplicar_diseño_visual():
    bin_str = get_base64_of_bin_file('logo.png')
    fondo_img = f'url("data:image/png;base64,{bin_str}");' if bin_str else 'none;'
    
    fondo_css = f"""
    <style>
    /* Fondo con transparencia para el logo */
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), 
                          {fondo_img}
        background-attachment: fixed;
        background-size: contain;
        background-position: center;
        background-repeat: no-repeat;
    }}
    
    /* Etiquetas y títulos en Borgoña para legibilidad */
    label, .stMarkdown p, h3, h2, [data-testid="stWidgetLabel"] p {{
        color: #800020 !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }}

    /* Selectores y campos de texto con fondo blanco sólido y borde borgoña */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    input {{
        background-color: white !important;
        border: 2px solid #800020 !important;
        color: #333 !important;
        border-radius: 8px !important;
    }}

    /* Estilo de las pestañas superiores */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background-color: rgba(255, 255, 255, 0.6);
        padding: 10px;
        border-radius: 15px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        background-color: #fff5f7;
        border-radius: 10px;
        border: 1px solid #fbcfe8;
        color: #800020;
        font-weight: bold;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #fbcfe8 !important;
        border: 2px solid #d4af37 !important;
    }}
    </style>
    """
    st.markdown(fondo_css, unsafe_allow_html=True)

# --- BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect('salon_belleza.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS servicios 
                 (id INTEGER PRIMARY KEY, nombre TEXT, duracion_minutos INTEGER, permite_paralelo INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS turnos 
                 (id INTEGER PRIMARY KEY, cliente_nombre TEXT, cliente_telefono TEXT, 
                  servicio_id INTEGER, fecha TEXT, hora TEXT)''')
    
    servicios_salon = [
        ('Corte', 30, 0), ('Corte + lavado + peinado', 60, 0), ('Tintura', 120, 1),
        ('Reflejos (4hs)', 240, 0), ('Tratamientos capilares', 60, 1), ('Alisado', 120, 0),
        ('Semipermanente', 60, 1), ('Esculpido', 120, 0), ('Spa de pies + semi', 120, 0),
        ('Permanente de pestañas', 60, 0), ('Peinado (planchado)', 30, 0), ('Peinado de fiesta', 60, 0)
    ]
    c.execute("DELETE FROM servicios") 
    c.executemany("INSERT INTO servicios (nombre, duracion_minutos, permite_paralelo) VALUES (?,?,?)", servicios_salon)
    conn.commit()
    conn.close()

# --- LÓGICA DE HORARIOS ---
def obtener_horarios_disponibles(fecha_sel, duracion_nueva, permite_paralelo_nuevo):
    formato = "%H:%M"
    inicio_jornada = datetime.strptime("09:00", formato)
    fin_jornada = datetime.strptime("20:00", formato)
    ahora = datetime.now()
    es_hoy = str(fecha_sel) == ahora.strftime("%Y-%m-%d")
    
    horarios_posibles = []
    actual = inicio_jornada
    while actual + timedelta(minutes=duracion_nueva) <= fin_jornada:
        if es_hoy:
            if actual.time() > (ahora + timedelta(minutes=30)).time():
                horarios_posibles.append(actual.strftime(formato))
        else:
            horarios_posibles.append(actual.strftime(formato))
        actual += timedelta(minutes=30)
        
    conn = sqlite3.connect('salon_belleza.db')
    c = conn.cursor()
    c.execute("""SELECT turnos.hora, servicios.duracion_minutos, servicios.permite_paralelo 
                 FROM turnos JOIN servicios ON turnos.servicio_id = servicios.id 
                 WHERE turnos.fecha = ?""", (str(fecha_sel),))
    ocupados = c.fetchall()
    conn.close()
    
    libres = []
    for h_pos in horarios_posibles:
        h_pos_dt = datetime.strptime(h_pos, formato)
        fin_pos_dt = h_pos_dt + timedelta(minutes=duracion_nueva + TIEMPO_MARGEN)
        clientes_en_rango = 0
        conflicto_exclusivo = False
        for h_ocu, dur_ocu, p_paralelo in ocupados:
            h_ocu_dt = datetime.strptime(h_ocu, formato)
            fin_ocu_dt = h_ocu_dt + timedelta(minutes=dur_ocu + TIEMPO_MARGEN)
            if not (fin_pos_dt <= h_ocu_dt or h_pos_dt >= fin_ocu_dt):
                clientes_en_rango += 1
                if p_paralelo == 0 or permite_paralelo_nuevo == 0:
                    conflicto_exclusivo = True
                    break
        if not conflicto_exclusivo and clientes_en_rango < 2:
            libres.append(h_pos)
    return libres

# --- ENCABEZADO COMÚN ---
def mostrar_encabezado():
    st.markdown(f"""
        <div style='text-align: center; padding-bottom: 10px;'>
            <h1 style='color: #800020; margin-bottom: 0px;'>🌸 Gabinete De Flor 🌸</h1>
            <p style='margin-bottom: 5px;'><a href='https://www.instagram.com/gabinete_de_flor/' target='_blank' style='text-decoration: none; color: #E1306C; font-weight: bold;'>📸 @gabinete_de_flor</a></p>
            <p><a href='https://wa.me/{NUMERO_FLOR}' target='_blank' style='text-decoration: none; color: #25D366; font-weight: bold;'>📞 WhatsApp: 342 528 2667</a></p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

# --- EJECUCIÓN PRINCIPAL ---
inicializar_db()
aplicar_diseño_visual()

tab_reserva, tab_cancelar, tab_admin = st.tabs(["📅 Reservar Turno", "❌ Cancelar Turno", "🔐 Panel Flor"])

with tab_reserva:
    mostrar_encabezado()
    st.subheader("Solicitá tu turno online")
    
    conn = sqlite3.connect('salon_belleza.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, duracion_minutos, permite_paralelo FROM servicios")
    res_servicios = cursor.fetchall()
    conn.close()
    
    serv_dict = {s[1]: (s[0], s[2], s[3]) for s in res_servicios}
    servicio_sel = st.selectbox("¿Qué servicio necesitás?", list(serv_dict.keys()), key="res_srv")
    fecha_sel = st.date_input("Día:", min_value=datetime.now().date(), key="res_fec")
    
    id_s, dur_s, p_paralelo_s = serv_dict[servicio_sel]
    libres = obtener_horarios_disponibles(fecha_sel, dur_s, p_paralelo_s)

    if libres:
        hora_sel = st.selectbox("Horarios disponibles:", options=libres, key="res_hor")
        nombre = st.text_input("Tu Nombre:", key="res_nom")
        tel = st.text_input("Tu WhatsApp (sin 0 ni 15):", key="res_tel") 

        if st.button("Confirmar Reserva", key="btn_confirmar"):
            if nombre and tel:
                conn = sqlite3.connect('salon_belleza.db')
                c = conn.cursor()
                c.execute("INSERT INTO turnos (cliente_nombre, cliente_telefono, servicio_id, fecha, hora) VALUES (?,?,?,?,?)",
                          (nombre, tel, id_s, str(fecha_sel), hora_sel))
                conn.commit()
                conn.close()
                
                # Éxito
                st.success(f"¡Hecho! Turno reservado para {nombre}.")
                
                # AVISO IMPORTANTE EN NEGRO Y NEGRITA
                st.markdown("""
                    <div style='background-color: rgba(255, 255, 255, 0.9); padding: 10px; border-radius: 5px; border: 1px solid #000; margin: 10px 0;'>
                        <p style='color: black; font-weight: bold; font-size: 18px; text-align: center; margin: 0;'>
                            AVISO IMPORTANTE: En caso de necesitar cancelar su turno, por favor hágalo con una antelación de 12 a 24 horas.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón WhatsApp
                texto_wa = urllib.parse.quote(f"¡Hola Flor! Soy {nombre}. Acabo de reservar un turno para {servicio_sel} el {fecha_sel} a las {hora_sel}.")
                st.markdown(f'<a href="https://wa.me/{NUMERO_FLOR}?text={texto_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366; color:white; padding:15px; border-radius:10px; font-weight:bold; text-align:center;">💬 ENVIAR WHATSAPP A FLOR</div></a>', unsafe_allow_html=True)
                st.balloons()
            else:
                st.warning("Completá tus datos.")

with tab_cancelar:
    mostrar_encabezado()
    st.subheader("Gestión de Turnos")
    c_tel = st.text_input("Ingresá tu WhatsApp para buscar:", key="canc_tel")
    if c_tel:
        conn = sqlite3.connect('salon_belleza.db')
        query = "SELECT turnos.id, turnos.fecha, turnos.hora, servicios.nombre FROM turnos JOIN servicios ON turnos.servicio_id = servicios.id WHERE turnos.cliente_telefono = ?"
        proximos = pd.read_sql_query(query, conn, params=(c_tel,))
        conn.close()
        
        if not proximos.empty:
            for _, row in proximos.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"📅 {row['fecha']} - {row['hora']} | {row['nombre']}")
                if col2.button("Eliminar", key=f"del_{row['id']}"):
                    conn = sqlite3.connect('salon_belleza.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM turnos WHERE id = ?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()
        else:
            st.write("No hay turnos registrados con ese número.")

with tab_admin:
    st.markdown("<h2 style='text-align: center; color: #800020;'>📊 Gestión de Gabinete</h2>", unsafe_allow_html=True)
    password = st.text_input("Contraseña de Flor:", type="password", key="adm_pass")
    if password == "salon2026":
        fecha_inicio = st.date_input("Ver agenda desde:", value=datetime.now().date(), key="adm_fec")
        st.divider()
        cols = st.columns(7)
        conn = sqlite3.connect('salon_belleza.db')
        for i in range(7):
            dia_actual = fecha_inicio + timedelta(days=i)
            fecha_str = str(dia_actual)
            dias_esp = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mié", "Thursday": "Jue", "Friday": "Vie", "Saturday": "Sáb", "Sunday": "Dom"}
            nombre_dia = dias_esp[dia_actual.strftime('%A')]
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:#f8f9fa; border-radius:8px; padding:5px; margin-bottom:10px; color:#111; border:1px solid #800020;'><b>{nombre_dia}</b><br>{dia_actual.strftime('%d/%m')}</div>", unsafe_allow_html=True)
                query = "SELECT turnos.id, turnos.hora, turnos.cliente_nombre, servicios.nombre as s_nom, turnos.cliente_telefono FROM turnos JOIN servicios ON turnos.servicio_id = servicios.id WHERE turnos.fecha = ? ORDER BY turnos.hora ASC"
                turnos_dia = pd.read_sql_query(query, conn, params=(fecha_str,))
                for _, row in turnos_dia.iterrows():
                    tel_cliente = "".join(filter(str.isdigit, row['cliente_telefono']))
                    if not tel_cliente.startswith("54"): tel_cliente = "54" + tel_cliente
                    msg_confirm = urllib.parse.quote(f"Hola {row['cliente_nombre']}, te confirmo tu turno para {row['s_nom']} el {dia_actual.strftime('%d/%m')} a las {row['hora']} en Gabinete De Flor.")
                    
                    st.markdown(f"""
                        <div style="background-color:white; padding:8px; border-radius:8px; border-left:5px solid #800020; margin-top:10px; border-top:1px solid #ddd; border-right:1px solid #ddd; border-bottom:1px solid #ddd;">
                            <p style="margin:0; font-size:13px; font-weight:bold; color:#111;">👤 {row['cliente_nombre']}</p>
                            <p style="margin:0; font-size:11px; color:#800020;"><b>🕒 {row['hora']}</b></p>
                            <p style="margin:0; font-size:10px; color:#555;">✂️ {row['s_nom']}</p>
                            <hr style="margin:5px 0; opacity:0.1;">
                            <a href="https://wa.me/{tel_cliente}?text={msg_confirm}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366; color:white; text-align:center; padding:4px; border-radius:4px; font-size:10px; font-weight:bold;">Confirmar WA</div>
                            </a>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("❌", key=f"adm_del_{row['id']}", use_container_width=True):
                        c = conn.cursor()
                        c.execute("DELETE FROM turnos WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()
        conn.close()
        