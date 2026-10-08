# Sección 19 — Monte Carlo riguroso: comparación pareada, cohortes futuras y varianza por parámetro

Código: `src/tbp_montecarlo.py` (autotest: `python src/tbp_montecarlo.py`). Colab: `notebooks/fragmentos/seccion_19_montecarlo_riguroso.ipynb`. Salidas: `datos/procesados/montecarlo_*.csv` y `seccion_19_*.png`. Reemplaza el diseño de la Sección 16.4 (la 16 no se modificó).

## 1. Idea en cinco líneas
El indicador es $TBP_C=\dfrac{N\,S_{65}\,\bar A\,\tau}{J^*\,\rho}$. Simulamos 20.000 "versiones del mundo" (semilla 42) moviendo las entradas y miramos cuánto se mueve el resultado. Lo importante es **qué se mueve junto**: $\tau$, $\rho$ y la regla de $\bar A$ son los mismos para todas las cohortes, así que **se comparan cohortes con los mismos sorteos** (comparación *pareada*).

## 2. Tres tipos de incertidumbre (no se mezclan sin avisar)
| Capa | Qué es | Entradas | De dónde sale |
|---|---|---|---|
| **Muestral** | Error de muestreo de la EPH | $\bar A$ | Bootstrap real `abar_bootstrap_ic.csv` (**todavía no existe: capa en cero, rotulada**; el módulo lo lee solo cuando aparezca) |
| **Medición** | Dos fuentes que miden lo mismo difieren | $N$ ($\sigma$=2,03 %: desvío de ln(RENAPER/DEIS) 2012–2024, razón 0,979–1,051); $J^*$ ($\sigma$=3,27 %: RMS de $J_{reponderado}/J_{ONU}-1$, 2000–2024) | Archivos del proyecto |
| **Escenario / definición** | No es azar: es una decisión o un supuesto | Regla de $\bar A$ (asalariados / PP07I / indep. 50 %); $\tau$ = 18,3 (supuesto) / 21,77 / 23,35 / 27 %; $\rho$ = 40,3 / 48,3 / 56,3 %; natalidad 2025+ (3 escenarios) | Secciones 9, 12, 13, 15 |

Los escenarios se simulan como categorías con **pesos iguales**: es una convención, **no son probabilidades**. Por eso, además de percentiles, se informa el rango mín–máx.

## 3. Resultados (años de prestación por jubilado)
**Nivel** (base → banda P5–P95; *medición sola* / *conjunta condicional*):
| Cohorte | Base | Solo medición | Conjunta (condicional) |
|---|---|---|---|
| 2000 | 0,312 | [0,293 ; 0,332] | [0,217 ; 0,544] |
| 2024 | 0,191 | [0,179 ; 0,203] | [0,133 ; 0,331] |
| 2030 (persist. / recup. lenta / caída adic.) | 0,209 / 0,231 / 0,194 | — | [0,146 ; 0,362] / [0,161 ; 0,401] / [0,135 ; 0,336] |
| 2035 (persist. / recup. lenta / caída adic.) | 0,222 / 0,271 / 0,208 | — | [0,155 ; 0,385] / [0,189 ; 0,469] / [0,145 ; 0,359] |

**Comparación pareada 2024 vs 2000:** razón base 0,611; P5–P95 = **[0,569 ; 0,656]**; **0 de 20.000** sorteos con razón ≥ 1 (máxima 0,739); el cero de $\ln$(razón) queda a 11 desvíos. En la razón **$\tau$ y $\rho$ se cancelan exactamente** (error numérico 7·10⁻¹⁶); solo cuentan $N$, $S_{65}$, $J^*$ y $\bar A(2024)/\bar A(2000)$. Duplicando $\sigma_N$ y $\sigma_J$ la razón va de 0,53 a 0,70: sigue < 1.

**Tendencia 2000→2024:** pendiente de $\ln TBP_C$ = **−1,73 % anual** (P5–P95: −1,87 a −1,59); ningún sorteo da pendiente ≥ 0.

**Futuro vs 2024** (probabilidad de que sea mayor, condicional): persistencia 2030 98 % / 2035 100 %; recuperación lenta 100 % / 100 % (2035: ×1,42); **caída adicional 65 % (2030) / 97 % (2035)**. En todos los casos y cohortes 2030/2035 el indicador sigue por debajo de la cohorte 2000 (probabilidad ≥ 99,9 %).

**¿Qué parámetro domina?** (% de la varianza, primer orden, en logs)
| Resultado | $\bar A$ regla | $\tau$ | $\rho$ | $J^*$ | $N$ | natalidad |
|---|---|---|---|---|---|---|
| Nivel 2024 | 50,0 | 24,7 | 23,9 | 1,4 | 0,5 | — |
| Nivel 2035 | 43,5 | 21,5 | 20,7 | 1,2 | 0,5 | 14,1 |
| Razón 2024/2000 | 2,1 | **0** | **0** | 55,2 | 42,8 | — |
| Pendiente 2000–24 | 1,3 | **0** | **0** | 56,2 | 42,3 | — |

El **nivel** lo mandan las definiciones y supuestos (≈ 99 % en 2024); la **tendencia**, la demografía medida ($J^*$ y $N$). Son *participaciones*, no tamaños: la varianza de la tendencia es mucho menor que la del nivel.

## 4. Descomposiciones: nombres correctos
* **Descomposición logarítmica exacta** (contabilidad de crecimiento): identidad $\Delta\ln TBP_C=\sum\Delta\ln(\text{factores})$, sin residuo ni orden. *No* es Campbell–Shiller (que descompone retornos con un VAR).
* **Descomposición de varianza por covarianzas** (participación en la covarianza): $\mathrm{Cov}(\Delta x_k,\Delta\ln TBP_C)/\mathrm{Var}(\Delta\ln TBP_C)$; suma 100 % solo con **todos** los componentes. *No* es un $R^2$ (puede ser negativa o > 100 %).
* **84,4 % vs 107,6 %**: son especificaciones distintas, ambas válidas. En puntos log, $N$ aporta lo mismo (−0,530). Con $J$=65+ y $\bar A$ constante la caída total es −0,628 (0,530/0,628 = 84,4 %). Con $J^*$ y $\bar A$ de la EPH (que sube +0,096) la caída es −0,4925 (0,530/0,4925 = 107,6 %). Cambia el **denominador**; no se comparan como porcentajes, sí en puntos log.

## 5. Errores corregidos respecto de la Sección 16
| # | Qué decía | Qué es lo correcto | Cuánto cambia |
|---|---|---|---|
| 1 | "Prueba de oro": 2024 simulado contra 2000 **fijo** (0,312) | Razón **pareada** (mismos sorteos) | Razón [0,57 ; 0,66]; 0 de 20.000 ≥ 1. Sin parear (error): 11,3 % de cruces |
| 2 | "$p<0{,}001$" | No hay $H_0$; frecuencia condicional a supuestos. Ni su propia simulación lo cumplía | 0,32 % (32 de 10.000) superaba 0,312 |
| 3 | $\bar A\sim$ Triangular[13,5; 15,5; 23,6] | Reglas de $\bar A$ = escenario; error muestral = bootstrap (pendiente) | $\bar A$ regla: 50 % de la varianza del nivel, 2 % de la razón |
| 4 | $\rho\sim$ Triangular desde 37,1 % | 3 escenarios de moratorias (40,3/48,3/56,3 %) | $\rho$: 24 % del nivel, 0 % de la razón |
| 5 | $\tau\sim$ Uniforme[18,3; 23,35 %] | 4 escenarios (incluye 27 %) | $\tau$: 25 % del nivel, 0 % de la razón |
| 6 | $N$: ±1,5 % | $\sigma$=2,03 % (RENAPER/DEIS) | Banda de $N$ más ancha |
| 7 | $J^*$: ±1 % sin respaldo | $\sigma$=3,27 % (ONU vs reponderado) | $J^*$ = 56 % de la varianza de la tendencia |
| 8 | Solo cohorte 2024 | 2000, 2024, 2030, 2035 y 3 escenarios de natalidad | Abanico por cohorte |
| 9 | Sin tendencia | Pendiente y razón con abanico | −1,73 %/año [−1,87 ; −1,59] |
| 10 | "Campbell–Shiller" | Log exacta + varianza por covarianzas | Solo el nombre |
| 11 | "85,2 % de la varianza" (N) | Mismo ddof y todos los componentes | **81,6 %**; el 85,2 % mezclaba `np.cov` (ddof=1) y `np.var` (ddof=0): sumaba 104,3 % |
| 12 | "Ā −19,0 %" | Ā más composición por sexo/retiro | Ā −19,5 %; sexo/retiro +0,4 % |
| 13 | Banda 2024 [0,152 ; 0,269] | Condicional [0,133 ; 0,331]; solo medición [0,179 ; 0,203] | Incluye $\tau$=27 % y las 3 reglas de $\bar A$ |

(En 16.1–16.3 el tornado y el $SE=0{,}38$ del bootstrap están escritos a mano en el código; conviene recalcularlos.)

## 6. Qué significa (y qué no)
* **No es un test de hipótesis clásico**: no hay $H_0$, estadístico ni p-valor. El TBP es una identidad contable; se cuantifica **cuánto se mueve el resultado si las entradas se mueven**.
* Es **incertidumbre condicional a los supuestos elegidos**: las bandas conjuntas **no son intervalos de confianza** y los pesos iguales de los escenarios son una convención.
* **Robusto:** la caída 2000→2024 (razón ≈ 0,61) y su tendencia (≈ −1,7 % anual). **No robusto:** el nivel (depende de cómo se defina $\bar A$ y de $\tau$ y $\rho$). **Futuro:** el signo de 2024→2035 depende del escenario de natalidad.

## 7. Límites
Estructura del modelo (sexo y retiro, $S_{65}$ ONU, EPH urbana de asalariados) tomada como dada; $S_{65}$ sin error. Regla de $\bar A$ aplicada como factor sobre el modelo con sexo (aproximación). $\bar A$ de 2024 en adelante es una extrapolación (meseta de densidad): con $\bar A$ constante la razón sería ≈ 0,56. Capa muestral = 0 hasta que exista el bootstrap (con el SE de 2,6 % citado en 16.3, no reproducible, y correlación 0 entre cohortes la razón queda en [0,56 ; 0,67]). Correlaciones entre cohortes ($N$ 0, $J^*$ 0,5, $\bar A$ 1) son supuestos con sensibilidad en `montecarlo_sensibilidad_supuestos.csv`. $\sigma_J$ viene de una discrepancia con signo sistemático (−3,1 %) y se usa solo como escala. $\tau$ efectivo 18,3 % es un supuesto y no hay serie histórica de $\tau$.
