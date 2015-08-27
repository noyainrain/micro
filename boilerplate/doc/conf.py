import sys
sys.path.insert(0, '.')

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.httpdomain']

project = '{name}'
copyright = '{year} {name} contributors'
version = release = '{version}'

html_sidebars = {'**': ['globaltoc.html', 'relations.html', 'searchbox.html']}

autodoc_member_order = 'bysource'
