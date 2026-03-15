import axios from 'axios';
import { JSDOM } from 'jsdom';
import { Readability } from '@mozilla/readability';
import pLimit from 'p-limit';

/**
 * 页面正文提取模块
 * 使用 axios 抓取页面，@mozilla/readability 智能提取正文
 * 失败时降级到 RSS 自带的 description
 */

/**
 * 抓取并提取单个页面的正文内容
 *
 * @param {string} url - 页面 URL
 * @param {number} timeout - 超时时间（毫秒）
 * @returns {object} { content, success, error? }
 */
async function fetchSinglePage(url, timeout = 30000) {
  if (!url) {
    return { content: '', success: false, error: 'URL 为空' };
  }

  try {
    const response = await axios.get(url, {
      timeout,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      },
      maxRedirects: 5,
      // 限制响应体大小（5MB）
      maxContentLength: 5 * 1024 * 1024,
    });

    const html = response.data;

    if (typeof html !== 'string' || html.trim().length === 0) {
      return { content: '', success: false, error: '页面内容为空' };
    }

    // 使用 Readability 提取正文
    const dom = new JSDOM(html, { url });
    const reader = new Readability(dom.window.document);
    const article = reader.parse();

    if (article && article.textContent && article.textContent.trim().length > 0) {
      // 清理正文：去除多余空白行
      const content = article.textContent
        .replace(/\n{3,}/g, '\n\n')
        .trim();

      return { content, success: true };
    }

    return { content: '', success: false, error: 'Readability 未能提取到正文' };
  } catch (error) {
    const errMsg = error.code === 'ECONNABORTED'
      ? `请求超时（${timeout}ms）`
      : error.response
        ? `HTTP ${error.response.status}`
        : error.message;

    return { content: '', success: false, error: errMsg };
  }
}

/**
 * 批量抓取文章页面正文
 * 如果抓取失败，降级使用 RSS 自带的 description
 *
 * @param {Array<object>} feedResults - 过滤后的信息源结果
 * @param {object} options - { concurrency, timeout }
 * @returns {Array<object>} 附带正文的信息源结果
 */
export async function fetchPages(feedResults, options = {}) {
  const { concurrency = 3, timeout = 30000 } = options;
  const limit = pLimit(concurrency);

  // 统计需要抓取的总数
  let totalUrls = 0;
  feedResults.forEach((feed) => {
    totalUrls += feed.items.length;
  });

  if (totalUrls === 0) {
    console.log('📄 没有需要抓取的文章页面');
    return feedResults;
  }

  console.log(`📄 开始抓取 ${totalUrls} 个文章页面（并发数: ${concurrency}）...`);

  let completed = 0;
  let succeeded = 0;
  let failed = 0;

  const enrichedResults = await Promise.all(
    feedResults.map(async (feed) => {
      const enrichedItems = await Promise.all(
        feed.items.map((item) =>
          limit(async () => {
            const result = await fetchSinglePage(item.link, timeout);
            completed++;

            if (result.success) {
              succeeded++;
              // 截取前 8000 字符（避免 token 超限）
              const content = result.content.length > 8000
                ? result.content.substring(0, 8000) + '...(内容截断)'
                : result.content;

              process.stdout.write(`\r   进度：${completed}/${totalUrls}  ✅${succeeded}  ❌${failed}`);

              return { ...item, fullContent: content, fetchSuccess: true };
            } else {
              failed++;
              process.stdout.write(`\r   进度：${completed}/${totalUrls}  ✅${succeeded}  ❌${failed}`);

              // 降级：使用 RSS 自带的 description
              return {
                ...item,
                fullContent: item.description || '',
                fetchSuccess: false,
                fetchError: result.error,
              };
            }
          })
        )
      );

      return { ...feed, items: enrichedItems };
    })
  );

  console.log(`\n✅ 页面抓取完成：成功 ${succeeded}，失败 ${failed}`);

  return enrichedResults;
}
