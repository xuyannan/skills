import dayjs from 'dayjs';

/**
 * 结果格式化模块
 * 将处理结果汇总为 Markdown 或 JSON 格式
 */

/**
 * 格式化为 Markdown
 */
function toMarkdown(feedResults, hours) {
  const now = dayjs().format('YYYY-MM-DD HH:mm');
  const totalArticles = feedResults.reduce((sum, f) => sum + f.items.length, 0);
  const totalSources = feedResults.filter((f) => f.items.length > 0).length;

  const lines = [];

  lines.push(`# 📰 信息摘要 - ${now}`);
  lines.push('');
  lines.push(`> ⏰ 时间范围：最近 ${hours} 小时 | 📊 共 ${totalArticles} 篇文章 | 📡 来自 ${totalSources} 个信息源`);
  lines.push('');

  for (const feed of feedResults) {
    if (feed.items.length === 0) continue;

    lines.push('---');
    lines.push('');
    lines.push(`## ${feed.sourceName}`);
    lines.push('');

    feed.items.forEach((item, index) => {
      const title = item.processedTitle || item.title;
      const pubDate = item.pubDate
        ? dayjs(item.pubDate).format('YYYY-MM-DD HH:mm')
        : '未知时间';

      lines.push(`### ${index + 1}. ${title}`);
      lines.push(`- 🔗 原文：[${item.link}](${item.link})`);
      lines.push(`- 📅 发布时间：${pubDate}`);

      if (!item.fetchSuccess && item.fetchError) {
        lines.push(`- ⚠️ 页面抓取：${item.fetchError}（使用 RSS 描述替代）`);
      }

      lines.push('');
      lines.push(`> ${item.summary || '（无摘要）'}`);
      lines.push('');
    });
  }

  // 无文章的信息源
  const emptySources = feedResults.filter((f) => f.items.length === 0 && !f.error);
  const failedSources = feedResults.filter((f) => f.error);

  if (emptySources.length > 0 || failedSources.length > 0) {
    lines.push('---');
    lines.push('');
    lines.push('## 📋 其他');
    lines.push('');

    if (emptySources.length > 0) {
      lines.push(`以下信息源在指定时间范围内没有新文章：`);
      emptySources.forEach((f) => lines.push(`- ${f.sourceName}`));
      lines.push('');
    }

    if (failedSources.length > 0) {
      lines.push(`以下信息源抓取失败：`);
      failedSources.forEach((f) => lines.push(`- ${f.sourceName}: ${f.error}`));
      lines.push('');
    }
  }

  return lines.join('\n');
}

/**
 * 格式化为 JSON
 */
function toJSON(feedResults, hours) {
  const totalArticles = feedResults.reduce((sum, f) => sum + f.items.length, 0);

  const output = {
    generatedAt: dayjs().toISOString(),
    timeRange: `${hours}h`,
    totalArticles,
    sources: feedResults.map((feed) => ({
      name: feed.sourceName,
      url: feed.source,
      error: feed.error || null,
      articles: feed.items.map((item) => ({
        originalTitle: item.title,
        processedTitle: item.processedTitle || item.title,
        link: item.link,
        pubDate: item.pubDate ? dayjs(item.pubDate).toISOString() : null,
        summary: item.summary || '',
        fetchSuccess: item.fetchSuccess ?? true,
        summarySuccess: item.summarySuccess ?? true,
      })),
    })),
  };

  return JSON.stringify(output, null, 2);
}

/**
 * 格式化输出结果
 *
 * @param {Array<object>} feedResults - 完整处理后的结果
 * @param {string} format - 输出格式：'markdown' | 'json'
 * @param {number} hours - 时间范围（用于显示）
 * @returns {string} 格式化后的字符串
 */
export function formatOutput(feedResults, format = 'markdown', hours = 24) {
  if (format === 'json') {
    return toJSON(feedResults, hours);
  }

  return toMarkdown(feedResults, hours);
}
