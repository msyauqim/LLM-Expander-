"""
02_finetune_colab.py
Script fine-tuning Qwen3-4B LoRA untuk Prompt Expander — versi Google Colab.

CARA PAKAI DI COLAB:
1. Upload file ini + folder dataset/ ke Colab
2. Install dependencies:
   !pip install transformers peft trl datasets accelerate bitsandbytes -q
3. Jalankan semua cell
4. Download folder output/prompt-expander-lora/ ke lokal

STRUKTUR UPLOAD:
  /content/
  ├── 02_finetune_colab.py
  └── dataset/
      ├── train_dataset.json
      ├── train_dataset_synthetic.json
      ├── train_dataset_schema.json
      └── train_dataset_schema_synthetic.json
"""
import json
import os
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, EarlyStoppingCallback
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

# ============================================================
# DETEKSI ENVIRONMENT
# ============================================================
IN_COLAB = "COLAB_GPU" in os.environ or os.path.exists("/content")
BASE_PATH = "/content" if IN_COLAB else os.path.dirname(os.path.abspath(__file__))

# ============================================================
# KONFIGURASI
# ============================================================
BASE_MODEL   = "Qwen/Qwen3-4B"
DATASET_PATH_ORIGINAL         = os.path.join(BASE_PATH, "dataset", "train_dataset.json")
DATASET_PATH_SYNTHETIC        = os.path.join(BASE_PATH, "dataset", "train_dataset_synthetic.json")
DATASET_PATH_SCHEMA           = os.path.join(BASE_PATH, "dataset", "train_dataset_schema.json")
DATASET_PATH_SCHEMA_SYNTHETIC = os.path.join(BASE_PATH, "dataset", "train_dataset_schema_synthetic.json")
DATASET_PATH_MERGED           = os.path.join(BASE_PATH, "dataset", "train_dataset_merged.json")
OUTPUT_DIR                    = os.path.join(BASE_PATH, "output", "prompt-expander-lora")

# Training hyperparameters
NUM_EPOCHS            = 5      # Dikurangi dari 10 — val loss naik sejak epoch 3
BATCH_SIZE            = 2
GRADIENT_ACCUMULATION = 2      # Effective batch = 4
LEARNING_RATE         = 1e-4
MAX_SEQ_LENGTH        = 2048
WEIGHT_DECAY          = 0.05   # Naikkan regularisasi untuk dataset kecil

# LoRA hyperparameters
LORA_RANK    = 16      # Diturunkan dari 32/64 — rank besar mempercepat overfitting
LORA_ALPHA   = 32      # 2x rank (standar)
LORA_DROPOUT = 0.15    # Dinaikkan sedikit untuk regularisasi tambahan


# ============================================================
# DETEKSI GPU TYPE
# ============================================================
def detect_gpu():
    """Deteksi GPU dan return (device, use_fp16, use_bf16, torch_dtype)."""
    if not torch.cuda.is_available():
        print("💻 Device: CPU")
        return "cpu", False, False, torch.float32

    gpu_name = torch.cuda.get_device_name(0)
    print(f"🎮 Device: {gpu_name}")

    # A100, H100, dll → support bf16
    if any(x in gpu_name for x in ["A100", "H100", "A6000", "3090", "4090"]):
        print("   → bf16 mode")
        return "cuda", False, True, torch.bfloat16
    else:
        # T4, V100, P100, dll → pakai fp16
        print("   → fp16 mode")
        return "cuda", True, False, torch.float16


def load_dataset_from_json(filepath: str) -> Dataset:
    print(f"📂 Membaca dataset dari: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"   ✅ Loaded {len(data)} contoh")
    return Dataset.from_list(data)


def merge_datasets() -> str:
    print("\n🔗 Merge datasets...")
    all_data = []
    for label, path in [
        ("Original",         DATASET_PATH_ORIGINAL),
        ("Synthetic",        DATASET_PATH_SYNTHETIC),
        ("Schema SFT",       DATASET_PATH_SCHEMA),
        ("Schema Synthetic", DATASET_PATH_SCHEMA_SYNTHETIC),
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"   ✅ {label}: {len(data)} contoh")
            all_data.extend(data)
        else:
            print(f"   ⚠️  {label} tidak ditemukan: {path}")

    os.makedirs(os.path.dirname(DATASET_PATH_MERGED), exist_ok=True)
    with open(DATASET_PATH_MERGED, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"   📦 Total merged: {len(all_data)} contoh")
    return DATASET_PATH_MERGED


def format_chat(example, tokenizer):
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
    print(f"   Environment: {'Google Colab' if IN_COLAB else 'Local'}")
    print("=" * 60)

    device, use_fp16, use_bf16, torch_dtype = detect_gpu()

    # ── Merge dataset ──
    merged_path = merge_datasets()

    # ── Load tokenizer & model ──
    print(f"\n📦 Loading {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
        device_map="auto" if device == "cuda" else None,
    )
    print(f"✅ Model loaded | Total params: {model.num_parameters():,}")

    # ── Setup LoRA ──
    print("\n🔧 Konfigurasi LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"✅ LoRA ready | Trainable: {trainable:,} ({100*trainable/total:.2f}%)")

    # ── Load & format dataset ──
    print("\n📂 Memuat dataset...")
    dataset = load_dataset_from_json(merged_path)
    dataset = dataset.map(lambda x: format_chat(x, tokenizer))
    # Split train/val 90:10 untuk early stopping
    split = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split["train"]
    eval_dataset  = split["test"]
    print(f"✅ Dataset siap: {len(train_dataset)} train, {len(eval_dataset)} val")

    # ── Training ──
    print(f"\n🏋️  Training...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dataset_size = len(train_dataset)
    steps_per_epoch = max(1, dataset_size // (BATCH_SIZE * GRADIENT_ACCUMULATION))
    total_steps = steps_per_epoch * NUM_EPOCHS
    print(f"   📊 Dataset: {dataset_size} contoh")
    print(f"   📊 Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
    print(f"   📊 Steps per epoch: {steps_per_epoch}")
    print(f"   📊 Total steps: {total_steps}")

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
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=use_fp16,
        bf16=use_bf16,
        max_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    trainer.train()

    # ── Simpan ──
    print("\n💾 Menyimpan LoRA adapter...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"\n{'=' * 60}")
    print(f"🎉 FINE-TUNING SELESAI!")
    print(f"{'=' * 60}")
    print(f"📁 Output: {OUTPUT_DIR}")

    if IN_COLAB:
        print("\n📥 Download hasil ke lokal:")
        print("   from google.colab import files")
        print("   import shutil")
        print("   shutil.make_archive('/content/prompt-expander-lora', 'zip', '/content/output/prompt-expander-lora')")
        print("   files.download('/content/prompt-expander-lora.zip')")


if __name__ == "__main__":
    main()
