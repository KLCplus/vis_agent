"""Additional classroom figures derived from retained intermediate evidence."""
import json
import math
import textwrap
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
import numpy as np
from build_evidence import build, ROOT, EVIDENCE

FIG = ROOT / 'reports/figures/evidence'
COLORS = ['#6257a4', '#2e9c8a', '#508bb2', '#c28c44', '#b56e99', '#73977d', '#9c83ba']


def main():
    data, summary = build(); FIG.mkdir(parents=True, exist_ok=True)
    names = {font.name for font in font_manager.fontManager.ttflist}
    font = next((name for name in ['Arial Unicode MS', 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei'] if name in names), 'DejaVu Sans')
    plt.rcParams.update({'font.family': font, 'axes.unicode_minus': False, 'font.size': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
    manifest = []
    def save(figure, name, title, totals):
        figure.savefig(FIG / (name + '.png'), dpi=220, bbox_inches='tight')
        plt.close(figure)
        manifest.append({'file': str((FIG / (name + '.png')).relative_to(ROOT)), 'title': title, 'totals': totals})
    import csv
    def rows(name):
        with (EVIDENCE / name).open(encoding='utf-8-sig') as stream: return list(csv.DictReader(stream))
    inventory = rows('01_archive_inventory.csv')
    values = [int(row['bytes']) for row in inventory if row['category'] == '语义文件'] + [sum(int(row['bytes']) for row in inventory if row['category'] == '系统元数据')]
    labels = ['MC1 原始 JSON', '数据说明 Markdown', '作答表 HTML', 'macOS 元数据合计']
    # Match labels to the ZIP's actual entry order without assuming the documentation order.
    semantics = [row for row in inventory if row['category'] == '语义文件']
    labels = [('MC1 原始 JSON' if row['name'].endswith('.json') else '数据说明 Markdown' if row['name'].endswith('.md') else '作答表 HTML') for row in semantics] + ['macOS 元数据合计']
    fig, ax = plt.subplots(figsize=(10.8, 4.2)); bars = ax.barh(labels, values, color=COLORS[:4]); ax.bar_label(bars, labels=[f'{n:,} B' for n in values], padding=5)
    ax.set_xscale('log'); ax.set_xlim(1000, max(values) * 3); ax.invert_yaxis(); ax.set_xlabel('文件大小 字节 对数刻度'); ax.set_title('解压文件的大小对比'); fig.tight_layout(); save(fig, '11_archive', '解压文件的大小对比', dict(zip(labels, values)))
    fig, ax = plt.subplots(figsize=(12.5, 4.9)); ax.axis('off'); ax.set(xlim=(0,12.5), ylim=(0,5))
    boxes = [(0.1,1.5,2.2,2,'rounds\n'+str(len(data['rounds']))+' 个轮次'), (3,3.2,3.5,1.2,'environment_context\n事件与市场上下文'),
             (3,1.65,3.5,1.2,'communications\n'+str(len(data['messages']))+' 条消息'), (3,.1,3.5,1.2,'participants\n'+str(len(data['participants']))+' 条轮次参与记录'),
             (7.3,3.2,4.9,1.2,'message_id / agent_id / timestamp\nchannel / recipients / responding_to'),
             (7.3,1.65,4.9,1.2,'content\n消息正文'), (7.3,.1,4.9,1.2,'internal_state\nreacting / rationalizing / deliberating')]
    for x,y,w,h,t in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.03',facecolor='#f0eff7',edgecolor=COLORS[0]));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=11)
    for y in [3.8,2.25,.7]:ax.annotate('',xy=(3,y),xytext=(2.3,2.5),arrowprops={'arrowstyle':'->','color':'#8493a4'})
    for y in [3.8,2.25,.7]:ax.annotate('',xy=(7.3,y),xytext=(6.5,2.25),arrowprops={'arrowstyle':'->','color':'#8493a4'})
    ax.set_title('实际 JSON 的层次结构'); fig.tight_layout(); save(fig,'12_schema','实际 JSON 的层次结构',{'rounds':len(data['rounds']),'messages':len(data['messages']),'participants':len(data['participants'])})
    windows = rows('03_round_windows.csv'); gaps = [float(row['next_start_gap_hours']) for row in windows[:-1]]
    fig, ax = plt.subplots(figsize=(12,4.7));bars=ax.bar(range(1,len(gaps)+1),gaps,color=[COLORS[0] if value==1 else COLORS[1] if value==24 else COLORS[3] for value in gaps]);ax.bar_label(bars,fmt='%g',fontsize=9,padding=3);ax.set_xticks(range(1,len(gaps)+1));ax.set_xlabel('当前轮次序号 与下一轮起点比较');ax.set_ylabel('小时');ax.set_ylim(0,max(gaps)*1.15);ax.set_title('相邻轮次起点的实际时间间隔');fig.tight_layout();save(fig,'13_round_gaps','相邻轮次起点的实际时间间隔',{'gaps':gaps,'counts':summary['nonterminal_gap_counts']})
    fields = summary['fields']; indices=np.arange(len(fields));fig,ax=plt.subplots(figsize=(12,4.8))
    for j,(key,title) in enumerate([('missing','字段不存在'),('null','值为 null'),('empty_list','空数组')]):
        ax.bar(indices+(j-1)*.25,[row[key] for row in fields],width=.25,label=title,color=COLORS[j])
    ax.set_xticks(indices,[row['field'] for row in fields],rotation=35,ha='right');ax.set_ylabel('消息条数');ax.set_title('缺字段 null 与空数组分别统计');ax.legend(frameon=False);fig.tight_layout();save(fig,'14_field_quality','缺字段 null 与空数组分别统计',{row['field']:{key:row[key] for key in ['missing','null','empty_list']} for row in fields})
    order=['时间有效引用','未来引用','非消息ID引用','空引用'];values=[summary['reply_counts'].get(key,0) for key in order]
    fig,ax=plt.subplots(figsize=(10.6,4.5));bars=ax.bar(order,values,color=[COLORS[1],COLORS[3],COLORS[4],COLORS[2]]);ax.bar_label(bars,padding=4);ax.set_ylim(0,max(values)*1.18);ax.set_ylabel('消息条数');ax.set_title('回复字段的四种检查结果');fig.tight_layout();save(fig,'15_reply_quality','回复字段的四种检查结果',dict(zip(order,values)))
    tables=summary['table_inventory'];fig,ax=plt.subplots(figsize=(11,5));bars=ax.barh([row['table'] for row in tables],[row['rows'] for row in tables],color=COLORS[0]);ax.bar_label(bars,padding=5);ax.set_xlim(0,max(row['rows'] for row in tables)*1.14);ax.invert_yaxis();ax.set_xlabel('记录条数 不同表的统计单元不同');ax.set_title('八张标准化数据表的记录规模');fig.tight_layout();save(fig,'16_tables','八张标准化数据表的记录规模',{row['table']:row['rows'] for row in tables})
    for number,name,title,counts in [(17,'internal_states','内部状态的类型分布',summary['internal_state_types']),(18,'events','环境上下文的事件类型分布',summary['environment_event_types'])]:
        fig,ax=plt.subplots(figsize=(10.5,4.2));pairs=sorted(counts.items(),key=lambda pair:pair[1],reverse=True);bars=ax.barh([pair[0] for pair in pairs],[pair[1] for pair in pairs],color=COLORS[:len(pairs)]);ax.bar_label(bars,padding=4);ax.set_xlim(0,max(counts.values())*1.18);ax.invert_yaxis();ax.set_xlabel('非空记录条数');ax.set_title(title);fig.tight_layout();save(fig,f'{number}_{name}',title,counts)
    agents=data['agents'];fig,ax=plt.subplots(figsize=(11.5,4.8));x=np.arange(len(agents));internal=[agent['internal_count'] for agent in agents];public=[agent['external_count'] for agent in agents]
    ax.bar(x,internal,color=COLORS[0],label='内部消息');ax.bar(x,public,bottom=internal,color=COLORS[1],label='公开渠道消息')
    for i,agent in enumerate(agents):ax.text(i,agent['message_count']+4,str(agent['message_count']),ha='center',fontsize=10)
    ax.set_xticks(x,[agent['label'].replace('-Agent','') for agent in agents],rotation=18,ha='right');ax.set_ylim(0,max(agent['message_count'] for agent in agents)*1.14);ax.set_ylabel('消息条数');ax.set_title('各 Agent 内部沟通与公开发布的对比');ax.legend(frameon=False);fig.tight_layout();save(fig,'19_agent_scope','各 Agent 内部沟通与公开发布的对比',{agent['agent_id']:{'internal':agent['internal_count'],'public':agent['external_count']} for agent in agents})
    rule_names={'rate_surge':'轮次消息速率跃升','decision_during_unavailability':'人员不可用时的主题决策','named_public_topic':'公开实体主题线索','named_public_before_formal_lift':'早于正式解禁的实体公开','new_public_channel':'首次使用公开渠道'}
    stats=summary['rule_stats'];fig,ax=plt.subplots(figsize=(11,4.6));bars=ax.barh([rule_names[row['rule']] for row in stats],[row['candidates'] for row in stats],color=COLORS[:len(stats)]);ax.bar_label(bars,padding=5);ax.set_xlim(0,max(row['candidates'] for row in stats)*1.18);ax.invert_yaxis();ax.set_xlabel('候选次数 一条消息可命中多个规则');ax.set_title('可解释规则生成的异常候选');fig.tight_layout();save(fig,'20_rules','可解释规则生成的异常候选',{row['rule']:row['candidates'] for row in stats})
    volumes=[int(row['messages']) for row in windows];rates=[int(row['messages'])/float(row['analysis_window_hours']) for row in windows]
    fig,axes=plt.subplots(2,1,figsize=(12,6.2),sharex=True)
    axes[0].bar(range(1,len(windows)+1),volumes,color=COLORS[0]);axes[0].set_ylabel('每轮消息数');axes[0].set_title('相同的消息量与不同的时间窗口')
    axes[1].bar(range(1,len(windows)+1),rates,color=COLORS[1]);axes[1].set_ylabel('样本消息数 除以窗口小时');axes[1].set_xticks(range(1,len(windows)+1));axes[1].set_xlabel('轮次序号 末轮窗口为起点到最后消息');fig.tight_layout();save(fig,'21_volume_rate','相同的消息量与不同的时间窗口',{'volumes':volumes,'rates':rates})
    markers=json.loads((EVIDENCE/'11_key_evidence_records.json').read_text());fig,ax=plt.subplots(figsize=(13.3,3.5));ax.axis('off');ax.set(xlim=(0,13.3),ylim=(0,3.5))
    for i,record in enumerate(markers):
        x=.08+i*2.65;ax.add_patch(FancyBboxPatch((x,.8),2.35,1.8,boxstyle='round,pad=.04',facecolor='#f1f0f7',edgecolor=COLORS[0]));text=record['kind']+'\n'+record['timestamp'][5:].replace('T',' ')+'\n'+record['agent_id'].replace('_agent','')+'\n'+record['message_id'];ax.text(x+1.175,1.7,text,ha='center',va='center',fontsize=9)
        if i<len(markers)-1:ax.annotate('',xy=(x+2.61,1.7),xytext=(x+2.37,1.7),arrowprops={'arrowstyle':'->','color':'#8291a1'})
    ax.set_title('HarborCrest 关键记录的时间顺序');ax.text(6.65,.25,'连线只表示记录先后  口头同意是消息中的声称  不据此判定合法性或因果',ha='center',fontsize=10,color='#576578');fig.tight_layout();save(fig,'22_key_records','HarborCrest 关键记录的时间顺序',{'message_ids':[record['message_id'] for record in markers]})
    example=json.loads((EVIDENCE/'06_before_after_examples.json').read_text())[1]
    fig,ax=plt.subplots(figsize=(11.5,3.6));ax.axis('off');cells=[[edge['source'],edge['target'],edge['relation']] for edge in example['generated_edges']]
    table=ax.table(cellText=cells,colLabels=['source 发送者','target 接收人','relation 关系类型'],loc='center',cellLoc='left',colWidths=[.3,.4,.25]);table.auto_set_font_size(False);table.set_fontsize(11);table.scale(1,2.4)
    for (row,col),cell in table.get_celld().items():cell.set_edgecolor('#d9d9d9');cell.set_facecolor('#e9edf5' if row==0 else '#f9fafc')
    ax.set_title('一条消息展开为三条指定接收人关系');fig.tight_layout();save(fig,'23_edge_example','一条消息展开为三条指定接收人关系',{'message_id':example['message_id'],'edge_count':len(cells),'targets':[edge['target'] for edge in example['generated_edges']]})
    examples=json.loads((EVIDENCE/'06_before_after_examples.json').read_text());selected=[record['normalized_record'] for record in examples]
    fig,ax=plt.subplots(figsize=(13,4));ax.axis('off');cells=[[record['message_id'],record['timestamp'][5:].replace('T','\n'),record['agent_id'],record['channel'].replace('_','\n'),',\n'.join(record['recipients']) or ('ALL 广播' if record['broadcast'] else '空接收人')] for record in selected]
    table=ax.table(cellText=cells,colLabels=['message_id','timestamp','agent_id','channel','规范化接收人'],cellLoc='left',loc='center',colWidths=[.23,.16,.17,.18,.26]);table.auto_set_font_size(False);table.set_fontsize(10);table.scale(1,3.2)
    for (row,col),cell in table.get_celld().items():cell.set_edgecolor('#d9d9d9');cell.set_facecolor('#e9edf5' if row==0 else '#f9fafc')
    ax.set_title('实际标准化消息的节选');fig.tight_layout();save(fig,'24_message_preview','实际标准化消息的节选',{'message_ids':[record['message_id'] for record in selected]})
    (FIG/'manifest.json').write_text(json.dumps({'source':'reports/evidence/summary.json','font':font,'figures':manifest},ensure_ascii=False,indent=2))
    print('Generated',len(manifest),'additional intermediate-evidence figures')

if __name__=='__main__':main()
