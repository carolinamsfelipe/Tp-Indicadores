# Sección 16 — Validación no econométrica: Sensibilidad, Descomposición, Bootstrap y Monte Carlo

Notebook: `notebooks/TBP_Argentina_Series_Reales.ipynb` (sección 16). Código auxiliar: `consultas_profesor/validacion_tbp.py` y `consultas_profesor/generar_graficos_validacion.py`. Documento formal: `consultas_profesor/TBP_Informe_Validacion_Metodologica.docx`. Salidas: `salidas_tbp/seccion_16_*.png` y `monte_carlo_resumen_2024.csv`.

## 1. Justificación epistemológica: ¿Por qué no hay regresión econométrica ($R^2$, $p$-valores)?

* **Identidad contable vs. modelo estocástico:** En una regresión ($Y = \beta X + \varepsilon$) se modela una conducta humana no observada con residuo aleatorio $\varepsilon$, y se usan $p$-valores para testear la hipótesis nula ($H_0: \beta = 0$). El TBP es una **identidad contable determinística**:
  $$TBP_C(t) = \frac{N_t \cdot (1-\mu) \cdot \bar{A} \cdot \tau}{J^* \cdot \rho}$$
  Dados los nacimientos, la supervivencia, los años de aporte y los jubilados, el valor surge por cálculo aritmético directo. No hay residuo $\varepsilon$, no se estiman coeficientes por MCO y no hay hipótesis de que un parámetro sea cero. Exigir un $p$-valor para el TBP equivaldría a exigirlo para la identidad del PBI ($Y = C + I + G + XN$).
* **Estándar científico internacional:** Siguiendo la metodología de las Cuentas Generacionales del NBER (Auerbach/Kotlikoff) y las razones de dependencia de Naciones Unidas, las identidades estructurales se validan mediante: (1) Sensibilidad y elasticidades; (2) Descomposición contable y de varianza; (3) Bootstrap sobre variables muestrales; y (4) Simulación estocástica conjunta de Monte Carlo.

## 2. Pilar 1: Análisis de Sensibilidad y Elasticidades (Tornado)

* **Elasticidades analíticas:** $\varepsilon(N)=+1$, $\varepsilon(\bar{A})=+1$, $\varepsilon(\tau)=+1$, $\varepsilon(J^*)=-1$, $\varepsilon(\rho)=-1$.
* **Estática comparativa (Cohorte 2024, Base = 0,191 años):**
  * $\bar{A}$ con 50 % de independientes: $+61,9\,\%$ ($0,309$ años).
  * $\tau$ alícuota 27 % (público): $+24,0\,\%$ ($0,237$ años).
  * $\bar{A}$ regla PP07I: $+22,3\,\%$ ($0,233$ años).
  * $J = 65+$ (sin $J^*$): $+8,3\,\%$ ($0,207$ años).
  * $\tau = 23,35\,\%$ (inciso b): $+7,3\,\%$ ($0,205$ años).
  * $\tau$ efectiva SIPA ($18,3\,\%$): $-16,0\,\%$ ($0,160$ años).
  * Moratorias caen a la mitad ($\rho = 48,3\,\%$): $-16,6\,\%$ ($0,159$ años).
  * Moratorias desaparecen ($\rho = 56,3\,\%$): $-28,4\,\%$ ($0,137$ años).
* **Conclusión:** Ningún cambio razonable de supuestos altera el diagnóstico: en todos los casos la cohorte 2024 financia menos de 4 meses de prestación ($0,14$ a $0,31$ años).

## 3. Pilar 2: Descomposición Contable y de Varianza (Campbell-Shiller)

* **Descomposición de la caída 2000 $\to$ 2024 (caída neta de $-38,9\,\%$, $\Delta \ln TBP_C = -0,4925$):**
  * **Natalidad ($N$):** explica el **$+107,6\,\%$** de la caída neta (supera el 100 % porque debió contrarrestar las leves mejoras en supervivencia y aportes).
  * **Jubilados ($J^*$):** explica el **$+21,5\,\%$**.
  * **Supervivencia ($S_{65}$):** aporta **$-10,1\,\%$** (amortiguador).
  * **Aportes EPH ($\bar{A}$):** aporta **$-19,0\,\%$** (amortiguador).
* **Descomposición de varianza interanual (2000–2024):** la covarianza de los nacimientos con el índice explica el **$85,2\,\%$ de la varianza total** de las variaciones del $TBP_C$.

## 4. Pilar 3: Variabilidad Muestral y Bootstrap para $\bar{A}$ (EPH)

* La única variable con diseño muestral probabilístico es $\bar{A}$ (EPH INDEC).
* Con 1.000 remuestreos bootstrap sobre las 35 bases trimestrales (2017-T2 a 2025-T4), el error estándar muestral de $\bar{A}$ (asalariados) es $\approx 0,38$ años, arrojando un intervalo de confianza al 95 % de $[13,82 ; 15,31]$ años.
* Trasladado al $TBP_C$, el error muestral traslada una banda de apenas **$\pm 5,1\,\%$** ($[0,181 ; 0,201]$ años).
* **Conclusión:** El error de muestreo no compromete los resultados. La verdadera incertidumbre es de definición institucional (independientes).

## 5. Pilar 4: Simulación Conjunta de Monte Carlo (10.000 iteraciones)

* Sorteo simultáneo de $N$ (Normal $\pm 1,5\,\%$), $\bar{A}$ (Triangular $[13,5 ; 15,5 ; 23,6]$), $\tau$ (Uniforme $[18,3\,\% ; 23,35\,\%]$), $\rho$ (Triangular $[37,1\,\% ; 40,3\,\% ; 56,3\,\%]$) y $J^*$ (Normal $\pm 1\,\%$).
* **Distribución simulada de la cohorte 2024:**
  * Estimación puntual base: $0,191$ años
  * Mediana (P50): $0,201$ años
  * Banda intercuartil 50 % (P25 - P75): $[0,179 ; 0,226]$ años
  * Banda del 90 % (P5 - P95): $[0,152 ; 0,269]$ años
* **La Prueba de Oro:** Aun en el Percentil 95 más optimista ($0,269$ años), el indicador de la cohorte 2024 queda significativamente por debajo del valor registrado por la cohorte 2000 ($0,312$ años). La probabilidad de que 2024 iguale a 2000 es prácticamente nula ($p < 0,001$).
