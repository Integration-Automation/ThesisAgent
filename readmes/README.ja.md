# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **言語**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · **日本語** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **ドキュメント**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

キーワード駆動の論文検索アシスタント。arXiv、Semantic Scholar、OpenAlex、PubMed、ACM(Crossref 経由)、IEEE Xplore、DBLP、汎用 Crossref、OpenAIRE、Springer Nature、Europe PMC、DOAJ、HAL、CORE、Google Scholar から結果を取得し、統一されたレコード形式に正規化、重複排除後の集合を **論文発表級の PowerPoint デッキ**、**Excel ワークブック**、**BibTeX ファイル** として出力します — CLI 1 回または MCP ツール呼び出し 1 回で完結。オプションで各論文の PDF を読んで構造化された論文ごとのサマリを生成でき、コンテキスト内(LLM-as-agent フロー)または Anthropic API 経由(Python パイプラインフロー)から選べます。

## このプロジェクトを駆動する AI エージェントへ

**あなたが LLM(Claude Code、Cursor、Aider、Codex CLI、…)で、この README を読んで何をすべきか把握しようとしているなら、ここから始めてください。** 以下の内容はすべて [`AGENTS.md`](AGENTS.md)(エージェント横断のミラー)と [`CLAUDE.md`](CLAUDE.md)(正式な参照先)にも固定されています。非自明な変更を加える前にそちらを読んでください。

### ユーザーが本当に欲しいもの

デフォルトの納品物は **論文発表向けのリッチな `.pptx` を 1 論文 1 枚** であり、CLI がデフォルトで吐く要約だけの軽量デッキではありません。軽量出力は中間成果物 — あなたの仕事はそれをアップグレードすることです。

### 判断フローチャート

1. 環境変数に `ANTHROPIC_API_KEY` が設定されているか? → CLI を実行するだけ。Anthropic API 経由で自動エンリッチされます。これで完了。
2. キーは無いが、あなた(LLM)がセッションを駆動している → **リッチサマリは自分で書く**。各 PDF を読み、リッチ層のフィールド(`pain_points`、`research_question`、`contributions_detailed`、`headline_metrics`、`technique_table`、`method_sections`、`evaluation_sections`、`system_flow`、`research_questions`、`rq_results`、`core_observation`、`limitations`、`future_work`)を持つ `PaperSummary` を手書きし、`scripts/regen_<query>.py` を置いて実行。**ユーザーに API キーを設定するよう求めてはいけません** — あなたがそのサマリを書けたはずの LLM です。
3. ループ内に LLM がいない(CI / cron / 無人運転)→ 軽量版で許容。

### MCP 6 ステップワークフロー

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

13 個の MCP ツール(`list_sources`、`list_exports`、`download_pdfs`、`pptx_inspect` / `pptx_review` / `pptx_update_slide` / `pptx_add_slide` など)はすべて [`docs/mcp.md`](docs/mcp.md) に記載されています。

### 必須: 納品前に URL / DOI を検証

出版社の URL パスは **推測できません** — AAAI は数値 ID(`v40i5.37389`)、IEEE は不透明な `arnumber`、ACM は不透明な DOI を使います。`Paper` を手書きする際は、**この実行を生成した検索 xlsx から `url` / `doi` / `arxiv_id` を逐語コピー** してください — 記憶からでも、タイトルから構築するのでもなく。

xlsx は `exports/<run>/<slug>-<timestamp>.xlsx` に出力され、列 7 = DOI、列 8 = URL。作業が終わったら regen スクリプトを監査します:

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

この方法で本番で検出された 2 件の偽造: AAAI 巻号の誤り(`v39i23.34521` 対 実際の `v39i22.34537`)と、捏造された著者 slug パス(`v40i5.37389` の代わりに `view/fang2026`)。

### 必須: 納品前に無関係なダウンロードを整理

検索のキーワードマッチはキーワードベースなので、話題外の論文が紛れ込みます: 「Claude code」クエリはどちらにも「code」を含むため Viterbi デコーダ論文を返し、「LLM code review」は物体検出のレビュー論文にマッチしました。要旨を読んでユーザーの実際の意図に対して話題外だと分類したら、実行ディレクトリを整理します:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

`exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx` を削除します。集約された `<slug>-<timestamp>.xlsx` / `.bib` は **残す** — それらは検索が何を返したかの正直な記録です。境界的なケースにはリッチサマリを付けます。可能性のあるマッチを黙って落とすよりは、含めすぎるほうが良いです。

### 実例

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) には、まさにこの方法で手書きされたリッチサマリが収録されています(単一論文、リッチ層、zh-tw、すべてのリッチフィールドを埋めたもの)。複数論文検索も同じ形に従い、`PaperCollection` タプル内に論文ごとに `Paper(...summary=PaperSummary(...))` エントリを 1 件ずつ置きます。

### 禁止事項

- **やってはいけない**: 複数論文検索の最後に「リッチデッキが欲しければ `ANTHROPIC_API_KEY` を設定して」とユーザーに伝える — あなたがそのサマリを書けたはずの LLM です。
- **やってはいけない**: 論文ごとの軽量 `.pptx` を最終納品物として扱う。
- **やってはいけない**: `download_pdfs` が「N 件保存」と報告した時点で止める — それはリッチ作成フェーズの開始であって終わりではない。
- **やってはいけない**: 論文に無い数字、RQ、貢献、限界を捏造する。
- **やってはいけない**: URL / DOI / arXiv ID を捏造する — 上記のルールを参照。
- **やってはいけない**: 実行ディレクトリに無関係なダウンロードを残す。キーワード検索のマッチは話題外の論文を含みうる(「Claude code」クエリが Viterbi デコーダ論文を引き込み、「LLM code review」が物体検出のレビュー論文を引き込んだ)。話題外と分類したら、その `pdfs/<key>.pdf` と軽量 `<key>.pptx` を削除する。集約 xlsx / bib は検索が何を返したかの正直な記録として残す。
- **やってはいけない**: コミットメッセージ、PR 説明、コードコメント、ドキュメントで「Claude」「Claude Code」「AI-generated」「GPT」「Copilot」など AI ツール / モデル名に言及する。

## 機能

- **15 個のプラガブルソース**: `arxiv`、`semantic_scholar`、`openalex`、`pubmed`、`acm`(Crossref スコープ)、`dblp`、`crossref`(スコープ無し)、`openaire`、`springer`(API キー必須)、`europepmc`(オープン、キー不要 — 生命科学 + プレプリント + 農業)、`doaj`(オープン、キー不要 — オープンアクセス誌、通常は直接 PDF リンク付き)、`hal`(オープン、キー不要 — フランスの CS / 数学 / 物理アーカイブ、全文 PDF 付き)、`core`(無料 API キー必須 — 最大のオープンアクセスアグリゲータ、2.5 億件以上)、`ieee`(可視 Chrome 経由でデフォルト有効、API キーで公式 Xplore API を追加)、`scholar`(可視 Chrome 経由でデフォルト有効)。各々が `sources/<name>/` 配下で `Fetcher` アダプタの後ろに実装されています。`--top-tier-only` を渡すと、結果を旗艦級 CS 学会 / 学会誌 + Nature/Science/PNAS に絞り込めます。デフォルトの検索はすべての venue を保持します。
- **単一論文モード**: arXiv ID、arXiv URL、DOI、PMID、または IEEE 文書 URL を貼り付けると、ThesisAgents が適切なソース経由でそれを解決し、同じエクスポートバンドルを生成します。論文読解ノートや修論発表準備に便利です。
- **ローカル PDF モード**(`--pdf <path>`): PDF 1 つまたはディレクトリを渡します。ヒューリスティック抽出器が各 PDF の冒頭から **タイトル、著者、年、arXiv ID、DOI、本物の要約** を直接引き出します(明示的な `Abstract` / `ABSTRACT` / `摘要` ヘッダーを基準とし、盲目的な先頭切り出しではありません)。単一 PDF 呼び出しでは `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` で上書き可能。ディレクトリではファイルごとの抽出が優先され、各論文はその BibTeX キーにちなんだ名前のデッキを得ます。
- **8 つのエクスポータ**:
  - `.pptx` — 16:9 ワイドスクリーン、ページ番号付き、3 つのレンダリング層(軽量な要約のみ · フラット強化 · **論文発表級**: ペインポイント四象限、KPI コールアウト、技術比較表、RQ ごとの結果表、貢献まとめ、コア観察、限界と今後の課題、Q&A、参考文献)。すべてのテンプレート文字列は **14 言語** に i18n 対応: English、繁體中文、简体中文、日本語、Español、Français、Deutsch、한국어、Português、Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - **デザイン済みデッキのビジュアルアイデンティティ**(デフォルトの Calibri-on-white ではありません): 言語ごとのタイポグラフィ(Latin に Inter、CJK + Hindi に Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI)、プログラム生成のアクセント幾何(全コンテンツスライド上端のアクセントバー + カバーの左帯)、学術風テーブル書式(デフォルトのグリッド除去、navy ヘッダールール、淡い行間 divider、交互の行ストライプ、垂直中央揃え、行ラベルは太字)、5 色 palette の規律(navy / teal / grey / light / white)、テキストの赤色は **禁止**(強調には代わりに太字 + teal `#0E7490` を使用)。
  - **ライトモードがデフォルトのレンダーパス**。`--dark-mode` を渡すか、GUI の Deck タブで **Dark mode** を有効化するか、`ExportOptions(dark_mode=True)` を設定すると、ダークの post-pass(slide 背景 `#12151B`、本文 `#E5E7EB`)を適用します。
  - `.xlsx` — Papers シート + Query 出典シート、URL / PDF ハイパーリンク、ヘッダー固定、列幅自動調整。列 5(**Source**)は実際の出版場所(例「IEEE Access」)を、列 6(**Indexed via**)はメタデータを返したフェッチャ(例「openalex」)を表示するので、2 つの情報が決して衝突しません。
  - `.md` — 完全なソース / タイトル / 要約リスト。
  - `.bib` — 衝突しない引用キー、LaTeX エスケープ済みフィールド。
  - `.json` — 下流ツーリング用の生ペイロード。
  - `.ris` — Zotero / Mendeley / EndNote / RefWorks が取り込む RIS 交換形式(非 LaTeX の文献管理ソフト向けの BibTeX の兄弟)。
  - `.csv` — スプレッドシート / 手早い grep トリアージ用の 1 論文 1 行のフラットな表(RFC-4180 クオート、タイトル内のカンマが列をずらしません)。
  - `.csl.json` — Pandoc / citeproc 用の CSL-JSON。任意の CSL スタイル(APA、IEEE、Nature、…)で文献目録をレンダリング。`.csl.json` 拡張子でプレーンな `.json` ダンプと区別されます。
- **PPT 編集ツールキット**: `thesisagents.exporters.pptx_edit`(inspect / update_slide / delete_slide / reorder_slides / add_slide)はエクスポータが生成する任意のデッキに対して動作し、加えて同等の `pptx_*` MCP ツールにより LLM エージェントが生成済みデッキ上で反復できます。
- **MCP サーバー**: 13 ツール — `list_sources` + `list_exports`(発見)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`、`export`、および 6 個の `pptx_*` デッキツール(`inspect`、`review`、`update_slide`、`delete_slide`、`reorder_slides`、`add_slide`)。MCP 対応の任意の LLM(Claude Code、Claude Desktop、Cursor、…)がワークフロー全体を駆動できます。
- **2 つのエンリッチパス**(要約を超えて真の論文発表級デッキに至るため):
  - **LLM-as-agent(API キー不要)** — 呼び出し側 LLM が `fetch_pdf_text` で PDF 本文を読み、構造化サマリをコンテキスト内で書き、`export` に渡します。
  - **Python パイプライン(`--enrich`)** — CLI が Anthropic の API を自身で呼びます。デフォルトモデルは `claude-opus-4-7`。
- **可視 Chrome の出版社フロー**: Scholar の SERP、IEEE の `/rest/search`、およびすべての paywalled-PDF ダウンロード(ieeexplore / dl.acm / link.springer / sciencedirect / wiley / oup / nature / science / …)は、`selenium` 経由で本物の可視 Chrome セッション内で実行されます。ユーザーはライブウィンドウで captcha を解いたり SSO を完了したりを一度だけ行い、`THESISAGENTS_CHROME_PROFILE_DIR` が実行間で cookie を永続化します。
- **LLM-as-agent フロー**: MCP ツールが検索、PDF ダウンロード、テキスト抽出を提供します。`scripts/regen_*.py` には、論文ごとにリッチな `PaperSummary` を手書きする再現可能な例が含まれています。
- **OA PDF リゾルバ**: 重複排除後、`pdf_url` の無い各論文は Unpaywall → S2 `openAccessPdf` → arXiv タイトル検索 → CORE.ac.uk(キー設定時)を通過します。IEEE / ACM / Springer / Elsevier 中心のクエリでの典型的な向上: 40〜70 パーセントポイント。
- **デフォルトで安全**: HTTPS-only な HTTP トランスポート、ソースごとのレート制限(トークンバケット)、任意の XML ペイロードには `defusedxml`、パストラバーサル対策済みのエクスポートパス、ユーザー入力に対する `eval` / `exec` / `pickle` の不使用。
- **zh-tw / zh-cn 語彙ガード**: `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary` にある約 244 個の正規表現パターンが、繁体字で書かれた簡体字由来の借用語(例: `內存` → `記憶體`、`魯棒性` → `穩健性`、`軟件` → `軟體`、`緩存` → `快取`)を捕捉します。同じガードが zh-cn ロケール文字列に対して逆方向にも走ります。完全なルールと正規表現カタログは `.claude/agents/rules/language-vocabulary-check.md` にあります。

## クイックスタート

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

arXiv を検索してデッキ + ワークブック + BibTeX を出力(`--query` のデフォルト):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL で単一論文を取得 — デフォルトは `.pptx + .bib`(1 行に `.xlsx` はあまり意味がありません):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

デッキを繁體中文でレンダリング:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM パイプラインによるエンリッチ(Python が自身で Anthropic を呼ぶ — API キー必須):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI フラグ

| フラグ | 用途 |
|---|---|
| `--query` / `-q` | キーワード(`--paper` が無い場合は必須)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID、または IEEE 文書 URL。`--query` と排他。 |
| `--source` / `-s` | カンマ区切りのソースリスト。デフォルト `arxiv`。 |
| `--max` / `-n` | ソースごとの最大件数(1..200)。デフォルト 25。 |
| `--year-from` / `--year-to` | 両端を含む年フィルタ。 |
| `--export` / `-e` | 形式: `pptx,xlsx,md,bib,json,ris,csv,csl` の任意の組合せ。デフォルトはモードによる(下記参照)。 |
| `--out` / `-o` | 出力ディレクトリ。デフォルト `./exports`。 |
| `--filename-stem` | 生成されるファイル名の stem を上書き。 |
| `--no-abstract` | エクスポートから要約内容を除外。 |
| `--lang` / `-l` | デッキ言語: 14 種のいずれか — `en`、`zh-tw`、`zh-cn`、`ja`、`es`、`fr`、`de`、`ko`、`pt`、`ru`、`it`、`vi`、`hi`、`id`。デフォルト `en`。 |
| `--enrich` | 自動エンリッチの fail-loud 版。`ANTHROPIC_API_KEY` と `[intelligence]` extra が必要。(キー設定時は自動エンリッチがデフォルト。) |
| `--lightweight` | エンリッチをスキップし、要約のみのデッキを強制。手早い / 無人運転にのみ使用。**LLM エージェントが駆動する場合は下記の LLM-as-agent フローを優先。** |
| `--llm-model` | エンリッチのデフォルト `claude-opus-4-7` を上書き。 |
| `--no-pdf` | 自動 PDF ダウンロードをスキップ。論文ごとの PPT ゲートも無効化(PDF 無し → 完全な内容無し)。 |
| `--no-oa-resolve` | 重複排除後の OA PDF リゾルバ(Unpaywall + S2 + arXiv + CORE.ac.uk)をスキップ。 |
| `--top-tier-only` | 結果を arXiv + 精選された CS 旗艦ホワイトリスト(S&P、CCS、NDSS、USENIX Security、NeurIPS、ICML、ICSE、…)に限定。デフォルトは無効。 |
| `--paywall-threshold` | 確認プロンプトをトリガする paywalled 結果の割合。デフォルト 0.30。 |
| `--yes` | paywall プロンプトをスキップして続行。 |
| `--max-slides` | 論文ごとのスライド上限(デフォルト 25、0 で無制限)。 |
| `--dark-mode` | pptx をダーク背景 + ほぼ白のテキストでレンダリング。デフォルトはライトの navy バンドデッキ。 |
| `--quiet` | 論文ごとの出力を抑制。 |

### 環境変数

| 変数 | 利用箇所 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 認証。MCP 経由の LLM-as-agent パスでは不要。 |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | デフォルト `claude-opus-4-7` を上書き。 |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA リゾルバ | より高いレート上限。OA リゾルバの S2 `openAccessPdf` ステップでも使用。無料キーは <https://www.semanticscholar.org/product/api>。 |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | NCBI の匿名上限(3/s)を 10/s に引き上げ。任意。 |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex、**Unpaywall** | polite-pool タグ + OA リゾルバの Unpaywall ステップを有効化(IEEE / ACM / Springer / Elsevier の paywalled 論文で最大の PDF カバレッジ向上、典型的な向上は 40〜70 pp)。 |
| `THESISAGENTS_IEEE_API_KEY` | IEEE(API パス) | 公式 IEEE Xplore API。対象論文の `pdf_url` を公開。 |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE は可視 Chrome 経由でデフォルト有効。** `=1` でオプトアウト(例: Chrome の無い CI)。httpx スクレイプ分岐は WebRunner が使えないときのフォールバックとしてのみ実行。 |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 加入者トークン(Bearer ヘッダ)。任意。 |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | 必須。<https://dev.springernature.com/> から無料キー。無いとプラグインは `ConfigError` を送出。 |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar は可視 Chrome 経由でデフォルト有効。** `=1` でオプトアウト(Google の ToS は自動アクセスを禁止するため、カバレッジ優先でデフォルト有効、captcha / IP ブロックのリスクを避けたい場合はオプトアウト)。 |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF ダウンロード | 永続的な Chrome `--user-data-dir`。これを設定して VPN / SSO / Google サインインを一度完了すると、以降の実行は cookie を継承し、IEEE は paywalled メタデータを返し、Scholar は非スロットルの SERP を提供します。 |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF ダウンロード | `=1` で本物の Chrome を駆動する代わりに httpx パスを強制。Chrome バイナリの無い CI / Docker に有用。それ以外は未設定のままに。 |
| `THESISAGENTS_CORE_API_KEY` | OA リゾルバ + `core` 検索ソース | <https://core.ac.uk/services/api> から無料キー。CORE.ac.uk の OA ルックアップステップ(2 億件以上の機関 / 地域 OA アイテム)**と** `core` 検索ソースを有効化。無い場合、`core` ソースは黙ってスキップされ、他の OA 戦略(Unpaywall、S2、arXiv)は引き続き走ります。 |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF ダウンローダ | Netscape 形式の `cookies.txt`。デフォルト無効。機関的アクセス権を持つ出版社にのみ使用。 |
| `THESISAGENTS_LOG_LEVEL` | logger | デフォルト `INFO`、詳細トレースは `DEBUG`。 |

デフォルト: `--query` → `pptx,xlsx,bib`。`--paper` → `pptx,bib`。常に明示的な `--export` で上書き可能。

## LLM-as-agent フロー

エディタ内の LLM がワークフローを駆動する場合、MCP ツールを順に使います: `search`、`download_pdfs`、`fetch_pdf_text`、そして手書きのリッチな `PaperSummary` を伴う `export`。既存の `scripts/regen_*.py` ファイルは、最終的な作成とエクスポートステップの再現可能な例です。

エンドツーエンドの完全なランブック(検索 → リッチデッキ)は `.claude/agents/tasks/paper-summary-author.md` にあります — 新しいクエリを開始する前にこれを開いておくと、LLM はユーザー入力を待たずにフローを実行できます。

## MCP サーバー

Claude Code に登録:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

または settings ファイルに記述:

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

ツール:

| ツール | 用途 |
|---|---|
| `list_sources` | すべてのプラグインを列挙し、現在の env で各々が有効かを報告。`search` の前に一度呼ぶ。 |
| `list_exports` | すべてのエクスポート形式を、その 1 行説明と、集約ファイルを 1 つ書くか論文ごとに 1 ファイルを書くかとともに列挙。 |
| `search` | キーワード → 論文リスト。`top_tier_only`、`min_citations` を受理。デフォルトは API キー不要のソース全体。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 識別子 → 単一論文。 |
| `fetch_pdf_text` | 単一 PDF をダウンロードし、抽出した本文を返す。**MCP 経由で「論文を読んだ」に至る入口。** |
| `download_pdfs` | 論文リストの PDF を `{out_dir}/pdfs/` に一括ダウンロード。BibTeX キーをキーとする論文ごとの結果を返す。 |
| `export` | 論文リスト + 形式 → `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json` を書き出す。リッチな論文発表級スキーマ用の論文ごとの `summary` フィールド、`max_slides_per_paper`(デフォルト 25)、`dark_mode`(デフォルト `false` — プロジェクトのデフォルトはライトの navy バンドデッキ、ダークの OLED / 暗所向け post-pass には `true` を渡す)を受理。 |
| `pptx_inspect` | 既存デッキのスライド / シェイプ構造を読む。 |
| `pptx_review` | 1 回の呼び出しでデッキを監査 — overflow + 色コントラクト + `paper_rule` セクション網羅性。デッキ言語を自動検出。CLI 版は `python -m thesisagents review <deck.pptx>` でも。 |
| `pptx_update_slide` | `title` / `body` / `meta`(シェイプ名経由)または任意のシェイプ(インデックス経由)を置換。 |
| `pptx_delete_slide` | スライドとその part relationship を削除。 |
| `pptx_reorder_slides` | `sldIdLst` 経由でスライドを並べ替え。 |
| `pptx_add_slide` | 新しい title / body / meta スライドを末尾追加または挿入。 |

LLM-as-agent フロー(`ANTHROPIC_API_KEY` 不要 — LLM 自身がエージェント):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

完全な参照は [`docs/mcp.md`](docs/mcp.md)。

## プロジェクト構成

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

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

bandit の `-c` フラグは必須 — 無いと bandit はプロジェクトの skip 設定を無視します。pptx エクスポータを触るときは overflow チェックも実行してください(`CLAUDE.md`「Slide Deck Rules」参照)。

## デスクトップ GUI(PySide6)

ネイティブのデスクトップインターフェースが `[gui]` extra の後ろに同梱されています:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

ウィンドウには 4 つのタブがあります — **Search**、**Settings**(QSettings 経由で API キーを永続化)、**Enrich**(`collection_ready` シグナルを介して LLM-as-agent / Python パイプラインのエンリッチを駆動)、**Deck**(Light モードトグル + スライド上限 + 最大図数のコントロールが `ExportOptions` に流れる)。Windows リリース zip は PySide6 を含む Nuitka コンパイル済みバンドルを同梱するので、別途 Python をインストールせずに `thesisagents.exe gui` が動作します。
**UI は 14 言語すべてで提供**(English、繁體中文、简体中文、日本語、Español、Français、Deutsch、한국어、Português、Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia) — 初回起動は OS ロケールから言語を選び、その後 **Settings → Interface language** で変更できます。デッキ出力言語は別のドロップダウンなので、UI を 1 つの言語で動かしつつ別の言語でスライドを出力できます。レイアウトはレスポンシブ: すべてのフォームが `QScrollArea` に収まり、ウィンドウは 900×600 まで縮小可能(720p にもなお収まる)、HiDPI スケーリングはデフォルトで有効です。

完全な参照: [`docs/gui.md`](docs/gui.md)。

## スタンドアロン実行ファイルとしてのパッケージング

Python がインストールされていなくても動く単一ファイルバイナリを出荷するために、2 つのパッケージャがドキュメント化されています:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — 高速ビルド(1 分未満)、200〜300 MB の出力、2〜4 秒の起動。
  ビルドスクリプトを反復するときに最適。
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  低速ビルド(5〜15 分)、80〜150 MB の出力、1 秒未満の起動、
  いくらかのバイトコード保護。エンドユーザーがバイナリを
  何度も実行するときに最適。

どちらのドキュメントも、プロジェクト固有の落とし穴 — `sources/<name>/` 配下の動的なソースプラグイン — を扱い、CLI と MCP サーバーのエントリポイントに対する検証済みコマンドを同梱しています。

## 継続的インテグレーション & リリース

`.github/workflows/` 配下に 2 つの GitHub Actions ワークフローがあります:

- **`ci.yml`** は `main` へのすべての push と PR で実行。マトリクスは Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14(6 ジョブ)。各ジョブが
  `ruff check`、`bandit -c pyproject.toml`、`pytest` を実行。
- **`release.yml`** は `main` 上で `ci.yml` の完了を待ちます
  (`workflow_run` トリガ)。CI が成功した場合にのみ実行。**`main` への
  CI 成功 push はすべてリリース** — ワークフローがパッチバージョンを
  `pyproject.toml` で自動インクリメントし、その bump を `chore: bump version to X.Y.Z`
  として `main` にコミットバックし、以下をパイプライン化します:
  1. **`bump-version`** — `pyproject.toml` から現在の `X.Y.Z` を読み、
     `X.Y.(Z+1)` にインクリメント、ワークフローの `GITHUB_TOKEN` を使って
     `main` にコミット + push バック。その push は CI を再トリガしません
     (`GITHUB_TOKEN` 駆動の push が新しいワークフロー実行を開始できないという
     GitHub のルールにより)ので、サイクルは自然に終了します。
  2. **`publish-pypi`** — sdist + wheel をビルド、`twine check`、
     `PYPI_API_TOKEN` 経由で `twine upload`。
  3. **`create-draft-release`** — タグ `v<version>` で *draft* の GitHub
     リリースを自動生成ノート付きで開く。
  4. **`build-nuitka`** — Windows ランナーで Nuitka スタンドアロンバンドルを
     コンパイル(エントリポイント: `--python-flag=-m` 経由の
     `python -m thesisagents`)、スモークテスト、結果の
     `thesisagents.dist/` フォルダを zip 化し、その zip + `.sha256`
     チェックサムを draft リリースに添付。設計上スタンドアロン(onefile では
     ない): onefile は起動ごとに `%TEMP%` に自己展開し、起動遅延を加え、
     ロックダウンされたマシンでアンチウイルスのヒューリスティックに引っかかる。
     設計上 Windows 専用でもある: Linux / macOS ユーザーは PyPI から
     インストール。`pyproject.toml` をキーとするビルドキャッシュが、
     ウォームビルドをコールドの約 70 分から約 5〜10 分に短縮。
  5. **`publish-release`** — Nuitka アセットがアップロードされたら draft を
     解除、ユーザーが半端なリリースを見ないように。

  **リリースのスキップ。** コミットメッセージのどこかに `[skip release]` を
  含めると、bump とすべての下流ジョブがスキップされます — バージョン番号を
  消費すべきでない docs のみ / typo / リファクタのコミットに使ってください。

PyPI 公開 + リリース実行ファイルを有効にするには:

1. <https://pypi.org/manage/account/token/> でプロジェクトスコープの
   API トークンを生成。
2. GitHub リポジトリで: `Settings → Secrets and variables → Actions →
   New repository secret`。名前を `PYPI_API_TOKEN` とし、トークン値を
   貼り付け。
3. GitHub Actions が `main` に push できるようにする: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`。bump
   コミットはワークフローの `GITHUB_TOKEN` によって push されます。
4. PR を `main` にマージしてリリースを切る。パイプラインは PyPI 公開まで
   約 3〜5 分、Windows zip の添付までさらに約 50〜70 分(コールド)または
   約 5〜10 分(ウォームな Nuitka キャッシュ)かかります。

`publish-pypi` ジョブは意図的に GitHub Environment を付けません。そのため
各実行は、リポジトリホームの「Deployment」サイドバーウィジェットとしてではなく、
(Nuitka の `.exe` を添付した)Release エントリとして現れます — リリースは
専用のページを持ち、その上の Deployment エントリは冗長なノイズになるだけです。

## ライセンス

`LICENSE` を参照。arXiv API は arXiv の API 利用規約
(<https://info.arxiv.org/help/api/tou.html>)に従って使用します — 3 秒あたり
1 リクエストのソフト上限を遵守してください。同梱のフェッチャは token bucket で
これを既に強制しています。
