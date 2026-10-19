"""Read media metadata or verify full decode. Never assigns an aesthetic/privacy grade."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def command(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def check(path: Path, mode: str, include_hash: bool, timeout: int) -> dict:
    report = {
        "source": str(path.resolve()), "mode": mode,
        "technical_pass": False if mode == "verify" else None, "aesthetic_checked": False,
        "privacy_checked": False, "errors": [],
    }
    if not path.is_file():
        report["errors"].append("source_missing")
        return report
    probe = shutil.which("ffprobe")
    if not probe:
        report["errors"].append("ffprobe_unavailable")
        return report
    result = command([probe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], timeout)
    if result.returncode:
        report["errors"].append("ffprobe_failed")
        report["diagnostic"] = result.stderr[-1500:]
        return report
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    fmt = data.get("format", {})
    report.update(duration_seconds=float(fmt.get("duration", 0)), size_bytes=path.stat().st_size, has_audio=bool(audios))
    if include_hash:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        report["sha256"] = h.hexdigest()
    if videos:
        v = videos[0]
        rotation = next((x.get("rotation") for x in v.get("side_data_list", []) if "rotation" in x), 0)
        rotation = float(rotation or v.get("tags", {}).get("rotate", 0))
        width, height = v.get("width", 0), v.get("height", 0)
        swapped = round(abs(rotation)) % 180 == 90
        report["video"] = {
            "codec": v.get("codec_name"), "coded_width": width, "coded_height": height,
            "rotation_degrees": rotation,
            "display_width": height if swapped else width,
            "display_height": width if swapped else height,
            "fps": v.get("avg_frame_rate"), "pixel_format": v.get("pix_fmt"),
            "color_primaries": v.get("color_primaries"), "color_transfer": v.get("color_transfer"),
            "color_space": v.get("color_space"),
            "hdr_signal": v.get("color_transfer") in {"arib-std-b67", "smpte2084"},
        }
    else:
        report["errors"].append("no_video_stream")
    report["audio_streams"] = [
        {"codec": a.get("codec_name"), "sample_rate": a.get("sample_rate"), "channels": a.get("channels")}
        for a in audios
    ]
    if mode == "inspect":
        return report
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        report["technical_pass"] = False
        report["errors"].append("ffmpeg_unavailable")
        return report
    decoded = command([ffmpeg, "-hide_banner", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"], timeout)
    report["decode"] = {"exit_code": decoded.returncode, "passed": decoded.returncode == 0}
    if decoded.returncode:
        report["errors"].append("decode_failed")
        report["decode"]["diagnostic"] = decoded.stderr[-1500:]
    report["technical_pass"] = bool(videos) and decoded.returncode == 0
    if audios:
        measured = command([ffmpeg, "-hide_banner", "-i", str(path), "-map", "0:a:0", "-vn", "-af", "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"], timeout)
        found = re.search(r'\{\s*"input_i"[\s\S]*?\}', measured.stderr)
        if measured.returncode == 0 and found:
            levels = json.loads(found.group())
            report["audio_measurement"] = {
                "integrated_lufs": levels["input_i"], "true_peak_dbtp": levels["input_tp"],
                "loudness_range_lu": levels["input_lra"], "listened": False,
                "note": "Measurement only; no aesthetic assessment or automatic loudness approval.",
            }
        else:
            report["audio_measurement"] = {"measured": False, "listened": False}
            report["warnings"] = ["audio_measurement_unavailable"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--mode", choices=("inspect", "verify"), default="inspect")
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON report; no source frames are exported")
    parser.add_argument("--hash", action="store_true", help="Include SHA-256 of the source")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout for each subprocess in seconds")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        report = check(args.source, args.mode, args.hash, args.timeout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        report = {"mode": args.mode, "source": str(args.source), "technical_pass": False if args.mode == "verify" else None,
                  "aesthetic_checked": False, "privacy_checked": False,
                  "errors": [type(error).__name__], "diagnostic": str(error)[-1200:]}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 2 if report.get("errors") or report.get("technical_pass") is False else 0


if __name__ == "__main__":
    sys.exit(main())
