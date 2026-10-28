"""Retain intermediate artifacts computed from official MC1 raw and processed data."""
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import zipfile

from inspect_data import ROOT, dump
from pipeline import TOPIC, NAMED, aliases, token

EVIDENCE = ROOT / 'reports/evidence'


def save_csv(name, rows):
    path = EVIDENCE / (name + '.csv')
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    return str(path.relative_to(ROOT))


def build():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / 'data/processed/dashboard.json').read_text())
    source = ROOT / 'data/raw' / data['messages'][0]['source_file']
    raw = json.loads(source.read_text())
    messages = [message for round_ in raw['rounds'] for message in round_['communications']]
    processed = {message['message_id']: message for message in data['messages']}
    raw_by_id = {message['message_id']: message for message in messages}
    assert set(raw_by_id) == set(processed), 'Evidence must use the exact current raw dataset.'
    archive = ROOT / 'data/raw/VAST_Challenge_2026_MC1.zip'
    with zipfile.ZipFile(archive) as zipped:
        files = [{'name': entry.filename, 'bytes': entry.file_size, 'compressed_bytes': entry.compress_size,
                  'category': '系统元数据' if entry.filename.startswith('__MACOSX/') or entry.filename.endswith('.DS_Store') else '语义文件'}
                 for entry in zipped.infolist() if not entry.is_dir()]
    save_csv('01_archive_inventory', files)
    fields = []
    for field in sorted({key for message in messages for key in message}):
        fields.append({'field': field, 'present': sum(field in message for message in messages),
                       'missing': sum(field not in message for message in messages),
                       'null': sum(field in message and message[field] is None for message in messages),
                       'empty_list': sum(isinstance(message.get(field), list) and not message[field] for message in messages),
                       'empty_string': sum(isinstance(message.get(field), str) and not message[field].strip() for message in messages),
                       'types': dict(Counter(type(message[field]).__name__ for message in messages if field in message))})
    save_csv('02_message_field_audit', fields)
    round_windows = []
    for index, round_ in enumerate(data['rounds']):
        group = [message for message in data['messages'] if message['round_index'] == index]
        next_start = data['rounds'][index + 1]['timestamp'] if index + 1 < len(data['rounds']) else None
        gap = (datetime.fromisoformat(next_start) - datetime.fromisoformat(round_['timestamp'])).total_seconds() / 3600 if next_start else None
        round_windows.append({'round': index + 1, 'round_start': round_['timestamp'], 'next_round_start': next_start,
                              'next_start_gap_hours': gap, 'analysis_window_hours': round_['window_hours'],
                              'last_message': max(message['timestamp'] for message in group), 'messages': len(group),
                              'public_messages': sum(message['scope'] == 'external' for message in group),
                              'unavailable': round_['unavailable']})
    save_csv('03_round_windows', round_windows)
    roster = [message for round_ in raw['rounds'] for message in round_['communications']] + [agent for round_ in raw['rounds'] for agent in round_['participants']]
    name_map = aliases(roster)
    recipient_tokens = sorted({recipient for message in messages for recipient in message.get('recipients', [])})
    mappings = [{'raw_recipient': recipient, 'normalized_agent_id': name_map.get(token(recipient), '') if recipient != 'ALL' else '',
                 'policy': '保留广播标志 不展开已读关系' if recipient == 'ALL' else '用实际 ID role label 无歧义匹配',
                 'occurrences': sum(recipient in message.get('recipients', []) for message in messages)} for recipient in recipient_tokens]
    save_csv('04_recipient_mapping', mappings)
    reference_rows = []
    for message in data['messages']:
        ref = message['responding_to']
        parent = processed.get(ref)
        status = '空引用' if not ref else '非消息ID引用' if parent is None else '未来引用' if parent['timestamp'] > message['timestamp'] else '时间有效引用'
        reference_rows.append({'message_id': message['message_id'], 'timestamp': message['timestamp'], 'responding_to': ref,
                               'parent_timestamp': parent['timestamp'] if parent else '', 'status': status,
                               'json_pointer': message['json_pointer']})
    save_csv('05_reply_reference_audit', reference_rows)
    examples = []
    chosen = [data['messages'][0]['message_id'], '20460605_13_004', '20460605_13_002', data['evidence_summary']['first_named_public']['message_id']]
    for message_id in chosen:
        item = processed[message_id]
        examples.append({'message_id': message_id, 'source_file': item['source_file'], 'json_pointer': item['json_pointer'],
                         'raw_record': raw_by_id[message_id], 'normalized_record': item,
                         'generated_edges': [edge for edge in data['communication_edges'] if edge['message_id'] == message_id],
                         'internal_state_rows': [state for state in data['internal_states'] if state['message_id'] == message_id]})
    dump(EVIDENCE / '06_before_after_examples.json', examples)
    table_rows = []
    for name in ['messages', 'agents', 'events', 'internal_states', 'communication_edges', 'participants', 'rounds', 'candidates']:
        path = ROOT / 'data/processed' / (name + '.csv')
        with path.open(encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream); rows = list(reader); columns = reader.fieldnames
        assert len(rows) == len(data[name])
        table_rows.append({'table': name, 'rows': len(rows), 'columns': len(columns), 'bytes': path.stat().st_size, 'path': str(path.relative_to(ROOT))})
        with path.open(encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            dump(EVIDENCE / f'preview_{name}.json', [row for _, row in zip(range(3), reader)])
    save_csv('07_normalized_table_inventory', table_rows)
    stages = [{'stage': '原始消息', 'count': len(messages)}, {'stage': '规范化保留', 'count': len(processed)},
              {'stage': '主题关键词消息', 'count': sum(message['topic_match'] for message in data['messages'])},
              {'stage': '公开渠道消息', 'count': sum(message['scope'] == 'external' for message in data['messages'])},
              {'stage': '异常候选支持消息', 'count': len({mid for candidate in data['candidates'] for mid in candidate['supporting_message_ids']})}]
    save_csv('08_filter_subsets', stages)
    reply_counts = dict(Counter(row['status'] for row in reference_rows))
    edge_counts = dict(Counter(edge['relation'] for edge in data['communication_edges']))
    valid_edges = [edge for edge in data['communication_edges'] if edge['temporal_valid']]
    network_edges = [edge for edge in valid_edges if edge['source'] != edge['target']]
    rule_counts = dict(Counter(candidate['type'] for candidate in data['candidates']))
    rule_stats = [{'rule': name, 'candidates': count,
                   'support_messages': len({mid for candidate in data['candidates'] if candidate['type'] == name for mid in candidate['supporting_message_ids']})}
                  for name, count in rule_counts.items()]
    save_csv('09_rule_statistics', rule_stats)
    contact_stats = []
    for agent in data['agents']:
        contact_stats.append({'agent_id': agent['agent_id'], 'label': agent['label'], 'messages': agent['message_count'],
                              'internal': agent['internal_count'], 'public': agent['external_count'],
                              'public_ratio': agent['external_ratio'], 'candidates': agent['candidate_count'],
                              'common_window_hours': agent['observed_window_hours'], 'rate_per_hour': agent['messages_per_window_hour']})
    save_csv('10_agent_behavior', contact_stats)
    markers = []
    def marker(kind, message):
        markers.append({'kind': kind, 'timestamp': message['timestamp'], 'message_id': message['message_id'],
                        'agent_id': message['agent_id'], 'channel': message['channel'], 'content': message['content'],
                        'source_file': message['source_file'], 'json_pointer': message['json_pointer']})
    named_internal = next(message for message in data['messages'] if message['scope'] == 'internal' and message['named_topic'])
    contamination = next(message for message in data['messages'] if 'neither intern was briefed' in message['content'].lower())
    consent = next(message for message in data['messages'] if 'verbal consent confirmed' in message['content'].lower() and 'GO' in message['content'])
    marker('内部实体提及', named_internal);marker('越权接触报告', contamination);marker('口头授权声称与公开指令', consent)
    marker('首次直接实体公开', data['evidence_summary']['first_named_public']);marker('正式解禁记录', data['evidence_summary']['formal_lift'])
    dump(EVIDENCE / '11_key_evidence_records.json', markers)
    summary = {'source_file': str(source.relative_to(ROOT)), 'archive_file_count': len(files),
               'archive_semantic_files': sum(file['category'] == '语义文件' for file in files),
               'archive_metadata_files': sum(file['category'] == '系统元数据' for file in files),
               'archive_uncompressed_bytes': sum(file['bytes'] for file in files), 'message_count': len(messages),
               'agent_count': len(data['agents']), 'round_count': len(data['rounds']), 'fields': fields, 'reply_counts': reply_counts,
               'edge_counts': edge_counts, 'valid_edge_count': len(valid_edges), 'hidden_self_edges': len(valid_edges) - len(network_edges),
               'network_edge_records': len(network_edges), 'network_aggregate_edges': len({(edge['source'], edge['target']) for edge in network_edges}),
               'candidate_count': len(data['candidates']), 'candidate_support_messages': stages[-1]['count'],
               'rule_stats': rule_stats, 'table_inventory': table_rows,
               'internal_state_types': dict(Counter(state['state_type'] for state in data['internal_states'])),
               'environment_event_types': dict(Counter(event['type'] for event in data['events'])),
               'nonterminal_gap_counts': dict(Counter(row['next_start_gap_hours'] for row in round_windows[:-1])),
               'role_mapping': mappings, 'filter_subsets': stages,
               'quality': {key: value for key, value in data['quality'].items() if key != 'issues'}}
    assert sum(reply_counts.values()) == len(messages)
    assert sum(summary['internal_state_types'].values()) == len(data['internal_states'])
    assert sum(summary['environment_event_types'].values()) == len(data['events'])
    assert summary['network_edge_records'] + summary['hidden_self_edges'] == summary['valid_edge_count']
    dump(EVIDENCE / 'summary.json', summary)
    index = ['# 数据处理中间证据', '', '全部文件由 `python scripts/build_evidence.py` 从官方原始 JSON 和当前标准化输出重建。', '',
             '| 文件 | 内容 |', '|---|---|']
    descriptions = {'01_archive_inventory.csv':'压缩包内每个文件及大小', '02_message_field_audit.csv':'字段缺失 null 空数组分别统计',
                    '03_round_windows.csv':'全部23轮真实时间和分析时长', '04_recipient_mapping.csv':'原始接收人到实际 Agent 的映射',
                    '05_reply_reference_audit.csv':'全部912条回复引用分类', '06_before_after_examples.json':'四条真实消息的原始与处理后对照',
                    '07_normalized_table_inventory.csv':'八张处理表的规模与路径', '08_filter_subsets.csv':'保留与各分析子集计数',
                    '09_rule_statistics.csv':'候选规则数及支持消息数', '10_agent_behavior.csv':'各 Agent 内外部行为统计',
                    '11_key_evidence_records.json':'五条关键时间节点的完整原文与来源', '12_verification_runs.json':'实际运行的验证命令 退出码和原样输出', 'report_manifest.json':'Word 的图表来源与章节清单', 'verification.json':'中间证据与原数据交叉核验结果', 'document_qa.json':'本次 Word 渲染逐页检查记录及文件校验值（重新生成后需复查）', 'summary.json':'报告引用的汇总统计'}
    for name, description in descriptions.items(): index.append(f'| [{name}]({name}) | {description} |')
    index += ['', 'preview_*.json 保留每张处理表的前三条记录。时间为官方模拟时间，不添加时区。关键词子集与异常支持子集可重叠。',
              '原始数据仍在 data/raw 并被 Git 忽略；这里只提交少量有指针的实例与统计结果。', '']
    (EVIDENCE / 'README.md').write_text('\n'.join(index))
    print(json.dumps({'intermediate_files': len(list(EVIDENCE.glob('*'))), 'messages_audited': len(messages),
                      'reply_counts': reply_counts, 'table_rows': {row['table']: row['rows'] for row in table_rows}}, ensure_ascii=False))
    return data, summary

if __name__ == '__main__': build()
