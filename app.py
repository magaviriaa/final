"""
Streamlit – Plantilla base (2 páginas) para "Asistente para Personas Mayores"
-----------------------------------------------------------------------------
✔️ 2 páginas: Dashboard (Cuidado) y Configuración
✔️ Modalidades: voz (stub), botones, simulación de sensores (PIR, SOS, Caída)
✔️ Puente hardware (stub) listo para conectar con WOKWI (serial/MQTT)
✔️ Reglas simples de automatización (recordatorio de medicación, inactividad, caída)

Estructura recomendada del repo (si lo separas):
- app.py  ← este archivo
- data/meds.json, data/user.json, data/rules.json  ← opcional (se crean en runtime)

Para correr:
  streamlit run app.py
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st

# ========== Helpers de almacenamiento (JSON sobre disco) ==========
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

MEDS_FILE = DATA_DIR / "meds.json"
USER_FILE = DATA_DIR / "user.json"
RULES_FILE = DATA_DIR / "rules.json"

DEFAULT_USER = {
    "name": "Ana",
    "birthyear": 1948,
    "contacts": [
        {"name": "Laura", "channel": "whatsapp", "priority": 1},
        {"name": "Dr. Ruiz", "channel": "email", "priority": 2},
    ],
}

DEFAULT_MEDS = [
    {
        "drug": "Losartan",
        "dose": "50mg",
        "times": ["10:30", "22:00"],
        "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        "requires_voice_confirm": True,
        "tolerance_min": 15,
    }
]

DEFAULT_RULES = {
    "fall_event": {"buzzer": "on", "led": "red", "notify_priority": 1},
    "no_presence_minutes_day": 20,
    "day_start": "06:00",
    "day_end": "22:00",
    "checkin_timeout_sec": 30,
}


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return default


def save_json(path: Path, obj: Any):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ========== Puente de hardware (stub) ==========
class HwBridge:
    """Stub de hardware.
    Reemplaza internamente con:
      - Serial (pyserial) leyendo JSON del ESP32/WOKWI
      - ó MQTT (paho-mqtt) suscribiendo a topics
    Métodos:
      - read() -> dict con estados de sensores
      - act(**kwargs) -> enviar acciones a actuadores
    """

    def __init__(self):
        # Estados simulados de sensores
        self._pir = 1  # 1 si detecta presencia
        self._sos = 0
        self._fall = 0
        # Estado actuadores
        self._led = "off"
        self._buzzer = "off"
        self._last_read_ts = time.time()

    def read(self) -> Dict[str, Any]:
        """Devuelve el estado actual (simulado)."""
        # En real: leer del puerto serial o del topic MQTT
        return {
            "pir": self._pir,
            "sos": self._sos,
            "fall": self._fall,
            "ts": time.time(),
        }

    def act(self, led: str = None, buzzer: str = None):
        if led is not None:
            self._led = led
        if buzzer is not None:
            self._buzzer = buzzer
        # En real: enviar JSON a ESP32/MQTT, por ej.
        # serial.write(json.dumps({"type":"act","led":led,"buzzer":buzzer}).encode())

    # Helpers de simulación (para la UI)
    def simulate_fall(self):
        self._fall = 1

    def reset_fall(self):
        self._fall = 0

    def press_sos(self):
        self._sos = 1

    def reset_sos(self):
        self._sos = 0

    def set_presence(self, present: bool):
        self._pir = 1 if present else 0


# ========== Stub de Voz (STT/TTS) ==========
class Voice:
    @staticmethod
    def say(text: str):
        # En demo: mostramos un toast/log. En real: usar pyttsx3 o gTTS
        st.toast(f"🔊 {text}")

    @staticmethod
    def listen() -> str:
        # Stub: campo de texto en la UI hará de STT manual
        return ""


# ========== Meds scheduler ==========

def str_to_time(hhmm: str) -> datetime:
    today = datetime.now().date()
    h, m = map(int, hhmm.split(":"))
    return datetime(today.year, today.month, today.day, h, m)


def within_tolerance(times: List[str], now: datetime, tol_min: int) -> List[str]:
    hits = []
    for t in times:
        dt = str_to_time(t)
        if abs((now - dt).total_seconds()) <= tol_min * 60:
            hits.append(t)
    return hits


def day_ok(med: Dict[str, Any], now: datetime) -> bool:
    return now.strftime("%a") in med.get("days", [])


def next_due(meds: List[Dict[str, Any]], now: datetime) -> Dict[str, Any] | None:
    candidates = []
    for m in meds:
        if day_ok(m, now):
            near = within_tolerance(m["times"], now, m.get("tolerance_min", 10))
            if near:
                m = m.copy(); m["due_times"] = near
                candidates.append(m)
    if not candidates:
        return None
    # El más próximo (heurística: el primer time match)
    candidates.sort(key=lambda x: x["due_times"][0])
    return candidates[0]


# ========== Estado global ==========
if "hw" not in st.session_state:
    st.session_state.hw = HwBridge()
if "user" not in st.session_state:
    st.session_state.user = load_json(USER_FILE, DEFAULT_USER)
if "meds" not in st.session_state:
    st.session_state.meds = load_json(MEDS_FILE, DEFAULT_MEDS)
if "rules" not in st.session_state:
    st.session_state.rules = load_json(RULES_FILE, DEFAULT_RULES)
if "logs" not in st.session_state:
    st.session_state.logs: List[Dict[str, Any]] = []
if "global_state" not in st.session_state:
    st.session_state.global_state = "SAFE"  # SAFE | REMINDER | ALERT_FALL | CHECK_IN
if "last_pir_on" not in st.session_state:
    st.session_state.last_pir_on = datetime.now()
if "checkin_started_at" not in st.session_state:
    st.session_state.checkin_started_at = None


# ========== Utilidades de reglas ==========

def daytime(now: datetime) -> bool:
    r = st.session_state.rules
    start = str_to_time(r.get("day_start", "06:00")).time()
    end = str_to_time(r.get("day_end", "22:00")).time()
    return start <= now.time() <= end


def minutes_no_presence(now: datetime) -> int:
    delta = now - st.session_state.last_pir_on
    return int(delta.total_seconds() // 60)


def log_event(evt_type: str, payload: Dict[str, Any] | None = None):
    st.session_state.logs.insert(0, {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": evt_type,
        "payload": payload or {}
    })


def notify_contact(priority: int = 1, who_name: str | None = None):
    contacts = st.session_state.user.get("contacts", [])
    if who_name:
        contact = next((c for c in contacts if c["name"].lower() == who_name.lower()), None)
    else:
        contact = next((c for c in contacts if c.get("priority") == priority), None)
    if contact:
        log_event("notify", {"contact": contact["name"], "channel": contact.get("channel", "?")})
        Voice.say(f"Notifiqué a {contact['name']} (simulado)")
    else:
        st.warning("No se encontró contacto para notificar.")


# ========== Render de páginas ==========

def render_dashboard():
    st.title("🧓 Cuidado – Dashboard")

    # Auto refresh suave para simular tiempo real
    st_autorefresh_ms = st.sidebar.slider("Refresco (ms)", 500, 5000, 1500, 100)
    st.sidebar.write("Estado HW:", st.session_state.hw._led, st.session_state.hw._buzzer)

    sensor = st.session_state.hw.read()
    now = datetime.now()

    # Update presencia
    if sensor["pir"] == 1:
        st.session_state.last_pir_on = now

    # Estados / Reglas
    # 1) Caída / SOS
    if sensor["fall"] or sensor["sos"]:
        if st.session_state.global_state != "ALERT_FALL":
            st.session_state.global_state = "ALERT_FALL"
            st.session_state.hw.act(buzzer="on", led="red")
            Voice.say("Alerta de emergencia. ¿Necesitas ayuda?")
            log_event("fall_alert", {"fall": sensor["fall"], "sos": sensor["sos"]})

    # 2) Recordatorio de medicación
    if st.session_state.global_state == "SAFE":
        med = next_due(st.session_state.meds, now)
        if med:
            st.session_state.global_state = "REMINDER"
            st.session_state.hw.act(led="green")
            Voice.say(f"Es hora de {med['drug']} {med['dose']}")
            log_event("med_reminder", {"drug": med["drug"], "dose": med["dose"], "times": med["due_times"]})
            st.session_state.current_med = med

    # 3) Inactividad diurna
    if st.session_state.global_state == "SAFE" and daytime(now):
        if minutes_no_presence(now) > st.session_state.rules.get("no_presence_minutes_day", 20):
            st.session_state.global_state = "CHECK_IN"
            st.session_state.checkin_started_at = now
            Voice.say("¿Todo bien?")
            log_event("checkin_start", {"minutes_no_presence": minutes_no_presence(now)})

    # UI – Estado global
    state = st.session_state.global_state
    if state == "SAFE":
        st.success("Estado: 🟢 Normal")
    elif state == "REMINDER":
        st.info("Estado: 🟡 Recordatorio de medicación")
    elif state == "ALERT_FALL":
        st.error("Estado: 🔴 Alerta de emergencia")
    elif state == "CHECK_IN":
        st.warning("Estado: 🟠 Chequeo de bienestar")

    # Tarjetas principales
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Próxima medicación")
        current_med = st.session_state.get("current_med")
        if state == "REMINDER" and current_med:
            st.metric(label=current_med["drug"], value=current_med["dose"], delta=f"Horarios: {', '.join(current_med['due_times'])}")
            c1, c2, c3 = st.columns([1,1,1])
            if c1.button("Tomada ✅", use_container_width=True):
                log_event("med_taken", {"drug": current_med["drug"]})
                st.session_state.global_state = "SAFE"
                st.session_state.hw.act(led="off")
                st.session_state.current_med = None
                Voice.say("¡Listo! Medicación confirmada")
            if c2.button("Posponer 10 min", use_container_width=True):
                log_event("med_snooze", {"drug": current_med["drug"], "mins": 10})
                # truco: agregamos un horario temporal 10 min adelante
                tnext = (datetime.now() + timedelta(minutes=10)).strftime("%H:%M")
                current_med["times"].append(tnext)
                st.session_state.global_state = "SAFE"
                st.session_state.hw.act(led="off")
                st.experimental_rerun()
            if c3.button("Omitir", use_container_width=True):
                log_event("med_skipped", {"drug": current_med["drug"]})
                st.session_state.global_state = "SAFE"
                st.session_state.hw.act(led="off")
                st.session_state.current_med = None
        else:
            st.caption("Sin recordatorios en ventana de tolerancia.")

    with col2:
        st.subheader("Sensores")
        s1, s2, s3 = st.columns(3)
        s1.metric("PIR", "🟢" if sensor["pir"] else "⚪")
        s2.metric("SOS", "🔴" if sensor["sos"] else "⚪")
        s3.metric("Caída", "🔴" if sensor["fall"] else "⚪")

        st.divider()
        st.subheader("Acciones rápidas")
        q1, q2, q3, q4 = st.columns(4)
        if q1.button("SOS manual", use_container_width=True):
            st.session_state.hw.press_sos()
            st.experimental_rerun()
        if q2.button("Silenciar", use_container_width=True):
            st.session_state.hw.act(buzzer="off")
            st.session_state.hw.reset_sos(); st.session_state.hw.reset_fall()
            st.session_state.global_state = "SAFE"
        if q3.button("Notificar prioridad 1", use_container_width=True):
            notify_contact(priority=1)
        if q4.button("Simular caída", use_container_width=True):
            st.session_state.hw.simulate_fall()
            st.experimental_rerun()

    st.divider()
    st.subheader("Feed de actividad")
    for row in st.session_state.logs[:50]:
        st.write(f"`{row['ts']}` • **{row['type']}** — {json.dumps(row['payload'], ensure_ascii=False)}")

    # Gestión de CHECK_IN timeout
    if state == "CHECK_IN" and st.session_state.checkin_started_at:
        elapsed = (now - st.session_state.checkin_started_at).total_seconds()
        st.info(f"Esperando confirmación… {int(elapsed)}s")
        c_ok, c_notify = st.columns([1,1])
        if c_ok.button("Estoy bien ✅", use_container_width=True):
            log_event("checkin_ok", {})
            st.session_state.global_state = "SAFE"
            st.session_state.checkin_started_at = None
        if elapsed > st.session_state.rules.get("checkin_timeout_sec", 30):
            log_event("checkin_timeout", {})
            notify_contact(priority=1)
            st.session_state.global_state = "SAFE"
            st.session_state.checkin_started_at = None

    # Auto-refresh
    st.experimental_singleton.clear()  # no-op visual; evitar caching viejo
    st.experimental_rerun()


def render_config():
    st.title("⚙️ Configuración")
    user = st.session_state.user
    meds = st.session_state.meds
    rules = st.session_state.rules

    st.subheader("Perfil")
    c1, c2 = st.columns([2,1])
    with c1:
        user["name"] = st.text_input("Nombre", value=user.get("name", ""))
        user["birthyear"] = st.number_input("Año de nacimiento", value=int(user.get("birthyear", 1948)))
    with c2:
        if st.button("Guardar perfil"):
            save_json(USER_FILE, user)
            st.success("Perfil guardado")

    st.divider()
    st.subheader("Contactos de emergencia")
    for i, c in enumerate(user.get("contacts", [])):
        with st.expander(f"Contacto #{i+1}"):
            c["name"] = st.text_input("Nombre", value=c.get("name", ""), key=f"cname{i}")
            c["channel"] = st.selectbox("Canal", ["whatsapp", "email", "sms"], index=["whatsapp","email","sms"].index(c.get("channel","whatsapp")), key=f"cch{i}")
            c["priority"] = st.number_input("Prioridad", 1, 3, value=int(c.get("priority", 1)), key=f"cpr{i}")
    if st.button("Guardar contactos"):
        save_json(USER_FILE, user)
        st.success("Contactos guardados")

    st.divider()
    st.subheader("Agenda de medicación")
    for i, m in enumerate(meds):
        with st.expander(f"{m['drug']} {m['dose']}"):
            m["drug"] = st.text_input("Medicamento", value=m.get("drug",""), key=f"mdrug{i}")
            m["dose"] = st.text_input("Dosis", value=m.get("dose",""), key=f"mdose{i}")
            m["times"] = st.text_input("Horarios (HH:MM, separados por coma)", value=", ".join(m.get("times", [])), key=f"mtimes{i}").replace(" ", "").split(",")
            m["requires_voice_confirm"] = st.checkbox("Requiere confirmación por voz", value=m.get("requires_voice_confirm", True), key=f"mvoice{i}")
            m["tolerance_min"] = st.number_input("Tolerancia (min)", 0, 120, value=int(m.get("tolerance_min", 15)), key=f"mtol{i}")
    cadd1, cadd2 = st.columns([1,3])
    if cadd1.button("➕ Agregar medicamento"):
        meds.append({"drug":"Nuevo","dose":"","times":["08:00"],"days":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],"requires_voice_confirm":False,"tolerance_min":10})
    if cadd2.button("Guardar medicación"):
        save_json(MEDS_FILE, meds)
        st.success("Medicaciones guardadas")

    st.divider()
    st.subheader("Reglas")
    colr1, colr2, colr3 = st.columns(3)
    with colr1:
        rules["no_presence_minutes_day"] = st.number_input("Min sin presencia (día)", 1, 240, value=int(rules.get("no_presence_minutes_day", 20)))
    with colr2:
        rules["day_start"] = st.text_input("Inicio día (HH:MM)", value=rules.get("day_start","06:00"))
    with colr3:
        rules["day_end"] = st.text_input("Fin día (HH:MM)", value=rules.get("day_end","22:00"))

    r1, r2 = st.columns(2)
    with r1:
        rules["checkin_timeout_sec"] = st.number_input("Timeout check-in (s)", 5, 300, value=int(rules.get("checkin_timeout_sec", 30)))
    with r2:
        st.write("Evento de caída: LED rojo + buzzer y notificación prioridad 1")

    if st.button("Guardar reglas"):
        save_json(RULES_FILE, rules)
        st.success("Reglas guardadas")

    st.divider()
    st.subheader("Simulación HW")
    sim1, sim2, sim3, sim4, sim5 = st.columns(5)
    if sim1.button("Caída"):
        st.session_state.hw.simulate_fall()
        st.success("Caída simulada")
    if sim2.button("Reset caída"):
        st.session_state.hw.reset_fall()
    if sim3.button("SOS"):
        st.session_state.hw.press_sos()
    if sim4.button("Reset SOS"):
        st.session_state.hw.reset_sos()
    with sim5:
        present = st.toggle("Presencia (PIR)", value=True)
        st.session_state.hw.set_presence(present)


# ========== Sidebar / Navegación ==========
st.set_page_config(page_title="Asistente Adulto Mayor", page_icon="🧓", layout="wide")

with st.sidebar:
    st.header("Asistente 🧓")
    page = st.radio("Navegación", ["Cuidado (Dashboard)", "Configuración"], index=0)
    st.caption("Demo multimodal: voz (stub), botones, sensores simulados.")

if page.startswith("Cuidado"):
    render_dashboard()
else:
    render_config()
