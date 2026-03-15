---
name: apple-image-to-jpg
version: 1.0.0
description: |
  将 Apple 设备的 HEIC 图片批量转换为 JPG 格式，并自动优化文件大小。
  适用于以下场景：
  - 需要将 iPhone/iPad 拍摄的 HEIC 图片转为通用的 JPG 格式
  - 批量转换目录中的所有 HEIC 文件
  - 需要将图片压缩到 1.5MB 以下（用于网页或邮件分享）
  - 转换后可选择删除原始 HEIC 文件
---

# Apple HEIC 图片转 JPG

将 Apple 设备的 HEIC 格式图片批量转换为 JPG 格式，自动进行大小优化。

## 快速开始

```bash
# 转换目录中所有 HEIC 文件
python3 apple-image-to-jpg/scripts/heic_to_jpg.py /path/to/heic/files

# 指定输出目录
python3 apple-image-to-jpg/scripts/heic_to_jpg.py /path/to/heic/files -o /output/dir

# 转换后删除原始文件
python3 apple-image-to-jpg/scripts/heic_to_jpg.py /path/to/heic/files -d
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `directory` | 包含 HEIC 文件的目录路径（必填） |
| `-o, --output` | 输出目录（默认：`<directory>/jpg_output`） |
| `-d, --delete` | 转换成功后删除原始 HEIC 文件 |

## 依赖安装

```bash
pip3 install pillow pillow-heif
```

## 功能特性

- **批量转换**：自动扫描并转换目录下所有 `.HEIC` 和 `.heic` 文件
- **大小优化**：自动调整质量确保输出文件不超过 1.5MB
- **智能缩放**：当质量调整无法满足大小要求时，自动缩放图片
- **安全删除**：可选在转换成功后删除原始文件
- **自定义输出**：支持指定输出目录

## 使用示例

### 基础转换

```bash
# 转换 ~/Photos 目录下的所有 HEIC 文件
python3 apple-image-to-jpg/scripts/heic_to_jpg.py ~/Photos
# 输出到 ~/Photos/jpg_output/
```

### 指定输出目录

```bash
python3 apple-image-to-jpg/scripts/heic_to_jpg.py ~/Photos -o ~/Desktop/converted
```

### 转换并清理原文件

```bash
python3 apple-image-to-jpg/scripts/heic_to_jpg.py ~/Photos -d
```

## 适用场景

- 需要将 Apple 设备照片分享到不支持 HEIC 格式的平台
- 为网页或邮件准备图片（自动压缩到 1.5MB 以下）
- 批量处理大量 HEIC 照片
- 释放存储空间（使用 `-d` 参数删除原文件）
