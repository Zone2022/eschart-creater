# -*- coding: utf-8 -*-
"""Halo 站内推广周报 · 数据分析脚本（skill 版）
读取两周导出表（万相台无界 CSV + 品销宝 xlsx），输出 analysis.json（机器可读）+ stdout JSON 摘要。
文件名后缀 = 数据所在周的周一（如 20260803）；CSV 必须 GBK 编码；品牌专区报表=品销宝。
用法：
  python analyze.py [--data-dir DIR] [--this YYYYMMDD] [--last YYYYMMDD] [--out analysis.json]
  不传 --this/--last 时自动识别目录中最新两个日期后缀。
环境变量：HALO_DATA_DIR 可替代 --data-dir。无密钥需求。
退出码：0 成功；2 输入缺失/校验失败（stderr 输出人类可读错误，stdout 输出 JSON 错误对象）。
"""
import argparse, glob, json, os, re, sys
from datetime import datetime, timedelta

import pandas as pd

NUM_COLS = ['展现量', '点击量', '花费', '直接成交金额', '间接成交金额', '总成交金额', '总成交笔数',
            '总收藏加购数', '成交新客数', '成交人数']
REQUIRED = ['关键词报表_{}.csv', '人群报表_{}.csv', '商品报表_{}.csv', '计划报表_{}.csv',
            '营销场景报表_{}.csv', '品牌专区报表{}.xlsx']


def fail(msg, code=2, **extra):
    json.dump({'ok': False, 'error': msg, **extra}, sys.stdout, ensure_ascii=False)
    print('\n[analyze] 错误：' + msg, file=sys.stderr)
    sys.exit(code)


def detect_dates(data_dir):
    tags = set()
    for f in glob.glob(os.path.join(data_dir, '*报表*_????????.*')) + glob.glob(os.path.join(data_dir, '*报表????????.*')):
        m = re.search(r'(\d{8})', os.path.basename(f))
        if m:
            tags.add(m.group(1))
    tags = sorted(tags, reverse=True)
    if len(tags) < 2:
        fail(f'数据目录中可识别的日期后缀不足 2 个（识别到 {tags}），无法做周环比。请检查文件名。')
    return tags[0], tags[1]


def week_range(tag):
    """suffix=周一 → 该周周一~周日"""
    d = datetime.strptime(tag, '%Y%m%d')
    return d, d + timedelta(days=6)


def check_inner_dates(df, tag, fname, warnings):
    """核对文件内部日期列与文件名后缀所在周是否一致（曾出现导错周期的情况）"""
    if '日期' not in df.columns or df.empty:
        return
    v = str(df['日期'].iloc[0])
    m = re.match(r'(\d{8})至(\d{8})', v)
    ws, we = week_range(tag)
    if m:
        s, e = datetime.strptime(m.group(1), '%Y%m%d'), datetime.strptime(m.group(2), '%Y%m%d')
        if not (abs((s - ws).days) <= 1 and abs((e - we).days) <= 1):
            warnings.append(f'{fname} 内部周期 {m.group(1)}~{m.group(2)} 与文件名后缀 {tag} 所在周不一致，请确认是否导错周期')
    else:
        try:
            ds = pd.to_datetime(df['日期'])
            if not (ds.min() >= ws - timedelta(days=1) and ds.max() <= we + timedelta(days=1)):
                warnings.append(f'{fname} 日粒度范围 {ds.min().date()}~{ds.max().date()} 超出后缀 {tag} 所在周')
        except Exception:
            warnings.append(f'{fname} 日期列无法解析：{v}')


def agg(df):
    out = {}
    for c in NUM_COLS:
        out[c] = float(pd.to_numeric(df[c], errors='coerce').fillna(0).sum()) if c in df.columns else 0.0
    out['ROI'] = out['总成交金额'] / out['花费'] if out['花费'] else None
    out['CTR'] = out['点击量'] / out['展现量'] if out['展现量'] else None
    out['CPC'] = out['花费'] / out['点击量'] if out['点击量'] else None
    out['新客率'] = out['成交新客数'] / out['成交人数'] if out['成交人数'] else None
    out['新客成本'] = out['花费'] / out['成交新客数'] if out['成交新客数'] else None
    return out


# ---------- 分类规则（token 见 references/classification-tokens.json，此处保持同步） ----------
TOK = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references',
                                  'classification-tokens.json'), encoding='utf-8'))
BRAND_TOKENS = TOK['brand_tokens']
COMP_TOKENS = TOK['competitor_tokens']
AUD_BRAND_TOKENS = TOK['audience_brand_tokens']


def has_any(name, tokens):
    n = str(name).lower()
    return any(t in n for t in tokens)


def classify_kw(row):
    name = str(row['词名字/词包名字'])
    if has_any(name, BRAND_TOKENS):
        return '品牌词'
    if has_any(name, COMP_TOKENS[3:]):
        return '竞品词'
    if row['词类型'] == '关键词包' or '智选' in name:
        return '智能词包'
    return '行业词'


def classify_aud(name):
    if has_any(name, COMP_TOKENS):
        return '竞品人群'
    if has_any(name, AUD_BRAND_TOKENS):
        return '品牌人群'
    return '行业人群'


def classify_plan(scene, name):
    if scene == '货品全站推广':
        return '全站推广'
    if scene in ('超级短视频', '超级直播'):
        return '内容场'
    if has_any(name, COMP_TOKENS) or '跟投' in str(name):
        return '竞品人群'
    if '品牌词' in str(name) or '_品牌_' in str(name) or has_any(name, BRAND_TOKENS):
        return '品牌人群'
    return '行业人群'


def merge_full(d1, d0, key):
    g1 = d1.groupby(key, as_index=False)[NUM_COLS].sum()
    g0 = d0.groupby(key, as_index=False)[NUM_COLS].sum()
    m = pd.merge(g1, g0, on=key, how='outer', suffixes=('_1', '_0')).fillna(0)
    m['spend_sum'] = m['花费_1'] + m['花费_0']
    return m


def plan_quadrant(roi, new_rate):
    """按 ROI=5、新客率=50% 将计划放入推广波士顿矩阵。"""
    if roi is None or new_rate is None:
        return '待观察'
    if roi >= 5 and new_rate >= 0.50:
        return '明星计划'
    if roi >= 5:
        return '效率计划'
    if new_rate >= 0.50:
        return '拉新潜力'
    return '待调整'


def plan_matrix_action(quadrant):
    return {
        '明星计划': 'ROI 与新客率双达标，守住 ROI≥5 后分步加预算',
        '效率计划': 'ROI 达标但新客率不足，保留收益并优化人群/素材提升拉新',
        '拉新潜力': '新客率达标但 ROI 不足，控价并优化转化承接，2 周观察',
        '待调整': 'ROI 与新客率双不达标，降预算或暂停，预算转向明星计划',
        '待观察': '成交人数不足，暂不进入四象限，补足样本后再判定',
    }[quadrant]


def _plan_week(r, suffix):
    sp = float(r[f'花费_{suffix}'])
    gmv = float(r[f'总成交金额_{suffix}'])
    buyers = float(r[f'成交人数_{suffix}'])
    new_customers = float(r[f'成交新客数_{suffix}'])
    roi = _roi(gmv, sp)
    new_rate = new_customers / buyers if buyers else None
    quadrant = plan_quadrant(roi, new_rate) if sp > 0 else '未投放'
    return {
        'active': sp > 0, 'spend': sp, 'gmv': gmv, 'roi': roi, 'new_rate': new_rate,
        'new_customers': new_customers, 'buyers': buyers, 'quadrant': quadrant,
        'action': plan_matrix_action(quadrant) if quadrant != '未投放' else '当周未投放',
    }


def build_plan_matrix(m):
    """输出计划级双周 ROI×新客率矩阵点，供前端切换并动画观察趋势。"""
    out = []
    for _, r in m.iterrows():
        sp1, sp0 = float(r['花费_1']), float(r['花费_0'])
        if sp1 <= 0 and sp0 <= 0:
            continue
        w0, w1 = _plan_week(r, '0'), _plan_week(r, '1')
        out.append({
            'key': str(r['计划key']), 'name': str(r['计划名字']),
            'cat': str(r['分类']), 'scene': str(r['场景名字']), 'w0': w0, 'w1': w1,
            # 保留本周扁平字段，兼容简评撰写与既有消费逻辑。
            'sp1': w1['spend'], 'sp0': w0['spend'], 'g1': w1['gmv'], 'g0': w0['gmv'],
            'roi1': w1['roi'], 'roi0': w0['roi'], 'new_rate': w1['new_rate'],
            'new_customers': w1['new_customers'], 'buyers': w1['buyers'],
            'quadrant': w1['quadrant'], 'action': w1['action'],
        })
    out.sort(key=lambda x: (-max(x['sp1'], x['sp0']), x['name']))
    return out


def build_product_sku(m):
    """输出所有 SKU 的双周推广费比；费比=花费÷总成交金额。"""
    out = []
    for _, r in m.iterrows():
        def week(suffix):
            spend = float(r[f'花费_{suffix}'])
            gmv = float(r[f'总成交金额_{suffix}'])
            return {'spend': spend, 'gmv': gmv, 'fee_ratio': spend / gmv if gmv else None}
        w0, w1 = week('0'), week('1')
        out.append({'name': str(r['主体名称']), 'w0': w0, 'w1': w1})
    out.sort(key=lambda x: (x['w1']['fee_ratio'] is None, -(x['w1']['fee_ratio'] or 0), -x['w1']['spend'], x['name']))
    return out


# ---------- 优化清单（判定标准见 references/business-rules.md 第 5 节，源自 8 月拉新方案） ----------
OPT_THRES = {'kw': 500.0, 'au': 1000.0, 'plan': 1000.0}  # 本周花费门槛（元）
ROI_PASS = 5.0          # 单项合格线（<5 进入优化或减投流程）
ROI_RED = 4.0           # 效率警戒线（<4 必须处置）
NEW_RATE_PASS = 0.50    # 拉新类人群包新客率合格线


def _roi(g, sp):
    return g / sp if sp else None


def kw_opt_action(cat, roi1):
    if cat == '品牌词':
        return '品牌承接词效率低于合格线，控价并核查与品专的分流'
    if cat == '竞品词':
        return '竞品词试点未达合格线，按 2 周 A/B 小样规则关停或调条件'
    if cat == '智能词包':
        return '词包效率低于合格线，周度巡检词包结构并控价'
    if roi1 is not None and roi1 < ROI_RED:
        return '低于 4 元警戒线，降价缩量或暂停'
    return '收窄匹配（短语/精确）+ 否词，2 周观察，持续 <5 减投'


def au_opt_action(cat, new_rate):
    """人群包分类评价：拉新类=新客率≥50% 且 ROI≥5；竞品拦截=三件套代理；品牌召回=ROI≥5"""
    if cat == '竞品人群':
        return '竞品拦截按三件套评估（首单转化/新客客单/复购，周报以新客率代理）；叠加「30 天搜进口粮/功能词」升级信号，持续 <5 减投'
    if cat == '品牌人群':
        return '品牌资产召回效率低于合格线，核查权益/券投放与承接 SKU 结构'
    if new_rate is not None and new_rate < NEW_RATE_PASS:
        return '拉新类包新客率未达 50%，调圈选条件或减投'
    return '新客率达标但 ROI<5，优化出价/创意，2 周观察'


def plan_opt_action(cat, roi1, new_rate):
    quadrant = plan_quadrant(roi1, new_rate)
    if cat == '全站推广':
        return f'{quadrant}；全站 ROI 含免费流量※，先核查货品结构与出价'
    return f'{quadrant}；{plan_matrix_action(quadrant)}'


def build_optimize(m, name_col, kind):
    """筛出本周花费达门槛且 ROI<5 的对象（词≥500 元 / 人群、计划≥1000 元），按本周花费降序。"""
    thres = OPT_THRES[kind]
    out = []
    for _, r in m.iterrows():
        sp1, sp0 = float(r['花费_1']), float(r['花费_0'])
        if sp1 < thres:
            continue
        g1, g0 = float(r['总成交金额_1']), float(r['总成交金额_0'])
        roi1 = _roi(g1, sp1)
        if roi1 is None or roi1 >= ROI_PASS:
            continue
        cat = str(r['分类']) if '分类' in m.columns else ''
        item = {'name': str(r[name_col]), 'cat': cat, 'sp1': sp1, 'g1': g1, 'roi1': roi1,
                'sp0': sp0, 'g0': g0, 'roi0': _roi(g0, sp0),
                'sp_chg': (sp1 / sp0 - 1) * 100 if sp0 else None}
        if kind == 'au':
            nr = (float(r['成交新客数_1']) / float(r['成交人数_1'])) if float(r['成交人数_1']) else None
            item['new_rate'] = nr
            item['action'] = au_opt_action(cat, nr)
        elif kind == 'kw':
            item['action'] = kw_opt_action(cat, roi1)
        else:
            nr = (float(r['成交新客数_1']) / float(r['成交人数_1'])) if float(r['成交人数_1']) else None
            item['new_rate'] = nr
            item['quadrant'] = plan_quadrant(roi1, nr)
            item['action'] = plan_opt_action(cat, roi1, nr)
        out.append(item)
    out.sort(key=lambda x: -x['sp1'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default=os.environ.get('HALO_DATA_DIR', r'C:\Users\24190\Desktop\推广文件'))
    ap.add_argument('--this', default=None, help='本周文件名后缀 YYYYMMDD（该周周一）')
    ap.add_argument('--last', default=None, help='上周文件名后缀 YYYYMMDD')
    ap.add_argument('--out', default=None, help='analysis.json 输出路径')
    args = ap.parse_args()
    base = args.data_dir
    if not os.path.isdir(base):
        fail(f'数据目录不存在：{base}')
    t1, t0 = (args.this, args.last) if (args.this and args.last) else detect_dates(base)
    out_path = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis.json')

    warnings = []
    dfs = {}
    for tag, wk in [(t1, '1'), (t0, '0')]:
        for tpl in REQUIRED:
            fname = tpl.format(tag)
            fpath = os.path.join(base, fname)
            if not os.path.exists(fpath):
                fail(f'缺少输入文件：{fpath}', missing=fname)
            try:
                if fname.endswith('.csv'):
                    df = pd.read_csv(fpath, encoding='gbk')
                else:
                    df = pd.read_excel(fpath, sheet_name='账户')
            except Exception as e:
                fail(f'文件读取失败：{fname}（{e}）。CSV 需 GBK 编码。')
            key = re.sub(r'[_\d.]', '', fname.replace('报表', '').replace('csv', '').replace('xlsx', '')) + wk
            check_inner_dates(df, tag, fname, warnings)
            dfs[key] = df

    sc0, sc1 = dfs['营销场景0'], dfs['营销场景1']
    kw0, kw1 = dfs['关键词0'], dfs['关键词1']
    au0, au1 = dfs['人群0'], dfs['人群1']
    pr0, pr1 = dfs['商品0'], dfs['商品1']
    pl0, pl1 = dfs['计划0'], dfs['计划1']
    px0, px1 = dfs['品牌专区0'], dfs['品牌专区1']

    scenes_order = ['关键词推广', '人群推广', '货品全站推广', '超级短视频', '超级直播']
    scene_agg = {s: {'w0': agg(sc0[sc0['场景名字'] == s]), 'w1': agg(sc1[sc1['场景名字'] == s])}
                 for s in scenes_order}
    total = {'w0': agg(sc0), 'w1': agg(sc1)}

    for df in (kw0, kw1):
        df['分类'] = df.apply(classify_kw, axis=1)
    kw_cat = {}
    for cat in ['品牌词', '竞品词', '行业词', '智能词包']:
        d0, d1 = kw0[kw0['分类'] == cat], kw1[kw1['分类'] == cat]
        kw_cat[cat] = {'w0': agg(d0), 'w1': agg(d1),
                       'n0': int(d0['词名字/词包名字'].nunique()), 'n1': int(d1['词名字/词包名字'].nunique())}
    kw_m = merge_full(kw1, kw0, '词名字/词包名字')
    name2cat = pd.concat([kw0[['词名字/词包名字', '分类']], kw1[['词名字/词包名字', '分类']]]) \
        .drop_duplicates('词名字/词包名字').set_index('词名字/词包名字')['分类'].to_dict()
    kw_m['分类'] = kw_m['词名字/词包名字'].map(name2cat)
    kw_detail = kw_m.sort_values('spend_sum', ascending=False).head(25)

    for df in (au0, au1):
        df['分类'] = df['人群名字'].apply(classify_aud)
    au_cat = {}
    for cat in ['品牌人群', '竞品人群', '行业人群']:
        d0, d1 = au0[au0['分类'] == cat], au1[au1['分类'] == cat]
        au_cat[cat] = {'w0': agg(d0), 'w1': agg(d1),
                       'n0': int(d0['人群名字'].nunique()), 'n1': int(d1['人群名字'].nunique())}
    au_top = {}
    for cat in ['品牌人群', '竞品人群', '行业人群']:
        m = merge_full(au1[au1['分类'] == cat], au0[au0['分类'] == cat], '人群名字')
        au_top[cat] = m.sort_values('花费_1', ascending=False).head(6).to_dict('records')

    def px_agg(df):
        num = df.select_dtypes('number').sum()
        return {'搜索量': float(num['搜索量']), '展现量': float(num['展现量']), '点击量': float(num['点击量']),
                '进店访客数': float(num['进店访客数']), '成交金额': float(num['成交金额']),
                '成交笔数': float(num['成交笔数']), '客单价': float(num['成交金额'] / num['成交笔数']),
                '宝贝收藏数': float(num['宝贝收藏数']), '宝贝加购数': float(num['宝贝加购数']),
                '回搜触达访客数': float(num['回搜触达访客数']), '店铺收藏数': float(num['店铺收藏数']),
                '触达访客数': float(num['触达访客数'])}
    px = {'w0': px_agg(px0), 'w1': px_agg(px1)}

    for df in (pl0, pl1):
        df['分类'] = df.apply(lambda r: classify_plan(r['场景名字'], r['计划名字']), axis=1)
        df['计划key'] = df['场景名字'] + '|' + df['计划名字']
    plan_cat = {}
    for cat in ['品牌人群', '竞品人群', '行业人群', '全站推广', '内容场']:
        d0, d1 = pl0[pl0['分类'] == cat], pl1[pl1['分类'] == cat]
        plan_cat[cat] = {'w0': agg(d0), 'w1': agg(d1),
                         'n0': int(d0['计划key'].nunique()), 'n1': int(d1['计划key'].nunique())}
    pm = merge_full(pl1, pl0, '计划key')
    sc_map = pd.concat([pl0[['计划key', '场景名字', '分类']], pl1[['计划key', '场景名字', '分类']]]).drop_duplicates('计划key')
    pm = pm.merge(sc_map, on='计划key', how='left')
    pm['计划名字'] = pm['计划key'].str.split('|').str[1]
    plan_detail = pm.sort_values('spend_sum', ascending=False)

    prm = merge_full(pr1, pr0, '主体名称')
    prod_sku = build_product_sku(prm)

    au_all = merge_full(au1, au0, '人群名字')
    au_all['分类'] = au_all['人群名字'].apply(classify_aud)
    plan_matrix = build_plan_matrix(pm)
    optimize = {
        'kw': build_optimize(kw_m.rename(columns={'词名字/词包名字': 'name'}), 'name', 'kw'),
        'au': build_optimize(au_all.rename(columns={'人群名字': 'name'}), 'name', 'au'),
        'plan': build_optimize(pm.rename(columns={'计划名字': 'name'}), 'name', 'plan'),
    }

    def parse_week(df, tag):
        """优先取文件内部'日期'列的真实周期（兼容旧导出日后缀），否则按后缀=周一推导"""
        try:
            v = str(df['日期'].iloc[0])
            m = re.match(r'(\d{4})(\d{2})(\d{2})至(\d{4})(\d{2})(\d{2})', v)
            if m:
                return f'{m.group(1)}-{m.group(2)}-{m.group(3)}', f'{m.group(4)}-{m.group(5)}-{m.group(6)}'
            ds = pd.to_datetime(df['日期'])
            return ds.min().strftime('%Y-%m-%d'), ds.max().strftime('%Y-%m-%d')
        except Exception:
            ws, we = week_range(tag)
            return ws.strftime('%Y-%m-%d'), we.strftime('%Y-%m-%d')

    ws1, we1 = parse_week(au1, t1)
    ws0, we0 = parse_week(au0, t0)
    meta = {'this': {'tag': t1, 'start': ws1, 'end': we1},
            'last': {'tag': t0, 'start': ws0, 'end': we0},
            'warnings': warnings}

    result = {'meta': meta, 'total': total, 'scene': scene_agg, 'kw_cat': kw_cat, 'au_cat': au_cat,
              'px': px, 'plan_cat': plan_cat, 'kw_detail': kw_detail.to_dict('records'),
              'au_top': au_top, 'plan_detail': plan_detail.to_dict('records'),
              'prod_sku': prod_sku,
              'plan_matrix': plan_matrix, 'optimize': optimize,
              'plan_total_w0': agg(pl0), 'plan_total_w1': agg(pl1)}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, default=str)

    summary = {'ok': True, 'meta': meta, 'out': out_path,
               'total': {k: round(total['w1'][k], 2) if isinstance(total['w1'][k], float) else total['w1'][k]
                         for k in ['花费', '总成交金额', '总成交笔数', '成交新客数']},
               'ROI': {'this': round(total['w1']['ROI'], 2), 'last': round(total['w0']['ROI'], 2)},
               'optimize': {k: {'n': len(v), 'spend': round(sum(i['sp1'] for i in v), 0)}
                            for k, v in optimize.items()},
               'warnings': warnings}
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=1)
    print()
    for w in warnings:
        print('[analyze] 警告：' + w, file=sys.stderr)


if __name__ == '__main__':
    main()
