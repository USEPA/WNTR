from setuptools import setup, find_packages
from distutils.core import Extension

DISTNAME = 'wntr'
VERSION = '0.1'
PACKAGES = find_packages()
EXTENSIONS = []
DESCRIPTION = 'Water Network Tool for Resilience'
LONG_DESCRIPTION = open('README.md').read()
AUTHOR = 'WNTR Developers'
MAINTAINER_EMAIL = 'kaklise@sandia.gov'
LICENSE = 'Revised BSD'
URL = 'https://github.com/USEPA/WNTR'

setuptools_kwargs = {
    'zip_safe': False,
    'install_requires': [],
    'scripts': [],
    'include_package_data': True
}

setup(name=DISTNAME,
      version=VERSION,
      packages=PACKAGES,
      ext_modules=EXTENSIONS,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author=AUTHOR,
      maintainer_email=MAINTAINER_EMAIL,
      license=LICENSE,
      url=URL,
      **setuptools_kwargs)

