/* Smoke checks for the simplified four-chart page, using official local data. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
  const page = await browser.newPage({viewport: {width: 1536, height: 1100}, deviceScaleFactor: 1});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const checks = [];
  await page.goto('http://127.0.0.1:5173');
  await page.getByRole('heading', {name: 'Agent × 时间行为矩阵'}).waitFor();
  assert.equal(await page.locator('.panel').count(), 4);
  assert.equal(await page.locator('canvas').count(), 4);
  assert.equal(await page.locator('nav, .kpis, .filters, .evidence-layout, footer').count(), 0);
  checks.push('only four chart panels and brief descriptions remain');
  const data = await (await page.request.get('http://127.0.0.1:8000/api/dashboard')).json();
  const chartTotals = await page.evaluate(async () => {
    const ec = await import(performance.getEntriesByType('resource').find(resource => resource.name.includes('/echarts.js?')).name);
    const option = id => ec.getInstanceByDom(document.querySelector(`#${id} [role=img]`)).getOption();
    return {
      messages: option('behavior').series[0].data.reduce((sum, row) => sum + row[2], 0),
      channels: option('channels').series[0].data.reduce((sum, row) => sum + row.value, 0),
      agents: option('network').series[0].data.map(node => node.id),
      timeline: option('timeline').series[0].data.length,
    };
  });
  assert.equal(chartTotals.messages, data.messages.length);
  assert.equal(chartTotals.channels, data.messages.length);
  assert.deepEqual(chartTotals.agents.sort(), data.agents.map(agent => agent.agent_id).sort());
  assert.equal(chartTotals.timeline, data.messages.length + data.events.length + data.candidates.length);
  checks.push('four charts use the official message, agent and event records');
  await page.getByLabel('热力图指标').selectOption('external_count');
  await page.getByText('按轮次比较各 Agent 的外部发布，颜色越深表示数量越多。').waitFor();
  await page.getByLabel('热力图指标').selectOption('candidate_count');
  await page.getByText('按轮次比较各 Agent 的异常候选，颜色越深表示数量越多。').waitFor();
  await page.getByLabel('热力图指标').selectOption('message_count');
  checks.push('heatmap metrics still switch');
  await page.getByLabel('关系类型').selectOption('reply');
  await page.getByLabel('关系类型').selectOption('recipient');
  await page.getByLabel('关系类型').selectOption('all');
  checks.push('network relation types still switch');
  await page.screenshot({path: 'reports/figures/08_dashboard.png', fullPage: true});
  await page.screenshot({path: 'reports/figures/08_dashboard_overview.png', fullPage: false});
  await page.setViewportSize({width: 768, height: 1024});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  await page.screenshot({path: 'reports/figures/10_tablet.png', fullPage: true});
  checks.push('narrow layout has no horizontal overflow');
  assert.deepEqual(errors, []);
  fs.writeFileSync('reports/browser_validation.json', JSON.stringify({checks, page_errors: errors}, null, 2));
  await browser.close();
  console.log(JSON.stringify({passed: checks.length, checks}, null, 2));
})().catch(error => { console.error(error); process.exit(1); });
