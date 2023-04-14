import os.path
import tempfile
import logging
logger = logging.getLogger(__name__)

from flm.main.configmerger import ConfigMerger
from flm.main.workflow import RenderWorkflow
from flm.main.workflow.templatebasedworkflow import TemplateBasedRenderWorkflow


from ._selenium_driver import SeleniumDriver


default_page_options = {
    'size': 'A4',
    'margin': {
        'top': '2.5cm',
        'right': '2.5cm',
        'bottom': '2.5cm',
        'left': '2.5cm',
        # 'top': '0px', #'2.5cm',
        # 'right': '0px', #'2.5cm',
        # 'bottom': '0px', #'2.5cm',
        # 'left': '0px', #'2.5cm'
    }
}


class HtmlPlusRenderWorkflow(RenderWorkflow):

    # will be set to True for PDF output only
    binary_output = False

    page_options = {}

    @staticmethod
    def get_fragment_renderer_name(req_outputformat, flm_run_info, run_config):

        if req_outputformat and req_outputformat not in ('html', 'pdf'):
            raise ValueError(
                f"The `flm_htmlplus` workflow only supports output formats 'html' and 'pdf'"
            )

        # Always use our own in-house fragment renderer.  Then we'll adjust
        # according to the desired format.
        return 'flm_htmlplus'

    @staticmethod
    def get_default_main_config(flm_run_info, run_config):
        return {
            'flm': {
                'template': {
                    'html': 'simple',
                },
            },
        }

    # ---

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selenium_driver = None

        self.use_output_format = None
        reqof = self.flm_run_info['requested_outputformat'] or 'html'
        if reqof == 'pdf':
            self.use_output_format = 'pdf'
        elif reqof == 'html':
            self.use_output_format = 'html'
        else:
            raise ValueError(
                "Unknown or invalid output format for ‘htmlplus’ workflow: "+repr(reqof)
            )

        if self.use_output_format == 'pdf':
            self.binary_output = True

    # ---

    def render_document(self, document):
        try:
            self.selenium_driver = SeleniumDriver()
            return super().render_document(document)
        finally:
            if self.selenium_driver is not None:
                self.selenium_driver.quit()
            self.selenium_driver = None

    def postprocess_rendered_document(self, rendered_content, document, render_context):

        is_rendering_pdf = False
        if self.use_output_format == 'pdf':
            is_rendering_pdf = True

        # get HTML document along with style

        def mk_page_css():
            if not is_rendering_pdf:
                return ''

            page_options = dict(default_page_options)
            if self.page_options:
                page_options.update(self.page_options)

            logger.debug("Using page_options = %r", page_options)

            # ### This solution prints the background image over the entire
            # ### paper surface, but does not leave enough room between the
            # ### first/last lines of each page and the page edge...
            #
            # s  = "@page { "
            # s += f"  size: {page_options['size']}; margin: 0px;"
            # s += "}\n"
            # s += "@media print { body {"
            # margin_opts = page_options['margin']
            # if isinstance(margin_opts, str):
            #     s += f"padding: {margin_opts}; "
            # else:
            #     for margin_which, margin_value in margin_opts.items():
            #         s += f"padding-{margin_which}: {margin_value}; "
            # s += "} }\n";
            
            # doesn't look great with a background image, but there's not much
            # we can do about that... :/
            s  = "@page { "
            s += f"  size: {page_options['size']}; "
            margin_opts = page_options['margin']
            if isinstance(margin_opts, str):
                s += f"margin: {margin_opts}; "
            else:
                for margin_which, margin_value in margin_opts.items():
                    s += f"margin-{margin_which}: {margin_value}; "
            s += "}\n";
            logger.debug("page CSS is -> %s", s)
            return s

        xtra_css = ""
        xtra_css += _extra_css
        xtra_css += mk_page_css()

        if 'css_pygments' in render_context.data:
            xtra_css += '\n' + render_context.data['css_pygments']

        if 'css_mathjax' in render_context.data:
            xtra_css += '\n' + render_context.data['css_mathjax']

        html_template_workflow_config = ConfigMerger().recursive_assign_defaults([
            {
                'use_output_format_name': 'html',
                'template_config_workflow_defaults': {
                    'style': {
                        'extra_css': xtra_css,
                    },
                }
            },
            self.config,
        ])

        html_template_workflow = TemplateBasedRenderWorkflow(
            html_template_workflow_config,
            self.flm_run_info,
            self.fragment_renderer_information,
            self.fragment_renderer,
        )

        result_html = html_template_workflow.render_templated_document(
            rendered_content, document, render_context,
        )

        # logger.debug('Full HTML:\n\n%s\n\n', result_html)

        if self.use_output_format == 'html':
            return result_html

        #
        # convert result to PDF, if applicable
        #
        if self.use_output_format == 'pdf':

            with tempfile.TemporaryDirectory() as tempdirname:
                htmlfname = os.path.join(tempdirname, 'inpage.html')
                #pdffname = os.path.join(tempdirname, 'result.pdf')
                with open(htmlfname, 'w') as fw:
                    fw.write(result_html)
                result_pdf = self.selenium_driver.html_to_pdf(
                    htmlfname,
                )

            return result_pdf

        raise ValueError("Shouldn't arrive at this point, internal error.")
            


# can add extra hard-coded CSS here
_extra_css = r""""""
