import glob
import os
import re
import tempfile
import shutil
import sys
import unittest

from sphinx.application import Sphinx

_fixturedir = os.path.join(os.path.dirname(__file__), 'fixture')
_fakecmd = os.path.join(os.path.dirname(__file__), 'fakecmd.py')


def setup():
    global _tempdir, _srcdir, _outdir
    _tempdir = tempfile.mkdtemp()
    _srcdir = os.path.join(_tempdir, 'src')
    _outdir = os.path.join(_tempdir, 'out')
    os.mkdir(_srcdir)


def teardown():
    shutil.rmtree(_tempdir)


def readfile(fname):
    f = open(os.path.join(_outdir, fname), 'rb')
    try:
        return f.read()
    finally:
        f.close()


def runsphinx(text, builder, confoverrides):
    f = open(os.path.join(_srcdir, 'index.rst'), 'wb')
    try:
        f.write(text.encode('utf-8'))
    finally:
        f.close()
    app = Sphinx(_srcdir, _fixturedir, _outdir, _outdir, builder,
                 confoverrides, status=sys.stdout, warning=sys.stdout)
    app.build()


def with_runsphinx(builder, **kwargs):
    confoverrides = {'ebnf': [sys.executable, _fakecmd]}
    confoverrides.update(kwargs)

    def wrapfunc(func):
        def test():
            if builder == 'pdf':
                try:
                    import rst2pdf
                    rst2pdf.__file__
                except ImportError:
                    raise unittest.SkipTest
            src = '\n'.join(l[4:] for l in func.__doc__.splitlines()[2:])
            os.mkdir(_outdir)
            try:
                runsphinx(src, builder, confoverrides)
                func()
            finally:
                os.unlink(os.path.join(_srcdir, 'index.rst'))
                shutil.rmtree(_outdir)
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
    assert b'-pipe' in pngcontent[0]
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


@with_runsphinx('html', ebnf_batch_size=2)
def test_buildhtml_in_batches():
    """Render in batches

    .. ebnf::

       Hello ::= World

    .. ebnf::

       Hello2 ::= World2

    .. ebnf::

       Hello3 ::= World3

    .. ebnf::

       !include seq.ja.ebnf
    """
    ebnf_files = glob.glob(os.path.join(_outdir, '_ebnf', '*', '*.ebnf'))
    assert len(ebnf_files) == 3
    ebnf_contents = [readfile(f).splitlines() for f in ebnf_files]
    assert all(len(lines) == 3 for lines in ebnf_contents)
    assert (sorted(lines[1] for lines in ebnf_contents)
            == [b'Hello ::= World', b'Hello2 ::= World2', b'Hello3 ::= World3'])

    # batches: [2, 1], excluded: 1
    png_files = glob.glob(os.path.join(_outdir, '_ebnf', '*', '*.png'))
    assert len(png_files) == 4
    png_commands = [readfile(f).splitlines()[0] for f in png_files]
    assert len(set(png_commands)) == 3
    assert sum(b'-pipe' in cmd for cmd in set(png_commands)) == 1
    assert sorted(sum(c.endswith(b'.ebnf') for c in cmd.split())
                  for cmd in set(png_commands)) == [0, 1, 2]


@with_runsphinx('latex')
def test_buildlatex_simple():
    """Generate simple LaTeX

    .. ebnf::

       Hello ::= World
    """
    files = glob.glob(os.path.join(_outdir, 'ebnf-*.png'))
    assert len(files) == 1
    assert re.search(br'\\(sphinx)?includegraphics\{+ebnf-',
                     readfile('_fixture.tex'))

    content = readfile(files[0]).splitlines()
    assert b'-pipe' in content[0]
    assert content[1][2:] == b'Hello ::= World'


@with_runsphinx('latex', ebnf_latex_output_format='eps')
def test_buildlatex_simple_with_eps():
    """Generate simple LaTeX with EPS

    .. ebnf::

       Hello ::= World
    """
    files = glob.glob(os.path.join(_outdir, 'ebnf-*.eps'))
    assert len(files) == 1
    assert re.search(br'\\(sphinx)?includegraphics\{+ebnf-',
                     readfile('ebnf_fixture.tex'))

    content = readfile(files[0]).splitlines()
    assert b'-teps' in content[0]
    assert content[1][2:] == b'Hello'


@with_runsphinx('latex', ebnf_latex_output_format='tikz')
def test_buildlatex_simple_with_tikz():
    """Generate simple LaTeX with TikZ

    .. ebnf::

       Hello ::= World
    """
    files = glob.glob(os.path.join(_outdir, 'ebnf-*.latex'))
    assert len(files) == 1
    assert re.search(br'\\input\{+ebnf-',
                     readfile('ebnf_fixture.tex'))

    content = readfile(files[0]).splitlines()
    assert b'-tlatex:nopreamble' in content[0]
    assert content[1][2:] == b'Hello'


@with_runsphinx('latex', ebnf_latex_output_format='tikz')
def test_buildlatex_simple_scale_with_tikz():
    """Generate simple LaTeX with TikZ

    .. ebnf::
       :scale: 20%

       Hello ::= World
    """
    assert re.search(br'\\adjustbox\{scale=0.2\}\{\\input\{+ebnf-',
                     readfile('ebnf_fixture.tex'))


@with_runsphinx('latex', ebnf_latex_output_format='tikz')
def test_buildlatex_simple_width_with_tikz():
    """Generate simple LaTeX with TikZ

    .. ebnf::
       :width: 50mm

       Hello ::= World
    """
    assert re.search(br'\\adjustbox\{width=50mm\}\{\\input\{+ebnf-',
                     readfile('ebnf_fixture.tex'))


@with_runsphinx('latex', ebnf_latex_output_format='tikz')
def test_buildlatex_simple_height_with_tikz():
    """Generate simple LaTeX with TikZ

    .. ebnf::
       :height: 50mm

       Hello ::= World
    """
    assert re.search(br'\\adjustbox\{height=50mm\}\{\\input\{+ebnf-',
                     readfile('ebnf_fixture.tex'))


@with_runsphinx('latex', ebnf_latex_output_format='pdf')
def test_buildlatex_simple_with_pdf():
    """Generate simple LaTeX with PDF

    .. ebnf::

       Hello ::= World
    """
    epsfiles = glob.glob(os.path.join(_outdir, 'ebnf-*.eps'))
    pdffiles = glob.glob(os.path.join(_outdir, 'ebnf-*.pdf'))
    assert len(epsfiles) == 1
    assert len(pdffiles) == 1
    assert re.search(br'\\(sphinx)?includegraphics\{+ebnf-',
                     readfile('ebnf_fixture.tex'))

    epscontent = readfile(epsfiles[0]).splitlines()
    assert b'-teps' in epscontent[0]
    assert epscontent[1][2:] == b'Hello'


@with_runsphinx('latex', ebnf_latex_output_format='none')
def test_buildlatex_no_output():
    """Generate simple LaTeX with ebnf directive disabled

    .. ebnf::

       Hello ::= World
    """
    assert not re.search(br'\\(sphinx)?includegraphics\{+ebnf-',
                         readfile('ebnf_fixture.tex'))


@with_runsphinx('latex')
def test_buildlatex_with_caption():
    """Generate LaTeX with caption

    .. ebnf::
       :caption: Hello UML

       Hello ::= World
    """
    out = readfile('ebnf_fixture.tex')
    assert re.search(br'\\caption\{\s*Hello UML\s*\}', out)
    assert re.search(br'\\begin\{figure\}\[htbp\]', out)
    assert not re.search(br'\\begin\{flushNone', out)  # issue #136


@with_runsphinx('latex')
def test_buildlatex_with_align():
    """Generate LaTeX with caption

    .. ebnf::
       :align: right

       Hello ::= World
    """
    out = readfile('ebnf_fixture.tex')
    assert (re.search(br'\\begin\{figure\}\[htbp\]\\begin\{flushright\}', out)
            or re.search(br'\\begin\{wrapfigure\}\{r\}', out))


@with_runsphinx('pdf')
def test_buildpdf_simple():
    """Generate simple PDF

    .. ebnf::

       Hello ::= World
    """
    epsfiles = glob.glob(os.path.join(_outdir, 'ebnf-*.eps'))
    pdffiles = glob.glob(os.path.join(_outdir, 'ebnf-*.pdf'))
    assert len(epsfiles) == 1
    assert len(pdffiles) == 1

    epscontent = readfile(epsfiles[0]).splitlines()
    assert b'-teps' in epscontent[0]
    assert epscontent[1][2:] == b'Hello'
