# Sección 21 — Backtest con proyecciones antiguas (ONU 2012-2019 e INDEC 2013)

Notebook: `notebooks/TBP_Argentina_Series_Reales.ipynb` (sección 21). Módulo: `src/tbp_vintages.py`. Datos: `datos/procesados/vintages_wpp_argentina.csv` (filas de Argentina de los paquetes R `wpp2012/2015/2017/2019` de CRAN, que contienen las tablas de la División de Población de la ONU) y, transcripta con página, la Serie Análisis Demográfico n.º 35 de INDEC (2013).

## Pregunta
¿Cuánto se equivocaron las proyecciones de fecundidad, nacimientos y población de 65+ disponibles *antes* de 2020? Es el único "fuera de muestra" legítimo del proyecto: se valida el **insumo** (N, J), no el índice, que no tiene resultado observable.

## Resultados
| Insumo | Error observado |
|---|---|
| TGF 2020-25 proyectada por la ONU (ediciones 2012, 2015, 2017, 2019) | **+48 % a +58 %** (2,06–2,20 contra ~1,39 observada) |
| TGF de INDEC 2013 | +34 % en 2020 (2,18 contra 1,63); +102 % en 2025 (2,10 contra 1,04, provisoria) |
| Nacimientos por año 2020-24 (derivados) | **+38 % a +54 %** |
| Población de 65+ (ONU, 2020) | −2,8 % a +0,2 % |
| Población de 65+ (INDEC 2013 contra INDEC 2025, 2022-2025) | −0,9 % a +0,9 % |

* El error de fecundidad **no se achica** al acercarse el horizonte (la edición 2019, a 3-4 años, falló igual que la de 2012, a 10): fue un cambio de régimen, no un error que crece de a poco.
* La población de 65+ es robusta: esas personas ya nacieron.

## Traducción al TBP
TBP_C es proporcional a N. Con la cohorte 2035 en persistencia (0,222 años), un error de ±17 % da 0,18–0,26; ±25 %, 0,17–0,28; ±40 %, 0,13–0,31. **±17 % es un piso, no un techo**, para la incertidumbre de la natalidad de cohortes posteriores a 2025.

## Límites
Los nacimientos derivados son una reconstrucción propia (error de −2 % a +7 % en 2015-2020, sin shock). La "población de 65+ observada" es WPP 2024 (no un censo por edad); para 2025 es proyección. Son cuatro ediciones de la ONU y una de INDEC: muestra pequeña. No se encontró WPP 2010. Los archivos originales (19 MB) están en `datos_tbp/proyecciones_antiguas/` de la carpeta de Drive y no se suben al repositorio.
