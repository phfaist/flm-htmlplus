import os.path
import json
import base64

import logging
logger = logging.getLogger(__name__)

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.common.by import By


with open(os.path.join(os.path.dirname(__file__), 'runmathjax_browser_dist.js')) as f:
    runmathjax_js_src = f.read()


def adjust_selenium_logging_levels():

    if not logging.getLogger().isEnabledFor(logging.DEBUG):
        # silence some verbose messages sent on INFO level
        for logname in ('selenium', 'urllib3',):
            logging.getLogger(logname).setLevel(level=logging.INFO)
        for logname in ('WDM',):
            logging.getLogger(logname).setLevel(level=logging.WARNING)

    # always silence very long and verbose DEBUG messages from this logger
    logging.getLogger('selenium.webdriver.remote').setLevel(level=logging.INFO)

#
# inspired by
# https://github.com/kumaF/pyhtml2pdf/blob/master/pyhtml2pdf/converter.py .
#
# Thanks!
#
class SeleniumDriver:
    def __init__(self, *, load_runmathjax=True):
        super().__init__()

        adjust_selenium_logging_levels()

        settings = {
            "appState": {
                "recentDestinations": [{
                    "id": "Save as PDF",
                    "origin": "local"
                }],
                "selectedDestinationId": "Save as PDF",
                "version": 2,
            },
            "images": 2,
        }

        prefs = {'printing.print_preview_sticky_settings': json.dumps(settings)}

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option('prefs', prefs)

        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--run-all-compositor-stages-before-draw")

        chrome_options.add_argument('--enable-print-browser')
        chrome_options.add_argument('--kiosk-printing')

        chrome_options.add_argument("--remote-allow-origins=*")

        self.driver = webdriver.Chrome(
            ChromeDriverManager(cache_valid_range=62).install(),
            options=chrome_options
        )


        if load_runmathjax:
            # install our runmathjax() function into this selenium driver's global
            # JS namespace
            self.driver.execute_script( runmathjax_js_src )


    def quit(self):
        if self.driver is not None:
            self.driver.quit()
        self.driver = None

    def __del__(self):
        self.quit()

    def html_to_pdf(self, input_path, *, wait_html_ready=False, wait_timeout=5):

        self.driver.get(f"file://{input_path}")

        # Waiting only seems necessary if we have dynamic JS on our page.  Since
        # we prerender mathjax to SVG at build time, we shouldn't normally need
        # to wait.
        if wait_html_ready:
            try:
                WebDriverWait(self.driver, wait_timeout).until(
                    staleness_of(self.driver.find_element(by=By.TAG_NAME, value="html"))
                )
            except TimeoutException:
                pass

        final_print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        #final_print_options.update(print_options)

        print_pdf_url = (
            f"{self.driver.command_executor._url}/session/"
            f"{self.driver.session_id}/chromium/send_command_and_get_result"
        )
        print_pdf_body = \
            json.dumps({"cmd": "Page.printToPDF", "params": final_print_options})
        print_pdf_response = \
            self.driver.command_executor._request("POST", print_pdf_url, print_pdf_body)
        if not print_pdf_response:
            raise RuntimeError(print_pdf_response.get("value"))

        result_data = print_pdf_response.get("value")

        result_pdf = base64.b64decode(result_data['data'])

        return result_pdf

