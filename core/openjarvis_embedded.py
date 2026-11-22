"""In-process OpenJarvis SDK adapter for Mark-LVII.

No OpenJarvis HTTP server, extra UI, or localhost port is started here.
The upstream `openjarvis` package must be installed in this interpreter,
and its model/engine dependencies configured using upstream instructions.
"""
from __future__ import annotations

import importlib
import threading
from typing import Any

ALLOWED_AGENTS = frozenset({"simple", "orchestrator", "native_react", "deep_research"})
# Conservative default set: no shell, code execution, file modification, or unrestricted tools.
ALLOWED_TOOLS = frozenset({"calculator", "think", "web_search", "retrieval", "file_read"})
MAX_QUESTION = 4000
MAX_RESPONSE = 12000


class EmbeddedOpenJarvisError(RuntimeError):
    pass


class EmbeddedOpenJarvis:
    """Thread-safe lazy SDK wrapper, with explicit capability filtering.

    The OpenJarvis SDK may use an Ollama engine or cloud model underneath;
    this adapter itself never launches an HTTP listener. All tool permissions
    are controlled by the caller and the upstream SDK's own policies.
    """

    def __init__(self, *, engine: str = "", model: str = ""):
        self.engine = str(engine or "").strip()
        self.model = str(model or "").strip()
        self._sdk: Any = None
        self._lock = threading.RLock()

    def _get_sdk(self):
        if self._sdk is None:
            try:
                module = importlib.import_module("openjarvis")
                cls = getattr(module, "Jarvis")
            except (ImportError, AttributeError) as exc:
                raise EmbeddedOpenJarvisError(
                    "OpenJarvis Python SDK isn't installed in this Python environment. "
                    "See OPENJARVIS_EMBEDDED_SETUP.md."
                ) from exc
            options = {}
            if self.engine:
                options["engine_key"] = self.engine
            if self.model:
                options["model"] = self.model
            try:
                self._sdk = cls(**options)
            except Exception as exc:
                raise EmbeddedOpenJarvisError(
                    f"OpenJarvis SDK initialization failed: {type(exc).__name__}: {exc}"
                ) from exc
        return self._sdk

    def status(self) -> str:
        with self._lock:
            sdk = self._get_sdk()
            return f"Embedded OpenJarvis SDK ready (version {getattr(sdk, 'version', 'unknown')}); no OpenJarvis server required."

    def ask(self, question: str, *, agent: str = "simple", tools: str | list[str] = "") -> str:
        question = str(question or "").strip()
        if not question or len(question) > MAX_QUESTION:
            raise ValueError(f"Question must be 1-{MAX_QUESTION} characters")
        agent = str(agent or "simple").strip().lower()
        if agent not in ALLOWED_AGENTS:
            raise ValueError("Allowed agent modes: " + ", ".join(sorted(ALLOWED_AGENTS)))
        if isinstance(tools, str):
            selected = [s.strip().lower() for s in tools.split(",") if s.strip()]
        elif isinstance(tools, list):
            selected = [str(s).strip().lower() for s in tools if str(s).strip()]
        else:
            raise ValueError("Tools must be a list or comma-separated string")
        if len(selected) > 5 or not set(selected).issubset(ALLOWED_TOOLS):
            raise ValueError("Only supported read-only tools are permitted: " + ", ".join(sorted(ALLOWED_TOOLS)))
        # Fully in-process call; JARVIS's plugin executor handles the worker thread.
        with self._lock:
            sdk = self._get_sdk()
            try:
                response = sdk.ask_full(question, agent=agent, tools=selected, context=True)
            except Exception as exc:
                raise EmbeddedOpenJarvisError(
                    f"Embedded agent failed: {type(exc).__name__}: {exc}"
                ) from exc
        if not isinstance(response, dict) or not isinstance(response.get("content"), str):
            raise EmbeddedOpenJarvisError("Unexpected response from OpenJarvis SDK")
        return response["content"][:MAX_RESPONSE]

    def close(self):
        with self._lock:
            sdk, self._sdk = self._sdk, None
            if sdk is not None:
                sdk.close()


_instance: EmbeddedOpenJarvis | None = None
_instance_lock = threading.RLock()


def instance(*, engine: str = "", model: str = "") -> EmbeddedOpenJarvis:
    global _instance
    with _instance_lock:
        if _instance is None or (_instance.engine, _instance.model) != (engine, model):
            if _instance is not None:
                _instance.close()
            _instance = EmbeddedOpenJarvis(engine=engine, model=model)
        return _instance
