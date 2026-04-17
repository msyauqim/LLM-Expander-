"""
04_pipeline.py
Pipeline lengkap: Prompt guru → LLM Expander → (opsional) Qwen3-Coder-WebDev API.
Jalankan: python 04_pipeline.py
"""
import json
import os
import torch
import requests
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Konfigurasi
BASE_MODEL = "Qwen/Qwen3-4B"
LORA_PATH = os.path.join(os.path.dirname(__file__), "output", "prompt-expander-lora")

# HuggingFace Space API (Qwen3-Coder-WebDev)
HF_SPACE_URL = "https://qwen-qwen3-coder-webdev.hf.space"

SYSTEM_PROMPT_TEXT = (
    "Kamu adalah asisten AI khusus pembuat prompt untuk game edukasi fisika "
    "berbasis web. Tugasmu adalah mengubah prompt sederhana dari guru menjadi "
    "prompt yang sangat detail, mencakup: (1) penjelasan materi fisika yang "
    "relevan, (2) mekanika game yang sesuai, (3) komponen web (HTML, CSS, "
    "JavaScript) yang diperlukan, dan (4) elemen interaktif untuk siswa."
)

SYSTEM_PROMPT_JSON = (
    "Kamu adalah asisten AI pembuat game edukasi. Tugasmu mengubah prompt "
    "sederhana dari guru menjadi JSON game edukasi yang lengkap dan valid "
    "sesuai schema v1.2. Output HARUS berupa JSON valid tanpa teks tambahan.\n\n"
    "ATURAN KETAT untuk setiap field:\n"
    '- schema_version: selalu "1.2"\n'
    '- game_id: format "game_{subject}{grade}_{topic}_{number}" contoh: "game_phys10_kin_word_001"\n'
    '- game_type: HANYA "word_game" | "puzzle_game" | "sim_lab"\n'
    "- metadata:\n"
    '  - subject: HANYA "Fisika" | "Kimia" | "Biologi" | "Matematika"\n'
    '  - grade_level: HANYA "SMA-10" | "SMA-11" | "SMA-12"\n'
    "  - difficulty: integer 1-5 (BUKAN string)\n"
    "  - estimated_duration_minutes: integer 5-60\n"
    "  - learning_objectives: array of string, 1-5 item, tanpa prefix dash\n"
    '  - language: selalu "id"\n'
    "- presentation:\n"
    "  - opening: OBJECT {id, show_once, title, story, image_description, cta_text}\n"
    "  - visual_element: OBJECT {theme_name, theme_preset, mood, color_palette{primary,secondary,background,accent,text}, setting_description, art_style}\n"
    '    - theme_preset: HANYA "classroom"|"scifi_neon"|"nature"|"retro"|"minimal"|"adventure"\n'
    "    - color_palette: semua nilai hex format #RRGGBB\n"
    "  - instructions: OBJECT {id, trigger{type,position,icon,label}, steps[{step,text}]}\n"
    "  - hint: OBJECT {id, scope, trigger{type,after_seconds,dismissible,reusable,manual_trigger_available}, content{title,strategy,formula,example,hint_image_description}}\n"
    "  - audio: OBJECT {enabled, tracks[{id,event,description}]}\n"
    '    - event: HANYA "on_correct_action"|"on_wrong_action"|"on_win"|"on_lose"|"background"\n'
    "- payload: HARUS sesuai game_type\n"
    "  - word_game: {instruction, word_bank[], questions[{id,type,prompt,answer,explanation}]}\n"
    '    - type: "fill_blank"|"match_pair"|"crossword_clue"|"unscramble"\n'
    "  - puzzle_game: {instruction, stages[{stage_id,title,description,challenges[{id,type,prompt,answer,explanation}]}]}\n"
    '    - type: "multiple_choice"|"drag_sort"|"drag_match"|"calculate"|"true_false"\n'
    "  - sim_lab: {instruction, variables[{name,label,unit,min,max,default,step}], formula{expression,description}, sim_steps[{step,action}], analysis_questions[{id,question,expected_answer}]}\n"
    "- win_lose_condition: OBJECT {applicable, win{description,logic,feedback_text,feedback_audio}, lose{description,logic,feedback_text,feedback_audio,retry_allowed}}\n"
    "- gameplay_parameters: OBJECT {scoring{}, lives, time_limit_seconds, pass_threshold}\n"
)

# Default ke mode JSON schema
SYSTEM_PROMPT = SYSTEM_PROMPT_JSON


def load_expander_model():
    """Load Prompt Expander model (base + LoRA)."""
    print("📦 Memuat Prompt Expander model...")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        trust_remote_code=True,
    )

    if os.path.exists(LORA_PATH):
        model = PeftModel.from_pretrained(base_model, LORA_PATH)
        print("✅ LoRA adapter loaded!")
    else:
        print("⚠️  LoRA tidak ditemukan, menggunakan base model.")
        model = base_model

    model.eval()
    return model, tokenizer


def expand_prompt(model, tokenizer, simple_prompt: str) -> str:
    """Step 1: Expand prompt sederhana → JSON game edukasi."""
    # Tambah instruksi eksplisit agar output JSON
    enforced_prompt = (
        f"{simple_prompt}\n\n"
        "PENTING: Jawab HANYA dengan JSON valid. "
        "Mulai langsung dengan karakter {{ dan akhiri dengan }}. "
        "Jangan tambahkan teks, markdown, atau penjelasan apapun di luar JSON."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": enforced_prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

    # Tambahkan prefix JSON agar model mulai dari '{'
    text += "{"

    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.3,
            top_p=0.85,
            repetition_penalty=1.15,
            do_sample=True,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    result = tokenizer.decode(new_tokens, skip_special_tokens=True)

    # Prefix kembali dengan '{' karena kita sudah inject di prompt
    if not result.strip().startswith("{"):
        result = "{" + result

    return result


def send_to_coder(detailed_prompt: str, game_json: dict = None) -> dict:
    """Step 2: Kirim ke Qwen3-Coder-WebDev untuk generate game HTML."""
    print("\n🌐 Mengirim ke Qwen3-Coder-WebDev...")
    print(f"   URL: {HF_SPACE_URL}")

    # Jika ada game_json, buat prompt khusus untuk coder
    if game_json:
        meta = game_json.get("metadata", {})
        pres = game_json.get("presentation", {})
        coder_prompt = (
            f"Buatkan game edukasi web interaktif dalam SATU file HTML lengkap (HTML+CSS+JS).\n\n"
            f"=== SPESIFIKASI GAME ===\n"
            f"Judul: {meta.get('title', 'Game Edukasi')}\n"
            f"Tipe: {game_json.get('game_type', 'puzzle_game')}\n"
            f"Mata Pelajaran: {meta.get('subject', 'Fisika')} - {meta.get('grade_level', 'SMA')}\n"
            f"Topik: {meta.get('topik', '')}\n"
            f"Bab: {meta.get('bab', '')} > {meta.get('subbab', '')}\n"
            f"Kesulitan: {meta.get('difficulty', 2)}/5\n"
            f"Durasi: {meta.get('estimated_duration_minutes', 15)} menit\n\n"
            f"=== TUJUAN PEMBELAJARAN ===\n"
        )
        for obj in meta.get("learning_objectives", []):
            coder_prompt += f"- {obj}\n"

        # Presentation
        opening = pres.get("opening", {})
        visual = pres.get("visual_element", {})
        if opening:
            if isinstance(opening, dict):
                coder_prompt += (
                    f"\n=== NARASI PEMBUKA ===\n"
                    f"Judul: {opening.get('title', '')}\n"
                    f"Cerita: {opening.get('story', '')}\n"
                )
            else:
                coder_prompt += f"\n=== NARASI PEMBUKA ===\n{opening}\n"
        if visual:
            if isinstance(visual, dict):
                palette = visual.get("color_palette", {})
                coder_prompt += (
                    f"\n=== VISUAL ===\n"
                    f"Tema: {visual.get('theme_name', '')}\n"
                    f"Mood: {visual.get('mood', '')}\n"
                    f"Art Style: {visual.get('art_style', '')}\n"
                )
                if isinstance(palette, dict):
                    coder_prompt += (
                        f"Warna: primary={palette.get('primary','')}, "
                        f"secondary={palette.get('secondary','')}, "
                        f"bg={palette.get('background','')}, "
                        f"accent={palette.get('accent','')}\n"
                    )
            else:
                coder_prompt += f"\n=== VISUAL ===\n{visual}\n"

        # Payload
        coder_prompt += f"\n=== KONTEN GAME (PAYLOAD) ===\n{json.dumps(game_json.get('payload', {}), ensure_ascii=False, indent=2)}\n"

        # Gameplay
        gp = game_json.get("gameplay_parameters", {})
        coder_prompt += f"\n=== GAMEPLAY ===\n{json.dumps(gp, ensure_ascii=False, indent=2)}\n"

        # Win/lose
        wl = game_json.get("win_lose_condition", {})
        if wl.get("applicable"):
            coder_prompt += f"\n=== KONDISI MENANG/KALAH ===\n{json.dumps(wl, ensure_ascii=False, indent=2)}\n"

        coder_prompt += (
            f"\n=== INSTRUKSI TEKNIS ===\n"
            f"- Buat dalam SATU file HTML lengkap dengan inline CSS dan JavaScript\n"
            f"- Gunakan bahasa Indonesia untuk semua teks\n"
            f"- Desain responsif dan mobile-friendly\n"
            f"- Tambahkan animasi dan transisi yang smooth\n"
            f"- Tampilkan skor, nyawa, dan timer jika ada\n"
            f"- Tampilkan penjelasan setelah setiap jawaban\n"
        )
    else:
        coder_prompt = detailed_prompt

    # Kirim ke Gradio API
    try:
        from gradio_client import Client
        client = Client("Qwen/Qwen3-Coder-WebDev")
        print("   Tersambung ke API. Sedang men-generate game (bisa 1-3 menit)...")

        result = client.predict(
            input_value=coder_prompt,
            system_prompt_input_value="",
            api_name="/generate_code"
        )

        # result = (markdown_explanation, html_code)
        code_result = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else str(result)

        return {"status": "success", "data": code_result}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "suggestion": (
                "Gagal terhubung ke API Gradio.\n"
                "Copy-paste prompt detail secara manual ke "
                "https://huggingface.co/spaces/Qwen/Qwen3-Coder-WebDev"
            ),
        }


def validate_game_json(text: str) -> dict:
    """Coba parse output LLM sebagai JSON game. Return dict atau None."""
    import re

    # Step 1: Bersihkan markdown code blocks
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()

    # Step 2: Coba langsung parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Cari blok JSON terbesar (greedy dari { pertama ke } terakhir)
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Step 4: Coba fix common issues — trailing comma, single quotes
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1]
        # Remove trailing commas before } or ]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        # Replace single quotes with double quotes (heuristic)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Step 5: Coba truncate di } terakhir yang membuat valid JSON
    if first_brace != -1:
        partial = cleaned[first_brace:]
        # Cari } dari belakang, coba parse setiap kali
        for i in range(len(partial) - 1, 0, -1):
            if partial[i] == '}':
                try:
                    return json.loads(partial[:i + 1])
                except json.JSONDecodeError:
                    continue

    return None


def main():
    print("=" * 60)
    print("🎮 PIPELINE: Prompt Guru → LLM Expander → Game Generator")
    print("=" * 60)

    output_mode = "json"
    print("📋 Mode: JSON Schema v1.2")

    # Load model
    model, tokenizer = load_expander_model()

    print("\n" + "=" * 60)
    print("Ketik prompt sederhana, lalu tekan Enter.")
    print("Ketik 'quit' untuk keluar.")
    print("=" * 60)

    while True:
        game_data = None
        print()
        user_input = input("📝 [GURU] Prompt sederhana: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Sampai jumpa!")
            break
        if not user_input:
            continue

        # Step 1: Expand prompt
        print("\n⏳ Step 1: Mengembangkan prompt...")
        detailed = expand_prompt(model, tokenizer, user_input)

        print("\n" + "=" * 60)
        print("🤖 [LLM] OUTPUT:")
        print("=" * 60)

        # Validasi JSON jika mode json
        if output_mode == "json":
            game_data = validate_game_json(detailed)
            if game_data:
                # Pretty print
                pretty = json.dumps(game_data, ensure_ascii=False, indent=2)
                print(pretty)

                # Simpan JSON
                import datetime, re as _re
                json_output_dir = os.path.join(os.path.dirname(__file__), "generated_games")
                os.makedirs(json_output_dir, exist_ok=True)
                safe = _re.sub(r'[^a-zA-Z0-9]', '_', user_input.lower()[:40]).strip('_')
                safe = _re.sub(r'_+', '_', safe) or "game"
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                json_path = os.path.join(json_output_dir, f"{safe}_{ts}.json")
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(game_data, jf, ensure_ascii=False, indent=2)
                print(f"\n✅ JSON valid! Disimpan ke: {json_path}")

                # Cek field penting
                missing = []
                for key in ["schema_version", "game_id", "game_type", "metadata", "payload"]:
                    if key not in game_data:
                        missing.append(key)
                if missing:
                    print(f"⚠️  Field kurang: {', '.join(missing)}")
                else:
                    print(f"📋 game_type={game_data['game_type']}, title={game_data.get('metadata',{}).get('title','?')}")
            else:
                print(detailed)
                print("\n⚠️  Output bukan JSON valid. Menampilkan sebagai teks.")
        else:
            print(detailed)

        # Step 2: Tanya apakah mau kirim ke Coder
        print("\n" + "-" * 60)
        send_choice = input(
            "🔗 Kirim ke Qwen3-Coder-WebDev? (y/n/copy): "
        ).strip().lower()

        if send_choice == "y":
            result = send_to_coder(detailed, game_json=game_data if output_mode == "json" else None)
            if result["status"] == "success":
                print("✅ Game berhasil di-generate!")
                
                # Ekstrak kode asli dari dictionary yang dikembalikan Gradio
                raw_data = result["data"]
                code_content = ""
                
                if isinstance(raw_data, str):
                    try:
                        # Jika berbentuk string JSON (seperti `{"value": "import React...", "__type__": "update"}`)
                        parsed_data = json.loads(raw_data.replace("'", '"')) # Hati-hati dengan quote
                        if "value" in parsed_data:
                            code_content = parsed_data["value"]
                        else:
                            code_content = raw_data
                    except json.JSONDecodeError:
                        code_content = raw_data
                elif isinstance(raw_data, dict) and "value" in raw_data:
                    code_content = raw_data["value"]
                else:
                    code_content = str(raw_data)
                
                # ----------------------------------------
                # SIMPAN KE DALAM FILE
                # ----------------------------------------
                import datetime
                import re
                
                output_folder = os.path.join(os.path.dirname(__file__), "generated_games")
                os.makedirs(output_folder, exist_ok=True)
                
                # Bersihkan prompt menjadi filename yang bagus
                safe_prompt = re.sub(r'[^a-zA-Z0-9]', '_', user_input.lower()[:40]).strip('_')
                safe_prompt = re.sub(r'_+', '_', safe_prompt)
                if not safe_prompt:
                    safe_prompt = "game"
                    
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if "<html>" in code_content.lower() or "<!doctype html>" in code_content.lower():
                    ext = ".html"
                else:
                    ext = ".jsx"
                    
                output_filename = f"{safe_prompt}_{timestamp}{ext}"
                output_filepath = os.path.join(output_folder, output_filename)
                
                viewer_app_path = os.path.join(os.path.dirname(__file__), "game-viewer", "src", "App.jsx")
                
                with open(output_filepath, "w", encoding="utf-8") as f:
                    f.write(code_content)
                
                if ext == ".jsx" and os.path.exists(os.path.dirname(viewer_app_path)):
                    with open(viewer_app_path, "w", encoding="utf-8") as f:
                        f.write(code_content)
                    print(f"📁 KODE RAW DISIMPAN KE: generated_games/{output_filename}")
                    print(f"✅ Preview App.jsx di React environment telah diperbarui!")
                    print("💡 Catatan: Game bisa dilihat di browser (localhost:5173).")
                else:
                    print(f"📁 KODE TELAH DISIMPAN KE: generated_games/{output_filename}")
                    if ext == ".jsx":
                        print("💡 Catatan: Game ini dibuat menggunakan React (JSX) + TailwindCSS.")
                    else:
                        print(f"🌐 Anda bisa langsung membuka file generated_games/{output_filename} di browser!")
                    
            else:
                print(f"❌ Error: {result['message']}")
                print(f"💡 {result['suggestion']}")
        elif send_choice == "copy":
            print("\n📋 COPY PROMPT INI ke Qwen3-Coder-WebDev:")
            print("=" * 60)
            print(detailed)
            print("=" * 60)
            print(f"🔗 Buka: https://huggingface.co/spaces/Qwen/Qwen3-Coder-WebDev")
        else:
            print("⏭️  Melewati pengiriman ke Coder.")


if __name__ == "__main__":
    main()
