# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **भाषाएँ**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · **हिन्दी** · [Bahasa Indonesia](README.id.md)
> **दस्तावेज़ीकरण**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

कीवर्ड-संचालित शोध-पत्र खोज सहायक। arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (Crossref के माध्यम से), IEEE Xplore, DBLP, सामान्य Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE और Google Scholar से परिणाम लाता है; उन्हें एकल रिकॉर्ड प्रारूप में सामान्यीकृत करता है; और डुप्लीकेट-मुक्त समूह को **थीसिस-शैली PowerPoint स्लाइड**, **Excel वर्कबुक** और **BibTeX फ़ाइल** के रूप में निर्यात करता है — एक CLI कॉल या एक MCP टूल कॉल से सब कुछ। वैकल्पिक रूप से प्रत्येक शोध-पत्र को उसकी PDF पढ़कर समृद्ध कर सकता है और संरचित प्रति-शोध-पत्र सारांश तैयार कर सकता है, या तो संदर्भ में (LLM-as-agent पथ) या Anthropic API के माध्यम से (Python pipeline पथ)।

## इस परियोजना को चलाने वाले AI एजेंट के लिए

**यदि आप एक LLM (Claude Code, Cursor, Aider, Codex CLI, …) हैं जो यह जानने के लिए इस README को पढ़ रहे हैं कि क्या करना है — यहाँ से शुरू करें।** नीचे दिया गया सब कुछ [`AGENTS.md`](AGENTS.md) (एजेंट-क्रॉस मिरर) और [`CLAUDE.md`](CLAUDE.md) (आधिकारिक संदर्भ) में भी पिन किया गया है; गैर-तुच्छ परिवर्तनों से पहले उन्हें पढ़ें।

### उपयोगकर्ता वास्तव में क्या चाहता है

डिफ़ॉल्ट डिलीवरेबल है **हर शोध-पत्र के लिए एक थीसिस-शैली समृद्ध `.pptx`**, न कि हल्का सार-केवल डेक जो CLI डिफ़ॉल्ट रूप से उत्पन्न करता है। हल्का आउटपुट एक मध्यवर्ती कलाकृति है — आपका काम उसे उन्नत करना है।

### निर्णय वृक्ष

1. क्या परिवेश में `ANTHROPIC_API_KEY` सेट है? → बस CLI चलाएँ; यह Anthropic API के माध्यम से स्वचालित रूप से समृद्ध हो जाता है। आपका काम हो गया।
2. कुंजी नहीं, लेकिन आप (एक LLM) सत्र चला रहे हैं → **समृद्ध सारांश आप स्वयं तैयार करें**। प्रत्येक PDF पढ़ें, हाथ से rich-tier फ़ील्ड्स (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`) वाला `PaperSummary` लिखें, एक `scripts/regen_<query>.py` रखें और उसे चलाएँ। **उपयोगकर्ता से API key सेट करने को न कहें** — आप ही वह LLM हैं जो सारांश लिख सकता था।
3. लूप में कोई LLM नहीं (CI / cron / अनदेखा) → हल्का आउटपुट स्वीकार्य।

### MCP 6-चरण कार्यप्रवाह

```
1. (वैकल्पिक) list_sources()                              # कौन से plugin सक्षम हैं
2. search(keywords, sources, top_tier_only=true, ...)
3. (वैकल्पिक) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # प्रति शोध-पत्र
5. (आप प्रत्येक PDF पढ़ें और एक संरचित सारांश dict तैयार करें)
6. export(papers=[{...paper, "summary": {...}}], language="hi", ...)
```

सभी तेरह MCP उपकरण (`list_sources`, `list_exports`, `download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` / `pptx_add_slide` / आदि सहित) [`docs/mcp.md`](docs/mcp.md) में प्रलेखित हैं।

### अनिवार्य: डिलीवरी से पहले URL / DOI सत्यापन

प्रकाशक URL पथ **अनुमान योग्य नहीं हैं** — AAAI संख्यात्मक ID (`v40i5.37389`) उपयोग करता है, IEEE एक अपारदर्शी `arnumber`, ACM अपारदर्शी DOI। जब आप हाथ से एक `Paper` लिखते हैं, **`url` / `doi` / `arxiv_id` को उस search xlsx से शब्दशः कॉपी करें जिसने इस रन को उत्पन्न किया** — कभी स्मृति से नहीं, कभी शीर्षक से निर्मित नहीं।

xlsx `exports/<run>/<slug>-<timestamp>.xlsx` में लिखी जाती है, कॉलम 7 = DOI, कॉलम 8 = URL। समाप्त होने पर अपनी regen स्क्रिप्ट का ऑडिट करें:

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

प्रोडक्शन में इसी तरीके से पकड़े गए दो कूट: गलत AAAI खंड (`v39i23.34521` बनाम वास्तविक `v39i22.34537`) और मनगढ़ंत लेखक-स्लग पथ (`v40i5.37389` के बजाय `view/fang2026`)।

### अनिवार्य: डिलीवरी से पहले अप्रासंगिक डाउनलोड हटाएँ

खोज कीवर्ड मिलान कीवर्ड-आधारित है, इसलिए विषय से बाहर के पेपर घुस आएँगे: एक "Claude code" क्वेरी ने एक Viterbi-decoder पेपर लौटाया क्योंकि दोनों में "code" है; "LLM code review" एक object-detection साहित्य समीक्षा से मेल खा गया। एक बार जब आप सार पढ़ लें और किसी पेपर को उपयोगकर्ता के वास्तविक इरादे के लिए विषय से बाहर वर्गीकृत करें, तो run निर्देशिका से उसे हटाएँ:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

`exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx` हटाएँ। aggregate `<slug>-<timestamp>.xlsx` / `.bib` को **रखें** — वे इस बात का ईमानदार रिकॉर्ड हैं कि खोज ने क्या लौटाया। सीमांत मामलों को समृद्ध सारांश मिलता है; किसी संभावित मिलान को चुपचाप गिराने की तुलना में अधिक-शामिल करना बेहतर है।

### कार्यान्वित उदाहरण

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) में ठीक इसी प्रक्रिया से हाथ से लिखा एक समृद्ध सारांश है (एकल शोध-पत्र, rich-tier, zh-tw, हर समृद्ध फ़ील्ड भरा हुआ)। बहु-शोध-पत्र खोज इसी आकार का अनुसरण करती है — `PaperCollection` tuple में प्रति शोध-पत्र एक `Paper(...summary=PaperSummary(...))` प्रविष्टि।

### निषेध

- **न** किसी बहु-शोध-पत्र खोज को यह कहकर समाप्त करें कि "समृद्ध डेक के लिए `ANTHROPIC_API_KEY` सेट करें" — आप ही वह LLM हैं जो सारांश लिख सकता था।
- **न** प्रति-शोध-पत्र हल्के `.pptx` को डिलीवरेबल मानें।
- **न** जब `download_pdfs` "N PDF सहेजे" रिपोर्ट करे तब रुकें — यह समृद्ध-लेखन चरण का आरंभ है, अंत नहीं।
- **न** शोध-पत्र में अनुपस्थित संख्याएँ, RQ, योगदान या सीमाएँ गढ़ें।
- **न** URLs / DOIs / arXiv IDs मनगढ़ंत करें — ऊपर दिया नियम देखें।
- **न** run निर्देशिका में अप्रासंगिक डाउनलोड छोड़ें। कीवर्ड खोज मिलान में विषय से बाहर के पेपर शामिल हो सकते हैं (एक "Claude code" क्वेरी ने एक Viterbi-decoder पेपर खींच लिया; "LLM code review" ने एक object-detection साहित्य समीक्षा खींच ली)। पेपरों को विषय से बाहर वर्गीकृत करने के बाद, उनके `pdfs/<key>.pdf` और हल्के `<key>.pptx` हटाएँ; aggregate xlsx / bib को खोज ने क्या लौटाया इसके ईमानदार रिकॉर्ड के रूप में रखें।
- **न** commit संदेश, PR विवरण, कोड टिप्पणी या प्रलेखन में "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" या किसी AI टूल/मॉडल नाम का उल्लेख करें।

## विशेषताएँ

- **पंद्रह प्लग-इन योग्य स्रोत**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (Crossref-scoped), `dblp`, `crossref` (unscoped), `openaire`, `springer` (API key आवश्यक), `europepmc` (खुला, कोई key नहीं — जीव-विज्ञान + preprints + कृषि), `doaj` (खुला, कोई key नहीं — open-access जर्नल, आमतौर पर सीधे PDF लिंक के साथ), `hal` (खुला, कोई key नहीं — फ़्रांस का CS / गणित / भौतिकी संग्रह, full-text PDFs सहित), `core` (मुफ़्त API key आवश्यक — सबसे बड़ा open-access aggregator, 250M+ रचनाएँ), `ieee` (दृश्यमान Chrome के माध्यम से डिफ़ॉल्ट-चालू; API key आधिकारिक Xplore API जोड़ता है), `scholar` (दृश्यमान Chrome के माध्यम से डिफ़ॉल्ट-चालू)। प्रत्येक `sources/<name>/` के अंतर्गत एक `Fetcher` एडाप्टर के पीछे रहता है। परिणामों को प्रमुख CS सम्मेलनों/जर्नलों + Nature/Science/PNAS तक फ़िल्टर करने के लिए `--top-tier-only` पास करें। डिफ़ॉल्ट खोज सभी वेन्यू रखती है।
- **एकल-शोध-पत्र मोड**: एक arXiv ID, arXiv URL, DOI, PMID, या IEEE दस्तावेज़ URL चिपकाएँ — ThesisAgents इसे सही स्रोत के माध्यम से हल करता है और वही निर्यात बंडल जारी करता है। पठन नोट्स और थीसिस रक्षा की तैयारी के लिए उपयोगी।
- **स्थानीय PDF मोड** (`--pdf <path>`): एक PDF या एक निर्देशिका पास करें। एक हेयूरिस्टिक एक्सट्रैक्टर प्रत्येक PDF के आरंभिक पृष्ठों से **शीर्षक, लेखक, वर्ष, arXiv ID, DOI और वास्तविक सार** सीधे निकालता है (स्पष्ट `Abstract` / `ABSTRACT` / `摘要` हेडर पर एंकर, एक अंधे उपसर्ग पर नहीं)। `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` एकल-PDF कॉल पर ओवरराइड करते हैं; एक निर्देशिका पर, प्रति-फ़ाइल निष्कर्षण जीतता है — इसलिए हर शोध-पत्र को अपनी BibTeX कुंजी के नाम पर अपना डेक मिलता है।
- **आठ एक्सपोर्टर**:
  - `.pptx` — 16:9 वाइडस्क्रीन, पृष्ठ-संख्यित, तीन रेंडरिंग स्तर (हल्का केवल-सार · enriched-flat · **थीसिस-शैली** दर्द-बिंदु चतुष्कोण, KPI कॉलआउट, तकनीक-तुलना तालिकाएँ, प्रति-RQ परिणाम तालिकाएँ, योगदान सारांश, मूल अवलोकन, सीमाएँ & भविष्य कार्य, Q&A, संदर्भ के साथ)। सभी टेम्पलेट स्ट्रिंग्स **14 भाषाओं** में i18n हैं: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia।
  - **डिज़ाइन किए गए डेक की विज़ुअल पहचान** (डिफ़ॉल्ट Calibri-on-white रूप नहीं): प्रति-भाषा टाइपोग्राफी (Latin के लिए Inter, CJK + Hindi के लिए Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI), प्रोग्रामेटिक accent geometry (हर content slide के ऊपर accent bar + cover के बाएँ band), academic-style table formatting (डिफ़ॉल्ट grid हटाई गई, navy header rule, soft inter-row dividers, alternating row stripe, middle-vertical alignment, bold row labels), और एक पाँच-रंगी palette अनुशासन (navy / teal / grey / light / white) जिसमें टेक्स्ट के लिए लाल **प्रतिबंधित** है (emphasis के लिए इसके बजाय bold + teal `#0E7490` उपयोग करें)।
  - **Light mode डिफ़ॉल्ट render पथ है।** dark post-pass लागू करने के लिए `--dark-mode` पास करें, GUI Deck tab में **Dark mode** सक्षम करें, या `ExportOptions(dark_mode=True)` सेट करें (slide background `#12151B`, body text `#E5E7EB`)।
  - `.xlsx` — Papers शीट + Query प्रोवेनेंस शीट, हाइपरलिंक्ड URL / PDF, फ़्रोज़न हेडर, स्वचालित कॉलम चौड़ाई। कॉलम 5 (**Source**) वास्तविक प्रकाशन स्थान (जैसे "IEEE Access") दिखाता है; कॉलम 6 (**Indexed via**) दिखाता है कि किस fetcher ने मेटाडेटा लौटाया (जैसे "openalex"), ताकि दोनों जानकारियाँ कभी न टकराएँ।
  - `.md` — पूर्ण स्रोत / शीर्षक / सार सूची।
  - `.bib` — टकराव-मुक्त उद्धरण कुंजियाँ, LaTeX-एस्केप्ड फ़ील्ड्स।
  - `.json` — डाउनस्ट्रीम टूलिंग के लिए कच्चा payload।
  - `.ris` — RIS इंटरचेंज जिसे Zotero / Mendeley / EndNote / RefWorks आयात करते हैं (गैर-LaTeX संदर्भ प्रबंधकों के लिए BibTeX का समकक्ष)।
  - `.csv` — spreadsheets / त्वरित grep छँटाई के लिए flat एक-पंक्ति-प्रति-शोध-पत्र तालिका (RFC-4180 quoting, इसलिए शीर्षकों में अल्पविराम कभी कॉलम नहीं खिसकाते)।
  - `.csl.json` — Pandoc / citeproc के लिए CSL-JSON; किसी भी CSL शैली (APA, IEEE, Nature, …) में bibliography रेंडर करें। `.csl.json` एक्सटेंशन इसे सादे `.json` dump से अलग रखता है।
- **PPT संपादन टूलकिट**: `thesisagents.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) एक्सपोर्टर द्वारा उत्पन्न किसी भी डेक पर काम करता है, साथ ही समकक्ष `pptx_*` MCP उपकरण ताकि एक LLM एजेंट उत्पन्न डेक पर पुनरावृत्ति कर सके।
- **MCP सर्वर**: 13 उपकरण — `list_sources` + `list_exports` (खोज/सूची), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, और छह `pptx_*` डेक उपकरण (`inspect`, `review`, `update_slide`, `delete_slide`, `reorder_slides`, `add_slide`)। किसी भी MCP-अनुकूल LLM (Claude Code, Claude Desktop, Cursor, …) को पूरा कार्यप्रवाह संचालित करने देता है।
- **दो समृद्धि पथ** सार से आगे एक वास्तविक थीसिस-शैली डेक तक जाने के लिए:
  - **LLM-as-agent (कोई API key नहीं)** — कॉलिंग LLM `fetch_pdf_text` के माध्यम से PDF मुख्य पाठ पढ़ता है, संदर्भ में एक संरचित सारांश लिखता है, और उसे `export` को पास करता है।
  - **Python pipeline (`--enrich`)** — CLI स्वयं Anthropic का API कॉल करती है; डिफ़ॉल्ट मॉडल `claude-opus-4-7`।
- **दृश्यमान-Chrome प्रकाशक प्रवाह**: Scholar SERP, IEEE `/rest/search`, और हर paywalled-PDF डाउनलोड (ieeexplore / dl.acm / link.springer / sciencedirect / wiley / oup / nature / science / …) `selenium` के माध्यम से एक वास्तविक दृश्यमान Chrome सत्र के भीतर चलते हैं। उपयोगकर्ता लाइव विंडो में एक बार captcha हल करता है / SSO पूरा करता है; `THESISAGENTS_CHROME_PROFILE_DIR` कुकीज़ को रनों के बीच बनाए रखता है।
- **LLM-as-agent प्रवाह**: MCP उपकरण खोज, PDF डाउनलोड और पाठ निष्कर्षण प्रदान करते हैं। `scripts/regen_*.py` में प्रति शोध-पत्र एक समृद्ध `PaperSummary` हाथ से लिखने के पुनरुत्पाद्य उदाहरण हैं।
- **OA PDF resolver**: dedup के बाद, `pdf_url` रहित हर शोध-पत्र Unpaywall → S2 `openAccessPdf` → arXiv शीर्षक खोज → CORE.ac.uk (जब keys सेट हों) से गुज़रता है। IEEE / ACM / Springer / Elsevier-भारी क्वेरियों पर विशिष्ट वृद्धि: 40-70 प्रतिशत-अंक।
- **डिफ़ॉल्ट रूप से सुरक्षित**: HTTPS-only HTTP परिवहन, प्रति-स्रोत दर सीमा (token bucket), किसी भी XML payload के लिए `defusedxml`, path-traversal-सुरक्षित निर्यात पथ, उपयोगकर्ता इनपुट पर कोई `eval` / `exec` / `pickle` नहीं।
- **zh-tw / zh-cn शब्दावली रक्षक**: `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary` में ~244 regex पैटर्न पारंपरिक हांज़ी में रेंडर किए गए सरलीकृत-चीनी उधार शब्द पकड़ते हैं (जैसे `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`, `緩存` → `快取`)। वही रक्षक zh-cn locale स्ट्रिंग्स के लिए उलटा चलता है। पूर्ण नियम + regex कैटलॉग `.claude/agents/rules/language-vocabulary-check.md` में हैं।

## त्वरित शुरुआत

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# dev extras के साथ इंस्टॉल (MCP SDK और intelligence deps भी आते हैं)
pip install -e .[dev]
```

arXiv खोजें और डेक + वर्कबुक + BibTeX निर्यात करें (`--query` के लिए डिफ़ॉल्ट):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL से एक शोध-पत्र लाएँ — डिफ़ॉल्ट `.pptx + .bib` (एक पंक्ति के लिए `.xlsx` कम अर्थपूर्ण है):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

डेक को हिंदी में रेंडर करें:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang hi --out .\exports\
```

LLM-pipeline समृद्धि (Python स्वयं Anthropic कॉल करता है — API key आवश्यक):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang hi --out .\exports\
```

## CLI फ़्लैग्स

| फ़्लैग | उद्देश्य |
|---|---|
| `--query` / `-q` | कीवर्ड (`--paper` न हो तो अनिवार्य)। |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID, या IEEE दस्तावेज़ URL। `--query` के साथ परस्पर अनन्य। |
| `--source` / `-s` | अल्पविराम-पृथक स्रोत सूची। डिफ़ॉल्ट `arxiv`। |
| `--max` / `-n` | प्रति स्रोत अधिकतम परिणाम (1..200)। डिफ़ॉल्ट 25। |
| `--year-from` / `--year-to` | समावेशी वर्ष फ़िल्टर। |
| `--export` / `-e` | प्रारूप: `pptx,xlsx,md,bib,json,ris,csv,csl` में से कोई भी। डिफ़ॉल्ट मोड पर निर्भर (नीचे देखें)। |
| `--out` / `-o` | आउटपुट निर्देशिका। डिफ़ॉल्ट `./exports`। |
| `--filename-stem` | उत्पन्न फ़ाइल नाम stem ओवरराइड करें। |
| `--no-abstract` | निर्यात से सार सामग्री छोड़ें। |
| `--lang` / `-l` | डेक भाषा: 14 में से एक — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`। डिफ़ॉल्ट `en`। |
| `--enrich` | auto-enrich का fail-loud संस्करण। `ANTHROPIC_API_KEY` और `[intelligence]` extra आवश्यक। (key सेट होने पर auto-enrich डिफ़ॉल्ट है।) |
| `--lightweight` | समृद्धि छोड़ें + केवल-सार डेक के लिए बाध्य करें। केवल त्वरित / अनदेखी रनों के लिए उपयोग करें; **जब कोई LLM एजेंट चला रहा हो, नीचे दिए LLM-as-agent पथ को प्राथमिकता दें**। |
| `--llm-model` | समृद्धि के लिए डिफ़ॉल्ट `claude-opus-4-7` ओवरराइड करें। |
| `--no-pdf` | स्वचालित PDF डाउनलोड छोड़ें। प्रति-शोध-पत्र PPT गेट भी अक्षम करता है (कोई PDF नहीं → कोई पूर्ण सामग्री नहीं)। |
| `--no-oa-resolve` | dedup-के-बाद OA PDF resolver (Unpaywall + S2 + arXiv + CORE.ac.uk) छोड़ें। |
| `--top-tier-only` | परिणामों को arXiv + एक क्यूरेटेड CS-flagship श्वेतसूची (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …) तक सीमित करें। डिफ़ॉल्ट बंद। |
| `--paywall-threshold` | paywalled परिणामों का अनुपात जो पुष्टिकरण प्रॉम्प्ट ट्रिगर करता है। डिफ़ॉल्ट 0.30। |
| `--yes` | paywall प्रॉम्प्ट छोड़ें और आगे बढ़ें। |
| `--max-slides` | प्रति-शोध-पत्र स्लाइड सीमा (डिफ़ॉल्ट 25; असीमित के लिए 0 पास करें)। |
| `--dark-mode` | pptx को गहरे पृष्ठभूमि + लगभग-सफ़ेद टेक्स्ट के साथ render करें। डिफ़ॉल्ट हल्का navy-band डेक है। |
| `--quiet` | प्रति-शोध-पत्र प्रिंटआउट दबाएँ। |

### पर्यावरण चर

| चर | उपयोग | उद्देश्य |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM प्रमाणीकरण। MCP पर LLM-as-agent पथ के लिए आवश्यक नहीं। |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | डिफ़ॉल्ट `claude-opus-4-7` ओवरराइड करें। |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA resolver | उच्च दर सीमा; OA resolver के S2 `openAccessPdf` चरण द्वारा भी उपयोग किया जाता है। मुफ़्त key <https://www.semanticscholar.org/product/api> पर। |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | NCBI की अनाम सीमा (3/s) को 10/s तक बढ़ाता है। वैकल्पिक। |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Polite-pool टैग + OA resolver का Unpaywall चरण सक्षम करता है (IEEE / ACM / Springer / Elsevier-paywalled पेपरों के लिए सबसे बड़ा PDF-कवरेज लाभ; विशिष्ट वृद्धि 40-70 pp)। |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (API पथ) | आधिकारिक IEEE Xplore API; दायरे में आने वाले पेपरों के लिए `pdf_url` उजागर करता है। |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE दृश्यमान Chrome के माध्यम से डिफ़ॉल्ट-चालू है।** opt-out के लिए `=1` सेट करें (जैसे Chrome रहित CI)। httpx scrape शाखा केवल WebRunner अनुपलब्ध होने पर fallback के रूप में चलती है। |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus ग्राहक टोकन (Bearer हेडर)। वैकल्पिक। |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | आवश्यक; मुफ़्त key <https://dev.springernature.com/> से। इसके बिना plugin `ConfigError` उठाता है। |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar दृश्यमान Chrome के माध्यम से डिफ़ॉल्ट-चालू है।** opt-out के लिए `=1` सेट करें (Google की ToS स्वचालित पहुँच निषेध करती है — कवरेज के लिए डिफ़ॉल्ट-चालू, captcha / IP-block जोखिम से बचने के लिए opt-out)। |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF डाउनलोड | Persistent Chrome `--user-data-dir`। इसे सेट करें और एक बार VPN / SSO / Google sign-in पूरा करें; बाद के रन कुकीज़ विरासत में लेते हैं ताकि IEEE paywalled मेटाडेटा लौटाए और Scholar un-throttled SERPs दे। |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF डाउनलोड | `=1` वास्तविक Chrome चलाने के बजाय httpx पथ बाध्य करता है। Chrome binary रहित CI / Docker के लिए उपयोगी; अन्यथा unset छोड़ें। |
| `THESISAGENTS_CORE_API_KEY` | OA resolver + `core` search source | मुफ़्त key <https://core.ac.uk/services/api> से। CORE.ac.uk OA-lookup चरण (200M+ संस्थागत / क्षेत्रीय OA आइटम) **और** `core` search source सक्षम करता है। इसके बिना, `core` source चुपचाप छोड़ दिया जाता है और अन्य OA रणनीतियाँ (Unpaywall, S2, arXiv) फिर भी चलती हैं। |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF डाउनलोडर | Netscape `cookies.txt`। डिफ़ॉल्ट बंद। केवल उन प्रकाशकों के साथ उपयोग करें जिनके लिए आपके पास संस्थागत अधिकार हैं। |
| `THESISAGENTS_LOG_LEVEL` | logger | डिफ़ॉल्ट `INFO`; विस्तृत ट्रेसिंग के लिए `DEBUG`। |

डिफ़ॉल्ट: `--query` → `pptx,xlsx,bib`। `--paper` → `pptx,bib`। हमेशा स्पष्ट `--export` से ओवरराइड किया जा सकता है।

## LLM-as-agent प्रवाह

जब आपके एडिटर में कोई LLM कार्यप्रवाह चलाता है, MCP उपकरणों को क्रम में उपयोग करें: `search`, `download_pdfs`, `fetch_pdf_text`, फिर हाथ से लिखे समृद्ध `PaperSummary` के साथ `export`। मौजूदा `scripts/regen_*.py` फ़ाइलें अंतिम लेखन और निर्यात चरण के लिए पुनरुत्पाद्य उदाहरण हैं।

पूर्ण एंड-टू-एंड रनबुक (खोज → समृद्ध डेक) `.claude/agents/tasks/paper-summary-author.md` में है — किसी नई क्वेरी से पहले इसे खोलें ताकि LLM उपयोगकर्ता इनपुट के लिए रुके बिना प्रवाह चला सके।

## MCP सर्वर

Claude Code के साथ पंजीकृत करें:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

या अपनी सेटिंग्स फ़ाइल में लिखें:

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

उपकरण:

| उपकरण | उद्देश्य |
|---|---|
| `list_sources` | प्रत्येक plugin की गणना करें + रिपोर्ट करें कि वर्तमान env में प्रत्येक सक्षम है या नहीं। `search` से पहले इसे एक बार कॉल करें। |
| `list_exports` | प्रत्येक निर्यात प्रारूप की एक-पंक्ति व्याख्या + यह एक aggregate फ़ाइल लिखता है या प्रति-शोध-पत्र एक फ़ाइल, इसके साथ गणना करें। |
| `search` | कीवर्ड → शोध-पत्रों की सूची। `top_tier_only`, `min_citations` स्वीकार करता है; डिफ़ॉल्ट पूर्ण API-key-रहित स्रोत मिश्रण। |
| `fetch_paper` | arXiv / DOI / PMID / IEEE पहचानकर्ता → एकल शोध-पत्र। |
| `fetch_pdf_text` | एक PDF डाउनलोड करें, निकाला गया मुख्य पाठ लौटाएँ। **"मैंने शोध-पत्र पढ़ा" तक का MCP पथ।** |
| `download_pdfs` | एक शोध-पत्र सूची की PDFs को `{out_dir}/pdfs/` में बैच-डाउनलोड करें। BibTeX कुंजी द्वारा अनुक्रमित प्रति-शोध-पत्र परिणाम लौटाता है। |
| `export` | शोध-पत्र सूची + प्रारूप → `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json` लिखता है। rich थीसिस-शैली schema के लिए प्रति-शोध-पत्र `summary` फ़ील्ड, `max_slides_per_paper` (डिफ़ॉल्ट 25), और `dark_mode` (डिफ़ॉल्ट `false` — परियोजना डिफ़ॉल्ट हल्का navy-band डेक है, dark OLED / low-light post-pass के लिए `true` पास करें) स्वीकार करता है। |
| `pptx_inspect` | मौजूदा डेक की स्लाइड / शेप संरचना पढ़ें। |
| `pptx_review` | एक ही कॉल में डेक ऑडिट करें — overflow + रंग अनुबंध + `paper_rule` अनुभाग पूर्णता। डेक भाषा स्वतः पहचानता है; CLI `python -m thesisagents review <deck.pptx>` भी। |
| `pptx_update_slide` | `title` / `body` / `meta` (शेप नाम से) या मनमाने शेप (अनुक्रमणिका से) प्रतिस्थापित करें। |
| `pptx_delete_slide` | एक स्लाइड और उसका part relationship हटाएँ। |
| `pptx_reorder_slides` | `sldIdLst` के माध्यम से स्लाइडों को क्रमबद्ध करें। |
| `pptx_add_slide` | एक नई title / body / meta स्लाइड अंत में जोड़ें या डालें। |

LLM-as-agent प्रवाह (`ANTHROPIC_API_KEY` की आवश्यकता नहीं — LLM ही एजेंट है):

```
1. (वैकल्पिक) list_sources()                       # सक्षम plugins खोजें
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (वैकल्पिक) download_pdfs(papers, out_dir="./exports/...")  # PDFs संग्रहीत करें
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # प्रति शोध-पत्र
5. (LLM मुख्य पाठ पढ़ता है, एक संरचित `summary` dict तैयार करता है)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="hi", formats=["pptx","bib"], dark_mode=true, ...)
```

पूर्ण संदर्भ [`docs/mcp.md`](docs/mcp.md) में।

## परियोजना संरचना

```
ThesisAgents/
├── thesisagents/                 # मुख्य पैकेज
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (थीसिस-शैली) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # PDF fetch + Anthropic summariser  ([intelligence] extra)
│   ├── evaluation/                  # ऑफ़लाइन search-quality benchmark (docs/search-quality.md)
│   ├── mcp/                         # FastMCP सर्वर (13 उपकरण)
│   ├── sources/<name>/              # plugin फ़ोल्डर: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── tests/                           # pytest सूट + रिकॉर्डेड fixtures (कोई लाइव HTTP नहीं)
├── docs/                            # Sphinx (14 भाषा वृक्ष)
├── scripts/                         # एक-बार regen स्क्रिप्ट
└── pyproject.toml                   # ruff, bandit, build, वैकल्पिक extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

bandit पर `-c` फ़्लैग आवश्यक है — इसके बिना bandit परियोजना के skip कॉन्फ़िगरेशन को अनदेखा करता है। pptx एक्सपोर्टर को छूते समय, एक overflow जाँच भी चलाएँ (`CLAUDE.md` "Slide Deck Rules" देखें)।

## डेस्कटॉप GUI (PySide6)

`[gui]` extra के पीछे एक नेटिव डेस्कटॉप इंटरफ़ेस आता है:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # या: thesisagents gui
```

विंडो में चार tab हैं — **Search**, **Settings** (QSettings के माध्यम से API keys बनाए रखता है), **Enrich** (एक `collection_ready` सिग्नल पर LLM-as-agent / Python-pipeline समृद्धि चलाता है), और **Deck** (Light mode toggle + slide-cap + max-figures नियंत्रण `ExportOptions` तक प्रवाहित होते हैं)। Windows रिलीज़ zip में PySide6 सहित Nuitka-compiled बंडल आता है, इसलिए `thesisagents.exe gui` एक अलग Python इंस्टॉल के बिना काम करता है।
**UI सभी 14 भाषाओं में आता है** (English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — पहला रन आपके OS locale से भाषा चुनता है, फिर **Settings → Interface language** आपको इसे बदलने देता है। डेक आउटपुट भाषा एक अलग dropdown है ताकि आप UI को एक भाषा में चला सकें और स्लाइड दूसरी में जारी कर सकें। लेआउट उत्तरदायी है: हर फ़ॉर्म एक `QScrollArea` में बैठता है और विंडो 900×600 तक नीचे resize होती है (फिर भी 720p में फ़िट), डिफ़ॉल्ट रूप से HiDPI स्केलिंग चालू के साथ।

पूर्ण संदर्भ: [`docs/gui.md`](docs/gui.md)।

## एक स्टैंडअलोन निष्पादन योग्य के रूप में पैकेजिंग

Python इंस्टॉल के बिना चलने वाला एकल-फ़ाइल बाइनरी शिप करने के लिए दो packagers प्रलेखित हैं:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)** — तेज़ build (एक मिनट से कम), 200–300 MB आउटपुट, 2–4 s स्टार्टअप। तब सबसे अच्छा जब आप build स्क्रिप्ट पर पुनरावृत्ति करते हैं।
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** — धीमा build (5–15 मिनट), 80–150 MB आउटपुट, उप-सेकंड स्टार्टअप, कुछ bytecode सुरक्षा। तब सबसे अच्छा जब अंतिम उपयोगकर्ता बाइनरी को कई बार चलाते हैं।

दोनों docs परियोजना-विशिष्ट पेच को कवर करते हैं — `sources/<name>/` के अंतर्गत dynamic source plugins — और CLI तथा MCP सर्वर प्रवेश-बिंदुओं के लिए एक सत्यापित कमांड शिप करते हैं।

## सतत एकीकरण & रिलीज़

`.github/workflows/` के अंतर्गत दो GitHub Actions workflow रहते हैं:

- **`ci.yml`** `main` पर हर push और PR पर चलता है। Matrix है Ubuntu + Windows × Python 3.12 / 3.13 / 3.14 (6 jobs)। प्रत्येक job `ruff check`, `bandit -c pyproject.toml`, और `pytest` चलाता है।
- **`release.yml`** `main` पर `ci.yml` के पूरा होने की प्रतीक्षा करता है (`workflow_run` trigger)। यह केवल तभी चलता है जब CI सफल हुआ हो। **`main` पर हर CI-सफलता push एक रिलीज़ है** — workflow `pyproject.toml` में patch संस्करण को स्वतः बढ़ाता है, bump को `chore: bump version to X.Y.Z` के रूप में `main` पर वापस commit करता है, और pipeline चलाता है:
  1. **`bump-version`** — `pyproject.toml` से वर्तमान `X.Y.Z` पढ़ें, `X.Y.(Z+1)` तक बढ़ाएँ, workflow `GITHUB_TOKEN` का उपयोग करके `main` पर commit + push करें। वह push CI को फिर से trigger नहीं करता (GitHub के नियम के अनुसार कि `GITHUB_TOKEN`-चालित push नए workflow रन शुरू नहीं कर सकते), इसलिए चक्र स्वाभाविक रूप से समाप्त होता है।
  2. **`publish-pypi`** — sdist + wheel build करें, `twine check`, `PYPI_API_TOKEN` के माध्यम से `twine upload`।
  3. **`create-draft-release`** — auto-generated notes के साथ tag `v<version>` पर एक *draft* GitHub रिलीज़ खोलें।
  4. **`build-nuitka`** — एक Windows runner पर एक Nuitka standalone बंडल compile करें (प्रवेश-बिंदु: `--python-flag=-m` के माध्यम से `python -m thesisagents`), उसे smoke-test करें, परिणामी `thesisagents.dist/` फ़ोल्डर को zip करें, और zip + एक `.sha256` checksum को draft रिलीज़ से attach करें। डिज़ाइन के अनुसार standalone (onefile नहीं): onefile हर launch पर `%TEMP%` में स्वयं-extract होता है, स्टार्टअप विलंब जोड़ता है और locked-down मशीनों पर antivirus heuristics को trigger करता है। डिज़ाइन के अनुसार Windows-only भी: Linux / macOS उपयोगकर्ता PyPI से इंस्टॉल करते हैं। `pyproject.toml` पर keyed build cache warm builds को ~70 मिनट cold से ~5–10 मिनट तक घटाता है।
  5. **`publish-release`** — Nuitka asset अपलोड होने पर draft को unmark करें, ताकि उपयोगकर्ता कभी अधूरी रिलीज़ न देखें।

  **एक रिलीज़ छोड़ना।** commit संदेश में कहीं भी `[skip release]` शामिल करें और bump + हर downstream job छोड़ दिया जाता है — इसे docs-only / typo / refactor commits के लिए उपयोग करें जिन्हें एक संस्करण संख्या नहीं जलानी चाहिए।

PyPI publishing + रिलीज़ निष्पादन योग्य सक्षम करने के लिए:

1. <https://pypi.org/manage/account/token/> पर एक project-scoped API token उत्पन्न करें।
2. GitHub repo में: `Settings → Secrets and variables → Actions → New repository secret`। इसे `PYPI_API_TOKEN` नाम दें और token मान पेस्ट करें।
3. GitHub Actions को `main` पर push करने की अनुमति दें: `Settings → Actions → General → Workflow permissions → Read and write permissions`। bump commit workflow के `GITHUB_TOKEN` द्वारा push किया जाता है।
4. `main` में PRs मर्ज करके रिलीज़ करें। pipeline को PyPI पर publish करने में ~3–5 मिनट और Windows zip attach होने में ~50–70 मिनट अधिक (cold) या ~5–10 मिनट (warm Nuitka cache) लगते हैं।

`publish-pypi` job जानबूझकर कोई GitHub Environment attach नहीं करता, इसलिए प्रत्येक रन repo home पर एक "Deployment" sidebar widget के बजाय एक Release प्रविष्टि (अपने Nuitka `.exe` attached के साथ) के रूप में दिखता है — रिलीज़ को अपना समर्पित पृष्ठ मिलता है और शीर्ष पर एक Deployment प्रविष्टि बस अनावश्यक शोर होगी।

## लाइसेंस

`LICENSE` देखें। arXiv API arXiv की API उपयोग शर्तों (<https://info.arxiv.org/help/api/tou.html>) के तहत उपयोग की जाती है — हर 3 सेकंड में 1 अनुरोध की सॉफ्ट सीमा का पालन करें; बंडल किया गया fetcher पहले से ही अपने token bucket के माध्यम से इसे लागू करता है।
