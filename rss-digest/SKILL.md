---
name: rss-digest
description: |
  读取 RSS 信息源，筛选指定时间范围内的文章，抓取页面正文，
  通过 AI 模型生成中文摘要和标题翻译。支持多个信息源、多种输出格式。
  使用场景：
  - 每日信息摘要生成
  - 技术博客/新闻追踪
  - 多源信息聚合阅读
  - 生成中文信息简报
---

# RSS Digest - 信息源摘要生成

读取 RSS 信息源，自动抓取文章正文，通过 AI 模型生成中文摘要。

## 功能特性

- **多源聚合**：支持同时抓取多个 RSS/Atom 信息源
- **时间过滤**：只处理指定时间范围内的文章
- **智能提取**：使用 Mozilla Readability 算法提取正文（与 Firefox Reader View 相同）
- **AI 摘要**：通过 OpenAI 兼容 API 生成不少于 120 字的中文摘要
- **标题翻译**：非中文标题自动保留原文并翻译
- **双格式输出**：支持 Markdown 和 JSON 格式
- **YAML 配置**：通过配置文件管理多个信息源
- **降级策略**：页面抓取失败时使用 RSS 描述替代

## 使用方法

### 前提条件

需要 Node.js >= 18 和一个 AI API Key（OpenAI 或兼容 API）。

首次使用先安装依赖：

```bash
cd rss-digest && npm install
```

### 基本使用

```bash
# 使用 YAML 配置文件
node rss-digest/scripts/digest.js --config rss-digest/sources.yaml

# 直接指定 RSS 源
node rss-digest/scripts/digest.js --sources "https://hnrss.org/newest" --hours 24

# 输出为 JSON 格式
node rss-digest/scripts/digest.js --config sources.yaml --format json

# 保存到文件
node rss-digest/scripts/digest.js --config sources.yaml --output ./digest.md
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config <path>` | YAML 配置文件路径 | 无 |
| `-s, --sources <urls>` | RSS 源 URL，逗号分隔 | 无 |
| `--hours <n>` | 抓取最近 N 小时的文章 | `24` |
| `-f, --format <type>` | 输出格式：`markdown` / `json` | `markdown` |
| `-o, --output <path>` | 输出文件路径 | stdout |
| `-m, --model <name>` | AI 模型名称 | `gpt-4o-mini` |
| `--concurrency <n>` | 并发抓取数 | `3` |
| `--api-key <key>` | AI API Key | 无 |
| `--base-url <url>` | AI API 端点 | 无 |

### API Key 配置

API Key 的优先级为：命令行参数 > 环境变量 > 配置文件。

**方式一：环境变量（推荐）**

```bash
export OPENAI_API_KEY="sk-your-api-key"
# 自定义端点（可选）
export OPENAI_BASE_URL="https://your-api-endpoint/v1"
```

**方式二：配置文件**

在 `sources.yaml` 的 `ai` 段配置：

```yaml
ai:
  apiKey: sk-your-api-key
  baseUrl: https://api.openai.com/v1
```

**方式三：命令行参数**

```bash
node rss-digest/scripts/digest.js --config sources.yaml --api-key sk-xxx
```

### YAML 配置文件格式

参考 `sources.example.yaml`：

```yaml
sources:
  - name: "Hacker News"
    url: "https://hnrss.org/newest"
    type: rss
  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
    type: rss

ai:
  model: gpt-4o-mini
  # apiKey: sk-xxx        # 推荐使用环境变量

settings:
  hours: 24
  concurrency: 3
  format: markdown
  timeout: 30000
  fetchStrategy: auto
```

## 在 OpenClaw 中安装

### 方式一：通过 Git 地址安装（推荐）

```bash
# 全局安装（所有 agent 可用）
cd ~/.openclaw/skills/
git clone https://github.com/<your-username>/rss-digest.git
cd rss-digest && npm install

# 或工作空间安装（仅当前项目可用）
cd <your-workspace>/skills/
git clone https://github.com/<your-username>/rss-digest.git
cd rss-digest && npm install
```

安装后验证：

```bash
openclaw skills list  # 应显示 rss-digest
```

### 方式二：在 OpenClaw 聊天中粘贴链接

直接在 OpenClaw 对话中粘贴 GitHub 仓库地址：

```
https://github.com/<your-username>/rss-digest
```

OpenClaw Assistant 会自动引导完成安装。

### 在 OpenClaw 中使用

安装后可以通过 slash command 调用：

```
/rss-digest --config ~/sources.yaml --hours 24
/rss-digest --config ~/sources.yaml --format json --output ~/digest.json
```

或用自然语言：

```
帮我读取 ~/sources.yaml 中的 RSS 源，生成最近 48 小时的信息摘要
```

## 输出示例

### Markdown 输出

每篇文章包含：
- **标题**：非中文标题保留原文并附中文翻译
- **原始地址**：文章链接
- **发布时间**
- **中文摘要**：不少于 120 字

### JSON 输出

结构化数据，包含 `sources` 数组，每个源包含 `articles` 数组，每篇文章包含 `originalTitle`、`processedTitle`、`link`、`pubDate`、`summary` 等字段。

## 页面抓取降级策略

默认使用内置方式（axios + Readability）抓取页面。当在 OpenClaw 中运行时，如果文章标记了 `fetchSuccess: false`，可以指引 Agent 使用 Agent Browser 或 web_fetch 对这些页面进行二次抓取。

配置文件中通过 `fetchStrategy` 控制：
- `auto`（默认）：先用内置方式，失败后标记
- `builtin`：仅用内置方式
- `agent-browser`：全部由 Agent Browser 处理
