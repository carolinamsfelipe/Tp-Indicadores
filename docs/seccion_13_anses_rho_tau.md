# Sección 13 — ρ y τ por año (ANSES) e integración al TBP_C

**Idea.** El TBP_C usaba ρ = 0,403 y τ = 0,2177 constantes. Pero cada cohorte se jubila en un año distinto (cohorte + 65) y la tasa de sustitución cambió mucho: 37,1 % en 2009, pico cerca de 47 % en 2021, 40,3 % en 2023. Esta sección asigna a cada cohorte el ρ y el τ de **su** año de retiro:

TBP_C = N_t · (1−μ) · Ā · τ(t+65) / ( J · ρ(t+65) )

## Qué es ρ (y qué no)
ρ = **tasa de sustitución de ANSES** = haber medio SIPA (diciembre) / salario imponible medio (noviembre). No es haber/RIPTE. Hay dos versiones: con todos los beneficios (37,1 % → 40,3 %) y "sin moratoria" (42,5 % → 56,3 %).

## De dónde sale la serie
El Anuario 2008-2023 publica la serie anual **solo en un gráfico** (Gráfico 4.3, p. 91). Se **digitalizó** leyendo los vértices de las líneas vectoriales del PDF y calibrando el eje con la grilla. Contra los cuatro valores rotulados (2009 y 2023) el error es < 0,05 puntos porcentuales; los años intermedios no tienen etiqueta, así que su precisión no se puede comprobar. Por eso se rotulan *"digitalizado del gráfico del Anuario (precisión aprox.)"* y no se presentan como dato oficial exacto. Los beneficiarios con/sin moratoria (Gráfico 3.1, p. 65) se digitalizaron igual (error < 0,06 % en los extremos).

## τ
Verificado en el Anuario (p. 39): aporte personal 11 % + contribución patronal al SIPA 10,77 % (inc. a) = **21,77 %**; 12,35 % (inc. b) = 23,35 %; 16 % (sector público) = 27 %. No se pudo verificar con fuentes oficiales una **historia anual** de alícuotas, así que τ es **constante por supuesto** y se muestran los otros dos como escenarios.

## Cómo se asigna por cohorte
Año de retiro = cohorte + 65. Solo las **cohortes 1950–1958** (retiro 2015–2023) caen dentro de la serie. Para las 1959–2035 (retiro 2024 en adelante) hay que **elegir una regla explícita** y queda rotulada como supuesto: `ultimo_valor` (ρ de 2023), `media_ultimos_k` (media de los últimos k años, 2019-2023 ≈ 44,7 %) o `constante`. No se rellena con una media global.

## Cómo leer los gráficos
* Los **niveles del TBP_C dependen de Ā** (14,2 años según ANSES, sesgado; 30 años, requisito legal): por eso hay un panel para cada uno.
* El TBP_C dinámico se separa del constante solo para 1950–1958 (los únicos con ρ "observado"). **Toda la cola posterior es extrapolación**: cambiar la regla mueve el nivel ~10 %.

## Archivos
`src/tbp_anses.py` (módulo + `autotest()` con datos sintéticos), `notebooks/fragmentos/seccion_13_anses_rho_tau.ipynb`, `datos/procesados/anses_rho_tau_anual.csv` y `anses_beneficiarios_moratoria_anual.csv`. Si se deja el Excel "Estadísticas de la Seguridad Social" en `datos/anses/`, el lector genérico lo explora (no se asume estructura; ANSES bloquea la descarga automática y no se intentó).
