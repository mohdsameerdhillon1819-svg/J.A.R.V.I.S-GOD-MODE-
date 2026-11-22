# Embedded OpenJarvis inside JARVIS Mark-LVII

The `openjarvis_agent` plugin now calls the upstream `openjarvis.Jarvis` **Python SDK directly in the Mark-LVII process**. It does not call `127.0.0.1:8000`, open the OpenJarvis GUI, or require `jarvis serve`. It does need the OpenJarvis SDK and an inference engine with a model (some engine choices may themselves be local processes, such as Ollama).

## Install the Python SDK

OpenJarvis uses native Rust extensions and supports Python 3.11–3.13. Per its official SDK instructions, install its source in the same Python interpreter/virtual environment used to run Mark-LVII. From a VS Code PowerShell terminal with Mark-LVII's virtual environment activated:

```powershell
# Install these prerequisites first: Git, Rust toolchain, uv.
git clone https://github.com/open-jarvis/OpenJarvis.git external/OpenJarvis
cd external/OpenJarvis
uv sync
uv run maturin develop -m rust/crates/openjarvis-python/Cargo.toml
```

**Important:** The commands above create an OpenJarvis-managed `.venv` via `uv sync`. Unless the project's `uv` environment is **the same interpreter** that starts Mark-LVII, Python won't find the installed SDK. To install into Mark-LVII's environment, use the documented upstream build workflow with that environment active, or point Mark-LVII at an interpreter which has both dependencies installed. Confirm with:

```powershell
python -c "from openjarvis import Jarvis; print('Embedded SDK import OK')"
```

Configure an inference engine/model using OpenJarvis's own documentation. Then start **only** `python main.py` in Mark-LVII (no OpenJarvis server). Enable `openjarvis_agent` in Plugin Settings. Set engine and model there or leave both blank for defaults.

## Available in-process modes

- `simple`: text responses
- `orchestrator`: multi-step agent (restricted read-only tools)
- `native_react`: reasoning with restricted tools
- `deep_research`: research if available in your upstream installed version

Supported tool list in this adapter: `calculator`, `think`, `web_search`, `retrieval`, `file_read`. These tools require corresponding OpenJarvis support and user consent for external web or file access. Dangerous/executable tools are intentionally not auto-enabled.

## Scope / limits

This integrates the **documented Python SDK agent interface directly** into JARVIS. It does **not** copy all upstream features into Mark-LVII, including schedules, connectors, Rust components, skill-store management, every research benchmark, the OpenJarvis desktop UI, or the upstream model engine. Those are major independent subsystems, some with separate dependencies or authentication. The God's Eye View 3D plugin and hand gestures remain unchanged and separate from this patch.

If `Embedded OpenJarvis unavailable` appears, run the SDK import check above and verify model/engine configuration. A missing SDK/model is reported explicitly instead of silently attempting a localhost fallback.

Official reference: https://open-jarvis.github.io/OpenJarvis/getting-started/installation/
