"""Validator: cek assembled HTML valid, konsisten, dan logika game bisa jalan."""
import re
from pipeline.models import AssembledGame, ValidationResult, VariableRegistry


# ID yang dianggap kritikal agar game bisa berjalan
CRITICAL_DOM_IDS = {"start-btn", "game-container"}

# Function JS minimal yang harus ada agar game punya flow
REQUIRED_JS_FUNCTIONS = {"start", "init"}  # minimal salah satu match substring

# Event handler yang menandakan game interaktif
INTERACTIVE_PATTERNS = [
    r"addEventListener\s*\(",
    r"onclick\s*=",
    r"\.on[A-Z]\w+\s*=",
]


def validate(game: AssembledGame, registry: VariableRegistry) -> ValidationResult:
    """Validasi assembled HTML + konsistensi variabel + logika game."""
    errors = []
    warnings = []

    # === 1. Basic HTML structure ===
    if "<body" not in game.html.lower():
        errors.append("Missing <body> tag")
    if "<script>" not in game.html and "script" not in game.html.lower():
        errors.append("No JavaScript found")

    # === 2. Content tidak kosong ===
    if len(game.html_raw) < 100:
        errors.append("HTML content too short")
    if len(game.js_raw) < 100:
        errors.append("JS content too short")

    # === 3. JS syntax - kurung balance ===
    open_braces = game.js_raw.count('{')
    close_braces = game.js_raw.count('}')
    if open_braces > 0 and abs(open_braces - close_braces) > 2:
        errors.append("JS braces unbalanced")

    open_paren = game.js_raw.count('(')
    close_paren = game.js_raw.count(')')
    if abs(open_paren - close_paren) > 2:
        errors.append("JS parentheses unbalanced")

    # === 4. Logika game bisa berjalan ===
    logic_errors = _validate_game_logic(game)
    errors.extend(logic_errors)

    # === 5. Konsistensi variabel antar HTML/CSS/JS ===
    consistency_errors = _validate_variable_consistency(game, registry)
    errors.extend(consistency_errors)

    return ValidationResult(passed=len(errors) == 0, errors=errors)


def _validate_game_logic(game: AssembledGame) -> list:
    """Cek apakah game punya flow logic yang bisa jalan."""
    errors = []
    js = game.js_raw.lower()

    html_lower = game.html_raw.lower()

    # a. Harus ada event handler (cek JS dan HTML inline onclick)
    has_interactive = any(re.search(p, game.js_raw) for p in INTERACTIVE_PATTERNS)
    has_inline_onclick = "onclick=" in html_lower or "onchange=" in html_lower or "onsubmit=" in html_lower
    if not has_interactive and not has_inline_onclick:
        errors.append("Game logic: no event listeners / onclick handlers (game tidak interaktif)")

    # b. Harus ada function start/init (entry point)
    has_entry = any(
        re.search(rf"function\s+\w*{kw}\w*\s*\(", js) or
        re.search(rf"\b\w*{kw}\w*\s*=\s*(function|\(.*\)\s*=>)", js) or
        re.search(rf"const\s+\w*{kw}\w*\s*=", js)
        for kw in REQUIRED_JS_FUNCTIONS
    )
    if not has_entry:
        errors.append("Game logic: no start/init function (game tidak punya entry point)")

    # c. Harus ada state management (score, gameState, dll)
    state_keywords = ["score", "gamestate", "lives", "timeleft", "currentquestion", "current", "state", "answer"]
    has_state = any(kw in js for kw in state_keywords)
    if not has_state:
        errors.append("Game logic: no state variables (score/gameState/lives tidak ditemukan)")

    # d. Harus ada DOM manipulation (cek JS dan HTML inline)
    dom_patterns = [r"getelementbyid", r"queryselector", r"innerhtml", r"textcontent", r"classlist"]
    has_dom = any(re.search(p, js) for p in dom_patterns)
    has_dom_html = any(tag in html_lower for tag in ["<input", "<button", "<select", "<textarea"])
    if not has_dom and not has_dom_html:
        errors.append("Game logic: no DOM manipulation (UI tidak akan update)")

    return errors


def _validate_variable_consistency(game: AssembledGame, registry: VariableRegistry) -> list:
    """Cek konsistensi nama DOM IDs dan CSS classes antar HTML/CSS/JS."""
    errors = []

    # Ekstrak semua IDs yang di-reference JS lewat getElementById / querySelector('#...')
    js_referenced_ids = set(re.findall(r"getElementById\s*\(\s*['\"]([^'\"]+)['\"]", game.js_raw))
    js_referenced_ids |= set(re.findall(r"querySelector(?:All)?\s*\(\s*['\"]#([a-zA-Z][\w-]*)", game.js_raw))

    # Ekstrak semua IDs yang benar-benar ada di HTML
    html_ids = set(re.findall(r'id\s*=\s*["\']([^"\']+)["\']', game.html_raw))

    # a. Setiap ID yang di-reference JS HARUS ada di HTML
    missing_in_html = js_referenced_ids - html_ids
    if missing_in_html:
        errors.append(
            f"Variable inconsistency: JS reference ID yang tidak ada di HTML: {sorted(missing_in_html)[:5]}"
        )

    # b. Critical IDs harus ada di HTML
    for critical in CRITICAL_DOM_IDS:
        if critical not in html_ids and critical in game.js_raw:
            errors.append(f"Missing critical DOM ID: {critical}")

    # c. CSS classes yang di-reference JS (classList.add/toggle) harus ada di CSS
    js_referenced_classes = set(re.findall(
        r"classList\.(?:add|toggle|remove|contains)\s*\(\s*['\"]([^'\"]+)['\"]",
        game.js_raw
    ))
    # Tambah class yang di-reference via querySelector('.class')
    js_referenced_classes |= set(re.findall(
        r"querySelector(?:All)?\s*\(\s*['\"]\.([a-zA-Z][\w-]*)",
        game.js_raw
    ))

    # Ekstrak class yang didefinisikan di CSS (cari selector .classname)
    css_classes = set(re.findall(r"\.([a-zA-Z][\w-]+)\s*[{,:]", game.css_raw))

    missing_in_css = js_referenced_classes - css_classes
    # Filter class built-in JS (e.g., kelas dari framework) dan class yang di-ignore
    missing_in_css = {c for c in missing_in_css if len(c) > 1}
    if missing_in_css:
        # Warning, bukan error (JS boleh pakai class tanpa styling)
        sample = sorted(missing_in_css)[:3]
        errors.append(
            f"Variable inconsistency: CSS class dipakai JS tapi tidak ada di CSS: {sample}"
        )

    # d. Registry check - DOM IDs yang diekspektasi tidak digunakan sama sekali
    expected_ids = set(registry.dom_ids[:10]) if registry.dom_ids else set()
    unused_expected = expected_ids - html_ids - js_referenced_ids
    if len(unused_expected) > len(expected_ids) * 0.5 and expected_ids:
        # Lebih dari 50% ID registry tidak terpakai → specialist tidak ikut registry
        errors.append(
            f"Variable inconsistency: {len(unused_expected)}/{len(expected_ids)} "
            f"registry IDs tidak digunakan di HTML/JS"
        )

    return errors


def simple_fix(game: AssembledGame, errors: list) -> AssembledGame:
    """Auto-fix common issues."""
    css = game.css_raw
    html = game.html_raw
    js = game.js_raw

    for err in errors:
        # Fix unclosed braces in JS
        if "braces unbalanced" in err or "braces tidak balanced" in err:
            diff = js.count('{') - js.count('}')
            if diff > 0:
                js += '\n' + '}' * diff
            elif diff < 0:
                # Too many closing braces - comment them out
                open_count = js.count('{')
                close_count = js.count('}')
                if close_count > open_count:
                    # Try to add missing opening braces
                    js = js.replace('function ', 'function ') # placeholder for missing functions

        # Fix missing critical IDs (add them to HTML if needed)
        match = re.search(r"Missing critical DOM ID: (\w+)", err)
        if match:
            missing_id = match.group(1)
            # Add placeholder div for missing ID
            if missing_id == "game-container":
                html = f'<div id="game-container">{html}</div>'
            elif missing_id == "scene-area":
                html = html.replace('<div id="content-area">', '<div id="scene-area"><div id="content-area">')
                html += '</div><!-- close scene-area -->'
            elif missing_id not in html:
                # Add generic div for other missing IDs
                html += f'\n<div id="{missing_id}"></div>'

        # Fix missing button IDs if referenced in JS
        if "start-btn" in err and 'id="start-btn"' not in html:
            html = html.replace('</div></div>', f'<button id="start-btn">Mulai</button>\n</div></div>', 1)

    from pipeline.assembler import assemble
    return assemble(css, html, js)
