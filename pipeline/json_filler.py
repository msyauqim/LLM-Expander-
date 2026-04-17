"""Mini LLM JSON Filler: isi field JSON yang kosong menggunakan Qwen3-4B+LoRA."""
import json
import re
try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False
from pipeline.models import TeacherInput, GameSpec
from pipeline.llm_client import call_local_model
from pipeline import cache

SYSTEM_PROMPT = """Kamu adalah asisten AI pembuat JSON game edukasi sesuai schema v1.2.
Diberikan input guru (kelas, mapel, bab, subbab, topik), lengkapi semua field JSON.

**PENTING: Output HANYA JSON valid, TANPA teks tambahan, TANPA penjelasan, TANPA markdown.**

**ATURAN FORMAT KETAT:**
1. Output HANYA JSON valid (tidak ada teks lain)
2. Mulai langsung dengan { (tanpa karakter sebelumnya)
3. Akhiri dengan } (tanpa karakter sesudahnya)
4. JANGAN gunakan markdown code block (```)
5. SEMUA string harus double quotes (",  TIDAK single quotes (')
6. Tidak boleh ada semicolon (;), trailing commas, atau komentar (// atau /* */)
7. SEMUA key dan value harus dalam Bahasa Indonesia atau Bahasa Inggris — DILARANG karakter China/Arab/non-latin
7. Pastikan quotes seimbang dan benar

ATURAN KETAT:
- schema_version: "1.2"
- game_id: format "game_{subject}{grade}_{topic}_{number}" contoh: "game_phys10_kin_word_001"
- game_type: "word_game" | "puzzle_game" | "sim_lab"
- metadata.subject: "Fisika" | "Kimia" | "Biologi" | "Matematika"
- metadata.grade_level: "SMA-10" | "SMA-11" | "SMA-12"
- metadata.difficulty: integer 1-5
- metadata.estimated_duration_minutes: integer 5-60
- metadata.learning_objectives: array of string, 1-5 item
- metadata.language: "id"
- presentation.opening: OBJECT {id, show_once, title, story, image_description, cta_text}
- presentation.visual_element: OBJECT {theme_name, theme_preset, mood, color_palette{primary,secondary,background,accent,text}, setting_description, art_style}
  - theme_preset: "classroom"|"scifi_neon"|"nature"|"retro"|"minimal"|"adventure"
  - color_palette: hex #RRGGBB
- presentation.instructions: OBJECT {id, trigger{type,position,icon,label}, steps[{step,text}]}
- presentation.hint: OBJECT {id, scope, trigger, content{title,strategy,formula,example,hint_image_description}}
- presentation.audio: OBJECT {enabled, tracks[{id,event,description}]}
  - event: "on_correct_action"|"on_wrong_action"|"on_win"|"on_lose"|"background"
- presentation.visual_element HARUS include:
  - gradient_bg: CSS gradient untuk main background
  - setting_description: Deskripsi detail tempat/suasana game
  - art_style: Gaya seni (e.g., "flat minimalist with neon glow")
  - ambient_elements: Array elemen ambient (asap, cahaya, dll)
  - canvas_scene: OBJECT dengan struktur berlapis:
    - render_method: "css_divs"
    - background_layers: Array background layer (gradient, glow, pattern)
    - objects: Array objek dekoratif (papan, lampu, dll) dengan posisi & animasi
    - particle_effects: Array efek partikel (asap, kilau, dll)
  - ui_components: Detail styling untuk button, card, score_display, input
- payload: sesuai game_type (word_game/puzzle_game/sim_lab)
- win_lose_condition: OBJECT {applicable, win{description,logic,feedback_text}, lose{description,logic,feedback_text,retry_allowed}}
- gameplay_parameters: OBJECT {scoring{}, lives, time_limit_seconds, pass_threshold}

CONTOH visual_element YANG BENAR:
{
  "theme_name": "Science Lab",
  "theme_preset": "minimal",
  "mood": "ekspresif dan amati",
  "color_palette": {"primary":"#1E90FF","secondary":"#FF6347","background":"#f8fafc","accent":"#ff6347","text":"#1e90ff"},
  "gradient_bg": "linear-gradient(135deg, #f8fafc 0%, #e3f2fd 100%)",
  "setting_description": "Laboratorium sains modern dengan meja percobaan, peralatan fisika, dan layar monitor digital.",
  "art_style": "flat modern with subtle shadows",
  "ambient_elements": ["Cahaya laboratorium lembut", "Efek shimmer pada peralatan"],
  "canvas_scene": {
    "render_method": "css_divs",
    "background_layers": [
      {"id":"bg_main","type":"gradient","css_description":"Dasar lab: linear-gradient(to bottom, #f8fafc 0%, #e3f2fd 100%)","z_index":0},
      {"id":"bg_glow","type":"image_css","css_description":"Glow halus: radial-gradient(circle at 50% 30%, rgba(30,144,255,0.08), transparent)","z_index":1}
    ],
    "objects": [
      {"id":"table","shape_description":"Meja percobaan: div 60% x 40%, background rgba(200,200,200,0.2), border 1px solid #ccc","position":"top:20%; left:20%","animation":null}
    ],
    "particle_effects": [
      {"type":"shimmer","count":3,"css_description":"Kilau: div 8px, border-radius 50%, background rgba(30,144,255,0.3), animasi twinkle 3s infinite"}
    ]
  },
  "ui_components": {
    "button_style": "Rounded 4px, background #1E90FF, color white, border none, padding 10px 20px, cursor pointer, hover: background #1874D2, transition 0.2s",
    "card_style": "Background white, border-radius 8px, box-shadow 0 2px 8px rgba(0,0,0,0.1), padding 16px",
    "score_display_style": "Font 24px bold, color #1E90FF, text-align center",
    "input_style": "Border 1px solid #ccc, border-radius 4px, padding 8px, font-size 14px"
  }
}"""


# Field yang WAJIB valid agar pipeline tidak crash
VALID_GAME_TYPES = {"word_game", "puzzle_game", "sim_lab"}

# Field di bawah hanya di-WARN, tidak di-fix otomatis
# Bisa dikembangkan sesuai kebutuhan guru nanti
WARN_ENUMS = {
    "subject":      {"Fisika", "Kimia", "Biologi", "Matematika"},
    "grade_level":  {"SMA-10", "SMA-11", "SMA-12"},
    "theme_preset": {"classroom", "scifi_neon", "nature", "retro", "minimal", "adventure"},
}


def _validate_and_fix_fields(data: dict, expected_game_type: str = None) -> dict:
    """Validasi field JSON setelah di-parse.

    FIX  : field yang kalau salah bikin pipeline crash (game_type, difficulty type)
    WARN : field fleksibel yang bisa berkembang (subject, grade, theme, language, duration)
    """
    fixed = []
    warnings = []

    # === FIX: game_type — wajib valid agar pipeline tahu cara assemble payload ===
    gt = data.get("game_type", "")
    if gt not in VALID_GAME_TYPES:
        data["game_type"] = expected_game_type or "word_game"
        fixed.append(f"game_type: '{gt}' → '{data['game_type']}'")
    elif expected_game_type and gt != expected_game_type:
        warnings.append(
            f"game_type: model pilih '{gt}', auto-detect '{expected_game_type}' (pakai model)"
        )

    # === FIX: difficulty — harus integer agar tidak crash saat kalkulasi ===
    meta = data.get("metadata", {})
    if isinstance(meta, dict):
        diff = meta.get("difficulty")
        try:
            meta["difficulty"] = int(diff)
        except (TypeError, ValueError):
            meta["difficulty"] = 2
            fixed.append(f"metadata.difficulty: '{diff}' → 2 (bukan integer)")
        data["metadata"] = meta

    # === WARN only: field fleksibel ===
    if isinstance(meta, dict):
        for field, valid_set in WARN_ENUMS.items():
            if field in ("subject", "grade_level"):
                val = meta.get(field)
                if val and val not in valid_set:
                    warnings.append(
                        f"metadata.{field}: '{val}' tidak dalam preset — ok kalau memang disengaja"
                    )

    pres = data.get("presentation", {})
    if isinstance(pres, dict):
        ve = pres.get("visual_element", {})
        if isinstance(ve, dict):
            tp = ve.get("theme_preset", "")
            if tp and tp not in WARN_ENUMS["theme_preset"]:
                warnings.append(f"theme_preset: '{tp}' tidak dalam preset bawaan — ok kalau custom")

    if fixed:
        print(f"  [field-validator] Fixed {len(fixed)}: {', '.join(fixed)}")
    if warnings:
        print(f"  [field-validator] Warn  {len(warnings)}: {', '.join(warnings)}")
    if not fixed and not warnings:
        print(f"  [field-validator] ✅ OK")

    data = _fill_empty_payload(data)
    return data


def _fill_empty_payload(data: dict) -> dict:
    """Isi payload kosong secara programmatic berdasarkan game_type dan metadata."""
    game_type = data.get("game_type", "word_game")
    payload = data.get("payload", {})

    # Cek apakah payload sudah berisi (tidak perlu diisi)
    if payload and len(payload) > 2:
        return data

    print(f"  [payload-filler] Payload kosong terdeteksi, mengisi programmatically untuk {game_type}...")

    meta = data.get("metadata", {})
    topik = meta.get("topik", meta.get("title", "Materi Pelajaran"))
    subject = meta.get("subject", "Fisika")
    subbab = meta.get("subbab", topik)

    if game_type == "word_game":
        data["payload"] = {
            "word_game_subtype": "fill_blank",
            "intro_narrative": f"Uji pemahamanmu tentang {topik}! Jawab setiap pertanyaan dengan benar.",
            "instruction": f"Baca setiap pertanyaan dan pilih atau isi jawaban yang benar tentang {subbab}.",
            "word_bank": [topik, subbab, subject],
            "questions": [
                {
                    "id": 1,
                    "type": "fill_blank",
                    "prompt": f"Apa yang dimaksud dengan {topik}?",
                    "answer": topik,
                    "explanation": f"{topik} adalah konsep penting dalam {subbab} pada mata pelajaran {subject}."
                },
                {
                    "id": 2,
                    "type": "fill_blank",
                    "prompt": f"Dalam {subbab}, {topik} berkaitan dengan bidang studi apa?",
                    "answer": subject,
                    "explanation": f"{topik} merupakan bagian dari {subject} yang dipelajari di sekolah."
                },
                {
                    "id": 3,
                    "type": "fill_blank",
                    "prompt": f"Sebutkan satu contoh penerapan {topik} dalam kehidupan sehari-hari!",
                    "answer": f"Penerapan {topik}",
                    "explanation": f"Konsep {topik} banyak diterapkan dalam kehidupan sehari-hari di bidang {subject}."
                }
            ],
            "outro_narrative": f"Selamat! Kamu telah menyelesaikan kuis tentang {topik}."
        }

    elif game_type == "puzzle_game":
        data["payload"] = {
            "puzzle_subtype": "matching",
            "intro_narrative": f"Pasangkan istilah-istilah dalam {topik} dengan definisinya!",
            "pairs": [
                {
                    "id": "p_001",
                    "left": {"type": "text", "content": topik},
                    "right": {"type": "text", "content": f"Konsep utama dalam {subbab}"},
                    "explanation": f"{topik} adalah konsep dasar yang perlu dipahami dalam {subbab}."
                },
                {
                    "id": "p_002",
                    "left": {"type": "text", "content": subbab},
                    "right": {"type": "text", "content": f"Bagian dari materi {subject} yang membahas {topik}"},
                    "explanation": f"{subbab} mencakup pembahasan tentang {topik} secara mendalam."
                },
                {
                    "id": "p_003",
                    "left": {"type": "text", "content": subject},
                    "right": {"type": "text", "content": "Mata pelajaran yang mempelajari fenomena alam"},
                    "explanation": f"{subject} adalah ilmu yang mempelajari berbagai fenomena termasuk {topik}."
                }
            ],
            "distractors": [
                f"Konsep yang tidak berkaitan dengan {topik}",
                f"Definisi yang salah tentang {subbab}"
            ]
        }

    elif game_type == "sim_lab":
        data["payload"] = {
            "instruction": f"Lakukan simulasi untuk memahami konsep {topik}. Ubah variabel dan amati perubahannya.",
            "variables": [
                {"id": "var_1", "name": "Parameter 1", "symbol": "x", "unit": "-", "default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}
            ],
            "formula": {"equation": "y = x", "description": f"Hubungan dasar dalam {topik}"},
            "sim_steps": [
                {"step": 1, "instruction": f"Atur nilai parameter sesuai yang ingin diamati."},
                {"step": 2, "instruction": "Klik Jalankan Simulasi dan amati hasilnya."},
                {"step": 3, "instruction": "Catat hasil dan bandingkan dengan prediksimu."}
            ],
            "analysis_questions": [
                {"id": "q_1", "question": f"Apa yang terjadi pada sistem saat parameter diubah?", "type": "short_answer"}
            ],
            "scene": {
                "title": f"Simulasi {topik}",
                "narrative": f"Selamat datang di lab virtual {topik}!",
                "context": f"Kamu berada di laboratorium untuk mempelajari {topik}.",
                "interactive_objects": [
                    {"id": "obj_1", "label": "Objek Utama", "visual_description": "Kotak 50x50px dengan warna biru", "position": "left: 50%; top: 50%", "bound_to_variable": "var_1", "visual_response": "Ukuran berubah proporsional dengan nilai parameter"}
                ],
                "visual_feedback": [
                    {"id": "vf_1", "type": "value_display", "description": "Tampilkan nilai parameter saat ini", "bound_to": "var_1"}
                ]
            }
        }

    # Isi win_lose_condition jika kosong
    wlc = data.get("win_lose_condition", {})
    if not wlc or not wlc.get("win"):
        data["win_lose_condition"] = {
            "applicable": True,
            "win": {
                "description": "Siswa menjawab dengan benar",
                "logic": "correct_count >= pass_threshold",
                "feedback_text": f"Selamat! Kamu berhasil memahami {topik}!",
                "feedback_audio": "sfx_win"
            },
            "lose": {
                "description": "Siswa kehabisan nyawa atau waktu",
                "logic": "lives <= 0",
                "feedback_text": f"Belum berhasil. Pelajari lagi tentang {topik} dan coba lagi!",
                "feedback_audio": "sfx_lose",
                "retry_allowed": True
            }
        }

    # Isi gameplay_parameters jika kosong
    gp = data.get("gameplay_parameters", {})
    if not gp or not gp.get("scoring"):
        data["gameplay_parameters"] = {
            "scoring": {"correct": 10, "wrong": -2},
            "lives": 3,
            "time_limit_seconds": 300,
            "pass_threshold": 70
        }

    print(f"  [payload-filler] ✅ Payload terisi ({game_type})")
    return data


def _determine_game_type(topik: str) -> str:
    """Tentukan game_type berdasarkan topik/keywords."""
    if not topik:
        return "word_game"  # default

    topik_lower = topik.lower()

    # Keywords untuk sim_lab (simulasi/praktik)
    sim_keywords = [
        "simulasi", "praktik", "percobaan", "eksperimen", "simulasi",
        "gerak", "gaya", "energi", "gelombang", "optik", "listrik",
        "kimia", "reaksi", "konsentrasi", "ph", "molaritas",
        "osmosis", "mitosis", "fotosintesis",  # removed "sel" and "biologi" (too generic)
        "kinematika", "dinamika", "hukum newton", "parabola",
        "bandul", "pegas", "fluida", "tekanan", "kalor"
    ]

    # Keywords untuk puzzle_game (matching/pairing)
    puzzle_keywords = [
        "pasang", "matching", "pair", "hubung", "korelasi",
        "relasi", "struktur", "organ", "bagian", "elemen"
    ]

    # Keywords untuk word_game (definisi/teori/quiz)
    word_keywords = [
        "definisi", "konsep", "teori", "arti", "pengertian",
        "istilah", "prinsip", "hukum", "rumus", "persamaan"
    ]

    # Check keywords
    for keyword in sim_keywords:
        if keyword in topik_lower:
            return "sim_lab"

    for keyword in puzzle_keywords:
        if keyword in topik_lower:
            return "puzzle_game"

    for keyword in word_keywords:
        if keyword in topik_lower:
            return "word_game"

    # Default
    return "word_game"


def fill_json(teacher_input: TeacherInput) -> GameSpec:
    """Isi JSON game spec dari input guru."""
    cache_key = f"json_filler:{teacher_input.kelas}:{teacher_input.mata_pelajaran}:{teacher_input.bab}:{teacher_input.subbab}:{teacher_input.topik}"

    cached = cache.get(cache_key)
    if cached:
        print("  [cache hit] JSON spec")
        return GameSpec(data=json.loads(cached))

    # 🎯 DETERMINE GAME TYPE
    game_type = _determine_game_type(teacher_input.topik)
    print(f"  [auto-detect] game_type: {game_type}")

    prompt = (
        f"Buatkan JSON game edukasi lengkap sesuai schema v1.2:\n"
        f"- Kelas: {teacher_input.kelas}\n"
        f"- Mata Pelajaran: {teacher_input.mata_pelajaran}\n"
        f"- Bab: {teacher_input.bab}\n"
        f"- Subbab: {teacher_input.subbab}\n"
    )
    if teacher_input.topik:
        prompt += f"- Topik: {teacher_input.topik}\n"

    # 🎯 EXPLICITLY SPECIFY GAME TYPE
    prompt += f"- **Game Type: {game_type}** (WAJIB gunakan tipe ini!)\n"

    prompt += "\n**INSTRUKSI KETAT:**\n"
    prompt += "1. Output HANYA JSON valid\n"
    prompt += "2. Mulai langsung dengan { (tanpa teks sebelumnya)\n"
    prompt += "3. Akhiri dengan } (tanpa teks sesudahnya)\n"
    prompt += "4. JANGAN ada markdown code block\n"
    prompt += "5. Semua field harus terisi dengan data yang valid dan realistis\n"
    prompt += "6. visual_element HARUS include canvas_scene dengan background_layers, objects, particle_effects\n"
    prompt += "7. ui_components harus detail dengan exact CSS descriptions\n"
    prompt += "8. Jadikan game VISUAL KAYA - banyak layer, dekorasi, efek, animasi"

    raw = call_local_model(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=1800)

    print(f"  [debug] Raw output length: {len(raw)}")

    # Parse JSON (prefix '{' jika belum ada)
    if not raw.strip().startswith("{"):
        print(f"  [debug] Adding opening brace")
        raw = "{" + raw

    data = _parse_json(raw)
    if data:
        print(f"  [debug] Parsed OK, keys: {list(data.keys())}")
        data = _validate_and_fix_fields(data, expected_game_type=game_type)
        cache.put(cache_key, json.dumps(data, ensure_ascii=False))
        return GameSpec(data=data)

    print(f"  [debug] Parse failed!")
    print(f"  [debug] First 300 chars: {repr(raw[:300])}")
    print(f"  [debug] Last 300 chars: {repr(raw[-300:])}")

    # Coba sekali lagi dengan cleaning lebih agresif
    print(f"  [debug] Trying aggressive cleanup...")
    raw_clean = re.sub(r'[^\{\}\[\]:,.\-\w":\s]', '', raw)
    data = _parse_json(raw_clean)
    if data:
        print(f"  [debug] Aggressive cleanup worked! Keys: {list(data.keys())}")
        data = _validate_and_fix_fields(data, expected_game_type=game_type)
        cache.put(cache_key, json.dumps(data, ensure_ascii=False))
        return GameSpec(data=data)

    # Last resort: potong JSON sebelum "payload" dan tutup — payload akan diisi programmatically
    print(f"  [debug] Trying truncate-before-payload strategy...")
    first = raw.find('{')
    if first != -1:
        truncated = raw[first:]
        # Cari posisi "payload" dan potong di sana
        payload_pos = truncated.find('"payload"')
        if payload_pos == -1:
            payload_pos = truncated.find('"win_lose_condition"')
        if payload_pos == -1:
            payload_pos = len(truncated)

        candidate = truncated[:payload_pos].rstrip().rstrip(',')
        # Tutup semua bracket yang terbuka
        open_braces = candidate.count('{') - candidate.count('}')
        open_brackets = candidate.count('[') - candidate.count(']')
        if candidate.count('"') % 2 != 0:
            candidate += '"'
        candidate += ']' * max(0, open_brackets)
        candidate += '}' * max(0, open_braces)
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)

        try:
            data = json.loads(candidate)
            print(f"  [debug] Truncate strategy worked! Keys: {list(data.keys())}")
            data = _validate_and_fix_fields(data, expected_game_type=game_type)
            cache.put(cache_key, json.dumps(data, ensure_ascii=False))
            return GameSpec(data=data)
        except json.JSONDecodeError as e:
            print(f"  [debug] Truncate strategy failed: {e}")

    raise ValueError(f"Gagal parse JSON dari Mini LLM setelah multiple attempts. Output:\n{raw[:1000]}")


def _escape_inner_quotes(text: str) -> str:
    """Escape unescaped quotes inside JSON string values using a state machine."""
    result = []
    i = 0
    n = len(text)

    # Simplified state: are we currently inside a string?
    in_string = False
    prev_backslash = False

    while i < n:
        ch = text[i]

        if in_string:
            if prev_backslash:
                result.append(ch)
                prev_backslash = False
                i += 1
                continue

            if ch == '\\':
                result.append(ch)
                prev_backslash = True
                i += 1
                continue

            if ch == '"':
                # Peek ahead to decide if this is the legitimate closing quote
                # A closing quote is followed by: whitespace then one of : , } ]
                j = i + 1
                while j < n and text[j] in ' \t\r\n':
                    j += 1
                next_char = text[j] if j < n else ''
                if next_char in (':', ',', '}', ']'):
                    # Legitimate closing quote
                    result.append(ch)
                    in_string = False
                else:
                    # Unescaped inner quote — escape it
                    result.append('\\"')
                i += 1
                continue

            result.append(ch)
            i += 1
        else:
            if ch == '"':
                result.append(ch)
                in_string = True
                i += 1
            else:
                result.append(ch)
                i += 1

    return ''.join(result)


def _repair_json(text: str) -> str:
    """Perbaiki kesalahan JSON umum dari output LLM kecil."""
    s = text

    # 0. Escape unescaped quotes inside string values (e.g. "story": "kata "X" dan ...")
    s = _escape_inner_quotes(s)

    # 1. Fix UNQUOTED hex colors: "text"#1B5E20} -> "text":"#1B5E20"}
    #    Only match # NOT preceded by opening quote (avoids breaking ,"#hex")
    s = re.sub(r'"(#[0-9a-fA-F]{3,8})([,}\]])', r'":"\1"\2', s)

    # 2. Fix double colon: "mood"":"" -> "mood":""
    s = re.sub(r'"":', '":', s)

    # 3. Iterative fix for ALL "Expecting ':'" errors
    #    Handles: "key","value" and "key""value" and "key"{  etc.
    s = _fix_colon_errors(s)

    # 4. Trailing commas before } or ]
    s = re.sub(r',\s*([}\]])', r'\1', s)

    return s



def _fix_colon_errors(text: str) -> str:
    """Fix all 'Expecting : delimiter' errors iteratively.

    Handles:
    - "key","value" (comma instead of colon)
    - "key""value"  (missing colon entirely)
    - "key"{ or "key"[ (missing colon before object/array)
    """
    max_iterations = 80
    s = text

    for _ in range(max_iterations):
        try:
            json.loads(s)
            return s
        except json.JSONDecodeError as e:
            if "Expecting ':' delimiter" not in str(e):
                return s

            pos = e.pos
            # Look around error position for fixable patterns
            search_start = max(0, pos - 5)
            search_end = min(len(s), pos + 5)
            window = s[search_start:search_end]

            fixed = False

            # Try 1: comma that should be colon
            comma_offset = window.find(',')
            if comma_offset != -1:
                abs_pos = search_start + comma_offset
                before = s[:abs_pos].rstrip()
                after = s[abs_pos + 1:].lstrip()
                if before.endswith('"') and (
                    after.startswith('"') or after.startswith('{') or
                    after.startswith('[') or after[0:1].isdigit() or
                    after.startswith('true') or after.startswith('false') or
                    after.startswith('null') or after.startswith('#')
                ):
                    s = s[:abs_pos] + ':' + s[abs_pos + 1:]
                    fixed = True

            # Try 2: missing colon entirely — insert ':' at error position
            if not fixed:
                # The error position is where ':' is expected
                # Typically right after a closing quote of a key
                before = s[:pos].rstrip()
                after = s[pos:].lstrip()
                if before.endswith('"') and (
                    after.startswith('"') or after.startswith('{') or
                    after.startswith('[') or after[0:1].isdigit() or
                    after.startswith('true') or after.startswith('false') or
                    after.startswith('null')
                ):
                    # Insert colon between key and value
                    s = before + ':' + after
                    fixed = True

            if not fixed:
                return s  # Can't fix this error

    return s


def _parse_json(text: str) -> dict:
    """Parse JSON dari output LLM dengan berbagai fallback."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()

    # Bersihkan trailing semicolon dan quotes
    cleaned = re.sub(r'[;\'"]\s*$', '', cleaned)

    # Strip inline // comments (Qwen3-4B sering nulis ini di JSON)
    cleaned = re.sub(r'//[^\n"]*(?=\n|,|\}|\])', '', cleaned)

    # Fix double quote pada key: "key"": → "key":
    cleaned = re.sub(r'("(?:[^"\\]|\\.)*)""\s*:', r'\1":', cleaned)

    # Fix object pakai koma sebagai separator key-value: {"k","v"} → {"k":"v"}
    # Pattern: "string","string" di dalam object context
    cleaned = re.sub(r'(\{|,)\s*"([^"]+)"\s*,\s*"([^"]+)"\s*(?=[,}])', r'\1"\2":"\3"', cleaned)

    # Hapus key berbahasa non-ASCII (Chinese/Arabic/dll) beserta valuenya
    cleaned = re.sub(r'"[^\x00-\x7F][^"]*"\s*:\s*"[^"]*"', '', cleaned)
    cleaned = re.sub(r'"[^\x00-\x7F][^"]*"\s*:\s*[^,}\]]+', '', cleaned)

    # Fix unescaped newline di dalam string JSON
    def fix_newlines_in_strings(s):
        result = []
        in_string = False
        i = 0
        while i < len(s):
            c = s[i]
            if c == '\\' and in_string:
                result.append(c)
                i += 1
                if i < len(s):
                    result.append(s[i])
                i += 1
                continue
            if c == '"':
                in_string = not in_string
            if in_string and c == '\n':
                result.append('\\n')
                i += 1
                continue
            result.append(c)
            i += 1
        return ''.join(result)
    cleaned = fix_newlines_in_strings(cleaned)

    # *** REPAIR dulu sebelum parse ***
    if HAS_JSON_REPAIR:
        try:
            repaired = repair_json(cleaned, return_objects=True)
            if isinstance(repaired, dict) and repaired:
                return repaired
        except Exception:
            pass
    cleaned = _repair_json(cleaned)

    # Attempt 1: raw_decode - ambil JSON pertama saja (ignore extra data)
    first = cleaned.find('{')
    if first != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(cleaned, first)
            return obj
        except json.JSONDecodeError as e:
            print(f"  [debug] raw_decode failed: {str(e)[:100]}")

    # Attempt 2: Direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  [debug] Direct parse failed: {str(e)[:100]}")

    # Attempt 3: Cari { ... } dan fix common issues
    last = cleaned.rfind('}')
    if first != -1 and last > first:
        candidate = cleaned[first:last + 1]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        candidate = re.sub(r'"([^"]+)\'', r'"\1"', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            print(f"  [debug] Bracket extraction failed: {str(e)[:100]}")

    # Attempt 4: Truncated JSON - tutup brackets yang kurang
    if first != -1:
        candidate = cleaned[first:]
        candidate = re.sub(r'[;\'"]\s*$', '', candidate)
        candidate = re.sub(r',\s*$', '', candidate)
        candidate = re.sub(r'\s+$', '', candidate)

        open_braces = candidate.count('{') - candidate.count('}')
        open_brackets = candidate.count('[') - candidate.count(']')

        if candidate.count('"') % 2 != 0:
            candidate += '"'

        candidate += ']' * max(0, open_brackets)
        candidate += '}' * max(0, open_braces)
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            print(f"  [debug] Bracket closing failed: {str(e)[:100]}")

    return None
