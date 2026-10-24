#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 A-M.png / A-V.png 上叠加兼容补丁标题文字。

默认参数按需求固定：
    文本    Talent Enhancement Compatibility Patch
    字体    Blippo（自动在用户字体目录 / 系统字体目录 / 脚本目录查找）
    字号    16
    颜色    (212, 209, 197)
    位置    横向居中；纵向由每张图的目标值决定
            A-M.png (512x512) -> 448
            A-V.png (500x500) -> 440

用法：
    python add_badge_text.py                 # 输出 A-M_text.png / A-V_text.png
    python add_badge_text.py --inplace       # 直接覆盖原图
    python add_badge_text.py --anchor top    # 纵向锚点改为文字顶部（默认 bottom）
    python add_badge_text.py --target A-M.png:448 --target A-V.png:440
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TEXT = "Talent Enhancement Compatibility Patch"
FONT_SIZE = 24
COLOR = (212, 209, 197)
TARGETS = (("A-M.png", 440), ("A-V.png", 440))


def find_blippo(explicit: str | None) -> Path | None:
    """按优先级查找 Blippo 字体文件。"""
    here = Path(__file__).resolve().parent
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(here / "Blippo Regular.ttf")
    candidates.extend(sorted(here.glob("Blippo*.ttf")))
    fonts_dir = here / "fonts"
    if fonts_dir.is_dir():
        candidates.extend(sorted(fonts_dir.glob("Blippo*.ttf")))

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        user_fonts = Path(local_appdata) / "Microsoft" / "Windows" / "Fonts"
        candidates.extend(sorted(user_fonts.glob("Blippo*.ttf")))

    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates.extend(sorted((windir / "Fonts").glob("Blippo*.ttf")))

    for path in candidates:
        if path.is_file():
            return path
    return None


def parse_color(value: str) -> tuple[int, int, int]:
    parts = [int(p.strip()) for p in value.split(",")]
    if len(parts) != 3 or any(not 0 <= c <= 255 for c in parts):
        raise argparse.ArgumentTypeError("颜色格式应为 R,G,B（0-255）")
    return parts[0], parts[1], parts[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="在 A-M.png / A-V.png 上叠加兼容补丁标题文字。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--text", default=TEXT, help="叠加的文字")
    parser.add_argument("--font", help="Blippo 字体文件路径（默认自动查找）")
    parser.add_argument("--size", type=int, default=FONT_SIZE, help="字号（像素）")
    parser.add_argument("--color", type=parse_color, default=COLOR, help="文字颜色 R,G,B")
    parser.add_argument(
        "--anchor",
        choices=("bottom", "baseline", "top"),
        default="bottom",
        help="纵向锚点：bottom=文字框底部对齐 y；baseline=基线对齐 y；top=文字框顶部对齐 y",
    )
    parser.add_argument("--inplace", action="store_true", help="覆盖原图")
    parser.add_argument(
        "--target",
        action="append",
        metavar="FILE:Y",
        help="自定义目标与纵向位置（可重复），默认 A-M.png:448 与 A-V.png:440",
    )
    parser.add_argument("--outdir", help="输出目录（默认脚本所在目录）")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parent
    outdir = Path(args.outdir).resolve() if args.outdir else root

    targets: list[tuple[str, int]] = []
    if args.target:
        for item in args.target:
            try:
                name, y = item.rsplit(":", 1)
                targets.append((name, int(y)))
            except ValueError:
                print(f"忽略无效的 --target：{item}", file=sys.stderr)
    else:
        targets = list(TARGETS)

    font_path = find_blippo(args.font)
    if font_path is None:
        print(
            "未找到 Blippo 字体。请安装 Blippo，或用 --font 指定 .ttf 路径。",
            file=sys.stderr,
        )
        return 2

    try:
        font = ImageFont.truetype(str(font_path), args.size)
    except OSError as exc:
        print(f"无法加载字体 {font_path}：{exc}", file=sys.stderr)
        return 2

    print(f"字体：{font_path}（{args.size}px）")
    print(f"文本：{args.text!r}")

    for name, y in targets:
        src = root / name
        if not src.is_file():
            print(f"跳过 {name}：文件不存在", file=sys.stderr)
            continue

        with Image.open(src) as opened:
            img = opened.copy()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        draw = ImageDraw.Draw(img)
        fill = (*args.color, 255) if img.mode == "RGBA" else args.color

        if args.anchor == "baseline":
            draw.text((img.width / 2, y), args.text, font=font, fill=fill, anchor="ms")
            box = None
        else:
            left, top, right, bottom = draw.textbbox((0, 0), args.text, font=font)
            width = right - left
            x = (img.width - width) / 2 - left
            y_origin = y - bottom if args.anchor == "bottom" else y - top
            draw.text((x, y_origin), args.text, font=font, fill=fill)
            box = (x, y_origin, x + width, y_origin + (bottom - top))

        dst = src if args.inplace else outdir / f"{src.stem}_text.png"
        img.save(dst, format="PNG")

        detail = f"bbox={tuple(round(v, 1) for v in box)}" if box else "baseline"
        print(f"{name}: {img.width}x{img.height}, y={y}, anchor={args.anchor}, {detail} -> {dst.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
