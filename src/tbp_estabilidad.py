# -*- coding: utf-8 -*-
"""
tbp_estabilidad.py — Backtest de insumos y estabilidad temporal del TBP_C.

Proyecto TBP — Índice de Cuna Vacía (Taller de Indicadores).

POR QUÉ ESTE MÓDULO (en una línea): el TBP_C es una IDENTIDAD contable sin variable resultado
observada, así que NO existe un "fuera de muestra" predictivo para el índice. Lo que SÍ se puede
validar es (A) cuánto se equivocaron proyecciones pasadas de los INSUMOS (nacimientos N, población 65+ J)
y (B) si el "motor" de la serie cambia a lo largo del tiempo (estabilidad), con las salvedades del caso.

    TBP_C = N · (1−μ) · Ā · (τ/ρ) / J          ⇒   ln TBP = ln N + ln(1−μ) + ln Ā + ln(τ/ρ) − ln J     (exacta)

CONTENIDO
  A) Backtest de insumos:   error_pct, interpolar_a_fecha, backtest_nacimientos_wpp2024, backtest_poblacion_indec2013,
                            comparar_J_fuentes, backtest_tabla (arma backtest_insumos.csv), PENDIENTES_DESCARGA,
                            sigma_por_horizonte, mc_tbp (Monte Carlo con bandas empíricas en lugar de ±1,5 %).
  B) Estabilidad temporal:  componentes_log, ventanas_moviles, chow_f, sup_f, wald_hac, sup_wald_hac,
                            permutacion_bloques, tabla_quiebre.
  C) autotest() con datos SINTÉTICOS rotulados (no son Argentina).

REGLA: no descarga nada. Todo lo que no está en el proyecto queda en PENDIENTES_DESCARGA (solo lista).
"""
import os, datetime as _dt
import numpy as np
import pandas as pd

RUTAS_CANDIDATAS = ["../datos/procesados", "datos/procesados", "../datos/crudos", "datos/crudos"]

# ----------------------------------------------------------------------------------------------
# Datos transcriptos de PDF locales (INDEC 2025, base Censo 2022). Se citan con página.
# Fuente: datos_tbp/indec_proyecciones_nacionales_2022_2040.pdf  (INDEC, "Estimaciones y proyecciones de
# población, por sexo y edad. Total del país. Años 2022-2040", 1.ª ed., 2025).
# ----------------------------------------------------------------------------------------------
CENSO_2022 = {
    "fecha": _dt.date(2022, 5, 18),
    "total_enumerado": 45_892_285,        # PDF INDEC 2025, p. 12, Tabla 1 (Población 2022)
    "total_sin_calle": 45_886_580,        # PDF p. 19, Tabla 4 (no incluye situación de calle sin edad)
    "j65_censada": 5_464_057,             # PDF p. 19, Tabla 4 (65 y más, ambos sexos, censada)
    "total_estimada_a_fecha_censal": 46_122_853,   # PDF p. 19, Tabla 4 (estimación INDEC a la fecha censal)
    "j65_estimada_a_fecha_censal": 5_521_560,      # PDF p. 19, Tabla 4
}
CENSO_2010 = {"fecha": _dt.date(2010, 10, 27), "total_enumerado": 40_117_096}  # PDF 2025, p. 12, Tabla 1

# Población al 1-jul de cada año (INDEC 2025). Total: fila "Total" del Cuadro 2.1 (pp. 39 y 41).
# 65+: suma de las edades 65..99 y "100 y más" del Cuadro 2.1 (pp. 39-42), calculada al transcribir (la suma de
# todas las edades reproduce el Total sin diferencias).
INDEC_2025_TOTAL = {2022: 46135579, 2023: 46214462, 2024: 46301743, 2025: 46387098, 2026: 46466688, 2027: 46540071,
                    2028: 46609533, 2029: 46676999, 2030: 46744389, 2031: 46814264, 2032: 46886737, 2033: 46961803,
                    2034: 47039274, 2035: 47118716, 2036: 47199436, 2037: 47280504, 2038: 47360804, 2039: 47439108,
                    2040: 47514116}
INDEC_2025_J65 = {2022: 5529167, 2023: 5610238, 2024: 5711979, 2025: 5815927, 2026: 5922327, 2027: 6031328,
                  2028: 6142648, 2029: 6255112, 2030: 6367718, 2031: 6480544, 2032: 6594032, 2033: 6709837,
                  2034: 6831713, 2035: 6963335, 2036: 7105814, 2037: 7258199, 2038: 7421088, 2039: 7597415,
                  2040: 7789606}
INDEC_2025_EDAD0 = {2022: 499587, 2023: 471623, 2024: 453124, 2025: 444076}   # población de 0 años al 1-jul (p. 39)

# Archivos que HABRÍA QUE BAJAR (solo lista; tamaños medidos con cabeceras HTTP HEAD, sin descargar).
PENDIENTES_DESCARGA = [
    dict(archivo="INDEC 2013 — Serie Análisis Demográfico n.º 35 (PDF)",
         url="https://www.indec.gob.ar/ftp/cuadros/publicaciones/proyeccionesyestimaciones_nac_2010_2040.pdf",
         bytes=267_025, para="65+ proyectado para 2020 (Cuadro 2, por sexo y edad quinquenal) y TGF/natalidad (Cuadro 5) → "
         "error de J y de N de la proyección 2013 contra Censo 2022 y DEIS. Verificado: HTTP 200, application/pdf."),
    dict(archivo="WPP 2019 (paquete R 'wpp2019_1.1-1.tar.gz', datos de la ONU)",
         url="https://cran.r-project.org/src/contrib/wpp2019_1.1-1.tar.gz", bytes=4_684_504,
         para="Nacimientos/fecundidad y población por edad proyectados en 2019 → error a 4-5 años (2023-24) y 65+ 2022. "
              "Contenido exacto de tablas: confirmar al abrirlo."),
    dict(archivo="WPP 2017 (paquete R 'wpp2017_1.2-3.tar.gz')",
         url="https://cran.r-project.org/src/contrib/wpp2017_1.2-3.tar.gz", bytes=4_743_882,
         para="Vintage intermedio (horizonte 6-7 años)."),
    dict(archivo="WPP 2015 (paquete R 'wpp2015_1.1-2.tar.gz', carpeta Archive de CRAN)",
         url="https://cran.r-project.org/src/contrib/Archive/wpp2015/wpp2015_1.1-2.tar.gz", bytes=4_585_228,
         para="Horizonte ~8-9 años para 2023-24 y ~7 años para el Censo 2022."),
    dict(archivo="WPP 2012 (paquete R 'wpp2012_2.2-1.tar.gz')",
         url="https://cran.r-project.org/src/contrib/wpp2012_2.2-1.tar.gz", bytes=4_902_348,
         para="Horizonte ~10-12 años; sirve para ver cómo crece el error con el horizonte."),
    dict(archivo="WPP 2010", url="(no verificado: sin paquete en CRAN ni URL vigente hallada; las URL históricas "
         "population.un.org/wpp/Download/Files/... devolvieron 404)", bytes=None,
         para="Habría que pedirlo al archivo de la División de Población de la ONU; no se puede estimar el tamaño."),
]


def tamano_pendientes():
    """Suma (en MB) de lo verificable de PENDIENTES_DESCARGA."""
    return sum(p["bytes"] for p in PENDIENTES_DESCARGA if p["bytes"]) / 1e6


# ==============================================================================================
# A) BACKTEST DE INSUMOS
# ==============================================================================================
def error_pct(proyectado, observado):
    """Error relativo en %: 100·(proyectado/observado − 1). Positivo = la proyección SOBRESTIMÓ."""
    return 100.0 * (np.asarray(proyectado, float) / np.asarray(observado, float) - 1.0)


def interpolar_a_fecha(serie_1jul, fecha):
    """Interpola linealmente una serie al 1-jul de cada año a una fecha calendario (p. ej. 18-may-2022)."""
    f0 = _dt.date(fecha.year if fecha >= _dt.date(fecha.year, 7, 1) else fecha.year - 1, 7, 1)
    f1 = _dt.date(f0.year + 1, 7, 1)
    w = (fecha - f0).days / (f1 - f0).days
    return float(serie_1jul[f0.year] + (serie_1jul[f1.year] - serie_1jul[f0.year]) * w)


def _fila(bloque, insumo, proyeccion, publicada, ref, horizonte, proy, obs, unidad, tipo, fuente_obs, nota):
    return dict(bloque=bloque, insumo=insumo, proyeccion=proyeccion, publicada=publicada, referencia=ref,
                horizonte_anios=horizonte, proyectado=proy, observado=obs, unidad=unidad,
                error_abs=(None if (proy is None or obs is None) else proy - obs),
                error_pct=(None if (proy is None or obs is None) else float(error_pct(proy, obs))),
                tipo=tipo, fuente_observado=fuente_obs, nota=nota)


def backtest_nacimientos_wpp2024(s):
    """ONU WPP 2024 (publicada jul-2024) vs nacimientos DEIS. `s` = series_tbp_extraidas.csv indexado por 'year'
    (un_births_miles en MILES; deis_nacimientos en personas)."""
    filas = []
    for y in (2022, 2023, 2024):
        proy = float(s.un_births_miles[y]) * 1000
        obs = float(s.deis_nacimientos[y])
        extra = ("El error ≈ 0 en 2022 sugiere que ése fue el último año con dato incorporado: 2023 y 2024 son pronósticos a 1 y 2 años."
                 if y == 2022 else "DEIS 2024 puede ser provisorio (inscripciones tardías suben el dato) → el error de 2024 podría ser algo menor.")
        filas.append(_fila("A1 nacimientos", f"Nacimientos {y}", "ONU WPP 2024 (medio)", "jul-2024", y, y - 2022,
                           proy, obs, "personas", "backtest legítimo (proyección publicada antes del dato)",
                           "DEIS (Min. Salud), series_tbp_extraidas.csv", extra))
    return filas


def backtest_poblacion_indec2013(x13, j_wpp_miles=None, tot_wpp_miles=None):
    """INDEC 2013 (base Censo 2010; población total al 1-jul 2010-2040) contra el Censo 2022 y contra la reestimación
    INDEC 2025. `x13`: Series año→población (Cuadro 1 del xls). Devuelve lista de filas."""
    filas = []
    p22 = interpolar_a_fecha(x13, CENSO_2022["fecha"])
    filas.append(_fila("A2 población total", "Población total al 18-may-2022", "INDEC 2013 (base Censo 2010)", "nov-2013",
                       2022, 12, p22, CENSO_2022["total_enumerado"], "personas",
                       "backtest legítimo (12 años)", "Censo 2022 enumerado — PDF INDEC 2025, p. 12 (Tabla 1)",
                       "Proyección interpolada al 18-may-2022 (publicada al 1-jul)."))
    filas.append(_fila("A2 población total", "Población total al 18-may-2022 (vs estimación INDEC a fecha censal)",
                       "INDEC 2013 (base Censo 2010)", "nov-2013", 2022, 12, p22,
                       CENSO_2022["total_estimada_a_fecha_censal"], "personas", "backtest legítimo (12 años)",
                       "INDEC 2025 p. 19 (Tabla 4): estimación a la fecha censal, que corrige por omisión/sobrecobertura",
                       "Comparación más justa: el censo enumerado tiene subnumeración de 0,5 %."))
    p10 = interpolar_a_fecha(x13, CENSO_2010["fecha"])
    filas.append(_fila("A2 población total", "Población total al 27-oct-2010 (año base)", "INDEC 2013 (base Censo 2010)",
                       "nov-2013", 2010, 0, p10, CENSO_2010["total_enumerado"], "personas",
                       "control del año base (no es pronóstico)", "Censo 2010 enumerado — PDF INDEC 2025, p. 12",
                       "La proyección parte del censo CORREGIDO por omisión, por eso queda ~2 % por encima del enumerado."))
    # trayectoria: INDEC 2013 vs reestimación INDEC 2025 (mismo organismo, otra base censal)
    for y in (2025, 2030, 2035, 2040):
        filas.append(_fila("A2 población total", f"Población total {y}: INDEC 2013 vs INDEC 2025", "INDEC 2013", "nov-2013",
                           y, y - 2010, float(x13[y]), float(INDEC_2025_TOTAL[y]), "personas",
                           "revisión entre vintages (la 'realidad' es otra proyección, no un dato)",
                           "INDEC 2025, Cuadro 2.1 (pp. 39-41)",
                           "Muestra cuánto cambia el escenario al incorporar el Censo 2022: mide revisión, no error contra hechos."))
    return filas


def comparar_J_fuentes(j_wpp_miles, tot_wpp_miles=None):
    """65+ de la ONU WPP 2024 (J del TBP) contra (i) Censo 2022 y (ii) INDEC 2025, 2022-2040.
    j_wpp_miles: Series año→65+ en MILES (1-jul)."""
    filas = []
    j22 = interpolar_a_fecha(j_wpp_miles * 1000, CENSO_2022["fecha"])
    filas.append(_fila("A3 población 65+", "65+ al 18-may-2022", "ONU WPP 2024", "jul-2024", 2022, 0, j22,
                       CENSO_2022["j65_censada"], "personas", "chequeo de nivel (WPP 2024 NO incorpora el Censo 2022: ver nota)",
                       "Censo 2022 — PDF INDEC 2025, p. 19 (Tabla 4), censada",
                       "Se verificó que WPP 2024 da 45,41 M para 2022, 1,1 % bajo el censo: no está calibrada con él."))
    filas.append(_fila("A3 población 65+", "65+ al 18-may-2022 (vs estimación INDEC a fecha censal)", "ONU WPP 2024", "jul-2024",
                       2022, 0, j22, CENSO_2022["j65_estimada_a_fecha_censal"], "personas", "chequeo de nivel",
                       "PDF INDEC 2025, p. 19 (Tabla 4)", "El censo subenumera 65+ en 1,0 % (INDEC)."))
    for y in (2022, 2025, 2030, 2035, 2040):
        filas.append(_fila("A3 población 65+", f"65+ {y}: ONU WPP 2024 vs INDEC 2025", "ONU WPP 2024", "jul-2024", y, max(y - 2024, 0),
                           float(j_wpp_miles[y]) * 1000, float(INDEC_2025_J65[y]), "personas",
                           "dispersión entre fuentes (NO es error de proyección)", "INDEC 2025, Cuadro 2.1 (pp. 39-42)",
                           "Sirve de piso para la incertidumbre de J: dos instituciones serias difieren esto."))
    return filas


def dispersion_J(j_wpp_miles):
    """Serie de diferencias % WPP2024 vs INDEC2025 en 65+ (2022-2040) y su RMSE."""
    ys = sorted(INDEC_2025_J65)
    e = pd.Series([float(error_pct(j_wpp_miles[y] * 1000, INDEC_2025_J65[y])) for y in ys], index=ys)
    return e, float(np.sqrt((e ** 2).mean()))


def proxy_edad0(s):
    """Proxy (no es error estricto): población de 0 años al 1-jul-2024 (INDEC 2025) vs promedio de nacimientos DEIS 2023-24
    (los de 0 años a mitad de 2024 nacieron entre jul-2023 y jun-2024)."""
    obs = (float(s.deis_nacimientos[2023]) + float(s.deis_nacimientos[2024])) / 2
    return _fila("A1 nacimientos", "Población de 0 años al 1-jul-2024 vs nacimientos DEIS (prom. 2023-24)", "INDEC 2025", "2025",
                 2024, 0, float(INDEC_2025_EDAD0[2024]), obs, "personas", "proxy (sin corrección por mortalidad infantil/migración)",
                 "DEIS", "INDEC 2025 ve ~3-4 % más nacimientos que el promedio DEIS: coherente con que DEIS 2024 sea provisorio.")


def backtest_tabla(s, x13=None):
    """Arma el DataFrame completo de backtest_insumos.csv (incluye filas 'pendiente de descarga')."""
    filas = backtest_nacimientos_wpp2024(s)
    filas.append(proxy_edad0(s))
    if x13 is not None:
        filas += backtest_poblacion_indec2013(x13)
    filas += comparar_J_fuentes(s.un_pob_65mas_miles)
    for p in PENDIENTES_DESCARGA:
        filas.append(dict(bloque="A4 pendiente", insumo=p["archivo"], proyeccion="(vintage anterior)", publicada="", referencia="",
                          horizonte_anios=None, proyectado=None, observado=None, unidad="", error_abs=None, error_pct=None,
                          tipo="PENDIENTE DE DESCARGA", fuente_observado=p["url"],
                          nota=(f"{p['bytes']/1e6:.2f} MB. " if p["bytes"] else "tamaño desconocido. ") + p["para"]))
    return pd.DataFrame(filas)


def sigma_por_horizonte(sigma_ref, h_ref, h, modo="raiz"):
    """Escala un desvío medido a horizonte h_ref hacia el horizonte h. HEURÍSTICA (supuesto, no estimada):
    'raiz' = el error crece como √h (camino aleatorio); 'constante' = no escala."""
    if modo == "constante" or h_ref <= 0:
        return float(sigma_ref)
    return float(sigma_ref * np.sqrt(max(h, 1) / h_ref))


def mc_tbp(N, S, J, sigma_N=0.015, sigma_J=0.01, n=10000, seed=42, a=(13.5, 15.5, 23.6), tau=(0.183, 0.2335),
           rho=(0.371, 0.403, 0.563)):
    """Monte Carlo idéntico al de la sección 16.4 del notebook (mismos rangos de Ā, τ, ρ y misma semilla y orden de
    sorteos), pero con σ_N y σ_J parametrizables (relativos). Con sigma_N=0,015 y sigma_J=0,01 reproduce el original."""
    np.random.seed(seed)
    Ns = np.random.normal(N, sigma_N * N, n)
    As = np.random.triangular(a[0], a[1], a[2], n)
    ts = np.random.uniform(tau[0], tau[1], n)
    rs = np.random.triangular(rho[0], rho[1], rho[2], n)
    Js = np.random.normal(J, sigma_J * J, n)
    sim = Ns * S * As * ts / (Js * rs)
    return sim, dict(p5=float(np.percentile(sim, 5)), p50=float(np.percentile(sim, 50)), p95=float(np.percentile(sim, 95)),
                     sd=float(sim.std()))


# ==============================================================================================
# B) ESTABILIDAD TEMPORAL
# ==============================================================================================
def componentes_log(av, version="p4", hasta=2024):
    """Descomposición logarítmica EXACTA de TBP_C por cohorte. `av` = tbp_modelo_avanzado_1950_2035.csv.
    ln TBP = ln N + ln S65 + ln Ā + ln(τ/ρ) − ln J.   (S65 = 1−μ).
    version 'p4': N_4, J_star_4 (J* por sexo/edad de retiro), Ā_efectivo = TBP·J*/(N·S·τ/ρ) (incluye el reparto por sexo y
                  edad de retiro: es el Ā que cierra la identidad), ρ del escenario por cohorte.
    version 'p1': N_t, J65 (65+ para todos), Ā = A_eph, τ/ρ constantes (= TBP_p1·J/(N·S·Ā))."""
    a = av.set_index("cohorte") if "cohorte" in av.columns else av
    a = a.loc[:hasta]
    if version == "p4":
        y, N, J, S = a.TBP_C_p4, a.N_4, a.J_star_4, a.S_tot65
        tr = a.tau_t / a.rho_escenario
        Ae = y * J / (N * S * tr)
    elif version == "p1":
        y, N, J, S = a.TBP_C_p1, a.N_t, a.J65, a.S_tot65
        Ae = a.A_eph
        tr = y * J / (N * S * Ae)
    else:
        raise ValueError("version debe ser 'p4' o 'p1'")
    c = pd.DataFrame({"lnTBP": np.log(y), "N": np.log(N), "S65": np.log(S), "Abar": np.log(Ae),
                      "tau_rho": np.log(tr), "J": -np.log(J)})
    c["TBP"] = y.values
    c.index.name = "cohorte"
    assert np.allclose(c[["N", "S65", "Abar", "tau_rho", "J"]].sum(axis=1), c.lnTBP, atol=1e-9), "descomposición no cierra"
    return c


def _pend(y, x):
    return float(np.polyfit(x, y, 1)[0])


FACTORES = ["N", "S65", "Abar", "tau_rho", "J"]


def ventanas_moviles(comp, ancho=20):
    """Para cada ventana de `ancho` cohortes consecutivas: media de TBP, pendiente de ln TBP por cohorte (en %/cohorte) y
    contribución de cada factor (motor_baja = el que más empuja hacia abajo; motor_sube = el que más empuja hacia arriba). Como la pendiente MCO es lineal, la suma de las pendientes de los factores = pendiente
    de ln TBP (exacto). También se da el cambio extremo a extremo (Δln) por factor."""
    filas = []
    co = comp.index.values
    for i in range(0, len(co) - ancho + 1):
        w = comp.iloc[i:i + ancho]
        x = np.arange(ancho, dtype=float)
        r = dict(ini=int(co[i]), fin=int(co[i + ancho - 1]), media_TBP=float(w.TBP.mean()),
                 pend_lnTBP_pct=100 * _pend(w.lnTBP.values, x))
        for f in FACTORES:
            r[f"pend_{f}_pp"] = 100 * _pend(w[f].values, x)
            r[f"dln_{f}_pp"] = 100 * float(w[f].iloc[-1] - w[f].iloc[0])
        r["dln_total_pp"] = 100 * float(w.lnTBP.iloc[-1] - w.lnTBP.iloc[0])
        r["control_suma_pend"] = sum(r[f"pend_{f}_pp"] for f in FACTORES) - r["pend_lnTBP_pct"]
        # qué factor empuja más hacia abajo / hacia arriba en la ventana (mayor pendiente negativa / positiva)
        r["motor_baja"] = min(FACTORES, key=lambda ff: r[f"pend_{ff}_pp"])
        r["motor_sube"] = max(FACTORES, key=lambda ff: r[f"pend_{ff}_pp"])
        filas.append(r)
    return pd.DataFrame(filas)


def _rss(y, X):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    return float(e @ e), b


def chow_f(y, x, corte, k=2):
    """F de Chow. k=2: constante+tendencia en cada tramo (x<corte vs x>=corte); k=1: solo media. Descriptivo."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    X = np.column_stack([np.ones(len(x)), x])[:, :k]
    m = x < corte
    if m.sum() <= k or (~m).sum() <= k:
        return np.nan
    rp, _ = _rss(y, X)
    r1, _ = _rss(y[m], X[m]); r2, _ = _rss(y[~m], X[~m])
    return ((rp - (r1 + r2)) / k) / ((r1 + r2) / (len(y) - 2 * k))


def sup_f(y, x, cortes, k=2):
    """F de Chow para cada corte candidato; devuelve (Serie F por corte, corte del máximo, F máximo)."""
    F = pd.Series({int(c): chow_f(y, x, c, k) for c in cortes})
    return F, int(F.idxmax()), float(F.max())


def wald_hac(y, x, corte, lag=None):
    """Wald (2 restricciones: salto de nivel y cambio de pendiente en `corte`) con covarianza Newey-West (Bartlett).
    y = b0 + b1·t + b2·D + b3·D·(t−corte) + e,  D = 1[t>=corte]."""
    y = np.asarray(y, float); x = np.asarray(x, float); n = len(y)
    D = (x >= corte).astype(float)
    X = np.column_stack([np.ones(n), x, D, D * (x - corte)])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    L = int(np.floor(4 * (n / 100) ** (2 / 9))) if lag is None else lag
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, L + 1):
        G = Xe[l:].T @ Xe[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ S @ XtXi
    R = np.array([[0, 0, 1, 0], [0, 0, 0, 1]], float)
    rb = R @ b
    return float(rb @ np.linalg.inv(R @ V @ R.T) @ rb)


def sup_wald_hac(y, x, cortes, lag=None):
    W = pd.Series({int(c): wald_hac(y, x, c, lag) for c in cortes})
    return W, int(W.idxmax()), float(W.max())


def permutacion_bloques(y, x, cortes, estadistico="F", bloque=8, B=499, seed=1):
    """P-valor por permutación CIRCULAR por bloques del sup-estadístico. Nula: una tendencia lineal única + ruido con la
    autocorrelación local preservada (se reordenan bloques de `bloque` residuos). SALVEDAD: con una serie determinística,
    suave y con ciclos largos el 'ruido' no es ruido; este p-valor es una vara de comparación, no una prueba formal."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float); x = np.asarray(x, float); n = len(y)
    X = np.column_stack([np.ones(n), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    fit = X @ b; res = y - fit
    f = (lambda yy: sup_f(yy, x, cortes)[2]) if estadistico == "F" else (lambda yy: sup_wald_hac(yy, x, cortes)[2])
    obs = f(y)
    nb = int(np.ceil(n / bloque))
    sup = np.empty(B)
    for i in range(B):
        ini = rng.permutation(n)[:nb] if nb <= n else rng.integers(0, n, nb)
        idx = np.concatenate([(np.arange(bloque) + s0) % n for s0 in ini])[:n]
        sup[i] = f(fit + res[idx])
    p = (1 + int((sup >= obs).sum())) / (B + 1)
    return obs, p, sup


def tabla_quiebre(serie, cortes=range(2000, 2019), nombre="TBP_C_p4", bloques=(5, 15), B=499):
    """Tabla resumen: F por corte, sup-F y su argmax, Wald-HAC y su argmax, p-valores por bloques, y el F del corte 2011."""
    y = serie.values.astype(float); x = serie.index.values.astype(float)
    F, cF, fmax = sup_f(y, x, cortes)
    W, cW, wmax = sup_wald_hac(y, x, cortes)
    out = dict(serie=nombre, corte_supF=cF, supF=fmax, F_2011=float(F.get(2011, np.nan)), corte_supWaldHAC=cW, supWaldHAC=wmax)
    for bl in bloques:
        _, pF, _ = permutacion_bloques(y, x, cortes, "F", bl, B)
        _, pW, _ = permutacion_bloques(y, x, cortes, "W", bl, B)
        out[f"p_perm_supF_bloque{bl}"] = pF
        out[f"p_perm_supWald_bloque{bl}"] = pW
    por_corte = pd.DataFrame({"corte": list(F.index), "F_chow": F.values, "Wald_HAC": W.values})
    por_corte["serie"] = nombre
    return out, por_corte


# ==============================================================================================
# C) AUTOTEST (SINTÉTICO)
# ==============================================================================================
def _banner(t):
    print("=" * 78); print(t); print("=" * 78)


def autotest(verbose=True):
    """Pruebas con datos SINTÉTICOS (no son Argentina)."""
    if verbose:
        _banner("AUTOTEST tbp_estabilidad — DATOS SINTÉTICOS (no son Argentina)")
    # 1) error_pct e interpolación
    assert abs(float(error_pct(110, 100)) - 10.0) < 1e-12 and abs(float(error_pct(90, 100)) + 10.0) < 1e-12
    serie = {2021: 100.0, 2022: 200.0}
    assert abs(interpolar_a_fecha(serie, _dt.date(2021, 7, 1)) - 100.0) < 1e-9
    assert abs(interpolar_a_fecha(serie, _dt.date(2022, 1, 1)) - (100 + 100 * 184 / 365)) < 1e-9
    # 2) descomposición exacta: construir un av sintético con factores conocidos
    co = np.arange(1950, 2036)
    rng = np.random.default_rng(0)
    N = 5e5 * np.exp(0.01 * (co - 1950) - 0.0002 * (co - 1950) ** 2) * np.exp(rng.normal(0, .01, len(co)))
    S = np.linspace(0.7, 0.93, len(co)); Ab = 14 + np.sin(co / 9.0); J = 4e6 * np.exp(0.03 * (co - 1950) ** 0.8)
    tau = 0.2177; rho = np.where(co < 1960, 0.4, 0.403)
    tbp = N * S * Ab * tau / (rho * J)
    av = pd.DataFrame(dict(cohorte=co, N_4=N, N_t=N, S_tot65=S, J_star_4=J, J65=J, A_eph=Ab, tau_t=tau,
                           rho_escenario=rho, TBP_C_p4=tbp, TBP_C_p1=N * S * Ab * (tau / 0.403) / J))
    c4 = componentes_log(av, "p4"); c1 = componentes_log(av, "p1")
    assert np.allclose(c4.Abar, np.log(Ab[:75])) and np.allclose(c4.N, np.log(N[:75]))
    assert np.allclose(c1.tau_rho, np.log(tau / 0.403))
    # 3) ventanas: la suma de pendientes cierra y el número de ventanas es n−ancho+1
    v = ventanas_moviles(c4, 20)
    assert len(v) == 75 - 20 + 1 and np.allclose(v.control_suma_pend, 0, atol=1e-9)
    # 4) sup-F recupera un quiebre sintético (serie con quiebre de pendiente en 2005 + ruido AR(1))
    x = np.arange(1950, 2025, dtype=float)
    e = np.zeros(len(x))
    for i in range(1, len(x)):
        e[i] = 0.5 * e[i - 1] + rng.normal(0, 0.01)
    y_q = 0.5 + 0.0 * x - 0.02 * np.clip(x - 2005, 0, None) + e
    F, cF, fm = sup_f(y_q, x, range(2000, 2019))
    assert abs(cF - 2005) <= 3, cF
    W, cW, wm = sup_wald_hac(y_q, x, range(2000, 2019))
    assert abs(cW - 2005) <= 4, cW
    # 5) bajo la nula (tendencia lineal + AR) el p-valor por bloques NO debe ser sistemáticamente ínfimo
    y_n = 0.5 - 0.002 * (x - 1950) + e
    _, p_n, _ = permutacion_bloques(y_n, x, range(2000, 2019), "F", 8, B=199, seed=3)
    _, p_q, _ = permutacion_bloques(y_q, x, range(2000, 2019), "F", 8, B=199, seed=3)
    assert p_q < 0.05 and p_n > p_q
    # 6) sigma por horizonte y Monte Carlo (reproducibilidad y monotonía en σ)
    assert abs(sigma_por_horizonte(0.02, 9, 36) - 0.04) < 1e-12 and sigma_por_horizonte(0.02, 9, 36, "constante") == 0.02
    _, a = mc_tbp(4e5, 0.9, 1.5e7, 0.015, 0.01, n=2000); _, a2 = mc_tbp(4e5, 0.9, 1.5e7, 0.015, 0.01, n=2000)
    _, b = mc_tbp(4e5, 0.9, 1.5e7, 0.15, 0.05, n=2000)
    assert a == a2 and (b["p95"] - b["p5"]) > (a["p95"] - a["p5"])
    # 7) tamaño de pendientes verificables
    assert 15 < tamano_pendientes() < 30
    if verbose:
        print(f"OK: error %, interpolación, descomposición exacta, ventanas (sumas cierran), sup-F (corte hallado {cF}; Wald-HAC {cW}),")
        print(f"    permutación por bloques (p con quiebre {p_q:.3f} < p sin quiebre {p_n:.3f}), σ por horizonte, Monte Carlo.")
        _banner("FIN AUTOTEST — estos números NO son Argentina")
    return True


if __name__ == "__main__":
    autotest()
