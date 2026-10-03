# Sección 9 — Escenario propio de natalidad 2025–2035 (RENAPER + DEIS + INDEC)

## Qué hicimos y por qué
La serie principal del TBP usa, para las cohortes 2025 en adelante, los nacimientos proyectados por la ONU (508 mil en 2025). Ese número genera un rebote artificial: la ONU proyectó 2023 y 2024 antes de tener el dato, y los nacimientos reales (DEIS) fueron 460.902 y 413.135. Los datos más recientes (RENAPER 2025, provisorio) y la TGF observada (~1,04) indican que la caída continúa.

Pasos:
1. **Dato base 2025 (ESTIMACIÓN).** RENAPER 2025 (384.042, provisorio) dividido por la relación RENAPER/DEIS promedio 2022–2024 (0,985): **~390 mil (389.973 con los datos exactos)**. No es un dato oficial.
2. **Tres escenarios de TGF** (propuesta a validar por el grupo): (a) persistencia en 1,04; (b) recuperación lineal a 1,32 en 2035 (valor de la variante media de INDEC); (c) caída a 0,95 en 2028 y estabilización.
3. **Nacimientos:** `N_t = TGF_t × K × M_t / M_2025`, con `K = N_2025 / TGF_2025` y `M_t` = mujeres de 15–49 años (ONU, variante media). Los tres escenarios coinciden en 2025.
4. **TBP:** se recalculan TBP_C y TBP_A de las cohortes 2025–2035 con cada escenario (Ā = 30, que es el requisito legal de referencia y no un máximo, y Ā = 14,2) y se comparan con la serie actual.

Salida: `datos/procesados/natalidad_escenarios_2025_2035.csv` (`anio, escenario, tgf, nacimientos`; incluye `onu_medio` solo con nacimientos e `indec_media_tgf` solo con TGF).

## Resultado principal
Con N propio, el TBP_C de las cohortes recientes queda por debajo de la serie actual en todos los escenarios (cohorte 2025: −23%). Recién la recuperación lenta se acerca a la serie actual hacia 2035. La TGF observada 2025 (~1,04) está por debajo incluso del mínimo de la variante baja de INDEC (1,17).

## Supuestos
- La estructura de edades de la fecundidad no cambia (TGF proporcional a nacimientos por mujeres 15–49).
- La relación RENAPER/DEIS de 2022–2024 se mantiene en 2025.
- Los valores de TGF de cada escenario son hipótesis de trabajo, no pronósticos.

## Limitaciones
- Los datos del RENAPER son los de la descarga CSV del tablero; 2025 es provisorio.
- **J (población 65+) sigue siendo el de la ONU y NO está re-ponderado**; se corrige en la sección 10. El nivel de TBP de las cohortes ≥2025 es parcial.
- INDEC se incluye solo como TGF de referencia (interpolada linealmente entre 2025, 2030 y 2035); no se calculan nacimientos con ella.

## Qué NO se puede afirmar
- Que 390 mil sea el nacimiento oficial 2025.
- Que alguno de los escenarios sea la proyección esperada.
- Que el nivel absoluto del TBP de las cohortes ≥2025 sea definitivo.
