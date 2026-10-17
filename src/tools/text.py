from pathlib import Path

_ESCAPE_MAP=(
    ("\\n", "\n"), # def hello(): \\n print("Hello, World") -> def hello(): \n print("Hello, World")
    ("\\t", "\t"),
    ("\\r", "\r"),
    ("\\b", "\b"),
    ("\\f", "\f"),
)


"""
For markdown, some models give <h1> hello </h1> as &lt;h1&gt; hello &lt;/h1&gt;
We need to convert them to actual html tags by replacing the html entities.
"""
_HTML_ENTITIES=(
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&amp;", "&"),
    ("&quot;", "\""),
    ("&apos;", "'"),
    ("&copy;", "©"),
    ("&reg;", "®"),
    ("&trade;", "™"),
)


_MARKDOWN_SUFFIXES={".md", ".markdown", ".mdx"}
_MARKUP_SUFFIXES={".html", ".htm", ".xhtml", ".xml", ".svg"}


def looks_like_escaped_source(text: str)->bool:
    """
    True when the payload is one logical line stuffed with \\n sequences.
    To check if the model has generated a multi line text or created a single line text with lots of \\n
    """

    if "\\n" not in text:
        return False
    
    return text.count("\\n")<=1


def normalize_source_text(text: str)->str:
    """
    Turn escaped newlines/tabs into actual newlines/tabs.
    """

    if not looks_like_escaped_source(text):
        return text
    
    normalized=text
    for escaped, actual in _ESCAPE_MAP:
        normalized=normalized.replace(escaped, actual)
    
    return normalized


def unescaped_html_entities(text: str)->str:
    """
    Convert html entities to actual html tags, as some weaker models emit those instead of raw <, > etc
    """

    if "&" not in text:
        return text

    unescaped=text
    for entity, actual in _HTML_ENTITIES:
        unescaped=unescaped.replace(entity, actual)
    
    return unescaped


def strip_markdown_fence(text: str)->str:
    """
    Removes the markdown code fences (```python ... ``` or ``` ... ```) from the text.
    """

    if "```" not in text:
        return text
    
    # splitting the text into list of lines
    lines=text.split("\n")

    # removing the starting fence
    if lines and lines[0].lstrip().startswith("```"):
        lines=lines[1:]
    
    # removing the trailing fence
    if lines and lines[-1].rstrip().endswith("```"):
        lines=lines[:-1]

    return "\n".join(lines)


def prepare_file_content(text: str, path: str)->str:
    """
    Prepares the file content for writing to a file.

    1. Converts escaped newlines/tabs into actual newlines/tabs.
    2. Removes the markdown code fences (```python ... ``` or ``` ... ```) from the text.
    3. Converts html entities to actual html tags, as some weaker models emit those instead of raw <, > etc
    """

    suffix=Path(path).suffix.lower()
    prepared=normalize_source_text(text)

    if suffix not in _MARKDOWN_SUFFIXES:
        prepared=strip_markdown_fence(prepared)
    
    if suffix not in _MARKUP_SUFFIXES:
        prepared=unescaped_html_entities(prepared)
    
    return prepared
