# -*- coding: utf-8 -*-
"""
tbp_montecarlo.py — Monte Carlo RIGUROSO para el TBP_C (reemplaza el diseño de la Sección 16.4).

    TBP_C(c) = N_c · S65_c · Ā_c · τ / (J*_c · ρ)                (años de prestación por jubilado; no contiene E_r)

QUÉ CORRIGE RESPECTO DE LA SECCIÓN 16 (resumen; el detalle está en docs/seccion_18_montecarlo.md)
 1) COMPARACIÓN PAREADA.  τ y ρ (y la regla de Ā) son factores COMUNES a todas las cohortes: si cambian, cambia también la
    cohorte 2000.  Por eso la pregunta "¿2024 < 2000?" se contesta con la RAZÓN TBP(2024)/TBP(2000) calculada con los MISMOS
    sorteos.  En la razón τ y ρ se cancelan EXACTAMENTE: solo cuentan N, S65, J* y el cociente Ā(2024)/Ā(2000).
 2) TRES CAPAS_MC DE INCERTIDUMBRE que NO se mezclan sin avisar:
        MUESTRAL   : error de muestreo de Ā (EPH).  Bootstrap real en abar_bootstrap_ic.csv (si existe; si no, queda en cero
                     y se rotula).  Es lo único que admite una "densidad" en sentido estricto.
        MEDICIÓN   : N (DEIS vs RENAPER: dos fuentes que miden lo mismo) y J* (ONU vs reponderado con nacimientos propios).
        ESCENARIO  : regla de Ā (asalariados / PP07I / independientes 50 %), τ (18,3 / 21,77 / 23,35 / 27 %), ρ (moratorias
                     40,3 / 48,3 / 56,3 %) y natalidad futura (3 escenarios).  Son DEFINICIONES o SUPUESTOS: se tratan como
                     categorías con pesos iguales (convención, NO probabilidades) y se reporta también el rango mín–máx.
 3) COHORTES FUTURAS (2030, 2035) con los 3 escenarios de natalidad y TENDENCIA (pendiente y razón 2000→2024), con abanico.
 4) VARIANZA DE PRIMER ORDEN por parámetro (índice de Sobol de primer orden por estratos, correlación de rangos y fracción
    exacta en logs) para el NIVEL y para la TENDENCIA.
 5) DESCOMPOSICIONES con el nombre correcto: "log exacta" y "varianza por covarianzas" (no es Campbell–Shiller ni un R²).

QUÉ NO ES: no es un test de hipótesis clásico (no hay H0 ni p-valor).  Es una cuantificación de incertidumbre CONDICIONAL a los
supuestos elegidos: "si las entradas se mueven dentro de estos rangos, el indicador se mueve así".

Todo el cálculo parte de los CSV del proyecto (datos/procesados). Sin datos nuevos inventados; el autotest usa datos
SINTÉTICOS rotulados.   Uso:  python src/tbp_montecarlo.py   (corre el autotest)
"""
import os
import numpy as np
import pandas as pd

RUTAS_MC = ["../datos/procesados", "datos/procesados", "github_staging/datos/procesados"]
COHORTES_MC = list(range(2000, 2036))
NAT_ESC_MC = ("persistencia", "recuperacion_lenta", "caida_adicional")
REGLAS_ABAR = ("solo_asalariados", "pp07i", "indep50")
ETQ_REGLA = {"solo_asalariados": "asalariados", "pp07i": "PP07I", "indep50": "indep. 50 %"}
CAPAS_MC = ("muestral", "medicion", "escenario")
SE_REL_PROVISORIO = 0.38 / 14.57        # SE citado en la Sec. 16.3 (hardcodeado, NO reproducible aquí): solo como sensibilidad rotulada
Q_MC = (5, 25, 50, 75, 95)


# ============================================================================================= 0) ENTRADAS
def _leer(nombre, rutas=None):
    """Lee un CSV de las rutas candidatas (más DATA/OUT del espacio global si existen). None si no está."""
    cand = list(rutas or RUTAS_MC)
    g = globals()
    for v in ("DATA", "OUT"):
        if isinstance(g.get(v), str):
            cand.append(g[v])
    for r in cand:
        f = os.path.join(r, nombre)
        if os.path.exists(f):
            return pd.read_csv(f, low_memory=False)
    return None


def cargar_insumos(rutas=None, modelo=None, d=None):
    """Junta las entradas del proyecto.  `modelo`: DataFrame del modelo avanzado (R15) si no está el CSV; `d`: tabla base del notebook."""
    ins = {}
    ma = _leer("tbp_modelo_avanzado_1950_2035.csv", rutas)
    if ma is None:
        ma = modelo if modelo is not None else (globals().get("R15") if globals().get("R15") is not None else globals().get("SAL15"))
        if ma is not None and "cohorte" not in ma.columns:
            ma = ma.reset_index()
    if ma is None:
        raise FileNotFoundError("Falta tbp_modelo_avanzado_1950_2035.csv (sección 15). Correr la sección 15 o copiar el CSV a datos/procesados.")
    ins["modelo"] = ma.set_index("cohorte")
    ab = _leer("abar_eph_por_cohorte.csv", rutas)
    if ab is None:
        raise FileNotFoundError("Falta abar_eph_por_cohorte.csv (sección 12).")
    ins["abar"] = ab.set_index("cohorte")
    ins["rho"] = _leer("anses_rho_tau_anual.csv", rutas)
    ins["series"] = _leer("series_tbp_extraidas.csv", rutas)
    ins["renaper"] = _leer("renaper_natalidad_2012_2025.csv", rutas)
    ins["jrw"] = _leer("tbp_cohortes_J_reponderado.csv", rutas)
    ins["nat"] = _leer("natalidad_escenarios_2025_2035.csv", rutas)
    if d is None:
        dd = _leer("tbp_argentina_cohortes_1950_2035.csv", rutas)
        d = dd
    ins["d"] = d
    ins["abar_ic"] = leer_abar_ic(rutas)
    return ins


def leer_abar_ic(rutas=None):
    """Lee el bootstrap real de Ā (abar_bootstrap_ic.csv) si existe.  Formato tolerante: busca columna de estimación puntual
    y de error estándar (o de límites del IC 95 %).  Devuelve {'se_rel', 'abar', 'fuente'} o None si no existe / no se entiende."""
    df = _leer("abar_bootstrap_ic.csv", rutas)
    if df is None:
        return None
    low = {c.lower(): c for c in df.columns}

    def _buscar(*pistas, excl=()):
        for c in low:
            if any(p in c for p in pistas) and not any(e in c for e in excl):
                return low[c]
        return None
    c_coh, c_reg = _buscar("cohorte"), _buscar("regla", "definicion", "variante")
    sub = df
    if c_coh is not None and (sub[c_coh] == 2024).any():
        sub = sub[sub[c_coh] == 2024]
    if c_reg is not None:
        m = sub[c_reg].astype(str).str.contains("asal", case=False)
        sub = sub[m] if m.any() else sub
    c_pt = _buscar("abar", "a_bar", "estim", "punto", "media", "mean", excl=("se", "ic", "lo", "hi"))
    c_se = _buscar("se", "error_est", excl=("rese",))
    c_lo, c_hi = _buscar("ic_lo", "ic_inf", "lo", "p2_5", "low"), _buscar("ic_hi", "ic_sup", "hi", "p97_5", "high")
    try:
        pt = float(sub[c_pt].iloc[0])
        if c_se is not None:
            se = float(sub[c_se].iloc[0])
        else:
            se = (float(sub[c_hi].iloc[0]) - float(sub[c_lo].iloc[0])) / (2 * 1.96)
        return dict(se_rel=se / pt, abar=pt, fuente="abar_bootstrap_ic.csv (bootstrap real)")
    except Exception as e:                                         # formato no reconocido: no se inventa nada
        print("AVISO: no pude interpretar abar_bootstrap_ic.csv (%s); la capa muestral queda en cero." % e)
        return None


# ============================================================================================= 1) CALIBRACIÓN CON DATOS DEL PROYECTO
def calibrar_incertidumbre(ins, tau0=0.2177, rho0=None, se_rel_abar=None, verbose=False):
    """Fija cada distribución/escenario con un dato del proyecto y deja la JUSTIFICACIÓN escrita.  Devuelve dict `par`."""
    just = {}
    # --- N: DEIS vs RENAPER (2012-2024)
    sig_N = 0.02
    ser, ren = ins.get("series"), ins.get("renaper")
    if ser is not None and ren is not None:
        deis = ser.set_index("year")["deis_nacimientos"]
        r = ren.set_index("anio")["nacimientos_identificados_miles"] * 1000
        idx = [a for a in r.index if a in deis.index and a <= 2024 and np.isfinite(deis[a])]
        rat = (r.loc[idx] / deis.loc[idx])
        sig_N = float(np.std(np.log(rat), ddof=1))
        just["N"] = ("medición: Normal log, σ = desvío de ln(RENAPER/DEIS) %d-%d = %.2f %% (razón entre %.3f y %.3f; conservador: no se divide por √2)"
                     % (min(idx), max(idx), 100 * sig_N, rat.min(), rat.max()))
    else:
        just["N"] = "medición: σ = 2 % (SIN el archivo RENAPER: valor de trabajo, no calibrado)"
    # --- J*: ONU vs reponderado con nacimientos propios (sección 10)
    sig_J = 0.03
    jr = ins.get("jrw")
    if jr is not None:
        j = jr[jr.escenario == "persistencia"].set_index("cohorte")
        dif = (j.J_reponderado / j.J_onu - 1).loc[2000:2024]
        sig_J = float(np.sqrt((dif ** 2).mean()))
        just["J"] = ("medición/modelo: Normal log, σ = RMS de J_reponderado/J_ONU-1 en cohortes 2000-2024 = %.2f %% (media %.2f %%: el reponderado "
                     "es sistemáticamente menor; se usa como ESCALA del error, centrado en 0)" % (100 * sig_J, 100 * dif.mean()))
    else:
        just["J"] = "medición: σ = 3 % (SIN el archivo de J reponderado: valor de trabajo, no calibrado)"
    # --- ρ: escenarios de moratorias
    rh = ins.get("rho")
    if rh is not None:
        u = rh.sort_values("anio").iloc[-1]
        r_tot, r_sin = float(u["rho"]), float(u["rho_sin_moratoria"])
    else:
        r_tot, r_sin = 0.403, 0.563
    rho0 = r_tot if rho0 is None else rho0
    rho_esc = {"moratorias persisten (%.1f %%)" % (100 * r_tot): r_tot,
               "mitad de moratorias (%.1f %%)" % (100 * (r_tot + r_sin) / 2): (r_tot + r_sin) / 2,
               "sin moratorias (%.1f %%)" % (100 * r_sin): r_sin}
    just["rho"] = ("escenario: 3 categorías (ρ 2023 publicado %.1f %%; sin moratorias %.1f %%); NO se usa el mínimo histórico 37,1 %% porque "
                   "la cohorte se retira en 2065+ y la serie digitalizada 2009-2023 tiene error < 0,1 pp" % (100 * r_tot, 100 * r_sin))
    tau_esc = {"efectiva SIPA ~18,3 % (supuesto)": 0.183, "nominal inc.(a) 21,77 %": 0.2177,
               "inc.(b) 23,35 %": 0.2335, "sector público 27 %": 0.27}
    just["tau"] = "escenario: 4 categorías (alícuotas nominales del Anuario ANSES p.39 + efectiva ~18,3 % que es un SUPUESTO); sin serie histórica verificada"
    # --- Ā
    ic = ins.get("abar_ic")
    if se_rel_abar is None:
        se_rel_abar = ic["se_rel"] if ic else 0.0
    just["Abar_muestral"] = (ic["fuente"] + ": SE relativo = %.2f %%" % (100 * se_rel_abar) if ic and se_rel_abar == ic["se_rel"] else
                             ("SE relativo = %.2f %% (fijado a mano)" % (100 * se_rel_abar) if se_rel_abar > 0 else
                              "SIN bootstrap real todavía (abar_bootstrap_ic.csv no existe): capa muestral = 0; rotulado"))
    just["Abar_regla"] = "escenario/definición: 3 reglas de la EPH (asalariados, PP07I, independientes 50 %); ver abar_eph_por_cohorte.csv"
    just["natalidad"] = "escenario: 3 escenarios de la sección 9 (persistencia, recuperación lenta, caída adicional) desde 2025"
    ab = ins["abar"]
    A = {r: ab["A_bar_" + r] for r in REGLAS_ABAR}
    return dict(tau0=tau0, rho0=rho0, sig_N=sig_N, sig_J=sig_J, se_rel_abar=se_rel_abar,
                tau_esc=tau_esc, rho_esc=rho_esc, A=A,
                corr=dict(N=0.0, J=0.5, Abar=1.0), justificacion=just)


def base_por_escenario(ins, cohortes=COHORTES_MC):
    """TBP_C_p4 por cohorte para cada escenario de natalidad (una columna por escenario; iguales hasta 2024)."""
    ma = ins["modelo"]
    out = {}
    for e in NAT_ESC_MC:
        c = "TBP_C_p4_" + e
        out[e] = ma[c] if c in ma.columns else ma["TBP_C_p4"]
    return pd.DataFrame(out).loc[cohortes]


# ============================================================================================= 2) SIMULACIÓN
def _choque(rng, n, nc, r):
    """Choque estándar n×nc con correlación r entre cohortes: sqrt(r)·común + sqrt(1-r)·propio."""
    comun, propio = rng.standard_normal((n, 1)), rng.standard_normal((n, nc))
    return np.sqrt(r) * comun + np.sqrt(1 - r) * propio


def simular(par, base, n=20000, seed=42, capas=CAPAS_MC, nat="mezcla", cohortes=None):
    """Simula `n` sorteos conjuntos para todas las cohortes (mismos τ, ρ, regla y choque común en todas: PAREADO).
    capas: subconjunto de ('muestral','medicion','escenario'). Una capa apagada deja su factor en 1 (valor base).
    nat: nombre de escenario de natalidad, o 'mezcla' (sortea uno por corrida, pesos iguales).
    Se sortea SIEMPRE el mismo número de variables, así que dos corridas con la misma semilla y distintas capas comparten los sorteos.
    Devuelve dict con tbp (n×nc), factores en logs por grupo (n×nc o n×1), índices de categorías."""
    co = list(cohortes if cohortes is not None else base.index)
    nc = len(co)
    rng = np.random.default_rng(seed)
    tau_v, rho_v = np.array(list(par["tau_esc"].values())), np.array(list(par["rho_esc"].values()))
    i_tau, i_rho = rng.integers(0, len(tau_v), n), rng.integers(0, len(rho_v), n)
    i_reg, i_nat = rng.integers(0, len(REGLAS_ABAR), n), rng.integers(0, len(NAT_ESC_MC), n)
    zN = _choque(rng, n, nc, par["corr"]["N"])
    zJ = _choque(rng, n, nc, par["corr"]["J"])
    zA = _choque(rng, n, nc, par["corr"]["Abar"])
    L = {}
    z0 = np.zeros((n, nc))
    L["N"] = par["sig_N"] * zN if "medicion" in capas else z0
    L["J"] = -par["sig_J"] * zJ if "medicion" in capas else z0                       # J está en el denominador
    L["Abar_muestral"] = par["se_rel_abar"] * zA if "muestral" in capas else z0
    A = pd.DataFrame(par["A"]).loc[co]
    a_base = A["solo_asalariados"].values
    if "escenario" in capas:
        fr = np.stack([np.log(A[r].values / a_base) for r in REGLAS_ABAR])          # reglas × cohortes
        L["Abar_regla"] = fr[i_reg]
        L["tau"] = np.repeat(np.log(tau_v[i_tau] / par["tau0"])[:, None], nc, 1)
        L["rho"] = np.repeat(np.log(par["rho0"] / rho_v[i_rho])[:, None], nc, 1)
    else:
        L["Abar_regla"], L["tau"], L["rho"] = z0, z0, z0
    lb = np.log(base[list(NAT_ESC_MC)].loc[co].values)                                  # cohortes × escenarios
    if nat == "mezcla":
        L["natalidad"] = lb[:, i_nat].T - lb[:, [0]].T                               # respecto de 'persistencia'
        lbase = lb[:, 0][None, :]
    else:
        k = NAT_ESC_MC.index(nat)
        L["natalidad"] = z0
        lbase = lb[:, k][None, :]
    lt = lbase + sum(L.values())
    return dict(tbp=np.exp(lt), L=L, lbase=np.repeat(lbase, n, 0), cohortes=co, n=n, seed=seed, capas=tuple(capas), nat=nat,
                i=dict(tau=i_tau, rho=i_rho, regla=i_reg, nat=i_nat))


def idx_c(sim, c):
    return sim["cohortes"].index(c)


def cuantiles(x, qs=Q_MC):
    p = np.percentile(x, qs)
    return dict({"P%d" % q: float(v) for q, v in zip(qs, p)}, media=float(np.mean(x)), minimo=float(np.min(x)), maximo=float(np.max(x)))


# ---------------------------------------------------------------------------------------- razón pareada y no pareada
def razon_pareada(sim, c1=2024, c0=2000):
    """TBP(c1)/TBP(c0) con los MISMOS sorteos.  τ y ρ se cancelan: solo importan N, S65, J* y Ā(c)."""
    return sim["tbp"][:, idx_c(sim, c1)] / sim["tbp"][:, idx_c(sim, c0)]


def razon_no_pareada(sim, c1=2024, c0=2000, seed=1):
    """CONTRAEJEMPLO (incorrecto): TBP(c1) de un sorteo contra TBP(c0) de OTRO sorteo (mezcla de escenarios independientes)."""
    p = np.random.default_rng(seed).permutation(sim["n"])
    return sim["tbp"][:, idx_c(sim, c1)] / sim["tbp"][p, idx_c(sim, c0)]


def pendiente(sim, c0=2000, c1=2024):
    """Pendiente MCO de ln(TBP) sobre la cohorte, en % por año (puntos log ×100), cohortes c0..c1, por sorteo."""
    cs = [c for c in sim["cohortes"] if c0 <= c <= c1]
    x = np.array(cs, float) - np.mean(cs)
    w = x / (x ** 2).sum()
    lt = np.log(sim["tbp"][:, [idx_c(sim, c) for c in cs]])
    return 100 * lt @ w, w, cs


def pesos_pendiente(cohortes, c0=2000, c1=2024):
    cs = [c for c in cohortes if c0 <= c <= c1]
    x = np.array(cs, float) - np.mean(cs)
    w = np.zeros(len(cohortes))
    for c, wi in zip(cs, x / (x ** 2).sum()):
        w[cohortes.index(c)] = wi
    return w


# ---------------------------------------------------------------------------------------- réplica del diseño de la Sección 16
def replica_seccion16(ins, n=10000):
    """Reproduce EXACTAMENTE el Monte Carlo de la Sección 16.4 (semilla 42, mismas distribuciones) para poder comparar."""
    c24 = ins["modelo"].loc[2024]
    c00 = ins["modelo"].loc[2000]
    np.random.seed(42)
    Nb, Jb, Sb = float(c24["N_4"]), float(c24["J_star_4"]), float(c24["S_tot65"])
    N = np.random.normal(Nb, 0.015 * Nb, n)
    A = np.random.triangular(13.5, 15.5, 23.6, n)
    tau = np.random.uniform(0.183, 0.2335, n)
    rho = np.random.triangular(0.371, 0.403, 0.563, n)
    J = np.random.normal(Jb, 0.01 * Jb, n)
    y = N * Sb * A * tau / (J * rho)
    ref00 = float(c00["TBP_C_p4"])
    return dict(y=y, ref2000=ref00, base2024=float(c24["TBP_C_p4"]), p_supera=float(np.mean(y >= ref00)), **cuantiles(y))


# ============================================================================================= 3) VARIANZA DE PRIMER ORDEN
def _indice_estratos(Y, f, nbins=50, max_cat=12):
    """Var(E[Y|f])/Var(Y) estimado por estratos: categorías si f tiene pocos valores distintos; si no, `nbins` cuantiles.
    Dos sesgos chicos y de signo opuesto: al alza ≈ (estratos-1)/n por ruido muestral y a la baja por aplanar cada estrato
    (≈ -0,5 puntos con 50 estratos; verificado en el autotest)."""
    vy = np.var(Y)
    if vy <= 0:
        return 0.0
    u = np.unique(np.round(f, 12))
    if len(u) <= max_cat:
        g = np.searchsorted(u, np.round(f, 12))
    else:
        edges = np.quantile(f, np.linspace(0, 1, nbins + 1)[1:-1])
        g = np.searchsorted(edges, f)
    s = np.bincount(g, weights=Y); k = np.bincount(g)
    ok = k > 0
    m = s[ok] / k[ok]
    return float(np.sum(k[ok] * (m - Y.mean()) ** 2) / len(Y) / vy)


def _rangos(x):
    return pd.Series(x).rank().values


def indices_primer_orden(sim, pesos, nombre_y="nivel", en_logs_y=True, grupos=None):
    """Índices de primer orden por GRUPO de parámetros.  `pesos` (vector sobre cohortes) define el resultado:
        nivel de la cohorte c : e_c ;  log-razón c1/c0 : e_c1 - e_c0 ;  pendiente : pesos_pendiente.
    Como ln TBP es EXACTAMENTE la suma de los logs de los factores, el resultado en logs es aditivo y el aporte de cada grupo es
    contrib_k = L_k @ pesos.  Se devuelven 3 medidas:
        frac_log  : Var(contrib_k)/Var(ln Y)                 (exacta; suma 1 porque los grupos son independientes)
        sobol_1   : Var(E[Y|grupo k])/Var(Y), con Y en la escala indicada (nivel en años, razón, o pendiente)
        spearman2 : (correlación de rangos entre Y y el aporte)²"""
    w = np.asarray(pesos, float)
    L = sim["L"]
    grupos = grupos or [k for k in L if np.any(L[k] != 0)]
    contrib = {k: L[k] @ w for k in grupos}
    lny = sim["lbase"] @ w + sum(L[k] @ w for k in L)
    Y = np.exp(lny) if en_logs_y else lny
    v = np.var(lny)
    filas = []
    for k in grupos:
        fk = contrib[k]
        r = float(np.corrcoef(_rangos(Y), _rangos(fk))[0, 1]) if np.var(fk) > 0 else 0.0
        filas.append(dict(resultado=nombre_y, grupo=k, frac_log=float(np.var(fk) / v) if v > 0 else 0.0,
                          sobol_1=_indice_estratos(Y, fk), spearman2=r ** 2))
    df = pd.DataFrame(filas)
    if len(df):
        df.loc[len(df)] = dict(resultado=nombre_y, grupo="(suma de primer orden)", frac_log=df.frac_log.sum(),
                               sobol_1=df.sobol_1.sum(), spearman2=np.nan)
    return df


# ============================================================================================= 4) DESCOMPOSICIONES (nombres correctos)
def descomposicion_log_exacta(modelo, d, c0=2000, c1=2024):
    """DESCOMPOSICIÓN LOGARÍTMICA EXACTA de ln TBP_C(c1) - ln TBP_C(c0) (contabilidad de crecimiento): suma EXACTA de los cambios en
    log de cada factor; con τ y ρ constantes no contribuyen.  Dos ESPECIFICACIONES (ambas válidas, responden preguntas distintas):
      A) 'simple': J = población 65+ total, Ā constante      -> N, S65, J (Ā, τ, ρ aportan 0).
      B) 'avanzada': J* (varones 65+, mujeres 60+), Ā EPH variable y sexo/retiro -> N, S65, J*, Ā y composición por sexo (residuo)."""
    dd = d.set_index("cohorte")
    a1, a0 = dd.loc[c1], dd.loc[c0]
    tot_A = np.log(a1.N_t * a1.S65 / a1.J) - np.log(a0.N_t * a0.S65 / a0.J)
    fa = {"N": np.log(a1.N_t / a0.N_t), "S65": np.log(a1.S65 / a0.S65), "J (65+)": -np.log(a1.J / a0.J), "Ā": 0.0}
    m1, m0 = modelo.loc[c1], modelo.loc[c0]
    tot_B = np.log(m1.TBP_C_p4 / m0.TBP_C_p4)
    fb = {"N": np.log(m1.N_4 / m0.N_4), "S65": np.log(m1.S_tot65 / m0.S_tot65), "J*": -np.log(m1.J_star_4 / m0.J_star_4),
          "Ā (EPH total)": np.log(m1.A_eph / m0.A_eph)}
    fb["composición sexo/retiro (residuo)"] = tot_B - sum(fb.values())
    filas = []
    for esp, f, tot in (("A: J=65+, Ā constante", fa, tot_A), ("B: J*, Ā EPH variable", fb, tot_B)):
        for k, v in f.items():
            filas.append(dict(especificacion=esp, componente=k, log_puntos=float(v), pct_de_la_caida=float(100 * v / tot)))
        filas.append(dict(especificacion=esp, componente="TOTAL Δln TBP_C", log_puntos=float(tot), pct_de_la_caida=100.0))
    return pd.DataFrame(filas)


def descomposicion_varianza_cov(modelo, c0=2000, c1=2024, ddof_consistente=True):
    """DESCOMPOSICIÓN DE VARIANZA POR COVARIANZAS: con Δln TBP = Σ_k Δx_k (x_k = ln de cada factor con su signo),
        Var(Δln TBP) = Σ_k Cov(Δx_k, Δln TBP)   =>   participación_k = Cov(Δx_k, Δln TBP)/Var(Δln TBP),  Σ_k participación_k = 100 %.
    No es un R² (puede ser negativa o > 100 %) ni Campbell–Shiller.  Usa el MISMO ddof en cov y var (el código original de la Sección 16
    mezclaba np.cov (ddof=1) con np.var (ddof=0), lo que infla todas las participaciones en n/(n-1))."""
    sub = modelo.loc[c0:c1]
    y = np.diff(np.log(sub.TBP_C_p4))
    comp = {"N": np.diff(np.log(sub.N_4)), "S65": np.diff(np.log(sub.S_tot65)), "J*": -np.diff(np.log(sub.J_star_4))}
    comp["Ā y sexo/retiro (residuo)"] = y - sum(comp.values())
    dd = 1 if ddof_consistente else 0
    var = np.var(y, ddof=1 if ddof_consistente else 0)
    filas = [dict(componente=k, participacion_pct=float(100 * np.cov(v, y, ddof=dd)[0, 1] / var)) for k, v in comp.items()]
    if not ddof_consistente:                                                  # réplica del cálculo original (np.cov ddof=1 / np.var ddof=0)
        filas = [dict(componente=k, participacion_pct=float(100 * np.cov(v, y)[0, 1] / np.var(y))) for k, v in comp.items()]
    df = pd.DataFrame(filas)
    df.loc[len(df)] = dict(componente="SUMA", participacion_pct=df.participacion_pct.sum())
    return df


# ============================================================================================= 5) ORQUESTACIÓN
def _fila(bloque, coh, nat, capa, metrica, valor, nota=""):
    return dict(bloque=bloque, cohorte=coh, escenario_nat=nat, capa=capa, metrica=metrica, valor=valor, nota=nota)


def correr(ins, n=20000, seed=42, verbose=True, par=None):
    """Corre todo el análisis y devuelve un dict `res` (tablas + simulaciones para graficar)."""
    par = par or calibrar_incertidumbre(ins)
    cs = COHORTES_MC
    base = base_por_escenario(ins, cs)
    filas = []
    capas_modos = {"medicion": ("medicion",), "escenario": ("escenario",), "conjunto": CAPAS_MC}
    if par["se_rel_abar"] > 0:
        capas_modos = {"muestral": ("muestral",), **capas_modos}
    sims = {}
    # ---- NIVEL por cohorte, capa y escenario de natalidad
    for modo, capas in capas_modos.items():
        for e in NAT_ESC_MC:
            s_ = simular(par, base, n, seed, capas, nat=e)
            sims[(modo, e)] = s_
            for c in (2000, 2024, 2030, 2035):
                if c <= 2024 and e != NAT_ESC_MC[0]:
                    continue
                q = cuantiles(s_["tbp"][:, idx_c(s_, c)])
                for k, v in q.items():
                    filas.append(_fila("nivel", c, e if c > 2024 else "n/a", modo, k, v))
    # ---- punto base
    for c in (2000, 2024, 2030, 2035):
        for e in NAT_ESC_MC:
            if c <= 2024 and e != NAT_ESC_MC[0]:
                continue
            filas.append(_fila("nivel", c, e if c > 2024 else "n/a", "base", "punto", float(base.loc[c, e])))
    sc = sims[("conjunto", NAT_ESC_MC[0])]
    mez = simular(par, base, n, seed, CAPAS_MC, nat="mezcla")
    sims["mezcla"] = mez
    # ---- RAZÓN pareada 2024/2000 (y contraejemplos)
    p_pareada = {}
    for modo in capas_modos:
        r = razon_pareada(sims[(modo, NAT_ESC_MC[0])])
        q = cuantiles(r)
        for k, v in q.items():
            filas.append(_fila("razon_2024_2000", "2024/2000", "n/a", modo, k, v))
        filas.append(_fila("razon_2024_2000", "2024/2000", "n/a", modo, "P(razon<1)", float(np.mean(r < 1))))
        p_pareada[modo] = float(np.mean(r < 1))
    r_cj = razon_pareada(sc)
    r_unp = razon_no_pareada(sc)
    filas.append(_fila("razon_2024_2000", "2024/2000", "n/a", "conjunto_NO_pareado(incorrecto)", "P(2024>=2000)", float(np.mean(r_unp >= 1)),
                       "contraejemplo: sorteos independientes para cada cohorte"))
    for k, v in cuantiles(r_unp).items():
        filas.append(_fila("razon_2024_2000", "2024/2000", "n/a", "conjunto_NO_pareado(incorrecto)", k, v))
    # τ y ρ se cancelan: quitando sus factores (en logs) la razón no cambia
    lt = np.log(sc["tbp"]) - sc["L"]["tau"] - sc["L"]["rho"]
    cancel = float(np.max(np.abs(np.log(r_cj) - (lt[:, idx_c(sc, 2024)] - lt[:, idx_c(sc, 2000)]))))
    # ---- diseño original de la Sección 16
    rep = replica_seccion16(ins)
    for k in ("P5", "P25", "P50", "P75", "P95", "media"):
        filas.append(_fila("seccion16_original", 2024, "n/a", "original", k, rep[k]))
    filas.append(_fila("seccion16_original", 2024, "n/a", "original", "P(2024>=0,312 fijo)", rep["p_supera"]))
    # ---- TENDENCIA 2000→2024
    sl = {}
    for modo in capas_modos:
        s_ = sims[(modo, NAT_ESC_MC[0])]
        pend, w, _ = pendiente(s_)
        sl[modo] = pend
        for k, v in cuantiles(pend).items():
            filas.append(_fila("pendiente_2000_2024_pct_anual", "2000-2024", "n/a", modo, k, v))
        filas.append(_fila("pendiente_2000_2024_pct_anual", "2000-2024", "n/a", modo, "P(pendiente<0)", float(np.mean(pend < 0))))
    pb, _, _ = pendiente(simular(par, base, 1, seed, (), nat=NAT_ESC_MC[0]))
    filas.append(_fila("pendiente_2000_2024_pct_anual", "2000-2024", "n/a", "base", "punto", float(pb[0])))
    # ---- variación 2024→c futuras por escenario de natalidad
    for e in NAT_ESC_MC:
        s_ = sims[("conjunto", e)]
        for c in (2030, 2035):
            rr = s_["tbp"][:, idx_c(s_, c)] / s_["tbp"][:, idx_c(s_, 2024)]
            for k, v in cuantiles(rr).items():
                filas.append(_fila("razon_futura_vs_2024", c, e, "conjunto", k, v))
            filas.append(_fila("razon_futura_vs_2024", c, e, "conjunto", "P(razon>1)", float(np.mean(rr > 1))))
            rr0 = s_["tbp"][:, idx_c(s_, c)] / s_["tbp"][:, idx_c(s_, 2000)]
            filas.append(_fila("razon_futura_vs_2000", c, e, "conjunto", "P(razon<1)", float(np.mean(rr0 < 1))))
            filas.append(_fila("razon_futura_vs_2000", c, e, "conjunto", "P50", float(np.median(rr0))))
    # ---- ABANICO por cohorte (conjunto, por escenario) y en índice 2000=100
    ab = []
    for e in NAT_ESC_MC:
        s_ = sims[("conjunto", e)]
        qs = np.percentile(s_["tbp"], Q_MC, axis=0)
        qi = np.percentile(100 * s_["tbp"] / s_["tbp"][:, [idx_c(s_, 2000)]], Q_MC, axis=0)
        for j, c in enumerate(s_["cohortes"]):
            ab.append(dict(cohorte=c, escenario_nat=e if c > 2024 else "n/a", **{"nivel_P%d" % q: qs[i, j] for i, q in enumerate(Q_MC)},
                           **{"indice2000_P%d" % q: qi[i, j] for i, q in enumerate(Q_MC)}))
    abanico = pd.DataFrame(ab)
    abanico = abanico[~((abanico.cohorte <= 2024) & (abanico.escenario_nat == "n/a") & abanico.duplicated(["cohorte"], keep="first"))]
    # ---- ÍNDICES de primer orden: nivel vs tendencia
    cos = list(sc["cohortes"])
    e_ = lambda c: np.eye(len(cos))[cos.index(c)]
    var_rows = [indices_primer_orden(sc, e_(2024), "nivel 2024"),
                indices_primer_orden(mez, e_(2030), "nivel 2030 (mezcla de natalidad)"),
                indices_primer_orden(mez, e_(2035), "nivel 2035 (mezcla de natalidad)"),
                indices_primer_orden(sc, e_(2024) - e_(2000), "razón 2024/2000"),
                indices_primer_orden(sc, pesos_pendiente(cos), "pendiente 2000-2024", en_logs_y=False)]
    varianza = pd.concat(var_rows, ignore_index=True)
    # ---- SENSIBILIDAD a supuestos de correlación y SE de Ā (sobre la razón y la pendiente)
    sens = []
    for nom, cambio in [("base (corr N=0, J=0,5, Ā=1; sin SE muestral)", {}),
                        ("J independiente entre cohortes (corr 0)", {"corr": dict(par["corr"], J=0.0)}),
                        ("J perfectamente correlacionado (corr 1)", {"corr": dict(par["corr"], J=1.0)}),
                        ("SE de Ā provisorio 2,6 % + corr Ā=1", {"se_rel_abar": SE_REL_PROVISORIO}),
                        ("SE de Ā provisorio 2,6 % + corr Ā=0 (peor caso)", {"se_rel_abar": SE_REL_PROVISORIO, "corr": dict(par["corr"], Abar=0.0)}),
                        ("σ_N y σ_J duplicados", {"sig_N": 2 * par["sig_N"], "sig_J": 2 * par["sig_J"]})]:
        p2 = dict(par, **cambio)
        s2 = simular(p2, base, n, seed, CAPAS_MC, nat=NAT_ESC_MC[0])
        r2 = razon_pareada(s2)
        pe2, _, _ = pendiente(s2)
        sens.append(dict(supuesto=nom, razon_P5=np.percentile(r2, 5), razon_P50=np.median(r2), razon_P95=np.percentile(r2, 95),
                         P_razon_menor_1=float(np.mean(r2 < 1)), pend_P5=np.percentile(pe2, 5), pend_P95=np.percentile(pe2, 95)))
    sens = pd.DataFrame(sens)
    # ---- descomposiciones
    d = ins["d"]
    dlog = descomposicion_log_exacta(ins["modelo"], d) if d is not None else None
    dvar = descomposicion_varianza_cov(ins["modelo"])
    dvar_orig = descomposicion_varianza_cov(ins["modelo"], ddof_consistente=False)
    resumen = pd.DataFrame(filas)
    res = dict(par=par, base=base, sims=sims, mezcla=mez, resumen=resumen, abanico=abanico, varianza=varianza, sens=sens,
               dlog=dlog, dvar=dvar, dvar_orig=dvar_orig, replica=rep, razon=r_cj, razon_no_pareada=r_unp, pendientes=sl,
               cancelacion_tau_rho=cancel, p_pareada=p_pareada, n=n, seed=seed)
    if verbose:
        imprimir(res)
    return res


def imprimir(res):
    R = res["resumen"]

    def g(b, c, e, capa, m):
        x = R[(R.bloque == b) & (R.cohorte.astype(str) == str(c)) & (R.escenario_nat == e) & (R.capa == capa) & (R.metrica == m)].valor
        return float(x.iloc[0]) if len(x) else np.nan
    print("== Justificación de las entradas ==")
    for k, v in res["par"]["justificacion"].items():
        print("  %-14s %s" % (k, v))
    print("\n== NIVEL (años de prestación por jubilado), bandas P5-P95 por capa ==")
    for c, e in [(2000, "n/a"), (2024, "n/a")] + [(c, e) for c in (2030, 2035) for e in NAT_ESC_MC]:
        txt = "  cohorte %d %-19s base %.3f | " % (c, "" if e == "n/a" else e, g("nivel", c, e, "base", "punto"))
        for capa in ("muestral", "medicion", "escenario", "conjunto"):
            if np.isnan(g("nivel", c, e, capa, "P50")):
                continue
            txt += "%s [%.3f ; %.3f]  " % (capa[:4], g("nivel", c, e, capa, "P5"), g("nivel", c, e, capa, "P95"))
        print(txt)
    print("\n== RAZÓN pareada TBP(2024)/TBP(2000) ==")
    for capa in res["p_pareada"]:
        print("  %-9s P5 %.3f  P50 %.3f  P95 %.3f  | P(razón<1) = %.4f" % (capa, g("razon_2024_2000", "2024/2000", "n/a", capa, "P5"),
              g("razon_2024_2000", "2024/2000", "n/a", capa, "P50"), g("razon_2024_2000", "2024/2000", "n/a", capa, "P95"), res["p_pareada"][capa]))
    print("  cancelación τ,ρ en la razón: máx |Δ ln razón| entre corrida con y sin variar τ,ρ = %.2e" % res["cancelacion_tau_rho"])
    print("  [contraejemplo NO pareado] P(2024 >= 2000) = %.4f" % g("razon_2024_2000", "2024/2000", "n/a", "conjunto_NO_pareado(incorrecto)", "P(2024>=2000)"))
    rp = res["replica"]
    print("  [Sección 16 original] P5-P95 2024 = [%.3f ; %.3f]; fracción de sorteos >= 0,312 fijo = %.4f" % (rp["P5"], rp["P95"], rp["p_supera"]))
    print("\n== PENDIENTE 2000-2024 (% anual en logs) ==")
    for capa, v in res["pendientes"].items():
        print("  %-9s P5 %.2f  P50 %.2f  P95 %.2f" % (capa, *np.percentile(v, [5, 50, 95])))
    print("\n== Varianza de primer orden ==")
    print(res["varianza"].round(3).to_string(index=False))
    print("\n== Descomposición logarítmica exacta ==")
    print(res["dlog"].round(4).to_string(index=False))
    print("\n== Varianza por covarianzas (ddof consistente) / réplica original ==")
    print(res["dvar"].round(1).to_string(index=False)); print(res["dvar_orig"].round(1).to_string(index=False))


def exportar(res, out):
    """Escribe montecarlo_resumen.csv, montecarlo_abanico.csv y montecarlo_varianza_primer_orden.csv en `out`."""
    os.makedirs(out, exist_ok=True)
    fs = []
    for nom, df in (("montecarlo_resumen.csv", res["resumen"]), ("montecarlo_abanico.csv", res["abanico"]),
                    ("montecarlo_varianza_primer_orden.csv", res["varianza"]), ("montecarlo_sensibilidad_supuestos.csv", res["sens"]),
                    ("montecarlo_descomposicion_log_exacta.csv", res["dlog"])):
        f = os.path.join(out, nom)
        df.round(6).to_csv(f, index=False)
        fs.append(f)
    return fs


# ============================================================================================= 6) GRÁFICOS
def graficar(res, out, show=False):
    import matplotlib
    import matplotlib.pyplot as plt
    os.makedirs(out, exist_ok=True)
    files = []
    ab, base = res["abanico"], res["base"]
    colores = {"persistencia": "#0072b2", "recuperacion_lenta": "#009e73", "caida_adicional": "#cc3311"}
    # 1) abanicos: nivel (arriba) e índice 2000=100 (abajo)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), dpi=120)
    for a, pref, tit in ((ax[0], "nivel", "NIVEL (años): todas las capas juntas\n(incluye escenarios de τ, ρ y Ā)"),
                         (ax[1], "indice2000", "TENDENCIA: índice 2000 = 100 (sorteos pareados)\nτ y ρ se cancelan")):
        h = ab[ab.cohorte <= 2024].drop_duplicates("cohorte")
        for lo, hi, al in ((5, 95, .18), (25, 75, .32)):
            a.fill_between(h.cohorte, h["%s_P%d" % (pref, lo)], h["%s_P%d" % (pref, hi)], color="#444444", alpha=al, lw=0)
        a.plot(h.cohorte, h["%s_P50" % pref], color="#222222", lw=2, label="mediana de los sorteos (cohortes observadas)")
        bb = base[NAT_ESC_MC[0]].loc[2000:2024]
        a.plot(bb.index, bb.values if pref == "nivel" else 100 * bb.values / bb.loc[2000], color="#222222", lw=1.2, ls="--", label="caso base (punto)")
        for e, c_ in colores.items():
            f_ = ab[(ab.escenario_nat == e) & (ab.cohorte >= 2024)]
            f_ = pd.concat([h[h.cohorte == 2024], f_]).drop_duplicates("cohorte")
            for lo, hi, al in ((5, 95, .15), (25, 75, .28)):
                a.fill_between(f_.cohorte, f_["%s_P%d" % (pref, lo)], f_["%s_P%d" % (pref, hi)], color=c_, alpha=al, lw=0)
            a.plot(f_.cohorte, f_["%s_P50" % pref], color=c_, lw=1.8, label="natalidad: " + e.replace("_", " "))
        a.axvline(2024.5, color="gray", ls=":", lw=1)
        a.set_title(tit, fontsize=10, fontweight="bold"); a.set_xlabel("cohorte (año de nacimiento)"); a.grid(alpha=.25)
    ax[0].set_ylabel("TBP_C (años de prestación por jubilado)"); ax[1].set_ylabel("índice (2000 = 100)")
    ax[1].legend(fontsize=8, loc="lower left")
    fig.suptitle("Abanico por cohorte (bandas 50 % y 90 %). Condicional a los supuestos; no es un intervalo de confianza clásico", fontsize=10)
    plt.tight_layout(); f1 = os.path.join(out, "seccion_18_abanico_cohortes.png"); plt.savefig(f1); files.append(f1)
    plt.show() if show else plt.close()
    # 2) razón pareada vs contraejemplo
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), dpi=120)
    r, ru = res["razon"], res["razon_no_pareada"]
    bins = np.linspace(0.3, 1.5, 70)
    ax[0].hist(r, bins=bins, color="#0072b2", alpha=.75, density=True, label="PAREADA (correcta)")
    ax[0].hist(ru, bins=bins, color="#e69f00", alpha=.5, density=True, label="no pareada (incorrecta)")
    ax[0].axvline(1, color="k", lw=1.5); ax[0].set_xlabel("TBP(2024) / TBP(2000)"); ax[0].set_ylabel("densidad")
    ax[0].set_title("Razón entre cohortes: sorteos con razón >= 1: %d de %d (pareada) | %.1f %% (sin parear)" % (np.sum(r >= 1), len(r), 100 * np.mean(ru >= 1)), fontsize=9, fontweight="bold")
    ax[0].legend(fontsize=8.5)
    sl = res["pendientes"]["conjunto"]
    ax[1].hist(sl, bins=50, color="#009e73", alpha=.8, density=True)
    ax[1].axvline(0, color="k", lw=1.2)
    ax[1].set_xlabel("pendiente 2000-2024 (% anual en logs)"); ax[1].set_ylabel("densidad")
    ax[1].set_title("Tendencia: P5 %.2f | P50 %.2f | P95 %.2f" % tuple(np.percentile(sl, [5, 50, 95])), fontsize=9.5, fontweight="bold")
    plt.tight_layout(); f2 = os.path.join(out, "seccion_18_razon_pareada.png"); plt.savefig(f2); files.append(f2)
    plt.show() if show else plt.close()
    # 3) varianza de primer orden: nivel vs tendencia
    v = res["varianza"]
    v = v[v.grupo != "(suma de primer orden)"]
    sel = ["nivel 2024", "nivel 2035 (mezcla de natalidad)", "razón 2024/2000", "pendiente 2000-2024"]
    grupos = ["tau", "rho", "Abar_regla", "Abar_muestral", "N", "J", "natalidad"]
    et = {"tau": "τ (escenario)", "rho": "ρ (escenario)", "Abar_regla": "Ā regla (escenario)", "Abar_muestral": "Ā muestral (sin bootstrap aún)",
          "N": "N (medición)", "J": "J* (medición)", "natalidad": "natalidad (escenario)"}
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=120)
    wd = 0.2
    cols = ["#0072b2", "#56b4e9", "#e69f00", "#009e73"]
    for i, rname in enumerate(sel):
        vals = [float(v[(v.resultado == rname) & (v.grupo == g)].frac_log.sum()) * 100 for g in grupos]
        ax.bar(np.arange(len(grupos)) + (i - 1.5) * wd, vals, wd, color=cols[i], label=rname)
    ax.set_xticks(np.arange(len(grupos))); ax.set_xticklabels([et[g] for g in grupos], rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("% de la varianza (primer orden, en logs)"); ax.grid(axis="y", alpha=.25); ax.legend(fontsize=9)
    ax.set_title("¿Qué parámetro domina? El NIVEL lo mandan las definiciones; la TENDENCIA, la demografía medida", fontsize=10, fontweight="bold")
    plt.tight_layout(); f3 = os.path.join(out, "seccion_18_varianza_por_parametro.png"); plt.savefig(f3); files.append(f3)
    plt.show() if show else plt.close()
    # 4) bandas del nivel 2024 por capa + réplica Sección 16
    R = res["resumen"]
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=120)
    filas = []
    for capa, lab in (("medicion", "MEDICIÓN (N, J*)"), ("escenario", "ESCENARIO (Ā regla, τ, ρ)"), ("conjunto", "CONJUNTO (condicional)")):
        x = R[(R.bloque == "nivel") & (R.cohorte.astype(str) == "2024") & (R.capa == capa)].set_index("metrica").valor
        if len(x):
            filas.append((lab, x["P5"], x["P50"], x["P95"], x["minimo"], x["maximo"]))
    rp = res["replica"]
    filas.append(("Sección 16 original (mezclado)", rp["P5"], rp["P50"], rp["P95"], np.nan, np.nan))
    for i, (lab, p5, p50, p95, mn, mx) in enumerate(filas[::-1]):
        ax.plot([p5, p95], [i, i], color="#0072b2", lw=6, solid_capstyle="butt", alpha=.7)
        ax.plot([p50], [i], "o", color="k")
        if np.isfinite(mn):
            ax.plot([mn, mx], [i, i], color="#0072b2", lw=1, ls=":")
    ax.set_yticks(range(len(filas))); ax.set_yticklabels([f[0] for f in filas[::-1]], fontsize=9)
    ax.axvline(float(res["base"].loc[2024].iloc[0]), color="#cc3311", ls="--", lw=1.3, label="base 2024")
    ax.set_xlabel("TBP_C cohorte 2024 (años)"); ax.legend(fontsize=8.5); ax.grid(axis="x", alpha=.25)
    ax.set_title("Banda P5-P95 del nivel 2024 por capa de incertidumbre (punto = mediana, línea fina = mín-máx)", fontsize=10, fontweight="bold")
    plt.tight_layout(); f4 = os.path.join(out, "seccion_18_bandas_por_capa.png"); plt.savefig(f4); files.append(f4)
    plt.show() if show else plt.close()
    return files


# ============================================================================================= 7) AUTOTEST (DATOS SINTÉTICOS)
def _banner_mc(txt="DATOS SINTÉTICOS — no son Argentina"):
    print("*" * 78); print("***  " + txt); print("*" * 78)


def insumos_sinteticos():
    """Mini-mundo inventado y ROTULADO: 2000..2035, natalidad cae hasta 2024 y se bifurca en 3 escenarios; Ā crece 10 % entre 2000 y 2024."""
    co = np.arange(1998, 2036)
    N = np.where(co <= 2024, 700 - 12 * (co - 1998), np.nan)
    N = np.where(co > 2024, 400, N).astype(float)
    S = 0.88 + 0.001 * (co - 2000)
    J = 12e3 + 90 * (co - 2000)
    A = 13 + 0.07 * (co - 2000)
    f = lambda N_, a, s_, j: N_ * s_ * a * 0.2177 / (j * 0.403)
    tb = f(N, A, S, J)
    ma = pd.DataFrame(dict(cohorte=co, TBP_C_p4=tb, N_4=N, S_tot65=S, J_star_4=J, A_eph=A))
    for e, k in zip(NAT_ESC_MC, (1.0, 1.3, 0.9)):
        ma["TBP_C_p4_" + e] = np.where(co > 2024, tb * k, tb)
    ab = pd.DataFrame(dict(cohorte=co, A_bar_solo_asalariados=A, A_bar_pp07i=A * 1.2, A_bar_indep50=A * 1.6))
    d = pd.DataFrame(dict(cohorte=co, N_t=N, S65=S, J=J))
    return dict(modelo=ma.set_index("cohorte"), abar=ab.set_index("cohorte"), rho=None, series=None, renaper=None, jrw=None,
                nat=None, d=d, abar_ic=None)


def autotest_montecarlo(verbose=True):
    _banner_mc()
    ins = insumos_sinteticos()
    par = calibrar_incertidumbre(ins)
    base = base_por_escenario(ins, COHORTES_MC)
    # (1) reproducibilidad
    a = simular(par, base, 3000, 7, CAPAS_MC, "persistencia"); b = simular(par, base, 3000, 7, CAPAS_MC, "persistencia")
    assert np.array_equal(a["tbp"], b["tbp"]), "misma semilla debe dar lo mismo"
    c = simular(par, base, 3000, 8, CAPAS_MC, "persistencia")
    assert not np.array_equal(a["tbp"], c["tbp"])
    # (2) con todas las capas apagadas se recupera el valor base exacto
    z = simular(par, base, 50, 1, (), "persistencia")
    assert np.allclose(z["tbp"], np.repeat(base["persistencia"].values[None, :], 50, 0))
    # (3) τ y ρ se cancelan EXACTAMENTE en la razón (capa escenario con regla de Ā fija en asalariados)
    par_fix = dict(par, A={k: par["A"]["solo_asalariados"] for k in REGLAS_ABAR})
    s_ = simular(par_fix, base, 4000, 3, ("escenario",), "persistencia")
    r = razon_pareada(s_)
    assert np.ptp(r) < 1e-12, "la razón no debe depender de τ ni ρ"
    nivel = s_["tbp"][:, idx_c(s_, 2024)]
    assert nivel.max() / nivel.min() > 1.5, "pero el NIVEL sí cambia con τ y ρ"
    # (4) pareada es más angosta que no pareada
    sc = simular(par, base, 6000, 4, CAPAS_MC, "persistencia")
    assert np.std(np.log(razon_pareada(sc))) < 0.5 * np.std(np.log(razon_no_pareada(sc)))
    # (5) un solo factor lognormal con σ conocido: P5/P95 = exp(±1,645σ)
    p1 = dict(par, sig_J=0.0, corr=dict(N=0.0, J=0.5, Abar=1.0), sig_N=0.10)
    s1 = simular(p1, base, 40000, 11, ("medicion",), "persistencia")
    q = np.percentile(np.log(s1["tbp"][:, idx_c(s1, 2000)] / base.loc[2000, "persistencia"]), [5, 95])
    assert abs(q[1] - 1.645 * 0.10) < 0.01 and abs(q[0] + 1.645 * 0.10) < 0.01
    # (6) índices de primer orden: aditivo en logs suma 1; estimador por estratos recupera caso analítico
    v = indices_primer_orden(sc, np.eye(len(sc["cohortes"]))[idx_c(sc, 2024)], "nivel")
    assert abs(v[v.grupo != "(suma de primer orden)"].frac_log.sum() - 1) < 0.08     # in-sample: categorías con pocos niveles dejan covarianzas de azar
    rng = np.random.default_rng(0)
    x1, x2 = rng.standard_normal(100000), rng.standard_normal(100000)
    Y = x1 + 0.5 * x2
    assert abs(_indice_estratos(Y, x1) - 0.8) < 0.015 and abs(_indice_estratos(Y, x2) - 0.2) < 0.015
    # (7) descomposiciones: suman 100 %
    dl = descomposicion_log_exacta(ins["modelo"], ins["d"], 2000, 2024)
    for esp, g in dl.groupby("especificacion"):
        assert abs(g[g.componente != "TOTAL Δln TBP_C"].pct_de_la_caida.sum() - 100) < 1e-8
    dv = descomposicion_varianza_cov(ins["modelo"], 2000, 2024)
    assert abs(dv[dv.componente != "SUMA"].participacion_pct.sum() - 100) < 1e-8
    # (8) lector de bootstrap con un archivo SINTÉTICO de juguete
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pd.DataFrame(dict(cohorte=[2024], regla=["solo_asalariados"], abar=[14.0], se=[0.35])).to_csv(os.path.join(tmp, "abar_bootstrap_ic.csv"), index=False)
        ic = leer_abar_ic([tmp])
        assert ic is not None and abs(ic["se_rel"] - 0.025) < 1e-12
    # (9) corrida completa sobre el mini-mundo
    res = correr(ins, n=3000, seed=5, verbose=False)
    assert 0 <= res["p_pareada"]["conjunto"] <= 1 and len(res["resumen"]) > 50
    if verbose:
        print("autotest OK (9 chequeos sobre datos sintéticos)")
    return True


if __name__ == "__main__":
    autotest_montecarlo()
