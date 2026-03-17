#!/usr/bin/env node

/**
 * RSS Digest - CLI 入口
 * 读取 RSS 信息源，生成 AI 摘要
 */

import { Command } from 'commander';
import fs from 'fs';
import path from 'path';
import { loadConfig } from '../src/configLoader.js';
import { parseFeeds } from '../src/feedParser.js';
import { filterByTime } from '../src/timeFilter.js';
import { fetchPages } from '../src/pageFetcher.js';
import { summarizeArticles } from '../src/summarizer.js';
import { formatOutput } from '../src/formatter.js';

const program = new Command();

program
  .name('rss-digest')
  .description('读取 RSS 信息源，通过 AI 生成中文摘要')
  .version('1.0.0')
  .option('-c, --config <path>', 'YAML 配置文件路径')
  .option('-s, --sources <urls>', 'RSS 源 URL，逗号分隔（与 --config 二选一）')
  .option('--hours <n>', '抓取最近 N 小时的文章', '24')
  .option('-f, --format <type>', '输出格式：markdown / json', 'markdown')
  .option('-o, --output <path>', '输出文件路径（默认输出到终端）')
  .option('-m, --model <name>', 'AI 模型名称')
  .option('--concurrency <n>', '并发抓取数', '3')
  .option('--api-key <key>', 'AI API Key（覆盖环境变量和配置文件）')
  .option('--base-url <url>', 'AI API 端点')
  .option('--test', '测试模式，仅处理前 3 篇文章的 AI 摘要')
  .action(async (options) => {
    const startTime = Date.now();

    try {
      // 1. 加载配置
      console.log('');
      console.log('╔══════════════════════════════════════╗');
      console.log('║        📰 RSS Digest v1.0.0          ║');
      console.log('╚══════════════════════════════════════╝');
      console.log('');

      const config = loadConfig(options);

      console.log(`📋 信息源：${config.sources.length} 个`);
      console.log(`⏰ 时间范围：最近 ${config.settings.hours} 小时`);
      console.log(`🤖 AI 模型：${config.ai.model}`);
      console.log(`📄 输出格式：${config.settings.format}`);
      console.log('');

      // 2. 抓取 RSS
      const feedResults = await parseFeeds(config.sources, config.settings.concurrency);
      console.log('');

      // 3. 时间过滤
      const filtered = filterByTime(feedResults, config.settings.hours);
      console.log('');

      // 测试模式：只保留前 5 篇文章
      if (options.test) {
        const TEST_ARTICLE_LIMIT = 5;
        let kept = 0;
        for (const feed of filtered) {
          const canTake = Math.max(0, TEST_ARTICLE_LIMIT - kept);
          if (feed.items.length > canTake) {
            feed.items = feed.items.slice(0, canTake);
          }
          kept += feed.items.length;
        }
        console.log(`🧪 测试模式：仅保留 ${kept} 篇文章`);
        console.log('');
      }

      // 检查是否有文章
      const totalItems = filtered.reduce((sum, f) => sum + f.items.length, 0);
      if (totalItems === 0) {
        console.log('ℹ️  在指定时间范围内没有找到任何文章。');
        console.log('   提示：可以尝试增大 --hours 参数。');
        process.exit(0);
      }

      // 4. 抓取页面正文
      const withContent = await fetchPages(filtered, {
        concurrency: config.settings.concurrency,
        timeout: config.settings.timeout,
      });
      console.log('');

      // 5. AI 生成摘要
      const withSummary = await summarizeArticles(
        withContent,
        config.ai,
        config.settings.concurrency,
        options.test ? 3 : 0
      );
      console.log('');

      // 6. 格式化输出
      const output = formatOutput(withSummary, config.settings.format, config.settings.hours);

      // 7. 输出结果
      if (config.output) {
        const outputPath = path.resolve(config.output);
        const outputDir = path.dirname(outputPath);
        if (!fs.existsSync(outputDir)) {
          fs.mkdirSync(outputDir, { recursive: true });
        }
        fs.writeFileSync(outputPath, output, 'utf-8');
        console.log(`💾 结果已保存到：${outputPath}`);
      } else {
        console.log('════════════════ 输出结果 ════════════════');
        console.log('');
        console.log(output);
      }

      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log('');
      console.log(`⏱️  总耗时：${elapsed} 秒`);
      console.log('');
    } catch (error) {
      console.error('');
      console.error(`❌ 错误：${error.message}`);
      console.error('');

      if (error.message.includes('API Key')) {
        console.error('💡 提示：设置环境变量 export OPENAI_API_KEY="sk-xxx"');
      }
      if (error.message.includes('信息源')) {
        console.error('💡 提示：使用 --config sources.yaml 或 --sources "url1,url2"');
      }

      process.exit(1);
    }
  });

program.parse();
