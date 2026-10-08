# -*- coding: utf-8 -*-
"""
tbp_vintages.py — Backtest de proyecciones ANTIGUAS (ONU WPP 2012/2015/2017/2019 e INDEC 2013) contra lo ocurrido.

Pregunta: ¿cuánto se equivocaron las proyecciones de fecundidad/nacimientos y de población de 65+ que estaban
disponibles antes de 2020? Es el único "fuera de muestra" legítimo del proyecto: se valida el INSUMO (N, J), no el índice.

Datos de entrada (todos en el repositorio):
  datos/procesados/vintages_wpp_argentina.csv   filas de Argentina extraídas de los paquetes R `wpp2012/2015/2017/2019`
                                                (CRAN; datos de la División de Población de la ONU)
  datos/procesados/series_tbp_extraidas.csv     nacimientos DEIS y población 65+ ONU 2024 (referencia)
  datos/procesados/renaper_natalidad_2012_2025.csv   TGF observada (RENAPER)
INDEC 2013 (Serie Análisis Demográfico n.º 35, Cuadros 2 y 6) está transcripta abajo con su página.

AVISOS:
  * Los nacimientos "derivados" = TGF × Σ_a (porcentaje de fecundidad por edad_a / 5) × mujeres_a, con las mujeres de
    cada grupo quinquenal promediadas entre el inicio y el fin del período. Es una reconstrucción propia, no un dato de la ONU.
    Control: en 2015-2020, sin shock, el error de esa reconstrucción es de −2 % a +7 %.
  * La "población 65+ observada" usa WPP 2024 como referencia (no es un censo por edad). Para 2025 es proyección.
  * El período 2020-2025 se compara con 2020-2024 observado; con 2025 (provisorio) la TGF media baja de 1,39 a 1,34.
"""
import os, io, urllib.request
import numpy as np
import pandas as pd

RAW_BASE_VINT = "https://raw.githubusercontent.com/carolinamsfelipe/Tp-Indicadores/main/datos/procesados"
RUTAS_VINT = ["../datos/procesados", "datos/procesados", "github_staging/datos/procesados", "datos_tbp", "."]
EDADES_MUJERES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]
LANZAMIENTO = {"wpp2012": 2012, "wpp2015": 2015, "wpp2017": 2017, "wpp2019": 2019}

# INDEC 2013 (Serie 35). Cuadro 6 (p. 17): TGF. Cuadro 2 (pp. 29-30): población de 65+ = suma de 65-69 ... 100 y más, ambos sexos.
INDEC_2013_TGF = {2010: 2.41, 2015: 2.28, 2020: 2.18, 2025: 2.10, 2030: 2.05, 2035: 2.01, 2040: 1.98}
INDEC_2013_J65 = {2018: 4982425, 2019: 5103968, 2020: 5227722, 2021: 5353272, 2022: 5480183, 2023: 5608402, 2024: 5737818, 2025: 5868496}
# INDEC 2025 (proyección base Censo 2022; pp. 39-42) para contraste de 65+
INDEC_2025_J65 = {2022: 5529167, 2023: 5610238, 2024: 5711979, 2025: 5815927}


def _leer(nombre, rutas=None):
    for r in (rutas or RUTAS_VINT):
        p = os.path.join(r, nombre)
        if os.path.exists(p):
            return pd.read_csv(p)
    with urllib.request.urlopen(f"{RAW_BASE_VINT}/{nombre}") as f:
        return pd.read_csv(io.BytesIO(f.read()))


def cargar_entradas(rutas=None):
    v = _leer("vintages_wpp_argentina.csv", rutas)
    ser = _leer("series_tbp_extraidas.csv", rutas).set_index("year")
    ren = _leer("renaper_natalidad_2012_2025.csv", rutas).set_index("anio")
    return v, ser, ren


def _edad_inicio(a):
    return int(str(a).replace("+", "-").split("-")[0])


def _pop(v, vint, anio, edades, sexo_tablas):
    tot = 0.0
    for tab in sexo_tablas:
        d = v[(v.vintage == vint) & (v.tabla == tab) & (v.periodo.astype(str) == str(anio)) & (v.edad.isin(edades))]
        tot += d.valor.sum()
    return tot


def backtest_wpp(v, ser, ren):
    """Compara TGF, nacimientos (derivados) y población 65+ proyectados por cada edición de la ONU con lo observado."""
    tfr_obs = ren.tgf_hijos_por_mujer
    obs_tfr = {"2015-2020": tfr_obs.loc[2015:2019].mean(), "2020-2025": tfr_obs.loc[2020:2024].mean()}
    nac = ser.deis_nacimientos
    obs_b = {"2015-2020": nac.loc[2015:2019].mean(), "2020-2025": nac.loc[2020:2024].mean()}
    filas = []
    for vint, yr in LANZAMIENTO.items():
        for per in ("2015-2020", "2020-2025"):
            t = v[(v.vintage == vint) & (v.tabla == "tfrprojMed") & (v.periodo == per)]
            if t.empty:
                continue
            T = float(t.valor.iloc[0]); y0, y1 = int(per[:4]), int(per[5:])
            pct = np.array([float(v[(v.vintage == vint) & (v.tabla == "percentASFR") & (v.periodo == per) & (v.edad == a)].valor.iloc[0])
                            for a in EDADES_MUJERES]) / 100
            W = []
            for a in EDADES_MUJERES:
                w0 = _pop(v, vint, y0, [a], ["popF", "popFprojMed"]); w1 = _pop(v, vint, y1, [a], ["popF", "popFprojMed"])
                W.append((w0 + w1) / 2)
            births = float((T * pct / 5 * np.array(W)).sum()) * 1000
            hz = (y0 + y1) / 2 - yr
            filas.append((vint, per, "TGF (hijos por mujer)", T, obs_tfr[per], hz))
            filas.append((vint, per, "Nacimientos por año (derivado)", births, obs_b[per], hz))
        edades65 = sorted({a for a in v[(v.vintage == vint) & v.tabla.isin(["popF", "popFprojMed"])].edad.unique() if _edad_inicio(a) >= 65})
        for Y in (2020, 2025):
            p65 = _pop(v, vint, Y, edades65, ["popF", "popFprojMed"]) + _pop(v, vint, Y, edades65, ["popM", "popMprojMed"])
            if p65 > 0:
                filas.append((vint, str(Y), "Población de 65+ (miles)", p65, ser.un_pob_65mas_miles[Y], Y - yr))
    df = pd.DataFrame(filas, columns=["edicion", "periodo", "variable", "proyectado", "observado", "horizonte_anios"])
    df["error_pct"] = (df.proyectado / df.observado - 1) * 100
    return df


def backtest_indec2013(ser, ren):
    tfr = ren.tgf_hijos_por_mujer
    filas = []
    for y in (2015, 2020, 2025):
        filas.append(("INDEC 2013", str(y), "TGF (hijos por mujer)", INDEC_2013_TGF[y], float(tfr[y]), y - 2013, "2025 provisorio" if y == 2025 else ""))
    for y in (2022, 2023, 2024, 2025):
        filas.append(("INDEC 2013", str(y), "Población de 65+ (contra INDEC 2025)", INDEC_2013_J65[y], INDEC_2025_J65[y], y - 2013, ""))
    df = pd.DataFrame(filas, columns=["edicion", "periodo", "variable", "proyectado", "observado", "horizonte_anios", "nota"])
    df["error_pct"] = (df.proyectado / df.observado - 1) * 100
    return df


def traduccion_a_tbp(tbp_c_base, errores_N=(0.17, 0.25, 0.40)):
    """TBP_C es PROPORCIONAL a N: si N de una cohorte futura se equivocara ±x %, el TBP_C cambia ±x % (resto constante)."""
    return pd.DataFrame({"error_en_N": [f"±{int(e*100)} %" for e in errores_N],
                         "TBP_C_bajo": [tbp_c_base * (1 - e) for e in errores_N],
                         "TBP_C_alto": [tbp_c_base * (1 + e) for e in errores_N]})


def autotest(verbose=True):
    v, ser, ren = cargar_entradas()
    b = backtest_wpp(v, ser, ren)
    # 1) la reconstrucción de nacimientos es razonable cuando NO hubo shock (2015-2020): error entre −5 % y +10 %
    n1 = b[(b.variable.str.startswith("Nacimientos")) & (b.periodo == "2015-2020")]
    assert n1.error_pct.between(-5, 10).all(), n1
    # 2) en 2020-2025 todas las ediciones sobreestimaron la fecundidad por más de 40 %
    t2 = b[(b.variable.str.startswith("TGF")) & (b.periodo == "2020-2025")]
    assert len(t2) == 4 and (t2.error_pct > 40).all(), t2
    # 3) la población de 65+ tiene error pequeño (< 4 %) en 2020
    j20 = b[(b.variable.str.startswith("Población")) & (b.periodo == "2020")]
    assert j20.error_pct.abs().max() < 4, j20
    # 4) el error de fecundidad NO crece de forma sistemática con el horizonte (de 3,5 a 10,5 años va de +48 % a +58 %)
    assert t2.error_pct.max() - t2.error_pct.min() < 15
    i = backtest_indec2013(ser, ren)
    assert abs(i[(i.variable.str.startswith("TGF")) & (i.periodo == "2020")].error_pct.iloc[0] - 33.7) < 1.0
    assert traduccion_a_tbp(0.2, (0.1,)).TBP_C_alto.iloc[0] == 0.2 * 1.1
    if verbose:
        print("Autotest tbp_vintages OK: reconstrucción de nacimientos, errores de TGF, 65+ e INDEC 2013.")
    return b


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Backtest de proyecciones antiguas (ONU, INDEC 2013)")
    ap.add_argument("--autotest", action="store_true")
    a = ap.parse_args()
    if a.autotest:
        autotest()
    else:
        v, ser, ren = cargar_entradas()
        pd.set_option("display.width", 200)
        print(backtest_wpp(v, ser, ren).round(2).to_string(index=False)); print(); print(backtest_indec2013(ser, ren).round(2).to_string(index=False))
