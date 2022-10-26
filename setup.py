from setuptools import setup, find_packages
from setuptools.extension import Extension
import os
import re
import sys

use_swig = False
build = True

extension_modules = list()

# if sys.version_info.major >= 3 and sys.version_info.minor >= 10:
#     print("Python version >= 3.10.x")
#     build = True

if build:
    import numpy

    try:
        numpy_include = numpy.get_include()
    except AttributeError:
        numpy_include = numpy.get_numpy_include()

    # inplace extension module
    project_dir = './'  # os.path.dirname(os.path.abspath(__file__))
    src_files = os.path.join(project_dir, 'wntr', 'sim', 'aml')
    evaluator_cxx = os.path.join(src_files, 'evaluator.cpp')
    evaluator_wrap_cxx = os.path.join(src_files, 'evaluator_wrap.cpp')
    evaluator_i = os.path.join(src_files, 'evaluator.i')
    network_isolation_dir = os.path.join(project_dir, 'wntr', 'sim', 'network_isolation')
    network_isolation_cxx = os.path.join(network_isolation_dir, 'network_isolation.cpp')
    network_isolation_i = os.path.join(network_isolation_dir, 'network_isolation.i')
    network_isolation_wrap_cxx = os.path.join(network_isolation_dir, 'network_isolation_wrap.cpp')

    if use_swig:
        aml_core_ext = Extension("wntr.sim.aml._evaluator",
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
        aml_core_ext = Extension("wntr.sim.aml._evaluator",
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
PACKAGES = find_packages()
EXTENSIONS = extension_modules
DESCRIPTION = 'Water Network Tool for Resilience'
AUTHOR = 'WNTR Developers'
MAINTAINER_EMAIL = 'kaklise@sandia.gov'
LICENSE = 'Revised BSD'
URL = 'https://github.com/USEPA/WNTR'
DEPENDENCIES = ['numpy>=1.21', 'scipy', 'networkx', 'pandas', 'matplotlib']

# use README file as the long description
file_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(file_dir, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

# get version from __init__.py
with open(os.path.join(file_dir, 'wntr', '__init__.py')) as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        VERSION = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")

print(extension_modules)

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
      zip_safe=False,
      install_requires=DEPENDENCIES,
      scripts=[],
      include_package_data=True)
