"""Assembler: gabung CSS + HTML + JS menjadi 1 file HTML."""
from pipeline.models import AssembledGame


def assemble(css: str, html: str, js: str) -> AssembledGame:
    """Gabung 3 output specialist menjadi 1 file HTML self-contained."""
    full_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Game Edukasi</title>
<style>
{css}
</style>
</head>
<body>
{html}
<script>
{js}
</script>
</body>
</html>"""

    return AssembledGame(html=full_html, css_raw=css, html_raw=html, js_raw=js)
