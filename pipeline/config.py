"""Konfigurasi pipeline."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Model lokal (DISABLED for speed - use HF Space instead)
USE_LOCAL_MODEL = True  # Set to True if you want local model
LOCAL_MODEL = "Qwen/Qwen3-4B"  # Keep original 4B model
LORA_PATH = os.path.join(BASE_DIR, "hasil latih qwen 4B di colab")

# HF Space (Coder Specialists) - primary method
HF_SPACE = "Qwen/Qwen3-Coder-WebDev"
HF_API_ENDPOINT = "/generate_code"

# Paths
SCHEMA_DIR = os.path.join(BASE_DIR, "dataset", "Json Schema")
ENVELOPE_SCHEMA = os.path.join(SCHEMA_DIR, "envelope.json")
PAYLOAD_SCHEMAS = {
    "word_game": os.path.join(SCHEMA_DIR, "word_game.json"),
    "puzzle_game": os.path.join(SCHEMA_DIR, "puzzle_game.json"),
    "sim_lab": os.path.join(SCHEMA_DIR, "simlab.json"),
}
RAG_KNOWLEDGE_DIR = os.path.join(BASE_DIR, "rag_knowledge")
CACHE_DIR = os.path.join(BASE_DIR, ".pipeline_cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated_games")
DB_PATH = os.path.join(BASE_DIR, "games.db")

# Validator
MAX_VALIDATION_RETRIES = 3

# Subjects & grades (enum values dari schema)
SUBJECTS = ["Fisika", "Kimia", "Biologi", "Matematika"]
GRADES = ["SMA-10", "SMA-11", "SMA-12"]
GAME_TYPES = ["word_game", "puzzle_game", "sim_lab"]
THEME_PRESETS = ["classroom", "scifi_neon", "nature", "retro", "minimal", "adventure"]
