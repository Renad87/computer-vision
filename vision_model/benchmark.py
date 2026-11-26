"""CPU vs MPS benchmark of the shared encoder and heads on this machine.

    .venv/bin/python -B -m vision_model.benchmark

Measures, per device: model load time; decode+preprocess per image; single-image forward latency
(median and p95 over 50 runs after 10 warm-up runs); batch-64 throughput; head time for scene, tags
and an 8-way linear head of the emotion head's shape (the heads are NumPy, device independent);
process peak RSS and, on MPS, driver-allocated memory. Images are real EmoSet images from the archive.
Writes evaluation/vision/benchmark_<host>.json.
"""
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time

import numpy as np

from . import config


def _sync(device):
    import torch

    if device == "mps":
        torch.mps.synchronize()


def bench_device(device, items, runs=50, warmup=10, batch=64):
    import torch

    from .backbone import ClipEncoder, decode_image, load_clip

    load_clip.cache_clear()
    t0 = time.perf_counter()
    enc = ClipEncoder(device)
    load_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    tensors = [enc.preprocess(decode_image(it["bytes"])) for it in items[:200]]
    prep_ms = (time.perf_counter() - t0) / 200 * 1000
    one = tensors[0].unsqueeze(0)
    for _ in range(warmup):
        enc.encode_tensors(one)
    lat = []
    for i in range(runs):
        x = tensors[i % len(tensors)].unsqueeze(0)
        _sync(device)
        t = time.perf_counter()
        enc.encode_tensors(x)
        _sync(device)
        lat.append((time.perf_counter() - t) * 1000)
    big = torch.stack(tensors[:batch])
    enc.encode_tensors(big)
    times = []
    for _ in range(5):
        _sync(device)
        t = time.perf_counter()
        enc.encode_tensors(big)
        _sync(device)
        times.append(time.perf_counter() - t)
    out = {"device": device, "load_seconds": round(load_s, 3), "decode_preprocess_ms_per_image": round(prep_ms, 3),
           "forward_batch1_ms_median": round(statistics.median(lat), 3),
           "forward_batch1_ms_p95": round(float(np.percentile(lat, 95)), 3),
           f"forward_batch{batch}_images_per_second": round(batch / statistics.median(times), 1),
           "runs": runs, "warmup": warmup}
    if device == "mps":
        out["mps_driver_allocated_mb"] = round(torch.mps.driver_allocated_memory() / 2**20, 1)
    return out


def bench_heads(n=2000):
    from contracts.taxonomy import load_taxonomy

    from .heads import load_old_scene_head, load_old_tag_head

    tax = load_taxonomy()
    scene, tags = load_old_scene_head(tax), load_old_tag_head(tax)
    rng = np.random.default_rng(config.SEED)
    z = rng.standard_normal((1, 512)).astype(np.float32)
    W8, b8 = rng.standard_normal((8, 512)).astype(np.float32), np.zeros(8, np.float32)
    t = time.perf_counter()
    for _ in range(n):
        scene.probs(z)
        tags.logits(z)
        z @ W8.T + b8
    return {"heads_ms_per_image": round((time.perf_counter() - t) / n * 1000, 4),
            "note": "scene softmax + 34 tag scores + one 8-way linear layer (random weights, timing only)"}


def machine():
    def sysctl(key):
        try:
            return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=True).stdout.strip()
        except Exception:  # noqa: BLE001
            return None

    import torch

    mem = sysctl("hw.memsize")
    return {"cpu": sysctl("machdep.cpu.brand_string"), "memory_gb": round(int(mem) / 2**30, 1) if mem else None,
            "macos": platform.mac_ver()[0], "python": platform.python_version(), "torch": torch.__version__,
            "torch_threads": torch.get_num_threads(), "mps_available": torch.backends.mps.is_available()}


def main():
    import torch

    from .features import emoset_items

    items = []
    for it in emoset_items():
        items.append(it)
        if len(items) >= 200:
            break
    report = {"machine": machine(), "images": "first 200 images of external/renad/emoset.zip (sorted by path)",
              "devices": []}
    for device in ["cpu"] + (["mps"] if torch.backends.mps.is_available() else []):
        report["devices"].append(bench_device(device, items))
    report["heads"] = bench_heads()
    report["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 1)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    host = platform.machine()
    path = os.path.join(config.REPORTS_DIR, f"benchmark_{host}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    json.dump(report, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
