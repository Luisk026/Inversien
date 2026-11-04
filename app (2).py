import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# -----------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------
st.set_page_config(
    page_title="Inversien | Observatorio Financiero",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
.stApp {background-color: #0b1220; color: #f1f5f9;}
[data-testid="stSidebar"] {background-color: #111c2e;}
h1, h2, h3 {color: #55d6be;}
.metric-card {
    background: #142238;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #263b56;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 INVERSIEN")
st.caption("OBSERVATORIO FINANCIERO | Análisis de mercados e indicadores")

# -----------------------------------
# PANEL LATERAL
# -----------------------------------
st.sidebar.title("⚙️ Configuración")

activos_texto = st.sidebar.text_input(
    "Símbolos de activos (separados por coma)",
    value="AAPL, MSFT, GOOGL"
)

activos = [
    x.strip().upper()
    for x in activos_texto.split(",")
    if x.strip()
]

periodo = st.sidebar.selectbox(
    "Periodo de consulta",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=3
)

frecuencia = st.sidebar.selectbox(
    "Frecuencia",
    ["Diaria", "Semanal"],
    index=0
)

# -----------------------------------
# DESCARGA DE INFORMACIÓN
# -----------------------------------
@st.cache_data(ttl=300)
def descargar_datos(simbolos, periodo, frecuencia):
    intervalo = "1d" if frecuencia == "Diaria" else "1wk"

    datos = yf.download(
        tickers=simbolos,
        period=periodo,
        interval=intervalo,
        auto_adjust=True,
        progress=False
    )

    if datos.empty:
        return pd.DataFrame()

    if isinstance(datos.columns, pd.MultiIndex):
        precios = datos["Close"].copy()
    else:
        precios = datos[["Close"]].copy()
        precios.columns = simbolos[:1]

    if isinstance(precios, pd.Series):
        precios = precios.to_frame()

    precios = precios.dropna(how="all")
    return precios

if not activos:
    st.warning("Escribe al menos un símbolo financiero en el panel lateral.")
    st.stop()

with st.spinner("Consultando información de Yahoo Finance..."):
    precios = descargar_datos(activos, periodo, frecuencia)

if precios.empty:
    st.error("No fue posible descargar información. Revisa los símbolos e inténtalo de nuevo.")
    st.stop()

# -----------------------------------
# CÁLCULOS FINANCIEROS
# -----------------------------------
rendimientos = precios.pct_change().dropna()
rendimiento_acumulado = (1 + rendimientos).cumprod() - 1
volatilidad = rendimientos.std() * np.sqrt(252 if frecuencia == "Diaria" else 52)
drawdown = (precios / precios.cummax()) - 1

# -----------------------------------
# RESUMEN GENERAL
# -----------------------------------
st.subheader("Resumen del mercado")

columnas = st.columns(len(precios.columns))

for columna, activo in zip(columnas, precios.columns):
    serie = precios[activo].dropna()

    if len(serie) >= 2:
        cambio = ((serie.iloc[-1] / serie.iloc[0]) - 1) * 100
        columna.metric(
            label=activo,
            value=f"{serie.iloc[-1]:,.2f}",
            delta=f"{cambio:.2f}% en el periodo"
        )

st.caption(
    "Fuente: Yahoo Finance. Datos históricos descargados al momento de la consulta; "
    "pueden presentar retrasos y no representan necesariamente cotizaciones en tiempo real."
)

# -----------------------------------
# SECCIONES DE LA PLATAFORMA
# -----------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Precios",
    "📈 Rendimientos",
    "⚠️ Riesgo",
    "🔗 Correlación"
])

# TAB 1: PRECIOS
with tab1:
    st.subheader("Evolución histórica de los activos")

    figura = px.line(
        precios,
        x=precios.index,
        y=precios.columns,
        labels={"value": "Precio", "variable": "Activo", "x": "Fecha"},
        template="plotly_dark"
    )
    figura.update_layout(
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        legend_title="Activos"
    )
    st.plotly_chart(figura, use_container_width=True)

    st.subheader("Datos consultados")
    st.dataframe(precios.tail(10), use_container_width=True)

# TAB 2: RENDIMIENTOS
with tab2:
    st.subheader("Rendimientos diarios o semanales")

    figura_r = px.line(
        rendimientos * 100,
        labels={"value": "Rendimiento (%)", "variable": "Activo"},
        template="plotly_dark"
    )
    figura_r.update_layout(
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220"
    )
    st.plotly_chart(figura_r, use_container_width=True)

    st.subheader("Rendimiento acumulado")

    figura_a = px.line(
        rendimiento_acumulado * 100,
        labels={"value": "Rendimiento acumulado (%)", "variable": "Activo"},
        template="plotly_dark"
    )
    st.plotly_chart(figura_a, use_container_width=True)

    st.subheader("Resumen de rendimientos")
    resumen = pd.DataFrame({
        "Rendimiento promedio (%)": rendimientos.mean() * 100,
        "Rendimiento acumulado (%)": rendimiento_acumulado.iloc[-1] * 100
    })
    st.dataframe(resumen.round(2), use_container_width=True)

# TAB 3: RIESGO
with tab3:
    st.subheader("Indicadores de riesgo")

    st.markdown("**Volatilidad anualizada**")
    st.caption("Mide cuánto varían los rendimientos. Una volatilidad mayor suele indicar mayor variabilidad.")

    st.dataframe(
        (volatilidad * 100).rename("Volatilidad anualizada (%)").to_frame().round(2),
        use_container_width=True
    )

    st.markdown("**Drawdown: caída desde el máximo histórico**")
    st.caption("Muestra cuánto ha caído el precio desde su máximo anterior.")

    figura_d = px.area(
        drawdown * 100,
        labels={"value": "Caída desde máximo (%)", "variable": "Activo"},
        template="plotly_dark"
    )
    st.plotly_chart(figura_d, use_container_width=True)

    max_drawdown = drawdown.min() * 100
    st.markdown("**Máxima caída observada en el periodo**")
    st.dataframe(
        max_drawdown.rename("Máximo drawdown (%)").to_frame().round(2),
        use_container_width=True
    )

# TAB 4: CORRELACIÓN
with tab4:
    st.subheader("Relación entre los activos")
    st.caption("La correlación mide qué tan relacionados se mueven dos activos.")

    if rendimientos.shape[1] >= 2:
        matriz = rendimientos.corr()

        figura_c = px.imshow(
            matriz,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1,
            template="plotly_dark"
        )
        st.plotly_chart(figura_c, use_container_width=True)
        st.dataframe(matriz.round(3), use_container_width=True)
    else:
        st.info("Agrega al menos dos activos para calcular la correlación.")

# -----------------------------------
# PIE DE PÁGINA
# -----------------------------------
st.divider()
st.markdown(
    "© 2026 **Inversien** | Herramienta académica de análisis financiero"
)
st.caption("La información presentada es educativa y no constituye asesoría de inversión.")
