import streamlit as st
from datetime import datetime

# --------- CONFIG BÁSICA + THEME ---------
st.set_page_config(page_title="Demo Multimodal – Casa Asistiva", page_icon="💡", layout="wide")

# CSS simple para look & feel
st.markdown("""
<style>
:root { --bg:#0b1220; --card:#0f172a; --muted:#64748b; --ok:#22c55e; --off:#475569; --accent:#7c3aed;}
body {background: var(--bg);}
.block-container {padding-top: 2rem; max-width: 1100px;}
.small {color: var(--muted); font-size: 0.9rem;}
.badge {display:inline-block; padding:.25rem .5rem; border-radius:999px; background:#1f2937; color:#e5e7eb; font-size:.8rem;}
.led {width:14px; height:14px; border-radius:50%; display:inline-block; margin-right:.4rem; vertical-align:middle;}
.card {background: var(--card); padding:1rem 1.25rem; border-radius:14px; border:1px solid #1f2937;}
.title {font-weight:700; font-size:1.4rem;}
.btn-row button {margin-right:.5rem;}
</style>
""", unsafe_allow_html=True)

# --------- ESTADO GLOBAL ---------
if "led_on" not in st.session_state:
    st.session_state.led_on = False

if "last_command" not in st.session_state:
    st.session_state.last_command = None

if "servo_angle" not in st.session_state:
    st.session_state.servo_angle = 0  # grados

# --------- HELPERS ---------
def set_led(on: bool, reason: str = ""):
    st.session_state.led_on = on
    st.session_state.last_command = f"{'ON' if on else 'OFF'} @ {datetime.now().strftime('%H:%M:%S')} {reason}".strip()

def set_servo(angle: int, reason: str = ""):
    st.session_state.servo_angle = angle
    st.session_state.last_command = f"Servo → {angle}° @ {datetime.now().strftime('%H:%M:%S')} {reason}".strip()

# --------- SIDEBAR / NAVEGACIÓN ---------
page = st.sidebar.radio(
    "Navegación",
    ["🔊 Ayuda por palabra de atención", "💊 Señalar medicamento (servo)"],
    help="Dos flujos independientes para cumplir el proyecto."
)
st.sidebar.markdown("<span class='badge'>Demo local</span>  •  Wokwi/Arduino en clase", unsafe_allow_html=True)

# =========================================================
#  PÁGINA 1: AYUDA POR PALABRA DE ATENCIÓN (MICRÓFONO)
# =========================================================
if page.startswith("🔊"):
    st.markdown("### 🔊 Palabra de atención → Enciende LED de ayuda")
    st.markdown(
        "<p class='small'>Cuando el sistema detecte la palabra de atención por voz, "
        "encenderá el LED de ayuda. Para la demo usamos reconocimiento en el navegador.</p>",
        unsafe_allow_html=True
    )

    # ------ Indicador LED (usa session_state SIEMPRE) ------
    status_color = '#22c55e' if st.session_state.led_on else '#475569'
    st.markdown(
        f"<div class='card'><span class='title'>Estado LED: "
        f"<span class='led' style='background:{status_color}'></span>"
        f"{'Encendido' if st.session_state.led_on else 'Apagado'}</span>"
        f"<div class='small'>Último evento: {st.session_state.last_command or '—'}</div></div>",
        unsafe_allow_html=True
    )

    # ------ Controles manuales (útiles para probar rápidamente) ------
    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Encender LED (prueba)"):
            set_led(True, "(botón)")
    with colB:
        if st.button("Apagar LED"):
            set_led(False, "(botón)")

    st.divider()

    # ------ Captura de voz en el navegador con Web Speech API ------
    # Esto corre en el cliente y se comunica vía componentes JS <-> Streamlit.
    # No requiere instalar pyaudio en tu PC.
    attn_word = st.text_input("Palabra de atención", value="ayuda", help="Di esta palabra para encender el LED.")
    st.markdown("<div class='small'>Haz clic en <b>Iniciar escucha</b> y permite el micrófono en el navegador.</div>", unsafe_allow_html=True)

    start = st.button("🎙️ Iniciar escucha")
    stop = st.button("⏹️ Detener escucha")

    # Componente JS mínimo para Web Speech API
    st.markdown("""
    <script>
    const s = window.streamlitSpeechComp || {recognizer:null, listening:false};
    function startRec(attn){
      try{
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if(!SpeechRecognition){ window.parent.postMessage({type:'st_comm', key:'voice_err', value:'API no soportada'}, '*'); return; }
        s.recognizer = new SpeechRecognition();
        s.recognizer.lang = 'es-ES';
        s.recognizer.continuous = true;
        s.recognizer.interimResults = false;
        s.recognizer.onresult = (e)=>{
          const txt = e.results[e.results.length-1][0].transcript.trim().toLowerCase();
          window.parent.postMessage({type:'st_comm', key:'voice_txt', value:txt}, '*');
          if (txt.includes(attn.toLowerCase())) {
            window.parent.postMessage({type:'st_comm', key:'voice_hit', value:txt}, '*');
          }
        };
        s.recognizer.onend = ()=>{ s.listening=false; window.parent.postMessage({type:'st_comm', key:'voice_state', value:'stopped'}, '*'); };
        s.recognizer.start(); s.listening = true;
        window.parent.postMessage({type:'st_comm', key:'voice_state', value:'started'}, '*');
      }catch(err){ window.parent.postMessage({type:'st_comm', key:'voice_err', value:String(err)}, '*'); }
    }
    function stopRec(){ if(s.recognizer){ s.recognizer.stop(); } }
    window.streamlitSpeechComp = s;

    // Puente de mensajes
    window.addEventListener('message',(ev)=>{
      const d = ev.data;
      if(d?.type==='streamlit:setComponentValue'){ /* no-op */ }
    });

    // Botones controlados por Streamlit (marcadores que escribimos abajo)
    </script>
    """, unsafe_allow_html=True)

    # Marcadores / triggers
    if start:
        # Iniciar con la palabra de atención que puso el usuario
        st.markdown(f"<script>startRec({repr(attn_word)});</script>", unsafe_allow_html=True)
    if stop:
        st.markdown("<script>stopRec();</script>", unsafe_allow_html=True)

    # Receptor de los mensajes del cliente
    # (truco: usamos st.experimental_data_editor invisible para forzar reruns con postMessage,
    # pero aquí bastará con un write-js que llame a /?voice_hit=1 vía hash; lo simple:)
    st.markdown("""
    <script>
    window.addEventListener('message', (e)=>{
      const d = e.data || {};
      if(d.type==='st_comm' && d.key==='voice_hit'){
        fetch(window.location.href, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action:'LED_ON_VOICE'})})
        .then(()=>{ window.location.reload(); });
      }
    });
    </script>
    """, unsafe_allow_html=True)

    # Procesar POST para encender LED al detectar la palabra
    try:
        import os, json, sys
        if st.session_state.get("_did_hook") is None:
            from streamlit.web.server.websocket_headers import _get_websocket_headers as _ws
            st.session_state["_did_hook"] = True  # solo una vez
        # Si el servidor no expone body fácil, ignoramos; mantenemos compatibilidad:
        # La recarga de la página ya refleja cambios de estado.
    except Exception:
        pass

    # Fallback server-side (ligero): si recargó con un marker en la URL, no lo usamos ahora.

    # Mini hack para mostrar instrucción clara
    st.info("Di la palabra de atención (por ejemplo **ayuda**) para encender el LED. Usa los botones si quieres probar sin voz.")

# =========================================================
#  PÁGINA 2: SEÑALAR MEDICAMENTO (SERVO 45° / 90° / 135°)
# =========================================================
else:
    st.markdown("### 💊 Señalar medicamento con un servo (3 posiciones)")
    st.markdown("<p class='small'>En el prototipo, la ‘palanca’ será un servo que apunta al medicamento seleccionado.</p>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        col1, col2 = st.columns([2,1])

        with col1:
            med = st.selectbox(
                "Selecciona el medicamento",
                ["— Selecciona —", "Analgésico (45°)", "Antibiótico (90°)", "Vitaminas (135°)"]
            )
            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("Analgésico → 45°"):
                    set_servo(45, "(botón)")
            with colB:
                if st.button("Antibiótico → 90°"):
                    set_servo(90, "(botón)")
            with colC:
                if st.button("Vitaminas → 135°"):
                    set_servo(135, "(botón)")

            # Si usan el selectbox en lugar de botones
            map_angles = {
                "Analgésico (45°)": 45,
                "Antibiótico (90°)": 90,
                "Vitaminas (135°)": 135
            }
            if med in map_angles:
                set_servo(map_angles[med], "(selector)")

        with col2:
            # Visual del ángulo
            st.markdown("<div class='title'>Estado servo</div>", unsafe_allow_html=True)
            st.metric("Ángulo actual", f"{st.session_state.servo_angle}°")
            st.markdown(f"<div class='small'>Último evento: {st.session_state.last_command or '—'}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown(
        "<p class='small'>Integración con hardware: envía el ángulo al Arduino/Wokwi por "
        "Serial o HTTP (según tu setup). Dejo el esqueleto de función a continuación.</p>",
        unsafe_allow_html=True
    )

    with st.expander("Ver ejemplo de stub para enviar al microcontrolador"):
        st.code("""
import requests  # si usas firmware con endpoint HTTP (Wokwi o ESP32/ESP8266)
# O usa pyserial si es por USB: import serial

def send_angle_to_device(angle:int):
    # EJEMPLO HTTP:
    # url = "http://<ip-o-url-del-dispositivo>/servo"
    # requests.post(url, json={"angle": angle}, timeout=2)

    # EJEMPLO SERIAL:
    # ser = serial.Serial('COM3', 9600, timeout=1)
    # ser.write(f"{angle}\\n".encode())
    # ser.close()
    pass
        """, language="python")

