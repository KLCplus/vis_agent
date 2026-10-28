# Build Note

| Rung | Feature | Acceptance command | Tier | Status |
|---|---|---|---|---|
| F0 | 原始文件到画像入口 | python scripts/inspect_data.py | MUST | passed |
| F1 | 标准化、规则和 API | python -m pytest -q | MUST | passed 14 |
| F2 | React ECharts 四类联动视图 | pnpm --dir frontend build | MUST | passed |
| F3 | 图表文档和来源验收 | python scripts/verify_artifacts.py | MUST | passed |
| F4 | 两轮假设审阅与修复 | python -m pytest -q | MUST | passed deterministic; review provisional |

## Run record

- 空远端已克隆，base commit none；F0/F1 本地提交 ba9cbee。
- 系统 Python 3.9 和缺失 PATH Node/npm：采用 Codex bundled Python 3.12 venv、Node、pnpm；所有依赖隔离或通过 runtime 使用。
- 官方 GitHub API 403，直接官方 raw ZIP 成功。已阅读官方 MC1 任务、包内说明与 Answer Sheet、参考 README；未复制参考代码或素材。
- F0 画像入口成功，23轮次912消息；schema以真实 JSON 为准。
- F1 初始10测试通过，后续修复新增4项回归检查；最终14项全部通过。
- F2 TypeScript 与 Vite 生产构建成功；本地 API 和 UI 联调成功；真实浏览器17项验收通过。
- F3 七张数据图表、六章材料、证据笔记与 Word 已生成。912条来源 JSON Pointer、八张表与图表总数交叉校验通过。
- Word 9页。先修复 fontconfig 不能读取系统 CJK 问题，再用临时子集字体映射避免 LibreOffice 的字体子集渲染缺字；最终每页 PNG 已视觉检查。字体及QA中间文件不提交。
- 两轮 gpt-6-astra/xhigh fresh-context 假设审阅，同模型家族，仅 provisional。原始回复在 REVIEW_ROUND_1/2.json，修复记录在 SILENT_ASSUMPTION_SWEEP.json。
- 补全 acquisition 词形；总体速率统一分母；整轮候选通过支持消息集合与UI/API/图表关联；人员不可用代理指标与发送者筛选明确标注。
- 网络正反向曲线原来重叠，浏览器验收定位后已改不同曲率，现可分别点击。

## Semantic choices

全窗口速率为抽样记录量/时间，不是连续监测事件率。候选整轮聚合，首条仅定位。任何人员不可用是代理信号，不等于监控整体失效。正式解禁前的公开不是自动违规结论。所有传播联系仍为待核验推断。

## Deferred

人工确证因果传播、授权真伪、预期行为标注、规则校准、团队姓名学号、生产部署。未实现 Neo4j、多用户权限、真实泄露概率。

## Non-blocking limitations

- Vite 主脚本约1.38MB（gzip约460KB），有 bundle size 警告；可后续模块化拆分。
- 当前 FastAPI/Starlette TestClient 提示 httpx 适配弃用，测试通过。
- CI 已配置；不能把本地成功等同远端 Actions 已完成。

## Blockers

实现与本地验收无阻塞。GitHub 推送结果在最终报告中给出，不伪报成功。
