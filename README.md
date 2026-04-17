# LLM Prompt Expander - Game Edukasi Generator

Pipeline otomatis untuk generate game edukasi HTML interaktif dari input guru, menggunakan **Qwen3-4B + LoRA** (fine-tuned) untuk JSON generation dan **Qwen3-Coder-WebDev** via HuggingFace Space untuk HTML/CSS/JS coding.

Bagian dari proyek **AITF 2026 — Use Case UB / Sekolah Rakyat**, dikerjakan oleh **Tim 4**.

---

## Arsitektur Pipeline

```
Input Guru (CLI / Web UI)
    ↓
[Stage 2] JSON Filler       → Qwen3-4B + LoRA (local, fine-tuned)
    ↓
[Stage 3] Prompter          → Programmatic (bukan LLM)
    ↓
[Stage 4] Coder (parallel)  → Qwen3-Coder-WebDev via HF Space API
    ↓
[Stage 5] Assembler         → CSS + HTML + JS → 1 file HTML
    ↓
[Stage 6] Validator         → Auto-fix hingga 3 attempt
    ↓
[Stage 7] Preview           → Path HTML / iframe browser
    ↓
[Stage 8] Revision          → Re-run specialist tertentu (opsional)
    ↓
[Stage 9] Publication       → SQLite + file generated_games/
```

---

## Model yang Digunakan

| Stage | Model | Lokasi |
|-------|-------|--------|
| JSON Filler | Qwen/Qwen3-4B + LoRA | Local (fine-tuned) |
| Prompter | — | Programmatic |
| Coder (3x parallel) | Qwen3-Coder-WebDev | HF Space API |

**Fine-tuned adapter**: [QyupyTzy](https://huggingface.co/QyupyTzy) di HuggingFace Hub

---

## Cara Jalankan

### Install Dependencies

```bash
pip install torch transformers peft gradio_client flask json-repair
```

### CLI

```bash
cd "llm-prompt-expander/"
python "05_run pipeline_main.py"
```

### Web UI

```bash
python run_web_ui.py
# Buka: http://localhost:5001
```

### Clear cache (regenerate ulang)

```bash
rm -rf ".pipeline_cache"/*
```

---

## Struktur File

```
llm-prompt-expander/
├── 05_run pipeline_main.py       ← Entry point CLI
├── run_web_ui.py                 ← Entry point Web UI
├── 02_finetune_dicolab.ipynb     ← Notebook fine-tuning (Colab/SR4)
│
├── pipeline/
│   ├── config.py                 ← Konfigurasi paths & model
│   ├── models.py                 ← Dataclasses (TeacherInput, GameSpec, dll)
│   ├── llm_client.py             ← Wrapper local model + HF Space API
│   ├── cache.py                  ← File-based cache (SHA256)
│   ├── json_filler.py            ← Stage 2: JSON generation + repair
│   ├── prompter.py               ← Stage 3: Prompt builder (programmatic)
│   ├── coder.py                  ← Stage 4: 3 specialist coders (HF Space)
│   ├── assembler.py              ← Stage 5: HTML assembler
│   ├── validator.py              ← Stage 6: Validator + auto-fix
│   ├── revision.py               ← Stage 8: Feedback classifier
│   └── publisher.py              ← Stage 9: SQLite + file publisher
│
├── web_ui/
│   ├── app.py
│   ├── templates/index.html
│   ├── static/style.css
│   └── static/script.js
│
├── dataset/
│   ├── Json Schema/              ← envelope.json, word_game.json, dll
│   └── Fisika/                   ← Dataset SFT per topik
│
├── hasil latih qwen 4B di colab/ ← LoRA adapter hasil fine-tuning
├── generated_games/              ← Output HTML + JSON spec
└── .pipeline_cache/              ← Cache (hapus untuk reset)
```

---

## Game Types

| Type | Kapan dipakai | Payload |
|------|--------------|---------|
| `word_game` | Definisi, konsep, teori | `instruction`, `word_bank`, `questions` |
| `puzzle_game` | Matching, pasang-pasangkan | `pairs`, `distractors` |
| `sim_lab` | Simulasi, praktikum | `variables`, `formula`, `sim_steps`, `scene` |

Game type dideteksi otomatis dari keyword topik. Bisa di-override manual di CLI.

---

## Input Guru

| Field | Wajib | Contoh |
|-------|-------|--------|
| Kelas | Ya | SMA-10, SMA-11, SMA-12 |
| Mata Pelajaran | Ya | Fisika, Kimia, Biologi, Matematika |
| Bab | Ya | Dinamika |
| Subbab | Opsional | Konsep Vektor |
| Topik | Opsional | Vektor dan Resultan |

---

## Fine-Tuning

Notebook: `02_finetune_dicolab.ipynb`

**Konfigurasi terbaru (anti-overfitting):**
```python
LORA_R       = 16      # rank kecil untuk generalisasi
LORA_ALPHA   = 32
LORA_DROPOUT = 0.15
NUM_EPOCHS   = 5       # + early stopping patience=2
WEIGHT_DECAY = 0.05
```

**Catatan**: Fine-tuning sebelumnya (r=64, epoch=10) mengalami overfitting — val loss naik sejak epoch 3. Konfigurasi di atas sudah diperbaiki.

---

## Known Issues & Fixes

| Masalah | Fix |
|---------|-----|
| Model output JSON dengan komentar `//` | Strip regex sebelum parse |
| Model output karakter China/non-latin | Strip key non-ASCII |
| Payload `{}` kosong | `_fill_empty_payload()` programmatic |
| JSON rusak (bracket salah, double quote) | `json-repair` library |
| Port 5000 conflict (macOS AirPlay) | Web UI default port **5001** |
| Loading model lama tiap run | Preload di awal session CLI |

---

## Performance

| Stage | Waktu |
|-------|-------|
| Model load (pertama kali) | ~9 detik |
| JSON Filler (Qwen3-4B) | ~60-90 detik |
| Coder (3 parallel HF Space) | ~45-60 detik |
| Assembler + Validator | <1 detik |
| **Total per game** | **~2-3 menit** |

---

## Tim

**Proyek**: AITF 2026 — Game Edukasi Sekolah Rakyat
**Institusi**: Universitas Brawijaya
**Tim**: Kelompok 4

**Catatan**: RAG stage (`pipeline/rag.py`) adalah tanggung jawab tim lain — saat ini di-skip dengan `rag_summary = ""`.

---

**Last Updated**: 2026-04-17
**Version**: 1.1.0
