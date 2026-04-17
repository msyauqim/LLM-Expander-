"""
01_prepare_dataset.py
Script untuk memvalidasi dan menyiapkan dataset fine-tuning.
Jalankan: python 01_prepare_dataset.py
"""
import json
import os


def validate_dataset(filepath: str):
    """Validasi format dataset JSONL untuk fine-tuning."""
    valid_count = 0
    errors = []

    if not os.path.exists(filepath):
        print(f"❌ File tidak ditemukan: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            dataset = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Format JSON keseluruhan tidak valid: {e}")
            return 0

        for idx, data in enumerate(dataset):
            line_num = idx + 1

            # Cek apakah ada key "messages"
            if "messages" not in data:
                errors.append(f"  Baris {line_num}: Tidak ada key 'messages'")
                continue

            messages = data["messages"]

            # Cek apakah messages adalah list
            if not isinstance(messages, list):
                errors.append(f"  Baris {line_num}: 'messages' bukan list")
                continue

            # Cek minimal ada 3 pesan (system, user, assistant)
            if len(messages) < 3:
                errors.append(
                    f"  Baris {line_num}: Kurang dari 3 messages (ada {len(messages)})"
                )
                continue

            # Cek role yang benar
            roles = [m.get("role") for m in messages]
            if roles[0] != "system":
                errors.append(f"  Baris {line_num}: Message pertama bukan 'system'")
                continue
            if roles[1] != "user":
                errors.append(f"  Baris {line_num}: Message kedua bukan 'user'")
                continue
            if roles[2] != "assistant":
                errors.append(f"  Baris {line_num}: Message ketiga bukan 'assistant'")
                continue

            # Cek apakah content tidak kosong
            for i, msg in enumerate(messages):
                if not msg.get("content", "").strip():
                    errors.append(
                        f"  Baris {line_num}: Message ke-{i+1} content kosong"
                    )
                    continue

            valid_count += 1

    print("=" * 60)
    print("📊 HASIL VALIDASI DATASET")
    print("=" * 60)
    print(f"📁 File: {filepath}")
    print(f"✅ Contoh valid: {valid_count}")
    print(f"❌ Error: {len(errors)}")

    if errors:
        print("\n⚠️  Detail error:")
        for err in errors:
            print(err)
    else:
        print("\n🎉 Semua data valid! Dataset siap untuk fine-tuning.")

    # Tampilkan contoh pertama
    print("\n" + "=" * 60)
    print("📝 CONTOH DATA PERTAMA:")
    print("=" * 60)
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            dataset = json.load(f)
            if dataset and len(dataset) > 0:
                data = dataset[0]  # Ambil item pertama dari array
                for msg in data.get("messages", []):
                    role = msg["role"].upper()
                    content = msg["content"][:150] + (
                        "..." if len(msg["content"]) > 150 else ""
                    )
                    print(f"\n[{role}]")
                    print(f"  {content}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"⚠️  Tidak bisa tampilkan contoh: {e}")

    return valid_count


if __name__ == "__main__":
    dataset_path = os.path.join(
        os.path.dirname(__file__), "dataset", "train_dataset.json"
    )
    validate_dataset(dataset_path)
