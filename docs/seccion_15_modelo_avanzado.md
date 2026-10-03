# Sección 15 — Modelo avanzado: sexo y edad de retiro, ρ con moratorias y migración

Notebook: `notebooks/fragmentos/seccion_15_modelo_avanzado.ipynb` (se pega al final del principal; usa `d`, `s`, `mort`, `TAU`, `RHO`, `A_OBS`, `A_LEGAL`, `DATA`, `OUT` y reusa `tbp_eph`, `tbp_anses`, `tbp_mortalidad`). Código: `src/tbp_modelo_avanzado.py` (`python src/tbp_modelo_avanzado.py` corre el autotest con datos **sintéticos**). Salidas: `datos/procesados/tbp_modelo_avanzado_1950_2035.csv` y `abar_eph_por_sexo_cohorte.csv` (Ā por sexo derivado de la EPH real).

**Aviso general.** Todos los niveles son condicionales a supuestos (sobre todo Ā, que es la cota inferior de asalariados de la EPH, y τ constante). No es una predicción, y no hay "significancia": son cuentas de un modelo determinista. Las diferencias entre pasos muestran cuánto pesa cada supuesto, no cuál es verdadero.

## 1. La fórmula y lo que NO se toca

TBP_C(t) = N_t·(1−μ)·Ā·τ / (J·ρ), en años. **No contiene E_r.** E_r entra solo en TBP_A = TBP_C/E_r y TBP_B = Āτ/(E_r ρ). Otro esquema que circuló metía E_r y un término (r−Ā) dentro de TBP_C, fabricaba E_r por sexo con 0,92/1,08 y sumaba "N + ΣM": nada de eso se usa (E_r sale de las tablas ONU por sexo; la migración se trata como en el punto 4).

## 2. Sexo y edad de retiro (varones 65, mujeres 60)

* Reparto: N_varones = N_t·SRB/(100+SRB), con el SRB de la ONU del año de nacimiento (≈105, 51,2 % varones); no se usa 51/49 fijo.
* S_s(r_s): supervivencia cohortal del sexo hasta *su* edad de retiro (mujeres a los 60, varones a los 65), con las tablas ONU por sexo.
* Ā_s: densidad de aportes de la EPH del sexo (`pipeline(..., sexo=)`), sumada hasta r_s−1 (varones 18–64, mujeres 18–59). Cohorte 1960: Ā varones 18,8; Ā mujeres (hasta 59) 10,4.
* Denominador J*·ρ, con J* = varones 65+ y mujeres 60+ en t+65: las mujeres de 60 a 64 ya cobran. La variante "todos a 65, J = 65+ total" (modelo base) sobrecuenta aportes de 60 a 64 y omite pasivas; se muestra como **sensibilidad**.
* **Agregación (una sola).** Se *suman* las contribuciones al numerador: TBP_C_total = TBP_C_varones + TBP_C_mujeres, ambos sobre el mismo J*·ρ. Se *promedian ponderando por los sobrevivientes al retiro* las intensidades por persona (Ā, E_r, TBP_B). TBP_A_total = Σ TBP_C_s/E_r,s y vale TBP_A = D*·TBP_B con D* = Σ N_sS_s / J*.

Efecto del retiro a los 60 (TBP_C, cohorte 1960; pasos acumulados, el orden importa): todos a 65 = 0,495; + más mujeres llegan a los 60 = 0,505; + Ā hasta 59 = 0,494; + J* = **0,418**. El denominador explica casi todo (J* es 18 % mayor que J en 1960): con J* el TBP_C cae 8–16 % según la cohorte.

## 3. ρ con moratorias (escenario)

ρ_total = s·ρ_mor + (1−s)·ρ_sin_mor (s = participación de beneficiarios con moratoria). Con los datos de ANSES (digitalizados, aprox.) se despeja ρ_mor implícito 2009–2023: entre **30,9 % y 36,8 %** (31,3 % en 2009, 30,9 % en 2023), siempre en (0,1) y por debajo del ρ sin moratoria: plausible (haber más cercano al mínimo). Para cohortes que se retiran después de 2023, s es un **supuesto**: *persiste* (≈62,9 %, ρ = 40,3 %, igual que la regla `ultimo_valor` de la sección 13), *mitad* (≈31 %, ρ = 48,3 %), *sin moratorias* (0 %, ρ = 56,3 %). Mayor ρ ⇒ menor TBP_C: −16,6 % (mitad) y −28,4 % (sin moratorias) respecto de "persiste", en todas las cohortes con retiro posterior a 2023. No se inventa cobertura real: s es un stock de beneficiarios, no la participación de las altas nuevas.

## 4. Migración (opcional)

Corrección empírica implícita en la proyección ONU: m = población de la edad de retiro en t+r_s / (N_s·S_s), de modo que N_efectivo·S = población ONU. Media 1,03 (cohortes ≤2024); cohorte 2024: 1,22 por el desfase DEIS (≈413 mil) / ONU (≈507 mil). Para cohortes ≥2025 la población ONU se repondera con los nacimientos del escenario (sección 10), y m ≈ 1,0. Efecto sobre TBP_C: +6,6 % (1960), +2,5 % (2000), +21,8 % (2024). **No es migración pura**: mezcla migración neta, diferencias de fuentes y desfase de nacimientos; supone que los migrantes aportaron como los nativos.

## 5. Comparación final por pasos (TBP_C, años; Ā de la EPH desde el paso 1)

| cohorte | 0: Ā=14,2 | 0: Ā=30 | 1: +Ā EPH | 2: +ρ ANSES | 3: +sexo/retiro, J* | 4: +natalidad, J* repond. | 5: +migración |
|---|---|---|---|---|---|---|---|
| 1960 | 0,476 | 1,006 | 0,487 | 0,487 | 0,418 | 0,418 | 0,445 |
| 1980 | 0,513 | 1,085 | 0,584 | 0,584 | 0,493 | 0,493 | 0,481 |
| 2000 | 0,384 | 0,811 | 0,358 | 0,358 | 0,312 | 0,312 | 0,320 |
| 2024 | 0,205 | 0,433 | 0,210 | 0,210 | 0,191 | 0,191 | 0,232 |
| 2035 | 0,285 | 0,603 | 0,294 | 0,294 | 0,264 | 0,222 | 0,222 |

El paso 2 solo se distingue en 1950–1958 (ρ ANSES = 0,403 desde la cohorte 1959). El paso 4 afecta solo a cohortes ≥2025 (escenario "persistencia"; −15,7 % en 2035). El nivel lo domina Ā: la línea Ā=30 es una referencia (requisito legal, no un máximo), no comparable con los pasos 1–5.

## 6. Controles y límites

Asserts: p0 reproduce `d`; ρ_mor ∈ (0,1); N_v+N_m = N_t; S_s ∈ (0,1); suma por sexo = total; con share=1 varón, r=65 y Ā constante se reproduce el TBP_C base; linealidad en Ā y τ; más ρ ⇒ menos TBP_C; N_efectivo·S = población ONU; J reponderado propio = `JRW` de la sección 10.

Límites: Ā por sexo es EPH urbana, solo asalariados (cota inferior), con extrapolación para cohortes jóvenes; ρ y τ iguales para ambos sexos y del año t+65; τ constante (supuesto); J* es un stock en t+65; en cohortes >2030 el J* de mujeres 60+ incluye cohortes sin escenario de natalidad (ONU); ρ_mor depende de datos digitalizados y de que ambos ρ compartan denominador. No se contrastó ρ_mor con cifras oficiales de haber por tipo de beneficio.
