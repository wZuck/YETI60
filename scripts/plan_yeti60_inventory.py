#!/usr/bin/env python3
"""Allocate a sanitized stock snapshot against the current per-keyboard BOM."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'hardware/bom/inventory-allocation.json'
BOM = ROOT / 'hardware/bom/mainboard.csv'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allocate(snapshot, bom):
    """Check physical-package/value matches and spend each received pool once."""
    by_ref = {}
    for row in bom:
        for ref in row['References'].split(', '):
            assert ref not in by_ref, 'Duplicate BOM reference: ' + ref
            by_ref[ref] = row
    assignments = {}
    stock_rows = set()
    for stock in snapshot['mainboard']:
        source_row = stock['source_row']
        assert source_row not in stock_rows, 'Stock pool counted twice'
        stock_rows.add(source_row)
        remaining = stock['received_units']
        assert isinstance(remaining, int) and remaining >= 0
        assert isinstance(stock['in_transit_units'], int) and stock['in_transit_units'] >= 0
        for ref in stock['references']:
            assert ref not in assignments, 'Reference allocated twice: ' + ref
            row = by_ref[ref]
            assert int(row['Quantity']) > 0, 'Cannot allocate DNP site'
            assert row['Package'] == stock['package'], 'Package mismatch: ' + ref
            assert row['Design value'] in stock['design_values'], 'Value mismatch: ' + ref
            used = int(remaining > 0)
            remaining -= used
            assignments[ref] = (stock, used)
    result = []
    for row in bom:
        required = int(row['Quantity'])
        if not required:
            continue
        refs = row['References'].split(', ')
        assert required == len(refs), 'Unexpected BOM grouping'
        available = sum(assignments[ref][1] for ref in refs if ref in assignments)
        matches = [assignments[ref][0] for ref in refs if ref in assignments]
        assert len({s['mpn'] for s in matches}) <= 1, 'Split mixed stock into separate BOM groups'
        result.append({
            'references': row['References'], 'required': required,
            'from_stock': available, 'buy': required - available,
            'value': row['Design value'], 'package': row['Package'],
            'stock_mpn': matches[0]['mpn'] if matches else '',
            'candidate_mpn': row['Specified or candidate MPN'],
            'source_rows': sorted({s['source_row'] for s in matches}),
        })
    assert sum(r['required'] for r in result) == 76
    assert all(r['from_stock'] + r['buy'] == r['required'] for r in result)
    return result


def main():
    snapshot = json.loads(INPUT.read_text())
    with BOM.open() as source:
        bom = list(csv.DictReader(source))
    rows = allocate(snapshot, bom)
    with (ROOT / 'hardware/bom/mainboard.zh-CN.csv').open() as source:
        chinese = {r[0]: r[4] for r in list(csv.reader(source))[1:]}
    outputs = []
    for zh in [False, True]:
        path = ROOT / ('hardware/bom/mainboard-purchase.zh-CN.csv' if zh else
                       'hardware/bom/mainboard-purchase.csv')
        with path.open('w', newline='') as target:
            writer = csv.writer(target, lineterminator='\n')
            writer.writerow(['位号', '需要数量', '计划用库存', '净补购数量', '设计值', '封装', '库存型号', '补购指定或候选型号', '来源行', '备注'] if zh else
                            ['References', 'Required', 'Planned stock use', 'Net purchase', 'Design value', 'Package', 'Stock MPN', 'Purchase specified or candidate MPN', 'Source rows', 'Notes'])
            for row in rows:
                note = ('库存按订单已收货数规划，装配前清点；电容须确认有效容量' if zh else
                        'Order-derived received stock; count before assembly; qualify effective capacitance') if row['stock_mpn'] else (
                        '库存未匹配；按原材料表确认供应商和参数后补购' if zh else
                        'No matching stock; qualify supplier and ratings per BOM before purchase')
                writer.writerow([row['references'], row['required'], row['from_stock'], row['buy'],
                                 row['value'], row['package'], row['stock_mpn'],
                                 (chinese[row['references']] if zh else row['candidate_mpn']) if row['buy'] else '',
                                 ', '.join(map(str, row['source_rows'])), note])
        outputs.append(path)
    optional = snapshot['bare_daughterboard_option']
    with (ROOT / 'hardware/usb-daughterboard/upstream/production/UDB-C-JSH_5.0_bom.csv').open() as source:
        daughter = list(csv.DictReader(source))
    cc = next(r for r in daughter if r['Designator'] == 'R1 R2')
    assert cc['Value'] == '5.1k' and cc['Manufacturer Part Number'] in optional['mpn']
    assert optional['references'] == ['R1', 'R2'] and not optional['credited_in_default_plan']
    sources = [INPUT, BOM, ROOT / 'hardware/bom/mainboard.zh-CN.csv', Path(__file__).resolve(),
               ROOT / 'hardware/usb-daughterboard/upstream/production/UDB-C-JSH_5.0_bom.csv',
               ROOT / 'README.md', ROOT / 'README.zh-CN.md',
               ROOT / 'docs/engineering/inventory-allocation.md',
               ROOT / 'docs/engineering/inventory-allocation.zh-CN.md']
    report = {
        'status': 'inventory-plan-reconciled-not-physical-stock-count',
        'required_mainboard_parts': sum(r['required'] for r in rows),
        'planned_stock_parts': sum(r['from_stock'] for r in rows),
        'net_purchase_parts': sum(r['buy'] for r in rows),
        'in_transit_credited': 0, 'optional_c5_parts_credited': 0,
        'physical_remaining_count_confirmed': False, 'production_approved': False,
        'rows': rows,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources},
        'outputs': {str(p.relative_to(ROOT)): sha(p) for p in outputs},
    }
    for suffix in ['', '.zh-CN']:
        text = (ROOT / ('README' + suffix + '.md')).read_text()
        for count in [report['planned_stock_parts'], report['net_purchase_parts']]:
            assert f'**{count}**' in text, 'README stock totals need refresh'
    (ROOT / 'docs/audit/yeti60-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['planned_stock_parts']}/76 mainboard parts planned from received stock; "
          f"{report['net_purchase_parts']} to buy; no in-transit or populated C5 double count")


if __name__ == '__main__':
    main()
