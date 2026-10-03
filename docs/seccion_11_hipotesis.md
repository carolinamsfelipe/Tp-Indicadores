# Sección 11 — Sensibilidad, hipótesis testeables y control

Notebook: `notebooks/fragmentos/seccion_11_sensibilidad_hipotesis.ipynb` (se pega después de la sección 8 del notebook principal; usa solo `d`, `s`, `sens`, `TAU`, `RHO`, `A_OBS`, `A_LEGAL`, `DATA`, `OUT`). Salidas en `OUT/salidas/`.

## 1. Qué se puede y qué no se puede probar

El TBP es una **identidad determinística**: `TBP_C = N·(1−μ)·Ā·τ / (J·ρ)`. No hay variable resultado ni error aleatorio, así que **no hay test de significancia** que hacer. Lo que sí se puede hacer es:

1. **Estática comparativa:** mover un parámetro y calcular cuánto cambia el índice.
2. **Escenarios:** rangos justificados de ρ, τ y Ā.
3. **Comparación con un indicador convencional** (razón de dependencia).

No se afirma novedad. "No rechazada" significa solo que el signo y la magnitud calculados coinciden con lo esperado.

## 2. Parámetros y fuentes (Anuario ANSES 2008-2023)

| Parámetro | Valores usados | Fuente |
|---|---|---|
| ρ (haber medio SIPA / salario imponible medio) | 0,371 (dic-2009); **0,403** (dic-2023, base); 0,563 (haber contributivo sin moratoria, 2023) | p. 91 |
| τ | **0,2177** (11% + 10,77%, inc. a, base); 0,2335 (11% + 12,35%, inc. b); 0,27 (11% + 16%, administración pública) | p. 39 |
| Ā | 15 y 30 (30 es un requisito legal de referencia, **no un máximo**); 14,2 observado y sesgado | notebook principal |

## 3. Las seis hipótesis

| | Hipótesis | Signo | Parte del modelo | Se rechaza si… |
|---|---|---|---|---|
| H1 | Caída sostenida de N respecto de las cohortes que integran J reduce TBP | − | N, J en D | la contribución de ΔlnN tiene signo opuesto, o N cae y TBP_C no |
| H2 | Mayor longevidad (E_r, J) reduce TBP | − | E_r y J (doble canal en TBP_A; solo J en TBP_C) | elasticidad a E_r ≠ −1 o J crece y su contribución no es negativa |
| H3 | Mayor Ā aumenta TBP (nivel, no forma) | + | Ā | elasticidad ≠ +1 o el índice normalizado depende de Ā |
| H4 | Mayor formalidad (Ā y/o τ efectiva) aumenta TBP | + | Ā, τ | como H3/H5; la magnitud requiere Ā por cohorte (EPH, sección 8, sin datos reales aún) |
| H5 | Mayor τ aumenta TBP | + | τ | elasticidad ≠ +1 |
| H6 | Mayor ρ reduce TBP | − | ρ | elasticidad ≠ −1 |

Nota: la supervivencia hasta 65 (S65) **aumenta** el TBP y la longevidad posterior a 65 lo reduce; por eso H2 habla de E_r y J, no de "longevidad" en general.

## 4. Resultados numéricos (cohortes reales)

* **Linealidad:** ρ, τ y Ā cambian el **nivel** por un factor constante, no la forma. En la grilla completa (3 ρ × 3 τ × 2 Ā) el TBP_C va de 0,29 a 1,09 años para las cohortes 2000 y 2010, y de 0,155 a 0,583 para la 2024 (cociente máx/mín = 3,76). Solo por ρ: TBP_C(ρ=0,563) = 0,66 × TBP_C(ρ=0,371).
* **Lo que no es lineal:** si ρ dependiera de la cohorte (ejemplo **ilustrativo, inventado, no es dato**: ρ cae 40% entre las cohortes 1975 y 2000 por menor cobertura), la forma de la curva sí cambia (índice 2024 con base 1950=100: 40,1 con ρ constante vs 66,8 en el ejemplo).
* **Tornado, cohorte 2024** (base Ā=30, ρ=0,403, τ=0,2177; TBP_C = 0,43 años): Ā 15–30: −50%; ρ 0,371–0,563: +8,6% / −28,4%; τ hasta 0,27: +24,0%; N ±10% (ilustrativo): ±10%; J ±10% (ilustrativo): −9,1% / +11,1%.
* **Caída 2000→2024 de TBP_C** (0,811 → 0,433 años, −46,6%; descomposición logarítmica exacta, suma 100%): natalidad N **84,4%**; stock 65+ (J) **23,6%**; supervivencia a 65 (S65) **−7,9%** (amortigua). Con TBP_A (incluye E_r): N 73,7%, J 20,6%, E_r 12,6%, S65 −6,9%. Con otros puntos de partida el peso de N crece (2010→2024: 96%) y el de J cae (7,8%).
* **Control con la razón de dependencia (ONU, 65+/15–64):** Spearman de TBP_C con la razón en t+65 = −0,91 y en t+40 = −0,91 (signo esperado).

## 5. Limitaciones (leer antes de citar)

* **Circularidad:** J entra en el TBP_C (denominador) y en la razón de dependencia en t+65 (numerador); el benchmark mecánico Spearman(1/J, razón) es −0,98. Además ambas series tienen tendencia; el −0,91 **no es una validación independiente**. En primeras diferencias la correlación casi desaparece (−0,15 y +0,05). No se reportan p-valores (cohortes consecutivas no son independientes).
* La contribución de J mezcla natalidad y longevidad de cohortes anteriores; no es "longevidad pura".
* Las elasticidades (±1) son propiedades del diseño del índice, no hallazgos empíricos.
* ρ y τ se usan como constantes de 2023; no hay serie por cohorte. Ā por cohorte requiere la EPH (sección 8, sin datos reales).
* Para la cohorte 2024 (y posteriores) J, S65 y E_r son **proyecciones ONU a 2089+**; la incertidumbre demográfica es grande y solo está ilustrada (J ±10%).
* Un TBP mayor por menor ρ no significa mejor situación del jubilado: significa una prestación más baja relativa al salario.
