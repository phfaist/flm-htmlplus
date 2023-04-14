import os.path
import json


import logging
logger = logging.getLogger(__name__)


from ._fragmentrenderer import (
    HtmlPlusFragmentRenderer, HtmlPlusFragmentRendererInformation
)

from ._selenium_driver import SeleniumDriver

from ._workflow import HtmlPlusRenderWorkflow


# so that we can load this fragment renderer simply as 'flm_htmlplus':
FragmentRendererInformation = HtmlPlusFragmentRendererInformation



RenderWorkflowClass = HtmlPlusRenderWorkflow

