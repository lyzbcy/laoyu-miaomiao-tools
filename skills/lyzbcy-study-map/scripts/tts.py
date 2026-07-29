"""
lyzbcy-study-map · 后台语音播报 · 批量音频+字幕生成脚本
======================================================
把一份「语音稿 JSON」批量合成成 .mp3 音频文件 + 整句字幕 .json 文件，
供学习地图的「后台语音」按钮播放。

原理
----
调用微软 Edge 浏览器同款的 Azure Neural TTS（edge-tts 库），免 API Key。
- 中文音质业界最好（晓晓/云希等）
- ⚠️ **依赖联网**：合成时需要联网调用微软服务
- ⚠️ **非真·离线**：合成完成后，播放是纯本地（浏览器放本地 mp3）
- ⚠️ 商用有灰色地带，个人学习自用没问题

字幕原理
--------
edge-tts 的 stream() 会发 SentenceBoundary 事件（中文按句切分），带：
  - offset（微秒，100ns 单位）
  - duration（微秒）
  - text（该句文本）
把这些转成秒，写成 [{start, end, text}, ...] 的 JSON。
播放器的字幕引擎按当前播放秒数高亮对应句子。

用法
----
    # 1) 准备语音稿 JSON（格式见下方 EXAMPLE）
    # 2) 批量合成（mp3 + 字幕 JSON 同时生成）
    python scripts/tts.py audio-script.json --out-dir audio/

    # 自定义音色（默认晓晓女声）
    python scripts/tts.py audio-script.json --out-dir audio/ --voice zh-CN-YunxiNeural

语音稿 JSON 格式（audio-script.json）
-------------------------------------
    {
      "voice": "zh-CN-XiaoxiaoNeural",       // 可选，覆盖默认音色
      "items": [
        {"id": "ch1", "title": "第一章 核心判断", "text": "口语化播报文本……"},
        {"id": "ch2", "title": "第二章 关键概念", "text": "口语化播报文本……"}
      ]
    }

产物
----
输出到 --out-dir（默认 audio/）下，每个 item 两个文件：
  - <id>.mp3   音频
  - <id>.json  整句字幕（与 mp3 同名，播放器自动加载）
例如：audio/ch1.mp3、audio/ch1.json、audio/ch2.mp3、audio/ch2.json
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 微软"晓晓"，中文女声，最自然温暖
MAX_RETRIES = 3  # 单段最多重试次数（edge-tts 调用微软服务偶发超时，自动重试更稳）


async def synthesize_one(text: str, voice: str, mp3_path: Path, json_path: Path) -> None:
    """合成单段 mp3 + 整句字幕 JSON。

    用 stream() 手动收集两类事件：
      - 'audio': 音频字节
      - 'SentenceBoundary' / 'WordBoundary': 整句/整词边界（带时间戳）

    写出：
      - mp3_path: 音频文件
      - json_path: 字幕 [{start, end, text}, ...]（秒）
    """
    import asyncio as _aio

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_chunks = []
            boundaries = []
            async for event in communicate.stream():
                etype = event.get("type")
                if etype == "audio":
                    audio_chunks.append(event["data"])
                elif etype in ("SentenceBoundary", "WordBoundary"):
                    # offset/duration 单位是 100 纳秒（HundredNanoseconds），转秒
                    offset_s = event.get("offset", 0) / 1e7
                    dur_s = event.get("duration", 0) / 1e7
                    seg_text = (event.get("text") or "").strip()
                    if seg_text:
                        boundaries.append({
                            "start": round(offset_s, 2),
                            "end": round(offset_s + dur_s, 2),
                            "text": seg_text,
                        })
            # 写 mp3
            mp3_path.write_bytes(b"".join(audio_chunks))
            # 写字幕 JSON
            json_path.write_text(
                json.dumps(boundaries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return  # 成功
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = attempt * 2  # 2s, 4s 退避
                print(f"           ⚠️  第 {attempt} 次失败（{type(e).__name__}），{wait}s 后重试…")
                await _aio.sleep(wait)
    raise last_err  # 重试用尽，抛出最后一个错误


async def synthesize_all(items, voice: str, out_dir: Path) -> int:
    """批量合成。返回成功条数。每个 item 同时产出 .mp3 和 .json。"""
    ok = 0
    for i, item in enumerate(items, 1):
        item_id = item.get("id") or f"item{i}"
        title = item.get("title", item_id)
        text = item.get("text", "").strip()
        if not text:
            print(f"  [{i}/{len(items)}] ⚠️  跳过 {item_id}（text 为空）")
            continue
        mp3_path = out_dir / f"{item_id}.mp3"
        json_path = out_dir / f"{item_id}.json"
        print(f"  [{i}/{len(items)}] 合成 {item_id} · {title}")
        try:
            await synthesize_one(text, voice, mp3_path, json_path)
            mp3_size = mp3_path.stat().st_size
            sub_count = len(json.loads(json_path.read_text(encoding="utf-8")))
            print(f"           ✅ {mp3_path.name} ({mp3_size // 1024} KB) + {json_path.name} ({sub_count} 句字幕)")
            ok += 1
        except Exception as e:
            print(f"           ❌ 失败：{e}")
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="lyzbcy 后台语音播报 · 批量音频+字幕生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="详见模块 docstring 了解语音稿 JSON 格式与字幕产物。",
    )
    parser.add_argument("script", help="语音稿 JSON 文件路径")
    parser.add_argument(
        "--out-dir", "-o", default="audio", help="输出目录（默认: audio/）"
    )
    parser.add_argument(
        "--voice",
        "-v",
        default=DEFAULT_VOICE,
        help=f"音色（默认: {DEFAULT_VOICE} 晓晓女声）",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="列出常用中文音色后退出",
    )
    args = parser.parse_args()

    if args.list_voices:
        voices = [
            ("zh-CN-XiaoxiaoNeural", "女", "晓晓（默认，自然温暖）"),
            ("zh-CN-XiaoyiNeural", "女", "晓伊（活泼）"),
            ("zh-CN-YunxiNeural", "男", "云希（最常用男声）"),
            ("zh-CN-YunyangNeural", "男", "云扬（新闻播音）"),
            ("zh-CN-YunjianNeural", "男", "云健（沉稳）"),
            ("zh-CN-liaoning-XiaobeiNeural", "女", "晓贝（东北话）"),
            ("zh-CN-shaanxi-XiaoniNeural", "女", "晓妮（陕西话）"),
        ]
        print("常用中文音色：\n")
        print(f"{'Voice ID':<35} {'性别':<6} 说明")
        print("-" * 65)
        for vid, gender, desc in voices:
            print(f"{vid:<35} {gender:<6} {desc}")
        return

    # 读取语音稿 JSON
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"❌ 找不到语音稿文件：{script_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ 语音稿 JSON 格式错误：{e}", file=sys.stderr)
        sys.exit(1)

    items = data.get("items")
    if not items or not isinstance(items, list):
        print("❌ 语音稿缺少 items 数组，或 items 为空", file=sys.stderr)
        sys.exit(1)

    # JSON 里的 voice 优先级低于命令行（只有命令行未显式指定时才用 JSON 的）
    voice = args.voice
    if voice == DEFAULT_VOICE and data.get("voice"):
        voice = data["voice"]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"语音稿  : {script_path}")
    print(f"音色    : {voice}")
    print(f"输出目录: {out_dir}")
    print(f"待合成  : {len(items)} 段（每段产出 mp3 + 字幕 JSON）")
    print(f"⚠️   依赖联网（调用微软 Azure TTS 服务）")
    print("=" * 60)

    ok = asyncio.run(synthesize_all(items, voice, out_dir))

    print("=" * 60)
    print(f"完成：{ok}/{len(items)} 段成功 → {out_dir}/")
    if ok < len(items):
        sys.exit(1)


if __name__ == "__main__":
    main()
