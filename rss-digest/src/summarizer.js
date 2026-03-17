import OpenAI from 'openai';

/**
 * AI 摘要生成模块
 * 调用 OpenAI 兼容 API，为每篇文章生成中文摘要和标题翻译
 */

// 内容最大字符数（约 4000 tokens），超出部分截断
const MAX_CONTENT_LENGTH = 8000;

// API 调用间隔（毫秒），防止触发频率限制
const API_CALL_INTERVAL = 6000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const SYSTEM_PROMPT = `你是一位专业的信息摘要助手。你需要根据提供的文章内容完成两个任务：

任务1 - 标题处理：
- 检测标题语言
- 如果标题是中文，直接保留原标题
- 如果标题不是中文，保留原标题并翻译，格式为：「原标题 | 中文翻译」

任务2 - 内容摘要：
- 用中文撰写摘要，字数不少于120字
- 涵盖文章的核心观点、关键数据和重要结论
- 语言简洁专业，信息密度高
- 如果原文是非中文内容，一定要翻译成中文摘要

请严格以如下 JSON 格式输出，不要包含 markdown 代码块标记或其他任何内容：
{
  "processedTitle": "处理后的标题",
  "summary": "中文摘要内容（不少于120字）"
}`;

/**
 * 生成单篇文章的摘要
 *
 * @param {object} client - OpenAI 客户端
 * @param {string} model - 模型名称
 * @param {object} article - 文章对象 { title, fullContent }
 * @param {number} retries - 重试次数
 * @returns {object} { processedTitle, summary, success, error? }
 */
async function summarizeSingle(client, model, article, retries = 2) {
  let content = article.fullContent || article.description || '';

  if (!content || content.trim().length < 20) {
    return {
      processedTitle: article.title,
      summary: '（文章内容过短，无法生成摘要）',
      success: false,
      error: '内容不足',
    };
  }

  // 截断过长内容，避免超出 token 限制
  if (content.length > MAX_CONTENT_LENGTH) {
    content = content.substring(0, MAX_CONTENT_LENGTH) + '\n\n[内容已截断，请基于以上部分生成摘要]';
  }

  const userMessage = `文章标题：${article.title}\n\n文章内容：\n${content}`;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await client.chat.completions.create({
        model,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userMessage },
        ],
        temperature: 0.3,
        max_tokens: 1000,
        response_format: { type: 'json_object' },
      });

      const text = response.choices[0]?.message?.content?.trim();
      if (!text) {
        throw new Error('AI 返回内容为空');
      }

      // 解析 JSON 响应
      const result = JSON.parse(text);

      if (!result.processedTitle || !result.summary) {
        throw new Error('AI 返回格式不完整');
      }

      // 检查摘要字数
      if (result.summary.length < 100 && attempt < retries) {
        // 摘要太短，重试
        continue;
      }

      return {
        processedTitle: result.processedTitle,
        summary: result.summary,
        success: true,
      };
    } catch (error) {
      if (attempt === retries) {
        return {
          processedTitle: article.title,
          summary: '（摘要生成失败）',
          success: false,
          error: error.message,
        };
      }
      // 等一下再重试
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
}

/**
 * 批量生成所有文章的摘要
 *
 * @param {Array<object>} feedResults - 附带正文的信息源结果
 * @param {object} aiConfig - AI 配置 { model, apiKey, baseUrl }
 * @param {number} concurrency - 并发数
 * @param {number} maxArticles - 最大处理文章数，0 为不限制
 * @returns {Array<object>} 附带摘要的信息源结果
 */
export async function summarizeArticles(feedResults, aiConfig, concurrency = 3, maxArticles = 0) {
  const client = new OpenAI({
    apiKey: aiConfig.apiKey,
    baseURL: aiConfig.baseUrl,
  });

  // 统计总数
  let totalArticles = 0;
  feedResults.forEach((feed) => {
    totalArticles += feed.items.length;
  });

  if (totalArticles === 0) {
    console.log('🤖 没有需要生成摘要的文章');
    return feedResults;
  }

  // 如果是测试模式，限制处理数量
  const isTestMode = maxArticles > 0;
  const articlesToProcess = isTestMode ? Math.min(totalArticles, maxArticles) : totalArticles;

  const estimatedMinutes = Math.ceil((articlesToProcess * API_CALL_INTERVAL / 1000) / 60);
  console.log(`🤖 开始生成 ${articlesToProcess} 篇文章的 AI 摘要（模型: ${aiConfig.model}）`);
  if (isTestMode) {
    console.log(`   🧪 测试模式：仅处理前 ${maxArticles} 篇`);
  }
  console.log(`   每次调用间隔 ${API_CALL_INTERVAL / 1000} 秒，预计需要 ${estimatedMinutes} 分钟`);

  let completed = 0;
  let succeeded = 0;
  let failed = 0;

  // 逐篇处理，每次调用间隔 API_CALL_INTERVAL，防止触发频率限制
  const summarizedResults = [];
  let processedCount = 0;

  for (const feed of feedResults) {
    const summarizedItems = [];
    for (const item of feed.items) {
      // 测试模式下达到上限，跳过剩余文章
      if (isTestMode && processedCount >= maxArticles) {
        summarizedItems.push({
          ...item,
          processedTitle: item.title,
          summary: '（测试模式，已跳过）',
          summarySuccess: false,
          summaryError: 'skipped in test mode',
        });
        continue;
      }

      // 第一篇不等待，后续每篇等待间隔
      if (completed > 0) {
        await sleep(API_CALL_INTERVAL);
      }

      const result = await summarizeSingle(client, aiConfig.model, item);
      completed++;
      processedCount++;

      if (result.success) {
        succeeded++;
      } else {
        failed++;
      }

      process.stdout.write(`\r   进度：${completed}/${totalArticles}  ✅${succeeded}  ❌${failed}`);

      summarizedItems.push({
        ...item,
        processedTitle: result.processedTitle,
        summary: result.summary,
        summarySuccess: result.success,
        summaryError: result.error || null,
      });
    }
    summarizedResults.push({ ...feed, items: summarizedItems });
  }

  console.log(`\n✅ AI 摘要生成完成：成功 ${succeeded}，失败 ${failed}`);

  return summarizedResults;
}
