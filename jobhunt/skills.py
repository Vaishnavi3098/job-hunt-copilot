"""Skill extraction and work-pass signal detection (plain keyword logic, no AI needed)."""
import re

# canonical skill -> aliases (all lowercase). Extend this list freely.
SKILLS: dict[str, list[str]] = {
    "python": ["python"],
    "sql": ["sql"],
    "javascript": ["javascript"],
    "typescript": ["typescript"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "nlp": ["nlp", "natural language processing"],
    "llm": ["llm", "llms", "large language model", "large language models"],
    "generative ai": ["generative ai", "genai", "gen ai"],
    "prompt engineering": ["prompt engineering", "prompt design"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "embeddings": ["embedding", "embeddings"],
    "vector database": ["vector database", "vector db", "vector store", "chroma", "chromadb",
                        "faiss", "pinecone", "weaviate", "qdrant", "milvus", "pgvector"],
    "langchain": ["langchain"],
    "langgraph": ["langgraph"],
    "llamaindex": ["llamaindex", "llama-index", "llama index"],
    "agents": ["ai agent", "ai agents", "agentic", "multi-agent", "tool calling", "function calling"],
    "mcp": ["mcp", "model context protocol"],
    "fine-tuning": ["fine-tuning", "fine tuning", "finetuning", "lora", "qlora", "peft"],
    "hugging face": ["hugging face", "huggingface", "transformers"],
    "openai api": ["openai", "gpt-4", "chatgpt api"],
    "claude / anthropic": ["anthropic", "claude"],
    "gemini": ["gemini", "vertex ai"],
    "llm evaluation": ["llm evaluation", "evals", "ragas", "llm-as-a-judge", "guardrails"],
    "ollama / local models": ["ollama", "vllm", "llama.cpp"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "streamlit": ["streamlit"],
    "gradio": ["gradio"],
    "rest api": ["rest api", "rest apis", "restful"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "cicd", "github actions", "jenkins"],
    "aws": ["aws", "amazon web services", "sagemaker", "bedrock"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "mlops": ["mlops", "mlflow", "kubeflow", "model deployment"],
    "postgresql": ["postgres", "postgresql"],
    "mongodb": ["mongodb"],
    "redis": ["redis"],
    "airflow": ["airflow"],
    "spark": ["spark", "pyspark"],
    "kafka": ["kafka"],
    "linux": ["linux"],
    "react": ["react", "reactjs"],
    "computer vision": ["computer vision", "opencv"],
    "data analysis": ["data analysis", "data analytics"],
        "observability": ["observability", "monitoring", "tracing"],
    "governance": ["governance", "human-in-the-loop", "human in the loop", "responsible ai"],
    "orchestration": ["orchestration", "orchestrator"],
    "system design": ["reference architecture", "reference architectures", "system design", "solution architecture"],
}

# Signals that a posting may be limited by nationality or work pass.
# These are hints only, never a decision about whether you can apply.
PASS_SIGNALS: dict[str, str] = {
    r"singapore citizens?|singaporeans?": "mentions Singapore citizens / Singaporeans",
    r"\bpr\b|permanent residents?": "mentions PR / permanent residents",
    r"employment pass|\bep\b": "mentions Employment Pass",
    r"s pass": "mentions S Pass",
    r"work pass|work permit": "mentions work pass / work permit",
    r"visa sponsorship|sponsorship": "mentions sponsorship",
    r"right to work|eligible to work|work authori[sz]ation": "mentions work eligibility",
}


def _pattern(alias: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9+#])" + re.escape(alias) + r"s?(?![a-z0-9+#])")


_COMPILED = {skill: [_pattern(a) for a in aliases] for skill, aliases in SKILLS.items()}


def extract_skills(text: str) -> list[str]:
    """Return the sorted list of known skills mentioned in text."""
    low = text.lower()
    return sorted(s for s, pats in _COMPILED.items() if any(p.search(low) for p in pats))


def work_pass_signals(text: str) -> list[str]:
    low = text.lower()
    return [label for pat, label in PASS_SIGNALS.items() if re.search(pat, low)]
