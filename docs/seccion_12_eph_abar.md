# Sección 12 — Calibración de Ā con microdatos de la EPH (rutina)

**Qué es:** una rutina en Python (`src/tbp_eph.py`, también embebida en la sección 12 del Colab) que lleva el método de la sección 8 a datos reales.

## Flujo
1. **Descarga** de las bases usuarias individuales trimestrales de la EPH (INDEC). Por defecto está en *modo prueba*: lista los archivos y su tamaño y **no descarga nada** hasta que se pone `confirmado=True` / `ACEPTO_DESCARGA = True`.
2. **Filtro:** población 18–64; "registrado" = ocupado asalariado con descuento jubilatorio (`PP07H == 1`). Para cuentapropistas, tres reglas: `solo_asalariados` (cota inferior), `pp07i` y un escenario con proporción supuesta.
3. **Pseudo-panel:** cohorte = `ANO4 − CH06`; densidad de aportes por cohorte × edad; modelo logit aditivo cohorte + edad.
4. **Edad efectiva de ingreso al empleo registrado** (modelada y observada) y **Ā por cohorte**: Ā_c = Σ_{a=18}^{64} S_c(a)·d_c(a).
5. **Conexión con el TBP:** `tbp_con_abar` calcula TBP_C y TBP_A con Ā(t) por cohorte; a diferencia de las bandas de la sección 7, **cambia la forma de la curva**.

## Datos
Bases verificadas (2 oct 2026): `https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_{T}_Trim_{AAAA}_txt.zip`, de **2017-T2 a 2025-T4** (35 archivos, ≈ 107 MB). 2016 y 2017-T1 no están con ese nombre en el sitio actual. No se descargó ningún microdato hasta ahora.

## Estado y verificación
* Probada con datos **sintéticos** (autotest: pipeline, tres reglas, edad de ingreso, lector de `.txt`/`.zip`, conexión con el TBP; error medio de Ā contra la verdad sintética 0,80 años). **No hay ningún valor de Ā para Argentina todavía.**
* Pendiente al primer uso real: verificar los nombres de variables y el separador del `.txt` (`resumen_base`).

## Límites
EPH urbana y transversal; no observa el primer empleo registrado ni la historia de aportes; `PP07H` mide la semana de referencia; con sólo 9 años de datos cada cohorte se observa en pocas edades y el resto depende del perfil por edad común (período, edad y cohorte no se separan del todo); no hay variable inequívoca de aporte para cuentapropistas; el Ā de la EPH no es comparable uno a uno con el 14,2 de ANSES.
