# Metodología: auditoría y supuestos del cálculo real

Nota corta. Estado: en construcción, resultados preliminares.

## 1. Hallazgos de la auditoría de la fórmula

Fórmula original: `TBP(t) = N_t(1−μ)·Ā·τ / (J_{t+65}·E_r·ρ)`.

1. **`ρ` es una tasa de reemplazo adimensional** (haber / salario), no un monto en pesos: no corrige unidades por sí sola.
2. **`J` es un stock que mezcla cohortes:** la población 65+ en `t+65` incluye a varias generaciones, no sólo a la cohorte `t`. Se compara un flujo de una cohorte con un stock de muchas.
3. **La longevidad se cuenta dos veces** en `TBP_A`: entra en `J` (más gente llega y permanece 65+) y en `E_r` (más años cobrando).
4. **Si `J = N(1−μ)` el `N` se cancela:** el indicador deja de depender de la natalidad y queda sólo la cohorte pura (`Ā·τ/(E_r·ρ)`, variante `TBP_B`).
5. **Identidades:** `TBP_A = D × B` (D = factor demográfico `N(1−μ)/J`, B = cohorte pura) y `TBP_A = TBP_C / E_r`. El notebook con series reales las verifica con `assert` en las 86 cohortes.
6. **El umbral 1 no es una frontera fiscal:** `TBP = 1` no equivale a equilibrio del sistema previsional (no hay tratamiento de otros recursos, moratorias, edad de retiro real ni dinámica de salarios). Es una señal de alerta, no una medida de sostenibilidad.

## 2. Supuestos del cálculo con series reales

| Variable | Valor / fuente | Comentario |
|---|---|---|
| `τ` | **21,77 %** = 11 % (aporte personal) + 10,77 % (contribución patronal SIPA) | Anuario ANSES 2008-2023, p. 39. Sin aportes a PAMI / obra social. Constante. |
| `ρ` | **40,3 %**, tasa de sustitución ANSES a dic-2023 (haber medio SIPA / salario imponible medio) | Anuario ANSES, p. 91. Constante. |
| `Ā` | Escenario **14,2** (piso sesgado) y **30** (techo legal) | 14,2 = promedio simple de varones 64 años (15,8) y mujeres 59 años (12,6), ANSES p. 46. Sesgado a la baja: ANSES sólo cuenta aportes desde jul-1994 y personas con al menos 12 meses de aporte. 30 es el requisito legal. |
| `N_t` | DEIS hasta 2024; proyección ONU WPP 2024 (variante media) desde 2025 | Las fuentes coinciden en promedio (ONU/DEIS 1,03), pero divergen en 2023-2024 (1,09 y 1,23). |
| `1 − μ` | Supervivencia de la cohorte hasta los 65: producto de `p_x` por grupo de edad, usando la tabla del año calendario en que se vive cada tramo | ONU WPP 2024. Más correcto que la tabla de período del año de nacimiento. |
| `J`, `E_r` | ONU WPP 2024 en `t+65` | Proyectados; `E_r` es de período. |

**Rebote post-2024:** el repunte del TBP de las cohortes 2025-2035 es un **artefacto del supuesto ONU** (~507 mil nacimientos en 2024 y ~520 mil hacia 2030, contra 413 mil registrados por DEIS en 2024). No es un dato; debe reemplazarse por un escenario propio de natalidad.

Todo el movimiento de la curva proviene de la demografía (`N_t`, `1−μ`, `J`, `E_r`) porque `τ` y `ρ` son constantes. El nivel absoluto del TBP no es interpretable mientras `Ā` siga siendo incierto.

## 3. Controles sobre los datos reales

Independientes de `Ā`, `τ`, `ρ`: (1) identidades algebraicas; (2) población de 65 años en `t+65` (ONU) vs `N_t · (1−μ)`: razón media 1,026 (rango 0,916-1,217; la cohorte 2024 queda fuera de [0,85; 1,20]); (3) nacimientos DEIS vs ONU.
