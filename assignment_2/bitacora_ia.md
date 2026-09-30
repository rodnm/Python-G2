# Bitácora de uso de IA

**Assignment 2 — Temporada: 1 de enero al 31 de mayo de 2023**

Herramienta usada: Claude Code (modelos Sonnet 5 y Opus 5).

Este archivo registra los momentos en que la IA entregó código o afirmaciones **incorrectas, incompletas o que no funcionaron**, cómo los detectamos y cómo los corregimos. Todos los casos son reales y verificables contra el historial de commits y las salidas de los notebooks.

Un patrón se repitió en casi todas las entradas y vale decirlo al principio: **el código generado por IA casi nunca fallaba con un error visible**. Terminaba, imprimía un mensaje de éxito y entregaba datos silenciosamente incorrectos. Encontrar eso obligó a re-ejecutar y comparar resultados, no a leer el código buscando errores de sintaxis.

---

# Parte 1 — Scraping de decretos de emergencia

Notebook: `01_scraping_emergencias.ipynb`

---

## Entrada 1 — La pausa entre pedidos quedó fuera del bucle

**1. ¿Qué le pedimos a la IA?**

Que implementara el paso 9 de la consigna: visitar la página de cada decreto con `requests` y `BeautifulSoup` para obtener el título completo, con una pausa de 1 segundo entre páginas.

**2. ¿Qué respondió?**

```python
# Obtenemos el título completo de cada decreto
print("Obteniendo títulos completos...")
df_pcm["titulo_completo"] = df_pcm["enlace"].apply(obtener_titulo_completo)

# Pausa entre pedidos
time.sleep(PAUSA_REQUESTS)
```

Y dentro de `obtener_titulo_completo`, un `try/except` que ante cualquier fallo imprimía el error y devolvía `None`.

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

El `time.sleep(PAUSA_REQUESTS)` está **después** del `.apply()`, no dentro. O sea que hacía las 49 peticiones seguidas, sin ninguna pausa, y después dormía 1 segundo una sola vez. La consigna pedía exactamente lo contrario, y la propia celda de texto del notebook explicaba por qué hay que pausar.

La consecuencia no fue un error visible. Fue peor: gob.pe cortó dos conexiones por timeout, `obtener_titulo_completo` devolvió `None` para esos dos decretos, y como el resto del notebook clasifica y detecta departamentos a partir del título completo, esos dos decretos **desaparecieron de todo el análisis**. El notebook terminó imprimiendo `✓ Parte 1 completada exitosamente`.

Lo detectamos al ejecutar el notebook dos veces y comparar los CSV generados. Los números cambiaban entre corridas:

| | Corrida A | Corrida B |
|---|---|---|
| Normas de lluvia | 20 | 19 |
| Lambayeque | 4 | 3 |
| Piura | 4 | 3 |
| Tumbes | 3 | 2 |

Los dos decretos perdidos fueron el `DS N.° 016-2023-PCM` y el `DS N.° 065-2023-PCM`. Un resultado que cambia en cada corrida no es un dato.

**4. ¿Cómo lo corregimos?**

Tres cambios:

- La pausa pasó **dentro** del bucle, reemplazando el `.apply()` por un `for` explícito.
- `obtener_titulo_completo` ahora reintenta hasta 4 veces con espera creciente (`PAUSA_REQUESTS * intento`), subió el `timeout` de 10 a 30 segundos y agregó `raise_for_status()` para no tragarse respuestas HTTP con error.
- Se capturan solo `requests.RequestException`, no cualquier excepción.

Verificación: dos corridas completas seguidas producen ahora CSV **byte a byte idénticos**, y la celda reporta `Títulos obtenidos: 49 de 49`.

---

## Entrada 2 — Explicación del `robots.txt` que contradecía la salida ya impresa

**1. ¿Qué le pedimos a la IA?**

Que escribiera la celda de texto del paso 1: explicar qué prohíbe el `robots.txt` de gob.pe, si `/busquedas` está permitida y por qué conviene pausar, fijándose en el `Crawl-delay` que el archivo le pide a otros bots.

**2. ¿Qué respondió?**

> "**¿Qué prohíbe?** El robots.txt de gob.pe no prohíbe explícitamente la ruta `/busquedas`. No hay reglas `Disallow` que bloqueen el acceso a la página de búsquedas.
>
> **¿Por qué igual conviene hacer pausas?** Aunque **no haya un `Crawl-delay` específico** para nuestro bot, hacer pausas de al menos 2 segundos entre páginas es una buena práctica..."

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

Nos dimos cuenta leyendo la salida de la celda **anterior**, que imprime el `robots.txt` real. El archivo sí trae `Crawl-delay`:

```
User-agent: GPTBot
Crawl-delay: 5
...
User-agent: OAI-SearchBot
Crawl-delay: 2
```

La IA escribió la explicación sin mirar el archivo que el propio notebook acababa de descargar. Dos problemas:

- Afirmó que no había `Crawl-delay`, cuando hay dos, y justamente para bots de IA. Ese dato era el que la consigna pedía usar para justificar la pausa.
- A la pregunta "¿qué prohíbe?" respondió solo qué **no** prohíbe. Nunca mencionó las reglas que el archivo sí tiene: `Disallow: /admin/`, `Disallow: /*?sheet=`, `Disallow: /*&sheet=` para todos los bots, y `Disallow: /` completo para `AhrefsBot`.

**4. ¿Cómo lo corregimos?**

Reescribimos la celda citando el contenido real del archivo: las tres rutas bloqueadas para todos los bots, el bloqueo total a `AhrefsBot`, y los dos `Crawl-delay` de 5 y 2 segundos. Y cambiamos el argumento de fondo: no pausamos "porque es buena práctica" en abstracto, sino porque el propio sitio declara que tolera entre 2 y 5 segundos entre pedidos, y nuestra pausa se justifica con ese número.

---

## Entrada 3 — El código tapaba sus propios fallos

**1. ¿Qué le pedimos a la IA?**

Que implementara el paso 6: la tabla de verificación que compara los resultados extraídos contra el total que declara la página, con la indicación de la consigna de que "si en alguno no coinciden, revisen su código antes de seguir".

**2. ¿Qué respondió?**

```python
if tabla_verificacion["coincide"].all():
    print("✓ Todos los meses coinciden. Podemos continuar.")
else:
    print("✗ Hay meses que no coinciden. Revisar el código antes de continuar.")
```

Y, en la función de scraping, para leer el total de resultados:

```python
try:
    total_elemento = driver.find_element(By.XPATH, "//span[contains(., 'Resultados')]")
    total_texto = total_elemento.text
    total = int(total_texto.split()[0])
except:
    total = 0
```

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

Los dos fragmentos tienen el mismo defecto: **fallan en silencio y dejan seguir al notebook**.

- La verificación solo *imprime* un aviso. Las celdas siguientes se ejecutan igual, con datos incompletos, y al final el notebook declara éxito. Un aviso impreso en la celda 6 de un notebook de 33 celdas no lo va a leer nadie.
- El `except:` pelado deja `total = 0` ante *cualquier* fallo, incluido un cambio de selector en gob.pe. Y con `total = 0`, la comparación `0 == 0` da `True`: la tabla de verificación diría "coincide" habiendo extraído cero resultados. El mecanismo de control se autoanula.

Lo notamos al revisar qué pasaba en el caso de fallo de la Entrada 1: el notebook había perdido dos decretos y aun así imprimió `✓ Parte 1 completada exitosamente`. Ahí quedó claro que ningún control del notebook era capaz de detener nada.

**4. ¿Cómo lo corregimos?**

- La celda de verificación ahora hace `raise RuntimeError` nombrando los meses que no coinciden.
- Después de bajar los títulos, una comprobación nueva lista los decretos sin título y lanza `RuntimeError`, porque sin título completo no se puede clasificar ni detectar departamentos.
- El `except:` pasó a `except Exception` en el bucle de artículos (donde saltear un resultado con formato raro sí es razonable) y se **eliminó** del conteo de totales: si no se puede leer el total, queremos que reviente.
- Se agregó un control extra al armar el CSV por departamento: verifica que `declaratorias + prorrogas` sea igual al total de menciones departamento-decreto, y lanza excepción si no cuadra.

La lección: un error silencioso es peor que uno que revienta. El que revienta se arregla; el silencioso se entrega.

---

## Entrada 4 — Febrero hardcodeado como día 28

**1. ¿Qué le pedimos a la IA?**

Una función que, dado un mes y un año, devolviera el rango de fechas `desde`/`hasta` en formato `DD-MM-AAAA` para armar la URL de búsqueda.

**2. ¿Qué respondió?**

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

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

Lo encontramos leyendo la función, no ejecutándola: en 2023 funciona, porque febrero de 2023 tiene 28 días. Pero el último día de febrero está escrito a mano, y **2024 es bisiesto**. Un grupo con la temporada 2024 perdería silenciosamente todos los decretos publicados el 29 de febrero, sin ningún error.

Es un error que el notebook no puede detectar por sí solo: la tabla de verificación compararía los resultados extraídos contra el total que la página reporta *para ese rango de fechas*, y ambos números coincidirían. El rango es el que está mal.

De paso, la función tampoco tenía `else`: con un mes fuera de 1–5 devolvía `None` en lugar de avisar.

**4. ¿Cómo lo corregimos?**

Reemplazamos los cinco `if` por el cálculo real del último día del mes:

```python
ultimo_dia = calendar.monthrange(año, mes)[1]
return f"01-{mes:02d}-{año}", f"{ultimo_dia}-{mes:02d}-{año}"
```

Además de arreglar el año bisiesto, la función pasó de 13 líneas a 2 y ahora sirve para cualquier mes, no solo para los cinco de nuestra temporada.

---

## Entrada 5 — Diagnóstico equivocado por no verificar

**1. ¿Qué le pedimos a la IA?**

Revisar la calidad de los títulos guardados en `decretos_lluvias.csv`, después de la limpieza con expresiones regulares que quita el texto sobrante (`DS N° ... PDF ... Descargar`).

**2. ¿Qué respondió?**

Que había un bug grave: los títulos estaban cortados a media frase y eso rompía la detección de departamentos. Como evidencia mostró títulos que terminaban así:

```
... de las provincias de Nasca, Ica y Palpa del departamento de
```

Y el diagnóstico: el `re.sub(r"\s*DS\s+N[°º].*$", "", titulo, flags=re.IGNORECASE | re.DOTALL)` estaba comiéndose parte del título legítimo. Si el título terminaba en `"del departamento de"`, el nombre del departamento se perdía y ese departamento no se contaba.

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

**El diagnóstico era falso.** Antes de tocar la expresión regular, comparamos el título guardado contra el HTML real de la página del decreto:

```
GUARDADO: 'Decreto Supremo que declara el Estado de Emergencia en algunos distritos
de las provincias de Leoncio Prado y Marañón del departamento de Huánuco; y, en
algunos distritos de las provincias de Nasca, Ica y Palpa del departamento de Ica,
por impacto de daños a consecuencia de intensas precipitaciones pluviales'

RAW:      '...intensas precipitaciones pluvialesDS N° 044-2023-PCMPDF2 MB\n\n\nDescargar'
```

El título guardado estaba **completo**, y la limpieza había funcionado perfectamente. El recorte venía de un `[:230]` en el `print` que la propia IA había usado para inspeccionar los datos. Se equivocó leyendo su propia salida de depuración y construyó un diagnóstico entero sobre eso.

**4. ¿Cómo lo corregimos?**

No había nada que corregir en el código: la expresión regular quedó como estaba. Lo que corregimos fue el proceso. Si hubiéramos aceptado el diagnóstico, habríamos reescrito una limpieza que funcionaba bien y probablemente introducido un bug real donde no había ninguno.

El decreto que usamos para verificar terminó siendo útil por otro motivo: el `DS N.° 044-2023-PCM` nombra Ica dos veces, como provincia y como departamento, y es justo el ejemplo que la consigna pide para explicar cómo evitamos el doble conteo. Quedó documentado en el notebook.

---

## Entrada 6 — La IA sobrescribió una celda de código con texto

**1. ¿Qué le pedimos a la IA?**

Reescribir la celda de texto que explica cómo evitamos contar mal los departamentos, para incluir un ejemplo real de nuestra temporada.

**2. ¿Qué respondió?**

Editó el notebook y reportó el cambio como exitoso.

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

Escribió el texto en la celda equivocada: **reemplazó la celda de código** que contenía la función `detectar_departamentos` y el armado de `df_departamentos`. La celda quedó marcada como código, pero con texto Markdown dentro. La celda de texto original siguió ahí, sin cambios.

Lo detectamos al re-ejecutar el notebook completo, que falló así:

```
Cell In[12], line 5
    **Riesgo 1 — falso positivo: `"ica"` vive dentro de `"Huancavelica"`.**
               ^
SyntaxError: invalid character '—' (U+2014)
```

Si nos hubiéramos confiado del reporte de éxito de la IA sin re-ejecutar, habríamos entregado un notebook que no corre y sin la función que calcula el archivo de salida principal. Es exactamente el escenario que la consigna advierte.

**4. ¿Cómo lo corregimos?**

Listamos el índice completo del notebook con `nbformat` para ver el tipo y el contenido real de cada celda, confirmamos qué se había perdido, restauramos el código de `detectar_departamentos` en su celda, pusimos el texto nuevo en la celda de texto correcta y movimos la sección de limitaciones al final, después del guardado de archivos. Después volvimos a ejecutar el notebook de principio a fin y verificamos que las 14 celdas de código tuvieran `execution_count` no nulo y cero salidas de error.

---

## Verificación final de la Parte 1

No alcanzaba con que el notebook corriera. Los controles que quedaron en el entregable:

1. Las 14 celdas de código ejecutadas, sin ninguna salida de error.
2. Tabla de verificación con `coincide == True` en los 5 meses (11, 9, 14, 11 y 8 resultados).
3. `Títulos obtenidos: 49 de 49`.
4. `declaratorias + prorrogas` = 78 = total de menciones departamento-decreto.
5. **Dos corridas completas seguidas producen CSV idénticos.** Es la prueba de que el problema de la Entrada 1 está resuelto: mientras existía, cada corrida daba números distintos.
