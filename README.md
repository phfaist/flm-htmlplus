# Enhancements to LLM's HTML output, plus PDF via HTML

Installation:
```
> pip install git+https://github.com/phfaist/flm-htmlplus
```

This LLM extension package provides the `flm_htmlplus` workflow
(`--workflow=flm_htmlplus`) which adds some processing levels
to LLM's default HTML output.  Mathematical equations can be
compiled into SVG elements.  You can also generate PDF output
(internally, this uses an instance of Chrome to print the
generated HTML content to a PDF document).
