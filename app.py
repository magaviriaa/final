"""
Streamlit – Versión Simple (2 funciones / 2 páginas)
---------------------------------------------------
Función A (Página 1): "Wake word" (palabra de atención) → enciende LED de ayuda.
Función B (Página 2): Señalar medicamento con servo a 45°/90°/135°.

Cómo correr:
  streamlit run app_simple.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st

# ==== Mini estilos (UI) ====
st.markdown(
    """
    <style>
      .card{background:#11151a;border:1px solid #1f2937;border-radius:16px;padding:18px;margin-bottom:14px}
      .title{font-size:1.2rem;font-weight:700;margin-bottom:6px}
      .muted{color:#9aa6b2;font-size:0.9rem}
      .status-dot{width:16px;height:16px;border-radius:50%;display:inline-block;margin-right:8px}
    </style>
    """,
    unsafe_allow_html=True
)

# === Micrófono / STT (usa el componente streamlit-mic-recorder) ===
# Instala antes:  pip install streamlit-mic-recorder
try:
    from streamlit_mic_recorder import speech_to_text, mic_recorder
    MIC_OK = True
except Exception:
    MIC_OK = False

# === MQTT opcional (para Wokwi/ESP32). Si no está instalado, se ignora y queda en modo simulado ===
# pip install paho-mqtt  (opcional)
MQTT_OK = False
try:
    import os
    import paho.mqtt.client as mqtt
    MQTT_OK = True
except Exception:
    MQTT_OK = False

BROKER = "broker.mqttdashboard.com"
TOPIC_LED = "migue/demo/led"       # cambia por algo único si quieres
TOPIC_SERVO = "migue/demo/servo"   # idem

def _mqtt_client():
    """Cliente MQTT singleton (si paho está disponible)."""
    if not MQTT_OK:
        return None
    if "_mqtt" not in st.session_state:
        c = mqtt.Client(client_id=f"streamlit-{os.getpid()}")
        try:
            c.connect(BROKER, 1883, 60)
            st.session_state._mqtt = c
        except Exception:
            st.session_state._mqtt = None
    return st.session_state._mqtt

# ==================== Datos simples ====================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
MEDS_FILE = DATA_DIR / "meds_simple.json"

DEFAULT_MEDS = [
    {"name": "Losartan 50mg", "angle": 45},
    {"name": "Metformina 500mg", "angle": 90},
    {"name": "Vitamina D 1000UI", "angle": 135},
]

if MEDS_FILE.exists():
    try:
        MEDS = json.loads(MEDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        MEDS = DEFAULT_MEDS
else:
    MEDS = DEFAULT_MEDS
    MEDS_FILE.write_text(json.dumps(MEDS, ensure_ascii=False, indent=2), encoding="utf-8")

# ==================== Puente de hardware (simulado + MQTT opcional) ====================
class HwBridge:
    """Reemplazar con implementación real (Serial/MQTT).
    Protocolo sugerido (JSON):
      LED:   {"type":"act","led":"on"|"off"}      -> aquí publicamos: topic TOPIC_LED  (on/off)
      Servo: {"type":"act","servo_angle": 0..180} -> aquí publicamos: topic TOPIC_SERVO (entero)
    """
    def __init__(self):
        self.led_state = "off"  # off|on
        self.servo_angle = 0
        self.last_med = None

    def set_led(self, state: str):
        self.led_state = state
        # MQTT opcional
        client = _mqtt_client()
        if client is not None:
            try:
                client.publish(TOPIC_LED, "on" if state == "on" else "off", qos=0, retain=False)
            except Exception:
                pass

    def point_servo(self, angle: int, med_name: str | None = None):
        self.servo_angle = int(angle)
        self.last_med = med_name
        # MQTT opcional
        client = _mqtt_client()
        if client is not None:
            try:
                client.publish(TOPIC_SERVO, str(int(angle)), qos=0, retain=False)
            except Exception:
                pass


if "hw" not in st.session_state:
    st.session_state.hw = HwBridge()
if "logs" not in st.session_state:
    st.session_state.logs: List[Dict[str, Any]] = []


def log(evt: str, payload: Dict[str, Any] | None = None):
    st.session_state.logs.insert(0, {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "evt": evt,
        "payload": payload or {}
    })

# ==================== Página 1: Wake Word → LED ====================

def page_wake_word():
    st.title("🔔 Ayuda por Palabra de Atención")

    st.write("Cuando el sistema escucha la *palabra de atención*, se enciende el LED de ayuda.")
    st.caption("Funciona con tu micrófono usando **streamlit-mic-recorder**. Da permisos al navegador.")

    col = st.columns(2)
    with col[0]:
        wake = st.text_input("Palabra de atención", value="ayuda")
    with col[1]:
        auto_off = st.number_input("Apagado automático (seg)", 0, 300, 10)

    st.markdown('<div class="card"><div class="title">🎙️ Escucha por micrófono</div><div class="muted">Di la palabra de atención para encender el LED.</div></div>', unsafe_allow_html=True)

    # Botón grande como alternativa a la voz
    st.markdown('<div class="card"><div class="title">🆘 Botón de ayuda</div><div class="muted">Si no quieres usar la voz, también puedes encender el LED desde aquí.</div></div>', unsafe_allow_html=True)
    if st.button("🚨 Necesito ayuda (botón)"):
        st.session_state.hw.set_led("on")
        log("led_on_button", {"source": "button"})
        st.success("LED de ayuda: ENCENDIDO por botón")
        st.session_state.led_on_since = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  
    if not MIC_OK:
        st.error("No se encontró el componente de micrófono. Instala con: pip install streamlit-mic-recorder")
    else:
        transcript = speech_to_text(language='es', use_container_width=True, just_once=True, key='stt_wake')
        if transcript:
            st.info(f"Transcripción: **{transcript}**")
            if wake.lower() in transcript.lower():
                st.session_state.hw.set_led("on")
                log("led_on", {"wake": wake, "cmd": transcript, "source": "mic"})
                st.success("LED de ayuda: ENCENDIDO por voz")
                st.session_state.led_on_since = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                st.write("No se detectó la palabra de atención en la transcripción.")

    # Auto-off simple por tiempo
    if 'led_on_since' in st.session_state and st.session_state.hw.led_state == 'on' and auto_off > 0:
        started = datetime.strptime(st.session_state.led_on_since, '%Y-%m-%d %H:%M:%S')
        if (datetime.now() - started).total_seconds() >= auto_off:
            st.session_state.hw.set_led('off')
            log('led_auto_off', {'after_sec': auto_off})
            st.session_state.pop('led_on_since', None)

    st.divider()
    st.subheader("Estado del LED")
    led_on = st.session_state.hw.led_state == 'on'
    status_color = '#22c55e' if led_on else '#475569'
    st.markdown(f'<span class="status-dot" style="background:{status_color}"></span>' + ("**ON**" if led_on else "**OFF**"), unsafe_allow_html=True)
    btn_cols = st.columns([1,1])
    if btn_cols[0].button("Apagar LED"):
        st.session_state.hw.set_led("off")
        log("led_off", {})
    if btn_cols[1].button("Encender LED (manual)"):
        st.session_state.hw.set_led("on")
        log("led_on_manual", {})

    st.divider()
    st.subheader("Logs")
    for r in st.session_state.logs[:30]:
        st.write(f"`{r['ts']}` • **{r['evt']}** — {json.dumps(r['payload'], ensure_ascii=False)}")

# ==================== Página 2: Señalar Medicamentos ====================

def page_dispenser():
    st.title("💊 Señalador de Medicamentos (Servo)")

    st.write("Selecciona un medicamento y la palanca (servo) **lo señalará** con un ángulo específico. Para el demo usamos 3 medicamentos mapeados a 45°, 90° y 135°.")

    # Config sencilla de 3 medicamentos
    if 'angle_meds' not in st.session_state:
        st.session_state.angle_meds = [
            {"name": "Losartan", "angle": 45},
            {"name": "Acetaminofen", "angle": 90},
            {"name": "Lírica", "angle": 135},
        ]

    with st.expander("Configurar nombres/ángulos", expanded=False):
        for i, m in enumerate(st.session_state.angle_meds):
            c1, c2 = st.columns([3,1])
            m['name'] = c1.text_input(f"Nombre #{i+1}", value=m['name'], key=f"cfg_name_{i}")
            m['angle'] = c2.number_input(f"Ángulo #{i+1}", 0, 180, value=int(m['angle']), key=f"cfg_ang_{i}")
        st.caption("Sugeridos: 45°, 90°, 135°")

    st.divider()
    st.subheader("Control por voz")

    st.markdown(
        "<div class='card'><div class='title'>🎙️ Di el nombre del medicamento</div>"
        "<div class='muted'>Ejemplo: “losartan”, “metformina”, “vitamina D”. "
        "El sistema intentará encontrar el medicamento configurado cuyo nombre coincida.</div></div>",
        unsafe_allow_html=True
    )

    if not MIC_OK:
        st.error("No se encontró el componente de micrófono. Instala con: pip install streamlit-mic-recorder")
    else:
        # Usamos una clave distinta a la de la otra página para no mezclar estados
        transcript_med = speech_to_text(
            language='es',
            use_container_width=True,
            just_once=True,
            key='stt_meds'
        )

        if transcript_med:
            st.info(f"Transcripción: **{transcript_med}**")
            texto = transcript_med.lower()

            matched = None
            # Buscamos un medicamento cuya “palabra clave” esté en lo que dijo la persona
            for m in st.session_state.angle_meds:
                # Palabra clave: primera palabra del nombre (ej. "Losartan" de "Losartan 50mg")
                keywords = m['name'].split()
                if not keywords:
                    continue
                clave = keywords[0].lower()
                if clave in texto:
                    matched = m
                    break

            if matched:
                st.session_state.hw.point_servo(matched['angle'], med_name=matched['name'])
                log("point_med_voice", {"name": matched['name'], "angle": matched['angle'], "source": "voice"})
                st.success(f"Medicamento reconocido: **{matched['name']}** → Servo a {matched['angle']}°")
            else:
                st.warning("No se reconoció ningún medicamento en la transcripción. Intenta decir claramente el nombre.")

    st.divider()
    st.subheader("Señalar medicamento (botones)")
    cols = st.columns(3)
    for i, m in enumerate(st.session_state.angle_meds):
        with cols[i % 3]:
            st.markdown(
                f"<div class='card'><div class='title'>{m['name']}</div>"
                f"<div class='muted'>Ángulo: {m['angle']}°</div></div>",
                unsafe_allow_html=True
            )
            if st.button(f"Señalar {m['name']}"):
                st.session_state.hw.point_servo(m['angle'], med_name=m['name'])
                log("point_med", {"name": m['name'], "angle": m['angle']})
                st.success(f"Servo apuntando a {m['name']} ({m['angle']}°)")

    cols = st.columns(3)
    for i, m in enumerate(st.session_state.angle_meds):
        with cols[i % 3]:
            st.markdown(f"<div class='card'><div class='title'>{m['name']}</div><div class='muted'>Ángulo: {m['angle']}°</div></div>", unsafe_allow_html=True)
            if st.button(f"Señalar {m['name']}"):
                st.session_state.hw.point_servo(m['angle'], med_name=m['name'])
                log("point_med", {"name": m['name'], "angle": m['angle']})
                st.success(f"Servo apuntando a {m['name']} ({m['angle']}°)")

    st.divider()
    st.subheader("Estado del servo")
    st.metric("Ángulo", f"{st.session_state.hw.servo_angle}°")
    st.caption(f"Último seleccionado: {st.session_state.hw.last_med or '—'}")

    st.divider()
    st.subheader("Logs")
    for r in st.session_state.logs[:30]:
        st.write(f"`{r['ts']}` • **{r['evt']}** — {json.dumps(r['payload'], ensure_ascii=False)}")

# ==================== App ====================

st.set_page_config(page_title="Demo 2 Funciones", page_icon="🧓", layout="wide")
with st.sidebar:
    st.header("Demo 2 Funciones")
    page = st.radio("Ir a…", ["Wake Word → LED", "Dispensador"])
    if MQTT_OK:
        st.caption("MQTT activo: publicando a test.mosquitto.org")
    else:
        st.caption("MQTT desactivado (modo simulado)")

if page == "Wake Word → LED":
    page_wake_word()
else:
    page_dispenser()
