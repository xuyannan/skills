---
name: pdf-compress
version: 1.0.0
description: |
  使用 Ghostscript 压缩 PDF 文件，支持指定目标大小和质量等级。
  适用于以下场景：
  - 需要将 PDF 压缩到指定大小（如 5M、500K）以便邮件发送或上传
  - 批量压缩目录中的所有 PDF 文件
  - 按不同质量等级压缩（screen / ebook / printer / prepress）
  - 需要直接覆盖原文件以节省空间
---

# PDF 文件压缩

使用 Ghostscript 压缩 PDF 文件，支持指定目标文件大小，自动迭代调整参数以达到目标。

## 快速开始

```bash
# 压缩单个 PDF 文件（默认 ebook 质量）
pdf-compress/scripts/pdf_compress.py document.pdf

# 压缩到指定大小
pdf-compress/scripts/pdf_compress.py document.pdf -s 5M

# 压缩目录中所有 PDF
pdf-compress/scripts/pdf_compress.py ./pdfs -s 2M

# 使用最低质量获得最小体积
pdf-compress/scripts/pdf_compress.py document.pdf -q screen
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `path` | PDF 文件路径或包含 PDF 的目录（必填） |
| `-o, --output` | 输出目录（默认：`<path>/compressed_output`） |
| `-s, --max-size` | 目标最大文件大小，如 `500K`、`5M`、`10M` |
| `-q, --quality` | 质量等级：`screen`、`ebook`（默认）、`printer`、`prepress` |
| `--overwrite` | 直接覆盖原文件（⚠️ 请谨慎使用） |

## 质量等级说明

| 等级 | DPI | 说明 |
|------|-----|------|
| `screen` | 72 | 低质量，最小体积，适合屏幕浏览 |
| `ebook` | 150 | 中等质量，适合电子书和一般阅读（默认） |
| `printer` | 300 | 较高质量，适合打印 |
| `prepress` | 300 | 最高质量，适合印前处理 |

## 依赖安装

需要安装 Ghostscript：

```bash
brew install ghostscript
```

脚本为纯 Python 实现，无需额外 pip 依赖。

## 功能特性

- **目标大小压缩**：通过 `-s` 参数指定目标大小，自动迭代降低 DPI 直到满足要求
- **质量等级**：4 种预设质量等级，覆盖从屏幕浏览到印前处理的各种场景
- **批量处理**：支持单文件或整个目录批量压缩
- **原文件覆盖**：`--overwrite` 参数支持直接替换原文件（安全的先写临时文件再替换）
- **智能压缩**：自动去除重复图片、压缩字体、子集化字体
- **压缩报告**：显示每个文件的压缩前后大小和压缩比

## 使用示例

### 压缩到指定大小

```bash
# 压缩到 5MB 以下（用于邮件附件）
pdf-compress/scripts/pdf_compress.py report.pdf -s 5M

# 压缩到 500KB 以下
pdf-compress/scripts/pdf_compress.py report.pdf -s 500K
```

### 批量压缩

```bash
# 压缩目录中所有 PDF，输出到默认目录
pdf-compress/scripts/pdf_compress.py ./documents

# 指定输出目录
pdf-compress/scripts/pdf_compress.py ./documents -o ./compressed
```

### 直接覆盖原文件

```bash
# ⚠️ 会直接替换原始 PDF 文件
pdf-compress/scripts/pdf_compress.py report.pdf -s 2M --overwrite
```

### 选择质量等级

```bash
# 最低质量，最大压缩
pdf-compress/scripts/pdf_compress.py report.pdf -q screen

# 打印质量
pdf-compress/scripts/pdf_compress.py report.pdf -q printer -s 10M
```

## 适用场景

- 邮件附件大小限制（压缩到 5M / 10M 以下）
- 网站/平台上传文件大小限制
- 批量压缩历史 PDF 文档以节省存储空间
- 在线分享 PDF 时减少传输时间
