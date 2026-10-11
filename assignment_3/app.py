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

st.dataframe(df_filtrado)