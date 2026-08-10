---
name: image-watermark
version: 1.0.0
description: |
  递归扫描指定目录中的照片，根据照片比例和横竖方向自动选择 watermark 目录中的 PNG 模板，
  将水印模板按照片宽度等比缩放并与照片底边对齐，输出到 processed 目录。
  支持 JPG/JPEG、PNG、WebP，以及可选的输出文件大小上限。
---

# 图片批量添加水印

递归处理指定目录中的所有 JPG/JPEG、PNG 和 WebP 图片。脚本根据图片方向和比例选择水印模板：

| 图片比例 | 横版模板 | 竖版模板 |
|----------|----------|----------|
| 4:3 | `4-3-h.png` | `4-3-v.png` |
| 16:9 | `16-9-h.png` | `16-9-v.png` |

只有比例完全符合 4:3 或 16:9 时才使用对应模板；其他比例横版默认使用
`16-9-h.png`，竖版默认使用 `4-3-v.png`。

模板会按照片宽度等比缩放，底边与照片底边对齐，原始照片不会被修改。

## 快速开始

```bash
# 首次使用时安装 Pillow（在仓库根目录执行）
python3 -m venv image-watermark/.venv
image-watermark/.venv/bin/pip install pillow

# 使用输入目录下的 watermark/，输出到输入目录下的 processed/
image-watermark/.venv/bin/python3 \
  image-watermark/scripts/image_watermark.py /path/to/photos

# 指定水印模板目录和输出目录
image-watermark/.venv/bin/python3 \
  image-watermark/scripts/image_watermark.py /path/to/photos \
  -w /path/to/watermark -o /path/to/processed

# 限制输出图片最大为 10M
image-watermark/.venv/bin/python3 \
  image-watermark/scripts/image_watermark.py /path/to/photos -s 10M
```

如果已经有安装了 Pillow 的 Python 环境，可以直接替换上面的
`image-watermark/.venv/bin/python3`。

## 目录示例

```text
photos/
├── watermark/
│   ├── 4-3-h.png
│   ├── 4-3-v.png
│   ├── 16-9-h.png
│   └── 16-9-v.png
├── vacation/
│   └── beach.jpg
├── portrait.png
└── ...
```

执行：

```bash
image-watermark/.venv/bin/python3 \
  image-watermark/scripts/image_watermark.py photos
```

输出：

```text
photos/processed/
├── vacation/
│   └── beach.jpg
└── portrait.png
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `directory` | 要递归处理的照片目录（必填） |
| `-w, --watermark-dir` | 水印模板目录（默认：`<directory>/watermark`） |
| `-o, --output` | 输出目录（默认：`<directory>/processed`） |
| `-s, --max-size` | 可选的输出文件最大大小，如 `10M`、`500K` |

大小单位使用二进制单位：`1M = 1024 × 1024` 字节。

## 输出大小控制

不指定 `-s` 时，使用高质量参数输出。

指定 `-s` 后，脚本会在添加水印后：

1. 对 JPG/JPEG 和 WebP 逐步降低质量；
2. 如果仍然超出限制，再按比例缩小图片尺寸；
3. 对 PNG 主要通过等比缩小尺寸来控制大小；
4. 如果无法压缩到目标大小，仍保存能够生成的最小结果，并标记
   `target not reached`。

## 注意事项

- 水印模板必须是 PNG，并且包含透明通道才能实现透明水印效果。
- 水印目录至少应包含实际会被使用的模板文件。
- `watermark/` 和 `processed/` 目录中的图片不会被重复扫描处理。
- 输出文件保留原始文件名和扩展名；如果输出文件已存在，会被覆盖。
- 处理失败的图片不会中断其他图片，命令最后会输出失败数量。
