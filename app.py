import json
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


# ==================== Página 2: Dispensador de Medicamentos ====================


def page_dispenser():
st.title("💊 Señalador de Medicamentos (Servo)")


st.write("Selecciona un medicamento y la palanca (servo) **lo señalará** con un ángulo específico. Para el demo usamos 3 medicamentos mapeados a 45°, 90° y 135°.")


# Config sencilla de 3 medicamentos
default_meds = [
{"name": "Med A", "angle": 45},
{"name": "Med B", "angle": 90},
{"name": "Med C", "angle": 135},
]
if 'angle_meds' not in st.session_state:
st.session_state.angle_meds = default_meds


with st.expander("Configurar nombres/ángulos", expanded=False):
for i, m in enumerate(st.session_state.angle_meds):
c1, c2 = st.columns([3,1])
m['name'] = c1.text_input(f"Nombre #{i+1}", value=m['name'], key=f"cfg_name_{i}")
m['angle'] = c2.number_input(f"Ángulo #{i+1}", 0, 180, value=int(m['angle']), key=f"cfg_ang_{i}")
st.caption("Sugeridos: 45°, 90°, 135°")


st.divider()
st.subheader("Señalar medicamento")
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
