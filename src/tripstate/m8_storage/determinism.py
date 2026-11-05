"""Environment fingerprint for `versions.determinism_env` (SPEC-2.0.0-draft §9, D-32; backlog C3).

Records what is actually installed and set: interpreter, platform, numpy/opencv/ffmpeg versions, and — only when
torch is importable — its CUDA/cuDNN versions, GPU model/count, the deterministic-algorithm, cuDNN benchmark /
deterministic and TF32 flags, `CUBLAS_WORKSPACE_CONFIG`; plus the run's seed, half-precision flag, batch size and
model-weight SHA-256s as given by the caller. Anything absent is `null`, never guessed; nothing is executed on a GPU.
The dict is key-sorted and JSON-serializable so the same environment yields byte-identical output (D-32)."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

FINGERPRINT_VERSION = 1


def _version_of(module: str) -> str | None:
    try:
        m = importlib.import_module(module)
    except (ImportError, OSError):      # absent, or present but unloadable (e.g. opencv without libGL)
        return None
    return str(getattr(m, "__version__", None))


def _ffmpeg_version(ffmpeg: str = "ffmpeg") -> str | None:
    if shutil.which(ffmpeg) is None:
        return None
    try:
        out = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    first = out.strip().splitlines()[0] if out.strip() else ""
    parts = first.split()
    return parts[2] if len(parts) >= 3 and parts[0] == "ffmpeg" else (first or None)


def _nvidia_driver() -> str | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[0] if lines else None


def _torch_block() -> dict[str, Any]:
    keys = ("torch", "cuda", "cudnn", "cuda_available", "gpu_count", "gpu_models", "use_deterministic_algorithms",
            "cudnn_benchmark", "cudnn_deterministic", "tf32_matmul", "tf32_cudnn")
    block: dict[str, Any] = dict.fromkeys(keys)
    try:
        torch = importlib.import_module("torch")
    except (ImportError, OSError):
        return block
    try:
        block["torch"] = str(torch.__version__)
        block["cuda"] = getattr(torch.version, "cuda", None)
        block["cudnn"] = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
        avail = bool(torch.cuda.is_available())
        block["cuda_available"] = avail
        block["gpu_count"] = torch.cuda.device_count() if avail else 0
        block["gpu_models"] = [torch.cuda.get_device_name(i) for i in range(block["gpu_count"])] if avail else []
        block["use_deterministic_algorithms"] = bool(torch.are_deterministic_algorithms_enabled())
        block["cudnn_benchmark"] = bool(torch.backends.cudnn.benchmark)
        block["cudnn_deterministic"] = bool(torch.backends.cudnn.deterministic)
        block["tf32_matmul"] = bool(torch.backends.cuda.matmul.allow_tf32)
        block["tf32_cudnn"] = bool(torch.backends.cudnn.allow_tf32)
    except (AttributeError, RuntimeError) as e:   # partial torch builds: record what could not be read, never guess
        block["read_error"] = f"{type(e).__name__}: {e}"
    return block


def weight_hashes(paths: list[str | Path]) -> dict[str, str | None]:
    """{basename: sha256} for the given weight files; a missing file records null rather than failing silently."""
    out: dict[str, str | None] = {}
    for p in paths:
        p = Path(p)
        out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return out


def fingerprint(seed: int | None = None, half_precision: bool | None = None, batch_size: int | None = None,
                weights: list[str | Path] | None = None, ffmpeg: str = "ffmpeg") -> dict[str, Any]:
    fp: dict[str, Any] = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": _version_of("numpy"),
        "opencv": _version_of("cv2"),
        "ffmpeg": _ffmpeg_version(ffmpeg),
        "nvidia_driver": _nvidia_driver(),
        "torch": _torch_block(),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "seed": seed,
        "half_precision": half_precision,
        "batch_size": batch_size,
        "model_weight_hashes": weight_hashes(weights or []),
    }
    return json.loads(json.dumps(fp, sort_keys=True))


def fingerprint_json(**kw: Any) -> str:
    return json.dumps(fingerprint(**kw), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def versions_row(producer_version: str, producer_kind: str, extractor_version: str | None = None,
                 module_git_hashes: dict[str, str] | None = None, **kw: Any) -> dict[str, Any]:
    """A `versions` table row with determinism_env filled (JSON text), ready for Store.insert."""
    fp = fingerprint(**kw)
    return {"producer_version": producer_version, "producer_kind": producer_kind, "extractor_version": extractor_version,
            "module_git_hashes": json.dumps(module_git_hashes or {}, sort_keys=True),
            "model_weight_hashes": json.dumps(fp["model_weight_hashes"], sort_keys=True),
            "determinism_env": json.dumps(fp, sort_keys=True, separators=(",", ":"), ensure_ascii=False)}
