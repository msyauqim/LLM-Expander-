"""LLM Prompter: generate 3 prompts (CSS/HTML/JS) + variable registry.

Prompts dibangun secara programmatic dari game_spec JSON.
"""
import json
from pipeline.models import GameSpec, PromptTriple, VariableRegistry
from pipeline import cache


def generate_prompts(game_spec: GameSpec, rag_summary: str) -> PromptTriple:
    """Generate 3 prompts + variable registry dari game spec."""
    spec_json = json.dumps(game_spec.data, ensure_ascii=False, indent=2)

    cache_key = f"prompter_v2:{spec_json[:500]}"
    cached = cache.get(cache_key)
    if cached:
        print("  [cache hit] Prompts")
        return _parse_prompt_triple(json.loads(cached))

    print("  [prompter] Building prompts dari game spec...")
    data = build_prompts_from_spec(game_spec.data, rag_summary)

    cache.put(cache_key, json.dumps(data, ensure_ascii=False))
    sv = data.get("shared_variables", {})
    print(f"  [prompter] Registry: {len(sv.get('dom_ids',[]))} IDs, {len(sv.get('js_variables',[]))} vars, {len(sv.get('js_functions',[]))} funcs")
    print(f"  [prompter] CSS prompt: {len(data['css_prompt'])} chars")
    print(f"  [prompter] HTML prompt: {len(data['html_prompt'])} chars")
    print(f"  [prompter] JS prompt: {len(data['js_prompt'])} chars")

    return _parse_prompt_triple(data)


def build_prompts_from_spec(spec: dict, rag_summary: str = "") -> dict:
    """Build 3 prompts + registry langsung dari game spec dict."""
    meta = spec.get("metadata", {})
    pres = spec.get("presentation", {})
    visual = pres.get("visual_element", {})
    canvas = visual.get("canvas_scene", {})
    ui = visual.get("ui_components", {})
    palette = visual.get("color_palette", {})
    payload = spec.get("payload", {})
    gameplay = spec.get("gameplay_parameters", {})
    win_lose = spec.get("win_lose_condition", {})

    game_type = spec.get("game_type", meta.get("game_type", "word_game"))
    title = meta.get("title", "Game Edukasi")
    subject = meta.get("subject", "Fisika")
    grade = meta.get("grade_level", "SMA-10")
    difficulty = meta.get("difficulty", 2)
    duration = meta.get("estimated_duration_minutes", 15)

    theme_name = visual.get("theme_name", "Science Lab")
    theme_preset = visual.get("theme_preset", "minimal")
    mood = visual.get("mood", "focused")
    gradient_bg = visual.get("gradient_bg", f"linear-gradient(135deg, {palette.get('background','#f8fafc')} 0%, #e3f2fd 100%)")
    setting_desc = visual.get("setting_description", "Ruangan belajar modern")
    art_style = visual.get("art_style", "flat modern")
    ambient = visual.get("ambient_elements", [])

    bg_layers = canvas.get("background_layers", [])
    objects = canvas.get("objects", [])
    particles = canvas.get("particle_effects", [])

    lives = gameplay.get("lives", 3)
    time_limit = gameplay.get("time_limit_seconds", 300)
    pass_threshold = gameplay.get("pass_threshold", 70)
    scoring = gameplay.get("scoring", {})

    # === SHARED VARIABLE REGISTRY (dengan Variable Register Extractor) ===
    print("  [prompter] Extracting variables from spec...")
    registry = _build_registry(game_type, payload, spec=spec)

    # === CSS PROMPT (flexible format - React or vanilla) ===
    css_prompt = f"""Styling untuk game: "{title}" ({theme_preset})

Format: Anda bebas pilih - CSS vanilla, Tailwind, atau CSS-in-JS di React (apapun yang terbaik)

COLOR PALETTE:
- Primary: {palette.get('primary', '#1E90FF')}
- Secondary: {palette.get('secondary', '#FF6347')}
- Background: {palette.get('background', '#f8fafc')}
- Text: {palette.get('text', '#333333')}
- Gradient: {gradient_bg}

REQUIREMENTS:
1. Dark/modern theme, gradient background
2. Buttons dengan hover effects & shadows
3. Cards dengan transparency & blur
4. Smooth animations & transitions
5. Responsive design
6. Particles dengan animation kalau perlu
7. Game area dengan proper contrast

IDs/Classes: {', '.join(registry['dom_ids'][:5])}... (adjust sesuai format yang dipilih)
"""

    # === HTML/COMPONENT PROMPT (flexible format) ===
    opening = pres.get("opening", {})

    html_prompt = f"""Component/UI untuk game: "{title}" ({game_type})
Subject: {subject} {grade}

FORMAT: Pilih yang terbaik - HTML vanilla, JSX React, atau Vue/Svelte component

STRUKTUR DASAR:
- Screen menu/start dengan tombol "Mulai"
- Screen game dengan content game-specific
- Screen hasil/end dengan score & tombol restart
- Popup instructions & hints
- Displays untuk score, lives, timer

GAME TYPE: {game_type}"""

    if game_type == "sim_lab":
        variables = [v for v in payload.get("variables", []) if v.get("role") == "user_input"]
        if variables:
            html_prompt += f"\n- {len(variables)} sliders/inputs untuk simulate variables"

    elif game_type == "word_game":
        questions = payload.get("questions", [])
        html_prompt += f"\n- {len(questions)} soal dengan input jawaban + check"

    elif game_type == "puzzle_game":
        pairs = payload.get("pairs", [])
        html_prompt += f"\n- {len(pairs)} pasangan untuk match/drag-drop"

    html_prompt += f"""

PENTING:
- Semua UI dalam Bahasa Indonesia
- Interactive & responsive
- Dark theme dengan good contrast
- Clean, modern design
- Game state management (start/playing/end)

Element kunci: start button, game area, input fields, submit button, score display, timer, instructions modal
"""

    # === JS LOGIC PROMPT (flexible format - React or vanilla) ===
    js_prompt = f"""Logic untuk game: "{title}" ({game_type})

FORMAT: Pilih yang terbaik
- Vanilla JavaScript
- React dengan hooks (useState, useEffect, useRef)
- Vue / Svelte component
- Atau apapun yang paling elegant!

REQUIREMENTS:
1. Game flow: menu → playing → results
2. State: gameState, score, lives={lives}, timeLeft={time_limit}s, isRunning
3. Timer countdown dengan display update
4. Score tracking & win condition (score >= {pass_threshold})
5. Instructions & hints (popup/modal)
6. Smooth animations & transitions
7. Responsive & interactive

GAMEPLAY ({game_type}):
"""

    if game_type == "sim_lab":
        user_vars = [v for v in payload.get("variables", []) if v.get("role") == "user_input"]
        if user_vars:
            js_prompt += f"- {len(user_vars)} sliders dengan real-time calculation\n"

    elif game_type == "word_game":
        questions = payload.get("questions", [])
        js_prompt += f"- {len(questions)} soal, check jawaban, progress tracking\n"

    elif game_type == "puzzle_game":
        pairs = payload.get("pairs", [])
        js_prompt += f"- {len(pairs)} pasangan untuk match dengan feedback visual\n"

    js_prompt += f"""
TARGET: Enterprise-grade quality dengan smooth UX, proper state management, error handling
"""

    if rag_summary:
        js_prompt += f"\nKONTEKS MATERI:\n{rag_summary[:300]}\n"

    result = {
        "css_prompt": css_prompt,
        "html_prompt": html_prompt,
        "js_prompt": js_prompt,
        "shared_variables": registry
    }
    return result


def extract_variables_from_spec(spec: dict) -> dict:
    """Ekstrak semua variabel, DOM IDs, dan function names dari JSON spec secara rekursif.

    Scan seluruh JSON spec untuk field: id, name, variable_name, element_id,
    function_name, js_var, css_class, dll.
    """
    extracted_ids = []
    extracted_vars = []
    extracted_classes = []
    extracted_functions = []

    ID_KEYS = {"id", "element_id", "dom_id", "target_id", "source_id", "object_id"}
    VAR_KEYS = {"name", "variable_name", "js_var", "var_name", "param"}
    CLASS_KEYS = {"css_class", "class_name", "className", "css_classes"}
    FUNC_KEYS = {"function_name", "js_function", "handler", "callback", "on_click"}

    def _recurse(node):
        if isinstance(node, dict):
            for key, val in node.items():
                k = key.lower()
                if k in ID_KEYS and isinstance(val, str) and val:
                    extracted_ids.append(val)
                elif k in VAR_KEYS and isinstance(val, str) and val:
                    extracted_vars.append(val)
                elif k in CLASS_KEYS:
                    if isinstance(val, str) and val:
                        extracted_classes.append(val)
                    elif isinstance(val, list):
                        extracted_classes.extend([v for v in val if isinstance(v, str)])
                elif k in FUNC_KEYS and isinstance(val, str) and val:
                    extracted_functions.append(val)
                _recurse(val)
        elif isinstance(node, list):
            for item in node:
                _recurse(item)

    _recurse(spec)

    return {
        "extracted_ids": list(dict.fromkeys(extracted_ids)),
        "extracted_vars": list(dict.fromkeys(extracted_vars)),
        "extracted_classes": list(dict.fromkeys(extracted_classes)),
        "extracted_functions": list(dict.fromkeys(extracted_functions)),
    }


def _build_registry(game_type: str, payload: dict, spec: dict = None) -> dict:
    """Build shared variable registry sesuai game_type + hasil Variable Register Extractor."""
    # Base DOM IDs yang selalu ada
    dom_ids = [
        "game-container", "scene-area", "content-area",
        "score-display", "lives-display", "timer-display",
        "start-screen", "game-screen", "end-screen",
        "instructions-btn", "instructions-popup",
        "hint-btn", "hint-popup",
        "feedback-area", "overlay"
    ]

    css_classes = [
        "hidden", "active", "correct", "incorrect",
        "btn-primary", "btn-secondary", "card",
        "particle", "glow", "fade-in", "shake"
    ]

    js_variables = [
        "gameState", "score", "lives", "timeLeft",
        "currentQuestion", "totalQuestions", "isRunning"
    ]

    js_functions = [
        "initGame", "startGame", "endGame",
        "updateScore", "updateTimer", "showFeedback",
        "showInstructions", "hideInstructions",
        "showHint", "hideHint", "spawnParticle"
    ]

    if game_type == "sim_lab":
        variables = payload.get("variables", [])
        scene = payload.get("scene", {})
        interactive = scene.get("interactive_objects", [])
        visual_fb = scene.get("visual_feedback", [])

        for v in variables:
            vid = v.get("id", v.get("name", ""))
            if vid:
                if v.get("role") == "user_input" or v.get("type") == "user_input":
                    dom_ids.append(f"{vid}-slider")
                    dom_ids.append(f"{vid}-value")
                dom_ids.append(f"{vid}-display")
                js_variables.append(vid)

        for obj in interactive:
            oid = obj.get("id", "")
            if oid:
                dom_ids.append(oid)

        for vf in visual_fb:
            vid = vf.get("id", "")
            if vid:
                dom_ids.append(vid)

        js_functions += ["calculateFormula", "updateVisualFeedback",
                         "updateInteractiveObjects", "runSimulation"]
        css_classes += ["slider-container", "value-display", "bar-fill",
                        "sim-object", "sim-active", "electron"]

    elif game_type == "word_game":
        dom_ids += ["question-area", "answer-input", "submit-btn",
                    "next-btn", "word-bank", "progress-bar"]
        js_functions += ["showQuestion", "checkAnswer", "nextQuestion", "shuffleArray"]
        js_variables += ["questions", "currentIndex", "answers"]
        css_classes += ["word-card", "selected", "matched", "progress-fill"]

    elif game_type == "puzzle_game":
        dom_ids += ["puzzle-area", "choices-area", "next-btn",
                    "progress-bar", "match-count"]
        js_functions += ["handleSelection", "checkMatch", "nextStage", "shuffleArray"]
        js_variables += ["pairs", "selectedItem", "matchedCount", "currentStage"]
        css_classes += ["puzzle-item", "selected", "matched", "dragging", "drop-zone"]

    # Merge hasil Variable Register Extractor dari JSON spec
    if spec is not None:
        extracted = extract_variables_from_spec(spec)
        dom_ids = list(dict.fromkeys(dom_ids + extracted["extracted_ids"]))
        css_classes = list(dict.fromkeys(css_classes + extracted["extracted_classes"]))
        js_variables = list(dict.fromkeys(js_variables + extracted["extracted_vars"]))
        js_functions = list(dict.fromkeys(js_functions + extracted["extracted_functions"]))

    return {
        "dom_ids": list(dict.fromkeys(dom_ids)),
        "css_classes": list(dict.fromkeys(css_classes)),
        "js_variables": list(dict.fromkeys(js_variables)),
        "js_functions": list(dict.fromkeys(js_functions))
    }


def _parse_prompt_triple(data: dict) -> PromptTriple:
    sv = data.get("shared_variables", {})
    registry = VariableRegistry(
        dom_ids=sv.get("dom_ids", []),
        css_classes=sv.get("css_classes", []),
        js_variables=sv.get("js_variables", []),
        js_functions=sv.get("js_functions", []),
    )
    return PromptTriple(
        css_prompt=data["css_prompt"],
        html_prompt=data["html_prompt"],
        js_prompt=data["js_prompt"],
        registry=registry,
    )
