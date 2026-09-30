# AI usage log

**Assignment 2 — Season: January 1 to May 31, 2023**

Tool used: Claude Code (Sonnet 5 and Opus 5 models).

This file records the moments when the AI produced code or claims that were **wrong, incomplete, or simply did not work**, how we caught them, and how we fixed them. Every case is real and can be checked against the commit history and the notebook outputs.

One pattern showed up in almost every entry, and it is worth stating up front: **the AI-generated code almost never failed with a visible error**. It finished, printed a success message, and handed back data that was quietly incorrect. Finding those required re-running the notebook and comparing results, not reading the code looking for syntax mistakes.

A note on language: prose, comments and identifiers in this project are in English. Column names, category values, file names and the scraped decree records stay in Spanish, because the assignment specifies them literally and Parts 2 and 3 join on them. A decree title is the legal name of a document published by the Peruvian government, so translating it would falsify the data rather than localize it.

---

# Part 1 — Scraping emergency decrees

Notebook: `01_scraping_emergencias.ipynb`

---

## Entry 1 — The pause between requests ended up outside the loop

**1. What we asked the AI for**

To implement step 9 of the assignment: visit each decree page with `requests` and BeautifulSoup to get the full title, pausing one second between pages.

**2. What it answered**

```python
# Obtenemos el título completo de cada decreto
print("Obteniendo títulos completos...")
df_pcm["titulo_completo"] = df_pcm["enlace"].apply(obtener_titulo_completo)

# Pausa entre pedidos
time.sleep(PAUSA_REQUESTS)
```

And inside the fetching function, a `try/except` that printed the error and returned `None` on any failure.

**3. What was wrong, and how we noticed**

The `time.sleep` call sits **after** the `.apply()`, not inside it. So the code fired all 49 requests back to back with no pause at all, and then slept one second once. The assignment asked for the opposite, and the notebook's own text cell explained why pausing matters.

The consequence was not a visible error. It was worse: gob.pe dropped two connections on timeout, the fetch function returned `None` for those two decrees, and since every later step classifies and detects departments from the full title, those two decrees **disappeared from the entire analysis**. The notebook still finished by printing a success message.

We caught it by running the notebook twice and comparing the generated CSVs. The numbers changed between runs:

| | Run A | Run B |
|---|---|---|
| Rainfall regulations | 20 | 19 |
| Lambayeque | 4 | 3 |
| Piura | 4 | 3 |
| Tumbes | 3 | 2 |

The two lost decrees were `DS N.° 016-2023-PCM` and `DS N.° 065-2023-PCM`. A result that changes on every run is not data.

**4. How we fixed it**

Three changes:

- The pause moved **inside** the loop, replacing the `.apply()` with an explicit `for`.
- The fetch function now retries up to 4 times with a growing wait (`REQUEST_PAUSE * attempt`), raised the timeout from 10 to 30 seconds, and calls `raise_for_status()` so failing HTTP responses are not swallowed.
- Only `requests.RequestException` is caught, instead of every exception.

Verification: two consecutive full runs now produce **byte-identical** CSVs, and the cell reports `Titles fetched: 49 of 49`.

---

## Entry 2 — A robots.txt explanation that contradicted the output printed right above it

**1. What we asked the AI for**

To write the text cell for step 1: explain what the gob.pe `robots.txt` forbids, whether `/busquedas` is allowed, and why pausing is a good idea anyway, paying attention to the `Crawl-delay` the file asks of other bots.

**2. What it answered**

> "**What does it forbid?** The gob.pe robots.txt does not explicitly forbid the `/busquedas` path. There are no `Disallow` rules blocking access to the search page.
>
> **Why pause anyway?** Even though **there is no specific `Crawl-delay`** for our bot, pausing at least 2 seconds between pages is good practice..."

**3. What was wrong, and how we noticed**

We noticed by reading the output of the **previous** cell, which prints the actual `robots.txt`. The file does contain `Crawl-delay` directives:

```
User-agent: GPTBot
Crawl-delay: 5
...
User-agent: OAI-SearchBot
Crawl-delay: 2
```

The AI wrote the explanation without looking at the file the notebook had just downloaded. Two problems:

- It claimed there was no `Crawl-delay` when there are two, and specifically for AI crawlers. That was exactly the fact the assignment asked us to use to justify our pause.
- Asked "what does it forbid?", it only answered what it does **not** forbid. It never mentioned the rules the file actually has: `Disallow: /admin/`, `Disallow: /*?sheet=` and `Disallow: /*&sheet=` for every bot, plus a full `Disallow: /` for `AhrefsBot`.

**4. How we fixed it**

We rewrote the cell quoting the real contents: the three blocked paths, the full block on `AhrefsBot`, and the two `Crawl-delay` values of 5 and 2 seconds. We also changed the underlying argument. We do not pause because "it is good practice" in the abstract, but because the site itself states it tolerates something between 2 and 5 seconds between requests, and our pause is justified by that number.

---

## Entry 3 — The code covered up its own failures

**1. What we asked the AI for**

To implement step 6: the verification table comparing extracted results against the total the page reports, following the assignment's instruction that "if any month does not match, review your code before continuing".

**2. What it answered**

```python
if tabla_verificacion["coincide"].all():
    print("✓ Todos los meses coinciden. Podemos continuar.")
else:
    print("✗ Hay meses que no coinciden. Revisar el código antes de continuar.")
```

And, inside the scraping function, to read the result count:

```python
try:
    total_elemento = driver.find_element(By.XPATH, "//span[contains(., 'Resultados')]")
    total_texto = total_elemento.text
    total = int(total_texto.split()[0])
except:
    total = 0
```

**3. What was wrong, and how we noticed**

Both fragments share the same defect: **they fail silently and let the notebook keep going**.

- The verification only *prints* a warning. Every later cell runs anyway, on incomplete data, and the notebook ends by declaring success. A warning printed in cell 6 of a 33-cell notebook is a warning nobody will read.
- The bare `except` leaves `total = 0` on *any* failure, including a selector change on gob.pe. And with `total = 0`, the comparison `0 == 0` evaluates to `True`: the verification table would report a match while having extracted zero results. The safety check cancels itself out.

We noticed while investigating the failure from Entry 1: the notebook had lost two decrees and still printed its success message. That made it clear no check in the notebook was capable of stopping anything.

**4. How we fixed it**

- The verification cell now raises `RuntimeError`, naming the months that do not match.
- After fetching the titles, a new check lists the decrees with no title and raises, because without the full title we cannot classify a decree or detect its departments.
- The bare `except` became `except Exception` in the article loop, where skipping a malformed result is reasonable, and was **removed** from the result-count read: if the total cannot be parsed, we want it to blow up.
- We added one more check when building the per-department CSV: it verifies that `declaratorias + prorrogas` equals the total number of department-decree mentions, and raises if it does not.

The lesson: a silent error is worse than one that crashes. The one that crashes gets fixed; the silent one gets submitted.

---

## Entry 4 — February hardcoded as day 28

**1. What we asked the AI for**

A function that, given a month and a year, returns the `desde`/`hasta` date range in `DD-MM-YYYY` format to build the search URL.

**2. What it answered**

```python
def obtener_rango_fechas(mes, año):
    if mes == 1:
        return f"01-01-{año}", f"31-01-{año}"
    elif mes == 2:
        return f"01-02-{año}", f"28-02-{año}"
    elif mes == 3:
        return f"01-03-{año}", f"31-03-{año}"
    ...
```

**3. What was wrong, and how we noticed**

We found this by reading the function, not by running it. It works for 2023, because February 2023 has 28 days. But the last day of February is written by hand, and **2024 is a leap year**. A group working the 2024 season would silently lose every decree published on February 29, with no error at all.

This is a bug the notebook cannot detect on its own: the verification table would compare extracted results against the total the page reports *for that date range*, and both numbers would match. The range itself is what is wrong.

The function also had no `else`: given a month outside 1 to 5 it returned `None` instead of complaining.

**4. How we fixed it**

We replaced the five `if` branches with the actual last day of the month:

```python
last_day = calendar.monthrange(year, month)[1]
return f"01-{month:02d}-{year}", f"{last_day}-{month:02d}-{year}"
```

Besides fixing the leap year, the function went from 13 lines to 2 and now works for any month, not just the five in our season.

---

## Entry 5 — A wrong diagnosis, from not verifying

**1. What we asked the AI for**

To review the quality of the titles stored in `decretos_lluvias.csv`, after the regex cleanup that strips the trailing boilerplate (`DS N° ... PDF ... Descargar`).

**2. What it answered**

That there was a serious bug: the titles were being cut off mid-sentence, which broke department detection. As evidence it showed titles ending like this:

```
... de las provincias de Nasca, Ica y Palpa del departamento de
```

And the diagnosis: `re.sub(r"\s*DS\s+N[°º].*$", "", title, flags=re.IGNORECASE | re.DOTALL)` was eating part of the legitimate title. If a title ended in `"del departamento de"`, the department name was lost and that department went uncounted.

**3. What was wrong, and how we noticed**

**The diagnosis was false.** Before touching the regex, we compared the stored title against the real HTML of the decree page:

```
STORED: 'Decreto Supremo que declara el Estado de Emergencia en algunos distritos
de las provincias de Leoncio Prado y Marañón del departamento de Huánuco; y, en
algunos distritos de las provincias de Nasca, Ica y Palpa del departamento de Ica,
por impacto de daños a consecuencia de intensas precipitaciones pluviales'

RAW:    '...intensas precipitaciones pluvialesDS N° 044-2023-PCMPDF2 MB\n\n\nDescargar'
```

The stored title was **complete**, and the cleanup had worked exactly as intended. The truncation came from a `[:230]` slice in the AI's own debugging `print`. It misread its own diagnostic output and built an entire diagnosis on top of it.

**4. How we fixed it**

There was nothing to fix in the code: the regex stayed as it was. What we fixed was the process. Had we accepted the diagnosis, we would have rewritten a cleanup that worked fine and probably introduced a real bug where there was none.

The decree we used to check turned out useful for another reason: `DS N.° 044-2023-PCM` names Ica twice, as a province and as a department, and it is exactly the example the assignment asks for when explaining how we avoid double counting. It is now documented in the notebook.

---

## Entry 6 — The AI overwrote a code cell with prose

**1. What we asked the AI for**

To rewrite the text cell explaining how we avoid miscounting departments, so it would include a real example from our season.

**2. What it answered**

It edited the notebook and reported the change as successful.

**3. What was wrong, and how we noticed**

It wrote the prose into the wrong cell: it **replaced the code cell** holding the `detectar_departamentos` function and the construction of the per-department table. The cell stayed marked as code but contained Markdown text. The original text cell was still there, untouched.

We caught it by re-running the whole notebook, which failed like this:

```
Cell In[12], line 5
    **Riesgo 1 — falso positivo: `"ica"` vive dentro de `"Huancavelica"`.**
               ^
SyntaxError: invalid character '—' (U+2014)
```

Had we trusted the AI's success report without re-running, we would have submitted a notebook that does not run and that is missing the function computing the main output file. That is exactly the scenario the assignment warns about.

**4. How we fixed it**

We listed the notebook's full cell index with `nbformat` to see the real type and content of every cell, confirmed what had been lost, restored the detection code in its own cell, put the new prose in the correct text cell, and moved the limitations section to the end, after the file-saving step. Then we re-ran the notebook from top to bottom and checked that every code cell had a non-null `execution_count` and zero error outputs.

---

## Entry 7 — Stripping accents would have silently zeroed five departments

**1. What we asked the AI for**

To write the department names without accents in the output data, so Part 3 can join tables without name mismatches.

**2. What it answered**

The obvious move: rewrite the `DEPARTMENTS` list without accents.

```python
DEPARTMENTS = [
    "Amazonas", "Ancash", "Apurimac", ..., "Huanuco", ..., "Junin", ..., "San Martin", ...
]
```

**3. What was wrong, and how we noticed**

That change alone would have destroyed the data, without any error message. Detection searches each department name inside the decree title, and **gob.pe writes the accented spelling**. Searching `Ancash` against a title containing `Áncash` matches nothing.

We measured it before applying the change, against the 20 rainfall decrees of the season:

| Department | Accented, in titles | Plain, in titles |
|---|---|---|
| Áncash | 7 | 0 |
| Huánuco | 4 | 0 |
| San Martín | 4 | 0 |
| Junín | 2 | 0 |
| Apurímac | 1 | 0 |

Eighteen department-decree mentions would have vanished. Ancash, the second most affected department of the season, would have reported 0 declarations. Nothing would have crashed, and the CSV would have looked perfectly normal.

**4. How we fixed it**

We separated the two concerns. The accent-free name is what gets **stored**; the accents are stripped from the **title** before searching, with a `strip_accents` helper built on `unicodedata`:

```python
def strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
```

There was a second trap in the same change. Unicode normalization also turns `ñ` into `n`, so applying `strip_accents` to the classification step would convert `daños` into `danos` and break the `impacto de daños` test. The stripping is therefore scoped to department detection only, and section 10 of the notebook states why.

Verification: a dedicated cell now prints, for each accented name, how many titles contain it and how many the accent-free name ends up counting. They match (7 and 7, 4 and 4, and so on), and the total stayed at 78 department-decree mentions.

---

## Final verification of Part 1

It was not enough for the notebook to run. These are the checks that stayed in the deliverable:

1. All 14 code cells executed, with no error output.
2. Verification table with `coincide == True` for all 5 months (11, 9, 14, 11 and 8 results).
3. `Titles fetched: 49 of 49`.
4. `declaratorias + prorrogas` = 78 = total department-decree mentions.
5. Every accented department name in the titles is counted under its accent-free name, one to one.
6. **Two consecutive full runs produce identical CSVs.** This is the proof that the problem from Entry 1 is resolved: while it existed, every run produced different numbers.

---

# Part 2 — Rainfall API

Notebook: `api_lluvias.ipynb`

---

## Entry 8 — The AI told us to keep the accents that Part 1 had removed

**1. What we asked the AI for**

A step-by-step guide to build the capitals table from Wikipedia and save `lluvias_por_departamento.csv`, so that Part 3 could later join it with the Part 1 tables.

**2. What it answered**

> "Es importante que los nombres de `departamento` usen las mismas tildes que la lista de la Parte 1 ("Áncash", "Apurímac", "Junín", "Huánuco", "San Martín"), porque @RenatoGates va a pegar el ubigeo por nombre. Si Wikipedia los trae distinto, corrígelos antes de guardar."

It also suggested a normalization step that mapped every Wikipedia name back to its **accented** spelling.

**3. What was wrong, and how we noticed**

The AI assumed Part 1 kept the accents. It did not. When we read the final Part 1 notebook, the `DEPARTMENTS` list is written **without** accents (`Ancash`, `Apurimac`, `Huanuco`, `Junin`, `San Martin`), and `decretos_por_departamento.csv` stores the names that way (see Entry 7).

Following the advice would have produced two different spellings for 5 of the 25 departments: `Áncash` in our CSV and `Ancash` in the Part 1 CSV. Nothing would have crashed. The mismatch would only have shown up in Part 3, when adding the ubigeo or joining the tables, and it would have looked like missing data rather than a naming problem.

**4. How we fixed it**

We stopped relying on the AI's description of Part 1 and reused its code directly: the exact same `DEPARTMENTS` list and the same `strip_accents` function. We applied `strip_accents` to the department names coming from Wikipedia, and added a check that stops the notebook unless the set of names is **exactly** `DEPARTMENTS`:

```python
print("Missing:", set(DEPARTMENTS) - set(capitals["departamento"]))
print("Extra:  ", set(capitals["departamento"]) - set(DEPARTMENTS))
if len(capitals) != 25 or set(capitals["departamento"]) != set(DEPARTMENTS):
    raise RuntimeError("The capitals table does not have the 25 expected departments.")
```

The output shows `Missing: set()` and `Extra: set()`, so the names match Part 1 one to one.

---

## Final verification of Part 2

1. The notebook runs from top to bottom after restarting the kernel, with no error output.
2. Capitals table: 25 rows (24 departments from Wikipedia's main table plus Callao from the special-regime table on the same page), with names identical to Part 1.
3. Geocoding: all 25 results have `country_code == "PE"`, `admin1` matches the department in all 25 rows, and every coordinate falls inside Peru's latitude/longitude range. Ayacucho, Ica and Lima each returned 10 places with only one in Peru.
4. Rainfall: all 25 departments received 151 days (January 1 to May 31, 2023) and **0 days came back as `None`**.
5. `datos/lluvias_por_departamento.csv` saved with 25 rows and the 6 columns the assignment asks for.