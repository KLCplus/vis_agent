"""Generate six course chapters and an evidence-grounded assignment draft."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    d=json.loads((ROOT/'data/processed/dashboard.json').read_text());p=d['profile'];q=d['quality'];agents=d['agents'];ms=d['messages'];cs=d['candidates']
    content_count=sum(m['topic_match'] for m in ms);public=sum(m['scope']=='external' for m in ms)
    release=d['evidence_summary']['formal_lift'];first=d['evidence_summary']['first_named_public']
    channels='、'.join(f"{c['channel']} {c['message_count']} 条" for c in d['channels'])
    source='[官方任务说明](https://vast-challenge.github.io/2026/MC1.html)、[官方数据仓库](https://github.com/vast-challenge/2026-data)。参考项目仅阅读 [README](https://github.com/keremilgaz/VAST_Challenge_2026)，未复制其代码、图像或分析结论。'
    docs=[
    ('01_数据下载','数据下载',[
      ('目标','取得可追溯的官方数据，建立可重新执行的获取入口。'),
      ('实际操作','从官方 raw.githubusercontent.com 地址下载 VAST_Challenge_2026_MC1.zip，解压并读取全部语义文件。数据说明与 Answer Sheet HTML 均已检查。macOS 资源叉和 .DS_Store 只计入文件清单。'),
      ('实现方法','运行 python scripts/download_data.py；离线时用 --archive 指向官方 ZIP。下载使用临时文件并验证 ZIP 格式，解压前检查路径不能越出 data/raw。官方 main 分支为下载来源，版本变化后须重新审阅 schema。'),
      ('主要结果',f"ZIP 内有 7 个文件条目（不含目录），其中 3 个语义文件：MC1_final_00.json 987742 字节、mc1 data description.md 5699 字节、Answer Sheet.htm 83347 字节。官方数据共 {p['message_count']} 条消息。当前文件清单和字节数由 data_profile.json 自动生成；本段是此次快照的核对结果。"),
      ('分析结论',source+' 原始数据和 ZIP 均不入 Git，画像、图表与代码可公开审阅。'),
      ('后续改进空间','当前官方入口使用 main；后续在课程报告中登记课程采用的数据版本，并保留离线压缩包。')],['01_pipeline']),
    ('02_数据理解','数据理解',[
      ('目标','确认实际结构与字段语义，区分文档示例和原始记录。'),
      ('实际操作',f"逐轮解析 rounds、communications、participants 和 environment_context；递归枚举 {p['field_paths']} 个字段路径及其类型、出现和空值次数。实际数据为 {p['agent_count']} 个 Agent、{p['round_count']} 个轮次、{p['message_count']} 条消息、{p['internal_state_rows']} 条非空状态流与 {p['event_count']} 条环境事件。"),
      ('实现方法','inspect_data.py 检查所有 JSON 的顶层结构并生成 data_dictionary.csv。消息位于 rounds[].communications，而非文档示例的 agent_outputs。角色以实际 agent_id 为主，保留 role 和 label。social_media_agent、judge_agent 与文档列名不同；接收人 social_manager 仅经真实标签 Social-Manager-Agent 映射。'),
      ('主要结果',f"时间覆盖 {p['start']} 至 {p['end']}，不指定时区。相邻轮次起点间隔为 1、24、72 小时，不能当作等间隔小时。{channels}。实际消息最多的是 {max(agents,key=lambda a:a['message_count'])['label']}。"),
      ('分析结论','Agent 在各轮次内的一分钟时间戳记录，并不保证内部文字引用的时间与记录时间一致。participants.declared_action 是声明行为，不能直接当作已发布消息。市场数据和不可用状态属于轮次环境上下文。'),
      ('后续改进空间','人工检查同一 Agent 连续消息中可能存在的语义归属歧义；暂不按照正文说话方式修改发送者。补充更多外部事件的精确时间标注。')],['02_agent_messages','03_channels']),
    ('03_数据过滤','数据过滤',[
      ('目标','减少分析噪声并保留审计证据，避免把字段不完整等同于无行为。'),
      ('实际操作',f"清洗前后均为 {len(ms)} 条消息；完全重复 ID 删除 {q['exact_id_duplicates_removed']} 条，排除记录 {q['excluded_count']} 条。没有缺失的必需字段。internal_state 为空 {q['null_fields'].get('internal_state',0)} 条，responding_to 为空 {q['null_fields'].get('responding_to',0)} 条；空接收人 {q['empty_recipients']} 条；不同 ID 的相同正文冗余 {q['same_text_repetitions']} 次均保留。"),
      ('实现方法','只在分析视图中过滤时间、Agent、渠道、关键词；CSV 保留原 ID、来源文件和 JSON Pointer。广播 ALL 不展开成阅读事件；空接收人不补猜。回复字段中的 @文本不能解析为消息 ID，按无效引用报告；未来回复边保留 temporal_valid=false，默认网络和传播线索均排除。'),
      ('主要结果',f"无效回复引用 {q['issue_counts'].get('invalid_reply_reference',0)} 条，未来回复引用 {q['issue_counts'].get('future_reply_reference',0)} 条。主题关键词消息 {content_count} 条，公开渠道 {public} 条，异常候选关联消息 {len({mid for c in cs for mid in c['supporting_message_ids']})} 条。子集互有重叠，不是逐层删除。"),
      ('分析结论','关键词只产生审阅入口。网络中的收件人和回复方向分别标记，不能自动解释成敏感信息已传播；未来引用尤其不应构成时间因果链。'),
      ('后续改进空间','加入人工标注的同义表达、否定表达及权限级别，评估关键词筛选的误报和漏报，不盲目扩大正则。')],['07_filtering']),
    ('04_数据处理','数据处理',[
      ('目标','将嵌套原始记录转为可复算的数据表，并产出有来源的统计与候选。'),
      ('实际操作','建立 messages、agents、events、internal_states、communication_edges、participants、rounds、candidates 八张 CSV，输出 API 共用 dashboard.json。画像和统计位于 data/reports。'),
      ('实现方法','总体速率统一采用全语料窗口总时长作分母。整轮速率候选关联该Agent该轮全部支持消息，首条只用于定位；候选在任一支持消息通过筛选时显示。轮次窗口按下轮起点计算，末轮以最后消息时间计算且至少一分钟；速率是样本轮次消息数除以窗口小时数，不能解释成连续监测的真实事件率。通道名 trim/lower，角色通过无歧义 ID/role/label 规范化。重复 ID 内容冲突直接失败，不悄悄覆盖。'),
      ('主要结果',f"共 {len(d['communication_edges'])} 条关系记录，其中时间有效 {sum(e['temporal_valid'] for e in d['communication_edges'])} 条（含自回复）；默认网络进一步隐藏自环。规则产生 {len(cs)} 条候选，涵盖速率跃升、首次公开渠道、实体公开与人员不可用时的主题决策。"),
      ('分析结论',f"首个实体公开消息 {first['message_id']} 在 {first['timestamp']}，发送者 {first['agent_id']}。明确正式解禁记录 {release['message_id']} 在 {release['timestamp']}。早于正式标记的公开不自动证明未经同意；17 时轮次存在 Legal 对双边同意的声称，必须并列阅读。"),
      ('后续改进空间','阈值需要人工标注评估。不同抽样粒度造成的速率变动会触发规则，所以候选需要结合真实时间窗口判断。后续区分首次披露、转述、推测和重复发布。')],['04_temporal']),
    ('05_可视化映射与后续设计','可视化映射与后续设计',[
      ('目标','把数据字段映射到能支持课程问题的视觉编码，并建立可复核的证据浏览流程。'),
      ('实际操作','实现总览 KPI 与渠道图、Agent 时间热力图、通信网络、真实时间事件散点轴、分页记录与证据面板。按时间、角色、渠道、关键词联动；热力图点击定位消息，网络节点查看全样本画像，边查看支持消息，时间轴直接打开原文。'),
      ('实现方法','React TypeScript Vite 与 Apache ECharts；FastAPI 提供只读文件快照。热力图颜色表示消息数、外部发布或候选命中数，横轴为带真实时间标签的轮次序列，等列宽不代表等时长。时间轴使用 time 标度；网络箭头为发送者到收件人/被回复者，金色边仅表示含候选消息。'),
      ('主要结果','证据详情包含消息 ID、角色、时间、渠道、原文、状态、关联环境和 JSON Pointer。证据分为事实记录、有效回复推断以及仍未确定的关系。不能从事件排序推出因果。'),
      ('分析结论','官方任务说明将事件设定为禁令被突破；本原型只能确认记录中的公开行为与正式解禁标记之间的时间差。Agent 关于授权、已公开或无风险的说法是被分析对象，不应作为独立验证的结论。'),
      ('后续改进空间','增加权限层和 Expected behavior 对照，人工标注真实传播关系，显示多个授权/解禁版本之间的争议；验证规则后再做传播路径高亮。')],['05_heatmap','06_network']),
    ('06_项目分工与交付清单','项目分工与交付清单',[
      ('目标','明确课程第一次作业的完成范围、团队责任和待补信息。'),
      ('实际操作','前四步已完成可运行代码与图表；第五步完成首版映射，第六至七步的系统评估与长期迭代仍待课程推进。全部组员姓名、学号、实际负责人均为待填写，不虚构团队贡献。'),
      ('实现方法','建议分工：数据工程负责人［待填写姓名 学号］，规则与证据核验负责人［待填写姓名 学号］，可视分析前端负责人［待填写姓名 学号］，课程材料与测试负责人［待填写姓名 学号］。'),
      ('主要结果','交付代码、自动画像六项文件、八张标准表、七张统计图、页面运行截图、六章说明和 Word 初稿。工程验收包括解析/时间/关系测试、API 响应、TypeScript 检查、生产构建与浏览器交互检查；实际执行结果见 reports/validation.json 和 browser_validation.json。'),
      ('分析结论','第一阶段实现的是可解释、可追溯的探索工具。风险候选分数为课程原型优先级，未经校准，不能用作真实泄露概率或自动问责依据。'),
      ('后续改进空间','待填写学生信息与教师模板；待人工核验关键证据链、误报率、真实传播及预期行为差异。尚无生产部署、数据库迁移、多用户权限或统计模型校准。')],['08_dashboard'])]
    out=ROOT/'docs';out.mkdir(exist_ok=True)
    for filename,title,sections,figs in docs:
        text='# '+title+'\n\n'+'\n\n'.join('## '+h+'\n\n'+body for h,body in sections)
        text+='\n\n## 真实图表\n\n'+'\n\n'.join(f'![{f}](../reports/figures/{f}.png)' for f in figs)+'\n'
        (out/(filename+'.md')).write_text(text,encoding='utf-8')
    return docs

if __name__=='__main__':main()
