# Sección 18 — Bootstrap real de Ā (por vivienda)

## El problema
En la sección 16.3 del notebook principal el "bootstrap" tenía el error estándar **escrito a mano** (`se_abar = 0.38`) y el intervalo de confianza era simplemente `14,57 ± 1,96 × 0,38 = [13,82 ; 15,31]`. **No había remuestreo**, aunque el texto decía "1.000 remuestreos sobre las 35 bases". Esta sección lo calcula de verdad.

## Qué es un bootstrap (en simple)
Ā sale de una muestra (la EPH). Si el INDEC hubiera sorteado otra muestra, Ā daría un número un poco distinto. El **error estándar (SE)** dice cuánto. No podemos volver a sortear la EPH, así que la **simulamos**: armamos muestras nuevas sacando datos *con reposición* de la que tenemos, y en cada una **repetimos todo el cálculo** (logit cohorte + edad, extrapolación de cohortes, Ā). La dispersión de esos 1.000 valores de Ā es el SE; los percentiles 2,5 y 97,5 son el IC de 95 %.

## Qué hicimos
* **Se remuestrean viviendas, no personas.** La EPH rota (2 trimestres adentro, 2 afuera, 2 adentro), así que las mismas personas aparecen en varios trimestres: el 83 % de las viviendas figura en más de un trimestre. Esas filas no son independientes. Por eso la unidad es la vivienda (`CODUSU`), con pesos multinomiales.
* **Se reajusta todo el pipeline en cada réplica**, para las tres reglas de independientes (`solo_asalariados`, `pp07i`, `indep50`). El resultado puntual del módulo coincide exactamente con `abar_eph_por_cohorte.csv`.
* B = 1.000 réplicas, semilla fija `20260507` (reproducible). Tarda ~12 s (B = 4.000: ~57 s). Los SE casi no cambian con B = 500, 1.000 o 4.000 ni con otra semilla (±0,02).
* Código: `src/tbp_bootstrap.py`; fragmento de Colab: `notebooks/fragmentos/seccion_17_bootstrap_abar.ipynb`; resultados: `datos/procesados/abar_bootstrap_ic.csv` (todas las cohortes 1950-2035 y las tres reglas).

## Resultado (regla `solo_asalariados`)

| Cohorte | Ā | SE real | IC 95 % | ± % | % de Ā en edades observadas |
|---|---|---|---|---|---|
| 1960 | 14,51 | 0,60 | [13,35 ; 15,70] | 8,1 | 12 |
| 1980 | 16,16 | 0,35 | [15,45 ; 16,87] | 4,4 | 24 |
| 2000 | 13,24 | 0,57 | [12,13 ; 14,35] | 8,4 | 9 |
| **2024** | **14,57** | **0,60** | **[13,43 ; 15,78]** | **8,1** | 0 (extrapolada) |

**Comparación con 16.3 (cohorte 2024):** SE real 0,60 contra 0,38 escrito a mano (**1,6 veces mayor**); IC real [13,43 ; 15,78] (± 8,1 %) contra [13,82 ; 15,31] (± 5,1 %). El "±5 %" **no se sostiene**. En términos de TBP_C (proporcional a Ā con el resto fijo): ± 8 %, p. ej. TBP_C p4 de 2024 = 0,191 con IC [0,176 ; 0,207] (aprox.). Con las otras reglas el SE de 2024 es 0,63 (`pp07i`) y 0,55 (`indep50`).

**Bootstrap ingenuo (por fila):** da SE = 0,45 para 2024 (25 % menos que el real) y entre 25 % y 33 % menos según cohorte y regla. Ignorar que las viviendas se repiten achica artificialmente la incertidumbre. (Notar que el 0,38 estaba por debajo incluso de ese valor ingenuo.) Remuestrear dentro de cada aglomerado sube el SE apenas 2-5 %.

**Cuánto es dato y cuánto extrapolación.** Sólo 0-24 % de Ā proviene de edades realmente observadas de la cohorte; el resto es el perfil por edad común del modelo. La cohorte 2024 no tiene ninguna edad observada: su nivel es el promedio de las cohortes 2001-2005, vistas sólo a los 18-20 años.

## Qué se puede y qué no afirmar
* **Se puede:** el error muestral de Ā (solo asalariados, las 86 cohortes) tiene mediana 0,57 años y va de 0,35 a ~1,1 (margen de 95 %: ± 4 % a ± 14 %, mediana ± 8 %); en la cohorte 2024 es ± 8 %. No es 0,38 ni ± 5 %.
* **No se puede:** decir que este IC es "la incertidumbre de Ā" o de TBP_C. Es **sólo variabilidad muestral**, con un diseño simplificado (viviendas como unidad, ponderadores fijos, sin estrato/UPM del INDEC). **No capta error de modelo:** perfil por edad común a todas las cohortes, confusión período/cohorte, extrapolación de cohortes jóvenes y futuras, EPH urbana, `PP07H` de la semana de referencia, reglas para independientes (por eso hay tres), S65 y Gompertz tratados como exactos. Tampoco incluye la incertidumbre de N, τ, ρ y J (eso es el Monte Carlo de 16.4).
* Una variante de modelo (extrapolar por tendencia en vez de "últimas 5 cohortes") mueve Ā 2024 apenas +0,23 años: es un solo ejemplo, no una cota del error de modelo.
