import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';

/**
 * 配置加载器
 * 优先级：命令行参数 > 环境变量 > YAML 配置文件 > 默认值
 */

const DEFAULTS = {
  hours: 24,
  concurrency: 3,
  format: 'markdown',
  timeout: 30000,
  fetchStrategy: 'auto',
  model: 'gpt-4o-mini',
  baseUrl: 'https://api.openai.com/v1',
};

/**
 * 从 YAML 文件加载配置
 */
function loadYamlConfig(configPath) {
  if (!configPath) return {};

  const resolved = path.resolve(configPath);
  if (!fs.existsSync(resolved)) {
    throw new Error(`配置文件不存在：${resolved}`);
  }

  const content = fs.readFileSync(resolved, 'utf-8');
  return yaml.load(content) || {};
}

/**
 * 从环境变量读取 AI 配置
 */
function loadEnvConfig() {
  const env = {};

  if (process.env.OPENAI_API_KEY) {
    env.apiKey = process.env.OPENAI_API_KEY;
  }
  if (process.env.OPENAI_BASE_URL) {
    env.baseUrl = process.env.OPENAI_BASE_URL;
  }
  if (process.env.AI_MODEL) {
    env.model = process.env.AI_MODEL;
  }

  return env;
}

/**
 * 解析 --sources 参数中的逗号分隔 URL
 */
function parseSources(sourcesStr) {
  if (!sourcesStr) return [];

  return sourcesStr.split(',').map((url, index) => ({
    name: `RSS 源 ${index + 1}`,
    url: url.trim(),
    type: 'rss',
  }));
}

/**
 * 合并所有配置源，生成最终配置
 *
 * @param {object} cliOptions - 命令行参数（来自 commander）
 * @returns {object} 合并后的完整配置
 */
export function loadConfig(cliOptions = {}) {
  // 1. 加载 YAML 配置
  const yamlConfig = loadYamlConfig(cliOptions.config);

  // 2. 加载环境变量
  const envConfig = loadEnvConfig();

  // 3. 合并信息源
  let sources = [];
  if (cliOptions.sources) {
    // 命令行指定的 sources 优先
    sources = parseSources(cliOptions.sources);
  } else if (yamlConfig.sources && yamlConfig.sources.length > 0) {
    sources = yamlConfig.sources;
  }

  if (sources.length === 0) {
    throw new Error('未指定信息源。请通过 --config 或 --sources 参数提供 RSS 源。');
  }

  // 4. 合并 AI 配置（优先级：CLI > 环境变量 > YAML > 默认）
  const yamlAi = yamlConfig.ai || {};
  const aiConfig = {
    model: cliOptions.model || envConfig.model || yamlAi.model || DEFAULTS.model,
    apiKey: cliOptions.apiKey || envConfig.apiKey || yamlAi.apiKey,
    baseUrl: cliOptions.baseUrl || envConfig.baseUrl || yamlAi.baseUrl || DEFAULTS.baseUrl,
  };

  if (!aiConfig.apiKey) {
    throw new Error(
      '未找到 AI API Key。请通过以下方式之一提供：\n' +
      '  1. 环境变量：export OPENAI_API_KEY="sk-xxx"\n' +
      '  2. 配置文件：ai.apiKey 字段\n' +
      '  3. 命令行：--api-key sk-xxx'
    );
  }

  // 5. 合并通用设置
  const yamlSettings = yamlConfig.settings || {};
  const settings = {
    hours: parseInt(cliOptions.hours) || yamlSettings.hours || DEFAULTS.hours,
    concurrency: parseInt(cliOptions.concurrency) || yamlSettings.concurrency || DEFAULTS.concurrency,
    format: cliOptions.format || yamlSettings.format || DEFAULTS.format,
    timeout: yamlSettings.timeout || DEFAULTS.timeout,
    fetchStrategy: yamlSettings.fetchStrategy || DEFAULTS.fetchStrategy,
  };

  // 6. 输出路径
  const output = cliOptions.output || null;

  return { sources, ai: aiConfig, settings, output };
}
