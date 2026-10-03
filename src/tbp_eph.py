# -*- coding: utf-8 -*-
"""
tbp_eph.py — Calibración de Ā (años de aporte esperados por persona de la cohorte) con la EPH (INDEC).

Rutina modular para el proyecto TBP — Índice de Cuna Vacía.

Flujo:
    1. plan_descarga / descargar_eph   -> baja las bases usuarias individuales trimestrales (con confirmación explícita)
    2. find_eph_files / read_all       -> lee las bases (txt o zip de INDEC)
    3. add_flags                       -> filtra ocupados y marca "registrado" (descuento jubilatorio PP07H)
    4. build_cells + ajuste logit      -> pseudo-panel cohorte x edad (densidad de aportes)
    5. edad_ingreso_*                  -> edad efectiva de ingreso al empleo registrado, por cohorte
    6. estimar_abar                    -> Ā por cohorte (3 reglas para independientes)
    7. tbp_con_abar                    -> TBP_C y TBP_A usando Ā(t) en lugar de un valor único

AVISOS METODOLÓGICOS (leer):
  * La EPH es una encuesta transversal y urbana: NO observa la edad del primer empleo registrado ni la historia de aportes
    de cada persona. Se trabaja con un pseudo-panel (cohorte = ANO4 − CH06) y se asume que el perfil por edad es estable
    entre cohortes (modelo logit aditivo cohorte + edad). Edad, período y cohorte no se pueden separar del todo.
  * PP07H ("¿le descuentan jubilación?") se pregunta a asalariados y mide la semana de referencia, no el año.
    Una persona con descuento no necesariamente suma "años de aporte" de ley (moratorias, regímenes provinciales, etc.).
  * La base individual no trae una variable inequívoca de aporte de cuentapropistas: por eso hay tres reglas
    ("solo_asalariados" = cota inferior, "pp07i", "escenario") y se reportan las tres.
  * Los nombres de variables y la lectura están basados en el diseño de registro de INDEC; verificar con la primera
    descarga real (ver `resumen_base`).
  * No hay valor de Ā "verdadero" para Argentina hasta correr esto con datos reales. Los números del autotest son sintéticos.

Uso mínimo:
    import tbp_eph as e
    e.descargar_eph("datos/eph")                                   # sólo muestra el plan (no descarga)
    e.descargar_eph("datos/eph", confirmado=True)                  # descarga de verdad
    df = e.read_all(e.find_eph_files(["datos/eph"]))
    tabla = e.estimar_abar(df, s65)                                # s65: Series cohorte -> supervivencia a 65
"""
import os, re, io, glob, time, zipfile, warnings, tempfile, urllib.request
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ constantes
EDAD_MIN, EDAD_MAX = 18, 64
EDADES = np.arange(EDAD_MIN, EDAD_MAX + 1)               # 47 edades simples
BASE_URL = "https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph"
# Disponibilidad verificada (2 oct 2026, por cabecera HTTP y firma ZIP): 2017-T2 a 2025-T4.
# 2016 y 2017-T1 NO están con este patrón de nombre en el sitio actual de INDEC.
DISPONIBLE_DESDE, DISPONIBLE_HASTA = (2017, 2), (2025, 4)
USER_AGENT = "Mozilla/5.0 (compatible; TBP-proyecto-universitario)"
MIN_N_CELDA = 20          # mínimo de observaciones (sin ponderar) por celda cohorte x edad
MIN_EDADES_COHORTE = 3    # mínimo de edades observadas para estimar el efecto propio de una cohorte
GOMPERTZ_B = 0.085        # pendiente de la mortalidad adulta (supuesto)
IND_RULE_DEFAULT = "solo_asalariados"
IND_SHARE_DEFAULT = None
NEEDED = {"ANO4", "TRIMESTRE", "CH04", "CH06", "ESTADO", "CAT_OCUP", "PP07H", "PP07I", "PONDERA"}
OBLIGATORIAS = {"ANO4", "CH06", "ESTADO", "PONDERA"}


# ================================================================== 1) DESCARGA
def urls_eph(desde=DISPONIBLE_DESDE, hasta=DISPONIBLE_HASTA):
    """Lista de bases trimestrales (año, trimestre, nombre, url) en el rango pedido."""
    out = []
    for y in range(desde[0], hasta[0] + 1):
        for t in (1, 2, 3, 4):
            if (y, t) < tuple(desde) or (y, t) > tuple(hasta):
                continue
            nombre = f"EPH_usu_{t}_Trim_{y}_txt.zip"
            out.append({"anio": y, "trim": t, "nombre": nombre, "url": f"{BASE_URL}/{nombre}"})
    return out


def _ctx_ssl():
    """Contexto SSL con verificación ACTIVA. Usa certifi si está instalado (Python de macOS suele no traer certificados raíz)."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _abrir(url, metodo="GET", rango=None, timeout=60):
    req = urllib.request.Request(url, method=metodo, headers={"User-Agent": USER_AGENT})
    if rango:
        req.add_header("Range", rango)
    return urllib.request.urlopen(req, timeout=timeout, context=_ctx_ssl())


def _curl(url, destino=None, solo_cabecera=False, timeout=120):
    """Alternativa con `curl` del sistema (usa el almacén de certificados del sistema; la verificación sigue activa)."""
    import subprocess
    cmd = ["curl", "-sL", "--max-time", str(timeout), "-A", USER_AGENT]
    if solo_cabecera:
        r = subprocess.run(cmd + ["-I", url], capture_output=True, text=True)
        cab = [l for l in r.stdout.splitlines() if l.lower().startswith("content-length")]
        return int(cab[-1].split(":")[1]) if cab else None
    subprocess.run(cmd + ["-o", destino, url], check=True)


def plan_descarga(destino="datos/eph", desde=DISPONIBLE_DESDE, hasta=DISPONIBLE_HASTA, consultar_tamanos=True):
    """Arma el plan SIN descargar: qué archivos, tamaño (cabecera HTTP HEAD) y cuáles ya están en `destino`."""
    plan = []
    for it in urls_eph(desde, hasta):
        it = dict(it); it["existe"] = os.path.exists(os.path.join(destino, it["nombre"])); it["bytes"] = None
        if consultar_tamanos:
            try:
                with _abrir(it["url"], "HEAD") as r:
                    it["bytes"] = int(r.headers.get("Content-Length", 0)) or None
                    it["tipo"] = r.headers.get("Content-Type", "")
            except Exception as ex:                       # problema de certificados/red: se prueba curl; si no, se informa
                try:
                    it["bytes"] = _curl(it["url"], solo_cabecera=True)
                except Exception as ex2:
                    it["error"] = f"{ex} | curl: {ex2}"
        plan.append(it)
    return pd.DataFrame(plan)


def descargar_eph(destino="datos/eph", desde=DISPONIBLE_DESDE, hasta=DISPONIBLE_HASTA, confirmado=False, pausa=0.5):
    """Descarga las bases usuarias individuales de la EPH desde INDEC.

    `confirmado=False` (por defecto): MODO PRUEBA. Muestra el plan (archivos y tamaño total) y NO descarga nada.
    `confirmado=True`: descarga los que falten. Verifica que cada archivo sea un ZIP real (INDEC devuelve una página HTML
    con código 200 cuando el archivo no existe) y no vuelve a bajar los que ya están.
    """
    os.makedirs(destino, exist_ok=True)
    plan = plan_descarga(destino, desde, hasta)
    faltan = plan[~plan["existe"]]
    total_mb = (faltan["bytes"].fillna(0).sum()) / 1e6
    print(f"EPH: {len(plan)} archivos en el rango; {len(faltan)} por descargar (~{total_mb:.1f} MB). Fuente: {BASE_URL}/")
    if not confirmado:
        print("MODO PRUEBA: no se descargó nada. Para descargar: descargar_eph(..., confirmado=True)")
        return plan
    ok, fallidos = 0, []
    for _, it in faltan.iterrows():
        ruta = os.path.join(destino, it["nombre"]); tmp = ruta + ".part"
        try:
            with _abrir(it["url"]) as r, open(tmp, "wb") as f:
                cab = r.read(4); f.write(cab)
                if cab[:2] != b"PK":
                    raise ValueError("la respuesta no es un ZIP (¿archivo inexistente?)")
                while True:
                    bloque = r.read(1 << 20)
                    if not bloque:
                        break
                    f.write(bloque)
            os.replace(tmp, ruta); ok += 1
            print(f"  ✔ {it['nombre']} ({os.path.getsize(ruta)/1e6:.1f} MB)")
        except Exception as ex:
            if "CERTIFICATE" in str(ex).upper() or "SSL" in str(ex).upper():      # reintento con curl (verificación activa)
                try:
                    _curl(it["url"], destino=tmp)
                    with open(tmp, "rb") as g:
                        if g.read(2) != b"PK":
                            raise ValueError("la respuesta no es un ZIP (¿archivo inexistente?)")
                    os.replace(tmp, ruta); ok += 1
                    print(f"  ✔ {it['nombre']} ({os.path.getsize(ruta)/1e6:.1f} MB, vía curl)")
                    time.sleep(pausa); continue
                except Exception as ex2:
                    ex = ex2
            fallidos.append((it["nombre"], str(ex)))
            if os.path.exists(tmp): os.remove(tmp)
            print(f"  ✘ {it['nombre']}: {ex}")
        time.sleep(pausa)
    print(f"Listo: {ok} descargados, {len(fallidos)} fallidos.")
    return plan


# ================================================================== 2) LECTURA
def find_eph_files(rutas=("datos/eph", "../datos/eph", "../../datos/eph")):
    """Busca bases individuales (usu_individual_T*.txt/.csv, o EPH_usu_*.zip con una base individual adentro)."""
    out = []
    for r in rutas:
        if not os.path.isdir(r):
            continue
        for p in sorted(glob.glob(os.path.join(r, "**", "*"), recursive=True)):
            b = os.path.basename(p).lower()
            if os.path.isfile(p) and re.search(r"usu_individual.*\.(txt|csv)$", b):
                out.append({"path": p, "member": None})
            elif os.path.isfile(p) and b.endswith(".zip") and "eph_usu" in b:
                with zipfile.ZipFile(p) as z:
                    for m in z.namelist():
                        if re.search(r"usu_individual.*\.(txt|csv)$", m.lower()):
                            out.append({"path": p, "member": m})
    return out


def _leer_texto(handle, nombre=""):
    cab = handle.readline() if hasattr(handle, "readline") else ""
    sep = ";" if cab.count(";") >= cab.count(",") else ","       # INDEC usa ';' (se autodetecta)
    handle.seek(0)
    return pd.read_csv(handle, sep=sep, usecols=lambda c: c.strip().upper() in NEEDED, low_memory=False)


def read_individual(src):
    """Lee UNA base individual trimestral (sólo las columnas necesarias). Columnas en MAYÚSCULAS, valores numéricos."""
    if src["member"] is None:
        with open(src["path"], "r", encoding="latin-1", newline="") as f:
            df = _leer_texto(f, src["path"])
    else:
        with zipfile.ZipFile(src["path"]) as z, z.open(src["member"]) as raw:
            df = _leer_texto(io.StringIO(raw.read().decode("latin-1")), src["member"])
    df.columns = [c.strip().upper() for c in df.columns]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    faltan = OBLIGATORIAS - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias {sorted(faltan)} en {src}. Revisar el diseño de registro de INDEC.")
    for opt in ("CAT_OCUP", "PP07H", "PP07I", "CH04", "TRIMESTRE"):
        if opt not in df.columns:
            df[opt] = np.nan
    return df


def read_all(srcs):
    return pd.concat([read_individual(s) for s in srcs], ignore_index=True)


def resumen_base(df):
    """Control rápido tras cargar datos reales: filas por año, % de nulos en variables clave, valores de PP07H."""
    print("Filas por año:", df.groupby("ANO4").size().to_dict())
    print("Nulos (%):", (df[["CH06", "ESTADO", "CAT_OCUP", "PP07H", "PP07I", "PONDERA"]].isna().mean() * 100).round(1).to_dict())
    print("ESTADO (1 ocupado, 2 desocupado, 3 inactivo):", df["ESTADO"].value_counts(dropna=False).sort_index().to_dict())
    print("PP07H entre asalariados (1 sí, 2 no, 9 NS/NR):", df.loc[df["CAT_OCUP"] == 3, "PP07H"].value_counts(dropna=False).sort_index().to_dict())


# ================================================================== 3) FILTRO: ocupados con descuento jubilatorio
def add_flags(df, ind_rule=IND_RULE_DEFAULT, ind_share=IND_SHARE_DEFAULT, sexo=None):
    """Población 18-64 con entrevista individual; construye `reg` = prob. de estar aportando.
    Asalariado (CAT_OCUP==3): reg = (PP07H==1). Independiente (1,2): según `ind_rule`. Desocupado/inactivo: 0."""
    d = df[(df["CH06"] >= EDAD_MIN) & (df["CH06"] <= EDAD_MAX) & (df["ESTADO"].isin([1, 2, 3]))].copy()
    if sexo is not None:
        d = d[d["CH04"] == sexo]
    ocupado = d["ESTADO"] == 1
    asal = ocupado & (d["CAT_OCUP"] == 3)
    indep = ocupado & d["CAT_OCUP"].isin([1, 2])
    reg = np.zeros(len(d))
    reg[asal.values] = (d.loc[asal, "PP07H"] == 1).astype(float).values       # 2 (no) y 9 (NS/NR) => no registrado
    if ind_rule == "pp07i":
        reg[indep.values] = (d.loc[indep, "PP07I"] == 1).astype(float).values
    elif ind_rule == "escenario":
        if ind_share is None or not (0 <= ind_share <= 1):
            raise ValueError("ind_rule='escenario' requiere ind_share en [0,1] (supuesto explícito).")
        reg[indep.values] = float(ind_share)
    elif ind_rule != "solo_asalariados":
        raise ValueError(f"ind_rule desconocida: {ind_rule}")
    d["reg"] = reg
    d["edad"] = d["CH06"].astype(int)
    d["cohorte"] = (d["ANO4"] - d["CH06"]).astype(int)        # error de ±1 año (no se usa la fecha exacta)
    d["w"] = d["PONDERA"].astype(float)
    return d[["cohorte", "edad", "w", "reg"]]


# ================================================================== 4) PSEUDO-PANEL + MODELO
def build_cells(d, min_n=MIN_N_CELDA):
    """Densidad ponderada por (cohorte, edad), agregando todos los trimestres/años en que esa cohorte tuvo esa edad."""
    d = d.assign(wreg=d["w"] * d["reg"])
    g = d.groupby(["cohorte", "edad"]).agg(n=("w", "size"), w=("w", "sum"), wreg=("wreg", "sum")).reset_index()
    g["dens"] = g["wreg"] / g["w"]
    return g[g["n"] >= min_n].reset_index(drop=True)


def _sig(x):
    return 1 / (1 + np.exp(-x))


def fit_age_cohort_logit(cells, iters=100, ridge=1e-3):
    """Logit aditivo: logit d_c(a) = alpha_c + f(a). Supuesto: el perfil por edad f(a) es común a todas las cohortes."""
    coh = np.sort(cells["cohorte"].unique()); eds = np.sort(cells["edad"].unique())
    ci = {c: i for i, c in enumerate(coh)}; ei = {a: i for i, a in enumerate(eds)}
    X = np.zeros((len(cells), len(coh) + len(eds) - 1))
    for r, (c, a) in enumerate(zip(cells["cohorte"], cells["edad"])):
        X[r, ci[c]] = 1.0
        if ei[a] > 0:
            X[r, len(coh) + ei[a] - 1] = 1.0
    y = cells["dens"].values; m = cells["n"].values.astype(float)
    yy = np.clip(y, 0.01, 0.99)
    beta = np.linalg.solve(X.T @ (m[:, None] * X) + ridge * np.eye(X.shape[1]), X.T @ (m * np.log(yy / (1 - yy))))
    for _ in range(iters):
        eta = X @ beta
        mu = np.clip(_sig(eta), 1e-6, 1 - 1e-6)
        W = m * mu * (1 - mu)
        z = eta + (y - mu) / (mu * (1 - mu))
        new = np.linalg.solve(X.T @ (W[:, None] * X) + ridge * np.eye(X.shape[1]), X.T @ (W * z))
        if np.max(np.abs(new - beta)) < 1e-9:
            beta = new; break
        beta = new
    alpha = pd.Series(beta[:len(coh)], index=coh)
    f = pd.Series(np.r_[0.0, beta[len(coh):]], index=eds)
    n_ed = cells.groupby("cohorte")["edad"].nunique().reindex(coh)
    return {"alpha": alpha, "f": f, "n_edades": n_ed, "cells": cells}


def extrapolar_alpha(fit, cohortes, modo="ultimas_k", k=5, ventana_tendencia=15):
    """Efecto de cohorte para cohortes con pocos datos (muy jóvenes, muy viejas o futuras). Supuesto explícito."""
    ok = fit["alpha"][fit["n_edades"] >= MIN_EDADES_COHORTE]
    out = {}
    for c in cohortes:
        if c in ok.index:
            out[c] = ok[c]
        elif c > ok.index.max():
            if modo == "ultimas_k":
                out[c] = ok.iloc[-k:].mean()
            elif modo == "tendencia":
                w = ok.iloc[-ventana_tendencia:]; b = np.polyfit(w.index.values, w.values, 1)
                out[c] = np.polyval(b, c)
            else:
                raise ValueError(modo)
        else:
            out[c] = ok.iloc[:k].mean()
    return pd.Series(out)


def densidad_modelada(fit, alpha_c):
    """Matriz cohorte x edad (18..64) de d_c(a). Edades sin datos usan el perfil f(a) del modelo (interpolado)."""
    f = fit["f"].reindex(EDADES).interpolate(limit_direction="both")
    return pd.DataFrame(_sig(alpha_c.values[:, None] + f.values[None, :]), index=alpha_c.index, columns=EDADES)


# ================================================================== 5) EDAD EFECTIVA DE INGRESO AL EMPLEO REGISTRADO
def edad_ingreso_modelada(dens, umbral=0.5):
    """Por cohorte, a partir de la densidad modelada d_c(a):
        meseta   = máx_a d_c(a)
        F_c(a)   = envolvente creciente de d_c(a) / meseta  (se interpreta como "fracción que ya ingresó" a la edad a)
        edad_umbral = primera edad con F >= umbral (por defecto 50 % de la meseta)
        edad_media  = 18 + Σ_{a=18}^{63} (1 − F_c(a))   (edad media de ingreso si F fuera la distribución de la edad de ingreso)
    ES UNA APROXIMACIÓN: la EPH no observa el primer empleo registrado; supone ingreso monótono sin salidas del empleo registrado."""
    v = dens.values
    meseta = v.max(axis=1)
    F = np.clip(np.maximum.accumulate(v, axis=1) / meseta[:, None], 0, 1)
    edad_umbral = np.array([EDADES[np.argmax(F[i] >= umbral)] for i in range(len(F))], dtype=float)
    edad_media = EDAD_MIN + (1 - F[:, :-1]).sum(axis=1)
    return pd.DataFrame({"meseta_densidad": meseta, "edad_ingreso_umbral50": edad_umbral, "edad_ingreso_media": edad_media},
                        index=dens.index)


def edad_ingreso_observada(fit, dens_modelada, umbral=0.5):
    """Estimación EMPÍRICA (sin modelo) de la edad de ingreso: primera edad OBSERVADA en que la densidad de la cohorte
    llega al `umbral` de su meseta modelada. Sólo para cohortes observadas desde edades tempranas; NaN en el resto."""
    cells = fit["cells"]; out = {}
    meseta = dens_modelada.max(axis=1)
    for c, g in cells.groupby("cohorte"):
        if c not in meseta.index:
            continue
        g = g.sort_values("edad")
        if g["edad"].min() > EDAD_MIN + 2:            # no vimos los años de entrada
            out[c] = np.nan; continue
        hit = g[g["dens"] >= umbral * meseta[c]]
        out[c] = float(hit["edad"].iloc[0]) if len(hit) else np.nan
    return pd.Series(out, name="edad_ingreso_observada").reindex(dens_modelada.index)


# ================================================================== 6) Ā
def supervivencia_gompertz(s65, b=GOMPERTZ_B):
    """S(a) desde el nacimiento para a=18..64 (Gompertz con pendiente b calibrada para que S(65)=s65 por cohorte)."""
    s65 = np.asarray(s65, float)
    a = -np.log(s65) * b / (np.exp(65 * b) - 1)
    return np.exp(-(a[:, None] / b) * (np.exp(b * EDADES[None, :]) - 1))


def abar_por_cohorte(dens, s65):
    """Ā(c) = Σ_{a=18}^{64} S_c(a) · d_c(a)  (incluye a quienes nunca aportan: densidad 0)."""
    S = supervivencia_gompertz(s65.reindex(dens.index).values)
    return pd.Series((S * dens.values).sum(axis=1), index=dens.index, name="A_bar"), S


def pipeline(df_ind, s65, ind_rule=IND_RULE_DEFAULT, ind_share=IND_SHARE_DEFAULT, sexo=None,
             modo_extrap="ultimas_k", cohortes=None):
    """EPH individual -> tabla por cohorte (Ā y edad de ingreso). Igual para datos sintéticos y reales."""
    d = add_flags(df_ind, ind_rule, ind_share, sexo)
    cells = build_cells(d)
    fit = fit_age_cohort_logit(cells)
    cohortes = list(cohortes) if cohortes is not None else list(s65.index)
    alpha_c = extrapolar_alpha(fit, cohortes, modo=modo_extrap)
    dens = densidad_modelada(fit, alpha_c)
    abar, S = abar_por_cohorte(dens, s65)
    ing = edad_ingreso_modelada(dens)
    tabla = pd.DataFrame({"A_bar": abar,
                          "n_edades_obs": fit["n_edades"].reindex(abar.index).fillna(0).astype(int),
                          "S65": s65.reindex(abar.index),
                          "A_max_sin_densidad": S.sum(axis=1)}).join(ing)
    tabla["edad_ingreso_observada"] = edad_ingreso_observada(fit, dens)
    return {"tabla": tabla, "dens": dens, "fit": fit, "cells": cells}


def estimar_abar(df_ind, s65, cohortes=None, modo_extrap="ultimas_k", ind_share_escenario=0.5):
    """Ā por cohorte con las TRES reglas para independientes. Devuelve un DataFrame (una fila por cohorte):
        A_bar_solo_asalariados (cota inferior) | A_bar_pp07i | A_bar_indep50 (escenario) |
        edad de ingreso (modelada / observada) | n_edades_obs | S65"""
    reglas = {"solo_asalariados": dict(ind_rule="solo_asalariados"),
              "pp07i": dict(ind_rule="pp07i"),
              f"indep{int(round(ind_share_escenario * 100))}": dict(ind_rule="escenario", ind_share=ind_share_escenario)}
    out, base = {}, None
    for nombre, kw in reglas.items():
        r = pipeline(df_ind, s65, cohortes=cohortes, modo_extrap=modo_extrap, **kw)
        chequeos(r)
        out[f"A_bar_{nombre}"] = r["tabla"]["A_bar"]
        if base is None:
            base = r["tabla"][["n_edades_obs", "S65", "meseta_densidad", "edad_ingreso_umbral50", "edad_ingreso_media", "edad_ingreso_observada"]]
    return pd.DataFrame(out).join(base)


def chequeos(res):
    t, dens, cells = res["tabla"], res["dens"], res["cells"]
    assert np.all((cells["dens"] >= 0) & (cells["dens"] <= 1)), "densidad observada fuera de [0,1]"
    assert np.all((dens.values >= 0) & (dens.values <= 1)), "densidad modelada fuera de [0,1]"
    assert np.all((t["A_bar"] >= 0) & (t["A_bar"] <= 47)), "A_bar fuera de [0,47]"
    assert np.all(t["A_bar"] <= t["A_max_sin_densidad"] + 1e-9), "A_bar supera Σ S(a) (densidad = 1)"
    assert np.all((t["edad_ingreso_umbral50"] >= EDAD_MIN) & (t["edad_ingreso_umbral50"] <= EDAD_MAX)), "edad de ingreso fuera de rango"
    assert np.all((t["edad_ingreso_media"] >= EDAD_MIN) & (t["edad_ingreso_media"] <= EDAD_MAX)), "edad media de ingreso fuera de rango"
    a2, _ = abar_por_cohorte(dens, (t["S65"] + 0.02).clip(upper=0.999))
    assert np.all(a2.values > t["A_bar"].values - 1e-12), "monotonía en S65 violada"
    return True


# ================================================================== 7) CONEXIÓN CON EL TBP
def tbp_con_abar(d, abar, tau=0.2177, rho=0.403, col_abar="A_bar_solo_asalariados"):
    """TBP_C y TBP_A usando Ā(t) por cohorte (en vez de un valor único).
    `d`: DataFrame del notebook principal con columnas cohorte, N_t, S65, J, E65. `abar`: salida de estimar_abar (o Serie)."""
    a = abar[col_abar] if isinstance(abar, pd.DataFrame) else abar
    x = d.set_index("cohorte").join(a.rename("A_bar_eph"), how="left")
    x["TBP_C_Abar"] = x["N_t"] * x["S65"] * x["A_bar_eph"] * tau / (x["J"] * rho)
    x["TBP_A_Abar"] = x["TBP_C_Abar"] / x["E65"]
    return x.reset_index()


# ================================================================== 8) DATOS SINTÉTICOS Y AUTOTEST
def banner(txt="DATOS SINTÉTICOS — no son Argentina"):
    line = "#" * 78
    print("\n".join([line, "##" + txt.center(74) + "##", line]))


def _f_edad_sint(a):
    return 1.2 * np.exp(-((np.asarray(a) - 40) / 18.0) ** 2) - 1.0


def _alpha_sint(c):
    return -0.2 + 0.008 * (np.asarray(c) - 1970)


def _s65_sint(c):
    return np.clip(0.70 + 0.0035 * (np.asarray(c) - 1950), 0.5, 0.97)


def generar_eph_sintetica(anios=range(2003, 2025), n_por_edad=25, seed=123):
    """EPH de juguete con las mismas columnas que la real. NO son datos de Argentina."""
    rng = np.random.default_rng(seed); filas = []
    for y in anios:
        for q in (1, 2, 3, 4):
            for a in range(14, 71):
                p = _sig(_alpha_sint(y - a) + _f_edad_sint(a) + 0.10 * np.sin((y - 2003) / 3.0))
                reg = rng.random(n_por_edad) < p
                v = rng.random(n_por_edad)
                estado = np.where(reg, 1, np.where(v < 0.45, 1, 3))
                cat = np.where(estado == 1, np.where(reg | (v < 0.30), 3, 2), np.nan)
                filas.append(pd.DataFrame({"ANO4": y, "TRIMESTRE": q, "CH04": rng.integers(1, 3, n_por_edad), "CH06": a,
                                           "ESTADO": estado, "CAT_OCUP": cat,
                                           "PP07H": np.where(cat == 3, np.where(reg, 1, 2), np.nan),
                                           "PP07I": np.where(cat == 2, 2, np.nan),
                                           "PONDERA": rng.integers(300, 900, n_por_edad)}))
    return pd.concat(filas, ignore_index=True)


def autotest(verbose=True):
    """Prueba de punta a punta con datos SINTÉTICOS: pipeline, lector (txt y zip), filtros y conexión con el TBP."""
    if verbose: banner()
    df = generar_eph_sintetica()
    coh = np.arange(1940, 2036); s65 = pd.Series(_s65_sint(coh), index=coh)
    tabla = estimar_abar(df, s65, cohortes=coh)
    # verdad sintética
    dens_true = pd.DataFrame(_sig(_alpha_sint(coh)[:, None] + _f_edad_sint(EDADES)[None, :]), index=coh, columns=EDADES)
    a_true, _ = abar_por_cohorte(dens_true, s65)
    obs = tabla[tabla["n_edades_obs"] >= MIN_EDADES_COHORTE]
    # la regla "solo_asalariados" es la que coincide con cómo se generó el dato sintético (todos los registrados son asalariados)
    mae = (obs["A_bar_solo_asalariados"] - a_true.reindex(obs.index)).abs().mean()
    assert mae < 1.5, f"el pipeline no recupera la verdad sintética (MAE={mae:.2f})"
    assert (tabla["A_bar_solo_asalariados"] <= tabla["A_bar_pp07i"] + 1e-9).all(), "pp07i no puede dar menos que solo_asalariados"
    assert (tabla["A_bar_pp07i"] <= tabla["A_bar_indep50"] + 1e-9).all(), "indep50 no puede dar menos que pp07i"
    assert tabla["edad_ingreso_media"].between(18, 64).all() and tabla["edad_ingreso_umbral50"].between(18, 64).all()
    # lector: txt y zip con el nombre típico de INDEC
    with tempfile.TemporaryDirectory() as tmp:
        sub = df[df["ANO4"].isin([2010, 2011])].copy()
        sub.columns = [c.lower() if c in ("CH04", "CH06", "ESTADO") else c for c in sub.columns]
        p = os.path.join(tmp, "usu_individual_T110.txt"); sub.to_csv(p, sep=";", index=False)
        s1 = find_eph_files([tmp]); assert len(s1) == 1 and len(read_all(s1)) == len(sub)
        zp = os.path.join(tmp, "EPH_usu_1_Trim_2010_txt.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.write(p, "usu_individual_T110.txt")
        os.remove(p)
        s2 = find_eph_files([tmp]); assert len(s2) == 1 and s2[0]["member"] is not None and len(read_all(s2)) == len(sub)
    assert find_eph_files(["/ruta/que/no/existe"]) == []
    # conexión con el TBP: con Ā(t) constante debe reproducir la fórmula con un valor único
    d = pd.DataFrame({"cohorte": [2000, 2001], "N_t": [700000., 690000.], "S65": [0.88, 0.89], "J": [1.2e7, 1.2e7], "E65": [21., 21.]})
    fijo = pd.Series(30.0, index=[2000, 2001])
    r = tbp_con_abar(d, fijo)
    assert np.allclose(r["TBP_C_Abar"], d["N_t"] * d["S65"] * 30 * 0.2177 / (d["J"] * 0.403))
    if verbose:
        print(f"[sintético] error absoluto medio de Ā: {mae:.3f} años | cohortes observadas: {len(obs)}")
        print("Autotest OK (pipeline, 3 reglas, edad de ingreso, lector txt/zip, conexión con TBP).")
        banner("FIN AUTOTEST — estos números NO son Argentina")
    return tabla


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Calibración de Ā con la EPH (TBP)")
    ap.add_argument("--plan", action="store_true", help="muestra el plan de descarga (no descarga)")
    ap.add_argument("--descargar", action="store_true", help="descarga las bases que falten (requiere decisión explícita)")
    ap.add_argument("--destino", default="datos/eph")
    ap.add_argument("--autotest", action="store_true")
    a = ap.parse_args()
    if a.autotest: autotest()
    elif a.plan or a.descargar: print(descargar_eph(a.destino, confirmado=a.descargar).to_string())
    else: ap.print_help()
