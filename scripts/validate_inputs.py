# -*- coding: utf-8 -*-
"""Halo 周报 · 输入校验脚本（skill 版）
只校验不产出：检查两周 12 个文件是否存在、CSV 能否以 GBK 解析、文件内部日期是否与后缀所在周一致。
用法：python validate_inputs.py [--data-dir DIR] [--this YYYYMMDD] [--last YYYYMMDD]
输出：stdout JSON {ok, files: [...], warnings: [...], errors: [...]}；退出码 0=通过，2=存在错误。
"""
import argparse, glob, json, os, re, sys
from datetime import datetime, timedelta

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--data-dir', default=os.environ.get('HALO_DATA_DIR', r'C:\Users\24190\Desktop\推广文件'))
ap.add_argument('--this', default=None)
ap.add_argument('--last', default=None)
args = ap.parse_args()

REQUIRED = ['关键词报表_{}.csv', '人群报表_{}.csv', '商品报表_{}.csv', '计划报表_{}.csv',
            '营销场景报表_{}.csv', '品牌专区报表{}.xlsx']

res = {'ok': True, 'data_dir': args.data_dir, 'files': [], 'warnings': [], 'errors': []}

if not os.path.isdir(args.data_dir):
    res['ok'] = False
    res['errors'].append(f'数据目录不存在：{args.data_dir}')
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(2)

this, last = args.this, args.last
if not (this and last):
    tags = sorted({m.group(1) for f in glob.glob(os.path.join(args.data_dir, '*.*'))
                   for m in [re.search(r'(\d{8})', os.path.basename(f))] if m}, reverse=True)
    if len(tags) < 2:
        res['ok'] = False
        res['errors'].append(f'可识别日期后缀不足 2 个：{tags}')
        print(json.dumps(res, ensure_ascii=False, indent=1))
        sys.exit(2)
    this, last = tags[0], tags[1]
res['this'], res['last'] = this, last

for tag, role in [(this, '本周'), (last, '上周')]:
    ws = datetime.strptime(tag, '%Y%m%d')
    we = ws + timedelta(days=6)
    for tpl in REQUIRED:
        fname = tpl.format(tag)
        fpath = os.path.join(args.data_dir, fname)
        item = {'file': fname, 'role': role, 'exists': os.path.exists(fpath)}
        if not item['exists']:
            res['errors'].append(f'缺少{role}文件：{fname}')
            res['files'].append(item)
            continue
        try:
            if fname.endswith('.csv'):
                df = pd.read_csv(fpath, encoding='gbk', nrows=5)
                item['cols'] = len(df.columns)
                if role == '本周' and fname.startswith(('关键词报表_', '人群报表_')):
                    missing_plan_cols = {'计划ID', '计划名字'} - set(df.columns)
                    if missing_plan_cols:
                        res['errors'].append(f'{fname} 缺少用于优化清单计划关联的字段：' + '、'.join(sorted(missing_plan_cols)))
                v = str(df['日期'].iloc[0]) if '日期' in df.columns else ''
                m = re.match(r'(\d{8})至(\d{8})', v)
                if m:
                    s = datetime.strptime(m.group(1), '%Y%m%d')
                    if abs((s - ws).days) > 1:
                        res['warnings'].append(f'{fname} 内部周期起点 {m.group(1)} 与后缀所在周 {tag} 不一致')
                item['readable'] = True
            else:
                xl = pd.ExcelFile(fpath)
                item['sheets'] = xl.sheet_names
                if '账户' not in xl.sheet_names:
                    res['warnings'].append(f'{fname} 缺少"账户"sheet')
                item['readable'] = True
        except Exception as e:
            item['readable'] = False
            res['errors'].append(f'{fname} 读取失败：{e}（CSV 需 GBK 编码）')
        res['files'].append(item)

res['ok'] = not res['errors']
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if res['ok'] else 2)
