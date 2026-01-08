import html


def escape_html(value: str) -> str:
    return html.escape(value, quote=True)
