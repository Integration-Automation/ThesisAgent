ThesisAgents Documentation
=============================

A keyword-driven paper search assistant that fetches results from
arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref),
IEEE Xplore, DBLP, generic Crossref, OpenAIRE, Springer Nature,
and Google Scholar, normalises them into one record shape, and
exports the deduplicated, ranked set as a thesis-style PowerPoint
deck, an Excel workbook, a BibTeX file, a Markdown summary, and
a JSON dump — from one CLI call, one MCP tool call, or the
desktop GUI.

Languages
---------

The user guide is available in fourteen languages. The
**reference docs** in the next section apply to every language.

.. toctree::
   :maxdepth: 1
   :caption: Languages

   en/index
   zh-tw/index
   zh-cn/index
   ja/index
   es/index
   fr/index
   de/index
   ko/index
   pt/index
   ru/index
   it/index
   vi/index
   hi/index
   id/index

Getting started
---------------

.. toctree::
   :maxdepth: 1
   :caption: First steps

   installation
   configuration

Surfaces
--------

Four ways to drive the project — pick the one that matches your
workflow.

.. toctree::
   :maxdepth: 1
   :caption: Driving the project

   cli
   mcp
   gui
   pptx_editing

Concepts
--------

How the project is wired together and what every record shape
means.

.. toctree::
   :maxdepth: 1
   :caption: Concepts

   architecture
   data_model

Operations
----------

Packaging, releases, and what to do when something breaks.

.. toctree::
   :maxdepth: 1
   :caption: Operations

   packaging-pyinstaller
   packaging-nuitka
   releases
   troubleshooting

Contributing
------------

.. toctree::
   :maxdepth: 1
   :caption: Contributing

   contributing
   source_plugins

Quick links
-----------

* `GitHub repo <https://github.com/Integration-Automation/ThesisAgents>`_
* `PyPI package <https://pypi.org/project/thesisagents/>`_
* `Latest release <https://github.com/Integration-Automation/ThesisAgents/releases/latest>`_
* `Issue tracker <https://github.com/Integration-Automation/ThesisAgents/issues>`_
