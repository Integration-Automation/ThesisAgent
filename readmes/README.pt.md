# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Idiomas**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · **Português** · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentação**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Assistente de busca de artigos guiado por palavras-chave que recupera resultados do arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore, DBLP, Crossref genérico, OpenAIRE, Springer Nature e Google Scholar; normaliza-os para um único formato de registro; e exporta o conjunto deduplicado como **apresentação PowerPoint estilo tese**, **planilha Excel** e **arquivo BibTeX** — tudo por uma única chamada CLI ou uma chamada de ferramenta MCP. Pode opcionalmente enriquecer cada artigo lendo seu PDF e produzindo um resumo estruturado, no próprio contexto (fluxo LLM-as-agent) ou via API Anthropic (fluxo Python pipeline).

## Para agentes de IA que dirigem este projeto

**Se você é um LLM (Claude Code, Cursor, Aider, Codex CLI, …) lendo este README para entender o que fazer — comece aqui.** As mesmas regras estão fixadas em [`AGENTS.md`](AGENTS.md) (espelho entre agentes) e [`CLAUDE.md`](CLAUDE.md) (referência canônica); leia-os antes de mudanças não triviais.

### O que o usuário realmente quer

A entrega padrão é **um `.pptx` enriquecido estilo tese por artigo**, não o deck leve só com o resumo que a CLI gera por padrão. A saída leve é um artefato intermediário — sua tarefa é elevá-la.

### Árvore de decisão

1. `ANTHROPIC_API_KEY` está definida no ambiente? → execute a CLI; ela auto-enriquece via API Anthropic. Fim.
2. Sem chave, mas você (LLM) está dirigindo a sessão → **você produz o resumo enriquecido**. Leia cada PDF, escreva à mão um `PaperSummary` com campos rich-tier (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), salve um `scripts/regen_<query>.py` e execute-o. **Não diga ao usuário para configurar a chave API** — você é o LLM que teria escrito o resumo.
3. Sem LLM no loop (CI / cron / não-supervisionado) → saída leve é aceitável.

### Fluxo MCP de 6 passos

```
1. (opcional) list_sources()                              # quais plugins estão habilitados
2. search(keywords, sources, top_tier_only=true, ...)
3. (opcional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # por artigo
5. (você lê cada PDF e produz um dict de resumo estruturado)
6. export(papers=[{...paper, "summary": {...}}], language="pt", ...)
```

As onze ferramentas MCP (incluindo `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / etc.) estão documentadas em [`docs/mcp.md`](docs/mcp.md).

### Obrigatório: verificação de URL / DOI antes da entrega

Caminhos de URL de editoras **não podem ser adivinhados** — AAAI usa IDs numéricos (`v40i5.37389`), IEEE usa `arnumber` opaco, ACM usa DOIs opacos. Ao escrever um `Paper` à mão, **copie `url` / `doi` / `arxiv_id` literalmente do xlsx que esta busca produziu** — nunca de memória, nunca construído a partir do título.

O xlsx é gravado em `exports/<run>/<slug>-<timestamp>.xlsx` com coluna 7 = DOI, coluna 8 = URL. Audite seu script regen ao terminar:

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

Duas fabricações detectadas assim em produção: volume AAAI errado (`v39i23.34521` vs o real `v39i22.34537`) e caminho com slug de autor inventado (`view/fang2026` em vez de `v40i5.37389`).

### Exemplo trabalhado

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) traz 8 resumos enriquecidos escritos à mão exatamente por este processo. Use-o como template para qualquer busca multi-artigos. A versão zh-tw está em [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Proibido

- **Não** encerre uma busca multi-artigos dizendo ao usuário "configure `ANTHROPIC_API_KEY` para deck enriquecido" — você é o LLM que poderia ter escrito os resumos.
- **Não** trate o `.pptx` leve por artigo como entrega.
- **Não** pare quando `download_pdfs` reportar N PDFs salvos — esse é o início da fase de redação rich, não o fim.
- **Não** invente números, RQs, contribuições ou limitações ausentes do artigo.
- **Não** fabrique URLs / DOIs / IDs arXiv — veja a regra acima.
- **Não** deixe downloads irrelevantes no diretório de execução. A busca por palavras-chave às vezes inclui artigos fora do tema (uma consulta "Claude code" trouxe um artigo sobre decodificador Viterbi; "LLM code review" trouxe uma revisão sobre detecção de objetos). Após classificar como fora de tema, exclua o `pdfs/<key>.pdf` e o `<key>.pptx` leve; mantenha o xlsx / bib agregado como registro honesto do que a busca retornou.
- **Não** mencione "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" nem qualquer nome de ferramenta/modelo de IA em mensagens de commit, descrições de PR, comentários ou documentação.

## Funcionalidades

- **Onze fontes plugáveis**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (limitado ao ACM via Crossref), `dblp`, `crossref` (genérico), `openaire`, `springer` (requer chave API), `ieee` (chave API ou scraping opt-in), `scholar` (scraping opt-in). Cada uma vive em `sources/<name>/` atrás de um adaptador `Fetcher`. Uma lista branca de periódicos de elite filtra os resultados para conferências/journals CS bandeira + Nature/Science/PNAS por padrão; `--all-venues` desativa.
- **Modo artigo único**: cole um arXiv ID, URL arXiv, DOI, PMID ou URL de documento IEEE — AutoPaperToPPT resolve via a fonte certa e emite o mesmo pacote de exportação. Útil para notas de leitura e preparação de defesa.
- **Modo PDF local** (`--pdf <caminho>`): passe um PDF ou um diretório. Um extrator heurístico extrai **título, autores, ano, ID arXiv, DOI e o resumo real** direto do início de cada PDF (ancorado no cabeçalho explícito `Abstract` / `ABSTRACT` / `摘要`, não em um prefixo cego). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` sobrescrevem em chamada de PDF único; em diretório, a extração por arquivo ganha — cada artigo recebe seu próprio deck nomeado com sua chave BibTeX.
- **Cinco exportadores**:
  - `.pptx` — widescreen 16:9, numerado, três níveis de renderização (leve só-resumo · enriched-flat · **estilo tese** com quadrantes de dor, KPIs destacados, tabelas comparativas de técnicas, tabelas por RQ, resumo de contribuições, observação central, limitações & trabalhos futuros, Q&A, referências). Todas as strings de template têm i18n em **14 idiomas**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — planilha Papers + planilha de proveniência Query, URL / PDF hiperlinkados, cabeçalho fixo, largura automática. Coluna 5 (**Source**) mostra o local real de publicação (ex.: "IEEE Access"); coluna 6 (**Indexed via**) mostra qual fetcher devolveu os metadados (ex.: "openalex"), evitando confusão.
  - `.md` — lista completa de fonte / título / resumo.
  - `.bib` — chaves de citação sem colisão, campos com escape LaTeX.
  - `.json` — payload bruto para ferramentas downstream.
- **Toolkit de edição PPT**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) funciona em qualquer deck que o exportador produzir, mais as ferramentas MCP equivalentes `pptx_*` para um agente LLM iterar no deck gerado.
- **Servidor MCP**: 11 ferramentas — `list_sources` (descoberta), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, e as cinco de edição `pptx_*`. Permite qualquer LLM compatível com MCP (Claude Code, Claude Desktop, Cursor, …) dirigir todo o workflow.
- **Duas rotas de enriquecimento** para ir além do resumo até um deck verdadeiro estilo tese:
  - **LLM-as-agent (sem chave API)** — o LLM chamador lê o texto do PDF via `fetch_pdf_text`, escreve um resumo estruturado no contexto e passa para `export`.
  - **Pipeline Python (`--enrich`)** — a CLI chama a API Anthropic diretamente; modelo padrão `claude-opus-4-7`.
- **Seguro por padrão**: transporte HTTP somente-HTTPS, rate limit por fonte (token bucket), `defusedxml` para qualquer payload XML, caminhos de exportação seguros contra path-traversal, sem `eval` / `exec` / `pickle` em input do usuário. Scraping de Scholar e IEEE desativado por padrão (opt-in via env var).

## Início rápido

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Instalar com extras dev (também traz SDK MCP e deps intelligence)
pip install -e .[dev]
```

Buscar arXiv e exportar deck + workbook + BibTeX (padrão para `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Buscar um artigo por URL — padrão `.pptx + .bib` (um `.xlsx` de uma linha não faz muito sentido):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderizar o deck em português:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang pt --out .\exports\
```

Enriquecimento pipeline LLM (Python chama Anthropic — exige chave API):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang pt --out .\exports\
```

## Flags CLI

| Flag | Propósito |
|---|---|
| `--query` / `-q` | Palavras-chave (obrigatório a menos que `--paper`). |
| `--paper` / `-p` | ID/URL arXiv, DOI, PMID ou URL documento IEEE. Mutuamente exclusivo com `--query`. |
| `--source` / `-s` | Lista de fontes separadas por vírgula. Padrão `arxiv`. |
| `--max` / `-n` | Máx. resultados por fonte (1..200). Padrão 25. |
| `--year-from` / `--year-to` | Filtro de ano inclusivo. |
| `--export` / `-e` | Formatos: qualquer de `pptx,xlsx,md,bib,json`. Padrão depende do modo (ver abaixo). |
| `--out` / `-o` | Diretório de saída. Padrão `./exports`. |
| `--filename-stem` | Sobrescreve o stem de nome gerado. |
| `--no-abstract` | Omite conteúdo de resumo nos exports. |
| `--lang` / `-l` | Idioma do deck: um dos 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Padrão `en`. |
| `--enrich` | Baixa PDF + resumo Anthropic. Requer `ANTHROPIC_API_KEY` e o extra `[intelligence]`. |
| `--lightweight` | Força deck leve mesmo com `ANTHROPIC_API_KEY` configurada. |
| `--llm-model` | Sobrescreve o modelo padrão `claude-opus-4-7`. |
| `--all-venues` | Desativa a whitelist de elite (padrão mantém venues CS bandeira + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Fração de resultados paywall que dispara confirmação. Padrão 0.30. |
| `--yes` | Pula o prompt de paywall. |
| `--max-slides` | Limite de slides por artigo (padrão 25; 0 para ilimitado). |
| `--quiet` | Suprime impressão por artigo. |

### Variáveis de ambiente

| Variável | Usada por | Propósito |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth do LLM. Desnecessário para a rota LLM-as-agent via MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Sobrescreve o padrão `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Rate limit maior. Opcional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Eleva o limite anônimo do NCBI (3/s) para 10/s. Opcional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Coloca requisições no polite pool do Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (rota API) | API oficial IEEE Xplore; expõe `pdf_url` para artigos no escopo. |
| `AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING` | IEEE (rota scraping) | `=1` ativa scraping. Desnecessário quando a chave API está configurada. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token de assinante Crossref Plus (header Bearer). Opcional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Obrigatório; chave gratuita em <https://dev.springernature.com/>. Plugin é silenciosamente pulado sem ele. |
| `AUTOPAPERTOPPT_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF downloads | Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO once; subsequent runs inherit the cookies. |
| `AUTOPAPERTOPPT_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF downloads | `=1` forces the httpx paths instead of driving real Chrome. For CI / Docker without a Chrome binary. |
| `AUTOPAPERTOPPT_CORE_API_KEY` | OA resolver | Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step in the OA PDF resolver. |
| `AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` ativa scraping. Padrão desligado — ToS do Scholar proíbe scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | Downloader PDF | `cookies.txt` formato Netscape. Padrão desligado. Use apenas com editoras nas quais você tem direitos institucionais. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` padrão; `DEBUG` para rastreamento verboso. |

Padrões: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Sempre sobrescritível com `--export` explícito.

## Servidor MCP

Registrar com Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Ou editar o arquivo de configuração:

```json
{
  "mcpServers": {
    "autopapertoppt": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "autopapertoppt.mcp"]
    }
  }
}
```

Ferramentas:

| Ferramenta | Propósito |
|---|---|
| `list_sources` | Enumera cada plugin + reporta se cada um está habilitado no env atual. Chame uma vez antes de `search`. |
| `search` | Palavras-chave → lista de artigos. Aceita `top_tier_only`, `min_citations`; padrão usa o mix completo sem chave API. |
| `fetch_paper` | Identificador arXiv / DOI / PMID / IEEE → artigo único. |
| `fetch_pdf_text` | Baixa um PDF, retorna o texto extraído. **A rota MCP para "li o artigo".** |
| `download_pdfs` | Baixa em lote PDFs de uma lista de artigos em `{out_dir}/pdfs/`. Retorna resultados por artigo indexados por chave BibTeX. |
| `export` | Lista de artigos + formatos → grava `.pptx/.xlsx/.md/.bib/.json`. Aceita campo `summary` por artigo para o schema estilo tese e `max_slides_per_paper` (padrão 25). |
| `pptx_inspect` | Lê a estrutura slide/shape de um deck existente. |
| `pptx_update_slide` | Substitui `title` / `body` / `meta` (pelo nome do shape) ou shapes arbitrários por índice. |
| `pptx_delete_slide` | Remove um slide e sua part relationship. |
| `pptx_reorder_slides` | Reordena slides via `sldIdLst`. |
| `pptx_add_slide` | Anexa ou insere novo slide title / body / meta. |

Fluxo LLM-as-agent (sem `ANTHROPIC_API_KEY` — o LLM é o agente):

```
1. (opcional) list_sources()                       # descobrir plugins habilitados
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (opcional) download_pdfs(papers, out_dir="./exports/...")  # persistir PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # por artigo
5. (o LLM lê o texto, produz um dict `summary` estruturado)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="pt", formats=["pptx","bib"], ...)
```

Referência completa em [`docs/mcp.md`](docs/mcp.md).

## Estrutura do projeto

```
AutoPaperToPPT/
├── autopapertoppt/                 # pacote principal
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # cliente async HTTPS only, rate limit token bucket
│   ├── exporters/                   # pptx (estilo tese) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # download PDF + sumarizador Anthropic ([intelligence] extra)
│   ├── mcp/                         # servidor FastMCP (11 ferramentas)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # pastas de plugin: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # suite pytest + fixtures gravados (sem HTTP ao vivo)
├── docs/                            # Sphinx (14 árvores de idiomas)
├── scripts/                         # scripts regen únicos
└── pyproject.toml                   # ruff, bandit, build, extras opcionais
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

O flag `-c` do bandit é obrigatório — sem ele, bandit ignora a configuração skip do projeto. Ao mexer no exportador pptx, rode também uma checagem de overflow (ver `CLAUDE.md` "Slide Deck Rules").

## Licença

Ver `LICENSE`. A API arXiv é usada sob seus termos (<https://info.arxiv.org/help/api/tou.html>) — respeite o limite soft de 1 requisição a cada 3 segundos; o fetcher embutido já o impõe via token bucket.
