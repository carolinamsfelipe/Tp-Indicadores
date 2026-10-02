# Sensibilidad por bandas de Ā (Opción 1)

Notebook: `notebooks/TBP_Sensibilidad_A.ipynb`. Salidas: `datos/procesados/tbp_sensibilidad_A.csv` y `datos/procesados/tbp_sensibilidad_A.png`.

## Qué se hizo

Ā es el número promedio de años de aporte. Hoy tiene dos escenarios: 14,2 (observado ANSES, sesgado a la baja porque ANSES cuenta aportes solo desde jul-1994 y a personas con al menos 12 meses de aporte) y 30 (requisito legal de referencia: es el mínimo para jubilarse, no un máximo). En vez de elegir uno, corrimos el modelo para Ā ∈ {15, 20, 25, 30} y graficamos la banda min–max con una línea por escenario, para TBP_C (versión recomendada) y TBP_A. τ = 0,2177 y ρ = 0,403 siguen constantes. Todo sale del CSV de cohortes; no se agregó ningún dato.

## Por qué

No sabemos dónde está el Ā verdadero, y mostrar un solo valor da una falsa precisión. La banda lo hace explícito sin tener que resolver el problema antes de presentar.

## Qué muestra: Ā mueve el nivel, no la historia

El TBP es lineal en Ā: TBP(t; Ā) = Ā · k(t), donde k(t) no depende de Ā. Entonces el cociente entre dos cohortes, TBP(t)/TBP(s) = k(t)/k(s), no depende de Ā. Por eso el índice normalizado (cohorte 1950 = 100) es idéntico en los cuatro escenarios (el panel derecho del gráfico muestra cuatro curvas superpuestas), y el notebook lo verifica con asserts (TBP(2Ā) = 2·TBP(Ā); índice igual entre escenarios; reproducción de las columnas `_obs` y `_legal` del CSV).

Resultado: la caída relativa entre cohortes, los puntos de inflexión y las tendencias son robustos a Ā. Solo cambia el nivel, con un factor 2 entre Ā = 15 y Ā = 30.

Valores de TBP_C (años), del CSV:

| Cohorte | Ā=15 | Ā=20 | Ā=25 | Ā=30 |
|---|---|---|---|---|
| 2000 | 0,406 | 0,541 | 0,676 | 0,811 |
| 2010 | 0,405 | 0,540 | 0,675 | 0,810 |
| 2024 | 0,216 | 0,289 | 0,361 | 0,433 |

Índice (1950 = 100): 75,1 en 2000, 75,0 en 2010 y 40,1 en 2024, para cualquier Ā.

## Qué NO muestra

- **No resuelve el sesgo de Ā.** Es un parche útil para presentar, no una estimación. La grilla 15/20/25/30 es ilustrativa: la banda no es un intervalo de confianza ni una distribución de probabilidad.
- **No dice nada sobre el nivel "correcto".** Tampoco se interpreta TBP = 1 como umbral fiscal.
- **El rebote posterior a 2024 es un artefacto.** Desde la cohorte 2025, N_t es proyección ONU (~507 mil nacimientos en 2024 contra ~413 mil observados por DEIS), no dato. La línea vertical 2024/2025 marca el corte.
- No captura que Ā pueda variar entre cohortes: acá es una constante.

## Conexión con las otras opciones

- **Opción 2 (calibración con EPH):** apunta a achicar la banda estimando Ā con datos de historias laborales. Si funciona, se elige un valor (o un rango acotado) dentro de 15–30.
- **Opción 3 (Ā_t dinámico):** deja que Ā cambie por cohorte. Es la única que puede alterar la forma de la curva, porque rompe la linealidad con constante que explica este hallazgo. La Opción 1 sigue sirviendo como referencia: lo que cambie la forma en la Opción 3 se debe a Ā_t y no a la escala.
