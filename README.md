# TBP — Índice de Cuna Vacía

Proyecto del **Taller de Indicadores Económicos** (universidad argentina). Propone y audita un indicador de alerta temprana demográfico-previsional para Argentina: el **TBP (Índice de Cuna Vacía)**.

> **Estado del proyecto: en construcción, resultados preliminares.** Los niveles del indicador dependen de supuestos todavía inciertos (ver [Limitaciones](#limitaciones)). No citar cifras como conclusiones.

## Qué es el TBP

Para cada cohorte de nacimiento `t`, el TBP compara lo que esa cohorte aportaría a lo largo de su vida activa con lo que demandaría como población jubilada:

```
TBP(t) = N_t · (1 − μ) · Ā · τ / ( J_{t+65} · E_r · ρ )
```

| Símbolo | Significado |
|---|---|
| `N_t` | nacimientos de la cohorte `t` |
| `1 − μ` | supervivencia de la cohorte hasta los 65 años |
| `Ā` | años de aporte promedio |
| `τ` | alícuota de aportes y contribuciones |
| `J_{t+65}` | población de 65 años y más en `t+65` |
| `E_r` | esperanza de vida a los 65 años |
| `ρ` | tasa de sustitución (haber medio / salario imponible medio) |

**Aviso:** el TBP es un **indicador de alerta temprana por cohorte**. **No es una medida de sostenibilidad fiscal** del sistema previsional: el umbral "TBP = 1" no es una frontera fiscal (ver [`docs/metodologia.md`](docs/metodologia.md)).

## Estructura del repositorio

```
notebooks/   TBP_Cuna_Vacia_Colab_v2.ipynb         auditoría + grupo de control sintético (datos ficticios)
             TBP_Argentina_Series_Reales.ipynb     cálculo por cohorte 1950-2035 con series reales
datos/
  procesados/  CSV y PNG usados y generados por el notebook con series reales
  crudos/      archivos públicos originales (DEIS, INDEC)
  README.md    diccionario de columnas, fuentes y PDFs que hay que bajar aparte
docs/        metodologia.md (hallazgos de la auditoría y supuestos del cálculo real)
```

## Fuentes

| Organismo | Qué se usa | Archivo en el repo | Enlace original |
|---|---|---|---|
| DEIS (Ministerio de Salud de la Nación) | Serie histórica de nacimientos por jurisdicción, 1914-2024 | `datos/crudos/salud_nacimientos_1914_2024.xlsx` | https://datos.salud.gob.ar/dataset/serie-historica-de-nacimientos-ocurridos-en-argentina-por-jurisdiccion |
| INDEC | Cuadro 1: población estimada por sexo, proyecciones nacionales 2010-2040 | `datos/crudos/indec_c1_proyecciones_nac_2010_2040.xls` | https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_nac_2010_2040.xls |
| INDEC | Proyecciones nacionales 2022-2040 (PDF metodológico; **no incluido**) | — (ver `datos/README.md`) | https://www.indec.gob.ar/ftp/cuadros/publicaciones/proyecciones_nacionales_2022_2040.pdf |
| ONU — World Population Prospects 2024 | Indicadores, población por edad simple, tabla de mortalidad abreviada de Argentina (variante media) | `datos/procesados/un_wpp2024_argentina_*.csv` | https://population.un.org/wpp/downloads |
| ANSES | Anuario estadístico 2008-2023 e Informe de estadísticas de la seguridad social IV-2025 (PDF, **no incluidos**); valores extraídos a mano | `datos/procesados/anses_valores_extraidos.csv` | https://www.anses.gob.ar/estadisticas-de-la-seguridad-social |

Los PDFs de ANSES e INDEC pertenecen a los organismos y no se redistribuyen aquí; `datos/README.md` explica cómo obtenerlos.

## Cómo reproducir

1. **En Colab** (recomendado): abrir el notebook con series reales.

   [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/carolinamsfelipe/Tp-Indicadores/blob/main/notebooks/TBP_Argentina_Series_Reales.ipynb)


   Sin copia local del repo, el notebook descarga los CSV necesarios desde la URL raw de GitHub (`RAW_BASE`). También busca los datos en una carpeta de Google Drive si está montada.
2. **En local:** clonar el repo, `pip install numpy pandas matplotlib jupyter` y abrir el notebook desde `notebooks/`. Lee `../datos/procesados/` y escribe sus salidas en `notebooks/salidas_tbp/` (ignorada por git).

El notebook `TBP_Cuna_Vacia_Colab_v2.ipynb` es autocontenido (datos sintéticos).

## Extensiones sobre Ā (años de aporte)

### Sensibilidad por bandas de Ā

`notebooks/TBP_Sensibilidad_A.ipynb` corre el modelo para Ā ∈ {15, 20, 25, 30} y grafica una banda de incertidumbre para TBP_C y TBP_A (salidas: `datos/procesados/tbp_sensibilidad_A.csv` y `.png`).
Hallazgo clave: el TBP es lineal en Ā, así que el índice normalizado (cohorte 1950 = 100) es idéntico en todos los escenarios. Ā cambia el **nivel** (factor 2 entre 15 y 30), no la forma ni las tendencias.
Es un parche para comunicar incertidumbre, no resuelve el sesgo de Ā (ver Opciones 2 y 3). El rebote posterior a 2024 es un artefacto del supuesto de nacimientos ONU. Detalle en `docs/sensibilidad_A.md`.

### Calibración de Ā con la EPH (Opción 2)

- Método para estimar Ā (años de aporte promedio por persona de la cohorte) con la EPH de INDEC como pseudo-panel por año de nacimiento: `docs/calibracion_A_EPH.md`.
- Código modular y probado con datos **sintéticos** (no son Argentina): `notebooks/TBP_Calibracion_A_EPH.ipynb`. Sin microdatos reales, termina diciendo "faltan datos"; **no entrega todavía ningún valor de Ā para Argentina**.
- Qué descargar de INDEC (bases individuales trimestrales, variables `PP07H`, `CAT_OCUP`, `CH06`, etc.) y dónde dejarlo: `datos/eph/README.md`. Los microdatos no se suben al repo (línea sugerida para `.gitignore`: `datos/eph/*` y `!datos/eph/README.md`).
- Salida prevista: un vector Ā_c por cohorte con escenarios (independientes: cota inferior, `PP07I`, supuesto), que alimenta la Opción 3 (Ā_t dinámico por cohorte).

## Secciones 9 a 11 del notebook de series reales (nuevas)

El notebook `notebooks/TBP_Argentina_Series_Reales.ipynb` conserva las secciones 1 a 8 y agrega, en orden:

* **9. Escenario propio de natalidad (RENAPER + DEIS + INDEC).** Desde 2025 la proyección de la ONU supone un rebote que los registros no muestran. Se parte de unos 390 mil nacimientos en 2025 (RENAPER provisorio ajustado por su relación con el DEIS) y se prueban tres trayectorias de fecundidad (persistencia, recuperación lenta, caída adicional). Datos: `datos/procesados/renaper_natalidad_2012_2025.csv` y `natalidad_escenarios_2025_2035.csv`. Detalle en `docs/seccion_09_natalidad.md`.
* **10. Consistencia de J.** El stock de 65+ de la ONU está construido con los nacimientos de la ONU; se repondera con los nacimientos propios. Salida: `datos/procesados/tbp_cohortes_J_reponderado.csv`. Detalle en `docs/seccion_10_J_reponderado.md`.
* **11. Sensibilidad (ρ, τ, N), hipótesis y control.** Estática comparativa, descomposición de la caída del TBP y comparación con la razón de dependencia (no son pruebas estadísticas). Detalle en `docs/seccion_11_hipotesis.md`.

* **12. Calibración de Ā con microdatos de la EPH.** Módulo `src/tbp_eph.py`: descarga (modo prueba por defecto), filtro de ocupados con descuento jubilatorio, edad efectiva de ingreso y Ā por cohorte, con conexión al TBP. Corrida con las 35 bases 2017-T2 a 2025-T4: **Ā preliminar entre ~13 y ~22 años según la regla para cuentapropistas (ninguna llega a 30)**. Detalle en `docs/seccion_12_eph_abar.md`.
* **13. ρ y τ por año (ANSES).** `src/tbp_anses.py`: ρ (tasa de sustitución) 2009-2023 recuperada de los gráficos vectoriales del Anuario (error < 0,05 pp en los extremos publicados; intermedios aproximados); τ constante como supuesto. Detalle en `docs/seccion_13_anses_rho_tau.md`.
* **14. Esperanza de vida cohortal.** `src/tbp_mortalidad.py`: E_r cohortal (reemplaza al de período y elimina el pico de la cohorte 1956; TBP_C no cambia porque no contiene E_r). Detalle en `docs/seccion_14_er_cohortal.md`.
* **15. Modelo avanzado.** `src/tbp_modelo_avanzado.py`: sexo (retiro varones 65 / mujeres 60), ρ con moratorias como escenario y ajuste por migración. Detalle en `docs/seccion_15_modelo_avanzado.md`.
* **16. Validación no econométrica y Monte Carlo.** Sensibilidad y elasticidades analíticas, descomposición contable y de varianza (Campbell-Shiller), bootstrap para Ā con microdatos EPH y simulación conjunta de Monte Carlo (10.000 iteraciones). Detalle en `docs/seccion_16_validacion.md`.
* **17. Validación temporal y estabilidad empírica (Pseudo IS vs. OOS).** Partición temporal (In-Sample 1950–2010 vs. Out-of-Sample 2011–2024), Test de Chow de quiebre estructural (corte 2011 y 2014) y proyección contrafáctica frente al colapso de nacimientos. Detalle en `docs/seccion_17_validacion_temporal.md`.

Los escenarios de natalidad son propuestas a validar por el grupo, no pronósticos. El dato de 2025 del RENAPER es provisorio.

## Limitaciones

- **`Ā` (años de aporte) es incierto:** el escenario observado (14,2) está sesgado a la baja; el legal (30) es el requisito mínimo para jubilarse, una referencia y no un máximo. El nivel del TBP no es interpretable todavía; la forma de la curva y su tendencia sí.
- **`τ` y `ρ` son constantes** (21,77 % y 40,3 %): no hay serie anual utilizable, así que todo el movimiento viene de la demografía.
- **Post-2024:** `N_t` pasa a la proyección ONU, que no refleja la caída de natalidad registrada por DEIS; el rebote de las cohortes 2025-2035 es un artefacto de ese supuesto.
- **Doble conteo de longevidad** en la fórmula original (en `J` y en `E_r`) y otros problemas de especificación: ver `docs/metodologia.md`.
- La fórmula se interpreta como señal de alerta, no como balance fiscal.

## Qué falta

- Escenario propio de natalidad para cohortes posteriores a 2024.
- Serie temporal de `τ`, `ρ` y `Ā` (hoy constantes/escenarios).
- Decisión del grupo sobre la especificación final de la fórmula (doble conteo de longevidad, definición de `J`).
- Revisión de los valores extraídos de los PDFs de ANSES.
- **Licencia: pendiente.** La decide el grupo; por ahora el repositorio no incluye archivo `LICENSE`.
