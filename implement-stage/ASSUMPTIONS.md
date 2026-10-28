# Assumption Ledger
ASK mode: never

| ID | 请求未确定项 | 采用定义 | Class | Source |
|---|---|---|---|---|
| A001 | 无时区的模拟时间 | 保留官方 naive ISO 时间，不转换为用户时区 | semantic | default |
| A002 | 广播 ALL 的含义 | 不生成虚构 ALL 节点，不扩展为已阅读；只保留已列名接收人与实际回复边 | semantic | default |
| A003 | 风险评分 | 可解释规则分值 0–100，仅候选优先级；关键词本身不证明泄露 | semantic | default |
| A004 | 单位时间速率 | 消息数/轮次起点至下轮起点小时数，末轮至最后消息至少1分钟；保留窗口时长 | semantic | default |
| A005 | 角色命名差异 | 使用真实 agent_id，保留原标签；不自动套用说明文档 social_manager_agent | semantic | default |
| A006 | 服务接口 | /api/dashboard 提供统一文件快照，前端本地过滤；/api/messages 查询与详情，缺文件返回503 | interface | default |
| A007 | 过滤策略 | 原始记录不删除；标准化只跳过缺失ID/不可解析时间记录并报告；同ID完全相同去重，冲突报错 | semantic | default |
| A008 | 传播证据 | 回复关系是推断线索；内容/状态/环境分别标注；不由关键词生成确证传播边 | semantic | default |
| A009 | 公共渠道 | official_post、personal_post、anonymous_post 为公开，其他未知渠道单列 | semantic | default |
| A010 | 基线异常 | 仅与同Agent过去轮次单位时长速率比较，至少3个历史轮次 | semantic | default |
| A011 | 实际回复字段有未来ID及@文本 | @文本保留为无效引用；未来ID的记录边标记 temporal_valid=false，仅审计，不进入默认网络或传播线索 | semantic | default |
| A012 | 解禁与同意可能不同步 | 从已完成的 formally lifted 语句取正式标记；此前公开只称早于正式标记，额外查阅双方同意，不能认定违规 | semantic | default |
| A013 | 主题与敏感实体 | 主题正则含 merger/acquisition/embargo；实体正则含 HarborCrest/CivicLoom/ResidentEdge；最早关键词出现只表示线索 | semantic | default |
