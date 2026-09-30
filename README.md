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

   [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/USUARIO/REPO/blob/main/notebooks/TBP_Argentina_Series_Reales.ipynb)

   > **PENDIENTE: reemplazar `USUARIO/REPO`** en el enlace del badge (arriba) y en la variable `RAW_BASE` de la primera celda de código del notebook, una vez que se conozca el repositorio real. Mientras tanto el badge no funciona.

   Sin copia local del repo, el notebook descarga los CSV necesarios desde la URL raw de GitHub (`RAW_BASE`). También busca los datos en una carpeta de Google Drive si está montada.
2. **En local:** clonar el repo, `pip install numpy pandas matplotlib jupyter` y abrir el notebook desde `notebooks/`. Lee `../datos/procesados/` y escribe sus salidas en `notebooks/salidas_tbp/` (ignorada por git).

El notebook `TBP_Cuna_Vacia_Colab_v2.ipynb` es autocontenido (datos sintéticos).

## Limitaciones

- **`Ā` (años de aporte) es incierto:** el escenario observado (14,2) está sesgado a la baja; el legal (30) es un techo. El nivel del TBP no es interpretable todavía; la forma de la curva y su tendencia sí.
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
