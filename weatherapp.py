# app.py
# City Guide • WeatherAPI + Google Gemini (LangChain) • Streamlit

import os
import requests
import streamlit as st
from typing import Optional

# ------------------------------
# Gemini availability check
# ------------------------------
LLM_AVAILABLE = True
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    LLM_AVAILABLE = False

# ------------------------------
# Page setup + CSS
# ------------------------------
st.set_page_config(
    page_title="Gemini Weather + Travel Guide",
    page_icon="🌤️",
    layout="wide"
)

st.markdown("""
<style>
.header {
  background: linear-gradient(90deg, #4f46e5, #06b6d4);
  padding: 22px 26px; border-radius: 18px; color: white; margin-bottom: 18px;
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
}
.header h1 {margin: 0; font-weight: 800; letter-spacing: .3px;}
.header p {margin: 6px 0 0; opacity: .9}

.card {
  border-radius: 18px; padding: 18px; background: #ffffff;
  border: 1px solid #eef2ff;
  box-shadow: 0 6px 20px rgba(79,70,229,.08);
}

.badge {
  display:inline-block; padding: 4px 10px; border-radius: 999px;
  background:#eef2ff; color:#4f46e5; font-size: 12px; font-weight:600;
}

.stButton>button {
  border-radius: 12px; padding: 10px 16px; font-weight: 700;
}

.block-container {padding-top: 1.2rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
  <h1>🌤️ Gemini Weather + Travel Guide</h1>
  <p>Enter a city to get live weather and a Gemini-powered attraction list tailored to current conditions.</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------
# Helpers
# ------------------------------
@st.cache_data(show_spinner=False, ttl=300)
def fetch_weather(city: str, api_key: str) -> Optional[dict]:
    try:
        url = "http://api.weatherapi.com/v1/current.json"
        params = {"key": api_key, "q": city, "aqi": "no"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if "current" in data and "location" in data else None
    except Exception as e:
        return {"error": str(e)}

def build_weather_summary(data: dict) -> str:
    loc = data["location"]
    cur = data["current"]
    cond = cur["condition"]["text"]
    return (
        f"Location: {loc['name']}, {loc['country']}. "
        f"Condition: {cond}. Temp: {cur['temp_c']}°C (feels {cur['feelslike_c']}°C). "
        f"Wind: {cur['wind_kph']} kph. Humidity: {cur['humidity']}%."
    )

def get_attractions_md(city: str, weather_summary: str, google_key: str) -> str:
    if not LLM_AVAILABLE:
        return "⚠️ Gemini package not installed. Run: `pip install langchain-google-genai`"

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        google_api_key=google_key,
    )
    prompt = (
        f"You are a concise local guide.\n"
        f"City: {city}\n"
        f"Weather now: {weather_summary}\n\n"
        f"Task: List 10 top attractions in {city}. "
        f"For each, provide <= 20 words and say if it's ideal given the weather "
        f"(e.g., 'great in sunshine', 'indoor-friendly today'). "
        f"Return a Markdown bullet list with **bold** attraction names."
    )
    try:
        return (llm.invoke(prompt).content or "No response.")
    except Exception as e:
        return f"⚠️ Gemini call failed: {e}"

# ------------------------------
# Sidebar — USER MUST ENTER BOTH KEYS
# ------------------------------
with st.sidebar:
    st.subheader("API Keys (Required)")
    google_key = st.text_input("Google Gemini API Key", value="", type="password")
    weather_key = st.text_input("WeatherAPI Key", value="", type="password")
    st.caption("These keys are required. We do not store them anywhere.")

# ------------------------------
# Main UI
# ------------------------------
left, mid, right = st.columns([2,1,1])
with left:
    city = st.text_input("City Name", value="Paris", placeholder="e.g., Tokyo")

with mid:
    units = st.selectbox("Units", ["Metric (°C, kph)"], index=0, disabled=True)

with right:
    go = st.button("✨ Generate Travel Guide", use_container_width=True)

# ------------------------------
# Action
# ------------------------------
if go:

    if not google_key.strip():
        st.error("Please enter your Google Gemini API key.")
        st.stop()

    if not weather_key.strip():
        st.error("Please enter your WeatherAPI key.")
        st.stop()

    with st.spinner("Fetching live weather..."):
        data = fetch_weather(city, weather_key)

    if not data or data.get("error"):
        st.error(f"Could not fetch weather. {data.get('error', 'Check city or API key.')}")
        st.stop()

    cur = data["current"]
    loc = data["location"]

    # Weather Card
    st.markdown(f"""
    <div class="card">
      <div style="display:flex; gap:18px; align-items:center;">
        <img src="https:{cur['condition']['icon']}" width="72">
        <div>
          <div class="badge">{cur['condition']['text']}</div>
          <h3 style="margin:6px 0 0">{loc['name']}, {loc['country']}</h3>
          <div style="opacity:.7">Local time: {loc['localtime']}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temperature", f"{cur['temp_c']:.1f} °C", f"Feels {cur['feelslike_c']:.1f}")
    c2.metric("Humidity", f"{cur['humidity']} %")
    c3.metric("Wind", f"{cur['wind_kph']} kph")
    c4.metric("Pressure", f"{cur.get('pressure_mb', '—')} mb")

    tab_weather, tab_attractions, tab_map, tab_json = st.tabs(
        ["🌦️ Weather details", "🏛️ Top attractions", "🗺️ Map", "🧾 Raw JSON"]
    )

    with tab_weather:
        st.write(f"**Cloud**: {cur.get('cloud', '—')}%  |  "
                 f"**UV**: {cur.get('uv', '—')}  |  "
                 f"**Visibility**: {cur.get('vis_km', '—')} km  |  "
                 f"**Wind dir**: {cur.get('wind_dir','—')}")
        st.progress(min(100, int(cur.get('humidity', 0))), text="Humidity")

    with tab_attractions:
        with st.spinner("Asking Gemini for an up-to-date list…"):
            weather_summary = build_weather_summary(data)
            md = get_attractions_md(city, weather_summary, google_key)
        st.markdown(md)

    with tab_map:
        st.caption("Approximate city location")
        st.map({"lat": [loc["lat"]], "lon": [loc["lon"]]}, zoom=10)

    with tab_json:
        st.json(data)

    st.success("Done! Try another city.")

else:
    st.info("Enter a city, add your API keys, then click **Generate Travel Guide**.")

st.caption("Built with Streamlit • Google Gemini • WeatherAPI")
