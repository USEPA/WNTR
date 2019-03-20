from setuptools import setup, find_packages
from setuptools.extension import Extension
import numpy
import os

use_swig = False

try:
    numpy_include = numpy.get_include()
except AttributeError:
    numpy_include = numpy.get_numpy_include()

# inplace extension module
project_dir = './'  # os.path.dirname(os.path.abspath(__file__))
src_files = os.path.join(project_dir, 'wntr', 'aml')
evaluator_cxx = os.path.join(src_files, 'evaluator.cpp')
evaluator_wrap_cxx = os.path.join(src_files, 'evaluator_wrap.cpp')
evaluator_i = os.path.join(src_files, 'evaluator.i')
network_isolation_dir = os.path.join(project_dir, 'wntr', 'sim', 'network_isolation')
network_isolation_cxx = os.path.join(network_isolation_dir, 'network_isolation.cpp')
network_isolation_i = os.path.join(network_isolation_dir, 'network_isolation.i')
network_isolation_wrap_cxx = os.path.join(network_isolation_dir, 'network_isolation_wrap.cpp')

extension_modules = list()

if use_swig:
    aml_core_ext = Extension("wntr.aml._evaluator",
                             sources=[evaluator_i, evaluator_cxx],
                             language="c++",
                             extra_compile_args=[],
                             include_dirs=[numpy_include, src_files],
                             library_dirs=[],
                             libraries=[],
                             swig_opts = ['-c++', '-builtin'])
    network_isolation_ext = Extension("wntr.sim.network_isolation._network_isolation",
                                      sources=[network_isolation_i, network_isolation_cxx],
                                      language="c++",
                                      include_dirs=[numpy_include, network_isolation_dir],
                                      extra_compile_args=[],
                                      swig_opts=['-c++', '-builtin'])
else:
    aml_core_ext = Extension("wntr.aml._evaluator",
                             sources=[evaluator_cxx, evaluator_wrap_cxx],
                             language="c++",
                             extra_compile_args=[],
                             include_dirs=[numpy_include, src_files],
                             library_dirs=[],
                             libraries=[])
    network_isolation_ext = Extension("wntr.sim.network_isolation._network_isolation",
                                      sources=[network_isolation_cxx, network_isolation_wrap_cxx],
                                      language="c++",
                                      include_dirs=[numpy_include, network_isolation_dir],
                                      extra_compile_args=[])

    
extension_modules.append(aml_core_ext)
extension_modules.append(network_isolation_ext)

DISTNAME = 'wntr'
VERSION = '0.2.1'
PACKAGES = find_packages()
EXTENSIONS = extension_modules
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

