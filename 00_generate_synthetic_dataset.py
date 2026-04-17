"""
00_generate_synthetic_dataset.py
Generate ~50 synthetic training examples (prompt_sederhana → prompt_detail) via Qwen3-4B lokal.
Used to augment the existing 18 training examples in train_dataset.json.

Jalankan: python 00_generate_synthetic_dataset.py

Output: dataset/train_dataset_synthetic.json (50+ contoh)
Note: Merge secara manual dengan train_dataset.json → train_dataset_merged.json
"""
import json
import os
import time
import torch
import re
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer

# ============================================================
# KONFIGURASI
# ============================================================
BASE_MODEL = "Qwen/Qwen3-4B"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_synthetic.json")
OUTPUT_PATH_SCHEMA = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_schema_synthetic.json")

# Daftar 50+ topik fisika SMA unik
PHYSICS_TOPICS = [
    # Mekanika
    "gerak parabola",
    "gerak melingkar beraturan",
    "gerak melingkar berubah beraturan",
    "usaha dan energi kinetik",
    "energi potensial dan hukum kekekalan energi",
    "momentum dan impuls",
    "tumbukan elastis dan tak elastis",
    "rotasi benda tegar",
    "momen inersia",
    "torsi dan keseimbangan rotasi",
    "gerak gelinding",
    "pesawat sederhana (katrol, tuas, bidang miring)",

    # Fluida
    "tekanan zat cair",
    "hukum Pascal",
    "hukum Archimedes",
    "viskositas dan aliran fluida",
    "persamaan kontinuitas",
    "persamaan Bernoulli",
    "tegangan permukaan air",
    "kapilaritas",

    # Termodinamika
    "suhu dan kalor",
    "perubahan wujud zat",
    "kalor laten dan kalor jenis",
    "transfer kalor (konduksi, konveksi, radiasi)",
    "hukum termodinamika pertama",
    "hukum termodinamika kedua",
    "mesin Carnot",
    "entropi",
    "gas ideal dan hukum gas",

    # Gelombang & Bunyi
    "gelombang transversal dan longitudinal",
    "cepat rambat gelombang",
    "frekuensi dan panjang gelombang",
    "interferensi gelombang",
    "difraksi gelombang",
    "polarisasi gelombang",
    "doppler effect",
    "resonansi bunyi",
    "gema dan pemantulan bunyi",
    "decibel dan intensitas bunyi",

    # Optik
    "pemantulan cahaya (hukum Snell)",
    "pembiasan cahaya",
    "lensa cembung dan cekung",
    "perbesaran lensa",
    "pembentukan bayangan",
    "prisma dan dispersi",
    "interferensi cahaya",
    "difraksi cahaya (celah tunggal dan ganda)",
    "spektrum cahaya",
    "cahaya polarisasi",

    # Listrik Statis
    "muatan listrik dan hukum Coulomb",
    "medan listrik",
    "potensial listrik dan beda potensial",
    "kapasitor dan kapasitansi",
    "energi listrik statis",
    "dielektrik",
    "grounding dan petir",
]

SYSTEM_PROMPT_JSON = """Kamu adalah asisten AI pembuat game edukasi. Tugasmu mengubah prompt sederhana dari guru menjadi JSON game edukasi yang lengkap dan valid sesuai schema v1.2.

Output HARUS berupa JSON valid tanpa teks tambahan, tanpa markdown code block.

ATURAN KETAT untuk setiap field:
- schema_version: selalu "1.2"
- game_id: format "game_{subject}{grade}_{topic}_{number}" contoh: "game_phys10_kin_word_001"
- game_type: HANYA "word_game" | "puzzle_game" | "sim_lab"
- metadata:
  - subject: HANYA "Fisika" | "Kimia" | "Biologi" | "Matematika"
  - grade_level: HANYA "SMA-10" | "SMA-11" | "SMA-12"
  - difficulty: integer 1-5 (BUKAN string seperti "Sedang")
  - estimated_duration_minutes: integer 5-60
  - learning_objectives: array of string, 1-5 item, tanpa prefix dash
  - language: selalu "id"
- presentation: SEMUA sub-field harus OBJECT, bukan string
  - opening: OBJECT {id, show_once, title, story, image_description, cta_text}
  - visual_element: OBJECT {theme_name, theme_preset, mood, color_palette (include gradient_bg), setting_description, art_style, canvas_scene, ui_components}
    - theme_preset: HANYA "classroom"|"scifi_neon"|"nature"|"retro"|"minimal"|"adventure"
    - color_palette: OBJECT {primary, secondary, background, accent, text, gradient_bg} semua format #RRGGBB (gradient_bg = CSS gradient string)
    - canvas_scene: OBJECT {render_method (css_divs|canvas_2d|svg|mixed), background_layers[], objects[], particle_effects[]}
    - ui_components: OBJECT {button_style, card_style, score_display_style, input_style} - deskripsi detail CSS
  - instructions: OBJECT {id, trigger{type,position,icon,label}, steps[{step,text}]}
  - hint: OBJECT {id, scope, trigger{type,after_seconds,dismissible,reusable,manual_trigger_available}, content{title,strategy,formula,example,hint_image_description}}
  - audio: OBJECT {enabled, tracks[{id,event,description}]}
    - event: HANYA "on_correct_action"|"on_wrong_action"|"on_win"|"on_lose"|"background"
- payload: HARUS sesuai game_type
  - word_game: {instruction, word_bank[], questions[{id,type,prompt,answer,explanation}]}
    - type soal: "fill_blank"|"match_pair"|"crossword_clue"|"unscramble"
  - puzzle_game: {instruction, intro_narrative, outro_narrative, stages[{stage_id,title,description,challenges[{id,type,prompt,options,answer,explanation}]}]}
    - type challenge: "multiple_choice"|"drag_sort"|"drag_match"|"calculate"|"true_false"
  - sim_lab: {instruction, scene{title,narrative,context,interactive_objects[],visual_feedback[]}, variables[{name,label,unit,min,max,default,step,role,slider_color}], formula{expression,description,display_latex}, sim_steps[], analysis_questions[]}
- win_lose_condition: OBJECT {applicable, win{description,logic,feedback_text,feedback_audio}, lose{description,logic,feedback_text,feedback_audio,retry_allowed}}
- gameplay_parameters: OBJECT {scoring{}, lives, time_limit_seconds, pass_threshold}

VISUAL KAYA (WAJIB):
- canvas_scene HARUS include background_layers dengan CSS description detail (gradient, pattern, glow spots, parallax)
- objects dekoratif HARUS divisualisasikan dengan deskripsi detail bentuk, warna, shadow, animasi
- particle_effects HARUS include (dust, sparkle, rain, firefly, dll) dengan CSS animation description
- ui_components HARUS detail: button glow, card backdrop-filter, slider custom styling
- Untuk sim_lab: interactive_objects HARUS ada visual_response (ubah warna/ukuran saat variabel berubah), animation_on_run HARUS ada

Variasikan game_type secara merata. Buat konten edukatif yang akurat dan game yang engaging dengan visual yang TIDAK POLOS."""

def load_model():
    """Load Qwen3-0.6B model lokal."""
    print("📦 Memuat Qwen3-0.6B model...")
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        trust_remote_code=True,
        device_map="auto"
    )
    
    model.eval()
    print("✅ Model loaded!")
    return model, tokenizer


def generate_via_qwen(model, tokenizer, prompt: str, system_prompt: str = "") -> Optional[str]:
    """
    Kirim prompt ke Qwen3-0.6B lokal.
    Return: response text atau None jika error.
    """
    try:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1500,  # Ganti max_length ke max_new_tokens
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.2,  # Prevent repeating characters
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Hapus prompt dari response
        if full_prompt in response:
            response = response.replace(full_prompt, "").strip()
        
        return response if response else None
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None
        return None


def generate_json_game(model, tokenizer, topic: str, game_type: str) -> Optional[str]:
    """
    Kirim prompt ke Qwen3-0.6B lokal untuk generate JSON game edukasi.
    Return: JSON string atau None jika error.
    """
    import random
    grade = random.choice(["SMA-10", "SMA-11", "SMA-12"])
    difficulty = random.randint(1, 4)

    user_prompt = (
        f"Buatkan game edukasi: mata_pelajaran=Fisika, jenjang={grade}, "
        f"topik={topic}, kesulitan={difficulty}, jenis={game_type}\n\n"
        f"PENTING: Output HANYA JSON valid. Mulai dengan {{ dan akhiri dengan }}. "
        f"Jangan tambahkan teks atau markdown apapun."
    )

    content = generate_via_qwen(model, tokenizer, user_prompt, SYSTEM_PROMPT_JSON)
    if not content:
        return None

    # Strip markdown code blocks
    content = re.sub(r'^```(?:json)?\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content.strip())

    # Cari blok JSON
    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        content = content[first_brace:last_brace + 1]

    try:
        json.loads(content)  # Validasi
        return content
    except json.JSONDecodeError:
        print(f"  ⚠️  Output bukan JSON valid, skip")
        return None


def main():
    print("=" * 70)
    print("🧬 SYNTHETIC DATASET GENERATOR")
    print("   Generate ~50 training examples: simple prompt → detailed prompt")
    print("=" * 70)

    # Load model lokal
    print("\n🔌 Load Qwen3-0.6B model lokal...")
    try:
        model, tokenizer = load_model()
    except Exception as e:
        print(f"❌ Gagal load model: {e}")
        print("💡 Pastikan model Qwen/Qwen3-0.6B terdownload:")
        print("   python -c \"from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen3-0.6B')\"")
        return

    # Siapkan output folder
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print(f"\n📊 Generate {len(PHYSICS_TOPICS)} training examples (JSON Schema only)...")
    print("   (setiap topic: ~30-60 detik tergantung kecepatan GPU)")
    print("-" * 70)

    import random

    # Langsung generate JSON saja (hapus mode picker)
    generate_text = False
    generate_json = True

    dataset_json = []
    system_prompt_json_content = SYSTEM_PROMPT_JSON.strip()

    game_types = ["word_game", "puzzle_game", "sim_lab"]
    for idx, topic in enumerate(PHYSICS_TOPICS, 1):
        print(f"\n[{idx}/{len(PHYSICS_TOPICS)}] 🧪 {topic.upper()}")

        # Generate JSON version only
        game_type = game_types[idx % len(game_types)]
        grade = random.choice(["SMA-10", "SMA-11", "SMA-12"])
        difficulty = random.randint(1, 4)
        user_prompt = (
            f"Buatkan game edukasi: mata_pelajaran=Fisika, jenjang={grade}, "
            f"topik={topic}, kesulitan={difficulty}, jenis={game_type}"
        )
        json_output = generate_json_game(model, tokenizer, topic, game_type)
        if json_output:
            print(f"  ✅ Generated ({game_type})")
            entry = {
                "messages": [
                    {"role": "system",    "content": system_prompt_json_content},
                    {"role": "user",      "content": user_prompt},
                    {"role": "assistant", "content": json_output}
                ]
            }
            dataset_json.append(entry)
        else:
            print(f"  ❌ Skip")

        # Rate limiting
        if idx < len(PHYSICS_TOPICS):
            time.sleep(2)

    # Simpan hasil
    print("\n" + "=" * 70)

    if dataset_json:
        with open(OUTPUT_PATH_SCHEMA, "w", encoding="utf-8") as f:
            json.dump(dataset_json, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON dataset: {OUTPUT_PATH_SCHEMA} ({len(dataset_json)} contoh)")

    if len(dataset_json) > 0:
        print(f"\n📈 Total generated: {len(dataset_json)} contoh")
        print("\n🔗 Langkah selanjutnya:")
        print("   1. Jalankan: python 01_prepare_dataset.py")
        print("   2. Jalankan: python 02_finetune.py")
    else:
        print("❌ Tidak ada data yang berhasil di-generate!")
        print("💡 Cek: Model loading OK? GPU memory cukup?")

if __name__ == "__main__":
    main()
