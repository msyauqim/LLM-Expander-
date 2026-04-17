"""
02_finetune.py
Script fine-tuning Qwen3-0.6B LoRA untuk Prompt Expander.
Jalankan: python 02_finetune.py

ARSITEKTUR PIPELINE:
  [Guru Prompt] → [Qwen3-0.6B + LoRA ← fine-tune di sini] → [Qwen3-Coder via Ollama] → [Game HTML]

CATATAN:
  Yang di-fine-tune adalah Qwen3-0.6B (Prompt Expander, ~1GB), BUKAN Qwen3-Coder.
  Qwen3-Coder berjalan via Ollama dan sudah cerdas secara default.
  Fine-tuning Prompt Expander mengajarkan model cara mengubah prompt sederhana guru
  menjadi prompt teknis yang lebih detail untuk dikirim ke Qwen3-Coder.
"""
import json
import os
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

# ============================================================
# KONFIGURASI
# ============================================================
BASE_MODEL   = "Qwen/Qwen3-4B"            # Model dasar Prompt Expander
DATASET_PATH_SCHEMA = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_schema.json")
DATASET_PATH_SCHEMA_SYNTHETIC = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_schema_synthetic.json")
DATASET_PATH_FISIKA = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_fisika_sft.json")
DATASET_PATH_MERGED = os.path.join(os.path.dirname(__file__), "dataset", "train_dataset_merged.json")
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "output", "prompt-expander-lora")

# Training hyperparameters
NUM_EPOCHS            = 10
BATCH_SIZE            = 1      # Kecil karena RAM terbatas (local)
GRADIENT_ACCUMULATION = 4      # Effective batch = 4
LEARNING_RATE         = 1e-4
MAX_SEQ_LENGTH        = 2048
WEIGHT_DECAY          = 0.01

# LoRA hyperparameters
LORA_RANK    = 32
LORA_ALPHA   = 64
LORA_DROPOUT = 0.1


def load_dataset_from_json(filepath: str) -> Dataset:
    """Load dataset dari file JSON."""
    print(f"📂 Membaca dataset dari: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} contoh")
    return Dataset.from_list(data)


def merge_datasets() -> str:
    """
    Merge semua dataset SFT yang task-nya konsisten (output JSON).
    Return: path ke merged dataset.
    """
    print("\n🔗 Merge datasets...")

    sources = [
        (DATASET_PATH_SCHEMA,           "Schema SFT"),
        (DATASET_PATH_SCHEMA_SYNTHETIC, "Schema Synthetic"),
        (DATASET_PATH_FISIKA,           "Fisika SFT"),
    ]

    merged = []
    for path, label in sources:
        if not os.path.exists(path):
            print(f"⚠️  {label} tidak ditemukan: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"   ✅ {label}: {len(data)} contoh")
        merged.extend(data)

    os.makedirs(os.path.dirname(DATASET_PATH_MERGED), exist_ok=True)
    with open(DATASET_PATH_MERGED, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"   📦 Merged: {len(merged)} contoh")
    print(f"   💾 Disimpan ke: {DATASET_PATH_MERGED}")
    return DATASET_PATH_MERGED


def format_chat(example, tokenizer):
    """Format contoh menjadi chat template."""
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )
    return {"text": text}


def main():
    print("=" * 60)
    print("🚀 FINE-TUNING PROMPT EXPANDER (Qwen3-4B + LoRA)")
    print("   Bagian dari Qwen3-Coder Pipeline")
    print("=" * 60)

    # ── Deteksi device ──
    if torch.backends.mps.is_available():
        device = "mps"
        print("🍎 Device: Apple Silicon GPU (MPS)")
    elif torch.cuda.is_available():
        device = "cuda"
        print("🎮 Device: NVIDIA GPU (CUDA)")
    else:
        device = "cpu"
        print("💻 Device: CPU (lebih lambat, tapi bisa jalan)")

    # ── Merge dataset ──
    merged_dataset_path = merge_datasets()
    if not os.path.exists(merged_dataset_path):
        print(f"\n❌ Merged dataset tidak ditemukan: {merged_dataset_path}")
        print("💡 Pastikan file dataset ada.")
        return

    # ============================================================
    # 1. LOAD TOKENIZER & MODEL
    # ============================================================
    print("\n📦 Mengunduh tokenizer dan model Qwen3-4B...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,  # bf16 untuk efisiensi memori di Mac M-series
        trust_remote_code=True,
    )
    print(f"✅ Model loaded: {BASE_MODEL}")
    print(f"   Total parameter: {model.num_parameters():,}")

    # ============================================================
    # 2. SETUP LoRA
    # ============================================================
    print("\n🔧 Mengkonfigurasi LoRA adapter...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    trainable_params, total_params = model.get_nb_trainable_parameters()
    print(f"✅ LoRA siap!")
    print(f"   Trainable : {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")
    print(f"   Total     : {total_params:,}")

    # ============================================================
    # 3. LOAD & FORMAT DATASET
    # ============================================================
    print("\n📂 Memuat dan memformat dataset...")
    dataset = load_dataset_from_json(merged_dataset_path)
    dataset = dataset.map(lambda x: format_chat(x, tokenizer))
    print(f"✅ Dataset siap! ({len(dataset)} contoh)")
    print(f"   Preview (50 char): {dataset[0]['text'][:50]}...")

    # ============================================================
    # 4. TRAINING
    # ============================================================
    print(f"\n🏋️  Memulai training...")
    print(f"   Epochs         : {NUM_EPOCHS}")
    print(f"   Batch size     : {BATCH_SIZE}")
    print(f"   Learning rate  : {LEARNING_RATE}")
    print(f"   Max seq length : {MAX_SEQ_LENGTH}")
    print(f"   Output dir     : {OUTPUT_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=2,
        save_strategy="epoch",
        save_total_limit=3,
        fp16=False,
        bf16=True,
        max_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    trainer.train()

    # ============================================================
    # 5. SIMPAN MODEL
    # ============================================================
    print("\n💾 Menyimpan LoRA adapter...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"\n{'=' * 60}")
    print(f"🎉 FINE-TUNING SELESAI!")
    print(f"{'=' * 60}")
    print(f"📁 LoRA adapter tersimpan di : {OUTPUT_DIR}")
    print(f"📝 Langkah selanjutnya:")
    print(f"   1. Test inference : python 03_inference.py")
    print(f"   2. Jalankan pipeline penuh : python 04_pipeline.py")


if __name__ == "__main__":
    main()
