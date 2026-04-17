#!/bin/bash

# RUN_TESTS.sh
# Quick test script untuk verify semua fixes bekerja
# Usage: bash RUN_TESTS.sh

echo "======================================================================="
echo "🧪 PIPELINE TEST SUITE"
echo "======================================================================="

cd "$(dirname "$0")" || exit 1

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# ── Test 1: Check fine-tuned LoRA ──
echo -e "\n${YELLOW}[1/4]${NC} Checking fine-tuned LoRA adapter..."
if [ -f "output/prompt-expander-lora/adapter_model.safetensors" ]; then
    size=$(du -h "output/prompt-expander-lora/adapter_model.safetensors" | cut -f1)
    echo -e "${GREEN}✅${NC} LoRA adapter found ($size)"
    ((passed++))
else
    echo -e "${RED}❌${NC} LoRA adapter not found - run: python 02_finetune.py"
    ((failed++))
fi

# ── Test 2: Check merged dataset ──
echo -e "\n${YELLOW}[2/4]${NC} Checking merged dataset..."
if [ -f "dataset/train_dataset_merged.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('dataset/train_dataset_merged.json'))))" 2>/dev/null)
    echo -e "${GREEN}✅${NC} Merged dataset found ($count examples)"
    ((passed++))
else
    echo -e "${YELLOW}⚠️${NC} Merged dataset not yet created (auto-created on next finetune run)"
fi

# ── Test 3: Check synthetic dataset ──
echo -e "\n${YELLOW}[3/4]${NC} Checking synthetic dataset..."
if [ -f "dataset/train_dataset_synthetic.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('dataset/train_dataset_synthetic.json'))))" 2>/dev/null)
    echo -e "${GREEN}✅${NC} Synthetic dataset found ($count examples)"
    if [ "$count" -ge 50 ]; then
        echo "    🎉 Full synthetic generation complete!"
    else
        echo "    💡 Only $count examples - run 00_generate_synthetic_dataset.py for more"
    fi
    ((passed++))
else
    echo -e "${RED}❌${NC} Synthetic dataset not found - run: python 00_generate_synthetic_dataset.py"
    ((failed++))
fi

# ── Test 4: Check Ollama & Qwen3-Coder ──
echo -e "\n${YELLOW}[4/4]${NC} Checking Ollama & Qwen3-Coder..."
if command -v ollama &> /dev/null; then
    # Try to connect to Ollama
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo -e "${GREEN}✅${NC} Ollama is running"
        # Check for Qwen model
        models=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; print([m['name'] for m in json.load(sys.stdin).get('models', [])])" 2>/dev/null)
        if echo "$models" | grep -q "qwen"; then
            echo -e "${GREEN}✅${NC} Qwen model found"
            ((passed++))
        else
            echo -e "${YELLOW}⚠️${NC} Qwen model not found - run: ollama pull qwen2.5-coder:7b-instruct-q4_K_M"
        fi
    else
        echo -e "${YELLOW}⚠️${NC} Ollama not running - start with: ollama serve"
    fi
else
    echo -e "${RED}❌${NC} Ollama not installed - install from: https://ollama.ai"
    ((failed++))
fi

# ── Summary ──
echo ""
echo "======================================================================="
echo "📊 TEST SUMMARY"
echo "======================================================================="
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"

if [ $failed -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed! Pipeline ready to use."
    echo ""
    echo "Next steps:"
    echo "   1. Generate synthetic data (optional): python 00_generate_synthetic_dataset.py"
    echo "   2. Train LoRA adapter: python 02_finetune.py"
    echo "   3. Test inference: python 03_inference.py"
    echo "   4. Run full pipeline: python 04_pipeline.py"
else
    echo ""
    echo "⚠️  Some tests failed. Fix the issues above before proceeding."
fi

echo "======================================================================="
