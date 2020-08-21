

name = 'Ludos'
long_name = 'Ludos'

version = '0.7'
url = 'https://github.com/felixludos/ludos'

description = 'AI-centric framework for turn-based games'

author = 'Felix Leeb'
author_email = 'felixludos.info@gmail.com'

license = 'GPL3'

readme = 'README.md'

packages = ['ludos']

import os
try:
	with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'requirements.txt'), 'r') as f:
		install_requires = f.readlines()
except:
	install_requires = ['pyyaml', 'flask', 'flask_cors', 'requests',]
del os


