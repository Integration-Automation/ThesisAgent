AutoPaperToPPT ユーザーガイド
=============================

キーワード駆動の論文検索アシスタント。arXiv、Semantic Scholar、OpenAlex、
PubMed、ACM、IEEE Xplore、DBLP、Crossref、OpenAIRE、Springer Nature、
Google Scholar から論文を取得し、論文発表用 PowerPoint デッキ、Excel
ワークブック、BibTeX ファイルとして出力します。1 つの CLI コール、または
1 つの MCP ツール呼び出しで完結します。

.. contents:: 目次
   :depth: 2
   :local:

----

このプロジェクトを駆動する AI エージェントへ
---------------------------------------------

**あなたが LLM(Claude Code、Cursor、Aider、Codex CLI、…)で何をすべきか
把握しようとしているなら、ここから始めてください。** 同じルールが repo の
``AGENTS.md``\ (エージェント横断のミラー)と ``CLAUDE.md``\ (正式な
参照)にも固定されています。非自明な変更を加える前にそちらを読んでください。

**デフォルト納品物は「論文ごとに 1 つのリッチな thesis-style ``.pptx``」**\
であり、CLI がデフォルトで吐く軽量の要約のみのデッキではありません。軽量版
は中間成果物 — あなたの仕事はそれをアップグレードすることです。

判断フローチャート
^^^^^^^^^^^^^^^^^^

1. 環境に ``ANTHROPIC_API_KEY`` あり? → CLI を実行するだけ。Anthropic
   API 経由で自動エンリッチされます。
2. キー無しで LLM(あなた)がセッションを駆動 → **リッチサマリを自分で
   書く**\ 。各 PDF を読み、``PaperSummary``\ をリッチ層フィールドで
   手書き、``scripts/regen_<query>.py``\ を置いて実行。**ユーザーに
   API キーの設定を求めない** — あなたがその LLM です。
3. LLM 不在(CI / cron)→ 軽量版で OK。

MCP 6 ステップ
^^^^^^^^^^^^^^

.. code-block:: text

   1. (任意) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (任意) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # 論文ごと
   5. (各 PDF を読み、構造化 summary dict を生成)
   6. export(papers=[{...paper, "summary": {...}}], language="ja", ...)

11 個の MCP ツールの完全な参照は :doc:`/mcp` にあります。

必須: 納品前 URL / DOI 検証
^^^^^^^^^^^^^^^^^^^^^^^^^^^

出版社の URL パスは推測できません — AAAI は数値 ID(``v40i5.37389``)、
IEEE は不透明な ``arnumber``\ 、ACM は不透明な DOI を使います。``Paper``\
を手書きする際、``url`` / ``doi`` / ``arxiv_id``\ は\ **検索が出力した
xlsx から逐語コピー**\ してください。記憶やタイトルから構築禁止。

xlsx は ``exports/<run>/<slug>-<timestamp>.xlsx``\ に出力され、列 7 = DOI、
列 8 = URL です。regen 後に必ず以下の監査を実行:

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

禁止事項
^^^^^^^^

* ユーザーに「``ANTHROPIC_API_KEY`` を設定すればリッチデッキが出る」と
  言わない — あなたがその LLM です。
* 軽量 ``.pptx``\ を納品物として扱わない。
* ``download_pdfs``\ の完了で止まらない — それはリッチ作成の開始です。
* 論文に無い数値、RQ、貢献、限界を捏造しない。
* URL / DOI / arXiv ID を捏造しない。
* 実行ディレクトリに無関係なダウンロードを残さない。キーワード検索は
  無関係な論文を含めることがある(「Claude code」検索が Viterbi
  デコーダ論文をヒットさせた等)。無関係な ``pdfs/<key>.pdf`` と
  軽量 ``<key>.pptx`` を削除し、集約 xlsx / bib は「正直な記録」
  として残す。完全な手順は ``CLAUDE.md`` の「Pruning irrelevant
  downloads」参照。
* コミット、PR、コメント、ドキュメントで「Claude」「Claude Code」
  「AI-generated」「GPT」「Copilot」など AI ツール / モデル名に言及しない。

ワーキング例: ``scripts/regen_llm_security_batch.py``\ (en、8 篇)と
``scripts/regen_llm_security_batch_zh_tw.py``\ (zh-tw)。

----

インストール
------------

Python **3.12+** が必要です。

.. code-block:: bash

   git clone <repo-url>
   cd AutoPaperToPPT
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

オプションの extras: ``[mcp]``\ (MCP SDK のみ)、``[intelligence]``\
(pypdf + anthropic、``--enrich``\ 用)、``[web]``\ (将来予約)、``[dev]``\
(全部)。

----

クイックスタート
----------------

.. code-block:: bash

   # arXiv で検索 → デッキ + ワークブック + BibTeX
   autopapertoppt --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # 単一論文を URL で取得 → デッキ + BibTeX
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # 日本語でデッキを描画
   autopapertoppt --paper 1706.03762 --lang ja --out ./exports/

   # Python パイプライン経由のエンリッチ(Anthropic API キー必須)
   export ANTHROPIC_API_KEY=sk-ant-...
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang ja --out ./exports/

CLI フラグの完全な表は :doc:`/cli` を参照してください。

----

さらに詳しく
------------

* CLI フラグの完全な一覧と環境変数: :doc:`/cli`
* MCP サーバーの 11 ツール: :doc:`/mcp`
* PPTX 編集ツールキット: :doc:`/pptx_editing`
* このリポジトリ言語別の README ファイル(``readmes/README.ja.md``\ など)に
  プロジェクトの全機能リストがあります
* より詳しい技術リファレンス(プラグインアーキテクチャ、安全性ポリシー、
  Definition of Done、SonarQube ルールなど)は英語版ガイド
  :doc:`/en/index` に集約されています
