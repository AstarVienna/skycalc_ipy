# -*- coding: utf-8 -*-
"""Sphinx configuration."""

# Project name for page title
project = "skycalc_ipy"

extensions = [
    "sphinx.ext.todo",  # Allows ".. todo::" in docstrings
    "sphinx.ext.autodoc",  # For API documentation from docstrings
    "sphinx.ext.autosummary",  # For API documentation from docstrings
    # "sphinx.ext.intersphinx",
    # "sphinx.ext.inheritance_diagram",
    # "sphinx.ext.mathjax",
    # "sphinx.ext.extlinks",
    # "sphinx.ext.doctest",
    # "sphinx.ext.coverage",
    # "sphinx.ext.viewcode",
    # "sphinxcontrib.apidoc",
    # "matplotlib.sphinxext.plot_directive",
    "sphinx.ext.napoleon",  # For Numpy-style docstrings (better than numpydoc)
    "sphinx_copybutton",  # Adds "copy" buttons (duh) to code cells
    "myst_nb",  # For markdown parsing and MyST Notebooks
    "sphinx_issues",  # For linking GitHub issues in RTD
]

# Link to templates for API documentation of modules, classes etc.
templates_path = ["_templates"]

# TODO: Check if these can use sphinx-autodoc2.readthedocs.io instead
autosummary_generate = True  # Run autosummary generation
autoclass_content = "class"  # ?
autodoc_default_flags = ["members", "inherited-members"]  # ?
autodoc_docstring_signature = False  # ?
napoleon_numpy_docstring = True  # Allow Numpy-style docstrings
napoleon_use_admonition_for_references = True
todo_include_todos = True  # Actually process ".. todo::" thingies

# Link to repo for "sphinx_issues" extension
issues_github_path = "AstarVienna/skycalc_ipy"

source_encoding = "utf-8"
# Link file types to parsers
source_suffix = {
    ".rst": "restructuredtext",  # default
    ".myst": "myst-nb",
    ".md": "myst-nb",
}

# Timeout for executing notebooks
nb_execution_timeout = 3600  # [s]
nb_execution_mode = "auto"  # Run those without output

# Design theme and config options for overall page
html_theme = "sphinx_book_theme"
html_theme_options = {
    "repository_url": "https://github.com/AstarVienna/skycalc_ipy",
    "use_repository_button": True,
    "use_download_button": True,  # allow download of individual pages
    "home_page_in_toc": True,
}

html_logo = "_static/logos/logo_skycalc_ipy_t.png"  # link to logo
html_title = "skycalc_ipy"
html_static_path = ["_static"]
# see https://sphinx-book-theme.readthedocs.io/en/stable/sections/sidebar-primary.html
html_sidebars = {
    "**": [
        "navbar-logo.html",
        "search-field.html",
        "sbt-sidebar-nav.html",
    ]
}
