EBNF to railroad diagram for Sphinx
===================================

Installation
------------

.. code-block::

   pip install sphinxcontrib-ebnf_rr

Usage
-----

Add ``sphinxcontrib.ebnf_rr`` to your extensions list in your ``conf.py``:


.. code-block:: python

   extensions = [
       'sphinxcontrib.ebnf_rr',
   ]

You will need the diagram generator available here:

https://github.com/GuntherRademacher/rr/releases

You may also need to specify the plantuml command in your **conf.py**:

.. code-block:: python

   plantuml = 'java -jar /path/to/rr.war'

Instead, you can install a wrapper script in your PATH:

.. code-block:: console

   % cat <<EOT > /usr/local/bin/rr
   #!/bin/sh -e
   java -jar /path/to/rr.war "$@"
   EOT
   % chmod +x /usr/local/bin/rr

Then, write PlantUML text under the ``.. ebnf::`` directive::

    .. ebnf::
       Preview  ::= 'terminal'
           | nonterminal
           | EBNF - expression

or specify path to an external PlantUML file::

    .. ebnf:: external.ebnf

You can specify ``height``, ``width``, ``scale`` and ``align``::

    .. ebnf::
       :scale: 50 %
       :align: center

       Foo <|-- Bar

You can also specify a caption::

    .. ebnf::
       :caption: Caption with **bold** and *italic*
       :width: 50mm

       Foo <|-- Bar

Configuration
-------------

plantuml
  Path to plantuml executable. (default: 'plantuml')

plantuml_output_format
  Type of output image for HTML renderer. (default: 'png')

  :png: generate only .png inside </img>
  :svg: generate .svg inside <object/> with .png inside </img> as a fallback
  :svg_img: generate only .svg inside <img/> (`browser support <svg_img_>`_)
  :svg_obj: generate only .svg inside <object/> (`browser support <svg_obj_>`_)
  :none: do not generate any images (ignore uml directive)

  When svg is inside <object/> it will always render full size, possibly bigger
  than the container. When svg is inside <img/> it will respect container size
  and scale if necessary.

plantuml_latex_output_format
  Type of output image for LaTeX renderer. (default: 'png')

  :eps: generate .eps (not supported by `pdflatex`)
  :pdf: generate .eps and convert it to .pdf (requires `epstopdf`)
  :png: generate .png
  :tikz: generate .latex in the TikZ format
  :none: do not generate any images (ignore uml directive)

  Because embedded png looks pretty bad, it is recommended to choose `pdf`
  for `pdflatex` or `eps` for `platex`.

plantuml_epstopdf
  Path to epstopdf executable. (default: 'epstopdf')

.. _svg_img: https://caniuse.com/svg-img
.. _svg_obj: https://caniuse.com/svg

plantuml_syntax_error_image
  Should plantuml generate images with render errors. (default: False)

plantuml_cache_path
  Directory where image cache is stored. (default: '_plantuml')

plantuml_batch_size
  **(EXPERIMENTAL)**
  Run plantuml command per the specified number of images. (default: 1)

  If enabled, plantuml documents will be first written to the cache directory,
  and rendered in batches. This eliminates bootstrapping overhead of Java
  runtime and allows plantuml to leverage multiple CPU cores.

  To enable batch rendering, set the size to 100-1000.

Developing
----------

Install the python test dependencies with

.. code-block::

   pip install sphinxcontrib-ebnf_rr[test]

In addition the following non-python dependencies are required in order to run the tests:

* `rr.war`

The tests can be executed using `pytest`

.. code-block::

    pytest
