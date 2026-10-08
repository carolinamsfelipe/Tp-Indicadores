# -*- coding: utf-8 -*-
"""
tbp_bootstrap.py — Bootstrap REAL (remuestreo por vivienda) de Ā con los microdatos de la EPH.

Reemplaza el "bootstrap" de la sección 16.3 del notebook principal, que tenía el error estándar escrito a mano
(se = 0,38) y calculaba IC = punto ± 1,96·se sin remuestrear nada.

Idea (para quien no es experta en estadística):
  * Ā sale de una muestra (la EPH). Si hubiéramos sorteado OTRA muestra, Ā daría un valor algo distinto. El "error estándar"
    mide cuánto cambiaría. Como no podemos volver a sortear la EPH, la simulamos: "remuestreamos" con reposición los datos
    que tenemos y recalculamos TODO (logit cohorte+edad, extrapolación, Ā) en cada réplica.
  * Unidad de remuestreo = la VIVIENDA (CODUSU), no la persona ni el trimestre. La EPH rota las viviendas (2 trimestres en la
    muestra, 2 fuera, 2 dentro): las MISMAS personas aparecen en varios trimestres y esas filas no son independientes.
    Remuestrear filas sueltas ignoraría esa dependencia y daría un error estándar demasiado chico (ver `bootstrap_ingenuo`).
  * Para que sea rápido, se precalculan por vivienda las sumas por celda (cohorte, edad): n, Σw, Σw·reg. Cada réplica es una
    suma ponderada con pesos multinomiales de viviendas.

QUÉ CAPTA: sólo la variabilidad MUESTRAL (con el diseño de cluster simplificado). QUÉ NO CAPTA: error de modelo (perfil por
edad común a todas las cohortes, confusión período/cohorte, EPH urbana, PP07H de la semana de referencia, reglas para
independientes, extrapolación "últimas k cohortes", S65 y Gompertz). Ver docs/seccion_17_bootstrap_abar.md.

Uso mínimo:
    import tbp_bootstrap as tb
    df  = tb.read_all_cluster(tb.find_eph_files(["datos/eph"]))        # con CODUSU y AGLOMERADO
    res = tb.bootstrap_abar(df, s65, B=500, seed=20260507)              # s65: Serie cohorte -> S65
    res["tabla"]                                                        # SE, IC95, sesgo por cohorte y regla

NO edita tbp_eph.py: importa de allí el pipeline (add_flags, fit_age_cohort_logit, extrapolar_alpha, densidad_modelada...).
"""
import os, io, sys, time, zipfile, tempfile, types
import numpy as np
import pandas as pd
from scipy import sparse


# ------------------------------------------------------------------ acceso a tbp_eph (módulo o notebook)
_FUNCS = ["add_flags", "fit_age_cohort_logit", "extrapolar_alpha", "densidad_modelada", "supervivencia_gompertz",
          "find_eph_files", "estimar_abar"]
_CONSTS = ["EDADES", "EDAD_MIN", "EDAD_MAX", "MIN_N_CELDA", "MIN_EDADES_COHORTE", "NEEDED", "OBLIGATORIAS"]


def _resolver_eph(ns=None):
    """Devuelve el objeto con las funciones de tbp_eph: `import tbp_eph` o, si no está, las definidas en el notebook."""
    try:
        import tbp_eph
        return tbp_eph
    except ImportError:
        pass
    ns = ns if ns is not None else globals()
    faltan = [n for n in _FUNCS + _CONSTS if n not in ns]
    if faltan:
        raise ImportError("No encuentro tbp_eph (ni importable ni cargado en el notebook). Faltan: %s. "
                          "Corré antes la celda del módulo de la sección 12." % faltan)
    obj = types.SimpleNamespace(**{n: ns[n] for n in _FUNCS + _CONSTS})
    if "ind_rule" not in obj.add_flags.__code__.co_varnames:
        raise ImportError("`add_flags` del notebook no es la de tbp_eph (otra versión). Corré la celda de la sección 12 de nuevo.")
    return obj


E = _resolver_eph()

REGLAS = ("solo_asalariados", "pp07i", "indep50")        # mismos nombres que A_bar_* de estimar_abar
_NQ = 5                                                  # n, w, wreg_solo, wreg_pp07i, wreg_indep


# ================================================================== 1) LECTOR CON CODUSU Y AGLOMERADO
def _leer_texto_cluster(handle):
    cab = handle.readline()
    sep = ";" if cab.count(";") >= cab.count(",") else ","
    handle.seek(0)
    need = set(E.NEEDED) | {"CODUSU", "AGLOMERADO"}
    return pd.read_csv(handle, sep=sep, usecols=lambda c: c.strip().upper() in need, low_memory=False,
                       dtype={"CODUSU": str})


def read_individual_cluster(src):
    """Como tbp_eph.read_individual pero conserva CODUSU (texto, identifica la VIVIENDA) y AGLOMERADO (numérico).
    CODUSU es la vivienda: se repite en los trimestres en que esa vivienda está en la muestra (rotación 2-2-2)."""
    if src["member"] is None:
        with open(src["path"], "r", encoding="latin-1", newline="") as f:
            df = _leer_texto_cluster(f)
    else:
        with zipfile.ZipFile(src["path"]) as z, z.open(src["member"]) as raw:
            df = _leer_texto_cluster(io.StringIO(raw.read().decode("latin-1")))
    df.columns = [c.strip().upper() for c in df.columns]
    for c in df.columns:
        if c != "CODUSU":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    faltan = (set(E.OBLIGATORIAS) | {"CODUSU"}) - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas {sorted(faltan)} en {src}.")
    for opt in ("CAT_OCUP", "PP07H", "PP07I", "CH04", "TRIMESTRE", "AGLOMERADO"):
        if opt not in df.columns:
            df[opt] = np.nan
    df["CODUSU"] = df["CODUSU"].astype(str).str.strip()
    return df


def read_all_cluster(srcs):
    return pd.concat([read_individual_cluster(s) for s in srcs], ignore_index=True)


# ================================================================== 2) PRECÁLCULO POR CLUSTER
def preparar(df, ind_share=0.5, unidad="vivienda", estratificar=False):
    """Precalcula, por unidad de remuestreo, las sumas por celda (cohorte, edad) para las tres reglas.

    unidad = "vivienda" (CODUSU; lo correcto) | "persona" (cada fila es una unidad; bootstrap INGENUO, sólo para comparar).
    estratificar=True: remuestrea viviendas DENTRO de cada aglomerado (el diseño de la EPH es estratificado por aglomerado).
    Devuelve un dict con la matriz dispersa Q (unidades x 5*celdas) y metadatos."""
    d_sol = E.add_flags(df, "solo_asalariados")
    d_pp = E.add_flags(df, "pp07i")
    d_ind = E.add_flags(df, "escenario", ind_share)
    assert d_sol.index.equals(d_pp.index) and d_sol.index.equals(d_ind.index)
    idx = d_sol.index
    if unidad == "vivienda":
        cl, _ = pd.factorize(df.loc[idx, "CODUSU"])
    elif unidad == "persona":
        cl = np.arange(len(idx))
    else:
        raise ValueError(unidad)
    K = int(cl.max()) + 1
    key = d_sol["cohorte"].values.astype(np.int64) * 100 + d_sol["edad"].values.astype(np.int64)
    ukey, cell = np.unique(key, return_inverse=True)
    nc = len(ukey)
    w = d_sol["w"].values
    vals = [np.ones(len(idx)), w, w * d_sol["reg"].values, w * d_pp["reg"].values, w * d_ind["reg"].values]
    rows = np.tile(cl, _NQ)
    cols = np.concatenate([cell + q * nc for q in range(_NQ)])
    Q = sparse.coo_matrix((np.concatenate(vals), (rows, cols)), shape=(K, _NQ * nc)).tocsr()
    est = None
    if estratificar:
        ag = df.loc[idx, "AGLOMERADO"].fillna(-1).values
        est_row = np.zeros(K, dtype=np.int64)
        est_row[cl] = pd.factorize(ag)[0]                  # una vivienda pertenece a un solo aglomerado
        est = est_row
    return {"Q": Q, "K": K, "nc": nc, "cohorte_celda": (ukey // 100).astype(int), "edad_celda": (ukey % 100).astype(int),
            "estratos": est, "unidad": unidad, "n_filas": len(idx), "ind_share": ind_share}


def _pesos(prep, rng):
    """Pesos multinomiales: cuántas veces entra cada unidad en la réplica (suma = K, o = K_h en cada estrato)."""
    K = prep["K"]
    if prep["estratos"] is None:
        return np.bincount(rng.integers(0, K, K), minlength=K).astype(float)
    est = prep["estratos"]; m = np.zeros(K)
    for h in np.unique(est):
        ids = np.flatnonzero(est == h)
        m[ids] = np.bincount(rng.integers(0, len(ids), len(ids)), minlength=len(ids))
    return m


# ================================================================== 3) PIPELINE SOBRE LAS SUMAS (idéntico a tbp_eph.pipeline)
def _abar_desde_sumas(prep, sums, S, cohortes, modo_extrap="ultimas_k", detalle=False):
    """Para cada regla: celdas -> logit cohorte+edad -> extrapolación de alpha -> densidad -> Ā. Misma lógica que
    tbp_eph.build_cells + fit_age_cohort_logit + extrapolar_alpha + densidad_modelada + abar_por_cohorte."""
    nc = prep["nc"]
    n = sums[0:nc]; w = sums[nc:2 * nc]
    out, det = {}, {}
    for q, regla in zip((2, 3, 4), REGLAS):
        wreg = sums[q * nc:(q + 1) * nc]
        keep = (n >= E.MIN_N_CELDA) & (w > 0)
        cells = pd.DataFrame({"cohorte": prep["cohorte_celda"][keep], "edad": prep["edad_celda"][keep], "n": n[keep],
                              "w": w[keep], "wreg": wreg[keep]})
        cells["dens"] = cells["wreg"] / cells["w"]
        fit = E.fit_age_cohort_logit(cells)
        alpha_c = E.extrapolar_alpha(fit, list(cohortes), modo=modo_extrap)
        dens = E.densidad_modelada(fit, alpha_c)
        out[regla] = (S * dens.values).sum(axis=1)
        if detalle:
            det[regla] = {"fit": fit, "dens": dens, "cells": cells}
    return (out, det) if detalle else out


def estimacion_puntual(prep, s65, cohortes=None, modo_extrap="ultimas_k"):
    """Ā con la muestra completa (todas las unidades con peso 1). Debe coincidir con tbp_eph.estimar_abar."""
    cohortes = list(s65.index) if cohortes is None else list(cohortes)
    S = E.supervivencia_gompertz(s65.reindex(cohortes).values)
    sums = np.asarray(prep["Q"].sum(axis=0)).ravel()
    out, det = _abar_desde_sumas(prep, sums, S, cohortes, modo_extrap, detalle=True)
    return pd.DataFrame(out, index=cohortes), det, S


def contribucion_extrapolado(det, S, cohortes):
    """Por cohorte y regla: ¿cuánto de Ā viene de edades OBSERVADAS y cuánto del perfil/modelo (extrapolado)?
    frac_edades_obs = Σ_{a observada} S(a)·d(a) / Ā ; alpha_extrapolado = la cohorte tiene < MIN_EDADES_COHORTE edades
    observadas (su nivel se toma de las últimas k cohortes o de las primeras k)."""
    filas = []
    for regla, dd in det.items():
        cells, fit, dens = dd["cells"], dd["fit"], dd["dens"]
        obs = cells.groupby("cohorte")["edad"].apply(set).to_dict()
        n_ed = fit["n_edades"]
        for i, c in enumerate(cohortes):
            ed = obs.get(c, set())
            mask = np.isin(E.EDADES, list(ed))
            tot = float((S[i] * dens.values[i]).sum())
            parte_obs = float((S[i] * dens.values[i])[mask].sum())
            filas.append({"cohorte": c, "regla": regla, "n_edades_obs": int(len(ed)),
                          "alpha_extrapolado": bool(int(n_ed.get(c, 0)) < E.MIN_EDADES_COHORTE),
                          "frac_edades_obs": parte_obs / tot if tot > 0 else np.nan})
    return pd.DataFrame(filas)


# ================================================================== 4) BOOTSTRAP
_G = {}                                                    # estado compartido con los procesos hijos (fork)


def _una_replica(b):
    prep, S, coh, modo, ss = _G["prep"], _G["S"], _G["coh"], _G["modo"], _G["ss"]
    rng = np.random.default_rng(ss[b])
    m = _pesos(prep, rng)
    sums = m @ prep["Q"]
    r = _abar_desde_sumas(prep, sums, S, coh, modo)
    return np.concatenate([r[k] for k in REGLAS])


def _correr(prep, s65, cohortes, B, seed, modo_extrap, n_jobs, verbose, etiqueta):
    cohortes = list(cohortes)
    S = E.supervivencia_gompertz(s65.reindex(cohortes).values)
    ss = np.random.SeedSequence(seed).spawn(B)               # una semilla por réplica: el resultado no depende de n_jobs
    _G.update(prep=prep, S=S, coh=cohortes, modo=modo_extrap, ss=ss)
    t0 = time.time()
    if n_jobs and n_jobs > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(n_jobs) as pool:
            filas = pool.map(_una_replica, range(B), chunksize=max(1, B // (n_jobs * 8)))
    else:
        filas = []
        for b in range(B):
            filas.append(_una_replica(b))
            if verbose and (b + 1) % max(1, B // 5) == 0:
                print(f"  [{etiqueta}] réplica {b + 1}/{B}  ({time.time() - t0:.0f} s)")
    arr = np.array(filas).reshape(B, len(REGLAS), len(cohortes))
    return arr, time.time() - t0


def _resumir(punto, arr, cohortes, nivel=0.95):
    a = (1 - nivel) / 2
    filas = []
    for j, regla in enumerate(REGLAS):
        x = arr[:, j, :]
        lo, hi = np.quantile(x, [a, 1 - a], axis=0)
        for i, c in enumerate(cohortes):
            p = float(punto[regla].iloc[i])
            filas.append({"cohorte": c, "regla": regla, "A_punto": p, "se": float(x[:, i].std(ddof=1)),
                          "ic95_lo": float(lo[i]), "ic95_hi": float(hi[i]), "sesgo_boot": float(x[:, i].mean() - p)})
    return pd.DataFrame(filas)


def bootstrap_abar(df, s65, B=500, seed=20260507, cohortes=None, modo_extrap="ultimas_k", ind_share=0.5,
                   estratificar=False, n_jobs=1, verbose=True, prep=None):
    """Bootstrap por VIVIENDA (CODUSU) de Ā. Reajusta todo el pipeline en cada réplica. Devuelve dict con
    'tabla' (long: cohorte x regla con A_punto, se, ic95_lo, ic95_hi, sesgo_boot, n_edades_obs, alpha_extrapolado,
    frac_edades_obs), 'replicas' (array B x 3 reglas x cohortes), 'punto', 'segundos', 'meta'."""
    t0 = time.time()
    cohortes = list(s65.index) if cohortes is None else list(cohortes)
    prep = prep or preparar(df, ind_share=ind_share, unidad="vivienda", estratificar=estratificar)
    punto, det, S = estimacion_puntual(prep, s65, cohortes, modo_extrap)
    t_prep = time.time() - t0
    arr, seg = _correr(prep, s65, cohortes, B, seed, modo_extrap, n_jobs, verbose, "vivienda")
    tab = _resumir(punto, arr, cohortes).merge(contribucion_extrapolado(det, S, cohortes), on=["cohorte", "regla"])
    meta = {"B": B, "seed": seed, "unidad": prep["unidad"], "estratificado": bool(estratificar), "n_unidades": prep["K"],
            "n_filas": prep["n_filas"], "ind_share": ind_share, "modo_extrap": modo_extrap, "segundos_prep": t_prep,
            "segundos_bootstrap": seg, "n_jobs": n_jobs}
    return {"tabla": tab, "replicas": arr, "punto": punto, "segundos": seg, "meta": meta, "prep": prep}


def bootstrap_ingenuo(df, s65, B=200, seed=20260507, cohortes=None, modo_extrap="ultimas_k", ind_share=0.5,
                      n_jobs=1, verbose=True):
    """Bootstrap INGENUO: remuestrea FILAS (personas-trimestre) como si fueran independientes. Subestima la incertidumbre
    porque ignora que la misma vivienda/persona aparece en varios trimestres. Sólo para mostrar cuánto."""
    cohortes = list(s65.index) if cohortes is None else list(cohortes)
    prep = preparar(df, ind_share=ind_share, unidad="persona")
    punto, det, S = estimacion_puntual(prep, s65, cohortes, modo_extrap)
    arr, seg = _correr(prep, s65, cohortes, B, seed, modo_extrap, n_jobs, verbose, "ingenuo")
    return {"tabla": _resumir(punto, arr, cohortes), "replicas": arr, "punto": punto, "segundos": seg}


# ================================================================== 5) TRASLADO A TBP_C Y TABLA FINAL
def trasladar_a_tbp(tabla, d, tau=0.2177, rho=0.403, tbp_col_p4=None):
    """TBP_C = N·S65·Ā·τ/(J·ρ) es PROPORCIONAL a Ā (N, S65, J, τ, ρ fijos) => los extremos del IC de TBP_C son
    TBP_C(punto) · (límite de Ā / Ā punto). `d`: DataFrame del notebook (cohorte, N_t, S65, J, E65).
    `tbp_col_p4`: opcional, Serie cohorte -> TBP_C de una versión más refinada (p. ej. R15['TBP_C_p4']); si se da, se usa esa base."""
    base = {}
    for regla in REGLAS:
        a = tabla[tabla["regla"] == regla].set_index("cohorte")["A_punto"]
        x = E_tbp_con_abar(d, a, tau, rho)
        base[regla] = x.set_index("cohorte")["TBP_C_Abar"]
    t = tabla.copy()
    t["TBP_C_punto"] = [base[r].get(c, np.nan) for r, c in zip(t["regla"], t["cohorte"])]
    if tbp_col_p4 is not None:
        t["TBP_C_p4_punto"] = [tbp_col_p4.get(c, np.nan) for c in t["cohorte"]]
    for k in ("se", "ic95_lo", "ic95_hi"):
        t[f"TBP_C_{k}"] = t["TBP_C_punto"] * (t[k] / t["A_punto"])
    if tbp_col_p4 is not None:
        for k in ("se", "ic95_lo", "ic95_hi"):
            t[f"TBP_C_p4_{k}"] = t["TBP_C_p4_punto"] * (t[k] / t["A_punto"])
    return t


def E_tbp_con_abar(d, a, tau, rho):
    x = d.set_index("cohorte").join(a.rename("A_bar_eph"), how="left")
    x["TBP_C_Abar"] = x["N_t"] * x["S65"] * x["A_bar_eph"] * tau / (x["J"] * rho)
    return x.reset_index()


def comparar_con_falso(tabla, cohorte=2024, regla="solo_asalariados", se_falso=0.38, punto_falso=14.57):
    """Compara el SE y el IC verdaderos con los escritos a mano (0,38 y [13,82; 15,31])."""
    r = tabla[(tabla["cohorte"] == cohorte) & (tabla["regla"] == regla)].iloc[0]
    falso = (punto_falso - 1.96 * se_falso, punto_falso + 1.96 * se_falso)
    return {"A_punto": r["A_punto"], "se_real": r["se"], "se_falso": se_falso, "razon_se": r["se"] / se_falso,
            "ic_real": (r["ic95_lo"], r["ic95_hi"]), "ic_falso": falso,
            "semiancho_rel_real_%": 100 * (r["ic95_hi"] - r["ic95_lo"]) / 2 / r["A_punto"],
            "semiancho_rel_falso_%": 100 * 1.96 * se_falso / punto_falso}


# ================================================================== 6) DATOS SINTÉTICOS Y AUTOTEST
def banner(txt="DATOS SINTÉTICOS — no son Argentina"):
    line = "#" * 78
    print("\n".join([line, "##" + txt.center(74) + "##", line]))


def generar_eph_sintetica_cluster(anios=range(2012, 2025), n_viv_por_celda=3, seed=7, efecto_vivienda=0.8):
    """EPH de juguete CON CODUSU: cada vivienda tiene un efecto común (todas sus personas tienden a ser parecidas), así que
    las filas de una misma vivienda están correlacionadas y el bootstrap por vivienda debe dar SE mayor que el ingenuo.
    Las viviendas se repiten en 2 trimestres consecutivos (rotación simplificada). NO son datos de Argentina."""
    rng = np.random.default_rng(seed); filas = []
    nviv = 0
    for y in anios:
        for q in (1, 2, 3, 4):
            for a in range(14, 71):
                for v in range(n_viv_por_celda):
                    nviv += 1
                    u = rng.normal(0, efecto_vivienda)            # efecto de la vivienda
                    for t in (0, 1):                               # la vivienda se entrevista dos trimestres seguidos
                        yy, qq = (y, q + t) if q + t <= 4 else (y + 1, 1)
                        if yy > anios[-1]:
                            continue
                        aa, k = a, 8
                        p = 1 / (1 + np.exp(-(-0.2 + 0.008 * (yy - aa - 1970) + 1.2 * np.exp(-((aa - 40) / 18.0) ** 2) - 1.0 + u)))
                        reg = rng.random(k) < p
                        filas.append(pd.DataFrame({"CODUSU": f"V{nviv:07d}", "AGLOMERADO": (nviv % 5) + 1, "ANO4": yy,
                                                   "TRIMESTRE": qq, "CH04": rng.integers(1, 3, k), "CH06": aa,
                                                   "ESTADO": 1, "CAT_OCUP": 3, "PP07H": np.where(reg, 1, 2), "PP07I": np.nan,
                                                   "PONDERA": rng.integers(300, 900, k)}))
    return pd.concat(filas, ignore_index=True)


def autotest(verbose=True, B=30):
    """Prueba con datos SINTÉTICOS: (1) lector con CODUSU (txt y zip); (2) el punto del bootstrap coincide con
    tbp_eph.estimar_abar; (3) reproducibilidad por semilla y por n_jobs; (4) con efecto de vivienda el SE por vivienda
    es mayor que el ingenuo; (5) con réplicas = muestra completa los pesos multinomiales suman K."""
    if verbose: banner()
    df = generar_eph_sintetica_cluster()
    coh = np.arange(1990, 2031)
    s65 = pd.Series(np.clip(0.70 + 0.0035 * (coh - 1950), 0.5, 0.97), index=coh)
    # (1) lector
    with tempfile.TemporaryDirectory() as tmp:
        sub = df[df["ANO4"] == 2015].copy()
        sub.columns = [c.lower() if c in ("CH04", "CH06", "ESTADO") else c for c in sub.columns]
        p = os.path.join(tmp, "usu_individual_T115.txt"); sub.to_csv(p, sep=";", index=False)
        zp = os.path.join(tmp, "EPH_usu_1_Trim_2015_txt.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.write(p, "usu_individual_T115.txt")
        os.remove(p)
        srcs = E.find_eph_files([tmp]); assert len(srcs) == 1
        lec = read_all_cluster(srcs)
        assert len(lec) == len(sub) and {"CODUSU", "AGLOMERADO"} <= set(lec.columns)
        assert lec["CODUSU"].iloc[0].startswith("V") and lec["CODUSU"].nunique() == sub["CODUSU"].nunique()
    # (2) punto == estimar_abar del módulo original
    ref = E.estimar_abar(df.drop(columns=["CODUSU", "AGLOMERADO"]), s65, cohortes=coh)
    prep = preparar(df)
    punto, det, S = estimacion_puntual(prep, s65, coh)
    for regla, col in zip(REGLAS, ("A_bar_solo_asalariados", "A_bar_pp07i", "A_bar_indep50")):
        assert np.allclose(punto[regla].values, ref[col].values, atol=1e-9), f"el punto no coincide con estimar_abar ({regla})"
    # (3) reproducibilidad
    r1 = bootstrap_abar(df, s65, B=B, seed=1, cohortes=coh, verbose=False, prep=prep)
    r2 = bootstrap_abar(df, s65, B=B, seed=1, cohortes=coh, verbose=False, prep=prep)
    r3 = bootstrap_abar(df, s65, B=B, seed=2, cohortes=coh, verbose=False, prep=prep)
    assert np.array_equal(r1["replicas"], r2["replicas"]) and not np.array_equal(r1["replicas"], r3["replicas"])
    if hasattr(os, "fork"):
        r4 = bootstrap_abar(df, s65, B=B, seed=1, cohortes=coh, verbose=False, prep=prep, n_jobs=2)
        assert np.array_equal(r1["replicas"], r4["replicas"]), "el resultado depende de n_jobs"
    # (4) cluster vs ingenuo (el efecto de vivienda y la repetición de viviendas deben ensanchar el SE)
    ing = bootstrap_ingenuo(df, s65, B=B, seed=1, cohortes=coh, verbose=False)
    c = 2005 if 2005 in coh else coh[len(coh) // 2]
    se_cl = r1["tabla"].query("cohorte == @c and regla == 'solo_asalariados'")["se"].iloc[0]
    se_in = ing["tabla"].query("cohorte == @c and regla == 'solo_asalariados'")["se"].iloc[0]
    assert se_cl > se_in, f"con efecto de vivienda el SE por vivienda ({se_cl:.3f}) debería superar al ingenuo ({se_in:.3f})"
    # (5) pesos multinomiales
    m = _pesos(prep, np.random.default_rng(0)); assert m.sum() == prep["K"]
    pe = preparar(df, estratificar=True); m = _pesos(pe, np.random.default_rng(0)); assert m.sum() == pe["K"]
    # IC contiene al punto en la mayoría de cohortes observadas
    t = r1["tabla"]; ok = ((t["ic95_lo"] <= t["A_punto"] + 0.5) & (t["A_punto"] <= t["ic95_hi"] + 0.5)).mean()
    assert ok > 0.9
    if verbose:
        print(f"[sintético] cohorte {c}: SE por vivienda = {se_cl:.3f} | SE ingenuo (por fila) = {se_in:.3f} "
              f"(razón {se_cl / se_in:.2f})")
        print("Autotest OK (lector con CODUSU, punto = estimar_abar, semilla/n_jobs reproducibles, cluster > ingenuo, pesos multinomiales).")
        banner("FIN AUTOTEST — estos números NO son Argentina")
    return r1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Bootstrap por vivienda de Ā (TBP)")
    ap.add_argument("--autotest", action="store_true")
    a = ap.parse_args()
    if a.autotest: autotest()
    else: ap.print_help()
