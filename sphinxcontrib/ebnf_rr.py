# -*- coding: utf-8 -*-
"""
    sphinxcontrib.ebnf_rr
    ~~~~~~~~~~~~~~~~~~~~~

    Embed railroad diagrams on your documentation.

    :copyright: Copyright 2023 by Mats Liljegren <liljegren.mats@gmail.com>.
    :license: BSD, see LICENSE for details.
"""

import codecs
import errno
import hashlib
import os
import re
import shlex
import shutil
import subprocess
from contextlib import contextmanager

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive

from sphinx import util
from sphinx.errors import SphinxError
from sphinx.util import (
    i18n,
    logging,
)
from sphinx.util.nodes import set_source_info
from sphinx.util.osutil import (
    ensuredir,
)

try:
    from PIL import Image
except ImportError:
    Image = None


logger = logging.getLogger(__name__)


if os.name == 'nt':

    def rename(src, dst):
        try:
            os.rename(src, dst)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
            os.unlink(dst)
            os.rename(src, dst)

else:
    rename = os.rename


class EbnfError(SphinxError):
    pass


class ebnf(nodes.General, nodes.Element):
    pass


def align(argument):
    align_values = ('left', 'center', 'right')
    return directives.choice(argument, align_values)


def html_format(argument):
    format_values = list(_KNOWN_HTML_FORMATS.keys())
    return directives.choice(argument, format_values)


class EbnfDirective(Directive):
    """Directive to insert EBNF markup

    Example::

        .. ebnf::
           :alt: Preview EBNF

           Preview  ::= 'terminal'
             | nonterminal
             | EBNF - expression
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True  # allow whitespace in arguments[-1]
    option_spec = {
        'alt': directives.unchanged,
        'align': align,
        'caption': directives.unchanged,
        'height': directives.length_or_unitless,
        'html_format': html_format,
        'name': directives.unchanged,
        'scale': directives.percentage,
        'width': directives.length_or_percentage_or_unitless,
        'max-width': directives.length_or_percentage_or_unitless,
    }

    def run(self):
        warning = self.state.document.reporter.warning
        env = self.state.document.settings.env
        if self.arguments and self.content:
            return [
                warning(
                    'ebnf directive cannot have both content and ' 'a filename argument',
                    line=self.lineno,
                )
            ]
        if self.arguments:
            fn = i18n.search_image_for_language(self.arguments[0], env)
            relfn, absfn = env.relfn2path(fn)
            env.note_dependency(relfn)
            try:
                ebnfcode = _read_utf8(absfn)
            except (IOError, UnicodeDecodeError) as err:
                return [
                    warning(
                        'EBNF file "%s" cannot be read: %s' % (fn, err),
                        line=self.lineno,
                    )
                ]
        else:
            relfn = env.doc2path(env.docname, base=None)
            ebnfcode = '\n'.join(self.content)

        node = ebnf(self.block_text, **self.options)
        node['ebnf'] = ebnfcode
        node['incdir'] = os.path.dirname(relfn)
        node['filename'] = os.path.split(relfn)[1]

        # XXX maybe this should be moved to _visit_ebnf functions. it
        # seems wrong to insert "figure" node by "ebnf" directive.
        if 'caption' in self.options or 'align' in self.options:
            node = nodes.figure('', node)
            if 'align' in self.options:
                node['align'] = self.options['align']
        if 'caption' in self.options:
            inodes, messages = self.state.inline_text(
                self.options['caption'], self.lineno
            )
            caption_node = nodes.caption(self.options['caption'], '', *inodes)
            caption_node.extend(messages)
            set_source_info(self, caption_node)
            node += caption_node
        self.add_name(node)
        if 'html_format' in self.options:
            node['html_format'] = self.options['html_format']
        if 'xhtml_format' in self.options:
            node['xhtml_format'] = self.options['xhtml_format']

        return [node]


def _read_utf8(filename):
    fp = codecs.open(filename, 'rb', 'utf-8')
    try:
        return fp.read()
    finally:
        fp.close()


def hash_ebnf_node(node):
    h = hashlib.sha1()
    # may include different file relative to doc
    h.update(node['incdir'].encode('utf-8'))
    h.update(b'\0')
    h.update(node['ebnf'].encode('utf-8'))
    return h.hexdigest()


def generate_name(self, node, fileformat):
    key = hash_ebnf_node(node)
    fname = 'ebnf-%s.%s' % (key, fileformat)
    imgpath = getattr(self.builder, 'imgpath', None)
    if imgpath:
        return (
            '/'.join((self.builder.imgpath, fname)),
            os.path.join(self.builder.outdir, '_images', fname),
        )
    else:
        return fname, os.path.join(self.builder.outdir, fname)


def _ntunquote(s):
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def _split_cmdargs(args):
    if isinstance(args, (tuple, list)):
        return list(args)
    if os.name == 'nt':
        return list(map(_ntunquote, shlex.split(args, posix=False)))
    else:
        return shlex.split(args, posix=True)


_ARGS_BY_FILEFORMAT = {
    'png': ['-png'],
    'svg': [],
}


def generate_rr_args(self, node, fileformat):
    args = _split_cmdargs(self.builder.config.ebnf)
    args.extend(['-pipe', '-charset', 'utf-8'])
    args.extend(_ARGS_BY_FILEFORMAT[fileformat])
    args.extend([node['filename']])
    return args


def render_ebnf(self, node, fileformat):
    refname, outfname = generate_name(self, node, fileformat)
    if os.path.exists(outfname):
        return refname, outfname  # don't regenerate

    cachefname = self.builder.ebnf_builder.render(node, fileformat)
    ensuredir(os.path.dirname(outfname))
    # TODO: optionally do symlink/link
    shutil.copyfile(cachefname, outfname)
    return refname, outfname


def render_ebnf_inline(self, node, fileformat):
    absincdir = os.path.join(self.builder.srcdir, node['incdir'])
    try:
        p = subprocess.Popen(
            generate_rr_args(self, node, fileformat),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=absincdir,
        )
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise
        raise EbnfError(
            'rr command %r cannot be run' % self.builder.config.ebnf
        )
    sout, serr = p.communicate(node['ebnf'].encode('utf-8'))
    if p.returncode != 0:
        raise EbnfError('error while running rr\n\n%s' % serr)
    return sout.decode('utf-8')


class RrBuilder(object):
    def __init__(self, builder):
        # for compatibility with existing functions which expect self.builder
        # TODO: remove self.builder
        self.builder = builder

        self.batch_size = builder.config.ebnf_batch_size
        self.cache_dir = os.path.join(
            builder.outdir, builder.config.ebnf_cache_path
        )

        self._base_cmdargs = _split_cmdargs(builder.config.ebnf)
        self._base_cmdargs.extend(['-charset', 'utf-8'])

        self.image_formats = []
        if builder.format == 'html':
            fmt = builder.config.ebnf_output_format
            if fmt != 'none':
                fileformats, _gettag = _lookup_html_format(fmt)
                self.image_formats = list(fileformats)
        elif builder.format == 'xhtml':
            fmt = builder.config.ebnf_xhtml_output_format
            if fmt != 'none':
                fileformat, _postproc = _lookup_latex_format(fmt)
                self.image_formats = [fileformat]

        self._known_keys = set()
        self._pending_keys = []

    def collect_nodes(self, doctree):
        for node in doctree.traverse(ebnf):
            key = hash_ebnf_node(node)
            if key in self._known_keys:
                continue
            self._known_keys.add(key)

            doc = node['ebnf'].encode('utf-8')
            if b'!include' in doc or b'%filename' in doc:
                # Heuristic to work around the path/filename issue. There's no
                # easy way to specify the cwd of the doc without using -pipe.
                continue

            outdir = os.path.join(self.cache_dir, key[:2])
            outfbase = os.path.join(outdir, key)
            if all(
                os.path.exists('%s.%s' % (outfbase, sfx))
                for sfx in ['ebnf'] + self.image_formats
            ):
                continue

            ensuredir(outdir)
            with open(outfbase + '.ebnf', 'wb') as f:
                f.write(doc)
            self._pending_keys.append(key)

    def render_batches(self):
        pending_keys = sorted(self._pending_keys)
        for fileformat in self.image_formats:
            for i in range(0, len(pending_keys), self.batch_size):
                keys = pending_keys[i : i + self.batch_size]
                with util.progress_message(
                    'rendering railroad diagrams [%d..%d/%d]'
                    % (i, i + len(keys), len(pending_keys))
                ):
                    self._render_files(keys, fileformat)

        del self._pending_keys[:]

    def _render_files(self, keys, fileformat):
        cmdargs = self._base_cmdargs[:]
        cmdargs.extend(_ARGS_BY_FILEFORMAT[fileformat])
        cmdargs.extend(os.path.join(k[:2], '%s.ebnf' % k) for k in keys)
        try:
            p = subprocess.Popen(cmdargs, stderr=subprocess.PIPE, cwd=self.cache_dir)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
            raise EbnfError(
                'rr command %r cannot be run' % self.builder.config.ebnf
            )
        serr = p.communicate()[1]
        if p.returncode != 0:
            if self.builder.config.ebnf_syntax_error_image:
                logger.warning(
                    'error while running rr\n\n%s' % serr, type='ebnf'
                )
            else:
                raise EbnfError('error while running rr\n\n%s' % serr)

    def render(self, node, fileformat):
        key = hash_ebnf_node(node)
        outdir = os.path.join(self.cache_dir, key[:2])
        outfname = os.path.join(outdir, '%s.%s' % (key, fileformat))
        if os.path.exists(outfname):
            return outfname

        ensuredir(outdir)
        absincdir = os.path.join(self.builder.srcdir, node['incdir'])
        with open(outfname + '.new', 'wb') as f:
            try:
                p = subprocess.Popen(
                    generate_rr_args(self, node, fileformat),
                    stdout=f,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=absincdir,
                )
            except OSError as err:
                if err.errno != errno.ENOENT:
                    raise
                raise EbnfError(
                    'rr command %r cannot be run' % self.builder.config.ebnf
                )
            serr = p.communicate(node['ebnf'].encode('utf-8'))[1]
            if p.returncode != 0:
                if self.builder.config.ebnf_syntax_error_image:
                    logger.warning(
                        'error while running rr\n\n%s' % serr,
                        location=node,
                        type='ebnf',
                    )
                else:
                    raise EbnfError('error while running rr\n\n%s' % serr)

        rename(outfname + '.new', outfname)
        return outfname


def _render_batches_on_vist(self):
    self.builder.ebnf_builder.render_batches()


def _get_png_tag(self, fnames, node):
    refname, outfname = fnames['png']
    alt = node.get('alt', node['ebnf'])

    # mimic StandaloneHTMLBuilder.post_process_images(). maybe we should
    # process images prior to html_vist.
    scale_attrs = [k for k in ('scale', 'width', 'height') if k in node]
    if scale_attrs and Image is None:
        logger.warning(
            (
                'ebnf: unsupported scaling attributes: %s '
                '(install PIL or Pillow)' % ', '.join(scale_attrs)
            ),
            location=node,
            type='ebnf',
        )
    if not scale_attrs or Image is None:
        return '<img src="%s" alt="%s"/>\n' % (self.encode(refname), self.encode(alt))

    scale = node.get('scale', 100)
    styles = []

    # Width/Height
    vu = re.compile(r"(?P<value>\d+)\s*(?P<units>[a-zA-Z%]+)?")
    for a in ['width', 'height']:
        if a not in node:
            continue
        m = vu.match(node[a])
        if not m:
            raise EbnfError('Invalid %s' % a)
        m = m.groupdict()
        w = int(m['value'])
        wu = m['units'] if m['units'] else 'px'
        styles.append('%s: %s%s' % (a, w * scale / 100, wu))

    # Add physical size to assist rendering (defaults)
    if not styles:
        # the image may be corrupted if ebnf isn't configured correctly,
        # which isn't a hard error.
        try:
            im = Image.open(outfname)
            im.load()
            styles.extend(
                '%s: %s%s' % (a, w * scale / 100, 'px')
                for a, w in zip(['width', 'height'], im.size)
            )
        except (IOError, OSError) as err:
            logger.warning(
                'ebnf: failed to get image size: %s' % err,
                location=node,
                type='ebnf',
            )

    return '<a href="%s"><img src="%s" alt="%s" style="%s"/>' '</a>\n' % (
        self.encode(refname),
        self.encode(refname),
        self.encode(alt),
        self.encode('; '.join(styles)),
    )


def _get_svg_style(fname):
    f = codecs.open(fname, 'r', 'utf-8')
    try:
        for l in f:
            m = re.search(r'<svg\b([^<>]+)', l)
            if m:
                attrs = m.group(1)
                break
        else:
            return
    finally:
        f.close()

    m = re.search(r'\bstyle=[\'"]([^\'"]+)', attrs)
    if not m:
        return
    return m.group(1)


def _svg_get_style_str(node, outfname):
    width_height_styles = [
        "%s:%s" % (key, val)
        for key, val in node.attributes.items()
        if key in ['width', 'height', 'max-width']
    ]
    if width_height_styles:
        style_str = '; '.join(width_height_styles)
    else:
        style_str = _get_svg_style(outfname) or ''
    return style_str


def _get_svg_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    style_str = _svg_get_style_str(node, outfname)
    return '\n'.join(
        [
            # copy width/height style from <svg> tag, so that <object> area
            # has enough space.
            '<object data="%s" type="image/svg+xml" style="%s">'
            % (self.encode(refname), style_str),
            _get_png_tag(self, fnames, node),
            '</object>',
        ]
    )


def _get_svg_img_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    alt = node.get('alt', node['ebnf'])
    return '<img src="%s" alt="%s"/>' % (self.encode(refname), self.encode(alt))


def _get_svg_obj_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    # copy width/height style from <svg> tag, so that <object> area
    # has enough space.
    return '<object data="%s" type="image/svg+xml" style="%s"></object>' % (
        self.encode(refname),
        _get_svg_style(outfname) or '',
    )


_KNOWN_HTML_FORMATS = {
    'png': (('png',), _get_png_tag),
    'svg': (('png', 'svg'), _get_svg_tag),
    'svg_img': (('svg',), _get_svg_img_tag),
    'svg_obj': (('svg',), _get_svg_obj_tag),
}


def _lookup_html_format(fmt):
    try:
        return _KNOWN_HTML_FORMATS[fmt]
    except KeyError:
        raise EbnfError(
            'ebnf_output_format must be one of %s, but is %r'
            % (', '.join(map(repr, _KNOWN_HTML_FORMATS)), fmt)
        )


@contextmanager
def _prepare_html_render(self, fmt, node):
    if fmt == 'none':
        raise nodes.SkipNode

    try:
        yield _lookup_html_format(fmt)
    except EbnfError as err:
        logger.warning(str(err), location=node, type='ebnf')
        raise nodes.SkipNode


def html_visit_ebnf(self, node):
    _render_batches_on_vist(self)
    if 'html_format' in node:
        fmt = node['html_format']
    else:
        fmt = self.builder.config.ebnf_output_format

    with _prepare_html_render(self, fmt, node) as (fileformats, gettag):
        # fnames: {fileformat: (refname, outfname), ...}
        fnames = dict((e, render_ebnf(self, node, e)) for e in fileformats)

    self.body.append(self.starttag(node, 'p', CLASS='ebnf'))
    self.body.append(gettag(self, fnames, node))
    self.body.append('</p>\n')
    raise nodes.SkipNode


def _convert_eps_to_pdf(self, refname, fname):
    args = _split_cmdargs(self.builder.config.ebnf_epstopdf)
    args.append(fname)
    try:
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as err:
            # workaround for missing shebang of epstopdf script
            if err.errno != getattr(errno, 'ENOEXEC', 0):
                raise
            p = subprocess.Popen(
                ['bash'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise
        raise EbnfError(
            'epstopdf command %r cannot be run' % self.builder.config.ebnf_epstopdf
        )
    serr = p.communicate()[1]
    if p.returncode != 0:
        raise EbnfError('error while running epstopdf\n\n%s' % serr)
    return refname[:-4] + '.pdf', fname[:-4] + '.pdf'


_KNOWN_CONFLUENCE_FORMATS = [
    'png',
    'svg',
]


def confluence_visit_ebnf(self, node):
    _render_batches_on_vist(self)
    fmt = self.builder.config.ebnf_output_format
    if fmt == 'none':
        raise nodes.SkipNode

    if fmt not in _KNOWN_CONFLUENCE_FORMATS:
        raise EbnfError(
            'ebnf_output_format must be one of %s, but is %r'
            % (', '.join(map(repr, _KNOWN_CONFLUENCE_FORMATS)), fmt)
        )

    _, outfname = render_ebnf(self, node, fmt)

    # put node representing rendered image
    img_node = nodes.image(uri=outfname, alt=node.get('alt', node['ebnf']))
    node.replace_self(img_node)
    self.visit_image(img_node)


def confluence_depart_ebnf(self, node):
    pass


def text_visit_ebnf(self, node):
    _render_batches_on_vist(self)
    try:
        text = render_ebnf_inline(self, node, 'txt')
    except EbnfError as err:
        logger.warning(str(err), location=node, type='ebnf')
        text = node['ebnf']  # fall back to ebnf text, which is still readable

    self.new_state()
    self.add_text(text)
    self.end_state()
    raise nodes.SkipNode


def pdf_visit_ebnf(self, node):
    _render_batches_on_vist(self)
    try:
        refname, outfname = render_ebnf(self, node, 'eps')
        refname, outfname = _convert_eps_to_pdf(self, refname, outfname)
    except EbnfError as err:
        logger.warning(str(err), location=node, type='ebnf')
        raise nodes.SkipNode
    rep = nodes.image(uri=outfname, alt=node.get('alt', node['ebnf']))
    node.parent.replace(node, rep)


def unsupported_visit_ebnf(self, node):
    logger.warning(
        'ebnf: unsupported output format (node skipped)',
        location=node,
        type='ebnf',
    )
    raise nodes.SkipNode


_NODE_VISITORS = {
    'html': (html_visit_ebnf, None),
    'latex': (unsupported_visit_ebnf, None),
    'man': (unsupported_visit_ebnf, None),  # TODO
    'texinfo': (unsupported_visit_ebnf, None),  # TODO
    'text': (text_visit_ebnf, None),
    'confluence': (confluence_visit_ebnf, confluence_depart_ebnf),
    'singleconfluence': (confluence_visit_ebnf, confluence_depart_ebnf),
}


def _on_builder_inited(app):
    app.builder.ebnf_builder = RrBuilder(app.builder)


def _on_doctree_read(app, doctree):
    # Collect as many static nodes as possible prior to start building.
    if app.builder.ebnf_builder.batch_size > 1:
        app.builder.ebnf_builder.collect_nodes(doctree)


def _on_doctree_resolved(app, doctree, docname):
    # Dynamically generated nodes will be collected here, which will be
    # batched at node visitor. Since 'doctree-resolved' and node visits
    # can be intermixed, there's no way to batch rendering of dynamic nodes
    # at once.
    if app.builder.ebnf_builder.batch_size > 1:
        app.builder.ebnf_builder.collect_nodes(doctree)


def setup(app):
    app.add_node(ebnf, **_NODE_VISITORS)
    app.add_directive('ebnf', EbnfDirective)
    try:
        app.add_config_value('ebnf', 'ebnf', 'html', types=(str, tuple, list))
    except TypeError:
        # Sphinx < 1.4?
        app.add_config_value('ebnf', 'ebnf', 'html')
    app.add_config_value('ebnf_output_format', 'png', 'html')
    app.add_config_value('ebnf_epstopdf', 'epstopdf', '')
    app.add_config_value('ebnf_latex_output_format', 'png', '')
    app.add_config_value('ebnf_syntax_error_image', False, '')
    app.add_config_value('ebnf_cache_path', '_ebnf', '')
    app.add_config_value('ebnf_batch_size', 1, '')
    app.connect('builder-inited', _on_builder_inited)
    app.connect('doctree-read', _on_doctree_read)
    app.connect('doctree-resolved', _on_doctree_resolved)

    # imitate what app.add_node() does
    if 'rst2pdf.pdfbuilder' in app.config.extensions:
        from rst2pdf.pdfbuilder import PDFTranslator as translator

        setattr(translator, 'visit_' + ebnf.__name__, pdf_visit_ebnf)

    return {'parallel_read_safe': True}
