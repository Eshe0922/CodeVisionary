# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

from enum import Enum
BASH_FENCE = ["```bash", "```"]
class Tools(Enum):
    syntax_check = {
        "command": "syntax_check -f 'path'",
        "description": f"""
<syntax check>
Checking file or directory for syntax compliance. like:
### Thought: I need to check the syntax of the file.
### Action:
{BASH_FENCE[0]} 
syntax_check -f a.py
{BASH_FENCE[1]}
</syntax check>
"""
    }
    web_browse = {
        "command": "web_browse -q 'query'",
        "description": f"""
<web browse>
Search the web for answers to the query. like:
### Thought: I want to search the web for answers to the query.
### Action:
{BASH_FENCE[0]} 
web_browse -q query
{BASH_FENCE[1]}
</web browse>
"""
    }
    screenshot_analyse = {
    "command": "screenshot_analyse -f 'html_file_path' [-q 'query'] [-a '[actions...]']",
    "description": f"""
<screenshot analyse>
Provide an HTML file, and this command will render it into a screenshot, with analysis provided by a software expert. Optionally, you can specify actions to interact with the content before taking the screenshot or ask questions about the screenshot.
Supported actions:
- click: Click an element (selector).
- fill: Fill an input field (selector, text).
- hover: Hover over an element (selector).
- scroll: Scroll an element (selector, x, y).

Example usage:
### Thought: I want to get the screenshot analysis from the front-end code file and perform some interactions.
### Action:
{BASH_FENCE[0]} 
screenshot_analyse -f a.html -q "What's in the screenshot?" -a '["click:#buttonId", "fill:#inputId:Hello", "hover:#elementId", "scroll:#scrollableElement:10:20"]'
{BASH_FENCE[1]}

Note: Only targets HTML files. Embed CSS/JS into an HTML file for proper rendering. The -q (query) and -a (actions) parameters are optional.
</screenshot analyse>
"""
    }
