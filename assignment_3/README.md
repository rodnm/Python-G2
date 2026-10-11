# Assignment 3: Does the State declare emergencies where it rains the most?

Interactive dashboard, charts and maps for Group 02 (Fundamentos de Python, Diplomado PUCP). It studies the rainy season of 2023 (January 1 to May 31) in Peru, department by department.

**Public dashboard:** _the link is added here right after the deployment_

## 1. Question

Does the State declare emergencies where it rains the most? The dashboard compares, for the 25 departments, the rainfall recorded during the season with the number of emergency declarations each one received. Filters in the sidebar (departments and a range of declarations) update the metrics, the three charts, the map and the table at the same time.

## 2. Data

- **Emergency declarations:** the legal norms of the Presidency of the Council of Ministers (PCM) published on gob.pe, scraped in Assignment 2. A decree usually covers several departments, so the 20 decrees of the season become 72 department-level declarations.
- **Rainfall:** total millimeters and days with 20 mm or more, from the Open-Meteo historical weather API, measured at the capital of each department.
- **Final table:** `datos/tabla_final.csv`, one row per department, built in Assignment 2. The `ubigeo` is read as text so it keeps its leading zero.
- **Decrees:** `datos/decretos_lluvias.csv`, the 20 decrees with their publication date and reason (used in `visualizacion.ipynb`).
- **Boundaries:** `datos/departamentos_peru.geojson`, joined to the table by `ubigeo`. The file only has department names, so each name was normalized (capital letters, no accent marks) just to assign its `ubigeo`, and the join was verified: all 25 departments matched.

## 3. Two findings

1. **More rain did not mean more declarations.** The correlation between total rainfall and declarations is r = -0.22, weak and slightly negative. The three rainiest departments, Loreto (1,605 mm), Ucayali (1,316 mm) and Madre de Dios (1,248 mm), received 1, 3 and 0 declarations, while Lima, with 55 mm, received 6. Six departments had more rain than the median (714 mm) but fewer declarations than the median (3): Loreto, Madre de Dios, Tumbes, Junín, Pasco and Apurímac.
2. **The gap follows a regional pattern.** The wettest class of the rainfall map (more than 1,000 mm) is the Amazon (Loreto, Ucayali, Madre de Dios and San Martín) plus Áncash, while the darkest class of the declarations map (5 or 6) is on the coast and in the Andes (Lima, La Libertad, Áncash and Ayacucho). The coast is not uniform either: Lima, Callao, Ica, Moquegua and Tacna recorded less than 120 mm, but Tumbes and Piura, in the north, recorded 931 and 719 mm.

The notebooks add a third result: only 3 of the 20 decrees were issued for imminent danger, before the damage, and 15 were issued after it.

## 4. Limitations

- **Rainfall is measured at one point per department, its capital.** On a map the color extends that value to the whole department. For example, Áncash looks rainy because of Huaraz, in the Andes, although it also includes a stretch of the arid coast. Open-Meteo values are modeled, not weather-station readings.
- **We cannot measure how long the State took to declare an emergency.** Assignment 2 stored only the season total of rainfall, not daily values, and the date of a decree is its publication date.
- **A declaration is counted once per department and decree.** It shows how often a department appeared in decrees, not how much damage it suffered or how large the response was.
- **Small sample.** There are 25 departments and a single season, so r = -0.22 is not evidence of cause and effect.
- **Choropleth maps give more visual weight to large departments.** The Amazon dominates the image, while Lima and Callao, with much of the population, are barely visible.

## Files

| File | What it is |
|---|---|
| `app.py` | Streamlit dashboard: filters, metrics, charts, map and table |
| `visualizacion.ipynb` | Part 1: three Plotly charts, check of extreme values, `grafico.html` and two extra analyses |
| `mapas.ipynb` | Part 2: join by `ubigeo`, two static choropleth maps and an interactive Folium map |
| `requirements.txt` | Pinned dependencies (Python 3.12 or newer) |
| `datos/` | Data used by the notebooks and the dashboard |

## Run it locally

From the root of the repository, the same way Streamlit Community Cloud runs it (so the theme in `.streamlit/config.toml` is applied):

```bash
pip install -r assignment_3/requirements.txt
streamlit run assignment_3/app.py
```

To rerun the notebooks with static PNG charts, also install `kaleido` (it needs Google Chrome). Without it the notebooks still run, with interactive charts only.
