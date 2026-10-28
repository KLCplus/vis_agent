# Build Note
| Rung | Feature | Acceptance command | Tier | Status |
|---|---|---|---|---|
| F0 | 原始文件到可读画像入口 | python scripts/inspect_data.py | MUST | pending |
| F1 | 标准化与规则分析 | python -m pytest tests | MUST | pending |
| F2 | API与前端视图 | pnpm --dir frontend build | MUST | pending |
| F3 | 图表文档与完整验收 | python scripts/verify_artifacts.py | MUST | pending |
| F4 | 假设审阅与修复 | python -m pytest tests | MUST | pending |

## Run record
- 环境：空远端仓库已克隆；系统 Node/npm 不可用，采用 Codex bundled Node/pnpm 与 Python 3.12 venv。
- 官方 API 403，raw.githubusercontent.com 官方 ZIP 下载成功。
## Deferred
- 经过人工确认的因果传播关系、受控统计阈值校准、团队姓名学号。
## Blockers
- 无。
