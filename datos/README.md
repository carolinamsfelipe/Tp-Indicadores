# Datos

Todo el contenido público y reproducible del proyecto. Los archivos **no** fueron modificados salvo los marcados como "elaboración propia".

## Fuentes y archivos

| Archivo | Carpeta | Origen | Tipo |
|---|---|---|---|
| `salud_nacimientos_1914_2024.xlsx` | `crudos/` | DEIS, https://datos.salud.gob.ar/dataset/serie-historica-de-nacimientos-ocurridos-en-argentina-por-jurisdiccion | original |
| `indec_c1_proyecciones_nac_2010_2040.xls` | `crudos/` | INDEC, https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_nac_2010_2040.xls | original |
| `un_wpp2024_argentina_indicadores.csv` | `procesados/` | ONU WPP 2024, https://population.un.org/wpp/downloads | extracto (Argentina, variante Medium) |
| `un_wpp2024_argentina_poblacion_edad_simple.csv` | `procesados/` | ONU WPP 2024 | extracto |
| `un_wpp2024_argentina_tabla_mortalidad_abreviada.csv` | `procesados/` | ONU WPP 2024 | extracto |
| `series_tbp_extraidas.csv` | `procesados/` | DEIS + ONU WPP 2024 | elaboración propia |
| `anses_valores_extraidos.csv` | `procesados/` | ANSES (PDFs, ver abajo) | extracción manual |
| `tbp_argentina_cohortes_1950_2035.csv` | `procesados/` | salida del notebook `TBP_Argentina_Series_Reales.ipynb` | elaboración propia |
| `tbp_argentina_graficos.png` | `procesados/` | salida del mismo notebook | elaboración propia |

Nota: el notebook con series reales lee `series_tbp_extraidas.csv` y `un_wpp2024_argentina_tabla_mortalidad_abreviada.csv`. El xls de INDEC se conserva como referencia cruzada y no alimenta el cálculo actual.

## PDFs que NO se incluyen (pertenecen a los organismos)

Bajarlos de la fuente y dejarlos localmente en `datos/` (el `.gitignore` los excluye):

| PDF (nombre local usado por el grupo) | Dónde bajarlo | Cómo se usó |
|---|---|---|
| Anuario estadístico ANSES 2008-2023 | https://www.anses.gob.ar/estadisticas-de-la-seguridad-social | Fuente de `τ` (p. 39), `Ā` (p. 46), aportantes y beneficiarios (p. 17, 65, 88-89) y tasa de sustitución `ρ` (p. 91) en `anses_valores_extraidos.csv`. |
| Informe de estadísticas de la seguridad social IV trim. 2025 (ANSES) | https://www.anses.gob.ar/estadisticas-de-la-seguridad-social | Beneficiarios, haber medio y beneficios a dic-2025 en `anses_valores_extraidos.csv` (p. 6-7). |
| INDEC, Proyecciones nacionales 2022-2040 | https://www.indec.gob.ar/ftp/cuadros/publicaciones/proyecciones_nacionales_2022_2040.pdf | Documento metodológico de referencia de las proyecciones INDEC (acompaña al xls `c1`). No alimenta columnas de los CSV procesados actuales. |

## Diccionario de columnas

### `series_tbp_extraidas.csv` (188 filas, una por año 1914-2101)

| Columna | Descripción | Unidad |
|---|---|---|
| `year` | Año calendario | año |
| `deis_nacimientos` | Nacimientos ocurridos, total país (DEIS); disponible 1914-2024, vacío desde 2025 | nacimientos |
| `un_births_miles` | Nacimientos, ONU WPP 2024 | miles |
| `un_e65` | Esperanza de vida a los 65 años, ambos sexos (período) | años |
| `un_e65_varones` / `un_e65_mujeres` | Ídem por sexo | años |
| `un_e0` | Esperanza de vida al nacer | años |
| `un_S65_periodo` | Supervivencia al 65 según la tabla de mortalidad de **período** del año (ignora mejoras futuras) | proporción |
| `un_pob_65mas_miles` | Población de 65 años y más (1 de julio) | miles |
| `un_pob_15_64_miles` | Población de 15 a 64 años | miles |
| `un_pob_edad65_miles` | Población de exactamente 65 años | miles |
| `un_dependencia_65mas_15_64` | Razón de dependencia: pob. 65+ / pob. 15-64 | razón |
| `tipo_un` | `estimado` (hasta 2023) o `proyectado` (ONU, desde 2024) | categoría |

### `anses_valores_extraidos.csv` (18 filas)

| Columna | Descripción |
|---|---|
| `variable` | Nombre de la variable (p. ej. `aportantes_sipa_total`, `tasa_sustitucion_haber_medio_sobre_salario_imponible`) |
| `periodo` | Año o mes-año (p. ej. `dic-2023`) |
| `valor` | Valor numérico |
| `unidad` | `personas`, `razon`, `proporcion`, `pesos corrientes`, `beneficios` |
| `fuente` | Publicación ANSES de origen |
| `pagina_pdf` | Página del PDF (y gráfico) de donde se extrajo |
| `tipo` | `observado` |

### `tbp_argentina_cohortes_1950_2035.csv` (86 filas, una por cohorte)

| Columna | Descripción |
|---|---|
| `cohorte` | Año de nacimiento `t` |
| `anio_65` | `t + 65` |
| `N_t` | Nacimientos usados: DEIS hasta 2024, ONU proyectado después |
| `fuente_N` | `DEIS` o `ONU proyectado` |
| `N_un` | Nacimientos según ONU (para comparación) |
| `S65` | Supervivencia de la cohorte hasta los 65 (`1 − μ`), producto de `p_x` por grupo de edad y año calendario |
| `J` | Población 65+ en `t+65` (personas) |
| `E65` | Esperanza de vida a los 65 en `t+65` (`E_r`) |
| `pob_edad65` | Población de exactamente 65 años en `t+65` |
| `TBP_A_obs` / `TBP_A_legal` | TBP con la fórmula original del grupo, con `Ā` = 14,2 / 30 |
| `TBP_C_obs` / `TBP_C_legal` | Variante en años (sin dividir por `E_r`) |
| `TBP_B_obs` / `TBP_B_legal` | Variante de cohorte pura, sin `N` |
| `D` | Factor demográfico `N_t · S65 / J` |

### `un_wpp2024_argentina_indicadores.csv` (152 filas, 1950-2101)

Formato original de ONU WPP 2024, Argentina, variante `Medium`. Columnas de identificación: `SortOrder, LocID, Notes, ISO3_code, ISO2_code, SDMX_code, LocTypeID, LocTypeName, ParentID, Location, VarID, Variant, Time`. Indicadores principales (población en miles; ver la documentación de ONU para el resto de las columnas): `TPopulation1Jan`, `TPopulation1July` (población total), `MedianAgePop`, `Births` (miles), `CBR`, `TFR` (tasa global de fecundidad), `Deaths`, `CDR`, `LEx` / `LExMale` / `LExFemale` (esperanza de vida al nacer), `LE15`, `LE65`, `LE80` (esperanza de vida a esas edades, total/varones/mujeres), `IMR`, `Q5`, `Q0040`, `Q1550`, `Q1560` (probabilidades de muerte entre edades), `NetMigrations`, `CNMR`. Definiciones: https://population.un.org/wpp/downloads

### `un_wpp2024_argentina_poblacion_edad_simple.csv` (15.352 filas)

Población por año (`Time`, 1950-2101) y edad simple (`AgeGrp` 0-99 y `100+`), variante `Medium`.

| Columna | Descripción |
|---|---|
| `Time`, `MidPeriod` | Año y punto medio del período |
| `AgeGrp`, `AgeGrpStart`, `AgeGrpSpan` | Edad (grupo, edad inicial, amplitud en años) |
| `PopMale`, `PopFemale`, `PopTotal` | Población en miles |
| (resto) | Columnas de identificación ONU (`SortOrder`, `LocID`, `ISO3_code`, `Location`, `Variant`, etc.) |

### `un_wpp2024_argentina_tabla_mortalidad_abreviada.csv` (9.966 filas)

Tabla de mortalidad abreviada (grupos 0, 1-4, 5-9, ..., 100+) por año (1950-2100) y sexo (`Sex`: `Male`, `Female`, `Total`), variante `Medium`.

| Columna | Descripción |
|---|---|
| `Time`, `MidPeriod` | Año y punto medio del período |
| `SexID`, `Sex` | Sexo |
| `AgeGrp`, `AgeGrpStart`, `AgeGrpSpan` | Grupo de edad, edad inicial, amplitud |
| `mx` | Tasa central de mortalidad |
| `qx` / `px` | Probabilidad de morir / de sobrevivir en el intervalo (`px = 1 − qx`) |
| `lx` | Sobrevivientes a la edad exacta (raíz 100.000) |
| `dx` | Defunciones de la tabla en el intervalo |
| `Lx` | Años-persona vividos en el intervalo |
| `Sx` | Razón de supervivencia por período |
| `Tx` | Años-persona vividos desde la edad `x` en adelante |
| `ex` | Esperanza de vida a la edad `x` |
| `ax` | Promedio de años vividos en el intervalo por quienes mueren en él |

### `crudos/salud_nacimientos_1914_2024.xlsx` (hoja `Hoja2`, 111 filas)

Columna `anio` (fecha 1 de enero de cada año), `total_argentina` y un nacimiento-total por jurisdicción (`capital_federal`, `buenos_aires`, `catamarca`, `cordoba`, ..., `tierra del fuego-antártida-islas-atlántico sud`). Los nombres de columna son los del archivo tal como lo dejó el grupo (incluye erratas: `medoza`, `santiengo_del_estero`).

### `crudos/indec_c1_proyecciones_nac_2010_2040.xls`

Cuadro 1 de INDEC: población estimada al 1 de julio, total y por sexo, 2010-2040. Sin modificar.
