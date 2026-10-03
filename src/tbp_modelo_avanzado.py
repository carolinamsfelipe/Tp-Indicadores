# -*- coding: utf-8 -*-
"""
tbp_modelo_avanzado.py — TBP_C con sexo y edad de retiro, ρ con moratorias (escenarios) y ajuste por migración.

Proyecto TBP — Índice de Cuna Vacía (Taller de Indicadores).  Versión principal propuesta (años de aporte por año de jubilado):

        TBP_C(t) = N_t · (1−μ) · Ā · τ / (J · ρ)            [en el código: N_t · S65 · Ā · τ / (J · ρ)]
        TBP_A    = TBP_C / E_r          TBP_B = Ā·τ / (E_r·ρ)          (TBP_C NO contiene E_r)

QUÉ AGREGA ESTE MÓDULO (todo REUSA tbp_eph, tbp_anses y tbp_mortalidad; no los reescribe)
 1) SEXO Y EDAD DE RETIRO (principal: varones 65, mujeres 60 = edad legal en el SIPA).  Numerador aditivo por sexo:
        Σ_s  N_s · S_s(r_s) · Ā_s · τ ,     N_s = N_t · share_s ,  share_varones = SRB/(100+SRB)   (SRB ONU del año t)
    S_s(r_s) = supervivencia cohortal de ese sexo hasta su edad de retiro (tablas ONU por sexo); Ā_s = Σ_{a=18}^{r_s−1} S(a)·d_s(a)
    con la densidad d_s de la EPH del sexo s (varones 18-64; mujeres 18-59).  Denominador: J*·ρ con
        J* = varones 65+ + mujeres 60+ (ONU, año t+65): las mujeres de 60 a 64 ya cobran, por eso cuentan como pasivas.
    SENSIBILIDAD ("retiro a los 65 para todos", J = población 65+ total, modelo base): sobrecuenta aportes de las mujeres de 60 a 64
    (que ya no aportan) y omite del denominador a las pasivas de 60 a 64.
    AGREGACIÓN (definida, no "ponderada y luego sumada"): lo que se SUMA son las contribuciones al numerador
    (TBP_C_total = TBP_C_varones + TBP_C_mujeres, ambos sobre el MISMO J*·ρ).  Lo que se PROMEDIA (ponderando por los
    sobrevivientes al retiro N_s·S_s) son las intensidades por persona: Ā, E_r y TBP_B.  TBP_A total = Σ_s TBP_C_s / E_{r,s}
    y cumple TBP_A = D*·TBP_B con D* = Σ N_s S_s / J*.
 2) ρ CON MORATORIAS (ESCENARIO).  Como ρ = haber medio / salario imponible medio y el haber medio de todos los beneficiarios es
    el promedio ponderado por beneficiarios, ρ_total = s·ρ_mor + (1−s)·ρ_sin_mor  (s = participación de beneficiarios con moratoria).
    Con ρ_total, ρ_sin_mor y s de ANSES (digitalizados, aprox.) se DESPEJA ρ_mor implícito 2009-2023 y se verifica que sea plausible.
    Para cohortes que se retiran después de 2023, s es un SUPUESTO (no una predicción): 'persiste' (≈62,9 %), 'mitad' (≈31 %),
    'sin_moratorias' (0 %).  Mayor ρ => menor TBP_C.
 3) MIGRACIÓN.  En vez de "N + ΣM" (no calculable por cohorte) se usa la corrección empírica implícita en la proyección ONU:
        m = población de la edad de retiro en el año calendario del retiro / (N_s · S_s)      (N_efectivo · S = población ONU)
    Mezcla migración neta, diferencias entre fuentes (DEIS vs ONU) y el desfase de nacimientos: NO es migración pura.
    Opción `ajuste_migracion` True/False.

SUPUESTOS Y LÍMITES (rotulados en cada función): ρ y τ iguales para varones y mujeres (no hay series por sexo); ρ y τ del año t+65
    para ambos sexos; J* es un stock en t+65 (las mujeres se retiran 5 años antes); τ constante (supuesto); todos los niveles dependen de Ā;
    la EPH es urbana, solo asalariados (cota inferior).  Los resultados son condicionales a supuestos, NO son una predicción.

Uso mínimo:
    import tbp_modelo_avanzado as ma
    ma.autotest_modelo_avanzado()            # datos SINTÉTICOS rotulados
"""
import os
import sys
import importlib
import urllib.request

import numpy as np
import pandas as pd

RAW_BASE_MA = "https://raw.githubusercontent.com/carolinamsfelipe/Tp-Indicadores/main/datos/procesados"
RUTAS_MA = ["../datos/procesados", "datos/procesados"]
RUTAS_SRC_MA = ["../src", "src", "github_staging/src"]
EDAD_V, EDAD_M = 65, 60                     # edades de retiro PRINCIPALES: varones 65, mujeres 60 (edad legal en el SIPA)
EDAD_ALT = 65                               # SENSIBILIDAD: "retiro a los 65 para todos" (modelo base) con J = población 65+ total
TAU_DEF, RHO_DEF, A_OBS_DEF, A_LEGAL_DEF = 0.2177, 0.403, 14.2, 30.0
ESCENARIOS_MOR = {"persiste": 1.0, "mitad": 0.5, "sin_moratorias": 0.0}   # multiplicador de la participación observada en 2023
ETQ_MOR = {"persiste": "persiste (≈62,9 %)", "mitad": "mitad (≈31 %)", "sin_moratorias": "sin moratorias (0 %)"}
ESC_NAT = ("persistencia", "recuperacion_lenta", "caida_adicional")
NOTA_ABAR = ("Ā por sexo: EPH (solo asalariados con descuento jubilatorio = cota inferior), pseudo-panel cohorte×edad, "
             "truncado a la edad de retiro del sexo (varones 18-64, mujeres 18-59).")


# ================================================================== 0) DEPENDENCIAS (reuso de los módulos del proyecto)
_NOMBRES_DEP = {"tbp_eph": ["pipeline", "supervivencia_gompertz", "EDADES", "find_eph_files", "read_all"],
                "tbp_anses": ["asignar_rho_tau_por_cohorte", "serie_rho_digitalizada", "serie_beneficiarios_digitalizada", "serie_tau"],
                "tbp_mortalidad": ["cargar_tablas", "supervivencia_cohortal", "er_cohortal"]}


class _Dep:
    pass


def dependencias():
    """Devuelve un objeto con las funciones reusadas de tbp_eph, tbp_anses y tbp_mortalidad.
    Orden: (1) nombres ya definidos en el espacio global (el notebook embebe los módulos de las secciones 12-14);
    (2) import desde src/ (rutas candidatas). Si falta alguno, error explícito."""
    g = globals()
    dep = _Dep()
    for mod, nombres in _NOMBRES_DEP.items():
        m = None
        if any(n not in g for n in nombres):
            for r in RUTAS_SRC_MA:
                if os.path.isdir(r) and os.path.abspath(r) not in sys.path:
                    sys.path.append(os.path.abspath(r))
            try:
                m = importlib.import_module(mod)
            except ImportError:
                m = None
        for n in nombres:
            if n in g:
                setattr(dep, n, g[n])
            elif m is not None and hasattr(m, n):
                setattr(dep, n, getattr(m, n))
            else:
                raise ImportError(f"falta `{n}` de {mod}: correr antes las secciones 12-14 del notebook o tener src/{mod}.py disponible")
    return dep


# ================================================================== 1) CARGA DE DATOS
def leer_csv_ma(nombre, rutas=None, destino="."):
    """Lee un CSV de datos/procesados: rutas candidatas ('../datos/procesados', 'datos/procesados' + las dadas);
    si no está, lo baja de GitHub (URL raw)."""
    for c in list(rutas or []) + RUTAS_MA:
        p = os.path.join(c, nombre)
        if os.path.exists(p):
            return pd.read_csv(p, low_memory=False)
    os.makedirs(destino, exist_ok=True)
    p = os.path.join(destino, nombre)
    urllib.request.urlretrieve(f"{RAW_BASE_MA}/{nombre}", p)
    return pd.read_csv(p, low_memory=False)


def cargar_poblacion_sexo(df=None, rutas=None):
    """Población ONU por edad simple y SEXO (personas). Devuelve (PM, PF): DataFrames año × edad (0..100; 100 = grupo abierto 100+)."""
    if df is None:
        df = leer_csv_ma("un_wpp2024_argentina_poblacion_edad_simple.csv", rutas)
    if "Variant" in df.columns:
        df = df[df["Variant"] == "Medium"]
    out = []
    for col in ("PopMale", "PopFemale"):
        P = df.pivot_table(index="Time", columns="AgeGrpStart", values=col) * 1000.0
        P.columns = P.columns.astype(int)
        out.append(P)
    return out[0], out[1]


def cargar_srb(df=None, rutas=None):
    """SRB (varones por 100 mujeres al nacer, ONU) por año. Verifica que exista y sea razonable."""
    if df is None:
        df = leer_csv_ma("un_wpp2024_argentina_indicadores.csv", rutas)
    if "SRB" not in df.columns:
        raise ValueError("el CSV de indicadores ONU no tiene la columna SRB (razón de masculinidad al nacer)")
    if "Variant" in df.columns:
        df = df[df["Variant"] == "Medium"]
    srb = df.set_index("Time")["SRB"].astype(float)
    srb = srb.loc[1950:2100]                      # 2101 no trae SRB en la tabla ONU
    assert srb.notna().all() and srb.between(100, 112).all(), "SRB fuera del rango esperado (100-112 varones por 100 mujeres)"
    return srb


def cargar_natalidad_escenarios(df=None, rutas=None):
    """Escenarios de natalidad de la sección 9: DataFrame año × escenario (nacimientos, personas)."""
    if df is None:
        df = leer_csv_ma("natalidad_escenarios_2025_2035.csv", rutas)
    return df.pivot(index="anio", columns="escenario", values="nacimientos")


def share_varones(srb):
    """Participación de varones al nacer: SRB/(100+SRB).  SRB = varones por 100 mujeres (no se usa 51/49 fijo)."""
    return srb / (100.0 + srb)


# ================================================================== 2) SUPERVIVENCIA, E_r Y Ā POR SEXO
def supervivencia_retiro(cohortes, tablas, edad_v=EDAD_V, edad_m=EDAD_M):
    """S_s(r_s) por sexo: supervivencia COHORTAL (tablas ONU por sexo, trayectoria calendario) hasta la edad de retiro.
    Devuelve DataFrame: S_v (varones a edad_v), S_m (mujeres a edad_m), S_m65 (mujeres a 65),
    S_tot65 (Total a 65, = columna S65 de `d`)."""
    D = dependencias()
    co = [int(c) for c in cohortes]
    sv = D.supervivencia_cohortal(co, "Male", tablas)
    sf = D.supervivencia_cohortal(co, "Female", tablas)
    st = D.supervivencia_cohortal(co, "Total", tablas)
    return pd.DataFrame({"S_v": sv[edad_v], "S_m": sf[edad_m], "S_m65": sf[65], "S_tot65": st[65]}, index=pd.Index(co, name="cohorte"))


def er_retiro(cohortes, tablas, edad_v=EDAD_V, edad_m=EDAD_M):
    """E_r cohortal a la edad de retiro de cada sexo (varones a 65, mujeres a `edad_m`, 60 por defecto). Usa tbp_mortalidad.er_cohortal(edad=...)."""
    D = dependencias()
    co = [int(c) for c in cohortes]
    return pd.DataFrame({"E_v": D.er_cohortal(co, edad_v, "Male", tablas), "E_m": D.er_cohortal(co, edad_m, "Female", tablas)})


def abar_hasta_edad(dens, s65, edad_retiro):
    """Ā truncado: Σ_{a=18}^{edad_retiro−1} S_c(a)·d_c(a), con S de Gompertz calibrada a S(65)=s65 (igual que tbp_eph.abar_por_cohorte,
    que suma hasta 64).  Con edad_retiro=65 reproduce abar_por_cohorte; con 60 suma las edades 18-59."""
    D = dependencias()
    S = D.supervivencia_gompertz(s65.reindex(dens.index).values)
    cols = np.asarray(D.EDADES) < int(edad_retiro)
    return pd.Series((S * dens.values)[:, cols].sum(axis=1), index=dens.index)


def abar_por_sexo(df_eph, tablas, cohortes, edad_v=EDAD_V, edad_m=EDAD_M, ind_rule="solo_asalariados"):
    """Ā por sexo con la EPH REAL: corre tbp_eph.pipeline(..., sexo=1|2) (1 = varón, 2 = mujer) y trunca la suma de edades a r_s−1.
    Columnas: A_varones_{edad_v}, A_mujeres_{edad_m} (60 => 18-59) y A_mujeres_65 (sensibilidad) + n_edades_obs.
    Si no hay microdatos NO se inventa nada: quien llama debe omitir la parte por sexo."""
    D = dependencias()
    co = [int(c) for c in cohortes]
    out = {}
    for nombre, cod, sx, r_s in (("varones", 1, "Male", edad_v), ("mujeres", 2, "Female", edad_m)):
        s65 = D.supervivencia_cohortal(co, sx, tablas)[65]
        res = D.pipeline(df_eph, s65, ind_rule=ind_rule, sexo=cod, cohortes=co)
        for r in sorted({65, r_s}):
            out[f"A_{nombre}_{r}"] = abar_hasta_edad(res["dens"], s65, r)
        out[f"n_edades_obs_{nombre}"] = res["tabla"]["n_edades_obs"]
        # control interno: con r=65 la suma debe reproducir A_bar del pipeline
        assert np.allclose(out[f"A_{nombre}_65"].values, res["tabla"]["A_bar"].values, atol=1e-9), "Ā truncado a 65 != A_bar del pipeline"
    res = pd.DataFrame(out)
    res.index.name = "cohorte"
    return res


# ================================================================== 3) J* (PASIVOS POTENCIALES) Y REPONDERACIÓN
def pesos_cohorte_ma(s, nat, escenario):
    """w(c) = N_propio(c)/N_ONU(c) (misma regla que la sección 10): DEIS para 1950-2024 (w=1 donde DEIS tiene hueco), escenario de la sección 9
    para 2025-2035, w=1 en el resto.  Sirve para reponderar la población ONU por cohorte."""
    n_onu = s["un_births_miles"] * 1000.0
    n_deis = s["deis_nacimientos"]
    w = pd.Series(1.0, index=np.arange(1900, 2101))
    for c in range(1950, 2025):
        if not np.isnan(n_deis.get(c, np.nan)):
            w[c] = n_deis[c] / n_onu[c]
    for c in range(2025, 2036):
        w[c] = nat.loc[c, escenario] / n_onu[c]
    assert w.notna().all()
    return w


def j_pasivos(PM, PF, anios, edad_v=EDAD_V, edad_m=EDAD_M, w=None):
    """Pasivos potenciales en el año calendario y:  J* = varones edad_v+ + mujeres edad_m+  (ONU, edad simple, grupo 100+ incluido);
    J65 = población 65+ total (definición del modelo base).  `w` (Serie por cohorte, opcional) repondera como la sección 10:
    la población de edad a en el año y pertenece a la cohorte y−a (grupo abierto 100+ -> y−100).  Devuelve DataFrame por año."""
    filas = {}
    for y in anios:
        y = int(y)
        a_v = np.arange(edad_v, 101); a_m = np.arange(edad_m, 101); a_65 = np.arange(65, 101)
        wv = np.ones(len(a_v)) if w is None else w.reindex(y - a_v).values
        wm = np.ones(len(a_m)) if w is None else w.reindex(y - a_m).values
        w65 = np.ones(len(a_65)) if w is None else w.reindex(y - a_65).values
        jv = float((PM.loc[y, a_v].values * wv).sum())
        jm = float((PF.loc[y, a_m].values * wm).sum())
        j65 = float(((PM.loc[y, a_65].values + PF.loc[y, a_65].values) * w65).sum())
        filas[y] = dict(J_star=jv + jm, J_v=jv, J_m=jm, J65=j65)
    return pd.DataFrame.from_dict(filas, orient="index")


# ================================================================== 4) ρ CON MORATORIAS (ESCENARIO)
def rho_implicito(rho_total, rho_sin_mor, share_mor):
    """ρ_mor implícito:  ρ_total = s·ρ_mor + (1−s)·ρ_sin_mor  =>  ρ_mor = (ρ_total − (1−s)·ρ_sin_mor)/s.
    Es exacto si ambos ρ comparten el denominador (salario imponible medio) y la media del haber se pondera por beneficiarios;
    con datos digitalizados del gráfico es una APROXIMACIÓN."""
    s = np.asarray(share_mor, float)
    return (np.asarray(rho_total, float) - (1.0 - s) * np.asarray(rho_sin_mor, float)) / s


def tabla_rho_moratoria(serie_rho, ben):
    """Tabla anual 2009-2023: ρ_total, ρ_sin_mor, share_mor (ANSES, digitalizados) y ρ_mor implícito. Verifica 0<ρ_mor<1."""
    r = serie_rho.set_index("anio")[["rho", "rho_sin_moratoria"]]
    b = ben.set_index("anio")["share_moratoria"]
    t = r.join(b, how="inner")
    t["rho_mor_implicito"] = rho_implicito(t["rho"], t["rho_sin_moratoria"], t["share_moratoria"])
    assert t["rho_mor_implicito"].between(0, 1).all(), "ρ_mor implícito fuera de (0,1)"
    return t


def rho_por_escenario(anios, tabla_mor, escenario):
    """ρ_total por año calendario de retiro.  Años con dato (≤2023): ρ digitalizado (igual en todos los escenarios).
    Años > 2023: ρ = s_esc·ρ_mor(2023) + (1−s_esc)·ρ_sin_mor(2023), con s_esc = mult·s(2023) y mult ∈ {1 (persiste), 0,5 (mitad), 0 (sin moratorias)}.
    Los valores post-2023 son SUPUESTOS rotulados (no predicciones)."""
    if escenario not in ESCENARIOS_MOR:
        raise ValueError(f"escenario {escenario!r} no está en {list(ESCENARIOS_MOR)}")
    u = tabla_mor.index.max()
    s_u, rm_u, rsm_u = tabla_mor.loc[u, "share_moratoria"], tabla_mor.loc[u, "rho_mor_implicito"], tabla_mor.loc[u, "rho_sin_moratoria"]
    s_esc = ESCENARIOS_MOR[escenario] * s_u
    rho_post = s_esc * rm_u + (1.0 - s_esc) * rsm_u
    vals, tipo = [], []
    for y in anios:
        y = int(y)
        if y in tabla_mor.index:
            vals.append(float(tabla_mor.loc[y, "rho"])); tipo.append("dato (digitalizado)")
        elif y > u:
            vals.append(float(rho_post)); tipo.append(f"supuesto:{escenario}")
        else:
            vals.append(float(tabla_mor.loc[tabla_mor.index.min(), "rho"])); tipo.append("extrapolado:primer_valor")
    return pd.Series(vals, index=pd.Index([int(a) for a in anios], name="anio"), name=f"rho_{escenario}"), tipo


# ================================================================== 5) TBP_C POR SEXO, TBP_A, TBP_B
def tbp_c_sexos(N, sh_v, S_v, S_m, A_v, A_m, tau, rho, J, mig_v=1.0, mig_m=1.0):
    """TBP_C con numerador aditivo por sexo y denominador común J·ρ:
        TBP_C_s = N_t·share_s · S_s(r_s) · Ā_s · m_s · τ / (J·ρ)         TBP_C_total = TBP_C_varones + TBP_C_mujeres.
    Todas las entradas son Series por cohorte (o escalares).  `J` es J* (varones 65+ y mujeres 60+) o J65 (variante base).
    m_s = factor de migración (1 = sin ajuste).  Devuelve DataFrame con N_v, N_m, sobrevivientes al retiro y TBP_C."""
    N_v = N * sh_v
    N_m = N - N_v
    sob_v = N_v * S_v * mig_v
    sob_m = N_m * S_m * mig_m
    den = J * rho
    out = pd.DataFrame({"N_v": N_v, "N_m": N_m, "sob_v": sob_v, "sob_m": sob_m})
    out["TBP_C_varones"] = sob_v * A_v * tau / den
    out["TBP_C_mujeres"] = sob_m * A_m * tau / den
    out["TBP_C_total"] = out["TBP_C_varones"] + out["TBP_C_mujeres"]
    return out


def tbp_ab_sexos(parts, A_v, A_m, E_v, E_m, tau, rho, J):
    """TBP_A y TBP_B por sexo con E_r cohortal del sexo a su edad de retiro.
    TBP_A_s = TBP_C_s/E_s (aditivo: TBP_A_total = suma);  TBP_B_s = Ā_s·τ/(E_s·ρ) (por persona) y TBP_B_total = promedio ponderado por
    los sobrevivientes al retiro (N_s·S_s).  Identidad:  TBP_A_total = D*·TBP_B_total con D* = Σ sobrevivientes / J."""
    out = pd.DataFrame(index=parts.index)
    out["TBP_A_varones"] = parts["TBP_C_varones"] / E_v
    out["TBP_A_mujeres"] = parts["TBP_C_mujeres"] / E_m
    out["TBP_A_total"] = out["TBP_A_varones"] + out["TBP_A_mujeres"]
    out["TBP_B_varones"] = A_v * tau / (E_v * rho)
    out["TBP_B_mujeres"] = A_m * tau / (E_m * rho)
    sob = parts["sob_v"] + parts["sob_m"]
    out["TBP_B_total"] = (parts["sob_v"] * out["TBP_B_varones"] + parts["sob_m"] * out["TBP_B_mujeres"]) / sob
    out["D_star"] = sob / J
    out["E_r_implicito_total"] = parts["TBP_C_total"] / out["TBP_A_total"]
    return out


def descomponer_retiro_mujeres(N, sh_v, S_v, S_m65, S_m60, A_v, A_m65, A_m60, tau, rho, J65, J_star):
    """Efecto de que las mujeres se retiren a los 60 (vs 65), por pasos ACUMULADOS (el orden importa; es una descomposición, no una
    identidad): (a) ambos sexos a 65 [referencia = variante "retiro 65 para todos"]; (b) + S_m a los 60 (más sobrevivientes llegan);
    (c) + Ā_m hasta 59 (menos años de aporte); (d) + J* (más pasivas: mujeres 60-64) = modelo principal.  Devuelve TBP_C total en cada paso."""
    p = lambda S_m, A_m, J: tbp_c_sexos(N, sh_v, S_v, S_m, A_v, A_m, tau, rho, J)["TBP_C_total"]
    return pd.DataFrame({"a_ambos_65": p(S_m65, A_m65, J65), "b_mas_S_m60": p(S_m60, A_m65, J65),
                         "c_mas_Abar_m59": p(S_m60, A_m60, J65), "d_mas_J_star": p(S_m60, A_m60, J_star)})


# ================================================================== 6) MIGRACIÓN (corrección empírica implícita en la proyección ONU)
def factor_migracion(PM, PF, cohortes, N, sh_v, S_v, S_m, w_pob=None, edad_v=EDAD_V, edad_m=EDAD_M):
    """m_s = población ONU de edad r_s en el año t+r_s / (N_s·S_s)  (N_efectivo·S = población ONU).  Por sexo, con varones a edad_v y
    mujeres a edad_m.  `w_pob` (Serie por cohorte, opcional) repondera la población ONU con el escenario de natalidad (cohortes ≥2025),
    de modo que N_t (escenario) y la población usen la misma historia de nacimientos.  Mezcla migración neta, diferencias entre fuentes
    (DEIS vs ONU) y el desfase de nacimientos: NO es migración pura."""
    co = [int(c) for c in cohortes]
    pv = pd.Series([PM.loc[c + edad_v, edad_v] for c in co], index=co)
    pm = pd.Series([PF.loc[c + edad_m, edad_m] for c in co], index=co)
    if w_pob is not None:
        wv = w_pob.reindex(co).values
        pv, pm = pv * wv, pm * wv
    m_v = pv / (N * sh_v * S_v)
    m_m = pm / (N * (1 - sh_v) * S_m)
    return pd.DataFrame({"m_v": m_v, "m_m": m_m, "pob_v": pv, "pob_m": pm})


# ================================================================== 7) CONSTRUCCIÓN DEL MODELO COMPLETO (pasos acumulados 0-5)
def construir_modelo(d, s, tablas, PM, PF, srb, nat, abar_tot, tabla_mor, abar_sx=None, tau=TAU_DEF, rho_const=RHO_DEF,
                     A_obs=A_OBS_DEF, A_legal=A_LEGAL_DEF, escenario_nat="persistencia", escenario_mor="persiste",
                     col_abar_tot="A_bar_solo_asalariados", edad_retiro_mujeres=EDAD_M):
    """Pasos acumulados de TBP_C (cohortes de `d`):
      p0  base: Ā constante (14,2 y 30), ρ y τ constantes
      p1  + Ā(t) de la EPH (total, 18-64)
      p2  + ρ(t) ANSES (digitalizado; 'ultimo_valor' después de 2023; τ constante por supuesto)
      p3  + diferenciación por sexo y retiro (varones 65, mujeres 60): S_s(r_s), Ā_s hasta r_s−1, J* = varones 65+ y mujeres 60+
      (sensibilidad, aparte: *_m65 = "retiro a los 65 para todos" con J = J65, modelo base)
      p4  + escenario de natalidad (sección 9) y J* reponderado (sección 10) para cohortes ≥2025
      p5  + ajuste por migración (opcional, aparte)
    Si `abar_sx` es None (sin microdatos EPH por sexo) se calculan solo p0-p2 y nada se inventa para el resto.
    Devuelve dict con R (DataFrame por cohorte) y piezas auxiliares."""
    dd = d.set_index("cohorte")
    co = dd.index
    D = dependencias()
    R = pd.DataFrame(index=co)
    R["anio_65"] = co + 65
    N0 = dd["N_t"].astype(float)
    S65, J65 = dd["S65"], dd["J"]
    R["N_t"] = N0
    # ---- p0: base
    R["TBP_C_p0_A14_2"] = N0 * S65 * A_obs * tau / (J65 * rho_const)
    R["TBP_C_p0_A30"] = N0 * S65 * A_legal * tau / (J65 * rho_const)
    # ---- p1: Ā(t) EPH
    A_eph = abar_tot[col_abar_tot].reindex(co)
    assert A_eph.notna().all(), "Ā EPH no cubre todas las cohortes"
    R["A_eph"] = A_eph
    R["TBP_C_p1"] = N0 * S65 * A_eph * tau / (J65 * rho_const)
    # ---- p2: ρ(t) ANSES (+ τ constante), vía tbp_anses.asignar_rho_tau_por_cohorte (regla 'ultimo_valor')
    sr = tabla_mor.reset_index()[["anio", "rho", "rho_sin_moratoria"]]
    st = D.serie_tau(valor=tau, anios=sr["anio"].tolist())
    asig = D.asignar_rho_tau_por_cohorte(d, sr, st, edad_retiro=65, extrapolacion="ultimo_valor")
    R["rho_t"] = asig.set_index("cohorte")["rho_v"]
    R["tau_t"] = asig.set_index("cohorte")["tau_v"]
    R["TBP_C_p2"] = N0 * S65 * A_eph * R["tau_t"] / (J65 * R["rho_t"])
    # ρ por escenario de moratorias (persiste == p2, verificado)
    RHO_ESC = {}
    for esc in ESCENARIOS_MOR:
        rr, _ = rho_por_escenario(co + 65, tabla_mor, esc)
        RHO_ESC[esc] = pd.Series(rr.values, index=co)
    assert np.allclose(RHO_ESC["persiste"].values, R["rho_t"].values, atol=1e-9), "escenario 'persiste' debe coincidir con 'ultimo_valor'"
    rho_v = RHO_ESC[escenario_mor]
    R["rho_escenario"] = rho_v
    aux = dict(RHO_ESC=RHO_ESC, asig=asig, tabla_mor=tabla_mor)
    if abar_sx is None:
        return dict(R=R, **aux, con_sexo=False)

    # ---- sexo: share, N_s, S_s, E_s  (principal: varones 65, mujeres 60; sensibilidad: todos a 65 con J = J65)
    sh_v = share_varones(srb).reindex(co)
    assert sh_v.notna().all()
    R["share_varones"] = sh_v
    Sx = supervivencia_retiro(co, tablas, edad_v=EDAD_V, edad_m=edad_retiro_mujeres)
    Ex = er_retiro(co, tablas, edad_v=EDAD_V, edad_m=edad_retiro_mujeres)
    for c_ in Sx.columns:
        R[c_] = Sx[c_]
    for c_ in Ex.columns:
        R[c_] = Ex[c_]
    S_m65 = Sx["S_m65"]
    E_m65 = er_retiro(co, tablas, edad_v=EDAD_V, edad_m=EDAD_ALT)["E_m"]
    R["E_m65"] = E_m65
    for c_ in abar_sx.columns:
        R[c_] = abar_sx[c_].reindex(co)
    A_v = R["A_varones_65"]
    A_m = R[f"A_mujeres_{edad_retiro_mujeres}"]
    A_m65 = R["A_mujeres_65"]
    JJ = j_pasivos(PM, PF, co + 65, edad_m=edad_retiro_mujeres)
    JJ.index = co
    R["J65"] = JJ["J65"]; R["J_star"] = JJ["J_star"]
    assert np.allclose(R["J65"].values, J65.values, rtol=1e-9), "J65 (suma de PopMale+PopFemale 65+) debe reproducir la columna J de d"
    # ---- p3: sexo y retiro (varones 65, mujeres edad_m); J* = varones 65+ y mujeres edad_m+
    p3 = tbp_c_sexos(N0, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rho_v, JJ["J_star"])
    R["TBP_C_p3"] = p3["TBP_C_total"]
    R["TBP_C_p3_J65"] = tbp_c_sexos(N0, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rho_v, J65)["TBP_C_total"]       # misma numeración, J = 65+ total
    # ---- p4: escenario de natalidad y J* reponderado (solo cohortes ≥ 2025)
    w = pesos_cohorte_ma(s, nat, escenario_nat)
    nuevo = co >= 2025
    N4 = N0.copy()
    N4.loc[2025:2035] = nat.loc[2025:2035, escenario_nat].values

    def _j4(edad_m_, w_=w):
        j0 = j_pasivos(PM, PF, co + 65, edad_m=edad_m_); j0.index = co
        jr = j_pasivos(PM, PF, co + 65, edad_m=edad_m_, w=w_); jr.index = co
        j4 = j0["J_star"].copy(); j4[nuevo] = jr["J_star"][nuevo]
        return j4, jr
    J4, JJ_rw = _j4(edad_retiro_mujeres)
    J4_65, _ = _j4(EDAD_ALT)                                  # J = 65+ total reponderado (modelo base)
    R["N_4"] = N4; R["J_star_4"] = J4
    p4 = tbp_c_sexos(N4, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rho_v, J4)
    R["TBP_C_p4"] = p4["TBP_C_total"]
    R["J_consistente"] = ~(co + EDAD_V - edad_retiro_mujeres > 2035) | (co < 2025)     # J* de mujeres en t+65 incluye cohortes hasta t+(65-edad_m)
    # ---- p5: migración (sobre p4)
    w_pob = pd.Series(1.0, index=w.index); w_pob.loc[2025:2035] = w.loc[2025:2035]       # solo cohortes ≥2025 (escenario)
    mig = factor_migracion(PM, PF, co, N4, sh_v, Sx["S_v"], Sx["S_m"], w_pob=w_pob, edad_m=edad_retiro_mujeres)
    R["m_v"], R["m_m"] = mig["m_v"], mig["m_m"]
    p5 = tbp_c_sexos(N4, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rho_v, J4, mig["m_v"], mig["m_m"])
    R["TBP_C_p5"] = p5["TBP_C_total"]
    R["m_total"] = (mig["pob_v"] + mig["pob_m"]) / (p4["sob_v"] + p4["sob_m"])
    # ---- salidas por sexo (modelo p4) y TBP_A / TBP_B
    for c_ in ("TBP_C_varones", "TBP_C_mujeres", "TBP_C_total"):
        R[c_ + "_p4"] = p4[c_]
    ab = tbp_ab_sexos(p4, A_v, A_m, Ex["E_v"], Ex["E_m"], tau, rho_v, J4)
    for c_ in ab.columns:
        R[c_ + "_p4"] = ab[c_]
    # ---- ρ escenarios sobre p4
    for esc, rv in RHO_ESC.items():
        R[f"TBP_C_p4_rho_{esc}"] = tbp_c_sexos(N4, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rv, J4)["TBP_C_total"]
    # ---- escenarios de natalidad (p4 con cada uno)
    for e_ in ESC_NAT:
        w_e = pesos_cohorte_ma(s, nat, e_)
        Ne = N0.copy(); Ne.loc[2025:2035] = nat.loc[2025:2035, e_].values
        Je, _ = _j4(edad_retiro_mujeres, w_e)
        R[f"TBP_C_p4_{e_}"] = tbp_c_sexos(Ne, sh_v, Sx["S_v"], Sx["S_m"], A_v, A_m, tau, rho_v, Je)["TBP_C_total"]
    # ---- SENSIBILIDAD (variante alternativa): "retiro a los 65 para todos" con J = población 65+ total (modelo base)
    s3 = tbp_c_sexos(N0, sh_v, Sx["S_v"], S_m65, A_v, A_m65, tau, rho_v, J65)
    s4 = tbp_c_sexos(N4, sh_v, Sx["S_v"], S_m65, A_v, A_m65, tau, rho_v, J4_65)
    R["TBP_C_p3_m65"] = s3["TBP_C_total"]; R["TBP_C_p4_m65"] = s4["TBP_C_total"]
    for c_ in ("TBP_C_varones", "TBP_C_mujeres"):
        R[c_ + "_p4_m65"] = s4[c_]
    ab65 = tbp_ab_sexos(s4, A_v, A_m65, Ex["E_v"], E_m65, tau, rho_v, J4_65)
    for c_ in ab65.columns:
        R[c_ + "_p4_m65"] = ab65[c_]
    desc = descomponer_retiro_mujeres(N0, sh_v, Sx["S_v"], S_m65, Sx["S_m"], A_v, A_m65, A_m, tau, rho_v, J65, JJ["J_star"])
    aux.update(p3=p3, p4=p4, p5=p5, s3=s3, s4=s4, ab=ab, ab65=ab65, mig=mig, desc=desc, w=w, JJ=JJ, JJ_rw=JJ_rw, Sx=Sx, Ex=Ex, N4=N4, J4=J4,
               sh_v=sh_v, rho_v=rho_v, tau=tau, A_v=A_v, A_m=A_m, A_m65=A_m65, edad_m=edad_retiro_mujeres)
    return dict(R=R, **aux, con_sexo=True)


# ================================================================== 8) CONTROLES (asserts) CON LOS DATOS REALES
def controles_modelo_avanzado(res, d, verbose=True):
    """Asserts del modelo ya construido (datos reales). Devuelve lista de mensajes OK."""
    R, msgs = res["R"], []
    dd = d.set_index("cohorte")
    tau, rho_c = res.get("tau", TAU_DEF), RHO_DEF
    # p0 reproduce las columnas de d
    assert np.allclose(R["TBP_C_p0_A14_2"], dd["TBP_C_obs"], rtol=1e-9) and np.allclose(R["TBP_C_p0_A30"], dd["TBP_C_legal"], rtol=1e-9)
    msgs.append("p0 reproduce TBP_C_obs (Ā=14,2) y TBP_C_legal (Ā=30) de `d`")
    tm = res["tabla_mor"]
    assert tm["rho_mor_implicito"].between(0, 1).all() and (tm["rho_mor_implicito"] < tm["rho_sin_moratoria"]).all()
    msgs.append(f"ρ_mor implícito ∈ (0,1) y < ρ sin moratoria en los {len(tm)} años (min {tm.rho_mor_implicito.min():.3f}, max {tm.rho_mor_implicito.max():.3f})")
    # ordenamiento por escenario: mayor ρ => menor TBP_C (solo cohortes con retiro > 2023, donde los escenarios difieren)
    if res["con_sexo"]:
        post = R.index + 65 > 2023
        a, b_, c_ = (R.loc[post, f"TBP_C_p4_rho_{k}"] for k in ("persiste", "mitad", "sin_moratorias"))
        assert (a > b_).all() and (b_ > c_).all(), "mayor ρ debe dar menor TBP_C"
        pre = ~post
        assert np.allclose(R.loc[pre, "TBP_C_p4_rho_persiste"], R.loc[pre, "TBP_C_p4_rho_sin_moratorias"]), "antes de 2024 los escenarios coinciden"
        msgs.append("escenarios de ρ: TBP_C(persiste) > TBP_C(mitad) > TBP_C(sin moratorias) en todas las cohortes con retiro > 2023; idénticos antes")
        Sx = res["Sx"]
        assert np.allclose(R["N_t"] * R["share_varones"] + R["N_t"] * (1 - R["share_varones"]), R["N_t"]) and R["share_varones"].between(0.45, 0.55).all()
        assert np.allclose(res["p3"]["N_v"] + res["p3"]["N_m"], R["N_t"])
        msgs.append("N_varones + N_mujeres = N_t; share_varones ∈ (0,45; 0,55)")
        assert Sx[["S_v", "S_m", "S_m65", "S_tot65"]].apply(lambda c: c.between(0, 1, inclusive="neither").all()).all()
        assert np.allclose(Sx["S_tot65"], dd["S65"], atol=1e-12)
        msgs.append("S_s(r_s) ∈ (0,1); S_Total(65) cohortal reproduce `S65` de `d`")
        p3 = res["p3"]
        indep = (p3["N_v"] * Sx["S_v"] * R["A_varones_65"] + p3["N_m"] * Sx["S_m"] * res["A_m"]) * tau / (R["J_star"] * res["rho_v"])
        assert np.allclose(p3["TBP_C_varones"] + p3["TBP_C_mujeres"], p3["TBP_C_total"]) and np.allclose(indep, R["TBP_C_p3"])
        msgs.append("TBP_C_varones + TBP_C_mujeres = TBP_C_total (calculado también por fuera como Σ_s N_s S_s Ā_s τ /(J*ρ))")
        # control de reducción al modelo base: share=1 varón, r=65, Ā constante, S = S65 de d, J = J de d
        base = tbp_c_sexos(R["N_t"], 1.0, dd["S65"], dd["S65"], 30.0, 30.0, TAU_DEF, RHO_DEF, dd["J"])
        assert np.allclose(base["TBP_C_total"], dd["TBP_C_legal"], rtol=1e-9) and np.allclose(base["TBP_C_mujeres"], 0)
        msgs.append("con share=1 varón, r=65, Ā=30 constante, ρ y τ constantes el modelo reproduce TBP_C_legal de `d`")
        # linealidad
        k = 1.7
        x1 = tbp_c_sexos(R["N_t"], res["sh_v"], Sx["S_v"], Sx["S_m"], R["A_varones_65"], res["A_m"], tau, res["rho_v"], R["J_star"])["TBP_C_total"]
        xa = tbp_c_sexos(R["N_t"], res["sh_v"], Sx["S_v"], Sx["S_m"], k * R["A_varones_65"], k * res["A_m"], tau, res["rho_v"], R["J_star"])["TBP_C_total"]
        xt = tbp_c_sexos(R["N_t"], res["sh_v"], Sx["S_v"], Sx["S_m"], R["A_varones_65"], res["A_m"], k * tau, res["rho_v"], R["J_star"])["TBP_C_total"]
        assert np.allclose(xa, k * x1) and np.allclose(xt, k * x1)
        msgs.append("linealidad: TBP_C escala exactamente con Ā y con τ (factor 1,7)")
        # p4 = p3 para cohortes ≤ 2024 ; migración sin ajuste = p4
        assert np.allclose(R.loc[R.index <= 2024, "TBP_C_p4"], R.loc[R.index <= 2024, "TBP_C_p3"])
        msgs.append("p4 = p3 para cohortes ≤ 2024 (solo cambian las ≥ 2025)")
        pb = res["p5"]
        assert np.allclose(pb["sob_v"] + pb["sob_m"], res["mig"]["pob_v"] + res["mig"]["pob_m"]), "N_efectivo·S debe igualar la población ONU"
        sin = tbp_c_sexos(res["N4"], res["sh_v"], Sx["S_v"], Sx["S_m"], R["A_varones_65"], res["A_m"], tau, res["rho_v"], res["J4"], 1.0, 1.0)
        assert np.allclose(sin["TBP_C_total"], R["TBP_C_p4"])
        msgs.append("migración: N_efectivo·S = población ONU a la edad de retiro; con m=1 vuelve exactamente a p4")
        ab = res["ab"]
        assert np.allclose(ab["TBP_A_total"], ab["D_star"] * ab["TBP_B_total"])
        msgs.append("identidad TBP_A_total = D*·TBP_B_total (agregación: TBP_A aditivo, TBP_B ponderado por sobrevivientes)")
    if verbose:
        for m_ in msgs:
            print("OK:", m_)
    return msgs


# ================================================================== 9) AUTOTEST CON DATOS SINTÉTICOS
def _banner_ma(txt="DATOS SINTÉTICOS — no son Argentina"):
    line = "#" * 78
    print("\n".join([line, "##" + txt.center(74) + "##", line]))


def autotest_modelo_avanzado(verbose=True):
    """Pruebas de las funciones puras con datos SINTÉTICOS (inventados, solo para verificar código; nunca se usan en salidas reales)."""
    if verbose:
        _banner_ma()
    co = pd.Index(np.arange(2000, 2006), name="cohorte")
    # población sintética: 120 mil personas por edad y sexo en todos los años, varones algo menos
    yrs = np.arange(2060, 2075)
    PM = pd.DataFrame(100000.0, index=yrs, columns=np.arange(0, 101))
    PF = pd.DataFrame(120000.0, index=yrs, columns=np.arange(0, 101))
    # J*: varones 65+ (36 edades, incl. 100) + mujeres 60+ (41 edades)
    J = j_pasivos(PM, PF, [2065], edad_m=60)
    assert abs(J.loc[2065, "J_v"] - 36 * 1e5) < 1e-6 and abs(J.loc[2065, "J_m"] - 41 * 1.2e5) < 1e-6
    assert abs(J.loc[2065, "J65"] - 36 * 2.2e5) < 1e-6
    assert abs((J.loc[2065, "J_star"] - J.loc[2065, "J65"]) - 5 * 1.2e5) < 1e-6          # difieren en las 5 edades 60-64 de mujeres
    # reponderación: w=0,5 para todas las cohortes -> J a la mitad
    w = pd.Series(0.5, index=np.arange(1900, 2101))
    assert abs(j_pasivos(PM, PF, [2065], edad_m=60, w=w).loc[2065, "J_star"] - 0.5 * J.loc[2065, "J_star"]) < 1e-6
    # share por SRB
    assert abs(share_varones(105.0) - 105.0 / 205.0) < 1e-15 and abs(share_varones(100.0) - 0.5) < 1e-15
    # ρ implícito: ida y vuelta
    s_ = np.array([0.3, 0.5, 0.7]); rm = np.array([0.25, 0.30, 0.35]); rs = np.array([0.5, 0.55, 0.6])
    rt = s_ * rm + (1 - s_) * rs
    assert np.allclose(rho_implicito(rt, rs, s_), rm)
    # tabla y escenarios
    sr = pd.DataFrame({"anio": [2021, 2022, 2023], "rho": rt, "rho_sin_moratoria": rs})
    be = pd.DataFrame({"anio": [2021, 2022, 2023], "share_moratoria": s_})
    tm = tabla_rho_moratoria(sr, be)
    r_p, _ = rho_por_escenario([2022, 2030], tm, "persiste"); r_h, _ = rho_por_escenario([2030], tm, "mitad"); r_0, _ = rho_por_escenario([2030], tm, "sin_moratorias")
    assert abs(r_p[2022] - rt[1]) < 1e-12 and abs(r_p[2030] - rt[2]) < 1e-12 and abs(r_0[2030] - rs[2]) < 1e-12
    assert r_p[2030] < r_h[2030] < r_0[2030]                                    # sin moratorias => ρ más alto
    try:
        rho_por_escenario([2030], tm, "otro"); raise AssertionError("debía fallar")
    except ValueError:
        pass
    # TBP_C por sexo
    N = pd.Series(1e6, index=co); Sv = pd.Series(0.85, index=co); Sm = pd.Series(0.93, index=co)
    Jc = pd.Series(1e7, index=co)
    a = tbp_c_sexos(N, 0.5, Sv, Sm, 10.0, 8.0, 0.2, 0.4, Jc)
    assert np.allclose(a["N_v"] + a["N_m"], N) and np.allclose(a["TBP_C_varones"] + a["TBP_C_mujeres"], a["TBP_C_total"])
    assert np.allclose(a["TBP_C_total"], (5e5 * 0.85 * 10 + 5e5 * 0.93 * 8) * 0.2 / (1e7 * 0.4))
    b = tbp_c_sexos(N, 1.0, Sv, Sv, 30.0, 30.0, 0.2177, 0.403, Jc)              # control: share=1 varón == fórmula base
    assert np.allclose(b["TBP_C_total"], N * Sv * 30 * 0.2177 / (Jc * 0.403)) and np.allclose(b["TBP_C_mujeres"], 0)
    assert np.allclose(tbp_c_sexos(N, 0.5, Sv, Sm, 20.0, 16.0, 0.2, 0.4, Jc)["TBP_C_total"], 2 * a["TBP_C_total"])      # linealidad en Ā
    assert np.allclose(tbp_c_sexos(N, 0.5, Sv, Sm, 10.0, 8.0, 0.4, 0.4, Jc)["TBP_C_total"], 2 * a["TBP_C_total"])       # linealidad en τ
    assert (tbp_c_sexos(N, 0.5, Sv, Sm, 10.0, 8.0, 0.2, 0.8, Jc)["TBP_C_total"] < a["TBP_C_total"]).all()               # ρ mayor => menor
    # TBP_A y TBP_B por sexo: identidad TBP_A = D*·TBP_B
    ab = tbp_ab_sexos(a, 10.0, 8.0, pd.Series(17.0, index=co), pd.Series(26.0, index=co), 0.2, 0.4, Jc)
    assert np.allclose(ab["TBP_A_total"], ab["D_star"] * ab["TBP_B_total"])
    assert np.allclose(ab["TBP_A_total"], a["TBP_C_varones"] / 17.0 + a["TBP_C_mujeres"] / 26.0)
    # migración: N_efectivo·S = población
    mg = factor_migracion(pd.DataFrame({65: [3e5, 3e5, 3e5, 3e5, 3e5, 3e5]}, index=co + 65), pd.DataFrame({60: [3.3e5] * 6}, index=co + 60),
                          co, N, 0.5, Sv, Sm, edad_m=60)
    assert np.allclose(mg["m_v"] * N * 0.5 * Sv, 3e5) and np.allclose(mg["m_m"] * N * 0.5 * Sm, 3.3e5)
    c = tbp_c_sexos(N, 0.5, Sv, Sm, 10.0, 8.0, 0.2, 0.4, Jc, mg["m_v"], mg["m_m"])
    assert np.allclose(c["sob_v"] + c["sob_m"], 3e5 + 3.3e5)
    # descomposición: pasos coherentes (a: 65 ambos; d = p3)
    de = descomponer_retiro_mujeres(N, 0.5, Sv, pd.Series(0.9, index=co), Sm, 10.0, 8.0, 7.0, 0.2, 0.4, Jc, Jc * 1.1)
    assert np.allclose(de["d_mas_J_star"], tbp_c_sexos(N, 0.5, Sv, Sm, 10.0, 7.0, 0.2, 0.4, Jc * 1.1)["TBP_C_total"])
    if verbose:
        print("autotest OK (J* y reponderación, share SRB, ρ_mor implícito y escenarios, TBP_C por sexo, linealidad, control share=1, "
              "TBP_A/TBP_B y D*, migración, descomposición). Datos SINTÉTICOS: no son Argentina.")
        _banner_ma("FIN AUTOTEST — estos números NO son Argentina")
    return True


if __name__ == "__main__":
    autotest_modelo_avanzado()
