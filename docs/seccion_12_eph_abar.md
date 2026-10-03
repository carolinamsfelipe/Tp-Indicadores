# Sección 12 — Calibración de Ā con microdatos de la EPH (rutina)

**Qué es:** una rutina en Python (`src/tbp_eph.py`, también embebida en la sección 12 del Colab) que lleva el método de la sección 8 a datos reales.

## Flujo
1. **Descarga** de las bases usuarias individuales trimestrales de la EPH (INDEC). Por defecto está en *modo prueba*: lista los archivos y su tamaño y **no descarga nada** hasta que se pone `confirmado=True` / `ACEPTO_DESCARGA = True`.
2. **Filtro:** población 18–64; "registrado" = ocupado asalariado con descuento jubilatorio (`PP07H == 1`). Para cuentapropistas, tres reglas: `solo_asalariados` (cota inferior), `pp07i` y un escenario con proporción supuesta.
3. **Pseudo-panel:** cohorte = `ANO4 − CH06`; densidad de aportes por cohorte × edad; modelo logit aditivo cohorte + edad.
4. **Edad efectiva de ingreso al empleo registrado** (modelada y observada) y **Ā por cohorte**: Ā_c = Σ_{a=18}^{64} S_c(a)·d_c(a).
5. **Conexión con el TBP:** `tbp_con_abar` calcula TBP_C y TBP_A con Ā(t) por cohorte; a diferencia de las bandas de la sección 7, **cambia la forma de la curva**.

## Datos
Bases verificadas (2 oct 2026): `https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_{T}_Trim_{AAAA}_txt.zip`, de **2017-T2 a 2025-T4** (35 archivos, ≈ 107 MB). 2016 y 2017-T1 no están con ese nombre en el sitio actual. Las 35 bases se descargaron y verificaron (firma ZIP, `testzip`) el 3 oct 2026 a `datos/eph/` (ignorada por git).

## Estado y verificación
* Probada con datos **sintéticos** (autotest: pipeline, tres reglas, edad de ingreso, lector de `.txt`/`.zip`, conexión con el TBP; error medio de Ā contra la verdad sintética 0,80 años). **No hay ningún valor de Ā para Argentina todavía.**
* Estructura verificada con las bases reales (ver abajo).

## Límites
EPH urbana y transversal; no observa el primer empleo registrado ni la historia de aportes; `PP07H` mide la semana de referencia; con sólo 9 años de datos cada cohorte se observa en pocas edades y el resto depende del perfil por edad común (período, edad y cohorte no se separan del todo); no hay variable inequívoca de aporte para cuentapropistas; el Ā de la EPH no es comparable uno a uno con el 14,2 de ANSES.


## Resultados con microdatos reales (preliminares)
**No son valores definitivos de Ā.** Son una estimación condicionada a supuestos: pseudo-panel (cohorte = ANO4 − CH06), perfil por edad común a todas las cohortes, EPH urbana, `PP07H` de la semana de referencia, supervivencia Gompertz calibrada a S65.

**Estructura real de las bases (35 trimestres, 2017-T2 a 2025-T4; 1.767.206 filas).** Separador `;`, texto ASCII/UTF-8. Los nombres de los miembros del zip varían (mayúsculas, subcarpetas, `.txt.txt`) y la base individual de 2020-T4 se llama `usu_personas` (el módulo no la encontraba; corregido). Están las 9 variables necesarias en todos los trimestres. `PP07H` y `PP07I` se relevan **sólo a asalariados**; `PP07I` ("¿aporta por sí mismo a algún sistema jubilatorio?") sólo a quienes respondieron `PP07H == 2`. Patrones y cuentapropistas tienen ambas vacías: **la base individual no trae aporte de independientes**. Por eso se corrigió la regla `pp07i` (asalariado con descuento o con aporte propio; antes se aplicaba a independientes y era idéntica a la cota inferior). Entre asalariados ocupados: `PP07H` sí 357.016, no 193.508; `PP07I` sí 21.036, no 170.606, NS/NR 281. `ESTADO`: 0 sin entrevista individual, 1 ocupado, 2 desocupado, 3 inactivo, 4 menor de 10.

**Ā por cohorte** (años; `datos/procesados/abar_eph_por_cohorte.csv`, 86 cohortes 1950-2035):

| Cohorte | Solo asalariados (cota inf.) | + PP07I | Escenario 50 % indep. | Edad ingreso (umbral 50 %) | Edad media ingreso | n edades obs. |
|---|---|---|---|---|---|---|
| 1960 | 14,5 | 14,6 | 17,5 | 23 | 23,8 | 8 |
| 1970 | 15,4 | 15,6 | 18,8 | 23 | 23,7 | 9 |
| 1980 | 16,2 | 17,0 | 20,9 | 23 | 23,6 | 9 |
| 1990 | 15,4 | 17,1 | 21,9 | 23 | 23,7 | 9 |
| 2000 | 13,2 | 16,1 | 21,7 | 23 | 23,9 | 8 |

51 cohortes (1955-2005) tienen al menos 3 edades observadas; 35 son extrapoladas (1950-54 y 2006-2035, con "últimas k"). Aun las cohortes "observadas" se ven en sólo 8-9 de las 47 edades de 18 a 64: el resto sale del perfil por edad común.

**Lectura.** Ā queda lejos de 30 en las tres reglas (máximo ≈ 22 con el escenario del 50 % de independientes). La cota inferior queda cerca del 14,2 de ANSES, pero no es comparable uno a uno: el 14,2 es el promedio de años aportados de los jubilados *nuevos* (los que lograron jubilarse, muchos por moratoria, con historias distintas), mientras que Ā es un promedio sobre *toda la persona de la cohorte* que sobrevive, incluidos quienes nunca aportan, y se proyecta hacia adelante con la densidad actual. La edad de ingreso (≈ 23) es casi constante entre cohortes **por construcción** (perfil por edad común); no es un hallazgo.

**Sensibilidad.**
* `modo_extrap` "ultimas_k" vs "tendencia": no cambia las cohortes con datos propios; en las extrapoladas la diferencia máxima es 0,5 años (cota inferior), 4,5 (pp07i) y 5,9 (escenario 50 %), en 2035.
* Exigir ≥ 5 o ≥ 7 edades observadas en vez de 3: no cambia las cohortes 1960-2000; cambia hasta 1,8-2,1 años en cohortes jóvenes que pasan a extrapolarse.
* Por sexo (cohortes observadas; misma S65 para ambos, sin supervivencia por sexo): varones 16,8-19,0 y mujeres 10,2-14,1 en las cohortes 1955-1990 (cota inferior); la brecha media es de 4,5 años y se achica en las cohortes jóvenes (2000: 13,7 vs 12,9).

**Limitaciones.** Efectos de período (2018-2020, pandemia) se confunden con el efecto de cohorte; las cohortes viejas se observan sólo a los 57-64 años y su historia previa se imputa con el perfil de cohortes más jóvenes (probable sesgo a la baja en cohortes que tuvieron más empleo registrado a edades jóvenes); no hay aporte de independientes en la base; `PP07H` es de la semana de referencia; no se cuentan moratorias ni regímenes provinciales; el error de ±1 año en la cohorte (no hay fecha de nacimiento exacta); la EPH cubre aglomerados urbanos.
