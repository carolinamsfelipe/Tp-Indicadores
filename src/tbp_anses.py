# -*- coding: utf-8 -*-
"""
tbp_anses.py — ρ (tasa de sustitución) y τ (tasa de aporte) por año y su asignación por cohorte, para el TBP_C.

    TBP_C(t) = N_t · (1−μ) · Ā · τ / (J · ρ)        [en el código: N_t · S65 · Ā · τ / (J · ρ)]

Funciones:
    1. cargar_serie_anses        -> lector GENÉRICO del Excel "Estadísticas de la Seguridad Social" (si existe)
    2. digitalizar_anuario       -> digitaliza los gráficos 4.3 (p.91) y 3.1 (p.65) del Anuario ANSES 2008-2023 desde el PDF
    3. serie_rho_digitalizada    -> serie anual de ρ 2009-2023 (PDF si está; si no CSV; si no valores embebidos)
    4. serie_tau                 -> τ por año (CONSTANTE por supuesto + escenarios; no se verificó historia oficial)
    5. asignar_rho_tau_por_cohorte -> ρ_v, τ_v por cohorte según anio_65 = cohorte + 65, con extrapolación EXPLÍCITA
    6. tbp_c_dinamico            -> TBP_C y TBP_A con vectores ρ_v, τ_v (y Ā opcional por cohorte)
    7. autotest                  -> prueba con datos SINTÉTICOS rotulados (nunca se usan en salidas reales)

AVISOS METODOLÓGICOS (leer):
  * ρ = tasa de sustitución de ANSES = haber medio SIPA (diciembre) / salario imponible medio (noviembre). NO es haber/RIPTE.
  * El Anuario publica la serie anual 2009-2023 SOLO como gráfico (Gráfico 4.3, p.91). Los valores intermedios son
    "digitalizados del gráfico del Anuario (precisión aprox.)": NO son datos oficiales exactos. Los extremos (2009 y 2023)
    sí están rotulados en el Anuario y se usan tal cual.
  * τ: no se pudo verificar una serie histórica anual con fuentes oficiales; se usa un valor constante (supuesto) y escenarios.
  * Antes de 2009 y después de 2023 NO hay dato: se extrapola con una regla explícita elegida por quien llama y queda rotulada.
  * Los números del autotest son sintéticos y no representan a Argentina.
"""
import os, re, io, glob, unicodedata, warnings
import numpy as np
import pandas as pd

FUENTE_ANUARIO = "Anuario Estadístico ANSES 2008-2023"
ETIQ_DIG = "digitalizado del gráfico del Anuario (precisión aprox.)"
ETIQ_EXT = "etiqueta del gráfico del Anuario (valor publicado)"
URL_RAW = "https://raw.githubusercontent.com/carolinamsfelipe/Tp-Indicadores/main/datos/procesados/"
RUTAS_PROCESADOS = ["../datos/procesados", "datos/procesados", "github_staging/datos/procesados"]
RUTAS_EXCEL = ["../datos/anses", "datos/anses", "../../datos_tbp", "datos_tbp", "../datos_tbp", "."]
ANIOS = list(range(2009, 2024))

# Valores etiquetados del Anuario (p.91 y p.65)
ETIQ_RHO = {2009: 0.371, 2023: 0.403}
ETIQ_RHO_SM = {2009: 0.425, 2023: 0.563}
ETIQ_BENEF = {2009: dict(nm=2481182, m=2310228, tot=4791410), 2023: dict(nm=2217222, m=3766708, tot=5983930)}

# τ: SUPUESTOS (Anuario ANSES p.39: aporte personal 11 % + contribución patronal SIPA 10,77 % [inc. a], 12,35 % [inc. b], 16 % adm. pública)
TAU_ESCENARIOS = {"base": 0.11 + 0.1077, "inc_b": 0.11 + 0.1235, "sector_publico": 0.11 + 0.16}

# Salida de la digitalización (Anuario, trazos vectoriales). Se embebe para que el Colab no dependa del PDF.
# Orden: dic-2009 ... dic-2023. Los extremos de ρ se reemplazan por la etiqueta publicada en serie_rho_digitalizada().
_RHO_DIG = [0.3708, 0.3696, 0.3752, 0.3789, 0.4028, 0.3898, 0.3947, 0.4059, 0.4332, 0.4345, 0.4562, 0.4605, 0.4683, 0.4456, 0.4028]
_RHO_SM_DIG = [0.4245, 0.4298, 0.4283, 0.4506, 0.4823, 0.4739, 0.4941, 0.5217, 0.5766, 0.5822, 0.6145, 0.6132, 0.6266, 0.5959, 0.5630]
_BEN_NM_DIG = [2480830, 2400818, 2290420, 2320781, 2298715, 2265582, 2202136, 2191091, 2207658, 2210407, 2213156, 2196613, 2193840, 2226950, 2215930]
_BEN_TOT_DIG = [4790483, 4876018, 4887063, 4909128, 4914650, 5049862, 5491379, 5665222, 5725943, 5723170, 5731441, 5654178, 5673494, 5764551, 5985322]


# ================================================================== 1) LECTOR GENÉRICO DEL EXCEL DE ANSES
def _norm(x):
    s = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


PALABRAS_CLAVE = ("tasa de sustitucion", "haber medio", "salario imponible", "beneficiarios", "moratoria")


def buscar_excel_anses(rutas=None):
    """Busca .xls/.xlsx cuyo nombre contenga 'seguridad social' o 'estadisticas'. Devuelve lista de rutas."""
    out = []
    for r in (rutas or RUTAS_EXCEL):
        for ext in ("*.xls", "*.xlsx"):
            for f in glob.glob(os.path.join(r, ext)):
                n = _norm(os.path.basename(f))
                if "seguridad social" in n or "estadisticas" in n or "anses" in n:
                    out.append(os.path.abspath(f))
    return sorted(set(out))


def cargar_serie_anses(ruta=None, palabras=PALABRAS_CLAVE, rutas=None, max_filas_por_hoja=60):
    """Lector GENÉRICO: no supone estructura. Lista hojas y busca palabras clave en TODAS las celdas.
    Devuelve dict(encontrado, archivo, hojas, hallazgos[DataFrame], mensaje). Si no hay archivo: encontrado=False y avisa.
    `hallazgos`: hoja, fila, columna, palabra, texto_celda, valores_fila (lista cruda de la fila, para inspección humana)."""
    if ruta is None:
        c = buscar_excel_anses(rutas)
        ruta = c[0] if c else None
    if ruta is None or not os.path.exists(ruta):
        msg = ("NO se encontró el Excel de ANSES ('Estadísticas de la Seguridad Social', .xls/.xlsx). ANSES bloquea las descargas "
               "automáticas: bajarlo a mano y dejarlo en datos_tbp/ o github_staging/datos/anses/. Se sigue con la serie digitalizada del Anuario.")
        return dict(encontrado=False, archivo=None, hojas=[], hallazgos=pd.DataFrame(), mensaje=msg)
    try:
        xl = pd.ExcelFile(ruta)
    except Exception as e:  # p.ej. falta xlrd para .xls
        return dict(encontrado=False, archivo=ruta, hojas=[], hallazgos=pd.DataFrame(),
                    mensaje=f"Archivo encontrado pero no se pudo abrir ({type(e).__name__}: {e}). Para .xls instalar xlrd, o guardarlo como .xlsx.")
    pk = [_norm(p) for p in palabras]
    filas = []
    for h in xl.sheet_names:
        try:
            df = xl.parse(h, header=None)
        except Exception:
            continue
        for i in range(len(df)):
            for j in range(df.shape[1]):
                v = df.iat[i, j]
                if isinstance(v, str):
                    nv = _norm(v)
                    for w in pk:
                        if w in nv:
                            filas.append(dict(hoja=h, fila=i, columna=j, palabra=w, texto_celda=v[:120],
                                              valores_fila=[x for x in df.iloc[i].tolist() if pd.notna(x)][:max_filas_por_hoja]))
    return dict(encontrado=True, archivo=ruta, hojas=xl.sheet_names, hallazgos=pd.DataFrame(filas),
                mensaje=f"Archivo: {os.path.basename(ruta)} | {len(xl.sheet_names)} hojas | {len(filas)} celdas con palabras clave. "
                        "Revisar a mano `hallazgos` antes de usar cualquier cifra (no se asume estructura).")


# ================================================================== 2) DIGITALIZACIÓN DEL ANUARIO (requiere pymupdf + PDF)
def _puntos_polilinea(dr, n=15):
    P = [dr["items"][0][1]] + [it[2] for it in dr["items"][:n - 1]]
    return [(q.x, q.y) for q in P]


def digitalizar_anuario(pdf_path, pag_rho=91, pag_ben=65):
    """Digitaliza desde los trazos VECTORIALES del PDF (no OCR):
      Gráfico 4.3 (p.91): dos polilíneas (celeste = SIPA total, azul oscuro = sin moratoria), 15 puntos dic-2009..dic-2023.
      Gráfico 3.1 (p.65): áreas apiladas (azul oscuro = No moratoria, celeste encima = total), 15 puntos.
    Eje y: ajuste lineal sobre las líneas de grilla (los rótulos 0 %,10 %…70 % / 0…6 M). Devuelve (df_rho, df_ben, diagnostico)."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    # --- p.91
    dr = doc[pag_rho - 1].get_drawings()
    grid = [d for d in dr if d["type"] == "s" and abs(d["rect"].height) < 1e-6 and d["rect"].width > 400]
    grid = sorted(grid, key=lambda d: -d["rect"].y0)           # de abajo hacia arriba: eje 0 %, 10 %, ... 70 %
    ys = [d["rect"].y0 for d in grid]
    assert len(ys) == 8, f"se esperaban 8 líneas horizontales (0-70 %), hay {len(ys)}"
    A = np.polyfit(ys, np.arange(8) / 10.0, 1)
    pol = [d for d in dr if d["type"] == "s" and len(d["items"]) == 14 and d["rect"].height > 5]
    pol = sorted(pol, key=lambda d: -d["rect"].y0)             # celeste (más baja) primero
    assert len(pol) == 2
    sipa = [float(np.polyval(A, y)) for _, y in _puntos_polilinea(pol[0])]
    sm = [float(np.polyval(A, y)) for _, y in _puntos_polilinea(pol[1])]
    # --- p.65
    dr2 = doc[pag_ben - 1].get_drawings()
    g2 = sorted([d for d in dr2 if d["type"] == "s" and abs(d["rect"].height) < 1e-6 and 300 < d["rect"].width < 450 and d["rect"].y0 < 600], key=lambda d: -d["rect"].y0)
    ys2 = [d["rect"].y0 for d in g2]
    assert len(ys2) == 7, f"se esperaban 7 líneas (0-6 M), hay {len(ys2)}"
    B = np.polyfit(ys2, np.arange(7) * 1e6, 1)
    areas = [d for d in dr2 if d["type"] == "f" and len(d["items"]) == 30]
    tot_pts = _puntos_polilinea(min(areas, key=lambda d: d["rect"].y0))
    nm_pts = _puntos_polilinea(max(areas, key=lambda d: d["rect"].y0))
    nm = [float(np.polyval(B, y)) for _, y in nm_pts]
    tot = [float(np.polyval(B, y)) for _, y in tot_pts]
    df_rho = pd.DataFrame(dict(anio=ANIOS, rho_dig=sipa, rho_sm_dig=sm))
    df_ben = pd.DataFrame(dict(anio=ANIOS, benef_no_moratoria_dig=nm, benef_total_dig=tot))
    df_ben["benef_moratoria_dig"] = df_ben.benef_total_dig - df_ben.benef_no_moratoria_dig
    diag = dict(ajuste_eje_rho_max_err=float(np.abs(np.polyval(A, ys) - np.arange(8) / 10).max()),
                ajuste_eje_ben_max_err=float(np.abs(np.polyval(B, ys2) - np.arange(7) * 1e6).max()),
                error_extremos=_error_extremos(df_rho, df_ben))
    return df_rho, df_ben, diag


def _error_extremos(df_rho, df_ben):
    """Compara lo digitalizado con las etiquetas publicadas (en puntos porcentuales / personas)."""
    r = df_rho.set_index("anio"); b = df_ben.set_index("anio")
    out = []
    for a in (2009, 2023):
        out.append(dict(anio=a, serie="ρ SIPA (pp)", digitalizado=100 * r.loc[a, "rho_dig"], etiqueta=100 * ETIQ_RHO[a]))
        out.append(dict(anio=a, serie="ρ sin moratoria (pp)", digitalizado=100 * r.loc[a, "rho_sm_dig"], etiqueta=100 * ETIQ_RHO_SM[a]))
        out.append(dict(anio=a, serie="benef. no moratoria", digitalizado=b.loc[a, "benef_no_moratoria_dig"], etiqueta=ETIQ_BENEF[a]["nm"]))
        out.append(dict(anio=a, serie="benef. total", digitalizado=b.loc[a, "benef_total_dig"], etiqueta=ETIQ_BENEF[a]["tot"]))
    e = pd.DataFrame(out); e["error"] = e.digitalizado - e.etiqueta
    e["error_rel_%"] = 100 * e.error / e.etiqueta
    return e


# ================================================================== 3) SERIE DE ρ
def _leer_csv_candidato(nombre, rutas=None):
    for r in (rutas or RUTAS_PROCESADOS):
        p = os.path.join(r, nombre)
        if os.path.exists(p):
            return pd.read_csv(p)
    try:
        return pd.read_csv(URL_RAW + nombre)
    except Exception:
        return None


def serie_rho_digitalizada(pdf=None, rutas=None, usar_csv=True):
    """Serie anual 2009-2023 de ρ. Orden de preferencia: (a) digitalizar el PDF si `pdf` existe; (b) CSV anses_rho_tau_anual.csv
    (si usar_csv); (c) valores embebidos (resultado de (a), misma versión). En todos los casos los extremos 2009/2023 son la ETIQUETA
    publicada y los intermedios son aproximados. Columnas: anio, rho, rho_sin_moratoria, tipo_dato, fuente, nota."""
    if pdf and os.path.exists(pdf):
        dr, _, _ = digitalizar_anuario(pdf)
        rho, sm = dr.rho_dig.values.copy(), dr.rho_sm_dig.values.copy()
    elif usar_csv and (c := _leer_csv_candidato("anses_rho_tau_anual.csv", rutas)) is not None and {"anio", "rho"} <= set(c.columns):
        c = c[c.anio.between(2009, 2023)]
        return c[[x for x in ("anio", "rho", "rho_sin_moratoria", "tipo_dato", "fuente", "nota") if x in c.columns]].reset_index(drop=True)
    else:
        rho, sm = np.array(_RHO_DIG), np.array(_RHO_SM_DIG)
    tipo, nota = [], []
    for k, a in enumerate(ANIOS):
        if a in ETIQ_RHO:
            rho[k], sm[k] = ETIQ_RHO[a], ETIQ_RHO_SM[a]
            tipo.append(ETIQ_EXT); nota.append(f"valor rotulado en el Gráfico 4.3 / texto p.91 (dic-{a})")
        else:
            tipo.append(ETIQ_DIG); nota.append("lectura de los trazos vectoriales del Gráfico 4.3 (p.91); error típico de los extremos < 0,1 pp")
    return pd.DataFrame(dict(anio=ANIOS, rho=np.round(rho, 4), rho_sin_moratoria=np.round(sm, 4), tipo_dato=tipo,
                             fuente=f"{FUENTE_ANUARIO}, Gráfico 4.3, p.91 (haber medio / salario imponible medio)", nota=nota))


def serie_beneficiarios_digitalizada():
    """Beneficiarios SIPA con/sin moratoria, Gráfico 3.1 (p.65). Extremos = etiquetas; intermedios digitalizados (aprox.)."""
    nm, tot = np.array(_BEN_NM_DIG, float), np.array(_BEN_TOT_DIG, float)
    tipo = []
    for k, a in enumerate(ANIOS):
        if a in ETIQ_BENEF:
            nm[k], tot[k] = ETIQ_BENEF[a]["nm"], ETIQ_BENEF[a]["tot"]; tipo.append(ETIQ_EXT)
        else:
            tipo.append(ETIQ_DIG)
    df = pd.DataFrame(dict(anio=ANIOS, benef_no_moratoria=nm.round(0), benef_moratoria=(tot - nm).round(0), benef_total=tot.round(0), tipo_dato=tipo,
                           fuente=f"{FUENTE_ANUARIO}, Gráfico 3.1, p.65"))
    df["share_moratoria"] = df.benef_moratoria / df.benef_total
    return df


# ================================================================== 4) SERIE DE τ
def serie_tau(escenario="base", anios=None, valor=None):
    """τ por año. NO hay historia oficial verificada: τ es CONSTANTE por SUPUESTO.
    escenario: 'base' (11 % + 10,77 % = 21,77 %), 'inc_b' (11 % + 12,35 % = 23,35 %), 'sector_publico' (11 % + 16 % = 27 %) o `valor` numérico."""
    anios = list(anios) if anios is not None else ANIOS
    if valor is not None:
        t, nom = float(valor), f"valor={valor}"
    else:
        t, nom = TAU_ESCENARIOS[escenario], escenario
    return pd.DataFrame(dict(anio=anios, tau=t, tipo_dato="supuesto (constante)",
                             fuente=f"{FUENTE_ANUARIO}, p.39 (alícuotas vigentes; sin historia anual verificada)",
                             nota=f"escenario {nom}: τ = {t:.4f} constante en todos los años; NO es una serie histórica"))


# ================================================================== 5) ASIGNACIÓN POR COHORTE
def _extrapolar(serie, anio, modo, k=5, constante=None):
    """Valor de la serie en `anio`. Devuelve (valor, tipo) con tipo 'dato' o 'extrapolado:<regla>'."""
    s = serie.dropna()
    if anio in s.index:
        return float(s.loc[anio]), "dato"
    if modo == "ultimo_valor":
        # fuera del rango se usa el valor del extremo más cercano (último año disponible si es posterior; primero si es anterior)
        v = s.iloc[-1] if anio > s.index.max() else s.iloc[0]
    elif modo == "media_ultimos_k":
        v = s.iloc[-k:].mean() if anio > s.index.max() else s.iloc[:k].mean()
    elif modo == "constante":
        if constante is None:
            raise ValueError("extrapolacion='constante' requiere pasar `constante=` (p.ej. RHO)")
        v = float(constante)
    else:
        raise ValueError("extrapolacion debe ser 'ultimo_valor', 'media_ultimos_k' o 'constante'")
    return float(v), f"extrapolado:{modo}"


def asignar_rho_tau_por_cohorte(d, serie_rho, serie_tau_df, edad_retiro=65, extrapolacion="ultimo_valor", k=5,
                                constante_rho=None, constante_tau=None, col_rho="rho", col_tau="tau"):
    """Asigna ρ y τ a cada cohorte según el año en que cumple `edad_retiro`: anio = cohorte + edad_retiro.
    Años sin dato (antes de 2009 o después de 2023) -> regla de `extrapolacion` (EXPLÍCITA, rotulada como supuesto):
      'ultimo_valor' (último año disponible), 'media_ultimos_k' (media de los k últimos años), 'constante' (usa constante_rho / constante_tau).
    NO se usa la media global como relleno silencioso. Devuelve DataFrame: cohorte, anio_ret, rho_v, tau_v, tipo_rho, tipo_tau."""
    sr = serie_rho.set_index("anio")[col_rho]
    st = serie_tau_df.set_index("anio")[col_tau]
    filas = []
    for c in d["cohorte"].values:
        a = int(c) + int(edad_retiro)
        rv, tr = _extrapolar(sr, a, extrapolacion, k, constante_rho)
        modo_t = extrapolacion if (extrapolacion != "constante" or constante_tau is not None) else "ultimo_valor"
        tv, tt = _extrapolar(st, a, modo_t, k, constante_tau)
        filas.append(dict(cohorte=int(c), anio_ret=a, rho_v=rv, tau_v=tv, tipo_rho=tr, tipo_tau=("supuesto" if tt == "dato" else tt)))
    out = pd.DataFrame(filas)
    out.attrs["extrapolacion"] = extrapolacion
    return out


# ================================================================== 6) TBP_C / TBP_A DINÁMICOS
def _vec(x, cohortes, nombre):
    if np.isscalar(x):
        return np.full(len(cohortes), float(x))
    if isinstance(x, pd.Series):
        v = x.reindex(cohortes).values.astype(float)
    elif isinstance(x, pd.DataFrame):
        raise ValueError(f"{nombre} debe ser escalar, Serie indexada por cohorte o vector")
    else:
        v = np.asarray(x, float)
    if len(v) != len(cohortes):
        raise ValueError(f"{nombre}: largo {len(v)} != {len(cohortes)} cohortes")
    return v


def tbp_c_dinamico(d, rho_v, tau_v, abar=None):
    """TBP_C = N_t·S65·Ā·τ/(J·ρ) y TBP_A = TBP_C/E65 con ρ_v y τ_v POR COHORTE (escalar, Serie por cohorte, vector o DataFrame de
    asignar_rho_tau_por_cohorte). abar=None -> dos niveles de referencia: 14,2 (ANSES, obs) y 30 (requisito legal); si se pasa (escalar o por
    cohorte, p.ej. salida de tbp_eph) -> columnas *_din. Los niveles dependen de Ā. Devuelve DataFrame con cohorte + columnas."""
    co = d["cohorte"].values
    if isinstance(rho_v, pd.DataFrame): rho_v = rho_v.set_index("cohorte")["rho_v"]
    if isinstance(tau_v, pd.DataFrame): tau_v = tau_v.set_index("cohorte")["tau_v"]
    r, t = _vec(rho_v, co, "rho_v"), _vec(tau_v, co, "tau_v")
    if np.any(~np.isfinite(r)) or np.any(r <= 0):
        raise ValueError("rho_v debe ser positivo y finito")
    base = d["N_t"].values * d["S65"].values / d["J"].values
    out = pd.DataFrame(dict(cohorte=co, rho_v=r, tau_v=t))
    niveles = {"obs": 14.2, "legal": 30.0} if abar is None else {"Abar": abar}
    for nom, A in niveles.items():
        Av = _vec(A, co, "abar")
        suf = nom if abar is None else "Abar"
        out[f"TBP_C_{suf}_din"] = base * Av * t / r
        out[f"TBP_A_{suf}_din"] = out[f"TBP_C_{suf}_din"].values / d["E65"].values
    return out


# ================================================================== 7) DATOS SINTÉTICOS Y AUTOTEST
def banner(txt="DATOS SINTÉTICOS — no son Argentina"):
    line = "#" * 78
    print("\n".join([line, "##" + txt.center(74) + "##", line]))


def autotest(verbose=True):
    """Prueba con datos SINTÉTICOS (inventados, solo para verificar código). NUNCA usar estos números en salidas reales."""
    if verbose: banner()
    co = np.arange(1950, 2036)
    d = pd.DataFrame(dict(cohorte=co, N_t=500000.0 - 1000 * (co - 1950), S65=0.8, J=5e6 + 5e4 * (co - 1950), E65=18.0))
    sr = pd.DataFrame(dict(anio=range(2009, 2024), rho=np.linspace(0.30, 0.50, 15)))
    st = serie_tau(valor=0.25, anios=range(2009, 2024))
    for modo, esperado in (("ultimo_valor", 0.50), ("media_ultimos_k", np.linspace(0.30, 0.50, 15)[-5:].mean()), ("constante", 0.40)):
        a = asignar_rho_tau_por_cohorte(d, sr, st, extrapolacion=modo, k=5, constante_rho=0.40, constante_tau=0.25)
        fila = a[a.cohorte == 2000].iloc[0]                 # anio_ret 2065 -> fuera de la serie
        assert abs(fila.rho_v - esperado) < 1e-12 and fila.tipo_rho == f"extrapolado:{modo}", (modo, fila)
        f2 = a[a.cohorte == 1950].iloc[0]                   # 2015 -> dato
        assert f2.tipo_rho == "dato" and abs(f2.rho_v - sr.set_index("anio").loc[2015, "rho"]) < 1e-12
    # antes de 2009 (cohorte 1940 -> 2005) y regla primera/primeros k
    d2 = pd.concat([pd.DataFrame(dict(cohorte=[1940], N_t=1.0, S65=1.0, J=1.0, E65=1.0)), d], ignore_index=True)
    a2 = asignar_rho_tau_por_cohorte(d2, sr, st, extrapolacion="ultimo_valor")
    assert abs(a2.iloc[0].rho_v - 0.30) < 1e-12 and a2.iloc[0].tipo_rho.startswith("extrapolado")
    # TBP con ρ,τ constantes == fórmula directa
    r = tbp_c_dinamico(d, 0.4, 0.2, abar=None)
    ref = d.N_t * d.S65 * 30 * 0.2 / (d.J * 0.4)
    assert np.allclose(r.TBP_C_legal_din, ref) and np.allclose(r.TBP_A_legal_din, ref / d.E65)
    # ρ_v mayor => TBP menor; Ā por cohorte
    r_hi = tbp_c_dinamico(d, 0.8, 0.2, abar=20.0)
    assert (r_hi.TBP_C_Abar_din.values < tbp_c_dinamico(d, 0.4, 0.2, abar=20.0).TBP_C_Abar_din.values).all()
    r_v = tbp_c_dinamico(d, pd.Series(0.4, index=co), 0.2, abar=pd.Series(np.linspace(10, 30, len(co)), index=co))
    assert np.isfinite(r_v.TBP_C_Abar_din).all()
    # escenarios de τ
    assert abs(serie_tau("base").tau.iloc[0] - 0.2177) < 1e-12 and abs(serie_tau("sector_publico").tau.iloc[0] - 0.27) < 1e-12
    # extrapolación 'constante' sin constante -> error explícito
    try:
        asignar_rho_tau_por_cohorte(d, sr, st, extrapolacion="constante"); raise AssertionError("debía fallar")
    except ValueError:
        pass
    # lector de Excel: sin archivo avisa; con un xlsx sintético encuentra palabras clave
    assert cargar_serie_anses(ruta="/ruta/que/no/existe.xlsx")["encontrado"] is False
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "sintetico.xlsx")
    pd.DataFrame([["Tasa de sustitución (SINTÉTICO)", 1, 2], ["Beneficiarios con moratoria", 3, 4]]).to_excel(p, header=False, index=False, sheet_name="Hoja_x")
    res = cargar_serie_anses(ruta=p)
    assert res["encontrado"] and len(res["hallazgos"]) == 3   # 1 por palabra clave presente (la 2ª celda tiene 2)
    if verbose:
        print("autotest OK (datos sintéticos: no son Argentina)")
    return True


if __name__ == "__main__":
    autotest()
