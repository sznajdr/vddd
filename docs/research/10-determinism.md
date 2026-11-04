# 10 — Determinism and reproducibility (D-32, DoD-5, M8)

## Findings

- `torch.use_deterministic_algorithms(True)` forces deterministic implementations where they exist and errors where they do not; PyTorch states it does not by itself guarantee reproducibility, and deterministic kernels are slower. ([PyTorch docs](https://docs.pytorch.org/docs/stable/generated/torch.use_deterministic_algorithms.html))
- NVIDIA's guidance (TAO Toolkit): reproducibility is only expected on the **same GPU architecture, library versions and GPU count**; bit-for-bit is not guaranteed for every model; keep `cudnn.benchmark` off; a fixed seed is still required for initialisation. ([TAO docs](https://docs.nvidia.com/tao/tao-toolkit/7.0.1/text/deterministic_training.html))
- Ultralytics (YOLOv5 PR #8213) sets cuDNN deterministic, benchmark off, `use_deterministic_algorithms(True)` and `CUBLAS_WORKSPACE_CONFIG=:4096:8` when seeding training; current docs could not be fetched from this session, so the `deterministic` flag's inference behaviour is unverified. ([commit mirror](https://huggingface.co/spaces/xiang-wuu/yolov5/commit/27d831b6e4ae4b0286ba0159f5c8542e052cd3c9))
- TF32 (`torch.backends.cuda.matmul.allow_tf32`, `torch.backends.cudnn.allow_tf32`) changes numerics on Ampere+ GPUs and must be pinned explicitly; no source in this pass covered it, so this is from general knowledge.

## Implications for the spec

1. **D-32 is the right contract:** cross-machine bit-identity of detections is not achievable in general; quantised canonical export + recorded environment knobs is. Already implemented in `m8_storage.canonical`.
2. **`producer_version.determinism_env` must record:** `torch`, `cuda`, `cudnn`, driver, GPU model and count, `use_deterministic_algorithms`, `cudnn.benchmark`, `cudnn.deterministic`, `allow_tf32` (matmul and cudnn), `CUBLAS_WORKSPACE_CONFIG`, seed, half-precision flag, batch size (batch composition can change results). The DDL already has the column; the DoD for M2 should enumerate these keys.
3. **Optional same-environment bit-exact CI** (D-32) = run the pilot's 3 OD-1x races twice on the same machine and diff the *unquantised* sidecars; report, do not gate.
