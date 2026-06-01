"""Built-in source plugins.

Each subpackage exposes a ``fetcher_class`` attribute pointing at a
``Fetcher`` subclass. Plugins are discovered dynamically by
``autopapertoppt.fetchers.base.load_fetcher(name)`` via
``importlib.import_module(f"autopapertoppt.sources.{name}")``.

Adding a new source: create ``autopapertoppt/sources/<name>/__init__.py``
with ``from .fetcher import <Name>Fetcher; fetcher_class = <Name>Fetcher``.
"""
