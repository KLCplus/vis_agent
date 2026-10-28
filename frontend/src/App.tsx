import {useEffect, useMemo, useState} from 'react';
import type {EChartsOption} from 'echarts';
import Chart from './Chart';
import type {Data} from './types';

const colors = ['#a4a0ff', '#4ddbb5', '#62b8f5', '#f6bf69', '#e78fc7', '#8cbea1', '#c4a6f8'];
const channelNames: Record<string, string> = {
  comms_huddle: '团队讨论',
  one_on_one_chat: '一对一',
  side_huddle: '侧边讨论',
  official_post: '官方公开',
  personal_post: '个人公开',
  anonymous_post: '匿名公开',
};
const metricNames: Record<string, string> = {
  message_count: '消息数量',
  external_count: '外部发布',
  candidate_count: '异常候选',
};
const shortTime = (value: string) => `${value.slice(5, 10)} ${value.slice(11, 16)}`;
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]!));
const common = {
  backgroundColor: 'transparent',
  textStyle: {fontFamily: 'system-ui', color: '#9aa8bd'},
  animation: false,
} as const;

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState('');
  const [metric, setMetric] = useState('message_count');
  const [relation, setRelation] = useState('all');

  useEffect(() => {
    fetch('/api/dashboard')
      .then(async response => {
        if (!response.ok) throw new Error(`数据服务返回 ${response.status}`);
        return response.json();
      })
      .then(setData)
      .catch(reason => setError(String(reason)));
  }, []);

  const edges = useMemo(() => data?.communication_edges.filter(edge =>
    edge.temporal_valid && edge.source !== edge.target &&
    (relation === 'all' || edge.relation === relation)
  ) || [], [data, relation]);

  if (error) return <main className="status"><h1>数据暂不可用</h1><p>{error}</p><button onClick={() => location.reload()}>重新加载</button></main>;
  if (!data) return <main className="status">正在加载图表…</main>;

  const label = (id: string) => data.agents.find(agent => agent.agent_id === id)?.label.replace('-Agent', '') || id;
  const heatValues = data.agents.flatMap((agent, agentIndex) =>
    data.rounds.map((round, roundIndex) => {
      const messages = data.messages.filter(message => message.agent_id === agent.agent_id && message.round_index === round.round_index);
      const value = metric === 'candidate_count'
        ? data.candidates.filter(candidate => candidate.agent_id === agent.agent_id && candidate.round_index === round.round_index).length
        : metric === 'external_count'
          ? messages.filter(message => message.scope === 'external').length
          : messages.length;
      return [roundIndex, agentIndex, value];
    })
  );
  const heatOption: EChartsOption = {
    ...common,
    grid: {left: 112, right: 20, top: 24, bottom: 92},
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const [roundIndex, agentIndex, value] = params.value;
        return `${escapeHtml(label(data.agents[agentIndex].agent_id))}<br/>${data.rounds[roundIndex].timestamp.replace('T', ' ')}<br/>${metricNames[metric]}：${value}`;
      },
    },
    xAxis: {
      type: 'category',
      data: data.rounds.map(round => shortTime(round.timestamp)),
      axisLabel: {rotate: 48, fontSize: 10},
      axisLine: {show: false},
      axisTick: {show: false},
    },
    yAxis: {
      type: 'category',
      data: data.agents.map(agent => label(agent.agent_id)),
      axisLabel: {fontSize: 11},
      axisLine: {show: false},
      axisTick: {show: false},
    },
    visualMap: {
      min: 0,
      max: Math.max(1, ...heatValues.map(value => value[2])),
      orient: 'horizontal',
      left: 'center',
      bottom: 5,
      inRange: {color: ['#192332', '#47457d', '#8d82e8', '#d4c6ff']},
      textStyle: {color: '#8e9cb2'},
      itemHeight: 110,
      itemWidth: 9,
    },
    series: [{
      type: 'heatmap',
      data: heatValues,
      itemStyle: {borderColor: '#131e2c', borderWidth: 3, borderRadius: 3},
      emphasis: {itemStyle: {borderColor: '#bcb5ff', borderWidth: 2}},
    }],
  };

  const candidateMessageIds = new Set(data.candidates.flatMap(candidate => candidate.supporting_message_ids));
  const aggregate = new Map<string, {source: string; target: string; value: number; risk: boolean}>();
  for (const edge of edges) {
    const key = `${edge.source}>${edge.target}`;
    const entry = aggregate.get(key) || {source: edge.source, target: edge.target, value: 0, risk: false};
    entry.value++;
    entry.risk ||= candidateMessageIds.has(edge.message_id);
    aggregate.set(key, entry);
  }
  const graphOption: EChartsOption = {
    ...common,
    tooltip: {trigger: 'item'},
    series: [{
      type: 'graph',
      layout: 'circular',
      circular: {rotateLabel: false},
      roam: true,
      draggable: true,
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: 6,
      label: {show: true, position: 'bottom', color: '#c1cad9', fontSize: 11},
      emphasis: {focus: 'adjacency', lineStyle: {width: 4}},
      data: data.agents.map((agent, index) => ({
        id: agent.agent_id,
        name: label(agent.agent_id),
        value: agent.message_count,
        symbolSize: 30 + Math.sqrt(agent.message_count) * 2.2,
        itemStyle: {
          color: colors[index],
          borderColor: agent.candidate_count ? '#f7c27a' : '#243348',
          borderWidth: 2,
        },
      })),
      links: [...aggregate.values()].map(edge => ({
        ...edge,
        lineStyle: {
          color: edge.risk ? '#ba9267' : '#53617d',
          opacity: .45,
          width: Math.min(5, 1 + Math.log1p(edge.value) / 2),
          curveness: edge.source < edge.target ? .06 : .18,
        },
      })),
    }],
  };

  const timelineOption: EChartsOption = {
    ...common,
    grid: {left: 80, right: 24, top: 26, bottom: 44},
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `${escapeHtml(params.data.timestamp.replace('T', ' '))}<br/>${escapeHtml(params.data.content.slice(0, 180))}`,
      extraCssText: 'max-width:360px;white-space:normal;line-height:1.7;',
    },
    xAxis: {type: 'time', axisLabel: {fontSize: 11}, splitLine: {show: false}},
    yAxis: {
      type: 'category',
      data: ['外部事件', '内部消息', '公开消息', '异常候选'],
      axisLabel: {fontSize: 11},
      axisLine: {show: false},
      splitLine: {show: true, lineStyle: {color: '#203044'}},
    },
    series: [{
      type: 'scatter',
      symbolSize: 7,
      data: [
        ...data.events.map(event => ({value: [event.timestamp, 0], timestamp: event.timestamp, content: event.content, itemStyle: {color: '#5c8fb8'}})),
        ...data.messages.map(message => ({value: [message.timestamp, message.scope === 'external' ? 2 : 1], timestamp: message.timestamp, content: message.content, itemStyle: {color: message.scope === 'external' ? '#51d1b0' : '#a19ae9'}})),
        ...data.candidates.map(candidate => ({value: [candidate.timestamp, 3], timestamp: candidate.timestamp, content: candidate.rule, itemStyle: {color: '#f4bf73'}})),
      ],
    }],
  };
  const channelOption: EChartsOption = {
    ...common,
    tooltip: {trigger: 'item', formatter: '{b}：{c} 条（{d}%）'},
    legend: {orient: 'vertical', right: 18, top: 'center', textStyle: {color: '#9aa8bd', fontSize: 12}, itemWidth: 8, itemHeight: 8, itemGap: 16},
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['35%', '50%'],
      label: {show: false},
      itemStyle: {borderColor: '#131e2c', borderWidth: 3, borderRadius: 3},
      data: Object.entries(channelNames).map(([channel, name], index) => ({
        name,
        value: data.messages.filter(message => message.channel === channel).length,
        itemStyle: {color: colors[index]},
      })),
    }],
  };

  return <main className="charts-page">
    <section className="chart-grid">
      <section className="panel" id="behavior">
        <div className="panel-head">
          <div><h2>Agent × 时间行为矩阵</h2><p>按轮次比较各 Agent 的{metricNames[metric]}，颜色越深表示数量越多。</p></div>
          <select aria-label="热力图指标" value={metric} onChange={event => setMetric(event.target.value)}>
            {Object.entries(metricNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
          </select>
        </div>
        <Chart option={heatOption} height={340}/>
      </section>
      <section className="panel" id="network">
        <div className="panel-head">
          <div><h2>Agent 通信网络</h2><p>节点表示 Agent，箭头表示收件或回复关系。</p></div>
          <select aria-label="关系类型" value={relation} onChange={event => setRelation(event.target.value)}>
            <option value="all">收件 + 回复</option><option value="recipient">指定收件人</option><option value="reply">有效时间回复</option>
          </select>
        </div>
        <Chart option={graphOption} height={340}/>
      </section>
      <section className="panel" id="timeline">
        <div className="panel-head"><div><h2>事件时间轴</h2><p>按真实时间展示外部事件、消息和异常候选。</p></div></div>
        <Chart option={timelineOption} height={300}/>
      </section>
      <section className="panel" id="channels">
        <div className="panel-head"><div><h2>通信渠道分布</h2><p>比较不同通信渠道的消息数量与占比。</p></div></div>
        <Chart option={channelOption} height={300}/>
      </section>
    </section>
  </main>;
}
