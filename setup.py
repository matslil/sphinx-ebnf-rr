# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_desc = open('README.rst').read()

setup(
    name='sphinxcontrib-ebnf-rr',
    version='0.26',
    url='https://github.com/matslil/sphinx-ebnf-rr/',
    download_url='https://pypi.python.org/pypi/sphinxcontrib-ebnf-rr',
    license='BSD',
    author='Mats Liljegren',
    author_email='liljegren.mats@gmail.com',
    description='Sphinx EBNF to railroad diagram extension',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Sphinx :: Extension',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=['sphinxcontrib'],
)
