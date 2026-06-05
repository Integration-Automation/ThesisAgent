ThesisAgents उपयोगकर्ता मार्गदर्शिका
=======================================

कीवर्ड-संचालित शोध-पत्र खोज सहायक। arXiv, Semantic Scholar, OpenAlex,
PubMed, ACM, IEEE Xplore, DBLP, Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE और
Google Scholar से परिणाम लाता है; और इन्हें थीसिस-शैली PowerPoint
प्रस्तुति, Excel वर्कबुक तथा BibTeX फ़ाइल के रूप में निर्यात करता है। एक
CLI कॉल या एक MCP टूल कॉल से सब कुछ।

.. contents:: विषय-सूची
   :depth: 2
   :local:

----

इस परियोजना को चलाने वाले AI एजेंट के लिए
-----------------------------------------

**यदि आप एक LLM (Claude Code, Cursor, Aider, Codex CLI, …) हैं जो यह
जानने के लिए यह दस्तावेज़ पढ़ रहे हैं कि क्या करना है — यहाँ से शुरू
करें।** वही नियम repo की जड़ में ``AGENTS.md`` (एजेंट-क्रॉस मिरर) और
``CLAUDE.md`` (आधिकारिक संदर्भ) में भी फिक्स हैं; गैर-तुच्छ परिवर्तनों
से पहले उन्हें पढ़ें।

**डिफ़ॉल्ट डिलीवरेबल है प्रति शोध-पत्र एक थीसिस-शैली समृद्ध ``.pptx``**,
न कि वह हल्का सार-केवल डेक जो CLI डिफ़ॉल्ट रूप से उत्पन्न करता है। हल्का
आउटपुट एक मध्यवर्ती कलाकृति है — आपका काम इसे उन्नत करना है।

निर्णय वृक्ष
^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` सेट है? → बस CLI चलाएँ; यह Anthropic API के
   माध्यम से स्वचालित रूप से समृद्ध हो जाता है।
2. कुंजी नहीं, LLM चला रहा है → **समृद्ध सारांश आप स्वयं तैयार करें**।
   प्रत्येक PDF पढ़ें, हाथ से ``PaperSummary`` को rich-tier फ़ील्ड्स के
   साथ लिखें, ``scripts/regen_<query>.py`` रखें, चलाएँ। **उपयोगकर्ता से
   API key सेट करने को न कहें** — आप ही LLM हैं।
3. LLM नहीं (CI / cron) → हल्का स्वीकार्य।

MCP 6 चरण
^^^^^^^^^

.. code-block:: text

   1. (वैकल्पिक) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (वैकल्पिक) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # प्रति शोध-पत्र
   5. (आप प्रत्येक PDF पढ़ें और संरचित summary dict तैयार करें)
   6. export(papers=[{...paper, "summary": {...}}], language="hi", ...)

12 MCP उपकरण: :doc:`/mcp`।

अनिवार्य: डिलीवरी से पहले URL / DOI सत्यापन
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

प्रकाशक URL पथ **अनुमान योग्य नहीं हैं** — AAAI संख्यात्मक ID
(``v40i5.37389``) उपयोग करता है, IEEE अपारदर्शी ``arnumber``, ACM
अपारदर्शी DOI। जब आप हाथ से ``Paper`` लिखते हैं, **``url`` / ``doi`` /
``arxiv_id`` को इस खोज द्वारा उत्पन्न xlsx से शब्दशः कॉपी करें** —
कभी स्मृति से नहीं, कभी शीर्षक से निर्मित नहीं।

xlsx ``exports/<run>/<slug>-<timestamp>.xlsx`` में लिखी जाती है, कॉलम
7 = DOI, कॉलम 8 = URL। regen स्क्रिप्ट समाप्त होने पर ऑडिट करें:

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

निषेध
^^^^^

* उपयोगकर्ता से न कहें "``ANTHROPIC_API_KEY`` सेट करें" — आप ही LLM हैं।
* हल्के ``.pptx`` को डिलीवरेबल न मानें।
* ``download_pdfs`` समाप्त होने पर न रुकें।
* शोध-पत्र में अनुपस्थित संख्याएँ, RQ, योगदान, सीमाएँ न गढ़ें।
* URLs / DOIs / arXiv IDs मनगढ़ंत न करें।
* run निर्देशिका में अप्रासंगिक डाउनलोड न छोड़ें। कीवर्ड खोज विषय
  से बाहर के पेपर ला सकती है ("Claude code" क्वेरी ने एक Viterbi
  डिकोडर पेपर खींच लिया)। विषय से बाहर के ``pdfs/<key>.pdf`` और
  हल्के ``<key>.pptx`` को हटा दें; aggregate xlsx / bib को ईमानदार
  रिकॉर्ड के रूप में रखें। पूरी प्रक्रिया ``CLAUDE.md`` के "Pruning
  irrelevant downloads" में।
* कमिट, PR, कोड या डॉक्स में "Claude", "Claude Code", "AI-generated",
  "GPT", "Copilot" या किसी AI टूल/मॉडल का नाम न लिखें।

उदाहरण: ``scripts/regen_llm_security_batch.py`` (en, 8 शोध-पत्र) और
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw)।

----

स्थापना
-------

Python **3.12+** आवश्यक।

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

वैकल्पिक extras: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``।

----

त्वरित शुरुआत
-------------

.. code-block:: bash

   # arXiv खोजें → डेक + वर्कबुक + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # URL से एक शोध-पत्र → डेक + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # डेक हिंदी में रेंडर करें
   thesisagents --paper 1706.03762 --lang hi --out ./exports/

   # Python pipeline समृद्धि (Anthropic key आवश्यक)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang hi --out ./exports/

CLI फ़्लैग की पूरी तालिका: :doc:`/cli`।

----

आगे कहाँ देखें
--------------

* CLI फ़्लैग और पर्यावरण चर: :doc:`/cli`
* 12 MCP सर्वर उपकरण: :doc:`/mcp`
* PPTX संपादन टूलकिट: :doc:`/pptx_editing`
* repo जड़ में ``readmes/README.hi.md`` फ़ाइल में सुविधाओं की पूरी सूची है।
* गहन तकनीकी संदर्भ (प्लगइन वास्तुकला, सुरक्षा नीतियाँ, Definition of
  Done, SonarQube नियम, …) अंग्रेज़ी गाइड में समेकित हैं:
  :doc:`/en/index`।
