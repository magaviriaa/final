"""
Streamlit – Versión Simple (2 funciones / 2 páginas)
---------------------------------------------------
Función A (Página 1): "Wake word" (palabra de atención) → enciende LED de ayuda.
Función B (Página 2): Botón físico por medicamento → abre compuerta (servo) del
compartimento correspondiente.

Esta plantilla es mínima para la rúbrica: 2 páginas, 2 modalidades (voz/texto y botón físico),
y vínculo con mundo físico (LED + servo). Incluye un puente HW simulado; cambienlo por
Serial/MQTT para WOKWI/ESP32.

Cómo correr:
  streamlit run app_simple.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st

# ==================== Datos simples ====================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
MEDS_FILE = DATA_DIR / "meds_simple.json"

DEFAULT_MEDS = [
    {"name": "Losartan 50mg", "compartment": 1},
    {"name": "Metformina 500mg", "compartment": 2},
]

if MEDS_FILE.exists():
    try:
        MEDS = json.loads(MEDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        MEDS = DEFAULT_MEDS
else:
    MEDS = DEFAULT_MEDS
    MEDS_FILE.write_text(json.dumps(MEDS, ensure_ascii=False, indent=2), encoding="utf-8")

# ==================== Puente de hardware (simulado) ====================
class HwBridge:
    """Reemplazar con implementación real (Serial/MQTT).
    Protocolo sugerido (JSON):
      → ESP32: {"type":"act","led":"on"|"off"}
      → ESP32: {"type":"act","servo": <compartment:int>, "angle": 90}
    """
    def __init__(self):
        self.led_state = "off"  # off|on
        self.compartment_last = None

    def set_led(self, state: str):
        self.led_state = state
        # Real: enviar por serial/mqtt
        # serial.write(b'[{"type":"act","led":"%s"}]' % state.encode())

    def open_compartment(self, idx: int):
        self.compartment_last = idx
        # Real: enviar {"type":"act","servo": idx, "angle": 90}


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
    st.caption("En demo usamos texto como si fuera STT. En producción: micrófono + STT.")

    # Configuración mínima
    col = st.columns(2)
    with col[0]:
        wake = st.text_input("Palabra de atención", value="ayuda")
    with col[1]:
        auto_off = st.number_input("Apagado automático (seg)", 0, 300, 10)

    st.divider()
    st.subheader("Simulación de escucha (STT → texto)")
    cmd = st.text_input("Di algo… (ej: 'ayuda por favor')", value="")
    c1, c2 = st.columns([1,1])
    if c1.button("Procesar entrada"):
        if wake.lower() in cmd.lower():
            st.session_state.hw.set_led("on")
            log("led_on", {"wake": wake, "cmd": cmd})
            st.success("LED de ayuda: ENCENDIDO")
        else:
            st.info("No se detectó la palabra de atención.")

    if c2.button("Apagar LED"):
        st.session_state.hw.set_led("off")
        log("led_off", {})

    st.divider()
    st.subheader("Estado del LED")
    st.metric("LED", "🟢 ON" if st.session_state.hw.led_state == "on" else "⚪ OFF")

    st.divider()
    st.subheader("Logs")
    for r in st.session_state.logs[:30]:
        st.write(f"`{r['ts']}` • **{r['evt']}** — {json.dumps(r['payload'], ensure_ascii=False)}")

# ==================== Página 2: Dispensador de Medicamentos ====================

def page_dispenser():
    st.title("💊 Dispensador de Medicamentos")

    st.write("Cada medicamento tiene un botón físico en el mundo real. Al presionarlo, se abre la compuerta de su compartimento (servo). Aquí simulamos ese evento y mostramos el estado.")

    # Lista editable simple (por si quieren renombrar)
    with st.expander("Configurar medicamentos (simple)", expanded=False):
        for i, m in enumerate(MEDS):
            col = st.columns([3,1,1])
            with col[0]:
                m["name"] = st.text_input(f"Nombre #{i+1}", value=m["name"], key=f"mname{i}")
            with col[1]:
                m["compartment"] = st.number_input(f"Comp #{i+1}", 1, 8, value=int(m["compartment"]), key=f"mcomp{i}")
        if st.button("Guardar lista"):
            MEDS_FILE.write_text(json.dumps(MEDS, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Medicamentos guardados")

    st.divider()
    st.subheader("Simular botón físico → abrir compuerta")
    cols = st.columns(3)
    for i, m in enumerate(MEDS):
        with cols[i % 3]:
            if st.button(f"Abrir {m['name']}"):
                st.session_state.hw.open_compartment(m["compartment"])
                log("open_compartment", {"name": m["name"], "compartment": m["compartment"]})
                st.success(f"Compuerta {m['compartment']} abierta (simulado)")

    st.divider()
    st.subheader("Última acción")
    last = st.session_state.hw.compartment_last
    st.metric("Compuerta", f"#{last}" if last else "—")

    st.divider()
    st.subheader("Logs")
    for r in st.session_state.logs[:30]:
        st.write(f"`{r['ts']}` • **{r['evt']}** — {json.dumps(r['payload'], ensure_ascii=False)}")

# ==================== App ====================

st.set_page_config(page_title="Demo 2 Funciones", page_icon="🧓", layout="wide")
with st.sidebar:
    st.header("Demo 2 Funciones")
    page = st.radio("Ir a…", ["Wake Word → LED", "Dispensador"])

if page == "Wake Word → LED":
    page_wake_word()
else:
    page_dispenser()
