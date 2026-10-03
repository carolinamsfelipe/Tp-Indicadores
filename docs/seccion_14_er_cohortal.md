# Sección 14 — Esperanza de vida cohortal (E_r) y corrección del pico de la cohorte 1956

Notebook: `notebooks/fragmentos/seccion_14_er_cohortal.ipynb` (se pega al final del principal; usa solo `d`, `s`, `mort`, `TAU`, `RHO`, `DATA`, `OUT`). Código: `src/tbp_mortalidad.py` (`python src/tbp_mortalidad.py --autotest`). Salida: `datos/procesados/er_cohortal_1950_2035.csv`.

## 1. Qué es

E_r es la esperanza de vida restante a los 65 años. Hasta ahora se tomaba la de **período**: la tabla de mortalidad del año t+65 (ONU WPP 2024). La versión **cohortal** sigue a la cohorte nacida en t año a año: cada tramo de edad [a, a+n) se recorre con la supervivencia del año calendario floor(t + a + n/2) (la misma convención de punto medio que ya usa 1−μ). E_r cohortal = años que se espera que le queden a esa cohorte a los 65, integrando la supervivencia con la identidad de la ONU (años vividos en el tramo = n·S(a+n) + aₓ·[S(a) − S(a+n)]) y el grupo abierto 100+.

## 2. Por qué

* **Pico de 1956.** La cohorte 1956 cumple 65 en 2021 (COVID). Con la tabla de período E_r cae a 16,1 años (mínimo de la serie; 17,9 en 1950) y TBP_B y TBP_A tienen su máximo ahí. Es un artefacto de mirar un solo año.
* **Longevidad subestimada.** La tabla de período congela la mortalidad de un año; las cohortes futuras todavía van a vivir mejoras. Resultado: E_r cohortal ≥ E_r de período (en promedio +1,0 año; +0,8 en la cohorte 2024).

## 3. Qué cambia (y qué no)

**TBP_C = N(1−μ)Āτ/(Jρ) no contiene E_r y no cambia** (se verifica con asserts). E_r aparece en TBP_A = TBP_C/E_r y en TBP_B = Āτ/(E_r ρ). Con E_r cohortal cambian esos dos; lo que cambia en TBP_C es solo su lectura frente a la longevidad.

| Cohorte | E_r período | E_r cohortal | TBP_B (Ā=30) per. → coh. | TBP_A (Ā=30) per. → coh. |
|---|---|---|---|---|
| 1950 | 17,87 | 18,06 | 0,907 → 0,897 | 0,0604 → 0,0598 |
| 1956 | 16,10 | 18,82 | 1,007 → 0,861 | 0,0662 → 0,0566 |
| 2024 | 23,72 | 24,50 | 0,683 → 0,662 | 0,0182 → 0,0177 |
| 2035 | 24,64 | 24,64 | 0,658 → 0,658 | 0,0245 → 0,0245 |

Con E_r cohortal el máximo de TBP_B y TBP_A pasa de la cohorte 1956 a la 1950. Índice 1950 = 100 de TBP_B: la cohorte 1956 pasa de 111 a 96.

## 4. Validaciones

(i) con mortalidad constante (test sintético) cohortal = período, exacto; (ii) la cohorte 1956 deja de ser el mínimo y la mayor caída interanual baja de −0,94 a −0,28 años; (iii) S65 cohortal recalculado = columna `S65` de `d`; (iv) cohortal ≥ período en las 86 cohortes del Total (única excepción por sexo: mujeres de la cohorte 1950, −0,015 años). La integración con aₓ reproduce el e₆₅ publicado por la ONU con error ≈ 5·10⁻⁵ años; con trapecio (aₓ = n/2) el error llega a ~0,08.

## 5. Límites

* Para cohortes que cumplen 65 después de ~2010 E_r es una **proyección** de la ONU (variante media), no un dato.
* Las tablas llegan a 2100: lo que cae después se calcula con la **tabla 2100 constante** (supuesto explícito, sin más mejoras). Afecta a las cohortes desde ~2000 (1 a 8 tramos de 8); las cohortes 2033–2035 coinciden con el período por construcción.
* El método asigna un único año a cada tramo de 5 años: **suaviza** el COVID, no lo elimina. Queda una ondulación menor en las cohortes 1951–1954 (hasta −0,28 años entre cohortes consecutivas).
* Tablas nacionales por sexo; sin diferencias por ingreso o historia de aportes.
