# 🎮 Game Type Auto-Detection Fix

## Problem
All generated games were becoming **word_game** quizzes regardless of the input topic. Even when the teacher specified simulation topics like "Simulasi gerak parabola", the system would generate a word_game instead of sim_lab.

## Root Cause
The `fill_json()` function in `pipeline/json_filler.py` was not specifying the `game_type` to the LLM. Without explicit instruction, the LLM defaulted to generating word_game (the simplest game type).

## Solution
Implemented automatic game_type detection in `pipeline/json_filler.py`:

### 1. Added `_determine_game_type()` Function (Lines 87-130)
This function analyzes the topic text and determines the appropriate game type using keyword detection:

```python
def _determine_game_type(topik: str) -> str:
    """Tentukan game_type berdasarkan topik/keywords."""
```

### 2. Keyword Categories

#### sim_lab (Simulation/Experiment)
Keywords that indicate a simulation or experiment game:
- Process keywords: "simulasi", "praktik", "percobaan", "eksperimen"
- Physics: "gerak", "gaya", "energi", "gelombang", "optik", "listrik", "kinematika", "dinamika", "hukum newton", "parabola", "bandul", "pegas", "fluida", "tekanan", "kalor"
- Chemistry: "reaksi", "konsentrasi", "ph", "molaritas"
- Biology: "osmosis", "mitosis", "fotosintesis"

#### puzzle_game (Matching/Pairing)
Keywords that indicate a matching or pairing game:
- "pasang", "matching", "pair", "hubung", "korelasi"
- "relasi", "struktur", "organ", "bagian", "elemen"

#### word_game (Definition/Quiz)
Keywords that indicate a definition or concept quiz:
- "definisi", "konsep", "teori", "arti", "pengertian"
- "istilah", "prinsip", "hukum", "rumus", "persamaan"

### 3. Modified `fill_json()` Function (Lines 143-157)
Now explicitly specifies game_type to the LLM:
1. Calls `_determine_game_type(teacher_input.topik)` to auto-detect
2. Prints debug message: `[auto-detect] game_type: {game_type}`
3. Adds to prompt: `- **Game Type: {game_type}** (WAJIB gunakan tipe ini!)`

This explicit instruction ensures the LLM generates the correct game type.

## Test Results

All test cases pass:
```
✓ "Simulasi gerak parabola..." → sim_lab
✓ "Praktik eksperimen kinematika" → sim_lab
✓ "Hukum Newton dan gaya" → sim_lab
✓ "Energi dan gelombang" → sim_lab
✓ "Definisi kecepatan" → word_game
✓ "Pengertian konsep momentum" → word_game
✓ "Arti istilah Fisika" → word_game
✓ "Pasang struktur sel" → puzzle_game
✓ "Matching organ dengan fungsinya" → puzzle_game
✓ "Hubung elemen dengan sifatnya" → puzzle_game
✓ "Biologi: struktur organisme" → puzzle_game
✓ "Mitosis dalam sel hidup" → sim_lab
```

## Important Fix: Removed Generic Keywords
Initially, `_determine_game_type()` included `"sel"` and `"biologi"` in sim_keywords, which caused conflicts:
- Topic: "Pasang struktur sel" (Match cell structures)
- Problem: "sel" matched sim_lab instead of "pasang" matching puzzle_game

**Fix Applied (Line 99):**
Removed generic keywords, keeping only specific process keywords:
- Removed: `"sel"`, `"biologi"`
- Kept specific processes: `"mitosis"`, `"fotosintesis"`, `"osmosis"`

## Verification Steps
To verify the fix is working:

1. **Run pipeline with simulation topic:**
   ```
   Kelas: SMA-10
   Mapel: Fisika
   Bab: Kinematika
   Subbab: Gerak Parabola
   Topik: Simulasi gerak parabola interaktif
   ```
   Expected: JSON should have `"game_type": "sim_lab"`

2. **Run pipeline with matching topic:**
   ```
   Kelas: SMA-10
   Mapel: Biologi
   Bab: Sel
   Subbab: Struktur Sel
   Topik: Pasang organela dengan fungsinya
   ```
   Expected: JSON should have `"game_type": "puzzle_game"`

3. **Check debug output:**
   Pipeline should print: `[auto-detect] game_type: sim_lab` or `puzzle_game` or `word_game`

## Files Modified
- `pipeline/json_filler.py`
  - Added: `_determine_game_type()` function (lines 87-130)
  - Modified: `fill_json()` to call `_determine_game_type()` and include in prompt (lines 143-157)

## Impact
- ✅ All games will now generate the correct game type based on topic
- ✅ LLM receives explicit game_type instruction
- ✅ No more default word_game for all inputs
- ✅ Supports sim_lab, puzzle_game, and word_game properly
