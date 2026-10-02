# datos/eph — microdatos de la EPH (NO se suben al repo)

Esta carpeta está pensada para dejar **localmente** las bases individuales de la Encuesta Permanente de Hogares (EPH) de INDEC. Sirven para el notebook `notebooks/TBP_Calibracion_A_EPH.ipynb` (calibración de Ā, ver `docs/calibracion_A_EPH.md`). **Hoy la carpeta está vacía a propósito: ningún microdato fue descargado.** La descarga la decide quien use el repo.

## Aviso: no subir al repo

Línea sugerida para el `.gitignore` (no se edita desde acá):

```
datos/eph/*
!datos/eph/README.md
```

## Qué bajar

Fuente oficial: **INDEC, "Bases de datos"** (https://sitioanterior.indec.gob.ar/bases-de-datos.asp; la página nueva de INDEC en https://www.indec.gob.ar enlaza a lo mismo desde "Servicios y herramientas / Bases de datos").

- Solo la **base individual** (`usu_individual`) de cada trimestre; la base de hogar (`usu_hogar`) no hace falta.
- Formato recomendado: **txt** (separador `;`). Los zip de INDEC se llaman con el patrón `EPH_usu_<T>_Trim_<AAAA>_txt.zip` y contienen `usu_individual_T<tt><aa>.txt` y `usu_hogar_T<tt><aa>.txt` (patrón observado en la página de INDEC del sitio anterior para 2016-2018).
- Cobertura sugerida: todos los trimestres disponibles desde **3T 2003** (primer microdato de la EPH continua según los resultados de INDEC consultados) hasta el último publicado. Más trimestres = más edades observadas por cohorte. Para una primera prueba alcanza con un trimestre por año.
- Tamaño: **no verificado** (cada archivo individual trimestral es del orden de unos pocos MB a algunas decenas de MB; a confirmar al bajar).
- Las bases 2003-2015 también existen en formatos SPSS, Stata y dbf; el notebook solo lee txt/csv con `;`.

## Cómo nombrarlos y dónde dejarlos

Basta con **dejar los archivos tal cual los entrega INDEC**, en `datos/eph/` (o en subcarpetas; se busca recursivamente). El notebook detecta:

- `usu_individual*.txt` o `usu_individual*.csv` (cualquier mayúscula/minúscula), o
- `EPH_usu_*.zip` que contengan un `usu_individual*.txt` adentro (se lee sin descomprimir).

No hace falta renombrar ni juntar archivos. Las columnas usadas son `ANO4`, `TRIMESTRE`, `CH04`, `CH06`, `ESTADO`, `CAT_OCUP`, `PP07H`, `PP07I`, `PONDERA` (nombres verificados en el diseño de registro INDEC de nov-2019 y 4T 2013; `PP07I` y su universo: a verificar). Si INDEC cambió algún nombre en una edición nueva, el notebook falla con un mensaje que lista las columnas faltantes.

## Documentación oficial (diseño de registro)

- 2019: https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_registro_2t19.pdf
- 4T 2013: https://sitioanterior.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_disenoreg_T4_2013.pdf
- Metodología de la EPH continua: https://www.indec.gob.ar/ftp/cuadros/sociedad/Metodologia_EPHContinua.pdf

Comprobar siempre el diseño de registro del trimestre que se baja (ediciones recientes pueden agregar o renombrar variables).

## Después de bajar

Correr el notebook; si todo está en orden la última celda escribe `salidas_tbp/abar_eph_por_cohorte.csv` (carpeta ya ignorada por `.gitignore`). Si faltan archivos, el notebook termina con el mensaje "FALTAN DATOS" y no calcula nada.
