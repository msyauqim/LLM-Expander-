"""Simple file-based RAG: retrieve ringkasan bab/subtopik."""
import glob
import os
from pipeline.config import RAG_KNOWLEDGE_DIR
from pipeline.models import TeacherInput


def retrieve(teacher_input: TeacherInput) -> str:
    """Cari ringkasan materi berdasarkan input guru.

    Cari file di rag_knowledge/{mapel}/ yang cocok dengan bab/subbab/topik.
    Return isi file sebagai konteks, atau string kosong jika tidak ada.
    """
    mapel = teacher_input.mata_pelajaran.lower()
    mapel_dir = os.path.join(RAG_KNOWLEDGE_DIR, mapel)

    if not os.path.isdir(mapel_dir):
        return ""

    # Cari file yang match
    keywords = [
        teacher_input.bab.lower(),
        teacher_input.subbab.lower(),
        teacher_input.topik.lower(),
    ]
    keywords = [k for k in keywords if k]

    best_match = ""
    best_score = 0

    for fpath in glob.glob(os.path.join(mapel_dir, "*.md")):
        fname = os.path.basename(fpath).lower()
        score = sum(1 for kw in keywords if kw in fname)
        if score > best_score:
            best_score = score
            best_match = fpath

    # Fallback: cari di dalam content file
    if not best_match:
        for fpath in glob.glob(os.path.join(mapel_dir, "*.md")):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            score = sum(1 for kw in keywords if kw in content)
            if score > best_score:
                best_score = score
                best_match = fpath

    if best_match:
        with open(best_match, "r", encoding="utf-8") as f:
            return f.read()

    return ""
