from setuptools import setup

setup(name='gsm',
      version='0.1',
      description='AI-centric framework for turn-based games',
      url='https://github.com/fleeb24/gsm',
      author='Felix Leeb',
      author_email='fleeb@uw.edu',
      license='MIT',
      packages=['gsm'],
      install_requires=[
            'yaml',
            'numpy',
      ],
      zip_safe=False)