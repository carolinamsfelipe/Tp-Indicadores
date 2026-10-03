# Sección 10 — Consistencia de J: reponderación con nacimientos propios

## Qué circularidad había
$J_{t+65}$ (población 65+ del año $t+65$) viene de la proyección ONU y está construida con los **nacimientos de la ONU**. Pero $N_t$ usa nacimientos DEIS (observados, hasta 2024) y, desde 2025, los escenarios propios de la sección 9. Numerador y denominador del $TBP$ contaban dos historias de natalidad distintas: si nacen menos chicos, habrá menos jubilados en el futuro y el $J$ de la ONU está sobreestimado.

## Qué hicimos
Reponderación por cohorte: para el año $y=t+65$,

$$J^{rw}(y)=\sum_{a=65}^{100+}\text{PopTotal}_{ONU}(a,y)\,w(y-a),\qquad w(c)=N_{propio}(c)/N_{ONU}(c)$$

($N_{propio}$ = DEIS si $c\le2024$, escenario si $c\ge2025$). Es una regla de tres: si una generación fue 20% más chica que lo supuesto por la ONU, su población a los 70 años también. Convenciones: $w=1$ para $c<1950$ (la serie ONU de nacimientos empieza en 1950) y para 1971–74 (hueco de DEIS, que el cuaderno principal ya completa con ONU); el grupo 100+ recibe $w(y-100)$; la cohorte es $y-a$ (convención del cuaderno principal). Se comparan tres versiones del $TBP$: (i) serie actual, (ii) $N$ propio con $J$ ONU (inconsistente), (iii) $N$ propio con $J$ reponderado (consistente).

## Resultado (cifras de la corrida; $\bar A=30$ salvo que se indique)
* **$t\le2024$:** $J^{rw}$ es en promedio 2,4% menor que $J$ ONU (máx 4,8%, cohorte 1999). Es sobre todo diferencia de nivel DEIS–ONU en cohortes viejas; ajustando solo 2023–24 la diferencia es ~0% (máx 0,9%). El nivel del $TBP$ de las cohortes ≤2024 sube ~5%, sin cambiar la forma.
* **$t\ge2025$:** $J$ cae hasta -9,9% (persistencia), -5,8% (recuperación lenta) y -12,0% (caída adicional) en la cohorte 2035.
* **$TBP_C$ (años), cohortes 2024 / 2030 / 2035:**

| versión | 2024 | 2030 | 2035 |
|---|---|---|---|
| (i) serie actual | 0,433 | 0,572 | 0,603 |
| (ii) persistencia, J ONU | 0,433 | 0,441 | 0,463 |
| (iii) persistencia, J reponderado | 0,442 | 0,470 | 0,513 |
| (iii) recuperación lenta | 0,442 | 0,527 | 0,623 |
| (iii) caída adicional | 0,442 | 0,433 | 0,480 |

* **Conclusión:** la curva post-2024 sigue por debajo de la serie actual con persistencia (-14,8% en 2035) y caída (-20,3%), pero menos que con la versión inconsistente (-23,3% y -29,9%): reponderar $J$ recupera 6 a 14 puntos de $TBP_C$ en 2035. Con recuperación lenta la cohorte 2035 queda apenas por encima de la serie actual (+3,4%). El rebote artificial de 2025 desaparece en los escenarios de natalidad baja.

## Supuestos y límites
* Mortalidad y migración de cada cohorte proporcionales a la proyección ONU (se reescala el tamaño de cada generación, no su comportamiento).
* Para cohortes ≤2024, DEIS/ONU mezcla la corrección de circularidad con la diferencia de nivel registro–estimación (media 0,97); por eso se informa la variante "solo 2023–24".
* 100+ tratado como una sola cohorte; la población ONU es de mitad de año y se usa $c=y-a$ (promediar $y-a$ e $y-a-1$ cambia $TBP_C$ en menos de 1%).
* Los escenarios de natalidad son propuestas a validar, no pronósticos; el dato 2025 del RENAPER es provisorio.

Archivos: `notebooks/fragmentos/seccion_10_J_reponderado.ipynb`, `datos/procesados/tbp_cohortes_J_reponderado.csv`.
