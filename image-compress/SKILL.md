---
name: image-compress
version: 1.0.0
description: |
  批量压缩图片文件大小，支持指定单个图片或图片目录，并按目标大小处理超限图片。
  压缩结果默认统一写入输入位置下的 compressed 目录，原始图片不会被修改。
  适用于以下场景：
  - 将图片压缩到指定大小（如 1.5M、500K）
  - 批量处理目录中的 JPG、PNG、WebP、GIF、TIFF 和 BMP 图片
  - 只处理大于目标大小的图片，小于或等于目标大小的图片跳过
---

# 图片批量压缩

使用 Pillow 压缩图片。输入可以是单个图片文件，也可以是图片目录；默认输出到：

- 单个文件：`<图片所在目录>/compressed/`
- 图片目录：`<图片目录>/compressed/`

原始图片不会被覆盖。只有文件大小**大于**目标大小的图片才会处理。

## 快速开始

```bash
# 首次使用时安装 Pillow（在仓库根目录执行）
python3 -m venv image-compress/.venv
image-compress/.venv/bin/pip install pillow

# 将单个图片压缩到 1.5M 以下
image-compress/.venv/bin/python3 image-compress/scripts/image_compress.py /path/to/photo.jpg -s 1.5M

# 批量压缩目录中的图片
image-compress/.venv/bin/python3 image-compress/scripts/image_compress.py /path/to/photos -s 1.5M

# 指定输出目录
image-compress/.venv/bin/python3 image-compress/scripts/image_compress.py /path/to/photos -s 500K -o /path/to/compressed

# 递归处理目录中的图片，并在 compressed 下保留相对目录结构
image-compress/.venv/bin/python3 image-compress/scripts/image_compress.py /path/to/photos -r -s 2M
```

如果已经有安装了 Pillow 的 Python 环境，也可以直接替换上面的
`image-compress/.venv/bin/python3`。

```bash
image-compress/.venv/bin/python3 -m pip show pillow
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `path` | 单个图片文件或图片目录（必填） |
| `-s, --max-size` | 目标最大文件大小，如 `500K`、`1.5M`、`2MB`（默认：`1.5M`） |
| `-o, --output` | 输出目录（默认：`<输入图片所在目录>/compressed`） |
| `-r, --recursive` | 递归扫描目录；输出目录中保留相对目录结构 |

支持的图片格式：JPG/JPEG、PNG、WebP、GIF、TIFF/TIF 和 BMP。扩展名不区分大小写。

## 行为说明

- 大小判断使用二进制单位：`1M = 1024 × 1024` 字节。
- 文件大小小于或等于目标值时跳过，不会复制到输出目录。
- JPEG 和 WebP 会优先降低质量，仍然超限时再按比例缩小尺寸。
- PNG、GIF、TIFF 和 BMP 会进行格式自身的优化，并在必要时缩小尺寸。
- 如果图片无法压缩到目标大小，但生成结果比原图更小，仍会保存结果并报告“目标未达到”。
- 如果压缩结果没有比原图更小，则不生成输出文件。
- 压缩失败的文件不会中断其他文件处理，命令最后会汇总结果。

## 输出示例

```text
Output directory: /path/to/photos/compressed
Found 3 image(s)
Compressed: large.jpg (3.20MB -> 1.42MB, 55.6%)
Skipped: small.png (800KB <= 1.50MB)
Compressed: huge.png (4.10MB -> 1.48MB, 36.1%)
Summary: 2 compressed, 1 skipped, 0 failed
```
