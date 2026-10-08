# Sección 17 — Validación Temporal y Estabilidad Empírica: Pseudo In-Sample vs. Out-of-Sample

Notebook: `notebooks/TBP_Argentina_Series_Reales.ipynb` (sección 17). Script ejecutable: `consultas_profesor/validacion_temporal_is_oos.py`. Salidas: `consultas_profesor/temporal_is_oos_resumen.csv` y `consultas_profesor/graficos/grafico5_validacion_temporal_is_oos.png`.

## 1. Justificación metodológica: Blindaje contra el sesgo retrospectivo (*Look-Ahead Bias*)

En el diseño de indicadores cuantitativos existe el riesgo de **sobreajuste retrospectivo** (*data snooping*): calibrar o defender parámetros conociendo previamente la contracción reciente del sistema. Para auditar la estabilidad temporal del indicador y demostrar que su alerta no es un artificio de calibración, se aplicó una partición temporal en dos ventanas:

* **Ventana In-Sample (IS: 1950–2010, N = 61 cohortes):** Etapa de transición demográfica estable y bono demográfico pleno. En esta etapa la natalidad creció o se mantuvo en meseta y el envejecimiento poblacional avanzó a ritmo pausado.
* **Ventana Out-of-Sample (OOS: 2011–2024, N = 14 cohortes):** Etapa contemporánea de quiebre estructural de natalidad (caída de la Tasa Global de Fecundidad del 34 % entre 2014 y 2020 documentada por Rofman et al., 2022).

## 2. Métricas Comparativas IS vs. OOS

| Métrica Cuantitativa | In-Sample (IS: 1950–2010) | Out-of-Sample (OOS: 2011–2024) | Variación Relativa |
| :--- | :--- | :--- | :--- |
| **Tamaño de muestra ($N$)** | 61 cohortes | 14 cohortes | — |
| **Media ($TBP_C$)** | **0,4012 años** (4,8 meses de haber) | **0,2863 años** (3,4 meses de haber) | **−28,64 %** (degradación media) |
| **Desvío estándar ($\sigma$)** | 0,0591 años | 0,0547 años | — |
| **Rango [Mínimo ; Máximo]** | [0,3039 ; 0,5126] años | [0,1908 ; 0,3440] años | Mínimo absoluto en 2024 |
| **Valores Punta a Punta** | 0,4479 (1950) $\to$ 0,3408 (2010) | 0,3408 (2011) $\to$ **0,1908 (2024)** | **−44,04 %** en 14 años |
| **Pendiente tendencial** | **−0,19 p.p. / año** (−0,00188) | **−1,24 p.p. / año** (−0,01240) | **Aceleración de 6,6x** |

## 3. Pruebas de Quiebre Estructural (Test de Chow / $F$-test)

Para contrastar formalmente si el comportamiento post-2010 responde a una oscilación transitoria o a un cambio de régimen estructural, se computó el **Test de Chow** comparando el modelo lineal conjunto (*pooled*) frente a modelos particionados antes y después del quiebre:

* **Corte 2011 (Inicio OOS):**
  * $F$-stat = **8,397** | $p$-valor = **$5,33 \times 10^{-4}$** ($p < 0,001$).
  * Se rechaza la hipótesis nula de estabilidad de parámetros al **99,9 % de confianza**.
* **Corte 2014 (Aceleración del shock de fecundidad):**
  * $F$-stat = **9,342** | $p$-valor = **$2,50 \times 10^{-4}$** ($p < 0,001$).
  * Pendiente post-2014: **−1,62 p.p. / año** $\to$ la velocidad de caída se multiplica por **8,5 veces** respecto de la trayectoria histórica previa a 2010.

## 4. Brecha Contrafáctica OOS: ¿Qué habría pasado sin el colapso de natalidad?

Extrapolando la tendencia observada en la ventana In-Sample (1950–2010) hacia 2024:
* **$TBP_C$ contrafáctico proyectado para 2024:** **0,3184 años** (~3,8 meses de haber).
* **$TBP_C$ real observado en 2024:** **0,1908 años** (~2,3 meses de haber).
* **Brecha neta por shock de fecundidad:** **−40,09 %** (−0,1276 años de haber por jubilado).

## 5. Conclusión para la Defensa Oral y Evaluadores

El análisis temporal confirma que el indicador se comporta como un **detector temprano de quiebre de régimen**: permaneció estable durante seis décadas de transición demográfica gradual, y reaccionó con una contracción del 44 % ante el colapso contemporáneo de nacimientos. La brecha contrafáctica demuestra que el 40 % de la pérdida de soporte intergeneracional actual es directamente imputable al shock demográfico reciente.
