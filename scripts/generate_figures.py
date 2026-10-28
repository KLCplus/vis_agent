"""Rebuild seven course figures strictly from dashboard.json and audit totals."""
import json
import textwrap
from collections import Counter
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'reports/figures'
COLORS=['#6559aa','#339c88','#498bb4','#c48d46','#bb6e9b','#6a9578','#9879bd']


def main():
    FIG.mkdir(parents=True,exist_ok=True)
    available={f.name for f in font_manager.fontManager.ttflist}
    chosen=next((n for n in ['Arial Unicode MS','PingFang SC','Noto Sans CJK SC','Microsoft YaHei','SimHei'] if n in available),'DejaVu Sans')
    plt.rcParams.update({'font.family':chosen,'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
    d=json.loads((ROOT/'data/processed/dashboard.json').read_text());ms=d['messages'];agents=d['agents'];rs=d['rounds'];manifest={'font':chosen,'source':'data/processed/dashboard.json','figures':[]}
    def save(fig,name,description,totals):
        fig.savefig(FIG/(name+'.png'),dpi=220,bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');plt.close(fig)
        svg=FIG/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
        manifest['figures'].append({'file':name+'.png','description':description,'totals':totals})
    fig,ax=plt.subplots(figsize=(13,4));ax.set(xlim=(0,13),ylim=(0,4));ax.axis('off')
    names=['官方 MC1 ZIP\n下载与文件清单',f"真实 JSON 画像\n{d['profile']['field_paths']} 字段路径",'标准化与质量审计\n消息、状态、事件、关系','可解释规则分析\n候选与证据分层','FastAPI 与 React\n联动视图和课程材料']
    for i,name in enumerate(names):
        x=.2+i*2.6;ax.add_patch(FancyBboxPatch((x,1.2),2.15,1.3,boxstyle='round,pad=.1',facecolor='#eff0f7',edgecolor=COLORS[0]));ax.text(x+1.075,1.85,name,ha='center',va='center',fontsize=11)
        if i<4:ax.annotate('',xy=(x+2.5,1.85),xytext=(x+2.2,1.85),arrowprops={'arrowstyle':'->','color':COLORS[0]})
    ax.text(6.5,.5,'原始消息 ID 与 JSON Pointer 贯穿每一步；广播、回复与确证传播分别处理。',ha='center',color='#556070')
    ax.set_title('数据处理流程',fontsize=17,pad=16);save(fig,'01_pipeline','数据处理流程',{'messages':len(ms)})
    fig,ax=plt.subplots(figsize=(11,5));names=[a['label'].replace('-Agent','') for a in agents];vals=[a['message_count'] for a in agents]
    bars=ax.barh(names,vals,color=COLORS);ax.bar_label(bars,padding=5);ax.set_xlim(0,max(vals)*1.16);ax.set_xlabel('消息条数');ax.set_title('Agent 消息数量统计');ax.invert_yaxis();fig.tight_layout();save(fig,'02_agent_messages','全样本按实际 sender ID 分组',dict(zip([a['agent_id'] for a in agents],vals)))
    fig,ax=plt.subplots(figsize=(11,5));channels=d['channels'];bars=ax.bar([c['channel'].replace('_','\n') for c in channels],[c['message_count'] for c in channels],color=COLORS[:6]);ax.bar_label(bars,padding=3);ax.set_ylim(0,max(c['message_count'] for c in channels)*1.14);ax.set_title('通信渠道分布');ax.set_ylabel('消息条数');fig.tight_layout();save(fig,'03_channels','原始 channel 分类统计',{c['channel']:c['message_count'] for c in channels})
    fig,ax=plt.subplots(figsize=(13,4.8));times=[datetime.fromisoformat(r['timestamp']) for r in rs];vol=[sum(m['round_index']==r['round_index'] for m in ms) for r in rs]
    ax.vlines(times,0,vol,color=COLORS[0],linewidth=2);ax.scatter(times,vol,color=COLORS[1],s=22,zorder=4);ax.set_title('消息时间分布 按真实轮次起点定位');ax.set_xlabel('模拟时间 无时区标记');ax.set_ylabel('该轮次消息数量');fig.autofmt_xdate();fig.text(.5,.01,'每天与每小时为不同抽样轮次；轮次之间留白不代表无通信。',ha='center',fontsize=10,color='#556070');fig.tight_layout(rect=(0,.04,1,1));save(fig,'04_temporal','真实日期间距的轮次消息计数',{'round_counts':vol,'sum':sum(vol)})
    import numpy as np
    matrix=np.array([[sum(m['agent_id']==a['agent_id'] and m['round_index']==r['round_index'] for m in ms) for r in rs] for a in agents])
    fig,ax=plt.subplots(figsize=(14,5));im=ax.imshow(matrix,aspect='auto',cmap='Purples');ax.set_yticks(range(len(names)),names);ax.set_xticks(range(len(rs)),[r['timestamp'][5:10]+' '+r['timestamp'][11:16] for r in rs],rotation=55,ha='right',fontsize=8);ax.set_title('Agent 行为热力图');fig.colorbar(im,ax=ax,label='消息条数');ax.set_xlabel('轮次顺序 列宽不代表时长 相邻起点间隔 1 至 72 小时');fig.tight_layout();save(fig,'05_heatmap','保留轮次序列与真实标签',{'matrix':matrix.tolist(),'sum':int(matrix.sum())})
    graph=nx.DiGraph();graph.add_nodes_from(a['agent_id'] for a in agents)
    valid=[e for e in d['communication_edges'] if e['temporal_valid'] and e['source']!=e['target']]
    for e in valid:
        u,v=e['source'],e['target'];graph.add_edge(u,v,weight=graph.get_edge_data(u,v,{}).get('weight',0)+1)
    fig,ax=plt.subplots(figsize=(11,7));pos=nx.circular_layout(graph)
    nx.draw_networkx_nodes(graph,pos,node_size=[600+a['message_count']*7 for a in agents],node_color=COLORS,alpha=.9,ax=ax)
    nx.draw_networkx_edges(graph,pos,width=[.5+__import__('math').log1p(e[2]['weight'])/2 for e in graph.edges(data=True)],edge_color='#a5b1bf',alpha=.65,arrows=True,arrowsize=15,connectionstyle='arc3,rad=0.12',node_size=2000,ax=ax)
    nx.draw_networkx_labels(graph,{k:(v[0],v[1]-.18) for k,v in pos.items()},labels={a['agent_id']:a['label'].replace('-Agent','') for a in agents},font_family=chosen,font_size=10,ax=ax);ax.set_title('Agent 通信网络 指定接收人与有效时间回复');ax.axis('off');fig.text(.5,.03,'箭头为发送者 → 接收人或被回复者；剔除未来引用与自环；通信边不等于敏感信息已传播。',ha='center',fontsize=10);fig.tight_layout(rect=(0,.06,1,1));save(fig,'06_network','真实记录边，去除不合时间顺序引用与自环',{'nodes':len(graph),'aggregate_edges':len(graph.edges),'supporting_edge_records':len(valid)})
    fig,ax=plt.subplots(figsize=(11,5));values=[len(ms),d['quality']['clean_message_count'],sum(m['topic_match'] for m in ms),sum(m['scope']=='external' for m in ms),len({mid for c in d['candidates'] for mid in c['supporting_message_ids']})];labels=['原始消息','标准化后 保留','主题关键词子集','公开渠道子集','异常候选关联消息'];bars=ax.barh(labels,values,color=[COLORS[0],COLORS[1],COLORS[2],COLORS[3],COLORS[4]]);ax.bar_label(bars,padding=5);ax.invert_yaxis();ax.set_xlim(0,len(ms)*1.15);ax.set_xlabel('消息条数 子集之间可重叠');ax.set_title('数据过滤前后对比');fig.tight_layout();save(fig,'07_filtering','仅分析视图过滤，不删除有问题的原始消息',dict(zip(labels,values)))
    (FIG/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Generated',len(manifest['figures']),'figures; font:',chosen)

if __name__=='__main__':main()
