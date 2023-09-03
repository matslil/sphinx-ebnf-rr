import glob
import os
import re
import tempfile
import shutil
import sys
import unittest

from sphinx.application import Sphinx

_fixturedir = os.path.join(os.path.dirname(__file__), 'fixture')
_fakecmd = ['java', '-jar', os.path.join(os.getcwd(), 'rr.war')]


def setup():
    global _testuniquedir
    _testcommondir = os.path.join(os.getcwd(), 'test-runs')
    os.makedirs(_testcommondir, exist_ok=True)
    _testuniquedir = tempfile.mkdtemp(dir=_testcommondir)


def teardown():
    pass
    # shutil.rmtree(_tempdir)


def readfile(fname):
    f = open(os.path.join(_outdir, fname), 'rb')
    try:
        return f.read()
    finally:
        f.close()


def with_runsphinx(builder, **kwargs):
    confoverrides = {'ebnf': _fakecmd}
    confoverrides.update(kwargs)

    def wrapfunc(func):
        def test():
            if builder == 'pdf':
                try:
                    import rst2pdf
                    rst2pdf.__file__
                except ImportError:
                    raise unittest.SkipTest
            _testdir = os.path.join(_testuniquedir, func.__name__)
            global _srcdir, _outdir
            _srcdir = os.path.join(_testdir, 'src')
            _outdir = os.path.join(_testdir, 'out')
            os.makedirs(_srcdir)
            os.makedirs(_outdir)
            src = '\n'.join(l[4:] for l in func.__doc__.splitlines()[2:])
            try:
                with open(os.path.join(_srcdir, 'index.rst'), 'wb') as f:
                    f.write(src.encode('utf-8'))
                app = Sphinx(_srcdir, _fixturedir, _outdir, _outdir, builder,
                             confoverrides, status=sys.stdout, warning=sys.stdout)
                app.build()
                func()
            finally:
                pass
#                os.unlink(os.path.join(_srcdir, 'index.rst'))
#                shutil.rmtree(_outdir)
        test.__name__ = func.__name__
        return test

    return wrapfunc


@with_runsphinx('html', ebnf_output_format='svg')
def test_buildhtml_simple_with_svg():
    """Generate simple HTML

    .. ebnf::

       Hello ::= World
    """
    pngfiles = glob.glob(os.path.join(_outdir, '_images', 'ebnf-*.png'))
    assert len(pngfiles) == 1
    svgfiles = glob.glob(os.path.join(_outdir, '_images', 'ebnf-*.svg'))
    assert len(svgfiles) == 1

    assert b'<img src="_images/ebnf' in readfile('index.html')
    assert b'<object data="_images/ebnf' in readfile('index.html')

    pngcontent = readfile(pngfiles[0]).splitlines()
    assert pngcontent[1][2:] == b'Hello'
    svgcontent = readfile(svgfiles[0]).splitlines()
    assert b'-tsvg' in svgcontent[0]
    assert svgcontent[1][2:] == b'Hello'


@with_runsphinx('html', ebnf_output_format='none')
def test_buildhtml_no_output():
    """Generate simple HTML with ebnf directive disabled

    .. ebnf::

       Hello ::= World
    """
    assert b'<img ' not in readfile('index.html')


@with_runsphinx('html')
def test_buildhtml_samediagram():
    """Same diagram should be same file

    .. ebnf::

       Hello ::= World

    .. ebnf::

       Hello ::= World
    """
    files = glob.glob(os.path.join(_outdir, '_images', 'ebnf-*.png'))
    assert len(files) == 1
    imgtags = [l for l in readfile('index.html').splitlines()
               if b'<img src="_images/ebnf' in l]
    assert len(imgtags) == 2


@with_runsphinx('html')
def test_buildhtml_alt():
    """Generate HTML with alt specified

    .. ebnf::
       :alt: Foo <Bar>

       Hello ::= World
    """
    assert b'alt="Foo &lt;Bar&gt;"' in readfile('index.html')


@with_runsphinx('html')
def test_buildhtml_caption():
    """Generate HTML with caption specified

    .. ebnf::
       :caption: Caption with **bold** and *italic*

       Hello ::= World
    """
    assert (b'Caption with <strong>bold</strong> and <em>italic</em>'
            in readfile('index.html'))


@with_runsphinx('html')
def test_buildhtml_name():
    """Generate HTML with name specified

    .. ebnf::
       :caption: Caption
       :name: label

       Hello ::= World
    """
    re.search(br'<div class="figure[^"]*" id="label">', readfile('index.html'))


@with_runsphinx('pdf')
def test_buildpdf_simple():
    """Generate simple PDF

    .. ebnf::

       Hello ::= World
    """
    pdffiles = glob.glob(os.path.join(_outdir, 'ebnf-*.pdf'))
    assert len(pdffiles) == 1
