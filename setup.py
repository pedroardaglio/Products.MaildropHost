""" Setup info for Products.MaildropHost

$Id: setup.py 1657 2008-11-01 12:10:57Z jens $
"""

import os
from setuptools import find_packages
from setuptools import setup

NAME = 'MaildropHost'
here = os.path.abspath(os.path.dirname(__file__))
package = os.path.join(here, 'Products', NAME)

def _read(name):
    f = open(os.path.join(package, name))
    return f.read()

_boundary = '\n' + ('-' * 60) + '\n\n'

setup(name='Products.%s' % NAME,
      version=_read('VERSION.txt').strip(),
      description="Asynchronous transaction-aware MailHost replacement for Zope 2",
      long_description=( _read('README.txt')
                       + _boundary
                       + _read('INSTALL.txt')
                       + _boundary
                       + _read('CHANGES.txt')
                       + _boundary
                       + 'Download\n========'
                       ),
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Zope2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Zope Public License",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Communications :: Email",
        "Topic :: Software Development",
        ],
      keywords='web zope zope2 mail smtp',
      author='Jens Vagelpohl',
      author_email='jens@dataflake.org',
      url='http://pypi.python.org/pypi/Products.MaildropHost',
      license="ZPL 2.1 (http://www.zope.org/Resources/License/ZPL-2.1)",
      packages=find_packages(),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # Zope >= 2.8
          'setuptools',
      ],
      entry_points="""
      [zope2.initialize]
      Products.%s = Products.%s:initialize
      """ % (NAME, NAME),
      )
