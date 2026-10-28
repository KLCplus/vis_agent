"""Generate source-quoted, explicitly qualified HarborCrest evidence notes."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    d=json.loads((ROOT/'data/processed/dashboard.json').read_text());ms=d['messages']
    selected=[]
    # Exact reproducible queries, not manually assigned culprit labels.
    queries=[('早期敏感主题线索',lambda m:m['topic_match']),
             ('首个包含明确交易实体的内部消息',lambda m:m['named_topic'] and m['scope']=='internal'),
             ('内部发现未经授权人员接触的报告',lambda m:'neither intern was briefed' in m['content'].lower()),
             ('声称口头双边同意并下达公开指令',lambda m:'verbal consent confirmed' in m['content'].lower() and 'GO' in m['content']),
             ('首条包含交易实体的直接公开消息',lambda m:m['named_topic'] and m['scope']=='external'),
             ('明确正式解禁记录',lambda m:'embargo formally lifted' in m['content'].lower())]
    for title,predicate in queries:
        matches=sorted((m for m in ms if predicate(m)),key=lambda m:m['timestamp'])
        if matches:selected.append((title,matches[0]))
    lines=['# HarborCrest 事件证据笔记','',
           '本笔记按可重复查询选择证据。时间使用记录时间；正文转述、授权声称和预测不被提升为独立已验证事实。关键词命中只说明记录讨论了主题。完整状态、环境和回复线索见 dashboard.json 与 evidence_chain.json。','']
    first=d['evidence_summary']['first_topic_record']
    lines+=['## 最早线索的限制','',f"主题证据中最早记录在 {first['timestamp']}，类型 {first['kind']}，对应消息 {first.get('message_id','无')}。这是包含战略交易猜测的内部状态，不能称为已掌握真实并购机密。",'']
    for title,m in selected:
        lines += ['## '+title,'',f"{m['timestamp']} · {m['agent_id']} · {m['channel']} · `{m['message_id']}`",'',m['content'],'',f"来源 `{m['source_file']}` → `{m['json_pointer']}`",'']
    topic_agents=sorted({m['agent_id'] for m in ms if m['named_topic']})
    early=[c for c in d['candidates'] if c['type']=='named_public_before_formal_lift']
    lines+=['## 接触与公开行为','',
            '在消息正文中明确提及实体的 Agent 为：'+', '.join(topic_agents)+'。这表示发出了提及实体的消息，不证明收件人实际阅读。',
            f"共有 {len(early)} 条实体公开消息早于正式解禁标记，实际发送者为 "+', '.join(sorted({c['agent_id'] for c in early}))+'。不能仅据命令把 PR-Intern 视为已执行首次完整新闻稿；正文内发布确认与实际 public_post 记录需分别核验。','',
            '## 推断与尚不确定的关系','',
            f"主题消息间有 {len(d['evidence_summary']['topic_reply_relations'])} 条时间有效的回复线索。它们是消息联系推断，均不是确证传播或因果边。",
            '官方任务背景描述 17 时左右发生禁令突破。原始消息还包含 17:19 Legal 声称取得口头同意、17:25 首条直接实体公开记录、18:00 明确正式解禁。系统并列呈现这些记录，不替 Agent 的自我辩护背书，也不将官方背景与记录的授权差异静默消除。',
            '5月29日正文自述误标交易对手 CEO、未给实习生授权却传播时间线、侧边渠道讨论及13时轮次的多人不可用，构成可审阅的领先信号。它们并非单独证明泄露的充分条件。',
            '待人工确定：真实授权权限和口头同意效力、间接实体表达、消息归属语义异常、首次完整官方新闻稿的执行证据、信息究竟由谁转给外部媒体。','']
    (ROOT/'reports/harborcrest_findings.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Wrote reports/harborcrest_findings.md')

if __name__=='__main__':main()
