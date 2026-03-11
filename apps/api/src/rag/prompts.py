"""Prompt templates for RAG pipeline."""

SYSTEM_PROMPT = """Du bist ein Enterprise Knowledge Assistant. Deine Aufgabe ist es, Fragen von Mitarbeitern präzise und hilfreich zu beantworten, basierend auf den bereitgestellten Dokumenten.

Regeln:
1. Antworte NUR basierend auf den bereitgestellten Kontext-Dokumenten.
2. Verwende Quellenverweise im Format [1], [2] etc. inline in deiner Antwort.
3. Wenn der Kontext die Frage nicht beantwortet, sage das ehrlich.
4. Antworte in der Sprache der Frage (Deutsch oder Englisch).
5. Strukturiere längere Antworten mit Absätzen oder Aufzählungen.
6. Zitiere keine ganzen Dokumente, sondern fasse relevante Informationen zusammen.
7. Wenn mehrere Quellen die gleiche Information enthalten, bevorzuge die aktuellere."""

NO_ANSWER_INSTRUCTION = """Ich konnte in den verfügbaren Dokumenten keine ausreichende Antwort auf deine Frage finden.

Mögliche Gründe:
- Das Thema ist noch nicht in den synchronisierten Quellen dokumentiert.
- Die Frage bezieht sich auf Informationen, auf die ich keinen Zugriff habe.

Bitte wende dich an die zuständige Abteilung oder stelle deine Frage spezifischer."""

QUERY_REWRITE_PROMPT = """Schreibe die folgende Benutzer-Frage so um, dass sie für eine semantische Suche in einer Wissensdatenbank optimiert ist.

Konversationskontext (letzte Nachrichten):
{conversation_context}

Aktuelle Frage: {query}

Umgeschriebene Frage (nur die Frage, keine Erklärung):"""


def build_system_prompt() -> str:
    """Build the system prompt for answer generation."""
    return SYSTEM_PROMPT


def build_context_prompt(chunks: list[dict]) -> str:
    """Build context section from retrieved and reranked chunks."""
    if not chunks:
        return NO_ANSWER_INSTRUCTION

    parts = ["Hier sind die relevanten Dokumente:\n"]
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title", "Unbekannt")
        content = chunk.get("content", "")
        source = chunk.get("source_url", "")
        parts.append(f"[{i}] Titel: {title}")
        if source:
            parts.append(f"    Quelle: {source}")
        parts.append(f"    Inhalt: {content}\n")

    return "\n".join(parts)
