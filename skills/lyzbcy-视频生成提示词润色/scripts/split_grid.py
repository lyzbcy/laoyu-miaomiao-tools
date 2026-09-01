#!/usr/bin/env python3
"""网格切分图：把一张 N×M 网格生图切成带切分线与角标的小图（抽帧验证用）。

用法：
  python split_grid.py grid.png --labels "分镜01-镜头2@0:03,分镜01-镜头3@0:07,..."
  python split_grid.py grid.png --rows 2 --cols 2 --labels "镜头1@0:00,镜头2@0:03,镜头3@0:05,镜头4@0:08"
  python split_grid.py grid.png --labels-file labels.txt   # 每行一格，按从左到右、从上到下
  python split_grid.py grid.png --labels ""                # 只切分画线，不打角标

输出（--out 目录，默认 out/）：
  grid_annotated.png   整图 + 红色切分线 + 每格左上角角标（人审就看这张）
  cell_01.png … cell_NN.png   各格单图（细看某格时用）

依赖：pip install pillow
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LINE_COLOR = (255, 0, 0)
DEFAULT_ROWS = DEFAULT_COLS = 4


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("msyh.ttc", "simhei.ttf", "simsun.ttc"):  # Windows 常见中文字体
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_label(draw: ImageDraw.ImageDraw, xy, text: str, font) -> None:
    """在 xy 处画黑底黄字角标，返回 None。"""
    x, y = xy
    tw = draw.textlength(text, font=font)
    band_h = font.size + 12
    draw.rectangle([x + 6, y + 6, x + 6 + tw + 10, y + 6 + band_h], fill=(0, 0, 0))
    draw.text((x + 11, y + 9), text, fill=(255, 255, 0), font=font)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image", help="网格生图路径")
    ap.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="网格行数（默认 4）")
    ap.add_argument("--cols", type=int, default=DEFAULT_COLS, help="网格列数（默认 4）")
    ap.add_argument("--labels", default="",
                    help="逗号分隔的角标，按从左到右、从上到下顺序；如 '分镜01-镜头2@0:03,...'")
    ap.add_argument("--labels-file", default=None, help="每行一个角标的文本文件，与 --labels 二选一")
    ap.add_argument("--out", default="out", help="输出目录（默认 out/）")
    args = ap.parse_args()

    rows, cols = args.rows, args.cols
    if rows < 1 or cols < 1:
        sys.exit("--rows/--cols 必须 ≥ 1")
    total = rows * cols
    if args.labels_file:
        labels = [l.strip() for l in Path(args.labels_file).read_text(encoding="utf-8").splitlines()]
    elif args.labels:
        labels = [l.strip() for l in args.labels.split(",")]
    else:
        labels = []
    if len(labels) > total:
        sys.exit(f"角标数 {len(labels)} 超过 {total} 格")

    img = Image.open(args.image).convert("RGB")
    w, h = img.size
    cw, ch = w // cols, h // rows
    font = load_font(max(14, ch // 18))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    full = img.copy()
    fd = ImageDraw.Draw(full)
    for i in range(1, rows):
        fd.line([(0, i * ch), (w, i * ch)], fill=LINE_COLOR, width=3)
    for j in range(1, cols):
        fd.line([(j * cw, 0), (j * cw, h)], fill=LINE_COLOR, width=3)

    n = 0
    for r in range(rows):
        for c in range(cols):
            box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
            cell = img.crop(box)
            cd = ImageDraw.Draw(cell)
            cd.rectangle([0, 0, cw - 1, ch - 1], outline=LINE_COLOR, width=3)
            label = labels[n] if n < len(labels) else ""
            if label:
                draw_label(cd, (0, 0), label, font)
                draw_label(fd, (box[0], box[1]), label, font)
            cell.save(out / f"cell_{n + 1:02d}.png")
            n += 1

    full.save(out / "grid_annotated.png")
    labeled = sum(1 for l in labels if l)
    print(f"完成：切分 {rows}×{cols}={n} 格（角标 {labeled} 条）→ {out.resolve()}（人审看 grid_annotated.png）")


if __name__ == "__main__":
    main()
