#!/bin/bash

# Full Pipeline Runner with Caffeinate (Keep Mac awake during training)
# Usage: chmod +x run_full_pipeline.sh && ./run_full_pipeline.sh

set -e  # Exit on error

PROJECT_DIR="/Users/muhammadsyauqimuttaqin/aitf/fortensor/project game edukasi kelompok 4/llm-prompt-expander"
cd "$PROJECT_DIR"

echo "=========================================="
echo "🚀 GAME EDUKASI PIPELINE - FULL RUN"
echo "=========================================="
echo ""

# Activate venv
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""

# STEP 1: Generate Synthetic Dataset
echo "========== STEP 1: Generate Synthetic Dataset =========="
echo "Description: Generate ~56 JSON game specs with schema v1.2"
echo "Expected time: 15-30 minutes"
echo "Output: dataset/train_dataset_schema_synthetic.json"
echo ""

if [ -f "dataset/train_dataset_schema_synthetic.json" ]; then
    echo "⚠️  File already exists (196 KB)"
    read -p "Skip Step 1? (y/n) [default=y]: " skip_step1
    skip_step1=${skip_step1:-y}
    if [ "$skip_step1" = "y" ]; then
        echo "✅ Skipped Step 1"
    else
        echo "Running Step 1..."
        python 00_generate_synthetic_dataset.py
    fi
else
    echo "Running Step 1..."
    python 00_generate_synthetic_dataset.py
fi

echo ""
echo "========== STEP 2: Prepare Dataset =========="
echo "Description: Merge and prepare dataset for fine-tuning"
echo "Expected time: <1 minute"
echo "Output: dataset/prepared_dataset.jsonl"
echo ""

python 01_prepare_dataset.py

echo "✅ Step 2 complete"
echo ""

# STEP 3: Fine-tune LoRA
echo "========== STEP 3: Fine-tune LoRA Model =========="
echo "Description: Fine-tune Qwen3-0.6B with LoRA"
echo "Expected time: 30-60 minutes (GPU dependent)"
echo "Output: output/prompt-expander-lora/"
echo ""
echo "⚠️  Keeping Mac awake with caffeinate..."
echo "    (Mac will not sleep during fine-tuning)"
echo ""

# Run with caffeinate to keep Mac awake
caffeinate -i python 02_finetune.py

echo ""
echo "=========================================="
echo "✅ PIPELINE COMPLETE!"
echo "=========================================="
echo ""
echo "🎮 Next: Test the pipeline"
echo "   python pipeline_main.py 'Gerak Parabola' --jenjang SMA-10 --subject Fisika"
echo ""
