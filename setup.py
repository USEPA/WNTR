from setuptools import setup, find_packages
from setuptools.extension import Extension
import numpy
import os
from distutils.spawn import find_executable

try:
    numpy_include = numpy.get_include()
except AttributeError:
    numpy_include = numpy.get_numpy_include()

ipopt_executable = find_executable('ipopt')

if ipopt_executable is None:
    ipopt_available = False
else:
    ipopt_available = True

if ipopt_available:
    ipopt_bin = os.path.dirname(ipopt_executable)
    ipopt_base = os.path.dirname(ipopt_bin)
    ipopt_include = os.path.join(ipopt_base, 'include', 'coin')
    ipopt_include_third_party = os.path.join(ipopt_include, 'ThirdParty')
    ipopt_lib = os.path.join(ipopt_base, 'lib')

# inplace extension module
project_dir = './'  # os.path.dirname(os.path.abspath(__file__))
src_files = os.path.join(project_dir, 'wntr', 'aml')
expression_cxx = os.path.join(src_files, 'expression.cpp')
component_cxx = os.path.join(src_files, 'component.cpp')
wntr_model_cxx = os.path.join(src_files, 'wntr_model.cpp')
aml_core_wrap_cxx = os.path.join(src_files, 'aml_core_wrap.cpp')
ipopt_model_cxx = os.path.join(src_files, 'ipopt_model.cpp')
ipopt_model_wrap_cxx = os.path.join(src_files, 'ipopt_model_wrap.cpp')
aml_tnlp_cxx = os.path.join(src_files, 'aml_tnlp.cpp')

extension_modules = list()

aml_core_ext = Extension("wntr.aml._aml_core",
                           sources=[expression_cxx, component_cxx, wntr_model_cxx, aml_core_wrap_cxx],
                           language="c++",
                           extra_compile_args=["-std=c++11"],
                           include_dirs=[numpy_include, src_files],
                           library_dirs=[],
                           libraries=[])
extension_modules.append(aml_core_ext)

if ipopt_available:
    ipopt_model_ext = Extension("wntr.aml._ipopt_model",
                                sources=[ipopt_model_cxx, aml_tnlp_cxx, ipopt_model_wrap_cxx],
                                language="c++",
                                extra_compile_args=["-std=c++11"],  # , "-stdlib=libc++"],
                                include_dirs=[numpy_include, src_files, ipopt_include],
                                library_dirs=[ipopt_lib],
                                libraries=[os.path.join(ipopt_lib, 'ipopt')])
    extension_modules.append(ipopt_model_ext)

DISTNAME = 'wntr'
VERSION = '0.1.6'
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

