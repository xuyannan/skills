import dayjs from 'dayjs';

/**
 * 时间过滤模块
 * 根据指定的小时数过滤文章，只保留时间范围内的条目
 */

/**
 * 过滤单个信息源的文章列表
 *
 * @param {Array<object>} items - 文章列表
 * @param {number} hours - 时间范围（小时）
 * @returns {Array<object>} 过滤后的文章列表
 */
function filterItems(items, hours) {
  const cutoff = dayjs().subtract(hours, 'hour');

  return items.filter((item) => {
    // 如果没有发布时间，默认保留（部分 feed 不提供时间）
    if (!item.pubDate) {
      return true;
    }

    const pubDate = dayjs(item.pubDate);

    // 无效日期也默认保留
    if (!pubDate.isValid()) {
      return true;
    }

    return pubDate.isAfter(cutoff);
  });
}

/**
 * 对所有信息源的文章进行时间过滤
 *
 * @param {Array<object>} feedResults - parseFeeds 的返回结果
 * @param {number} hours - 时间范围（小时）
 * @returns {Array<object>} 过滤后的结果（同结构，items 被过滤）
 */
export function filterByTime(feedResults, hours) {
  console.log(`⏰ 过滤最近 ${hours} 小时内的文章...`);

  let totalBefore = 0;
  let totalAfter = 0;

  const filtered = feedResults.map((feed) => {
    const before = feed.items.length;
    const items = filterItems(feed.items, hours);
    const after = items.length;

    totalBefore += before;
    totalAfter += after;

    return {
      ...feed,
      items,
    };
  });

  console.log(`✅ 时间过滤完成：${totalBefore} → ${totalAfter} 篇文章`);

  return filtered;
}
