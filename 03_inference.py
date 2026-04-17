"""
03_inference.py
Script untuk menguji model yang sudah di-fine-tune.
Jalankan: python 03_inference.py
Atau:     python 03_inference.py --prompt "Buat game tentang gerak parabola"
"""
import argparse
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Konfigurasi
BASE_MODEL = "Qwen/Qwen3-4B"
LORA_PATH = os.path.join(os.path.dirname(__file__), "hasil latih qwen 4B di colab")

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
    "sesuai schema v1.2. Output HARUS berupa JSON valid tanpa teks tambahan. "
    "JSON harus mengandung: schema_version, game_id, game_type "
    "(word_game|puzzle_game|sim_lab), metadata (title, subject, grade_level, "
    "bab, subbab, topik, difficulty, estimated_duration_minutes, "
    "learning_objectives, language), presentation (opening, visual_element, "
    "instructions, hint, audio), payload (sesuai game_type), "
    "win_lose_condition, dan gameplay_parameters."
)

# Default mode JSON
SYSTEM_PROMPT = SYSTEM_PROMPT_JSON


def load_model():
    """Load base model + LoRA adapter."""
    print("📦 Memuat model...")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Auto-detect device
    if torch.cuda.is_available():
        dtype = torch.bfloat16
    elif torch.backends.mps.is_available():
        dtype = torch.float16
    else:
        dtype = torch.float32

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        trust_remote_code=True,
    )

    # Load LoRA adapter
    if os.path.exists(LORA_PATH):
        print(f"🔧 Memuat LoRA adapter dari: {LORA_PATH}")
        model = PeftModel.from_pretrained(base_model, LORA_PATH, device_map=None)
    else:
        print(f"⚠️  LoRA adapter tidak ditemukan di {LORA_PATH}")
        print("   Menggunakan base model tanpa fine-tuning.")
        model = base_model

    model.eval()
    print("✅ Model siap!")
    return model, tokenizer


def expand_prompt(model, tokenizer, user_prompt: str) -> str:
    """Mengembangkan prompt sederhana menjadi prompt detail / JSON."""
    if SYSTEM_PROMPT == SYSTEM_PROMPT_JSON:
        enforced = (
            f"{user_prompt}\n\n"
            "PENTING: Jawab HANYA dengan JSON valid. "
            "Mulai langsung dengan {{ dan akhiri dengan }}. "
            "Jangan tambahkan teks di luar JSON."
        )
    else:
        enforced = user_prompt

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": enforced},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

    # Prefix JSON agar model mulai dari '{'
    if SYSTEM_PROMPT == SYSTEM_PROMPT_JSON:
        text += "{"

    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.3 if SYSTEM_PROMPT == SYSTEM_PROMPT_JSON else 0.7,
            top_p=0.85,
            top_k=50,
            repetition_penalty=1.15,
            do_sample=True,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)

    if SYSTEM_PROMPT == SYSTEM_PROMPT_JSON and not response.strip().startswith("{"):
        response = "{" + response

    return response


def main():
    parser = argparse.ArgumentParser(description="Test Prompt Expander LLM")
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Prompt sederhana dari guru untuk di-expand",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="json",
        choices=["json", "text"],
        help="Mode output: json (schema v1.2) atau text (prompt detail)",
    )
    args = parser.parse_args()

    global SYSTEM_PROMPT
    if args.mode == "text":
        SYSTEM_PROMPT = SYSTEM_PROMPT_TEXT
        print("📝 Mode: Text (prompt detail)")
    else:
        SYSTEM_PROMPT = SYSTEM_PROMPT_JSON
        print("📋 Mode: JSON Schema v1.2")

    model, tokenizer = load_model()

    if args.prompt:
        # Mode single prompt
        print(f"\n📝 Input: {args.prompt}")
        print("\n" + "=" * 60)
        print("🤖 OUTPUT PROMPT DETAIL:")
        print("=" * 60)
        result = expand_prompt(model, tokenizer, args.prompt)
        print(result)
    else:
        # Mode interaktif
        print("\n" + "=" * 60)
        print("🎮 PROMPT EXPANDER - Mode Interaktif")
        print("=" * 60)
        print("Ketik prompt sederhana, lalu tekan Enter.")
        print("Ketik 'quit' untuk keluar.\n")

        while True:
            user_input = input("📝 Guru: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Sampai jumpa!")
                break
            if not user_input:
                continue

            print("\n⏳ Sedang mengembangkan prompt...")
            result = expand_prompt(model, tokenizer, user_input)
            print("\n" + "=" * 60)
            print("🤖 PROMPT DETAIL:")
            print("=" * 60)
            print(result)
            print()


if __name__ == "__main__":
    main()
