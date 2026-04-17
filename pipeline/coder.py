"""Stage 4: 3 Specialist Coders (CSS, HTML, JS) via HF Space."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pipeline.models import PromptTriple, VariableRegistry, AssembledGame
from pipeline.llm_client import call_hf_space, extract_code_from_response
from pipeline.assembler import assemble
from pipeline.validator import validate, simple_fix


MAX_VALIDATION_RETRIES = 3


def _build_specialist_prompt(role: str, prompt: str, registry: VariableRegistry) -> str:
    """Build specialist prompt dengan context dari Variable Registry Extractor."""
    def _fmt(items, label):
        items = list(items)
        shown = ', '.join(items[:10])
        more = f" (+{len(items)-10} lagi)" if len(items) > 10 else ""
        return f"- {label}: {shown}{more}"

    context = f"""
## Shared Variable Registry untuk {role.upper()} specialist:
(Semua specialist WAJIB pakai nama yang sama agar CSS/HTML/JS konsisten)
{_fmt(registry.dom_ids, 'DOM IDs')}
{_fmt(registry.css_classes, 'CSS Classes')}
{_fmt(registry.js_variables, 'JS Variables')}
{_fmt(registry.js_functions, 'JS Functions')}
"""
    return context + "\n" + prompt


def _call_specialist(role: str, prompt: str, registry: VariableRegistry) -> str:
    """Call specialist LLM untuk satu role (CSS/HTML/JS)."""
    full_prompt = _build_specialist_prompt(role, prompt, registry)
    
    system_prompt = f"""Kamu adalah {role.upper()} specialist untuk game edukasi HTML.
Output HANYA code yang diminta, tanpa penjelasan, tanpa markdown.
Pastikan semua DOM IDs dan CSS classes sesuai dengan context yang diberikan."""
    
    print(f"    [{role.upper()}] Calling HF Space Qwen3-Coder...")
    raw = call_hf_space(full_prompt, system_prompt=system_prompt)
    code = extract_code_from_response(raw)
    print(f"    [{role.upper()}] Generated {len(code)} chars")
    return code


def run_coder_stage(prompt_triple: PromptTriple) -> AssembledGame:
    """Run 3 specialists in parallel using HF Space."""
    print("\n[Coder Stage] 3 Parallel HF Space Specialists...")
    
    registry = prompt_triple.registry
    
    # Run 3 specialists in parallel
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_call_specialist, "css", prompt_triple.css_prompt, registry): "css",
            pool.submit(_call_specialist, "html", prompt_triple.html_prompt, registry): "html",
            pool.submit(_call_specialist, "js", prompt_triple.js_prompt, registry): "js",
        }
        
        results = {}
        for future in futures:
            role = futures[future]
            results[role] = future.result()
    
    css_code = results["css"]
    html_code = results["html"]
    js_code = results["js"]
    
    # Assemble
    print("\n[Assembler] Gabung CSS + HTML + JS...")
    game = assemble(css_code, html_code, js_code)
    
    # Validate & auto-fix
    print("\n[Validator] Cek struktur HTML & syntax...")
    for attempt in range(MAX_VALIDATION_RETRIES):
        result = validate(game, registry)
        if result.passed:
            print(f"  ✅ Validation passed!")
            break
        
        print(f"  ❌ Attempt {attempt+1}/{MAX_VALIDATION_RETRIES} failed:")
        for err in result.errors:
            print(f"     - {err}")
        
        if attempt < MAX_VALIDATION_RETRIES - 1:
            print(f"  🔧 Auto-fixing...")
            game = simple_fix(game, result.errors)
        else:
            print(f"  ⚠️  Max retries reached, melanjutkan dengan output yang ada...")
    
    return game


def rerun_specialist(role: str, revised_prompt: str, registry: VariableRegistry, original_game: AssembledGame) -> AssembledGame:
    """Re-run single specialist dengan feedback guru."""
    print(f"\n[Revise] Re-running {role.upper()} specialist...")
    
    code = _call_specialist(role, revised_prompt, registry)
    
    # Assemble dengan code baru
    if role == "css":
        game = assemble(code, original_game.html_raw, original_game.js_raw)
    elif role == "html":
        game = assemble(original_game.css_raw, code, original_game.js_raw)
    else:  # js
        game = assemble(original_game.css_raw, original_game.html_raw, code)
    
    # Validate
    result = validate(game, registry)
    if not result.passed:
        print(f"  ⚠️  Validation failed: {result.errors}")
        game = simple_fix(game, result.errors)
    
    return game
