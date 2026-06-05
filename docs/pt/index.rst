Guia de uso ThesisAgents
==========================

Assistente de busca de artigos guiado por palavras-chave. Recupera
resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE e Google Scholar; e
exporta como apresentação PowerPoint estilo tese, planilha Excel e
arquivo BibTeX. Tudo a partir de uma chamada CLI ou uma chamada de
ferramenta MCP.

.. contents:: Sumário
   :depth: 2
   :local:

----

Para agentes de IA que dirigem este projeto
-------------------------------------------

**Se você é um LLM (Claude Code, Cursor, Aider, Codex CLI, …) lendo
isto para entender o que fazer — comece aqui.** As mesmas regras estão
fixadas em ``AGENTS.md`` (espelho entre agentes) e ``CLAUDE.md``
(referência canônica) na raiz do repo; leia-os antes de mudanças não
triviais.

**A entrega padrão é um ``.pptx`` enriquecido estilo tese por artigo**,
não o deck leve só-resumo que a CLI gera por padrão. Leve é artefato
intermediário — sua tarefa é elevá-lo.

Árvore de decisão
^^^^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` configurada? → execute a CLI; auto-enriquece
   via API Anthropic.
2. Sem chave, LLM dirige → **escreva o resumo enriquecido você mesmo**.
   Leia cada PDF, escreva à mão ``PaperSummary`` com campos rich-tier,
   salve ``scripts/regen_<query>.py``, execute. **Não diga ao usuário
   para configurar a chave API** — você é o LLM.
3. Sem LLM (CI / cron) → leve aceitável.

Fluxo MCP de 6 passos
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (opcional) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (opcional) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # por artigo
   5. (você lê cada PDF e produz dict summary estruturado)
   6. export(papers=[{...paper, "summary": {...}}], language="pt", ...)

As 11 ferramentas MCP completas: :doc:`/mcp`.

Obrigatório: verificação URL / DOI antes da entrega
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caminhos de URL das editoras **não podem ser adivinhados** — AAAI usa
IDs numéricos (``v40i5.37389``), IEEE usa ``arnumber`` opaco, ACM usa
DOIs opacos. Ao escrever um ``Paper`` à mão, **copie ``url`` /
``doi`` / ``arxiv_id`` literalmente do xlsx que esta busca produziu**
— nunca de memória, nunca construído a partir do título.

O xlsx é gravado em ``exports/<run>/<slug>-<timestamp>.xlsx`` com
coluna 7 = DOI, coluna 8 = URL. Audite seu script regen ao terminar:

.. code-block:: python

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

Proibições
^^^^^^^^^^

* Não diga ao usuário "configure ``ANTHROPIC_API_KEY``" — você é o LLM.
* Não trate ``.pptx`` leve como entrega.
* Não pare quando ``download_pdfs`` terminar.
* Não invente números, RQs, contribuições, limitações.
* Não fabrique URLs / DOIs / IDs arXiv.
* Não deixe downloads irrelevantes no diretório de execução. A busca
  por palavras-chave pode trazer artigos fora do tema (uma consulta
  "Claude code" trouxe um artigo sobre decodificador Viterbi). Apague
  ``pdfs/<key>.pdf`` e ``<key>.pptx`` leves fora de tema; mantenha o
  xlsx / bib agregado como registro honesto. Procedimento completo em
  ``CLAUDE.md`` "Pruning irrelevant downloads".
* Não mencione "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot" nem qualquer nome de ferramenta/modelo IA em commits,
  PRs, código ou docs.

Exemplos: ``scripts/regen_llm_security_batch.py`` (en, 8 artigos) e
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Instalação
----------

Requer Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras opcionais: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Início rápido
-------------

.. code-block:: bash

   # Buscar arXiv → deck + workbook + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Um artigo por URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Renderizar deck em português
   thesisagents --paper 1706.03762 --lang pt --out ./exports/

   # Enriquecimento Python pipeline (exige chave Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang pt --out ./exports/

Tabela completa de flags CLI: :doc:`/cli`.

----

Onde procurar mais
------------------

* Flags CLI e variáveis de ambiente: :doc:`/cli`
* 11 ferramentas do servidor MCP: :doc:`/mcp`
* Toolkit de edição PPTX: :doc:`/pptx_editing`
* O arquivo ``readmes/README.pt.md`` na raiz do repo tem a lista completa de
  funcionalidades.
* A referência técnica profunda (arquitetura de plugins, políticas de
  segurança, Definition of Done, regras SonarQube, …) está
  consolidada no guia inglês: :doc:`/en/index`.
