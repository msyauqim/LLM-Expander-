"""Data models untuk pipeline."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TeacherInput:
    kelas: str          # "SMA-10", "SMA-11", "SMA-12"
    mata_pelajaran: str  # "Fisika", "Kimia", "Biologi", "Matematika"
    bab: str
    subbab: str
    topik: str = ""     # opsional


@dataclass
class GameSpec:
    """Complete JSON game specification (envelope.json v1.2)."""
    data: dict  # Full JSON sesuai envelope schema


@dataclass
class VariableRegistry:
    """Shared contract antara CSS/HTML/JS specialists."""
    dom_ids: list = field(default_factory=list)
    css_classes: list = field(default_factory=list)
    js_variables: list = field(default_factory=list)
    js_functions: list = field(default_factory=list)

    def to_context_string(self) -> str:
        lines = ["=== VARIABLE REGISTRY (SHARED CONTRACT) ==="]
        lines.append(f"DOM IDs: {', '.join(self.dom_ids)}")
        lines.append(f"CSS Classes: {', '.join(self.css_classes)}")
        lines.append(f"JS Variables: {', '.join(self.js_variables)}")
        lines.append(f"JS Functions: {', '.join(self.js_functions)}")
        return "\n".join(lines)


@dataclass
class PromptTriple:
    """Output dari LLM Prompter: 3 prompts + variable registry."""
    css_prompt: str
    html_prompt: str
    js_prompt: str
    registry: VariableRegistry


@dataclass
class AssembledGame:
    """Hasil assembler: 1 file HTML."""
    html: str
    css_raw: str = ""
    html_raw: str = ""
    js_raw: str = ""


@dataclass
class ValidationResult:
    passed: bool
    errors: list = field(default_factory=list)


@dataclass
class RevisionInput:
    feedback: str
    category: str = ""  # "css", "html", "complex"
