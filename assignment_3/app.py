from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Emergencies and rainfall 2023", layout="wide")

# Path relative to this file, so it works on any computer and on Streamlit Cloud
RUTA = Path(__file__).parent / "datos" / "tabla_final.csv"


@st.cache_data
def cargar_datos(ruta):
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"ubigeo": str})
    df["ubigeo"] = df["ubigeo"].str.zfill(2)
    return df


tabla = cargar_datos(RUTA)

st.title("Does the State declare emergencies where it rains the most?")

st.sidebar.header("Filters")

departamentos = st.sidebar.multiselect(
    "Department",
    options=sorted(tabla["departamento"].unique()),
    default=sorted(tabla["departamento"].unique()),
)

rango_decl = st.sidebar.slider(
    "Emergency declarations",
    int(tabla["declaratorias"].min()), int(tabla["declaratorias"].max()),
    (int(tabla["declaratorias"].min()), int(tabla["declaratorias"].max())),
)

df_filtrado = tabla[
    tabla["departamento"].isin(departamentos)
    & tabla["declaratorias"].between(*rango_decl)
]

if df_filtrado.empty:
    st.warning("No department matches the filters.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Departments", len(df_filtrado))
col2.metric("Total declarations", int(df_filtrado["declaratorias"].sum()))
col3.metric("Average rainfall (mm)", f"{df_filtrado['lluvia_total_mm'].mean():,.1f}")
col4.metric("Avg. days of heavy rain", f"{df_filtrado['dias_lluvia_fuerte'].mean():.1f}")

st.subheader("Filtered data")
st.dataframe(df_filtrado, width="stretch", hide_index=True)

st.download_button(
    label="Download filtered data (CSV)",
    data=df_filtrado.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_data.csv",
    mime="text/csv",
)

st.caption("Source: PCM emergency decrees (gob.pe) and Open-Meteo, Jan-May 2023. Own elaboration.")