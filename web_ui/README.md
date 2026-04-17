# Web UI untuk Pipeline 3-LLM

Web interface Flask untuk Game Edukasi Generator dengan 3-LLM Pipeline.

## Fitur

✅ **Input Form Guru** - Interface untuk input kelas, mata pelajaran, bab, subbab, topik

✅ **Game Generation** - Automatic generation dengan tahapan:
- JSON Filler (local Qwen3-0.6B + LoRA)
- Prompter (local Qwen3-0.6B + LoRA)
- 3 Specialist Coders (parallel via HF Space API)
- Validator & Fix Loop

✅ **Live Preview** - Preview game langsung di iframe

✅ **Revision Stage** - Teacher feedback → automatic re-run specialist yang relevan

✅ **Publication** - Publish ke SQLite database + save HTML file

## Instalasi & Setup

### 1. Install Dependencies

```bash
pip install flask
```

### 2. Run Web Server

```bash
python web_ui/app.py
```

Output:
```
============================================================
🎮 PIPELINE 3-LLM Web UI
============================================================
Buka: http://localhost:5000
============================================================
```

### 3. Open Browser

```
http://localhost:5000
```

## Workflow

### Step 1: Input Guru
Guru mengisi form:
- Kelas (SMA-10, SMA-11, SMA-12)
- Mata Pelajaran (Fisika, Kimia, Biologi, Matematika)
- Bab (e.g., "Kinematika")
- Subbab (optional)
- Topik (optional)

### Step 2: Game Generation
Backend akan:
1. **JSON Filler** - Generate complete game spec (10-15 sec)
2. **Prompter** - Generate 3 prompts + shared variable registry (5-10 sec)
3. **Coder Stage** - 3 specialists generate CSS/HTML/JS in parallel (30-45 sec each)
4. **Assembler** - Combine into single HTML file (<1 sec)
5. **Validator** - Auto-fix syntax errors (<1 sec)

Total: ~60-90 seconds

### Step 3: Preview
Game dimuat di iframe untuk teacher review.

Opsi:
- **Revisi** - Submit feedback, akan di-classify dan re-run specialist yang tepat
- **Publikasi** - Save ke database

### Step 4: Revision (Optional)
Jika ada revisi:
1. Teacher submit feedback
2. System classify: CSS, HTML, atau Complex?
3. Re-run specialist yang relevan (30-45 sec)
4. Assembler + Validator
5. Preview updated game

### Step 5: Publication
Publish ke database:
- Save HTML file ke `generated_games/`
- Insert ke SQLite `games.db`
- Mark as published

## File Structure

```
web_ui/
├── __init__.py
├── app.py                 # Flask app main
├── README.md
├── requirements.txt
├── templates/
│   └── index.html        # Main UI template
└── static/
    ├── style.css         # Styling
    └── script.js         # Frontend logic
```

## API Endpoints

### POST /api/generate
Generate game dari teacher input.

Request:
```json
{
  "kelas": "SMA-10",
  "mata_pelajaran": "Fisika",
  "bab": "Kinematika",
  "subbab": "Gerak Lurus",
  "topik": "Kecepatan Konstan"
}
```

Response:
```json
{
  "status": "success",
  "game_type": "sim_lab",
  "title": "Simulasi Kinematika",
  "message": "Game berhasil di-generate!"
}
```

### GET /api/preview
Load HTML game untuk preview.

Response:
```json
{
  "html": "<html>...</html>",
  "html_b64": "base64-encoded-html"
}
```

### POST /api/revise
Submit feedback revisi game.

Request:
```json
{
  "feedback": "Ubah warna latar jadi biru tua"
}
```

Response:
```json
{
  "status": "success",
  "category": "css",
  "message": "Game direvisi (kategori: css)"
}
```

### POST /api/publish
Publikasikan game ke database.

Response:
```json
{
  "status": "success",
  "game_id": "game_phys10_kin_001",
  "file": "kinematika_20260414_125832.html",
  "message": "Game published! ID: game_phys10_kin_001"
}
```

### GET /api/status
Check status pipeline.

Response:
```json
{
  "has_game": true,
  "game_type": "sim_lab"
}
```

## Troubleshooting

### Port 5000 sudah digunakan

```bash
python web_ui/app.py --port 5001
```

### Game generation timeout

Jika generation terlalu lama:
- Check HF Space API status: https://huggingface.co/spaces/Qwen/Qwen3-Coder-WebDev
- Check network connection
- Try dengan topik yang lebih sederhana

### Preview blank

Jika iframe tidak menampilkan game:
- Check browser console (F12) untuk error message
- Verify HTML content di response `/api/preview`

## Development

### Modify Template

Edit `templates/index.html` dan refresh browser.

### Modify Style

Edit `static/style.css` dan refresh browser.

### Modify API Logic

Edit `app.py` dan restart server.

## Notes

- Session data disimpan di memory, bukan database
- Reset session saat browser refresh atau server restart
- RAG stage di-skip (out of scope Tim 4)
- Prompter menggunakan **local model** (Qwen3-0.6B + LoRA)
- Coder stage menggunakan **HF Space API** (Qwen3-Coder-WebDev)

## Contact

Tim 4 Fortensor 🎮
