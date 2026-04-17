"""Wrapper untuk LLM calls: local model + HF Space API."""
import json
import re
import torch
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from pipeline.config import LOCAL_MODEL, LORA_PATH, HF_SPACE, HF_API_ENDPOINT, USE_LOCAL_MODEL

# Singleton untuk local model
_local_model = None
_local_tokenizer = None


def get_local_model():
    """Load Qwen3 + LoRA (singleton) - or fallback to HF Space."""
    global _local_model, _local_tokenizer
    if _local_model is not None:
        return _local_model, _local_tokenizer

    if not USE_LOCAL_MODEL:
        print("⚠️  Local model disabled, using HF Space instead")
        return None, None

    import os
    # Auto-detect device: CUDA > MPS (Apple Silicon) > CPU
    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.bfloat16
    elif torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16  # MPS belum full support bf16
    else:
        device = "cpu"
        dtype = torch.float32

    print(f"Loading local model (Qwen + LoRA) on {device.upper()}...")
    tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        LOCAL_MODEL, torch_dtype=dtype, trust_remote_code=True, device_map=device
    )

    if os.path.exists(LORA_PATH):
        model = PeftModel.from_pretrained(base, LORA_PATH, device_map=device)
        print("LoRA adapter loaded.")
    else:
        print("LoRA not found, using base model.")
        model = base

    model.eval()
    _local_model, _local_tokenizer = model, tokenizer
    return model, tokenizer


def call_local_model(prompt: str, system_prompt: str = "", max_new_tokens: int = 1800) -> str:
    """Inference via local Qwen + LoRA, fallback to HF Space if disabled."""
    model, tokenizer = get_local_model()

    # Fallback: use HF Space if local model is disabled or failed
    if model is None or tokenizer is None:
        print("  [Local model unavailable] Using HF Space instead...")
        return call_hf_space(prompt, system_prompt)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    print(f"  [LLM] Generating (max {max_new_tokens} tokens, harap tunggu)...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            min_new_tokens=200,          # cegah JSON terpotong terlalu pendek
            temperature=0.3,
            top_p=0.85,
            top_k=40,                    # batasi kosakata → kurangi token random
            repetition_penalty=1.15,
            no_repeat_ngram_size=4,      # cegah pengulangan frasa 4-gram
            do_sample=True,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def call_hf_space(prompt: str, system_prompt: str = "") -> str:
    """Call Qwen3-Coder-WebDev via Gradio API."""
    from gradio_client import Client

    client = Client(HF_SPACE)
    result = client.predict(
        input_value=prompt,
        system_prompt_input_value=system_prompt,
        api_name=HF_API_ENDPOINT,
    )

    # result bisa tuple, dict, atau string
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, dict):
                return item.get("value", json.dumps(item))
            if item:
                return str(item)
        return ""
    if isinstance(result, dict):
        return result.get("value", json.dumps(result))
    return str(result)


def extract_code_from_response(text: str) -> str:
    """Bersihkan markdown code blocks dari response LLM."""
    text = text.strip()
    # Remove ```lang ... ```
    match = re.search(r'```(?:\w+)?\s*\n?(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
