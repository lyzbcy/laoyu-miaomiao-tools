#!/usr/bin/env python3
"""Validate local video/cover/copy manifest. No upload or browser operations."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess, sys

LIMITS = {"douyin": 30, "bilibili": 80, "xiaohongshu": 20, "youtube": 100}
RATIOS = {"4:3": (4, 3), "3:4": (3, 4), "16:9": (16, 9), "9:16": (9, 16)}

def dimensions(path):
    with path.open("rb") as f:
        if f.read(8) == b"\x89PNG\r\n\x1a\n":
            length = struct.unpack(">I", f.read(4))[0]
            if f.read(4) != b"IHDR" or length != 13:
                raise ValueError("Invalid PNG header")
            return struct.unpack(">II", f.read(8))
        f.seek(0)
        if f.read(2) != b"\xff\xd8":
            raise ValueError("Use a PNG or JPEG cover")
        while True:
            lead = f.read(1)
            if not lead:
                raise ValueError("JPEG dimensions not found")
            if lead != b"\xff":
                continue
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            if not marker:
                raise ValueError("Truncated JPEG marker")
            code = marker[0]
            if code in (0xD8, 0x01) or 0xD0 <= code <= 0xD7:
                continue
            if code in (0xD9, 0xDA):
                raise ValueError("JPEG dimensions not found before image data")
            size_raw = f.read(2)
            if len(size_raw) != 2:
                raise ValueError("Truncated JPEG segment")
            size = struct.unpack(">H", size_raw)[0]
            if size < 2:
                raise ValueError("Invalid JPEG segment")
            if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                raw = f.read(5)
                if len(raw) != 5:
                    raise ValueError("Truncated JPEG dimensions")
                height, width = struct.unpack(">HH", raw[1:])
                return width, height
            f.seek(size - 2, 1)

def describe(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Missing or empty file: " + str(path))
    with path.open("rb") as f:
        digest_state = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest_state.update(chunk)
        digest = digest_state.hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}

def check(manifest_path):
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Manifest must be an object")
    base = manifest_path.resolve().parent
    def local(raw):
        if not isinstance(raw, str) or not raw:
            raise ValueError("File path must be a nonempty string")
        return (base / raw).resolve()
    video = describe(local(data.get("video")))
    covers = {}
    cover_specs = data.get("covers", {})
    if not isinstance(cover_specs, dict):
        raise ValueError("covers must be an object")
    for ratio, raw in cover_specs.items():
        if ratio not in RATIOS:
            raise ValueError("Unsupported cover ratio: " + ratio)
        path = local(raw)
        item = describe(path)
        width, height = dimensions(path)
        a, b = RATIOS[ratio]
        if min(width, height) <= 0 or width * b != height * a:
            raise ValueError(f"Cover {ratio} is actually {width}x{height}: {path}")
        item.update(width=width, height=height)
        covers[ratio] = item
    if not covers:
        raise ValueError("Provide at least one cover")
    platforms = data.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        raise ValueError("Provide target platforms")
    for name, item in platforms.items():
        if name not in LIMITS or not isinstance(item, dict):
            raise ValueError("Unknown or invalid platform: " + str(name))
        title = item.get("title", "")
        if not isinstance(title, str) or not title.strip() or len(title) > LIMITS[name]:
            raise ValueError(f"{name} title must contain 1..{LIMITS[name]} characters (verify current page limits)")
        if not isinstance(item.get("description", ""), str):
            raise ValueError(name + " description must be text")
        if name == 'youtube' and len(item.get('description','')) > 5000:
            raise ValueError('youtube description exceeds 5000 characters')
        if name == 'youtube' and ('<' in title or '>' in title):
            raise ValueError('youtube title cannot contain angle brackets')
        prefix=data.get('required_description_prefix','')
        if prefix and (not isinstance(prefix,str) or not item.get('description','').startswith(prefix)):
            raise ValueError(name + ' required description prefix differs')
        markers=item.get('expected_account_markers',[])
        if not isinstance(markers,list) or any(not isinstance(x,str) or not x.strip() for x in markers):
            raise ValueError(name + ' expected_account_markers must be nonempty strings')
        if item.get('visibility') not in (None,'public','private','unlisted'):
            raise ValueError(name + ' invalid visibility')
        topics = item.get("topics", [])
        if not isinstance(topics, list) or any(not isinstance(x, str) or not x.strip() for x in topics):
            raise ValueError(name + " topics must be a list of nonempty strings")
        topic_ids=item.get('topic_ids',{})
        if not isinstance(topic_ids,dict) or any(k not in topics or not isinstance(v,str) or not v.strip() for k,v in topic_ids.items()):
            raise ValueError(name+' topic_ids must map configured topics to nonempty observed IDs')
        if name=='bilibili':
            activities=item.get('activity_topics',[])
            if not topics and not activities:raise ValueError('Bilibili requires at least one actual tag or activity topic')
            if isinstance(activities,str):activities=[activities]
            if not isinstance(activities,list) or len(activities)>1 or any(not isinstance(x,str) or not x.strip() for x in activities):
                raise ValueError('Bilibili allows at most one activity topic per video')
    if data.get('mode','prepare') != 'prepare':
        raise ValueError('This skill scripts drafts only; mode must be prepare')
    if data.get('video_sha256') and data['video_sha256'] != video['sha256']:
        raise ValueError('Video differs from the locked SHA256')
    media = {"status": "not_checked", "reason": "ffprobe unavailable"}
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", video["path"]], capture_output=True, text=True, encoding="utf8", timeout=60)
        if result.returncode:
            raise ValueError("ffprobe failed: " + result.stderr[:500])
        probe = json.loads(result.stdout)
        streams = probe.get("streams", [])
        if not any(s.get("codec_type") == "video" for s in streams):
            raise ValueError("No video stream")
        media = {"status": "probed", "duration": probe.get("format", {}).get("duration"), "streams": [{k:s.get(k) for k in ("codec_type", "codec_name", "width", "height", "sample_rate", "channels")} for s in streams], "full_decode": "not_performed"}
    return {"local_preflight": "passed", "video": video, "covers": covers, "platforms": platforms, "media": media, "browser_verification": "not_performed", "publishing_authorization": "must_follow_current_user_request"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = check(args.manifest)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.SubprocessError, struct.error) as err:
        print("Preflight failed: " + str(err), file=sys.stderr)
        return 1
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf8")
    print("Local preflight passed; browser upload, saved fields and publication state still require verification.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
