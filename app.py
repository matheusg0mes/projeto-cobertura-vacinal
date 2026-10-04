
import io
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st
from sqlalchemy import create_engine

# ----------------------------------------------------------------------------
# Configuração geral
# ----------------------------------------------------------------------------
BASE = Path(__file__).parent
CSV = BASE / "dados" / "simulacao_cobertura_vacinal_brasil.csv"
DB = BASE / "database" / "vacinacao.db"

COLUNAS = ["ano", "mes", "data", "regiao", "uf", "municipio", "vacina", "doses_aplicadas",
           "publico_alvo", "cobertura_percentual", "meta_percentual", "populacao_alvo",
           "campanhas", "nivel_alerta"]
TEXTO = ["regiao", "uf", "municipio", "vacina", "publico_alvo", "nivel_alerta"]
ORDEM_ALERTA = ["Adequado", "Atenção", "Crítico"]
CORES_ALERTA = {"Adequado": "#2e8b57", "Atenção": "#e6a23c", "Crítico": "#c0392b"}
MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
         7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}

# Coordenadas aproximadas das capitais (usadas no mapa)
COORD = {
    "AM": (-3.12, -60.02), "PA": (-1.46, -48.50), "RO": (-8.76, -63.90), "TO": (-10.18, -48.33),
    "BA": (-12.97, -38.51), "PE": (-8.05, -34.88), "CE": (-3.73, -38.52), "MA": (-2.53, -44.30),
    "PB": (-7.12, -34.86), "DF": (-15.79, -47.88), "GO": (-16.68, -49.25), "MT": (-15.60, -56.10),
    "MS": (-20.47, -54.62), "SP": (-23.55, -46.63), "RJ": (-22.91, -43.17), "MG": (-19.92, -43.94),
    "ES": (-20.32, -40.34), "PR": (-25.43, -49.27), "SC": (-27.60, -48.55), "RS": (-30.03, -51.23),
}

sns.set_theme(style="whitegrid")
st.set_page_config(page_title="Cobertura Vacinal no Brasil", page_icon="💉", layout="wide")


# ----------------------------------------------------------------------------
# Tratamento dos dados
# ----------------------------------------------------------------------------
def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa a base e cria os atributos derivados."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes no arquivo: {sorted(faltando)}")

    for c in TEXTO:                                   # espaços sobrando
        df[c] = df[c].astype(str).str.strip()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    df = df.dropna(subset=COLUNAS).drop_duplicates()   # nulos e duplicatas
    df = df[df["cobertura_percentual"].between(0, 100)]  # valores impossíveis
    df = df[df["populacao_alvo"] > 0]

    # Engenharia de atributos
    df["gap_meta"] = df["cobertura_percentual"] - df["meta_percentual"]
    df["abaixo_meta"] = df["gap_meta"] < 0
    df["trimestre"] = df["data"].dt.quarter
    return df.reset_index(drop=True)


def construir_banco() -> None:
    """CSV -> limpeza -> SQLite com duas tabelas (dim_uf e cobertura)."""
    df = preparar(pd.read_csv(CSV, encoding="utf-8-sig"))
    DB.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{DB}")

    dim = df[["uf", "regiao"]].drop_duplicates().copy()
    dim["lat"] = dim["uf"].map(lambda u: COORD.get(u, (np.nan, np.nan))[0])
    dim["lon"] = dim["uf"].map(lambda u: COORD.get(u, (np.nan, np.nan))[1])
    dim.to_sql("dim_uf", engine, if_exists="replace", index=False)

    fato = df.drop(columns=["regiao"]).copy()
    fato["data"] = fato["data"].dt.strftime("%Y-%m-%d")
    fato.to_sql("cobertura", engine, if_exists="replace", index=False)


@st.cache_data(show_spinner="Consultando o banco SQLite...")
def carregar_banco() -> pd.DataFrame:
    if not DB.exists():
        construir_banco()
    engine = create_engine(f"sqlite:///{DB}")
    sql = """
        SELECT c.*, d.regiao, d.lat, d.lon
        FROM cobertura c
        JOIN dim_uf d ON c.uf = d.uf
    """
    df = pd.read_sql(sql, engine, parse_dates=["data"])
    df["abaixo_meta"] = df["abaixo_meta"].astype(bool)
    return df


@st.cache_data
def ler_upload(arquivo: bytes) -> pd.DataFrame:
    df = preparar(pd.read_csv(io.BytesIO(arquivo), encoding="utf-8-sig"))
    df["lat"] = df["uf"].map(lambda u: COORD.get(u, (np.nan, np.nan))[0])
    df["lon"] = df["uf"].map(lambda u: COORD.get(u, (np.nan, np.nan))[1])
    return df


# ----------------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------------
def br(n: float, casas: int = 0) -> str:
    """Formata número no padrão brasileiro (1.234,5)."""
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pt(texto: str) -> str:
    """Troca ponto decimal por vírgula nos textos (84.0 -> 84,0)."""
    return re.sub(r"(?<=\d)\.(?=\d)", ",", texto)


def mostrar(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def forca_corr(r: float) -> str:
    r = abs(r)
    if np.isnan(r):
        return "indefinida"
    if r < 0.1:
        return "desprezível"
    if r < 0.3:
        return "fraca"
    if r < 0.5:
        return "moderada"
    return "forte"


# ----------------------------------------------------------------------------
# Cabeçalho
# ----------------------------------------------------------------------------
st.title("💉 Cobertura Vacinal no Brasil (2015–2024)")
st.markdown(
    """ Projeto G1- LINGUAGEM DE PROGRAMAÇÃO, PROFESSOR Alexandre Neves Louzada, ALUNO MATHEUS GOMES DA COSTA
     
**O problema.** A queda da cobertura vacinal aumenta o risco de surtos de doenças já controladas.
Este painel monitora a cobertura de seis vacinas em 20 estados e 37 municípios, compara cada
registro com a meta de imunização (80% ou 95%) e aponta onde a atenção da saúde pública deve se concentrar.

> ⚠️ A base é **simulada** (fornecida para fins didáticos). Os resultados ilustram o método de análise
> e não representam a situação real do país.
"""
)

# ----------------------------------------------------------------------------
# Dados + filtros (barra lateral)
# ----------------------------------------------------------------------------
sb = st.sidebar
sb.header("Filtros")

upload = sb.file_uploader("Usar outro CSV (mesmas colunas)", type="csv")
try:
    df = ler_upload(upload.getvalue()) if upload else carregar_banco()
except Exception as erro:  # arquivo inválido
    sb.error(f"Não foi possível usar o arquivo: {erro}")
    df = carregar_banco()
sb.caption("Fonte: " + ("arquivo enviado" if upload else "SQLite (database/vacinacao.db)"))


def multi(rotulo, opcoes, chave, fmt=str):
    return sb.multiselect(rotulo, opcoes, default=opcoes, key=chave, format_func=fmt)


anos = multi("Ano", sorted(df["ano"].unique()), "ano")
meses = multi("Mês", sorted(df["mes"].unique()), "mes", lambda m: MESES.get(m, m))
regioes = multi("Região", sorted(df["regiao"].unique()), "regiao")
ufs_disp = sorted(df[df["regiao"].isin(regioes)]["uf"].unique())
ufs = multi("Estado", ufs_disp, "uf_" + "".join(sorted(regioes)))   # lista depende da região
vacinas = multi("Vacina", sorted(df["vacina"].unique()), "vacina")
publicos = multi("Público-alvo", sorted(df["publico_alvo"].unique()), "publico")
alertas = multi("Nível de alerta", [a for a in ORDEM_ALERTA if a in df["nivel_alerta"].unique()], "alerta")

f = df[
    df["ano"].isin(anos) & df["mes"].isin(meses) & df["regiao"].isin(regioes) & df["uf"].isin(ufs)
    & df["vacina"].isin(vacinas) & df["publico_alvo"].isin(publicos) & df["nivel_alerta"].isin(alertas)
]
sb.metric("Registros após filtros", br(len(f)), f"de {br(len(df))}", delta_color="off")

if f.empty:
    st.warning("Nenhum registro para essa combinação de filtros. Amplie a seleção na barra lateral.")
    st.stop()

# ----------------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------------
por_vacina = f.groupby("vacina")["cobertura_percentual"].mean().sort_values()
por_uf = f.groupby("uf")["cobertura_percentual"].mean().sort_values()
por_regiao = f.groupby("regiao")["cobertura_percentual"].mean().sort_values()
cob_media = f["cobertura_percentual"].mean()
cob_pond = f["doses_aplicadas"].sum() / f["populacao_alvo"].sum() * 100
pct_abaixo = f["abaixo_meta"].mean() * 100
pct_critico = (f["nivel_alerta"] == "Crítico").mean() * 100

st.subheader("Indicadores principais")
k = st.columns(4)
k[0].metric("Cobertura vacinal média", f"{cob_media:.1f}%".replace(".", ","),
            f"{cob_media - f['meta_percentual'].mean():+.1f} p.p. vs meta média".replace(".", ","),
            help="Média simples dos registros filtrados. Delta = diferença para a meta média.")
k[1].metric("Registros abaixo da meta", f"{pct_abaixo:.1f}%".replace(".", ","),
            help="Percentual de registros com cobertura menor que a meta.")
k[2].metric("Total de doses aplicadas", br(f["doses_aplicadas"].sum()))
k[3].metric("Registros em nível crítico", f"{pct_critico:.1f}%".replace(".", ","),
            help="Cobertura pelo menos 15 p.p. abaixo da meta.")
k = st.columns(3)
k[0].metric("Vacina com menor cobertura", por_vacina.index[0],
            f"{por_vacina.iloc[0]:.1f}%".replace(".", ","), delta_color="off")
k[1].metric("Estado com menor cobertura", por_uf.index[0],
            f"{por_uf.iloc[0]:.1f}%".replace(".", ","), delta_color="off")
k[2].metric("Região mais vulnerável", por_regiao.index[0],
            f"{por_regiao.iloc[0]:.1f}%".replace(".", ","), delta_color="off")
st.caption(f"Cobertura ponderada pela população-alvo (doses ÷ população): {cob_pond:.1f}%".replace(".", ","))

# ----------------------------------------------------------------------------
# Seções (abas)
# ----------------------------------------------------------------------------
abas = st.tabs(["📈 Evolução temporal", "🗺️ Regiões e estados", "💊 Vacinas e público",
                "🎯 Metas e alertas", "🔗 Correlação", "📋 Tabela dinâmica"])

# --- 1. Temporal --------------------------------------------------------------
with abas[0]:
    st.markdown("#### Cobertura mensal e média móvel de 12 meses")
    serie = f.groupby("data", as_index=False)["cobertura_percentual"].mean()
    serie["Média móvel (12 meses)"] = serie["cobertura_percentual"].rolling(12, min_periods=6).mean()
    serie = serie.rename(columns={"cobertura_percentual": "Média mensal"})
    fig = px.line(serie, x="data", y=["Média mensal", "Média móvel (12 meses)"],
                  labels={"data": "Data", "value": "Cobertura (%)", "variable": ""})
    fig.add_hline(y=f["meta_percentual"].mean(), line_dash="dash", line_color="gray",
                  annotation_text="meta média")
    fig.update_layout(legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=10))
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Cobertura anual por região")
        anual_reg = f.groupby(["ano", "regiao"], as_index=False)["cobertura_percentual"].mean()
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(data=anual_reg, x="ano", y="cobertura_percentual", hue="regiao", marker="o", ax=ax)
        ax.set(xlabel="Ano", ylabel="Cobertura média (%)")
        ax.legend(title="", fontsize=8, ncol=2)
        mostrar(fig)
    with c2:
        st.markdown("#### Variação anual (p.p.)")
        anual = f.groupby("ano")["cobertura_percentual"].mean()
        var = anual.diff().dropna()
        fig, ax = plt.subplots(figsize=(7, 4))
        if len(var):
            ax.bar(var.index.astype(str), var.values, color=np.where(var < 0, "#c0392b", "#2e8b57"))
        ax.axhline(0, color="black", lw=.8)
        ax.set(xlabel="Ano", ylabel="Variação vs ano anterior (p.p.)")
        mostrar(fig)

    st.markdown("#### Heatmap mensal (ano × mês)")
    heat = f.pivot_table(index="ano", columns="mes", values="cobertura_percentual", aggfunc="mean")
    heat = heat.rename(columns=MESES)
    fig, ax = plt.subplots(figsize=(11, 4))
    sns.heatmap(heat, annot=True, fmt=".1f", cmap="RdYlGn", cbar_kws={"label": "Cobertura (%)"},
                annot_kws={"size": 8}, ax=ax)
    ax.set(xlabel="Mês", ylabel="Ano")
    mostrar(fig)

    # Interpretação dinâmica
    txt = f"No recorte selecionado, a cobertura média anual variou entre **{anual.min():.1f}%** ({anual.idxmin()}) e **{anual.max():.1f}%** ({anual.idxmax()})."
    if len(var):
        txt += f" A maior queda de um ano para o outro foi em **{var.idxmin()}** ({var.min():+.1f} p.p.)."
    if len(anual) >= 3:
        inclinacao = np.polyfit(anual.index, anual.values, 1)[0]
        tendencia = "estável" if abs(inclinacao) < 0.3 else ("de queda" if inclinacao < 0 else "de alta")
        txt += f" A tendência linear do período é **{tendencia}** ({inclinacao:+.2f} p.p. por ano)."
    mes_pior = f.groupby("mes")["cobertura_percentual"].mean().idxmin()
    txt += f" Sazonalmente, o mês de menor média é **{MESES[mes_pior]}**."
    st.info(pt(txt))

# --- 2. Regiões e estados -----------------------------------------------------------------
with abas[1]:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### Cobertura média por estado")
        fig, ax = plt.subplots(figsize=(7, 5.5))
        ordem = por_uf.sort_values()
        sns.barplot(x=ordem.values, y=ordem.index, color="#3b7dd8", ax=ax)
        ax.axvline(cob_media, color="black", ls="--", lw=1, label="média do recorte")
        ax.set_xlim(max(0, ordem.min() - 5), min(100, ordem.max() + 3))
        ax.set(xlabel="Cobertura média (%)", ylabel="")
        ax.legend()
        mostrar(fig)
    with c2:
        st.markdown("#### Cobertura média por região")
        fig, ax = plt.subplots(figsize=(5, 5.5))
        r = por_regiao.sort_values()
        sns.barplot(x=r.values, y=r.index, color="#2a9d8f", ax=ax)
        ax.set_xlim(max(0, r.min() - 5), min(100, r.max() + 3))
        ax.set(xlabel="Cobertura média (%)", ylabel="")
        mostrar(fig)

    st.markdown("#### Mapa interativo (capitais como referência)")
    mapa = (f.dropna(subset=["lat", "lon"])
             .groupby(["uf", "regiao", "lat", "lon"], as_index=False)
             .agg(cobertura=("cobertura_percentual", "mean"), doses=("doses_aplicadas", "sum")))
    if mapa.empty:
        st.caption("Sem coordenadas disponíveis para as UFs do recorte.")
    else:
        fig = px.scatter_geo(mapa, lat="lat", lon="lon", color="cobertura", size="doses",
                             hover_name="uf", hover_data={"regiao": True, "lat": False, "lon": False,
                                                          "cobertura": ":.1f", "doses": ":,"},
                             color_continuous_scale="RdYlGn", size_max=35, scope="south america")
        fig.update_geos(lonaxis_range=[-75, -30], lataxis_range=[-35, 6], showcountries=True)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=480,
                          coloraxis_colorbar=dict(title="Cobertura (%)"))
        st.plotly_chart(fig, width="stretch")

    dif = por_uf.max() - por_uf.min()
    st.info(pt(f"**{por_uf.index[0]}** tem a menor cobertura média ({por_uf.iloc[0]:.1f}%) e **{por_uf.index[-1]}** a maior "
            f"({por_uf.iloc[-1]:.1f}%): diferença de {dif:.1f} p.p. entre estados. Entre regiões, "
            f"**{por_regiao.index[0]}** é a mais vulnerável ({por_regiao.iloc[0]:.1f}%) e **{por_regiao.index[-1]}** a melhor "
            f"({por_regiao.iloc[-1]:.1f}%). Diferenças pequenas indicam um problema distribuído, e não concentrado em uma região."))

# --- 3. Vacinas e público ------------------------------------------------------------------
with abas[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Ranking de vacinas (cobertura média)")
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(x=por_vacina.values, y=por_vacina.index, color="#8e6bbf", ax=ax)
        ax.set_xlim(max(0, por_vacina.min() - 5), min(100, por_vacina.max() + 3))
        ax.set(xlabel="Cobertura média (%)", ylabel="")
        mostrar(fig)
    with c2:
        st.markdown("#### Distribuição da cobertura por vacina")
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.boxplot(data=f, y="vacina", x="cobertura_percentual", order=por_vacina.index,
                    color="#cfc1e6", ax=ax)
        ax.set(xlabel="Cobertura (%)", ylabel="")
        mostrar(fig)

    st.markdown("#### Cobertura média: vacina × público-alvo")
    cruz = f.pivot_table(index="vacina", columns="publico_alvo", values="cobertura_percentual", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    sns.heatmap(cruz, annot=True, fmt=".1f", cmap="RdYlGn", cbar_kws={"label": "%"}, ax=ax)
    ax.set(xlabel="", ylabel="")
    mostrar(fig)

    tab_vac = (f.groupby("vacina")
                .agg(cobertura_media=("cobertura_percentual", "mean"),
                     pct_abaixo_meta=("abaixo_meta", lambda s: s.mean() * 100),
                     doses=("doses_aplicadas", "sum"))
                .sort_values("cobertura_media").round(2))
    st.dataframe(tab_vac, width="stretch")
    pior_pub = f.groupby("publico_alvo")["cobertura_percentual"].mean().sort_values()
    st.info(pt(f"**{por_vacina.index[0]}** é a vacina com menor cobertura média ({por_vacina.iloc[0]:.1f}%); "
            f"**{por_vacina.index[-1]}** tem a maior ({por_vacina.iloc[-1]:.1f}%). "
            f"Entre os públicos-alvo, **{pior_pub.index[0]}** apresenta a menor cobertura ({pior_pub.iloc[0]:.1f}%). "
            f"A vacina com maior proporção de registros abaixo da meta é **{tab_vac['pct_abaixo_meta'].idxmax()}** "
            f"({tab_vac['pct_abaixo_meta'].max():.1f}%)."))

# --- 4. Metas e alertas -----------------------------------------------------------------------
with abas[3]:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Dispersão: meta × cobertura")
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.stripplot(data=f, x="meta_percentual", y="cobertura_percentual", hue="nivel_alerta",
                      hue_order=[a for a in ORDEM_ALERTA if a in f["nivel_alerta"].unique()],
                      palette=CORES_ALERTA, alpha=.45, size=3, jitter=.3, ax=ax)
        for i, m in enumerate(sorted(f["meta_percentual"].unique())):
            ax.hlines(m, i - .5, i + .5, color="black", ls="--", lw=1)
        ax.set(xlabel="Meta (%)", ylabel="Cobertura (%)")
        ax.legend(title="", fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.15), ncol=3)
        mostrar(fig)
    with c2:
        st.markdown("#### Distribuição dos níveis de alerta")
        cont = f["nivel_alerta"].value_counts().reindex(ORDEM_ALERTA).dropna()
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(cont.index, cont.values, color=[CORES_ALERTA[i] for i in cont.index])
        for i, v in enumerate(cont.values):
            ax.text(i, v, f"{v / cont.sum() * 100:.1f}%".replace(".", ","), ha="center", va="bottom")
        ax.set(xlabel="", ylabel="Registros")
        mostrar(fig)

    st.markdown("#### Composição dos níveis de alerta por estado (% dos registros)")
    comp = pd.crosstab(f["uf"], f["nivel_alerta"], normalize="index") * 100
    comp = comp.reindex(columns=[a for a in ORDEM_ALERTA if a in comp.columns])
    if "Crítico" in comp.columns:
        comp = comp.sort_values("Crítico", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 4))
    comp.plot.bar(stacked=True, color=[CORES_ALERTA[c] for c in comp.columns], ax=ax, width=.8)
    ax.set(xlabel="", ylabel="% dos registros")
    ax.legend(title="", ncol=3, loc="upper center", bbox_to_anchor=(.5, 1.12))
    plt.xticks(rotation=0)
    mostrar(fig)

    crit_uf = (comp["Crítico"] if "Crítico" in comp.columns else pd.Series(dtype=float))
    txt = (f"**{pct_abaixo:.1f}%** dos registros ficaram abaixo da meta e **{pct_critico:.1f}%** estão em nível crítico "
           f"(≥ 15 p.p. abaixo da meta). Metas de 95% são mais difíceis de atingir que as de 80%.")
    if len(crit_uf):
        txt += f" O estado com maior fatia de registros críticos é **{crit_uf.idxmax()}** ({crit_uf.max():.1f}%)."
    st.info(pt(txt))

# --- 5. Correlação -----------------------------------------------------------------------------
with abas[4]:
    cols = ["cobertura_percentual", "meta_percentual", "gap_meta", "doses_aplicadas", "populacao_alvo", "campanhas"]
    corr = f[cols].corr()
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### Matriz de correlação (Pearson)")
        fig, ax = plt.subplots(figsize=(7, 5))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, vmin=-1, vmax=1, ax=ax)
        ax.set_xticklabels([c.replace("_", "\n") for c in cols], rotation=0, fontsize=7)
        ax.set_yticklabels(cols, rotation=0, fontsize=8)
        mostrar(fig)
    with c2:
        st.markdown("#### Cobertura média por nº de campanhas")
        camp = f.groupby("campanhas")["cobertura_percentual"].mean()
        fig, ax = plt.subplots(figsize=(5, 5))
        n_camp = f.groupby("campanhas").size()
        sns.barplot(x=camp.index, y=camp.values, color="#e07a5f", ax=ax)
        for i, (qtd, n) in enumerate(zip(camp.index, n_camp.reindex(camp.index))):
            ax.text(i, camp.loc[qtd], f"n={n}", ha="center", va="bottom", fontsize=7)
        ax.set_ylim(max(0, camp.min() - 5), min(100, camp.max() + 3))
        ax.set(xlabel="Campanhas no mês", ylabel="Cobertura média (%)")
        mostrar(fig)

    r_camp = corr.loc["campanhas", "cobertura_percentual"]
    r_pop = corr.loc["populacao_alvo", "cobertura_percentual"]
    st.info(pt(f"Correlação entre campanhas e cobertura: **r = {r_camp:.2f}** ({forca_corr(r_camp)}). "
            f"Entre população-alvo e cobertura: **r = {r_pop:.2f}** ({forca_corr(r_pop)}). "
            "Correlação não implica causalidade; valores próximos de zero indicam que, nesta base, "
            "o número de campanhas não explica a cobertura (barras com poucos registros, n baixo, oscilam mais). A correlação de `gap_meta` com `cobertura_percentual` "
            "é alta por construção (gap = cobertura − meta)."))

# --- 6. Tabela dinâmica ---------------------------------------------------------------------------
with abas[5]:
    st.markdown("#### Monte sua tabela dinâmica")
    dims = ["uf", "regiao", "vacina", "publico_alvo", "ano", "mes", "nivel_alerta", "municipio"]
    c = st.columns(4)
    linhas = c[0].selectbox("Linhas", dims, index=0)
    colunas = c[1].selectbox("Colunas", ["(nenhuma)"] + dims, index=3)
    valor = c[2].selectbox("Valor", ["cobertura_percentual", "doses_aplicadas", "gap_meta", "campanhas", "populacao_alvo"])
    agg = c[3].selectbox("Agregação", ["mean", "sum", "median", "count", "min", "max"])
    if colunas == linhas:
        st.warning("Escolha dimensões diferentes para linhas e colunas.")
    else:
        piv = pd.pivot_table(f, index=linhas, columns=None if colunas == "(nenhuma)" else colunas,
                             values=valor, aggfunc=agg)
        if isinstance(piv, pd.Series):
            piv = piv.to_frame(valor)
        st.dataframe(piv.round(2).style.background_gradient(cmap="RdYlGn", axis=None), width="stretch")
    with st.expander("Ver registros detalhados (dados filtrados)"):
        det = f.drop(columns=["lat", "lon"], errors="ignore")
        st.dataframe(det, width="stretch", height=350)
        st.download_button("⬇️ Baixar dados filtrados (CSV)", det.to_csv(index=False).encode("utf-8-sig"),
                           "cobertura_filtrada.csv", "text/csv")

# ----------------------------------------------------------------------------
# Conclusão executiva
# ----------------------------------------------------------------------------
st.divider()
st.subheader("Conclusão executiva")
anual_all = f.groupby("ano")["cobertura_percentual"].mean()
if len(anual_all) >= 3:
    slope = np.polyfit(anual_all.index, anual_all.values, 1)[0]
    tend = ("sem tendência clara de queda ou alta" if abs(slope) < 0.3
            else ("com tendência de queda" if slope < 0 else "com tendência de alta"))
else:
    tend = "sem série suficiente para avaliar tendência (selecione 3 anos ou mais)"
vac_abaixo = por_vacina[por_vacina < f["meta_percentual"].mean()]
st.success(pt(f"""
- **Situação geral:** cobertura média de **{cob_media:.1f}%** para uma meta média de **{f['meta_percentual'].mean():.1f}%**; {tend}.
- **Metas:** **{pct_abaixo:.1f}%** dos registros ficam abaixo da meta e **{pct_critico:.1f}%** estão em nível crítico; {len(vac_abaixo)} de {len(por_vacina)} vacinas têm cobertura média inferior à meta média.
- **Onde priorizar:** estado **{por_uf.index[0]}**, região **{por_regiao.index[0]}** e vacina **{por_vacina.index[0]}** têm os menores índices do recorte.
- **Recomendação:** concentrar busca ativa e campanhas nos registros críticos (vacinas com meta de 95%) e acompanhar mensalmente a média móvel.
- **Ressalva:** a base é simulada e as diferenças entre estados, regiões e vacinas são pequenas ({por_uf.max() - por_uf.min():.1f} p.p. entre estados); em dados reais, convém validar com séries oficiais antes de decisões de política pública.
"""))
st.caption("Projeto acadêmico · Python, Pandas, Matplotlib, Seaborn, Streamlit, SQLAlchemy/SQLite e Plotly.")
