import json

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name

from flm.fragmentrenderer.html import HtmlFragmentRenderer
from flm.fragmentrenderer import html as fragmentrenderer_html

from ._selenium_driver import SeleniumDriver





class HtmlPlusFragmentRenderer(HtmlFragmentRenderer):

    use_selenium_driver = True

    render_math_as_svg = True
    mathjax_id_offset = 1

    use_pygments_highlight = True
    use_pygments_style = 'friendly'

    # ---

    # set to a specific selenium driver (`SeleniumDriver` instance) to use.
    # Don't need to set this if it is run using the htmlplus workflow.
    selenium_driver = None

    def _get_selenium_driver(self, render_context):
        if self.selenium_driver is not None:
            return self.selenium_driver

        return render_context.doc.metadata['_flm_workflow'].selenium_driver

    # ---
    def document_render_start(self, render_context):
        super().document_render_start(render_context)

        if self.use_pygments_highlight:
            pyg_html_formatter = HtmlFormatter(
                cssclass='pyg-highlight',
                style=self.use_pygments_style,
            )
            render_context.data['pyg_html_formatter'] = pyg_html_formatter

    def document_render_finish(self, render_context):

        if self.use_pygments_highlight:
            pyg_html_formatter = render_context.data['pyg_html_formatter']
            render_context.data['css_pygments'] = (
                pyg_html_formatter.get_style_defs('.pyg-highlight')
                + _extra_css_pygments
            )

    # ---

    def render_math_content(self,
                            delimiters,
                            nodelist,
                            render_context,
                            displaytype,
                            environmentname=None,
                            target_id=None):

        if not self.render_math_as_svg:
            return super().render_math_content(delimiters, nodelist, render_context,
                                               displaytype, environmentname, target_id)

        if delimiters[0] in ('\\(', '\\[', '$', '$$'):
            # skip simple delimiters for nonnumbered equations
            tex = nodelist.latex_verbatim()
        else:
            tex = (
                delimiters[0]
                + nodelist.latex_verbatim()
                + delimiters[1]
            )

        self.mathjax_id_offset = self.mathjax_id_offset + 1

        indata = {
            'math_list': [
                {
                    'tex': tex,
                    'displaytype': displaytype,
                },
            ],
            'id_offset': self.mathjax_id_offset,
        }

        selenium_driver = self._get_selenium_driver(render_context)

        result = selenium_driver.driver.execute_script(
            f"return window.runmathjax( {json.dumps(indata)} )"
        )

        outdata = json.loads(result)

        if 'css_mathjax' not in render_context.data:
            render_context.data['css_mathjax'] = outdata['css']

        class_names = [ f"{displaytype}-math" ]
        if environmentname is not None:
            class_names.append(f"env-{environmentname.replace('*','-star')}")

        attrs = {}
        if target_id is not None:
            attrs['id'] = target_id

        content_html = outdata['svg_list'][0]

        if displaytype == 'display':
            # BlockLevelContent( # -- don't use blockcontent as display
            # equations might or might not be in their separate paragraph.
            return (
                self.wrap_in_tag(
                    'span',
                    content_html,
                    class_names=class_names,
                    attrs=attrs
                )
            )
        return self.wrap_in_tag(
            'span',
            content_html,
            class_names=class_names,
            attrs=attrs
        )

    # ---

    verbatim_lang_prefix = 'verbatim-lang-'

    def render_verbatim(self, value, render_context, *,
                        is_block_level=False, annotations=None, target_id=None):
        if annotations and len(annotations) > 0:
            for annotation in annotations:
                # determine if there is any special rendering to perform
                if annotation.endswith('-math'):

                    # non-MathJax-SVG-precompiled math content
                    return super().render_verbatim(value,
                                                   render_context,
                                                   is_block_level=is_block_level,
                                                   annotations=annotations,
                                                   target_id=target_id)

                if self.use_pygments_highlight \
                   and annotation.startswith(self.verbatim_lang_prefix):

                    lang = annotation[len(self.verbatim_lang_prefix):]

                    pyg_html_formatter = render_context.data['pyg_html_formatter']
                    highlighted_html_code = \
                        highlight(value, get_lexer_by_name(lang), pyg_html_formatter)

                    attrs = {}
                    if target_id is not None:
                        attrs['id'] = target_id

                    return self.wrap_in_tag(
                        ('div' if is_block_level else 'span'),
                        highlighted_html_code.strip(),
                        class_names=['pyg-highlight-container']+annotations,
                        attrs=attrs,
                    )


        return super().render_verbatim(value, render_context,
                                       is_block_level=is_block_level,
                                       annotations=annotations,
                                       target_id=target_id)
        


_extra_css_pygments = r"""
.pyg-highlight-container {
  padding: 3px 2px;
}
.pyg-highlight-container > .pyg-highlight,
.pyg-highlight-container > .pyg-highlight > pre {
  margin: 0px; padding: 0px;
}
.pyg-highlight {
  background-color: transparent;
}
"""


# ------------------------------------------------------------------------------

class HtmlPlusFragmentRendererInformation:
    FragmentRendererClass = HtmlPlusFragmentRenderer

    format_name = 'html'

    @staticmethod
    def get_style_information(fr):
        return dict(
            fragmentrenderer_html.FragmentRendererInformation.get_style_information(fr),
            **{
                # don't need any MathJax scripts.
                'js': '',
                'body_end_js_scripts': ''
            }
        )

