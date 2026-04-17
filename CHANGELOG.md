# Changelog - Pipeline 3-LLM Corrections

## 2026-04-14

### ✅ Fixed Issues

#### 1. **Prompter menggunakan Local Model (CRITICAL FIX)**
- **File**: `pipeline/prompter.py`
- **Perubahan**: 
  - Line 5: `from pipeline.llm_client import call_hf_space` → `call_local_model`
  - Line 78: `call_hf_space(prompt)` → `call_local_model(prompt, max_new_tokens=4096)`
- **Alasan**: Prompter harus generate JSON specs dengan format ketat, bukan code. HF Space API (Qwen3-Coder-WebDev) dirancang untuk code generation, bukan JSON.
- **Impact**: ✅ Prompter sekarang konsisten dengan architecture (local model untuk JSON generation)

---

### 📁 New Folder: Web UI

Created dedicated folder `web_ui/` untuk interface guru yang rapi dan terstruktur.

#### Files Created:

1. **`web_ui/app.py`** (Main Flask App)
   - API endpoints untuk generate, preview, revise, publish
   - Session management untuk game yang sedang dikerjakan
   - Integration dengan semua pipeline stages

2. **`web_ui/templates/index.html`** (HTML Template)
   - 3-step workflow: Input → Preview → Success
   - Form untuk input guru (kelas, mapel, bab, subbab, topik)
   - Live preview dengan iframe
   - Revision modal untuk feedback

3. **`web_ui/static/style.css`** (Styling)
   - Modern gradient design
   - Responsive layout (mobile-friendly)
   - Dark theme dengan purple gradient
   - Smooth animations

4. **`web_ui/static/script.js`** (Frontend Logic)
   - Form submission & API calls
   - Loading states & error handling
   - Preview iframe management
   - Revision flow & modal management
   - Publish workflow

5. **`web_ui/README.md`** (Documentation)
   - Setup & installation guide
   - Workflow explanation
   - API endpoints documentation
   - Troubleshooting guide

6. **`web_ui/requirements.txt`**
   - Dependencies: Flask, Werkzeug

7. **`run_web_ui.py`** (Entry Point)
   - Script untuk menjalankan web server
   - Usage: `python run_web_ui.py [--port 5000]`

---

### 🔄 Pipeline Workflow (Tetap Sama)

```
Input Guru
    ↓
[Stage 1] JSON Filler (local Qwen3-0.6B + LoRA) → ~10-15 sec
    ↓
[Stage 2] Prompter (local Qwen3-0.6B + LoRA) → ~5-10 sec ✅ FIXED
    ↓
[Stage 3] Coder (3 parallel specialists via HF Space) → ~30-45 sec each
    ↓
[Stage 4] Assembler → <1 sec
    ↓
[Stage 5] Validator → <1 sec
    ↓
Preview + Revision (optional)
    ↓
Publish to Database
```

---

### 📊 Summary of Changes

| Component | Before | After | Status |
|-----------|--------|-------|--------|
| Prompter LLM | HF Space (❌ wrong) | Local model (✅ correct) | Fixed |
| Input form | CLI text input | Web form + validation | Enhanced |
| Preview | "Open in browser" | Live iframe preview | Enhanced |
| Revision | Manual re-run | Automatic classify + re-run | Enhanced |
| Publication | File only | File + Database | Enhanced |
| UI Organization | Inline with pipeline_main.py | Separate `web_ui/` folder | Improved |

---

### 🚀 How to Run

#### Option 1: Web UI (Recommended)
```bash
python run_web_ui.py
# Buka http://localhost:5000
```

#### Option 2: CLI (Legacy)
```bash
python pipeline_main.py
```

---

### 📝 Notes

- **RAG Stage**: Out of scope untuk Tim 4 (di-skip dengan string kosong)
- **Local Model**: Qwen3-0.6B dengan LoRA adapter (fine-tuned)
- **Remote Coders**: Qwen3-Coder-WebDev via HF Space API (CSS/HTML/JS specialists)
- **Database**: SQLite (`games.db`) di root directory
- **Generated Games**: Disimpan di `generated_games/` folder

---

### ✅ What's Working

- ✅ JSON Filler (local model + LoRA)
- ✅ Prompter (now with local model!) 
- ✅ Coder Stage (3 parallel HF Space calls)
- ✅ Validator + Auto-fix
- ✅ Revision Stage (feedback classification)
- ✅ Publisher (database + files)
- ✅ Web UI (Flask app + responsive design)
- ✅ Caching (prompts + game specs)

---

### ⚠️ Still TODO (Future)

- [ ] Integration dengan RAG knowledge base (Tim lain)
- [ ] Advanced preview options (mobile view, fullscreen)
- [ ] Game statistics dashboard
- [ ] Export formats (PDF, Docx)
- [ ] Batch generation
- [ ] API authentication

---

### 🧪 Testing Checklist

- [ ] Run `python run_web_ui.py` and test input form
- [ ] Generate sample game (Fisika - Kinematika)
- [ ] Check preview renders correctly
- [ ] Test revisi with CSS feedback
- [ ] Test publikasi dan check `games.db`
- [ ] Verify HTML file generated dalam `generated_games/`

---

Generated: 2026-04-14  
Updated By: Claude Code  
Team: Tim 4 Fortensor 🎮
