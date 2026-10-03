# -*- coding: utf-8 -*-
"""
tbp_mortalidad.py — Esperanza de vida restante a los 65 años POR COHORTE (E_r cohortal) para el TBP.

Proyecto TBP — Índice de Cuna Vacía (Taller de Indicadores).

QUÉ HACE
    Hoy E_r = esperanza de vida a los 65 de PERÍODO del año t+65 (ONU WPP 2024). Eso tiene dos problemas:
      (a) la cohorte 1956 cumple 65 en 2021 (COVID): E_r = 16,1 (mínimo) frente a 17,9 de la cohorte 1950;
      (b) la tabla de período congela la mortalidad de ese año y subestima la longevidad de las cohortes futuras.
    Acá se sigue a la cohorte por el calendario: el tramo de edad [a, a+n) se recorre con la probabilidad de supervivencia
    p_x del año calendario  floor(t + a + n/2)  (misma convención de punto medio que `surv65_cohorte` del notebook
    principal, que da 1−μ). E_r_cohorte(t) = años esperados de vida restantes a los 65 siguiendo esa trayectoria.

MÉTODO (grupos de 5 años + grupo abierto 100+)
    Para la cohorte t, con S(65)=1 y S(a+n) = S(a)·p_x(año del tramo):
        años vividos en el tramo = n·S(a+n) + a_x·[S(a) − S(a+n)]       (a_x de la tabla ONU, en años)
        E_r = Σ_tramos (años vividos) + S(100)·e_100+(año del tramo abierto)
    Es la misma identidad que usa la ONU para L_x y T_x en una tabla de período (L_x = n·l_{x+n} + a_x·d_x), por lo que
    con mortalidad constante en el tiempo reproduce EXACTAMENTE e_65 de período (autotest). Regla alternativa
    `regla="trapecio"` (a_x = n/2) para medir cuánto importa a_x.

SUPUESTO EXPLÍCITO (rotulado): las tablas ONU llegan a 2100. Si el recorrido de la cohorte pasa de 2100 se MANTIENE
    CONSTANTE la tabla de 2100 (sin más mejoras de mortalidad). Afecta a las últimas cohortes; ver `grupos_extrapolados`.

LÍMITES
    * Es un cálculo sobre tablas ONU proyectadas (variante media): no hay "verdad" observada para cohortes futuras.
    * La convención de punto medio asigna UN año calendario a cada grupo de 5 años: suaviza shocks de un año (COVID).
    * Argentina total/varones/mujeres; sin diferenciales por nivel socioeconómico.

Uso mínimo:
    import tbp_mortalidad as m
    T = m.cargar_tablas()                                  # busca ../datos/procesados, datos/procesados; si no, URL raw
    er = m.er_cohortal(range(1950, 2036), edad=65, sexo="Total", tablas=T)
    comp = m.comparar_con_periodo(range(1950, 2036), tablas=T)
    m.autotest()
"""
import os
import urllib.request
from dataclasses import dataclass

import numpy as np
import pandas as pd

ARCHIVO_MORT = "un_wpp2024_argentina_tabla_mortalidad_abreviada.csv"
RAW_BASE_MORT = "https://raw.githubusercontent.com/carolinamsfelipe/Tp-Indicadores/main/datos/procesados"
RUTAS_MORT = ["../datos/procesados", "datos/procesados"]
SEXOS = ("Total", "Male", "Female")
REGLAS = ("ax", "trapecio")


# ================================================================== 1) CARGA
@dataclass
class TablaSexo:
    """Tablas de período abreviadas de un sexo: matrices año × inicio de grupo de edad."""
    px: pd.DataFrame        # prob. de sobrevivir el grupo (condicional a llegar a su inicio)
    ax: pd.DataFrame        # años promedio vividos en el grupo por quienes mueren en él
    ex: pd.DataFrame        # esperanza de vida restante al inicio del grupo (período)
    starts: np.ndarray      # inicio de cada grupo (0, 1, 5, ..., 95, 100)
    spans: np.ndarray       # ancho de cada grupo (el último, abierto, es NaN)
    y0: int
    y1: int


def buscar_archivo(nombre, rutas=None, destino="."):
    """Busca `nombre` en las rutas candidatas; si no está, lo descarga de GitHub (URL raw) a `destino`."""
    for c in list(rutas or []) + RUTAS_MORT:
        p = os.path.join(c, nombre)
        if os.path.exists(p):
            return p
    os.makedirs(destino, exist_ok=True)
    p = os.path.join(destino, nombre)
    urllib.request.urlretrieve(f"{RAW_BASE_MORT}/{nombre}", p)
    return p


def _tabla_desde_df(sub):
    if "Variant" in sub.columns:
        sub = sub[sub["Variant"] == "Medium"]
    sub = sub.copy()
    sub["AgeGrpStart"] = sub["AgeGrpStart"].astype(int)
    px = sub.pivot_table(index="Time", columns="AgeGrpStart", values="px").sort_index()
    ax = sub.pivot_table(index="Time", columns="AgeGrpStart", values="ax").sort_index()
    ex = sub.pivot_table(index="Time", columns="AgeGrpStart", values="ex").sort_index()
    g = (sub[sub.Time == sub.Time.min()].sort_values("AgeGrpStart")[["AgeGrpStart", "AgeGrpSpan"]])
    starts = g["AgeGrpStart"].to_numpy(int)
    spans = np.where(g["AgeGrpSpan"].to_numpy(float) > 0, g["AgeGrpSpan"].to_numpy(float), np.nan)
    assert px.notna().all().all() and ax.notna().all().all() and ex.notna().all().all(), "tabla con huecos"
    assert np.isnan(spans[-1]) and not np.isnan(spans[:-1]).any(), "se espera un único grupo abierto, el último"
    return TablaSexo(px, ax, ex, starts, spans, int(px.index.min()), int(px.index.max()))


def cargar_tablas(rutas=None, archivo=ARCHIVO_MORT, df=None, destino="."):
    """Lee la tabla de mortalidad abreviada de la ONU y devuelve {'Total','Male','Female'} -> TablaSexo.

    `df` permite pasar una tabla ya cargada (con la misma estructura de columnas)."""
    if df is None:
        df = pd.read_csv(buscar_archivo(archivo, rutas, destino), low_memory=False)
    out = {}
    for sx in SEXOS:
        sub = df[df["Sex"] == sx]
        if len(sub):
            out[sx] = _tabla_desde_df(sub)
    if not out:
        raise ValueError("la tabla no tiene ninguna de las columnas Sex esperadas: " + str(SEXOS))
    return out


# ================================================================== 2) SUPERVIVENCIA Y E_r COHORTAL
def _anio_tramo(t, a, ancho, tab):
    """Año calendario (punto medio, igual que surv65_cohorte) con que la cohorte t recorre el tramo [a, a+ancho)."""
    y = int(np.floor(t + a + ancho / 2.0))
    if y < tab.y0:
        raise ValueError(f"cohorte {t}: el tramo {a}+ cae en {y}, antes de la primera tabla ({tab.y0})")
    return min(y, tab.y1), y > tab.y1          # (año de tabla usado, ¿extrapolado con la tabla 2100 constante?)


def _tab(tablas, sexo):
    tablas = tablas if tablas is not None else cargar_tablas()
    if sexo not in tablas:
        raise ValueError(f"sexo {sexo!r} no disponible: {list(tablas)}")
    return tablas[sexo]


def supervivencia_cohortal(cohortes, sexo="Total", tablas=None):
    """S(a): probabilidad de que la cohorte nacida en t llegue viva a la edad a (inicio de cada grupo de edad).

    Devuelve DataFrame (índice = cohorte, columnas = 0, 1, 5, ..., 95, 100). S(0)=1 y, para cada grupo cerrado,
    S(a+n) = S(a)·p_x[año calendario floor(t+a+n/2), grupo a]. Para años > 2100 se usa la tabla de 2100 (supuesto)."""
    tab = _tab(tablas, sexo)
    cohortes = [int(c) for c in cohortes]
    filas = []
    for t in cohortes:
        S = [1.0]
        for k in range(len(tab.starts) - 1):
            y, _ = _anio_tramo(t, tab.starts[k], tab.spans[k], tab)
            S.append(S[-1] * tab.px.at[y, tab.starts[k]])
        filas.append(S)
    return pd.DataFrame(filas, index=pd.Index(cohortes, name="cohorte"), columns=tab.starts)


def _k_edad(tab, edad):
    if int(edad) not in set(tab.starts.tolist()):
        raise ValueError(f"edad {edad} no es el inicio de un grupo de la tabla abreviada: {tab.starts.tolist()}")
    return int(np.where(tab.starts == int(edad))[0][0])


def _er_una(t, k0, tab, regla):
    S, total = 1.0, 0.0
    for k in range(k0, len(tab.starts) - 1):
        a, n = tab.starts[k], tab.spans[k]
        y, _ = _anio_tramo(t, a, n, tab)
        Snext = S * tab.px.at[y, a]
        axk = tab.ax.at[y, a] if regla == "ax" else n / 2.0
        total += n * Snext + axk * (S - Snext)          # n·l_{x+n} + a_x·d_x, con l normalizado a S(edad)=1
        S = Snext
    a_op = tab.starts[-1]                                # grupo abierto 100+
    y_ref, _ = _anio_tramo(t, a_op, 0.0, tab)
    e_ref = tab.ex.at[y_ref, a_op]
    y, _ = _anio_tramo(t, a_op, e_ref, tab)              # punto medio con la duración esperada del grupo abierto
    return total + S * tab.ex.at[y, a_op]


def er_cohortal(cohortes, edad=65, sexo="Total", tablas=None, regla="ax"):
    """Años esperados de vida restantes a la edad `edad` (65) para cada cohorte, siguiendo la trayectoria calendario.

    `regla`: "ax" (a_x de la tabla ONU; reproduce la tabla de período si la mortalidad es constante) o "trapecio"
    (a_x = n/2, para medir la sensibilidad). Devuelve Series indexada por cohorte."""
    if regla not in REGLAS:
        raise ValueError(f"regla debe ser una de {REGLAS}")
    tab = _tab(tablas, sexo)
    k0 = _k_edad(tab, edad)
    cohortes = [int(c) for c in cohortes]
    return pd.Series([_er_una(t, k0, tab, regla) for t in cohortes],
                     index=pd.Index(cohortes, name="cohorte"), name=f"er_cohortal_{sexo.lower()}")


def er_periodo(cohortes, edad=65, sexo="Total", tablas=None):
    """E_r de PERÍODO: e_x de la tabla del año t+edad (lo que usa hoy el notebook, columna un_e65)."""
    tab = _tab(tablas, sexo)
    _k_edad(tab, edad)
    vals = [tab.ex.at[int(t) + int(edad), edad] if tab.y0 <= int(t) + int(edad) <= tab.y1 else np.nan for t in cohortes]
    return pd.Series(vals, index=pd.Index([int(c) for c in cohortes], name="cohorte"), name=f"er_periodo_{sexo.lower()}")


def er_periodo_integrado(anios, edad=65, sexo="Total", tablas=None, regla="ax"):
    """Reconstruye e_edad de PERÍODO integrando p_x y a_x de UNA sola tabla (la del año dado), con la misma regla que
    `er_cohortal`. Sirve para probar la integración: con regla="ax" debe coincidir con la columna `ex` de la ONU
    (salvo el redondeo de la tabla); con "trapecio" muestra cuánto importa a_x."""
    tab = _tab(tablas, sexo)
    k0 = _k_edad(tab, edad)
    out = []
    for y in anios:
        y = int(y)
        S, total = 1.0, 0.0
        for k in range(k0, len(tab.starts) - 1):
            a, n = tab.starts[k], tab.spans[k]
            Sn = S * tab.px.at[y, a]
            total += n * Sn + (tab.ax.at[y, a] if regla == "ax" else n / 2.0) * (S - Sn)
            S = Sn
        out.append(total + S * tab.ex.at[y, tab.starts[-1]])
    return pd.Series(out, index=pd.Index([int(a) for a in anios], name="anio"), name=f"e{edad}_integrado_{regla}")


def grupos_extrapolados(cohortes, edad=65, sexo="Total", tablas=None):
    """Cuántos tramos del recorrido de la cohorte (desde `edad`, incluido el abierto) usan la tabla 2100 constante."""
    tab = _tab(tablas, sexo)
    k0 = _k_edad(tab, edad)
    out = []
    for t in cohortes:
        n_ext = 0
        for k in range(k0, len(tab.starts) - 1):
            n_ext += int(_anio_tramo(int(t), tab.starts[k], tab.spans[k], tab)[1])
        n_ext += int(_anio_tramo(int(t), tab.starts[-1], 2.3, tab)[1])
        out.append(n_ext)
    return pd.Series(out, index=pd.Index([int(c) for c in cohortes], name="cohorte"), name="grupos_extrapolados")


def comparar_con_periodo(cohortes, edad=65, sexos=SEXOS, tablas=None, regla="ax"):
    """Tabla ancha por cohorte: E_r de período y cohortal por sexo, diferencia y tramos extrapolados."""
    cohortes = [int(c) for c in cohortes]
    tablas = tablas if tablas is not None else cargar_tablas()
    out = pd.DataFrame({"cohorte": cohortes}).set_index("cohorte")
    for sx in sexos:
        suf = sx.lower()
        per = er_periodo(cohortes, edad, sx, tablas)
        coh = er_cohortal(cohortes, edad, sx, tablas, regla)
        out[f"er_periodo_{suf}"] = per
        out[f"er_cohortal_{suf}"] = coh
        out[f"dif_{suf}"] = coh - per
    out["grupos_extrapolados"] = grupos_extrapolados(cohortes, edad, sexos[0], tablas)
    return out.reset_index()


# ================================================================== 3) TBP CON E_r COHORTAL
def recalcular_tbp(d, er, A, tau, rho, nombre="cohortal"):
    """Recalcula TBP con un E_r alternativo. NOTA: TBP_C = N(1−μ)Āτ/(Jρ) NO contiene E_r y no cambia;
    cambian TBP_A = TBP_C/E_r y TBP_B = Āτ/(E_r ρ). `d` necesita cohorte, N_t, S65, J; `er` es Series por cohorte."""
    e = d["cohorte"].map(er).to_numpy(float)
    out = pd.DataFrame({"cohorte": d["cohorte"].to_numpy()})
    out["TBP_C"] = d["N_t"].to_numpy() * d["S65"].to_numpy() * A * tau / (d["J"].to_numpy() * rho)
    out[f"TBP_A_{nombre}"] = out["TBP_C"] / e
    out[f"TBP_B_{nombre}"] = A * tau / (e * rho)
    return out


# ================================================================== 4) AUTOTEST CON DATOS SINTÉTICOS
def _banner(txt):
    print("=" * 78 + "\n" + txt + "\n" + "=" * 78)


def tablas_sinteticas(mejora=0.0, y0=1950, y1=2100, A=4.3e-5, B=0.09, factor_sexo=(1.0, 1.3, 0.8)):
    """Tablas abreviadas SINTÉTICAS (Gompertz: h(x) = A·e^{Bx}·e^{−mejora·(año−y0)}); NO son Argentina.

    L_x se integra numéricamente (grilla fina), por lo que a_x sale exacto. Estructura idéntica a `cargar_tablas`."""
    starts = np.array([0, 1] + list(range(5, 100, 5)) + [100])
    spans = np.array([1.0, 4.0] + [5.0] * 19 + [np.nan])
    out = {}
    for sx, fs in zip(SEXOS, factor_sexo):
        años = np.arange(y0, y1 + 1)
        px = pd.DataFrame(index=años, columns=starts, dtype=float)
        ax = px.copy(); ex = px.copy()
        for y in años:
            Ay = A * fs * np.exp(-mejora * (y - y0))
            S = lambda x: np.exp(-(Ay / B) * (np.exp(B * np.asarray(x)) - 1.0))
            for k, (a, n) in enumerate(zip(starts, spans)):
                if np.isnan(n):
                    xs = np.linspace(a, 250, 12501)
                    L = np.trapezoid(S(xs), xs) / S(a)
                    ex.at[y, a] = L; ax.at[y, a] = L; px.at[y, a] = 0.0
                else:
                    xs = np.linspace(a, a + n, 401)
                    La = np.trapezoid(S(xs), xs)                                 # ∫ S dx sobre el tramo
                    p = S(a + n) / S(a)
                    px.at[y, a] = p
                    ax.at[y, a] = (La - n * S(a + n)) / (S(a) - S(a + n))        # años vividos por los que mueren en el tramo
            # e_x al inicio de cada grupo: ∫_x^∞ S / S(x)
            for a in starts:
                xs = np.linspace(a, 250, 12501)
                ex.at[y, a] = np.trapezoid(S(xs), xs) / S(a)
        out[sx] = TablaSexo(px, ax, ex, starts, spans, y0, y1)
    return out


def _er_exacto_continuo(t, edad, mejora, y0=1950, A=4.3e-5, B=0.09, fs=1.0):
    """E_r exacto (integral numérica) de la cohorte t con riesgo h(x, año) = A·e^{Bx}·e^{−mejora·(año−y0)}, año = t+x.
    Con tope de la mejora en 2100 (tabla constante después), igual que el supuesto del módulo."""
    xs = np.linspace(0, 250, 250001)
    año = t + xs
    f = np.exp(-mejora * (np.minimum(año, 2100.0) - y0))
    h = A * fs * np.exp(B * xs) * f
    H = np.concatenate([[0.0], np.cumsum((h[1:] + h[:-1]) / 2 * np.diff(xs))])
    S = np.exp(-H)
    i = int(round(edad / (xs[1] - xs[0])))
    return np.trapezoid(S[i:], xs[i:]) / S[i], S[i]


def autotest(verbose=True):
    """Pruebas con tablas SINTÉTICAS (rotuladas): (i) mortalidad constante => cohortal = período; (ii) integración vs
    valor exacto; (iii) mejora anual => cohortal ≥ período y cerca del exacto; (iv) tabla 2100 constante; (v) errores."""
    if verbose:
        _banner("AUTOTEST CON TABLAS SINTÉTICAS (Gompertz) — NO son datos de Argentina")
    cohs = list(range(1950, 2036))

    # (i) mortalidad constante en el tiempo: cohortal == período (exacto) para los 3 sexos
    T0 = tablas_sinteticas(mejora=0.0)
    for sx in SEXOS:
        c = er_cohortal(cohs, 65, sx, T0); p = er_periodo(cohs, 65, sx, T0)
        assert np.allclose(c.values, p.values, atol=1e-9), (sx, float((c - p).abs().max()))
    if verbose:
        print("OK (i)  mortalidad constante: E_r cohortal = E_r de período en las 86 cohortes y 3 sexos (tol 1e-9)")

    # (ii) la regla con a_x reproduce la integral exacta; el trapecio (a_x = n/2) se aparta un poco
    e_ex, _ = _er_exacto_continuo(1990, 65, 0.0)
    e_ax = er_cohortal([1990], 65, "Total", T0, "ax").iloc[0]
    e_tr = er_cohortal([1990], 65, "Total", T0, "trapecio").iloc[0]
    assert abs(e_ax - e_ex) < 1e-3, (e_ax, e_ex)
    assert abs(e_tr - e_ex) < 0.05, (e_tr, e_ex)
    if verbose:
        print(f"OK (ii) integración: exacto {e_ex:.4f} | regla a_x {e_ax:.4f} (error {e_ax - e_ex:+.5f}) | trapecio {e_tr:.4f} (error {e_tr - e_ex:+.5f}) años")

    # (iii) mejora anual de la mortalidad (1 %/año): cohortal > período y cercano a la integral exacta con tabla 2100 constante
    m = 0.01
    T1 = tablas_sinteticas(mejora=m)
    c = er_cohortal(cohs, 65, "Total", T1); p = er_periodo(cohs, 65, "Total", T1)
    assert (c >= p - 1e-6).all(), c[c < p - 1e-6]
    errs = []
    for t in (1950, 1970, 2000, 2020):
        ex_, _ = _er_exacto_continuo(t, 65, m)
        errs.append(c[t] - ex_)
    assert max(abs(e) for e in errs) < 0.15, errs
    S_ap = supervivencia_cohortal([1990, 2000], "Total", T1)[65]
    for t in (1990, 2000):
        _, s_ex = _er_exacto_continuo(t, 65, m)
        assert abs(S_ap[t] - s_ex) < 2e-3, (t, S_ap[t], s_ex)
    if verbose:
        print(f"OK (iii) mejora {m:.0%}/año: E_r cohortal ≥ período en todas las cohortes (mín. dif. {(c - p).min():+.3f}, máx. {(c - p).max():+.3f}); "
              f"error vs integral exacta: {', '.join(f'{e:+.3f}' for e in errs)} años; S65 cohortal ≈ exacta (<2e-3)")

    # (iv) supuesto explícito: pasado 2100 se mantiene la tabla 2100 => la cohorte 2035 (cumple 65 en 2100) = período 2100
    assert abs(c[2035] - p[2035]) < 1e-6
    g = grupos_extrapolados([1950, 2000, 2035], 65, "Total", T1)
    assert g[1950] == 0 and g[2000] == 1 and g[2035] == 8, g.to_dict()     # 2000: solo el abierto 100+ (año 2101); 2035: 7 tramos (65-99) + el abierto
    if verbose:
        print(f"OK (iv) tabla 2100 constante: cohorte 2035 cohortal = período; tramos extrapolados 1950/2000/2035 = {g.tolist()}")

    # (v) errores esperados + identidad TBP_A = TBP_C / E_r + TBP_C sin E_r
    for malo in (lambda: er_cohortal([2000], 66, "Total", T0), lambda: er_cohortal([2000], 65, "Otro", T0),
                 lambda: er_cohortal([2000], 65, "Total", T0, "foo")):
        try:
            malo(); raise AssertionError("debía fallar")
        except ValueError:
            pass
    dd = pd.DataFrame({"cohorte": [2000, 2001], "N_t": [7e5, 6.9e5], "S65": [0.88, 0.89], "J": [1.2e7, 1.2e7]})
    r1 = recalcular_tbp(dd, pd.Series({2000: 20.0, 2001: 21.0}), 30.0, 0.2177, 0.403)
    r2 = recalcular_tbp(dd, pd.Series({2000: 25.0, 2001: 26.0}), 30.0, 0.2177, 0.403)
    assert np.allclose(r1.TBP_C, r2.TBP_C)                                             # TBP_C no depende de E_r
    assert np.allclose(r1.TBP_A_cohortal, r1.TBP_C / np.array([20.0, 21.0]))
    assert np.allclose(r1.TBP_B_cohortal, 30 * 0.2177 / (np.array([20.0, 21.0]) * 0.403))
    if verbose:
        print("OK (v)  validación de entradas; TBP_C idéntico con distinto E_r; TBP_A = TBP_C/E_r; TBP_B = Āτ/(E_r ρ)")
        _banner("FIN AUTOTEST — estos números NO son Argentina")
    return True


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="E_r cohortal (esperanza de vida a los 65 por cohorte) para el TBP")
    ap.add_argument("--autotest", action="store_true", help="corre las pruebas con tablas sintéticas")
    ap.add_argument("--comparar", action="store_true", help="compara período vs cohortal con la tabla real de la ONU")
    ap.add_argument("--csv", default=None, help="si se pasa con --comparar, guarda la comparación en ese CSV")
    a = ap.parse_args()
    if a.autotest:
        autotest()
    elif a.comparar:
        comp = comparar_con_periodo(range(1950, 2036))
        print(comp.round(3).to_string(index=False))
        if a.csv:
            comp.to_csv(a.csv, index=False)
    else:
        ap.print_help()
