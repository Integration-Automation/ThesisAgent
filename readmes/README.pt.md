# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Idiomas**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · **Português** · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentação**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Um assistente de busca de artigos orientado por palavras-chave que recupera
resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref),
IEEE Xplore, DBLP, Crossref genérico, OpenAIRE, Springer Nature, Europe PMC,
DOAJ, HAL, CORE e Google Scholar, normaliza-os num único formato de registro
e exporta o conjunto sem duplicatas como um **slide de PowerPoint no estilo
de tese**, uma **planilha do Excel** e um **arquivo BibTeX** — tudo a partir
de uma única chamada de CLI ou de uma única chamada de ferramenta MCP.
Opcionalmente, enriquece cada artigo lendo o seu PDF e produzindo um resumo
estruturado por artigo, seja em contexto (fluxo LLM-como-agente) ou via API
da Anthropic (fluxo de pipeline Python).

## Para agentes de IA que operam este projeto

**Se você é um LLM (Claude Code, Cursor, Aider, Codex CLI, …) lendo este
README para descobrir o que fazer — comece aqui.** Tudo o que está abaixo
também está fixado em [`AGENTS.md`](AGENTS.md) (espelho entre agentes) e
[`CLAUDE.md`](CLAUDE.md) (referência canônica); leia-os antes de fazer
alterações não triviais.

### O que o usuário realmente quer

O entregável padrão é **um `.pptx` rico no estilo de tese por artigo**, e
não o slide leve, apenas com o resumo, que a CLI produz por padrão. A
emissão leve é um artefato intermediário — o seu trabalho é aprimorá-la.

### Árvore de decisão

1. `ANTHROPIC_API_KEY` está definida no ambiente? → basta executar a CLI;
   ela enriquece automaticamente via API da Anthropic. Você terminou.
2. Sem chave, mas você (um LLM) está conduzindo a sessão → **você produz o
   resumo rico por conta própria**. Leia cada PDF, escreva manualmente um
   `PaperSummary` com campos de nível rico (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), coloque um
   `scripts/regen_<query>.py` e execute-o. **Não diga ao usuário para
   definir a chave de API** — você é o LLM que teria escrito o resumo.
3. Nenhum LLM no laço (CI / cron / não supervisionado) → o modo leve é
   aceitável.

### Fluxo MCP de 6 passos

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Todas as treze ferramentas MCP (incluindo `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / etc.) estão documentadas em [`docs/mcp.md`](docs/mcp.md).

### Obrigatório: verificação de URL / DOI antes de entregar

Os caminhos de URL das editoras **não podem ser adivinhados** — a AAAI usa
IDs numéricos (`v40i5.37389`), o IEEE usa um `arnumber` opaco, a ACM usa DOIs
opacos. Quando você escreve manualmente um `Paper`, **copie `url` / `doi` /
`arxiv_id` textualmente do xlsx de busca que gerou esta execução** — nunca de
memória, nunca construído a partir do título.

O xlsx é escrito em `exports/<run>/<slug>-<timestamp>.xlsx` com a coluna
7 = DOI, coluna 8 = URL. Audite o seu script de regeneração quando terminar:

```python
from openpyxl import load_workbook
from scripts.regen_<run> import ALL_PAPERS
real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
        for sh in [load_workbook("exports/<run>/<slug>-<ts>.xlsx")["Papers"]]
        for r in range(2, sh.max_row + 1)}
for p in ALL_PAPERS:
    actual = next((u for t, u in real.items() if p.title[:30] in (t or "")), None)
    if actual and not (p.url == actual
                       or p.url.split("v")[0] == actual.split("v")[0]):
        print(f"! {p.bibtex_key()} authored {p.url} vs real {actual}")
```

Duas fabricações capturadas assim em produção: volume errado da AAAI
(`v39i23.34521` vs o real `v39i22.34537`) e caminho de slug de autor inventado
(`view/fang2026` em vez de `v40i5.37389`).

### Obrigatório: remova downloads irrelevantes antes de entregar

A correspondência de busca é baseada em palavras-chave, então artigos fora do
tema vão se infiltrar: uma consulta "Claude code" retornou um artigo sobre
decodificador de Viterbi porque ambos contêm "code"; "LLM code review"
correspondeu a uma revisão de literatura sobre detecção de objetos. Depois de
ler os resumos e classificar um artigo como fora do tema para a real intenção
do usuário, limpe o diretório da execução:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Exclua `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Mantenha** o `<slug>-<timestamp>.xlsx` / `.bib` agregado — esses são o
registro honesto do que a busca retornou. Casos limítrofes recebem um resumo
rico; é melhor incluir demais do que descartar silenciosamente uma
correspondência possível.

### Exemplo resolvido

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) traz um resumo rico
escrito à mão, construído exatamente desta forma (artigo único, nível rico,
zh-tw, cada campo rico preenchido). Uma busca com vários artigos segue o mesmo
formato, com uma entrada `Paper(...summary=PaperSummary(...))` por artigo na
tupla `PaperCollection`.

### O que não fazer

- **Não** encerre uma busca com vários artigos dizendo ao usuário para
  "definir `ANTHROPIC_API_KEY` para um slide rico" — você é o LLM que
  poderia ter escrito os resumos.
- **Não** trate o `.pptx` leve por artigo como o entregável.
- **Não** pare depois que `download_pdfs` relatar N PDFs salvos — esse é o
  começo da fase de autoria rica, não o fim.
- **Não** invente números, RQs, contribuições ou limitações que não estão
  no artigo.
- **Não** fabrique URLs / DOIs / IDs do arXiv — veja a regra acima.
- **Não** deixe downloads irrelevantes no diretório da execução. As
  correspondências de busca por palavra-chave podem incluir artigos fora do
  tema (uma consulta "Claude code" trouxe um artigo sobre decodificador de
  Viterbi; "LLM code review" trouxe uma revisão de literatura sobre detecção
  de objetos). Depois de classificar artigos como fora do tema, exclua os seus
  `pdfs/<key>.pdf` e o `<key>.pptx` leve; mantenha o xlsx / bib agregado como
  o registro honesto do que a busca retornou.
- **Não** mencione "Claude", "Claude Code", "AI-generated", "GPT", "Copilot"
  ou qualquer nome de ferramenta/modelo de IA em mensagens de commit,
  descrições de PR, comentários de código ou documentação.

## Recursos

- **Quinze fontes conectáveis**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (escopado por Crossref), `dblp`, `crossref` (sem escopo),
  `openaire`, `springer` (precisa de chave de API), `europepmc` (aberto, sem
  chave — ciências da vida + preprints + agricultura), `doaj` (aberto, sem
  chave — periódicos de acesso aberto, normalmente com link direto para o
  PDF), `hal` (aberto, sem chave — arquivo francês de CC / matemática / física
  com PDFs de texto completo), `core` (precisa de chave de API gratuita — o
  maior agregador de acesso aberto, mais de 250 milhões de obras), `ieee`
  (ativo por padrão via Chrome visível; a chave de API adiciona a API oficial
  do Xplore), `scholar` (ativo por padrão via Chrome visível). Cada um vive em
  `sources/<name>/` por trás de um adaptador `Fetcher`. Passe
  `--top-tier-only` para filtrar os resultados às principais
  conferências/periódicos de CC mais Nature/Science/PNAS. A busca padrão
  mantém todos os veículos.
- **Modo de artigo único**: cole um ID do arXiv, uma URL do arXiv, um DOI, um
  PMID ou uma URL de documento do IEEE — o ThesisAgents o resolve pela fonte
  certa e emite o mesmo pacote de exportação. Útil para notas de leitura de
  artigos e preparação para a defesa de tese.
- **Modo de PDF local** (`--pdf <path>`): passe um PDF ou um diretório. Um
  extrator heurístico puxa **título, autores, ano, ID do arXiv, DOI e o resumo
  real** diretamente do início de cada PDF (ancorado no cabeçalho explícito
  `Abstract` / `ABSTRACT` / `摘要`, não num prefixo cego). `--title` /
  `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` sobrescrevem numa
  chamada de PDF único; num diretório, a extração por arquivo vence, então cada
  artigo recebe o seu próprio slide nomeado a partir da sua chave BibTeX.
- **Oito exportadores**:
  - `.pptx` — widescreen 16:9, com números de página, três níveis de
    renderização (apenas resumo leve · plano enriquecido · **estilo de tese**
    com quadrantes de pontos de dor, destaques de KPI, tabelas de comparação
    de técnicas, tabelas de resultados por RQ, resumo de contribuições,
    observação central, limitações e trabalho futuro, Q&A, referências). Todas
    as strings de template estão internacionalizadas em **14 idiomas**:
    English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어,
    Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Identidade visual de slide projetado** (não o visual padrão Calibri sobre
    branco): tipografia por idioma (Inter para latino, Microsoft JhengHei UI /
    YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI para CJK + hindi),
    geometria de acento programática (barra de acento superior em cada slide de
    conteúdo + faixa lateral na capa), formatação de tabela no estilo acadêmico
    (grade padrão removida, régua de cabeçalho azul-marinho, divisórias suaves
    entre linhas, listra alternada de linhas, alinhamento médio-vertical,
    rótulos de linha em negrito) e uma disciplina de paleta de cinco cores
    (azul-marinho / azul-petróleo / cinza / claro / branco) com o vermelho
    **proibido** para texto (use negrito + azul-petróleo `#0E7490` para ênfase).
  - **O modo claro é o caminho de renderização padrão.** Passe `--dark-mode`,
    ative o **Dark mode** na aba Deck da GUI ou defina
    `ExportOptions(dark_mode=True)` para aplicar a pós-passagem escura (fundo do
    slide `#12151B`, texto do corpo `#E5E7EB`).
  - `.xlsx` — planilha Papers + planilha de proveniência da Query, URL / PDF com
    hyperlink, cabeçalho congelado, larguras de coluna automáticas. A coluna 5
    (**Source**) mostra o veículo real de publicação (por exemplo, "IEEE
    Access"); a coluna 6 (**Indexed via**) mostra qual fetcher retornou os
    metadados (por exemplo, "openalex"), de modo que as duas informações nunca
    colidem.
  - `.md` — lista completa de fonte / título / resumo.
  - `.bib` — chaves de citação sem colisão, campos escapados para LaTeX.
  - `.json` — payload bruto para ferramentas posteriores.
  - `.ris` — intercâmbio RIS importado por Zotero / Mendeley / EndNote /
    RefWorks (o irmão do BibTeX para gerenciadores de referência não-LaTeX).
  - `.csv` — tabela plana de uma linha por artigo para planilhas / triagem
    rápida com grep (aspas RFC-4180, então vírgulas em títulos nunca deslocam
    colunas).
  - `.csl.json` — CSL-JSON para Pandoc / citeproc; renderize uma bibliografia
    em qualquer estilo CSL (APA, IEEE, Nature, …). A extensão `.csl.json` a
    mantém distinta do dump `.json` comum.
- **Kit de edição de PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  funciona contra qualquer slide que o exportador produz, mais as ferramentas
  MCP `pptx_*` equivalentes, para que um agente LLM possa iterar sobre um slide
  gerado.
- **Servidor MCP**: 13 ferramentas — `list_sources` + `list_exports`
  (descoberta), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`,
  `export` e as seis ferramentas de slide `pptx_*` (`inspect`, `review`,
  `update_slide`, `delete_slide`, `reorder_slides`, `add_slide`). Permite que
  qualquer LLM compatível com MCP (Claude Code, Claude Desktop, Cursor, …)
  conduza todo o fluxo de trabalho.
- **Dois caminhos de enriquecimento** para ir além do resumo até um verdadeiro
  slide no estilo de tese:
  - **LLM-como-agente (sem chave de API)** — o LLM chamador lê o texto do corpo
    do PDF via `fetch_pdf_text`, escreve um resumo estruturado em contexto e o
    passa para `export`.
  - **Pipeline Python (`--enrich`)** — a CLI chama a API da Anthropic por conta
    própria; modelo padrão `claude-opus-4-7`.
- **Fluxos de editora com Chrome visível**: a SERP do Scholar, o
  `/rest/search` do IEEE e todo download de PDF com paywall (ieeexplore /
  dl.acm / link.springer / sciencedirect / wiley / oup / nature / science / …)
  rodam dentro de uma sessão real e visível do Chrome via `selenium`. O usuário
  resolve o captcha / conclui o SSO na janela ao vivo uma vez;
  `THESISAGENTS_CHROME_PROFILE_DIR` persiste os cookies entre execuções.
- **Fluxo LLM-como-agente**: as ferramentas MCP fornecem busca, download de PDF
  e extração de texto. `scripts/regen_*.py` contém exemplos reproduzíveis para
  escrever à mão um `PaperSummary` rico por artigo.
- **Resolvedor de PDF de OA**: pós-deduplicação, cada artigo sem `pdf_url`
  passa por Unpaywall → S2 `openAccessPdf` → busca por título no arXiv →
  CORE.ac.uk (quando as chaves estão definidas). Ganho típico em consultas com
  muito IEEE / ACM / Springer / Elsevier: 40 a 70 pontos percentuais.
- **Segurança por padrão**: transporte HTTP somente HTTPS, limite de taxa por
  fonte (token bucket), `defusedxml` para qualquer payload XML, caminhos de
  exportação seguros contra travessia de diretório, nenhum `eval` / `exec` /
  `pickle` sobre entrada do usuário.
- **Guarda de vocabulário zh-tw / zh-cn**: ~244 padrões regex em
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  capturam palavras emprestadas do chinês simplificado renderizadas com hanzi
  tradicional (por exemplo, `內存` → `記憶體`, `魯棒性` → `穩健性`,
  `軟件` → `軟體`, `緩存` → `快取`). A mesma guarda roda ao contrário para as
  strings do locale zh-cn. A regra completa + o catálogo de regex vivem em
  `.claude/agents/rules/language-vocabulary-check.md`.

## Início rápido

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Busque no arXiv e exporte slide + planilha + BibTeX (padrão para `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Recupere um único artigo por URL — o padrão é `.pptx + .bib` (o `.xlsx` faz
menos sentido para uma única linha):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderize o slide em 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Enriquecimento por pipeline LLM (o Python chama a Anthropic diretamente —
precisa de chave de API):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Flags da CLI

| Flag | Finalidade |
|---|---|
| `--query` / `-q` | Palavras-chave (obrigatório a menos que `--paper`). |
| `--paper` / `-p` | ID / URL do arXiv, DOI, PMID ou URL de documento do IEEE. Mutuamente exclusivo com `--query`. |
| `--source` / `-s` | Lista de fontes separada por vírgulas. Padrão `arxiv`. |
| `--max` / `-n` | Máximo de resultados por fonte (1..200). Padrão 25. |
| `--year-from` / `--year-to` | Filtro de ano inclusivo. |
| `--export` / `-e` | Formatos: qualquer de `pptx,xlsx,md,bib,json,ris,csv,csl`. O padrão depende do modo (veja abaixo). |
| `--out` / `-o` | Diretório de saída. Padrão `./exports`. |
| `--filename-stem` | Sobrescreve o radical de nome de arquivo gerado. |
| `--no-abstract` | Omite o conteúdo do resumo das exportações. |
| `--lang` / `-l` | Idioma do slide: um de 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Padrão `en`. |
| `--enrich` | Variante que falha ruidosamente do auto-enriquecimento. Precisa de `ANTHROPIC_API_KEY` e do extra `[intelligence]`. (O auto-enriquecimento é padrão quando a chave está definida.) |
| `--lightweight` | Pula o enriquecimento + força o slide apenas com resumo. Use apenas para execuções rápidas / não supervisionadas; **quando um agente LLM está conduzindo, prefira o fluxo LLM-como-agente** abaixo. |
| `--llm-model` | Sobrescreve o padrão `claude-opus-4-7` para o enriquecimento. |
| `--no-pdf` | Pula o download automático do PDF. Também desativa o portão de PPT por artigo (sem PDF → sem conteúdo completo). |
| `--no-oa-resolve` | Pula o resolvedor de PDF de OA pós-deduplicação (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Restringe os resultados a arXiv + uma lista branca curada de destaques de CC (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Desativado por padrão. |
| `--paywall-threshold` | Fração de resultados com paywall que dispara o prompt de confirmação. Padrão 0.30. |
| `--yes` | Pula o prompt de paywall e prossegue. |
| `--max-slides` | Limite de slides por artigo (padrão 25; passe 0 para ilimitado). |
| `--dark-mode` | Renderiza o pptx com fundo escuro + texto quase branco. O padrão é o slide claro com faixa azul-marinho. |
| `--quiet` | Suprime a impressão por artigo. |

### Variáveis de ambiente

| Variável | Usada por | Finalidade |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Autenticação do LLM. Não é necessária para o caminho LLM-como-agente sobre MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Sobrescreve o padrão `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + resolvedor de OA | Limite de taxa mais alto; também usada pelo passo S2 `openAccessPdf` do resolvedor de OA. Chave gratuita em <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Eleva o limite anônimo do NCBI (3/s) para 10/s. Opcional. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Etiqueta de pool cortês + habilita o passo Unpaywall do resolvedor de OA (o maior ganho de cobertura de PDF para artigos com paywall de IEEE / ACM / Springer / Elsevier; ganho típico de 40 a 70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (caminho de API) | API oficial do IEEE Xplore; expõe `pdf_url` para artigos dentro do escopo. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **O IEEE está ATIVO por padrão via Chrome visível.** Defina `=1` para desativar (por exemplo, CI sem Chrome). A ramificação de scrape via httpx só roda como fallback quando o WebRunner está indisponível. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token de assinante do Crossref Plus (cabeçalho Bearer). Opcional. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Obrigatória; chave gratuita em <https://dev.springernature.com/>. O plugin levanta `ConfigError` sem ela. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **O Scholar está ATIVO por padrão via Chrome visível.** Defina `=1` para desativar (os ToS do Google proíbem acesso automatizado — ativo por padrão para cobertura, opte por sair para evitar o risco de captcha / bloqueio de IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Downloads de Scholar + IEEE + PDF com paywall | `--user-data-dir` persistente do Chrome. Defina isto e conclua VPN / SSO / login no Google uma vez; execuções subsequentes herdam os cookies, então o IEEE retorna metadados com paywall e o Scholar entrega SERPs sem limitação. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Downloads de Scholar + IEEE + PDF com paywall | `=1` força os caminhos httpx em vez de conduzir o Chrome real. Útil para CI / Docker sem um binário do Chrome; caso contrário, deixe sem definir. |
| `THESISAGENTS_CORE_API_KEY` | Resolvedor de OA + fonte de busca `core` | Chave gratuita em <https://core.ac.uk/services/api>. Habilita o passo de busca de OA no CORE.ac.uk (mais de 200 milhões de itens de OA institucionais / regionais) **e** a fonte de busca `core`. Sem ela, a fonte `core` é silenciosamente ignorada e as outras estratégias de OA (Unpaywall, S2, arXiv) ainda rodam. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Downloader de PDF | `cookies.txt` no formato Netscape. Desativado por padrão. Use apenas com editoras às quais você tem direitos institucionais. |
| `THESISAGENTS_LOG_LEVEL` | logger | `INFO` por padrão; `DEBUG` para rastreamento verboso. |

Padrões: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Sempre
sobrescrevível com um `--export` explícito.

## Fluxo LLM-como-agente

Quando um LLM no seu editor conduz o fluxo de trabalho, use as ferramentas MCP
em sequência: `search`, `download_pdfs`, `fetch_pdf_text`, depois `export` com
um `PaperSummary` rico escrito à mão. Os arquivos `scripts/regen_*.py`
existentes são exemplos reproduzíveis para o passo final de autoria e
exportação.

O runbook completo de ponta a ponta (busca → slide rico) vive em
`.claude/agents/tasks/paper-summary-author.md` — abra-o antes de iniciar uma
nova consulta para que o LLM possa executar o fluxo sem pausar por entrada do
usuário.

## Servidor MCP

Registre com o Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Ou escreva no seu arquivo de configurações:

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "thesisagents.mcp"]
    }
  }
}
```

Ferramentas:

| Ferramenta | Finalidade |
|---|---|
| `list_sources` | Enumera cada plugin + relata se cada um está habilitado no ambiente atual. Chame isto uma vez antes de `search`. |
| `list_exports` | Enumera cada formato de exportação com a sua descrição de uma linha e se ele escreve um arquivo agregado ou um arquivo por artigo. |
| `search` | Palavras-chave → lista de artigos. Aceita `top_tier_only`, `min_citations`; usa por padrão o mix completo de fontes sem chave de API. |
| `fetch_paper` | Identificador arXiv / DOI / PMID / IEEE → artigo único. |
| `fetch_pdf_text` | Baixa um PDF, retorna o texto do corpo extraído. **O caminho MCP para "eu li o artigo".** |
| `download_pdfs` | Baixa em lote os PDFs de uma lista de artigos em `{out_dir}/pdfs/`. Retorna resultados por artigo indexados pela chave BibTeX. |
| `export` | Lista de artigos + formatos → escreve `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Aceita um campo `summary` por artigo para o esquema rico no estilo de tese, `max_slides_per_paper` (padrão 25) e `dark_mode` (padrão `false` — o padrão do projeto é o slide claro com faixa azul-marinho, passe `true` para a pós-passagem escura OLED / de pouca luz). |
| `pptx_inspect` | Lê a estrutura de slide / forma de um slide existente. |
| `pptx_review` | Audita um slide numa chamada — overflow + contratos de cor + completude de seções do `paper_rule`. Detecta automaticamente o idioma do slide; também o CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Substitui `title` / `body` / `meta` (por nome de forma) ou formas arbitrárias por índice. |
| `pptx_delete_slide` | Remove um slide e a sua relação de parte. |
| `pptx_reorder_slides` | Permuta slides via `sldIdLst`. |
| `pptx_add_slide` | Anexa ou insere um novo slide de título / corpo / meta. |

Fluxo LLM-como-agente (nenhuma `ANTHROPIC_API_KEY` necessária — o LLM é o
agente):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Referência completa em [`docs/mcp.md`](docs/mcp.md).

## Estrutura do projeto

```
ThesisAgents/
├── thesisagents/                 # main package
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (thesis-style) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # PDF fetch + Anthropic summariser  ([intelligence] extra)
│   ├── evaluation/                  # offline search-quality benchmark (docs/search-quality.md)
│   ├── mcp/                         # FastMCP server (13 tools)
│   ├── sources/<name>/              # plugin folders: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── tests/                           # pytest suite + recorded fixtures (no live HTTP)
├── docs/                            # Sphinx (14 language trees)
├── scripts/                         # one-off regen scripts
└── pyproject.toml                   # ruff, bandit, build, optional extras
```

## Definição de pronto

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

A flag `-c` no bandit é obrigatória — sem ela o bandit ignora a configuração de
exceções do projeto. Ao tocar no exportador pptx, execute também uma
verificação de overflow (veja `CLAUDE.md` "Slide Deck Rules").

## GUI de desktop (PySide6)

Uma interface nativa de desktop é distribuída por trás do extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

A janela tem quatro abas — **Search**, **Settings** (persiste chaves de API
via QSettings), **Enrich** (conduz o enriquecimento LLM-como-agente /
pipeline-Python sobre um sinal `collection_ready`) e **Deck** (o toggle de modo
claro + o limite de slides + os controles de máximo de figuras fluem para
`ExportOptions`). O zip de release do Windows traz o pacote compilado com
Nuitka incluindo o PySide6, então `thesisagents.exe gui` funciona sem uma
instalação separada de Python.
**A UI é distribuída em todos os 14 idiomas** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano,
Tiếng Việt, हिन्दी, Bahasa Indonesia) — a primeira execução escolhe o idioma
a partir do locale do seu SO, então **Settings → Interface language** permite
alterá-lo. O idioma de saída do slide é uma lista suspensa separada, para que
você possa rodar a UI num idioma e emitir slides em outro. O layout é
responsivo: cada formulário fica numa `QScrollArea` e a janela redimensiona
até 900×600 (ainda cabe em 720p), com escalonamento HiDPI ativado por padrão.

Referência completa: [`docs/gui.md`](docs/gui.md).

## Empacotamento como um executável independente

Dois empacotadores estão documentados para distribuir um binário de arquivo
único que roda sem Python instalado:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build rápido (menos de um minuto), saída de 200–300 MB, inicialização de
  2–4 s. Melhor quando você itera no script de build.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build lento (5–15 minutos), saída de 80–150 MB, inicialização em menos de um
  segundo, alguma proteção de bytecode. Melhor quando os usuários finais rodam
  o binário muitas vezes.

Ambos os docs cobrem a pegadinha específica do projeto — os plugins de fonte
dinâmicos em `sources/<name>/` — e trazem um comando verificado para os pontos
de entrada da CLI e do servidor MCP.

## Integração contínua & releases

Dois workflows do GitHub Actions vivem em `.github/workflows/`:

- **`ci.yml`** roda em cada push e PR para `main`. A matriz é Ubuntu + Windows
  × Python 3.12 / 3.13 / 3.14 (6 jobs). Cada job roda `ruff check`,
  `bandit -c pyproject.toml` e `pytest`.
- **`release.yml`** espera o `ci.yml` completar em `main` (gatilho
  `workflow_run`). Ele roda apenas se o CI teve sucesso. **Cada push com CI
  bem-sucedido para `main` é um release** — o workflow incrementa
  automaticamente a versão de patch em `pyproject.toml`, faz o commit do
  incremento de volta em `main` como `chore: bump version to X.Y.Z`, e
  encadeia:
  1. **`bump-version`** — lê a `X.Y.Z` atual de `pyproject.toml`, incrementa
     para `X.Y.(Z+1)`, faz commit + push de volta em `main` usando o
     `GITHUB_TOKEN` do workflow. Esse push NÃO re-dispara o CI (pela regra do
     GitHub de que pushes conduzidos pelo `GITHUB_TOKEN` não podem iniciar
     novas execuções de workflow), então o ciclo termina naturalmente.
  2. **`publish-pypi`** — constrói sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — abre um release *rascunho* do GitHub na tag
     `v<version>` com notas geradas automaticamente.
  4. **`build-nuitka`** — compila um pacote standalone do Nuitka num runner do
     Windows (ponto de entrada: `python -m thesisagents` via
     `--python-flag=-m`), faz smoke-test dele, compacta a pasta
     `thesisagents.dist/` resultante e anexa o zip + um checksum `.sha256` ao
     release rascunho. Standalone (não onefile) por design: o onefile se
     autoextrai para `%TEMP%` a cada inicialização, adicionando latência de
     inicialização e disparando heurísticas de antivírus em máquinas
     bloqueadas. Somente Windows por design também: usuários de Linux / macOS
     instalam a partir do PyPI. O cache de build indexado por `pyproject.toml`
     corta os builds quentes de ~85 min a frio para ~5–10 min.
  5. **`publish-release`** — desmarca o rascunho assim que o artefato do Nuitka
     é enviado, para que os usuários nunca vejam um release pela metade.

  **Pulando um release.** Inclua `[skip release]` em qualquer lugar da mensagem
  de commit e o incremento + cada job downstream são pulados — use isto para
  commits apenas de docs / typo / refatoração que não devem queimar um número
  de versão.

Para habilitar a publicação no PyPI + executáveis de release:

1. Gere um token de API com escopo de projeto em
   <https://pypi.org/manage/account/token/>.
2. No repositório do GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Nomeie-o `PYPI_API_TOKEN` e cole o valor do token.
3. Permita que o GitHub Actions faça push para `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. O commit de
   incremento é enviado pelo `GITHUB_TOKEN` do workflow.
4. Corte releases mesclando PRs em `main`. O pipeline leva ~3–5 min para
   publicar no PyPI e mais ~80–90 min (a frio) ou ~5–10 min (com cache quente
   do Nuitka) para o zip do Windows ser anexado.

O job `publish-pypi` intencionalmente NÃO anexa um Environment do GitHub, então
cada execução aparece como uma entrada de Release (com o seu `.exe` do Nuitka
anexado) em vez de como um widget lateral de "Deployment" na home do repo — os
releases têm a sua própria página dedicada e uma entrada de Deployment por cima
seria apenas ruído redundante.

## Licença

Veja `LICENSE`. A API do arXiv é usada sob os termos de uso da API do arXiv
(<https://info.arxiv.org/help/api/tou.html>) — observe o limite suave de 1
requisição a cada 3 segundos; o fetcher incluído já o impõe via o seu token
bucket.
