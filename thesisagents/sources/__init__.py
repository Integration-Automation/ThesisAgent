"""Built-in source plugins.

Each subpackage exposes a ``fetcher_class`` attribute pointing at a
``Fetcher`` subclass. Plugins are discovered dynamically by
``thesisagents.fetchers.base.load_fetcher(name)`` via
``importlib.import_module(f"thesisagents.sources.{name}")``.

Adding a new source: create ``thesisagents/sources/<name>/__init__.py``
with ``from .fetcher import <Name>Fetcher; fetcher_class = <Name>Fetcher``.
"""
