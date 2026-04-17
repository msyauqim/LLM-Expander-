"""
convert_alpaca_to_sft.py
Konversi semua file Alpaca format {instruction, input, output}
di dataset/Fisika/ ke SFT format {messages: [{role, content}]}.

Output: dataset/train_dataset_fisika_sft.json
"""
import json
import glob
import os
import hashlib

# System prompt yang sama dengan json_filler.py
SYSTEM_PROMPT = """Kamu adalah asisten AI pembuat JSON game edukasi sesuai schema v1.2.
Diberikan input guru (kelas, mapel, bab, subbab, topik), lengkapi semua field JSON.

**PENTING: Output HANYA JSON valid, TANPA teks tambahan, TANPA penjelasan, TANPA markdown.**

**ATURAN FORMAT KETAT:**
1. Output HANYA JSON valid (tidak ada teks lain)
2. Mulai langsung dengan { (tanpa karakter sebelumnya)
3. Akhiri dengan } (tanpa karakter sesudahnya)
4. JANGAN gunakan markdown code block (```)
5. SEMUA string harus double quotes (",  TIDAK single quotes (')
6. Tidak boleh ada semicolon (;) atau trailing commas
7. Pastikan quotes seimbang dan benar"""

BASE_DIR = os.path.dirname(__file__)
FISIKA_DIR = os.path.join(BASE_DIR, "dataset", "Fisika")
OUTPUT_FILE = os.path.join(BASE_DIR, "dataset", "train_dataset_fisika_sft.json")

EXCLUDE_FILES = {"train_dataset_merged.json", "train_dataset_fisika_sft.json"}


def alpaca_to_messages(item: dict) -> dict | None:
    """Konversi 1 item Alpaca → SFT messages format.

    Isi tidak diubah sama sekali:
    - instruction (string) → bagian pertama user message
    - input (dict/string) → dilampirkan apa adanya sebagai JSON string rapi
    - output (dict/string) → assistant message, tetap JSON string rapi
    """
    instruction = item.get("instruction", "")
    inp = item.get("input", "")
    output = item.get("output", "")

    if not instruction or not output:
        return None

    # Serialisasi output → string JSON (kalau belum string)
    if isinstance(output, dict):
        output_str = json.dumps(output, ensure_ascii=False)
    else:
        output_str = str(output).strip()

    # Gabung instruction + input untuk user message
    if isinstance(inp, dict):
        inp_str = json.dumps(inp, ensure_ascii=False, indent=2)
    else:
        inp_str = str(inp).strip()

    user_content = str(instruction).strip()
    if inp_str:
        user_content += "\n" + inp_str

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": output_str},
        ]
    }


def content_hash(item: dict) -> str:
    s = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(s.encode()).hexdigest()


def main():
    json_files = sorted(glob.glob(
        os.path.join(FISIKA_DIR, "**", "*.json"),
        recursive=True
    ))
    json_files = [f for f in json_files if os.path.basename(f) not in EXCLUDE_FILES]

    print(f"Ditemukan {len(json_files)} file JSON di dataset/Fisika/")

    converted = []
    seen_hashes = set()
    skipped_format = 0
    skipped_dup = 0
    skipped_empty = 0

    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Skip (JSON error): {os.path.basename(fpath)} — {e}")
                continue

        # Bisa berupa dict (1 item) atau list of dicts
        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                skipped_format += 1
                continue

            # Sudah SFT format? skip konversi
            if "messages" in item:
                h = content_hash(item)
                if h in seen_hashes:
                    skipped_dup += 1
                    continue
                seen_hashes.add(h)
                converted.append(item)
                continue

            # Alpaca format
            if "instruction" not in item:
                skipped_format += 1
                continue

            result = alpaca_to_messages(item)
            if result is None:
                skipped_empty += 1
                continue

            h = content_hash(result)
            if h in seen_hashes:
                skipped_dup += 1
                continue
            seen_hashes.add(h)
            converted.append(result)

    print(f"\nHasil:")
    print(f"  ✅ Berhasil dikonversi : {len(converted)} contoh")
    print(f"  ⏭️  Skip (duplikat)    : {skipped_dup}")
    print(f"  ⏭️  Skip (format lain) : {skipped_format}")
    print(f"  ⏭️  Skip (kosong)      : {skipped_empty}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Disimpan ke: {OUTPUT_FILE}")
    print(f"   Total contoh: {len(converted)}")


if __name__ == "__main__":
    main()
