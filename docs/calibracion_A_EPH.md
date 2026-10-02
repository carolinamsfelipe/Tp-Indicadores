# Calibración de Ā con la EPH (Opción 2)

> **Estado:** método y código listos; **no hay todavía ninguna estimación de Ā para Argentina**, porque no se descargaron microdatos de la EPH. El notebook `notebooks/TBP_Calibracion_A_EPH.ipynb` solo fue probado con un dataset **sintético** (rotulado como tal). Cualquier cifra que salga de esa prueba no dice nada sobre Argentina.

## 1. Por qué hace falta calibrar Ā

Hoy Ā tiene dos escenarios sin base sólida: **14,2** años (ANSES, observado; sesgado a la baja porque los registros arrancan en jul-1994 y se exige un piso de 12 meses de aportes, Anuario ANSES 2008-2023, p. 46-47) y **30** años (requisito legal de referencia: mínimo para jubilarse, no un máximo). El valor realista está entre ambos, pero no sabemos dónde. La idea sugerida en el grupo de que estaría "en torno a 22-24 años" es una **hipótesis sin verificar**: este método sirve para ponerla a prueba, no para confirmarla; no se usa como objetivo en ningún cálculo.

## 2. Definición precisa

Para una persona de la cohorte c (nacida en el año c):

Ā_c = Σ_{a=18}^{64} S_c(a) · d_c(a)

- S_c(a) = P(sobrevivir desde el nacimiento hasta la edad a), de la cohorte c.
- d_c(a) = P(aportar a la edad a | vivo), es decir, la fracción del año a esa edad en que la persona está aportando.
- La suma incluye a los **nunca-aportantes** (d = 0 durante toda la vida): Ā es un promedio sobre *todas* las personas de la cohorte, no solo sobre las que aportaron alguna vez. Por eso 0 ≤ Ā ≤ Σ S_c(a) ≤ 47.
- Es un promedio por persona de la cohorte: no es "años de aporte entre quienes se jubilan" ni "años promedio de aportantes".

Diferencia con la "densidad de aportes" del Anuario ANSES: allí es *años aportados / años transcurridos desde los 18* por grupo (p. 47-48; p. ej. 41,5% en varones y 33,2% en mujeres de 55-59 años, p. 48). Acá d_c(a) es la densidad **por edad simple**; Ā_c es la suma de densidades ponderadas por supervivencia, y vale `Ā_c / Σ S_c(a)` como densidad media de la cohorte.

## 3. Idea central: la EPH como pseudo-panel

Los registros de ANSES dan historias individuales solo desde 1994 y con piso de 12 meses. La EPH no sigue personas por décadas, pero sí entrevista cada trimestre una muestra representativa. Se agrupa a las personas por **año de nacimiento (cohorte)** y se observa cada cohorte a edades sucesivas en años sucesivos: una "cohorte ficticia" o **pseudo-panel**. Es exactamente el enfoque de Moreno (2003), que construye información por cohorte a partir del año de nacimiento y el período de relevamiento y estudia la evolución del empleo registrado 1974-2002 en el Gran Buenos Aires para nacidos 1945-1984, con la conclusión de que alrededor de 30% de los asalariados de cada cohorte no alcanzaría los requisitos mínimos (Anuario ANSES, p. 45). Paz (2003) usa en cambio paneles EPH (transiciones entre empleo protegido, no protegido y desempleo, 1997-2002, p. 45) y Apella (2022) usa la MLER (asalariados privados registrados 1996-2021, p. 45), que excluye a quienes nunca estuvieron en el sistema formal y a los empleados públicos.

## 4. Paso a paso

### Paso 1. Variables y filtros (base individual trimestral)

Variables verificadas en el diseño de registro de INDEC (ediciones 2013 y 2019, ver sección 8):

| Uso | Variable | Contenido |
|---|---|---|
| Año / trimestre | `ANO4`, `TRIMESTRE` | año de relevamiento, ventana trimestral |
| Edad | `CH06` | años cumplidos (la fecha de nacimiento es `CH05`, no se usa) |
| Sexo | `CH04` | 1 varón, 2 mujer |
| Condición de actividad | `ESTADO` | 0 entrevista individual no realizada, 1 ocupado, 2 desocupado, 3 inactivo, 4 menor de 10 años |
| Categoría ocupacional | `CAT_OCUP` | 1 patrón, 2 cuenta propia, 3 obrero o empleado, 4 trabajador familiar sin remuneración |
| Descuento jubilatorio (asalariados) | `PP07H` | "¿Por ese trabajo tiene descuento jubilatorio?" 1 sí, 2 no |
| Aporte propio | `PP07I` | "¿Aporta por sí mismo a algún sistema jubilatorio?" 1 sí, 2 no. En el diseño de registro figura en el bloque de la ocupación principal de **asalariados**; su universo exacto es **a verificar** en el cuestionario |
| Ponderador | `PONDERA` | factor de expansión (para las variables no de ingreso) |
| Aglomerado | `AGLOMERADO` | código de aglomerado (opcional, para controles) |

Se trabaja con personas de 18 a 64 años con entrevista individual realizada (`ESTADO` ≠ 0). Se **mantiene a los inactivos y desocupados en el denominador**: d(a) es sobre toda la población de esa edad, no sobre ocupados.

### Paso 2. Cohorte y celdas

- `cohorte = ANO4 − CH06`. Tiene un error de ±1 año porque `CH06` son años cumplidos y no se usa la fecha exacta; es un error de medición clásico en pseudo-paneles y se acepta.
- Para cada celda (cohorte, edad simple) se acumulan todos los trimestres y años en que esa cohorte tuvo esa edad.
- Se descartan celdas con menos de `MIN_N_CELDA` observaciones (por defecto 20, sin ponderar). Con el esquema de rotación 2-2-2 de la EPH continua (la vivienda se entrevista dos trimestres seguidos, sale dos, vuelve dos) hay repetición de viviendas, así que los trimestres no son muestras independientes: los errores estándar reales son mayores que los de muestra independiente.

### Paso 3. Indicador de aporte por persona

Se define `reg` (probabilidad de estar aportando en el momento de la encuesta):

- **Asalariados** (`ESTADO`=1, `CAT_OCUP`=3): `reg = 1` si `PP07H`=1; 0 en caso contrario (incluye no respuesta).
- **Cuentapropistas y patrones** (`CAT_OCUP` 1 y 2): la base individual **no** trae una variable inequívoca de aporte de independientes que haya podido verificar (ver límites). Se ofrecen tres reglas, a elegir y reportar como escenario:
  1. `solo_asalariados`: independientes = 0. Es una **cota inferior** de d.
  2. `pp07i`: independientes aportan si `PP07I`=1, **solo si** se confirma que la variable se pregunta a independientes (a verificar).
  3. `escenario`: independientes aportan con una probabilidad supuesta (p. ej. calibrada con la proporción de monotributistas y autónomos aportantes de ANSES). Es un supuesto, no un dato EPH.
- **No ocupados, desocupados, trabajadores familiares sin remuneración**: `reg = 0`.

La densidad de la celda es la media ponderada de `reg` con `PONDERA`: **d̂(c, a) = Σ w·reg / Σ w**, que equivale a "tasa de empleo registrado = ocupados con descuento jubilatorio / población de esa edad". Ver sección 6 para por qué la interpretación como "fracción del año aportando" es un supuesto.

### Paso 4. Completar el triángulo (cohorte × edad) con un modelo aditivo

Ninguna cohorte se observa de 18 a 64 años: con la EPH continua (desde 2003) cada cohorte aparece a lo sumo durante ~22 años de edad. Por eso se ajusta un modelo logit aditivo:

logit d(c, a) = α_c + f(a)

con efectos fijos por cohorte (α_c) y perfil por edad (f(a)), estimado por regresión logística fraccional (IRLS, pesos = n de la celda). El perfil f(a) se identifica con la variación de edad *dentro* de cada cohorte; α_c mide cuánto más (o menos) formal es esa cohorte. Con esto se imputan las edades no observadas de cada cohorte usando el perfil de edad de las demás.

**Supuestos explícitos de este paso:**
1. El perfil por edad es *paralelo* en logit entre cohortes (misma forma, distinto nivel). Es fuerte: la cohorte que entró al mercado laboral en los años 90 pudo tener un perfil distinto.
2. **No hay efecto de período** separado: los ciclos (crisis 2001-02, recuperación, 2020) quedan absorbidos por α_c y f(a). En general edad, período y cohorte no se pueden separar (identidad exacta período = cohorte + edad); no incluir período es una elección, no un hallazgo. En la prueba sintética un efecto de período pequeño ya produjo errores de ±1-2 años en Ā por cohorte, que es una cota de la magnitud del problema.
3. Las edades jóvenes de cohortes viejas (cuando la EPH aún era puntual, ver sección 7) no se observan con la EPH continua: se imputan con el perfil, es decir, se supone que la cohorte nacida en 1950 a los 20 años se comportaba como el perfil medio ajustado más su α. Si se dispone de EPH puntual (1974-2002, microdatos a verificar) se pueden usar para validar esta imputación.

### Paso 5. Extrapolar a cohortes jóvenes y futuras

- Cohortes con menos de `MIN_EDADES_COHORTE` (3) edades observadas, o aún no nacidas en el rango EPH: α_c se completa con una regla explícita:
  - `ultimas_k`: promedio de α de las últimas k=5 cohortes con datos (supone que la formalidad por cohorte se estanca).
  - `tendencia`: extrapola linealmente α de las últimas ~15 cohortes (supone que sigue la tendencia reciente). Es un escenario, no un pronóstico.
- Las edades futuras de cohortes jóvenes se completan con f(a). Esto supone que el patrón por edad de las cohortes actuales vale para el futuro (los jóvenes de hoy dependerán de reformas laborales y previsionales, informalidad estructural, etc.).
- Tanto para las cohortes sin datos como para las que se observan solo en pocas edades, Ā tendrá **intervalos de incertidumbre de modelo** más grandes que los de muestreo. Se recomienda reportar los dos escenarios (`ultimas_k` y `tendencia`) y los tres de independientes.

### Paso 6. Supervivencia y cálculo de Ā

Para S_c(a) se usa, en el notebook, una aproximación de Gompertz con pendiente fija (b = 0,085, supuesto) calibrada para que S_c(65) coincida con el S65 de cada cohorte de `datos/procesados/tbp_argentina_cohortes_1950_2035.csv`. Es una aproximación simple: ignora la mortalidad infantil, que casi no afecta a S(a) a partir de los 18 años dado S65, pero **mejorable** usando directamente los `lx` por cohorte de la tabla de mortalidad de la ONU (`un_wpp2024_argentina_tabla_mortalidad_abreviada.csv`).

Ā_c = Σ S_c(a) · d_c(a), con asserts de control: d ∈ [0,1], Ā ∈ [0,47], Ā ≤ Σ S_c(a), y Ā creciente en S65 a igual densidad.

## 5. Asalariados, independientes, no ocupados y sexo

- **Asalariados**: es donde la EPH mide mejor el aporte (`PP07H`), aunque es una pregunta declarada sobre *ese empleo* y *ese momento*.
- **Independientes**: es el punto más débil. Según el Anuario (p. 46), los no asalariados (casas particulares, autónomos, monotributo) promediaban 14,1 años de aporte frente a 16,8 de los de relación de dependencia entre varones de 64 años, y 9,2 frente a 16,3 en mujeres de 59: son una parte importante de los aportantes. Dejarlos en cero subestima Ā; imputarles una tasa sin dato la hace dependiente de un supuesto. Hay que mostrar ambos.
- **No ocupados**: aportan 0 en este indicador. Cubre (i) personas que nunca trabajan formalmente (la masa de ceros que los registros con piso de 12 meses no ven, como señala el Anuario al discutir a Apella 2022, p. 45) y (ii) períodos de desempleo o inactividad entre empleos.
- **Sexo**: `pipeline(..., sexo=1|2)` repite todo por sexo. Recomendado: la trayectoria de aportes de mujeres y varones difiere mucho (p. 46-48 del Anuario). Después se combinan con la proporción de nacimientos o población por sexo de la cohorte. Ojo: S65 del CSV es total o por sexo según la columna usada, a verificar antes de combinar.

## 6. Cómo se interpreta d(a) (y qué supone)

La EPH pregunta por la **semana de referencia**. Se interpreta `reg` como proxy de "fracción del año aportando". Eso vale si el estado en la semana de referencia es representativo del año y si la rotación entre estados formal-informal es estacionaria. Si no, hay sesgos en ambos sentidos: una persona puede estar registrada en la semana de referencia y haber aportado solo 4 meses, o lo contrario.

## 7. Cobertura de la EPH: urbana y desde cuándo

- **Urbana, no nacional**: la EPH cubre aglomerados urbanos (31 desde 2002 según INDEC; 28 históricos en la EPH puntual), más un área urbano-rural; no cubre población rural ni localidades chicas. Si la formalidad urbana difiere de la nacional (en general es mayor en áreas urbanas grandes), Ā calculado con EPH puede estar sesgado hacia arriba como estimación nacional. Se puede mitigar con `AGLOMERADO` y reponderación por región, pero no se elimina.
- **Períodos**: la EPH "puntual" (mayo y octubre) funcionó desde 1973 según la reseña de INDEC (Moreno 2003 cita el período 1974-2002 en GBA; la fecha de inicio exacta no la pude cotejar contra una sola fuente, **a verificar**). La EPH **continua** (trimestral) reemplazó a la puntual en 2003; INDEC publica microdatos trimestrales desde el 3.er trimestre de 2003 (verificado en resultados de búsqueda del sitio de INDEC, no en la página de descarga misma). Antes de 2003 el cuestionario cambió y hay que comprobar que `PP07H` exista y sea comparable en la EPH puntual (microdatos puntuales: disponibilidad **a verificar**).
- Cohortes: nacidos desde ~1939 (64 años en 2003) en adelante tienen alguna edad observada con la EPH continua, lo que cubre el rango de cohortes de `tbp_argentina_cohortes_1950_2035.csv` (1950-2035) solo parcialmente para las más jóvenes (nacidos después de ~2007 no tienen ninguna edad observable).

## 8. Límites

1. **Sesgo de declaración**: `PP07H` es autodeclarado (descuento "en el recibo"); puede haber confusión entre descuento jubilatorio y otros descuentos, o desconocimiento. No es verificable con la EPH.
2. **Registro ≠ aporte efectivo**: tener descuento no garantiza que el empleador lo ingrese; recíprocamente puede haber aportes sin descuento en el recibo (p. ej. monotributistas).
3. **Moratorias**: los años cubiertos por moratoria previsional no son años de aporte; la EPH no los ve (es una virtud respecto del acceso a beneficios, pero implica que Ā no explica por sí solo el acceso a jubilación).
4. **Años de aporte por empleo público y regímenes especiales**: los empleados públicos provinciales/municipales con cajas propias pueden tener descuento jubilatorio en un sistema distinto del SIPA; la EPH no los distingue en `PP07H`. Esto puede inflar d para Ā definido sobre el SIPA.
5. **Sin trayectoria individual**: el pseudo-panel da la tasa media por cohorte y edad, no la distribución. Dos cohortes con igual Ā pueden tener distribuciones muy distintas (muchos ceros y muchos de 35 años, o todos 17 años), y para el acceso a la jubilación importa la distribución (Anuario, p. 46-48). Este método sirve para el promedio Ā del indicador TBP, no para la proporción que alcanza 30 años.
6. **Aglomerados urbanos** y **error de ±1 año en la cohorte** (sección 4 y 7).
7. **Confusión edad-período-cohorte** (paso 4).
8. **Cambios de cuestionario y de ponderadores** entre ondas (muestra ampliada en 3T2006 en aglomerados de menos de 500 mil habitantes, según el diseño de registro 2013).
9. **No hay piso de 12 meses**: a diferencia del 14,2 de ANSES (Anuario, p. 47: población con más de 12 meses de aporte, registros desde jul-1994), la EPH incluye a quienes aportan de forma esporádica y no está truncada en 1994. Por eso el resultado no es comparable 1 a 1 con 14,2; sirve para ubicar el valor entre los dos escenarios, no para "corregir" uno de ellos.

## 9. Conexión con la Opción 3 (Ā_t dinámico por cohorte)

La Opción 2 produce un **vector Ā_c** (una cifra por cohorte, con intervalos y escenarios) en lugar de una constante. La Opción 3 consiste en usar esa serie en el indicador: Ā_t = Ā_{c(t)}, donde c(t) es la cohorte que llega a edad de retiro (65) en el año t, es decir c = t − 65. Entonces TBP_t usa el Ā de *su propia* cohorte. Con este entregable, la Opción 3 se reduce a: (i) ejecutar el notebook con los datos reales, (ii) leer `salidas_tbp/abar_eph_por_cohorte.csv`, (iii) hacer un `merge` por `cohorte` con `tbp_argentina_cohortes_1950_2035.csv` y sustituir Ā constante por la columna elegida (cota inferior `solo_asalariados` y escenarios con independientes como bandas). Las cohortes con pocas edades observadas (jóvenes) heredan la incertidumbre del paso 5: conviene mostrar bandas y no una línea.

## 10. Qué archivos descargar

La descarga la decide la persona usuaria; este trabajo **no descargó ningún microdato**. Ver `datos/eph/README.md` para nombres y ubicación. Resumen de fuentes oficiales (verificadas por lectura):

| Qué | URL | Verificación |
|---|---|---|
| Bases de datos INDEC (EPH 2016-2018 y anteriores; formatos txt, xls, SPSS, Stata, dbf; nombres tipo `EPH_usu_4_Trim_2018_txt.zip`) | https://sitioanterior.indec.gob.ar/bases-de-datos.asp | Leída |
| Portal Redatam INDEC (EPH 2003-2013 consultas en línea, sin bajar microdatos) | https://redatam.indec.gob.ar/ | Aparece en resultados; no abierta |
| Diseño de registro EPH, nov-2019 (`PP07H`, `PP07I`, `ESTADO`, `CAT_OCUP`, `CH06`, `PONDERA`, `ANO4`, `TRIMESTRE`, `AGLOMERADO`) | https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_registro_2t19.pdf | Leída (variables comprobadas) |
| Diseño de registro EPH, 4T 2013 (misma estructura) | https://sitioanterior.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_disenoreg_T4_2013.pdf | Leída (variables comprobadas) |
| Metodología EPH continua ("La nueva EPH de Argentina, 2003") | https://www.indec.gob.ar/ftp/cuadros/sociedad/Metodologia_EPHContinua.pdf | Leída (puntual mayo/octubre; 28 aglomerados históricos; esquema 2-2-2; 31 aglomerados) |
| Página EPH en el sitio anterior de INDEC (mercado de trabajo) | https://sitioanterior.indec.gob.ar/nivel4_default.asp?id_tema_1=4&id_tema_2=31&id_tema_3=58 | Leída |
| Anuario estadístico ANSES 2008-2023 | https://www.anses.gob.ar/estadisticas-de-la-seguridad-social | Referido en `datos/README.md`; usado localmente |

**No verificado**: el enlace directo exacto de cada archivo trimestral de 2019 en adelante en el sitio actual de INDEC (la página nueva de "Bases de datos" no devolvió el listado al leerla; los nombres de archivo `EPH_usu_<T>_Trim_<AAAA>_txt.zip` y de contenido `usu_individual_T<tt><aa>.txt` sí fueron observados en documentación de terceros y en la página del sitio anterior, no en un listado oficial vigente); tamaño de los archivos (no verificado); disponibilidad de microdatos de la EPH puntual (1974-2002); universo exacto de `PP07I`; existencia de una variable de aporte jubilatorio específica para cuentapropistas en la base individual.

## 11. Referencias

- Anuario Estadístico ANSES 2008-2023 (`datos_tbp/Anuario Estadístico_final.pdf`), pp. 44-48 (Bertranou y Sánchez 2003, p. 44; Moreno 2003, Paz 2003 y Apella 2022, p. 45; promedios por sector, p. 46; densidad de aportes, pp. 47-48) y bibliografía, p. 61.
- Moreno, J. (2003). *Trayectorias laborales a partir de cohortes ficticias. Gran Buenos Aires, 1974-2002.* En MTESS y OIT, *Historias Laborales en la Seguridad Social*, pp. 127-147.
- Paz, J. (2003). Movilidad entre empleos protegidos y no protegidos (EPH, 1997-2002), citado en Anuario p. 45.
- Apella, I. (2022). *El sistema previsional argentino, sus logros y desafíos.* Banco Mundial.
- INDEC. EPH, diseño de registro (2013, 2019) y metodología de la EPH continua (2003): enlaces en la sección 10.
