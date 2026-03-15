import RssParser from 'rss-parser';
import pLimit from 'p-limit';

/**
 * RSS/Atom Feed 解析模块
 * 并发抓取多个信息源，提取文章列表
 */

const parser = new RssParser({
  timeout: 15000,
  headers: {
    'User-Agent': 'RSS-Digest/1.0 (+https://github.com/rss-digest)',
    'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
  },
});

/**
 * 解析单个 RSS/Atom Feed
 *
 * @param {object} source - 信息源配置 { name, url, type }
 * @returns {object} 解析结果 { source, sourceName, items, error? }
 */
async function parseSingleFeed(source) {
  try {
    const feed = await parser.parseURL(source.url);

    const items = (feed.items || []).map((item) => ({
      title: item.title || '无标题',
      link: item.link || item.guid || '',
      pubDate: item.pubDate ? new Date(item.pubDate) : (item.isoDate ? new Date(item.isoDate) : null),
      description: item.contentSnippet || item.content || item.summary || '',
    }));

    return {
      source: source.url,
      sourceName: source.name || feed.title || source.url,
      items,
      error: null,
    };
  } catch (error) {
    console.error(`⚠️  抓取 RSS 失败 [${source.name || source.url}]: ${error.message}`);
    return {
      source: source.url,
      sourceName: source.name || source.url,
      items: [],
      error: error.message,
    };
  }
}

/**
 * 并发解析多个 RSS/Atom Feed
 *
 * @param {Array<object>} sources - 信息源配置列表
 * @param {number} concurrency - 并发数
 * @returns {Array<object>} 所有信息源的解析结果
 */
export async function parseFeeds(sources, concurrency = 3) {
  const limit = pLimit(concurrency);

  console.log(`📡 开始抓取 ${sources.length} 个 RSS 信息源...`);

  const tasks = sources.map((source) =>
    limit(() => parseSingleFeed(source))
  );

  const results = await Promise.all(tasks);

  const totalItems = results.reduce((sum, r) => sum + r.items.length, 0);
  const failedSources = results.filter((r) => r.error);

  console.log(`✅ RSS 抓取完成：${totalItems} 篇文章，${failedSources.length} 个源失败`);

  if (failedSources.length > 0) {
    failedSources.forEach((r) => {
      console.log(`   ❌ ${r.sourceName}: ${r.error}`);
    });
  }

  return results;
}
