# Cobertura Vacinal no Brasil (2015–2024)

Projeto G1/G2 LINGUAGEM DE PROGRAMAÇÃO, PROFESSOR Alexandre Neves Louzada, ALUNO MATHEUS GOMES DA COSTA.

Analisa a cobertura de seis vacinas em 20 estados e 37 municípios, compara com as metas de imunização (80% e 95%) e apresenta os resultados em um dashboard interativo.

> A base (`dados/simulacao_cobertura_vacinal_brasil.csv`) é **simulada** e foi fornecida pelo professor. Os resultados ilustram o método e não descrevem a situação real do país.

## Links

| Entrega | Link |
|---|---|
| Repositório GitHub | https://github.com/matheusg0mes/projeto-cobertura-vacinal |
| Página (GitHub Pages) | https://matheusg0mes.github.io/projeto-cobertura-vacinal/ |
| Dashboard (Streamlit) | https://projeto-cobertura-vacinal.streamlit.app |

## Estrutura

```
projeto-cobertura-vacinal/
├── app.py                  # dashboard Streamlit
├── requirements.txt
├── README.md
├── index.html              # página de apresentação (GitHub Pages)
├── dados/                  # CSV original
├── database/               # banco SQLite (vacinacao.db), gerado a partir do CSV
├── notebooks/              # análise completa (.ipynb)
└── imagens/                # gráficos exportados pelo notebook
```

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O banco `database/vacinacao.db` é recriado automaticamente a partir do CSV se não existir.
Para refazer a análise: abra `notebooks/analise_cobertura_vacinal.ipynb` (`pip install jupyter`).

## O que o projeto entrega

**Dashboard (`app.py`)**
- Título, descrição do problema, **7 filtros** (ano, mês, região, estado, vacina, público-alvo, nível de alerta)
- **KPIs dinâmicos:** cobertura média, % abaixo da meta, doses aplicadas, % crítico, vacina/estado/região com menor cobertura
- Seções em abas: evolução temporal, regiões e estados (com mapa), vacinas e público, metas e alertas, correlação, tabela dinâmica
- **Interpretação textual** gerada a partir dos filtros e **conclusão executiva** dinâmica
- Upload de outro CSV com as mesmas colunas e download dos dados filtrados

**Funcionalidades intermediárias:** filtros múltiplos, KPIs dinâmicos, gráficos interativos (Plotly), análise temporal, tratamento avançado de dados, integração entre tabelas, upload de arquivos, dashboard em seções, visualizações comparativas, análise geográfica.

**Funcionalidades avançadas:** persistência em banco (SQLAlchemy + SQLite), modelagem relacional (`dim_uf` + `cobertura`, consulta com `JOIN`), correlação estatística (Pearson), séries temporais (média móvel de 12 meses, variação anual e tendência linear), mapa interativo (Plotly).

## Tratamento dos dados

- Leitura com `utf-8-sig` (o arquivo tem BOM), conversão de datas e remoção de espaços
- Checagem de nulos, duplicatas, faixas válidas (cobertura 0–100) e consistência (data × ano/mês, UF × região)
- Validação: cobertura = doses ÷ população-alvo e `nivel_alerta` segue a regra sobre cobertura − meta (≥ 0 Adequado; −15 a 0 Atenção; ≤ −15 Crítico)
- Atributos criados: `gap_meta`, `abaixo_meta`, `trimestre`, `faixa_cobertura`

## Principais resultados

- Cobertura média de 84,0% (meta média de 89,1%); 65,2% dos registros abaixo da meta e 21,6% em nível crítico
- Sem tendência de queda no período; maior queda anual em 2024 (−1,6 p.p.)
- O problema se concentra nas metas de 95%: 85,7% dos registros abaixo da meta (33,8% críticos), contra 33,5% (2,8% críticos) nas metas de 80%
- MS, MA e AM têm a maior proporção de registros críticos; campanhas não mostram correlação com a cobertura (r ≈ 0)

## Publicação

1. **GitHub:** `git add . && git commit -m "projeto cobertura vacinal" && git branch -M main && git remote add origin <URL> && git push -u origin main`
2. **GitHub Pages:** Settings → Pages → Branch `main`, pasta `/ (root)`
3. **Streamlit Community Cloud:** New app → escolha o repositório, branch `main`, arquivo `app.py`

Projeto desenvolvido para fins educacionais.
