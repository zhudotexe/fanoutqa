from itertools import islice

from markdownify import MarkdownConverter


def batched(iterable, n):
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


# markdownification
def yeet(*_):
    return ""


def is_valid_url(x):
    if not x:
        return False
    return not x.startswith("data:")


class MDConverter(MarkdownConverter):
    def convert_img(self, el, text, convert_as_inline):
        alt = el.attrs.get("alt", None) or ""
        return f"![{alt}](image)"

    def convert_a(self, el, text, convert_as_inline):
        return text

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def convert_div(self, el, text, convert_as_inline):
        content = text.strip()
        if not content:
            return ""
        return f"{content}\n"

    # sometimes these appear inline and are just annoying
    convert_script = yeet
    convert_style = yeet


def markdownify(html: str):
    return MDConverter(heading_style="atx").convert(html)
