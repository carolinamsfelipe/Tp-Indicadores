# Sección 20 — Backtest de insumos y estabilidad temporal

Notebook: `notebooks/fragmentos/seccion_20_backtest_estabilidad.ipynb`. Módulo: `src/tbp_estabilidad.py` (con autotest sintético). Salidas: `datos/procesados/backtest_insumos.csv`, `estabilidad_ventanas.csv` (y de apoyo `estabilidad_quiebre.csv`, `backtest_bandas_montecarlo.csv`) y tres PNG `seccion_20_*.png`.

## 1. La idea en simple

El $TBP_C$ es una **cuenta** (identidad contable): nacimientos × supervivencia × años de aporte × (alícuota/ρ) ÷ jubilados. No hay una variable "resultado" que se observe después, así que **no existe** un "fuera de muestra" para el índice. Lo que sí se puede validar es: (A) cuánto se equivocaron proyecciones *pasadas* de los **insumos** (nacimientos $N$ y jubilados $J$) y (B) si el "motor" de la serie cambia con el tiempo.

## 2. Por qué el test IS/OOS existente (corte 2011) no es lo que parece

1. **No hay resultado observado**, y los TBP de las cohortes 2011-2024 usan $J$, $E_r$, $S_{65}$, $
ho$ proyectados a 2076-2089: "OOS" es una etiqueta de calendario.
2. **Los $p$-valores no tienen lectura inferencial**: serie determinística, suave y autocorrelada (con permutación por bloques el $p$ del sup-F pasa de 0,0005 a 0,43-0,62).
3. **El corte 2011 es arbitrario**: nacimientos DEIS con pico en 2014 y caída desde 2015; el estadístico es casi plano entre 2013 y 2018.
4. **El "look-ahead bias" está mal planteado**: no se ajustó nada a una trayectoria de déficit. El problema real es el **anacronismo** (parámetros de 2017-2025 aplicados a cohortes lejanas) y la estabilidad estructural supuesta.

## 3. Resultados

**Backtest de insumos (error % = proyectado/observado − 1; positivo = sobrestimó)**

* Nacimientos, ONU WPP 2024 vs DEIS: 2022 +0,2 %; **2023 +9,3 %; 2024 +22,6 %** (RMSE de los dos años: 17,3 %). Salvedad: DEIS 2024 puede ser provisorio.
* Población total, INDEC 2013 vs Censo 2022 (12 años): **+0,6 %** (+0,1 % contra la estimación INDEC a fecha censal). Acertó el total; no prueba que acertara $N$ y 65+ por separado.
* INDEC 2013 vs INDEC 2025 (revisión, no error): +2,3 % (2025), +5,7 % (2030), +8,6 % (2035), +11,1 % (2040).
* 65+ ONU WPP 2024 vs Censo 2022: −0,8 % (WPP 2024 no incorpora el censo); vs INDEC 2025, 2022-2040: −0,7 % a −2,5 %, RMSE 1,5 %.
* Cifras del censo y de INDEC 2025: PDF `datos_tbp/indec_proyecciones_nacionales_2022_2040.pdf`, p. 12 (Tabla 1: 45.892.285), p. 19 (Tabla 4: 65+ censada 5.464.057; estimada a fecha censal 46.122.853 y 5.521.560), pp. 39-42 (Cuadro 2.1).

**Banda de incertidumbre para el Monte Carlo (reemplaza ±1,5 % en $N$ y ±1 % en $J$):** $\sigma_J$ ≈ 1,5 % (RMSE entre fuentes; variante creciente con √horizonte, supuesto heurístico) y, para cohortes ≥ 2025, $\sigma_N$ ≈ 17 % (RMSE del backtest, solo 2 puntos). Cohorte 2024: P5-P95 prácticamente igual (0,152-0,269 → 0,152-0,271). Cohorte 2030: de 0,167-0,294 a 0,142-0,324, y la probabilidad de superar a la cohorte 2000 (0,312) sube de 2,0 % a ≈ 6,7-6,9 %. $J$ de cohortes ≤ 2024 corresponde a gente ya nacida: el error de $N$ no entra ahí.

**Ventanas móviles de 20 cohortes (1950-2024)**: en todas las ventanas que terminan hasta 2020 el principal freno es **$J$** (−1,7 a −2,1 pp de ln TBP por cohorte hasta 1989; −0,8 en 2001-2020); $N$ empuja hacia arriba (hasta +2,2 pp). **$N$ pasa a ser el motor recién en ventanas que terminan en 2021-2024** (2005-2024: $N$ −2,5 pp, $J$ −0,35). No se verifica que "desde ~2000 domine $N$". Entre 1974 y 2005 $ar A$ es el segundo freno (hasta −1,3 pp). Media de la ventana: 0,46 (1970-1989) → 0,30 (2005-2024).

**Quiebre (sup-F, cortes 2000-2018)**: máximo en **2015** (p4: F = 9,37; p1: 9,10; nacimientos: 168); el F de 2011 es 8,40 (se reproduce el 8,3972 del test existente). Meseta 2013-2018. Con permutación por bloques el $p$ del sup-F de TBP es 0,43-0,62 (nacimientos ≈ 0,003); el Wald-HAC da 0,005-0,06 según serie y bloque. **Sale:** la pendiente cambia hacia 2014-2015 por $N$. **No sale:** un "quiebre estructural significativo" en 2011 ni en otra fecha. Todo es **descriptivo**.

## 4. Qué sirve validar y qué no



## 5. Qué habría que descargar (NO se descargó; tamaños por cabeceras HTTP)



## 6. Límites

Faltan los vintages previos para medir cómo crece el error con el horizonte; $\sigma_N$ sale de 2 observaciones; el escalamiento por horizonte es un supuesto; DEIS 2024 puede ser provisorio. Observación sobre 16.5: con los parámetros de 16.4 la probabilidad de que la cohorte 2024 supere a la 2000 es ≈ 0,3 % (no "< 0,1 %"); la conclusión cualitativa no cambia.
