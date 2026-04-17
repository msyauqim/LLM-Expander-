"""
pipeline_main.py
Pipeline 3-LLM: Input Guru → JSON Filler + RAG → Prompter → 3 Specialists → Assembler → Preview → Publish
"""
import json
import os
import sys
import datetime
from concurrent.futures import ThreadPoolExecutor

# Tambah parent dir ke path agar pipeline/ bisa diimport
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.config import OUTPUT_DIR, SUBJECTS, GRADES
from pipeline.models import TeacherInput
from pipeline.json_filler import fill_json
from pipeline.llm_client import get_local_model
from pipeline.rag import retrieve
from pipeline.prompter import generate_prompts
from pipeline.coder import run_coder_stage, rerun_specialist
from pipeline.revision import classify
from pipeline.publisher import publish


def input_stage() -> TeacherInput:
    """Kumpulkan input dari guru via CLI."""
    print("\n" + "=" * 60)
    print("INPUT GURU")
    print("=" * 60)

    # Kelas
    print(f"Pilih kelas: {', '.join(GRADES)}")
    kelas = input("  Kelas: ").strip()
    if kelas not in GRADES:
        # Coba mapping singkat
        mapping = {"10": "SMA-10", "11": "SMA-11", "12": "SMA-12"}
        kelas = mapping.get(kelas, kelas)

    # Mata pelajaran
    print(f"Pilih mapel: {', '.join(SUBJECTS)}")
    mapel = input("  Mata Pelajaran: ").strip()

    bab = input("  Bab: ").strip()
    subbab = input("  Subbab: ").strip()
    topik = input("  Topik (opsional, tekan Enter untuk skip): ").strip()

    return TeacherInput(
        kelas=kelas,
        mata_pelajaran=mapel,
        bab=bab,
        subbab=subbab,
        topik=topik,
    )


def save_html(html: str, teacher_input: TeacherInput) -> str:
    """Simpan HTML ke file, return path."""
    import re
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe = re.sub(r'[^a-zA-Z0-9]', '_', teacher_input.bab.lower()[:30]).strip('_') or "game"
    safe = re.sub(r'_+', '_', safe)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"{safe}_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    print("=" * 60)
    print("PIPELINE 3-LLM: Game Edukasi Generator")
    print("Input Guru -> JSON Filler + RAG -> Prompter -> 3 Coders")
    print("=" * 60)

    # Preload model sekali di awal agar run berikutnya langsung
    print("\nMemuat model... (hanya sekali)")
    get_local_model()
    print("Model siap!\n")

    while True:
        # === STAGE 1: INPUT ===
        teacher_input = input_stage()

        # === STAGE 2: PREP (JSON Filler) ===
        print("\n[Stage 2] Prompt Preparation...")
        print("  Track A: Mini LLM JSON Filler...")
        game_spec = fill_json(teacher_input)
        rag_summary = ""  # RAG belum diimplementasi

        # === DISPLAY & SAVE JSON OUTPUT ===
        game_type = game_spec.data.get('game_type', '?')
        game_id = game_spec.data.get('game_id', 'unknown')
        print(f"\n✅ JSON Spec Generated!")
        print(f"   game_id: {game_id}")
        print(f"   game_type: {game_type}")

        # Save JSON to file untuk easy inspection
        json_file = os.path.join(OUTPUT_DIR, f"{game_id}_spec.json")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(game_spec.data, f, ensure_ascii=False, indent=2)
        print(f"   💾 Saved to: {json_file}")

        # Display full JSON in console
        print("\n" + "="*80)
        print("📋 FULL JSON GAME SPEC (untuk review):")
        print("="*80)
        json_str = json.dumps(game_spec.data, ensure_ascii=False, indent=2)
        print(json_str)
        print("="*80 + "\n")

        # Ask user to review
        review = input("Review JSON OK? (y/n/edit): ").strip().lower()
        if review == 'n':
            print("Dibatalkan! Coba lagi dengan input berbeda.")
            continue
        elif review == 'edit':
            print(f"Edit file di: {json_file}")
            print("Kemudian jalankan pipeline lagi.")
            continue

        print("✅ Melanjutkan ke Stage 3...\n")

        # === STAGE 3: PROMPTER ===
        print("[Stage 3] LLM Prompter (generating 3 prompts)...")
        prompt_triple = generate_prompts(game_spec, rag_summary)
        print(f"  CSS prompt: {len(prompt_triple.css_prompt)} chars")
        print(f"  HTML prompt: {len(prompt_triple.html_prompt)} chars")
        print(f"  JS prompt: {len(prompt_triple.js_prompt)} chars")
        print(f"  Registry: {len(prompt_triple.registry.dom_ids)} DOM IDs, "
              f"{len(prompt_triple.registry.css_classes)} classes, "
              f"{len(prompt_triple.registry.js_functions)} functions")

        # === STAGE 4: CODER (3 parallel specialists) ===
        print("\n[Stage 4] Coder Stage (3 parallel specialists)...")
        game = run_coder_stage(prompt_triple)

        # Simpan HTML
        html_path = save_html(game.html, teacher_input)
        print(f"\n  Game disimpan ke: {html_path}")

        # === STAGE 5: PREVIEW ===
        print("\n[Stage 5] Preview")
        print(f"  Buka file di browser: {html_path}")

        # Revision loop
        while True:
            print("\nKeputusan:")
            print("  1. Approve (publish)")
            print("  2. Revisi")
            print("  3. Skip (tanpa publish)")
            choice = input("  Pilih (1/2/3): ").strip()

            if choice == "1":
                # === STAGE 7: PUBLISH ===
                game_id = publish(game, game_spec)
                print(f"  Game published! ID: {game_id}")
                break

            elif choice == "2":
                # === STAGE 6: REVISION ===
                feedback = input("  Feedback revisi: ").strip()
                revision = classify(feedback)
                print(f"  Klasifikasi: {revision.category}")

                if revision.category == "complex":
                    # Re-run dari prompter
                    print("  Re-generating dari LLM Prompter...")
                    # Tambahkan feedback ke RAG summary
                    rag_with_feedback = rag_summary + f"\n\nFeedback guru: {feedback}"
                    prompt_triple = generate_prompts(game_spec, rag_with_feedback)
                    game = run_coder_stage(prompt_triple)
                else:
                    # Re-run specialist tertentu
                    role = revision.category  # "css" atau "html"
                    prompt = prompt_triple.css_prompt if role == "css" else prompt_triple.html_prompt
                    revised_prompt = f"{prompt}\n\nREVISI GURU: {feedback}"

                    print(f"  Re-running {role.upper()} specialist...")
                    game = rerun_specialist(role, revised_prompt, prompt_triple.registry, game)

                html_path = save_html(game.html, teacher_input)
                print(f"  Game revisi disimpan ke: {html_path}")

            else:
                print("  Skipped.")
                break

        # Lanjut atau quit
        again = input("\nBuat game lagi? (y/n): ").strip().lower()
        if again != "y":
            print("Selesai!")
            break


if __name__ == "__main__":
    main()
