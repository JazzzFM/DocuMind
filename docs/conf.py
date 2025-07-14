# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document) are in another directory,
# add these directories to sys.path here.
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../documind'))

# Skip Django setup for docs generation - use mock imports instead
DJANGO_AVAILABLE = False
print("Building docs without Django autodoc to avoid configuration issues.")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DocuMind'
copyright = '2025, DocuMind Team'
author = 'DocuMind Team'
release = '1.0.0'
version = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
]

# Add optional extensions if available
try:
    import sphinx_autodoc_typehints
    extensions.append('sphinx_autodoc_typehints')
except ImportError:
    pass

# Skip Django extension to avoid configuration issues
# try:
#     import sphinxcontrib_django
#     extensions.append('sphinxcontrib_django')
# except ImportError:
#     pass

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

autodoc_mock_imports = [
    'chromadb',
    'redis',
    'tesseract',
    'PIL',
    'pdf2image',
    'sentence_transformers',
    'openai',
    'dateutil',
    'django',
    'rest_framework',
    'rest_framework_simplejwt',
    'celery',
    'pytesseract',
    'pandas',
    'decouple',
    'numpy',
    'cv2',
    'azure',
    'google',
]

# Autosummary settings
autosummary_generate = True
autosummary_generate_overwrite = True

# Todo extension settings
todo_include_todos = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
    'requests': ('https://requests.readthedocs.io/en/stable/', None),
}

# HTML theme options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Custom sidebar templates
html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

# HTML title
html_title = f"{project} v{version} Documentation"

# The name for this set of Sphinx documents
html_short_title = project

# Output file base name for HTML help builder
htmlhelp_basename = 'DocuMinddoc'

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {}
latex_documents = [
    ('index', 'DocuMind.tex', 'DocuMind Documentation',
     'DocuMind Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

man_pages = [
    ('index', 'documind', 'DocuMind Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

texinfo_documents = [
    ('index', 'DocuMind', 'DocuMind Documentation',
     author, 'DocuMind', 'AI-Powered Document Processing System.',
     'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

epub_title = project
epub_exclude_files = ['search.html']