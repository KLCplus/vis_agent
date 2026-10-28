# 第一阶段实现规范
目标：官方 MC1 数据的可重复下载、画像、标准化、可解释候选分析，React ECharts 与 FastAPI 联动分析台，以及课程前四步材料。
输入：官方仓库 MC1 ZIP 中的全部语义文件；参考项目只阅读 README。
输出：data/processed/*.csv 与 dashboard.json；data/reports 下画像、字典、质量报告和统计；reports/figures 实测图表；docs 六章与作业 docx。
Base commit: none (empty cloned repository).
验证命令：python -m pytest；pnpm --dir frontend build；python scripts/verify_artifacts.py。
边界：不调用 LLM，不宣称启发式分数为泄露概率，不将广播收件人推定成实际阅读，不推断因果。
