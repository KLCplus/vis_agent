# 数据处理中间证据

全部文件由 `python scripts/build_evidence.py` 从官方原始 JSON 和当前标准化输出重建。

| 文件 | 内容 |
|---|---|
| [01_archive_inventory.csv](01_archive_inventory.csv) | 压缩包内每个文件及大小 |
| [02_message_field_audit.csv](02_message_field_audit.csv) | 字段缺失 null 空数组分别统计 |
| [03_round_windows.csv](03_round_windows.csv) | 全部23轮真实时间和分析时长 |
| [04_recipient_mapping.csv](04_recipient_mapping.csv) | 原始接收人到实际 Agent 的映射 |
| [05_reply_reference_audit.csv](05_reply_reference_audit.csv) | 全部912条回复引用分类 |
| [06_before_after_examples.json](06_before_after_examples.json) | 四条真实消息的原始与处理后对照 |
| [07_normalized_table_inventory.csv](07_normalized_table_inventory.csv) | 八张处理表的规模与路径 |
| [08_filter_subsets.csv](08_filter_subsets.csv) | 保留与各分析子集计数 |
| [09_rule_statistics.csv](09_rule_statistics.csv) | 候选规则数及支持消息数 |
| [10_agent_behavior.csv](10_agent_behavior.csv) | 各 Agent 内外部行为统计 |
| [11_key_evidence_records.json](11_key_evidence_records.json) | 五条关键时间节点的完整原文与来源 |
| [12_verification_runs.json](12_verification_runs.json) | 实际运行的验证命令 退出码和原样输出 |
| [report_manifest.json](report_manifest.json) | Word 的图表来源与章节清单 |
| [verification.json](verification.json) | 中间证据与原数据交叉核验结果 |
| [document_qa.json](document_qa.json) | 本次 Word 渲染逐页检查记录及文件校验值（重新生成后需复查） |
| [summary.json](summary.json) | 报告引用的汇总统计 |

preview_*.json 保留每张处理表的前三条记录。时间为官方模拟时间，不添加时区。关键词子集与异常支持子集可重叠。
原始数据仍在 data/raw 并被 Git 忽略；这里只提交少量有指针的实例与统计结果。
