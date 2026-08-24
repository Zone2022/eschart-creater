# -*- coding: utf-8 -*-
"""Halo 站内推广周报 · HTML 渲染脚本（skill 版）
输入：analysis.json（analyze.py 产物）+ insights.json（Skill 流程按 templates/insight-style.md 撰写）。
输出：桌面 Halo站内推广周报_<周期>.html。
用法：
  python build_report.py [--analysis PATH] [--insights PATH] [--model NAME] [--out PATH]
环境变量：HALO_TEMPLATE_HTML 指定 CSS 模板来源（默认取桌面最新周报 HTML）。
退出码：0 成功；2 输入缺失；3 insights 缺键。
"""
import argparse, glob, html as html_lib, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument('--analysis', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis.json'))
ap.add_argument('--insights', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'insights.json'))
ap.add_argument('--model', default=os.environ.get('HALO_MODEL_NAME', 'Kimi-K3'))
ap.add_argument('--out', default=None)
args = ap.parse_args()


def fail(msg, code=2, **extra):
    json.dump({'ok': False, 'error': msg, **extra}, sys.stdout, ensure_ascii=False)
    print('\n[build_report] 错误：' + msg, file=sys.stderr)
    sys.exit(code)


if not os.path.exists(args.analysis):
    fail(f'analysis.json 不存在：{args.analysis}，请先运行 analyze.py')
J = json.load(open(args.analysis, encoding='utf-8'))
if not os.path.exists(args.insights):
    fail(f'insights.json 不存在：{args.insights}，请按 templates/insight-style.md 撰写各板块简评后再运行')
INS = json.load(open(args.insights, encoding='utf-8'))
need = ['scene', 'keyword', 'audience', 'brandzone', 'product', 'plan', 'optimize']
missing = [k for k in need if k not in INS or not INS[k]]
if missing:
    fail('insights.json 缺少字段：' + ', '.join(missing), code=3, missing=missing)
for k in ['scene', 'keyword', 'audience', 'brandzone', 'product', 'plan']:
    v = INS[k]
    if isinstance(v, list):
        if not all(isinstance(it, dict) and it.get('t') and it.get('c') for it in v):
            fail(f'insights.json 的 {k} 数组元素必须为 {{"t": 小标题, "c": 内容}} 结构', code=3)
    elif not isinstance(v, str):
        fail(f'insights.json 的 {k} 必须为字符串或结构化数组', code=3)
def render_insight(v, cls='insight', exclude_titles=()):
    """结构化结论：数组→带小标题的精简条目列表；字符串→兼容旧版单段文案"""
    if isinstance(v, list):
        items = [it for it in v if it['t'] not in exclude_titles]
        lis = ''.join(f'<li><b>{it["t"]}：</b>{it["c"]}</li>' for it in items)
        return f'<div class="{cls}"><ul class="take">{lis}</ul></div>'
    return f'<div class="{cls}">{v}</div>'

META = J['meta']
MODEL = args.model

# ---------------- 格式化助手 ----------------
def wan(v):
    return f'{v/10000:.1f}万'

def money(v):
    return f'{v:,.2f}'

def pct_chg(a, b):
    return (a / b - 1) * 100 if b else None

def chip(a, b, kind='pct'):
    if not b:
        return '<span class="chip neu">新增</span>' if a else '<span class="na">—</span>'
    if kind == 'pct':
        p = pct_chg(a, b)
        if p is None:
            return '<span class="na">—</span>'
        return f'<span class="chip {"up" if p >= 0 else "down"}">{"▲" if p >= 0 else "▼"} {abs(p):.1f}%</span>'
    d = a - b
    if kind == 'pp':
        return f'<span class="chip {"up" if d >= 0 else "down"}">{"▲" if d >= 0 else "▼"} {d*100:+.2f}pp</span>'
    return f'<span class="chip {"up" if d >= 0 else "down"}">{"▲" if d >= 0 else "▼"} {d:+.2f}</span>'

def roi_span(v):
    if v is None:
        return '<span class="na">—</span>'
    color = '#9A5D0B' if v >= 6 else ('#467A3C' if v < 4 else '#2A2333')
    return f'<span style="font-weight:800;color:{color}">{v:.2f}</span>'

def roi_span2(v):
    if v is None:
        return '<span class="na">—</span>'
    color = '#9A5D0B' if v >= 6 else ('#467A3C' if v < 4 else '#2A2333')
    return f'<span style="font-weight:600;color:{color}">{v:.2f}</span>'

def roi_chip(r1, r0):
    if r1 is None or r0 is None:
        return '<span class="chip neu">新增</span>' if r1 else '<span class="na">—</span>'
    d = r1 - r0
    return f'<span class="chip {"up" if d >= 0 else "down"}" title="ROI {r0:.2f} → {r1:.2f}">{"▲" if d >= 0 else "▼"} {d:+.2f}</span>'

def countup(v, f):
    return f'<span class="countup" data-v="{v}" data-f="{f}">0</span>'

TAG_STYLE = {
    '品牌词': 'color:#592688;background:#F4EEF9;border:1px solid #59268822',
    '竞品词': 'color:#CC7D11;background:#FBF1DF;border:1px solid #CC7D1122',
    '行业词': 'color:#2F86C9;background:#EAF3FB;border:1px solid #2F86C922',
    '智能词包': 'color:#B4A8C7;background:#F4EEF9;border:1px solid #B4A8C722',
    '品牌人群': 'color:#592688;background:#F4EEF9;border:1px solid #59268822',
    '竞品人群': 'color:#CC7D11;background:#FBF1DF;border:1px solid #CC7D1122',
    '行业人群': 'color:#2F86C9;background:#EAF3FB;border:1px solid #2F86C922',
    '全站推广': 'color:#7860A7;background:#F4EEF9;border:1px solid #7860A722',
    '内容场': 'color:#B4A8C7;background:#F4EEF9;border:1px solid #B4A8C722',
}
CAT_COLOR = {'品牌人群': '#592688', '竞品人群': '#CC7D11', '行业人群': '#2F86C9', '全站推广': '#7860A7', '内容场': '#B4A8C7',
             '品牌词': '#592688', '竞品词': '#CC7D11', '行业词': '#2F86C9', '智能词包': '#B4A8C7'}
def tag(cat):
    return f'<span class="tag" style="{TAG_STYLE[cat]}">{cat}</span>'

def cut(name, n=30):
    return name if len(name) <= n else name[:n - 1] + '…'


def attr(value):
    return html_lib.escape(str(value), quote=True)

T = J['total']
SC = J['scene']
KC = J['kw_cat']
AC = J['au_cat']
PX = J['px']
PC = J['plan_cat']
PLAN_MATRIX = J['plan_matrix']
PLAN_VALUE = J.get('plan_value', {})

# ---------------- 01 核心总览 ----------------
kpis = [
    ('推广总花费', countup(T['w1']['花费'], 'wan1'), ' 元', chip(T['w1']['花费'], T['w0']['花费']), f"上周：{money(T['w0']['花费'])} 元"),
    ('总成交金额', countup(T['w1']['总成交金额'], 'wan1'), ' 元', chip(T['w1']['总成交金额'], T['w0']['总成交金额']), f"上周：{money(T['w0']['总成交金额'])} 元"),
    ('整体 ROI', countup(T['w1']['ROI'], 'f2'), ' ', roi_chip(T['w1']['ROI'], T['w0']['ROI']), f"上周：{T['w0']['ROI']:.2f}"),
    ('新客率（新客/成交人数）', countup(T['w1']['新客率'] * 100, 'pct'), ' ', chip(T['w1']['新客率'], T['w0']['新客率'], 'pp'), f"上周：{T['w0']['新客率']*100:.2f}%"),
    ('成交新客数', countup(T['w1']['成交新客数'], 'int'), ' 人', chip(T['w1']['成交新客数'], T['w0']['成交新客数']), f"上周：{T['w0']['成交新客数']:,.0f} 人"),
    ('单个新客成本', countup(T['w1']['新客成本'], 'yuan1'), ' 元/人', chip(T['w1']['新客成本'], T['w0']['新客成本']), f"上周：{T['w0']['新客成本']:.1f} 元"),
    ('成交笔数', countup(T['w1']['总成交笔数'], 'int'), ' 笔', chip(T['w1']['总成交笔数'], T['w0']['总成交笔数']), f"上周：{T['w0']['总成交笔数']:,.0f} 笔"),
    ('点击量', countup(T['w1']['点击量'], 'wan1'), ' 次', chip(T['w1']['点击量'], T['w0']['点击量']), f"上周：{T['w0']['点击量']:,.0f} 次"),
    ('点击率 CTR', countup(T['w1']['CTR'] * 100, 'pct'), ' ', chip(T['w1']['CTR'], T['w0']['CTR']), f"上周：{T['w0']['CTR']*100:.2f}%"),
    ('平均点击花费 CPC', countup(T['w1']['CPC'], 'f2'), ' 元', chip(T['w1']['CPC'], T['w0']['CPC']), f"上周：{T['w0']['CPC']:.2f} 元"),
]
kpi_html = ''.join(f'''  <div class="card kpi reveal"><div class="lab">{l}</div><div class="val">{v}<small>{u}</small></div><div>{c}</div><div class="prev">{p}</div></div>\n''' for l, v, u, c, p in kpis)

# ---------------- 02 营销场景 ----------------
scenes_order = ['关键词推广', '人群推广', '货品全站推广', '超级短视频', '超级直播']
max_sp = max(SC[s][w]['花费'] for s in scenes_order for w in ('w0', 'w1'))
scene_rows = ''
for s in scenes_order:
    a, b = SC[s]['w1'], SC[s]['w0']
    star = '<span class="na" title="含免费流量成交">※</span>' if s == '货品全站推广' else ''
    nk1 = f"{a['新客率']*100:.2f}%" if a['新客率'] else '—'
    nk0 = f"{b['新客率']*100:.2f}%" if b['新客率'] else '—'
    cpc1 = f"{a['CPC']:.2f}" if a['CPC'] else '—'
    ctr1 = f"{a['CTR']*100:.2f}%" if a['CTR'] else '—'
    scene_rows += f'''<tr>
      <td style="font-weight:600">{s}{star}</td>
      <td style="min-width:170px">
        <div class="barbg" style="margin-bottom:3px"><div class="barfg" style="--w:{b['花费']/max_sp*100:.1f}%;background:#C4BBD1"></div></div>
        <div class="barbg"><div class="barfg" style="--w:{a['花费']/max_sp*100:.1f}%;background:#592688"></div></div>
      </td>
      <td class="r">{money(a['花费'])}</td>
      <td class="r">{chip(a['花费'], b['花费'])}</td>
      <td class="r">{money(a['总成交金额'])}</td>
      <td class="r">{chip(a['总成交金额'], b['总成交金额'])}</td>
      <td class="r">{roi_span(a['ROI'])}{star}</td>
      <td class="r">{roi_span2(b['ROI'])}</td>
      <td class="r">{roi_chip(a['ROI'], b['ROI'])}</td>
      <td class="r">{cpc1}</td>
      <td class="r">{ctr1}</td>
      <td class="r"><span style="font-weight:700">{nk1}</span><div style="font-size:11px;color:#978DA3">上周 {nk0}</div></td>
    </tr>'''

# ---------------- 分类卡 ----------------
def cat_card(cat, d, unit, sub=''):
    a, b = d['w1'], d['w0']
    r1 = f"{a['ROI']:.2f}" if a['ROI'] else '—'
    r0 = f"{b['ROI']:.2f}" if b['ROI'] else '—'
    rc = roi_chip(a['ROI'], b['ROI']) if a['ROI'] and b['ROI'] else '<span class="na">—</span>'
    gmv_chg = f"{pct_chg(a['总成交金额'], b['总成交金额']):+.1f}%" if b['总成交金额'] else '—'
    return f'''<div class="card kpi reveal" style="border-top:3px solid {CAT_COLOR[cat]}">
      <div class="lab">{tag(cat)} <span style="margin-left:6px">{d['n1']} {unit}</span> <span style="font-size:11px">{sub}</span></div>
      <div class="val" style="color:{CAT_COLOR[cat]}">{countup(a['花费'], 'wan1')}<small> 元 · 本周花费</small></div>
      <div>{chip(a['花费'], b['花费'])}</div>
      <div class="prev">成交 {wan(a['总成交金额'])} 元（{gmv_chg}）｜ ROI {r1}（上周 {r0}） {rc}</div>
    </div>'''

def matrix_html(items):
    """计划级双周 ROI×新客率矩阵；按钮切周时点位平滑移动。"""
    values = [a[w]['roi'] for a in items for w in ('w0', 'w1')
              if a[w]['active'] and a[w]['roi'] is not None and a[w]['new_rate'] is not None]
    x_max = max(10.0, max(values, default=10.0) * 1.10)
    w, h, ml, mr, mt, mb = 1000, 500, 62, 24, 28, 54
    pw, ph = w - ml - mr, h - mt - mb
    x_mid, y_mid = ml + 5 / x_max * pw, mt + 0.50 * ph
    qcolors = {'明星计划': '#467A3C', '效率计划': '#592688', '拉新潜力': '#CC7D11', '待调整': '#9B4A45'}
    circles = ''
    table_bodies = {'w0': '', 'w1': ''}
    pending_counts = {}
    for idx, a in enumerate(items, 1):
        coords = {}
        for wk in ('w0', 'w1'):
            d = a[wk]
            valid = d['active'] and d['roi'] is not None and d['new_rate'] is not None
            coords[wk] = {
                'valid': valid,
                'x': ml + min(d['roi'], x_max) / x_max * pw if valid else None,
                'y': mt + (1 - min(max(d['new_rate'], 0), 1)) * ph if valid else None,
            }
        initial = coords['w1'] if coords['w1']['valid'] else coords['w0']
        ix = initial['x'] if initial['valid'] else ml
        iy = initial['y'] if initial['valid'] else mt + ph
        d1, d0 = a['w1'], a['w0']
        color1 = qcolors.get(d1['quadrant'], '#978DA3')
        trend = ''
        if d0['roi'] is not None and d1['roi'] is not None and d0['new_rate'] is not None and d1['new_rate'] is not None:
            if d1['roi'] - d0['roi'] < -1 and d1['new_rate'] - d0['new_rate'] < -0.20:
                trend = ' trend-down'
            elif d1['roi'] - d0['roi'] > 1 and d1['new_rate'] - d0['new_rate'] > 0.20:
                trend = ' trend-up'
        circles += f'''<g class="matrix-point{trend}" transform="translate({ix:.1f} {iy:.1f})"
          data-name="{attr(a['name'])}" data-scene="{attr(a['scene'])}" data-cat="{attr(a['cat'])}"
          data-x0="{coords['w0']['x'] if coords['w0']['valid'] else ''}" data-y0="{coords['w0']['y'] if coords['w0']['valid'] else ''}" data-valid0="{int(coords['w0']['valid'])}"
          data-x1="{coords['w1']['x'] if coords['w1']['valid'] else ''}" data-y1="{coords['w1']['y'] if coords['w1']['valid'] else ''}" data-valid1="{int(coords['w1']['valid'])}"
          data-spend0="{d0['spend']}" data-roi0="{d0['roi'] if d0['roi'] is not None else ''}" data-new0="{d0['new_rate'] if d0['new_rate'] is not None else ''}" data-quadrant0="{attr(d0['quadrant'])}"
          data-spend1="{d1['spend']}" data-roi1="{d1['roi'] if d1['roi'] is not None else ''}" data-new1="{d1['new_rate'] if d1['new_rate'] is not None else ''}" data-quadrant1="{attr(d1['quadrant'])}"
          style="opacity:{1 if coords['w1']['valid'] else 0};pointer-events:{'auto' if coords['w1']['valid'] else 'none'}">
          <title>{attr(a['name'])}</title><circle r="12" fill="{color1}" opacity=".9"/><text y="4" text-anchor="middle" font-size="10" font-weight="800" fill="#fff">{idx}</text></g>'''
        for wk in ('w1', 'w0'):
            d = a[wk]
            if not d['active']:
                continue
            star = '※' if a['scene'] == '货品全站推广' else ''
            roi_text = f"{d['roi']:.2f}" if d['roi'] is not None else '—'
            new_text = f"{d['new_rate']*100:.1f}%" if d['new_rate'] is not None else '—'
            color = qcolors.get(d['quadrant'], '#978DA3')
            table_bodies[wk] += f'''<tr><td class="r">{idx}</td><td style="font-weight:600" title="{attr(a['name'])}">{html_lib.escape(cut(a['name'], 30))}</td>
              <td>{tag(a['cat'])}</td><td class="r">{money(d['spend'])}</td><td class="r">{roi_text}{star}</td>
              <td class="r">{new_text}</td><td><span class="matrix-tag" style="--q:{color}">{d['quadrant']}</span></td></tr>'''
        pending_counts['w0'] = pending_counts.get('w0', 0) + int(d0['active'] and not coords['w0']['valid'])
        pending_counts['w1'] = pending_counts.get('w1', 0) + int(d1['active'] and not coords['w1']['valid'])
    svg = f'''<svg class="matrix-svg" viewBox="0 0 {w} {h}" role="img" aria-label="推广计划波士顿矩阵">
      <rect x="{ml}" y="{mt}" width="{x_mid-ml:.1f}" height="{y_mid-mt:.1f}" fill="#FBF1DF"/>
      <rect x="{x_mid:.1f}" y="{mt}" width="{ml+pw-x_mid:.1f}" height="{y_mid-mt:.1f}" fill="#EFF6ED"/>
      <rect x="{ml}" y="{y_mid:.1f}" width="{x_mid-ml:.1f}" height="{mt+ph-y_mid:.1f}" fill="#FBEDEC"/>
      <rect x="{x_mid:.1f}" y="{y_mid:.1f}" width="{ml+pw-x_mid:.1f}" height="{mt+ph-y_mid:.1f}" fill="#F4EEF9"/>
      <line x1="{x_mid:.1f}" y1="{mt}" x2="{x_mid:.1f}" y2="{mt+ph}" stroke="#8F829C" stroke-dasharray="6 5"/>
      <line x1="{ml}" y1="{y_mid:.1f}" x2="{ml+pw}" y2="{y_mid:.1f}" stroke="#8F829C" stroke-dasharray="6 5"/>
      <line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#5D5568"/><line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#5D5568"/>
      <text x="{(ml+x_mid)/2:.1f}" y="{mt+19}" text-anchor="middle" font-size="16" font-weight="800" fill="#9A5D0B">拉新潜力</text>
      <text x="{(x_mid+ml+pw)/2:.1f}" y="{mt+19}" text-anchor="middle" font-size="16" font-weight="800" fill="#467A3C">明星计划</text>
      <text x="{(ml+x_mid)/2:.1f}" y="{mt+ph-12}" text-anchor="middle" font-size="16" font-weight="800" fill="#9B4A45">待调整</text>
      <text x="{(x_mid+ml+pw)/2:.1f}" y="{mt+ph-12}" text-anchor="middle" font-size="16" font-weight="800" fill="#592688">效率计划</text>
      <text x="{ml+pw/2:.1f}" y="{h-12}" text-anchor="middle" font-size="13" fill="#5D5568">ROI（中线=5）</text>
      <text x="17" y="{mt+ph/2:.1f}" text-anchor="middle" transform="rotate(-90 17 {mt+ph/2:.1f})" font-size="13" fill="#5D5568">新客率（中线=50%）</text>
      <text x="{x_mid+5:.1f}" y="{mt+ph+18}" font-size="11" fill="#978DA3">5</text><text x="{ml-30}" y="{y_mid+4:.1f}" font-size="11" fill="#978DA3">50%</text>
      {circles}</svg>'''
    period1 = f"{META['this']['start'][5:]}~{META['this']['end'][5:]}"
    period0 = f"{META['last']['start'][5:]}~{META['last']['end'][5:]}"
    controls = f'''<div class="matrix-controls" role="group" aria-label="选择计划矩阵周次">
      <button type="button" class="matrix-week active" data-week="w1" aria-pressed="true">本周 {period1}</button>
      <button type="button" class="matrix-week" data-week="w0" aria-pressed="false">上周 {period0}</button>
      <span class="matrix-hint">点击切换周次；红框=ROI 下降&gt;1 且新客率下降&gt;20pp，蓝框为相反方向的同幅度上升</span></div>'''
    table = (f'<table class="matrix-table"><thead><tr><th class="r">编号</th><th>计划</th><th>分类</th><th class="r">当周花费</th>'
             '<th class="r">ROI</th><th class="r">新客率</th><th>象限</th></tr></thead>'
             f'<tbody data-week="w1">{table_bodies["w1"]}</tbody><tbody data-week="w0" hidden>{table_bodies["w0"]}</tbody></table>')
    pending = (f'<div class="note matrix-pending" data-pending0="{pending_counts.get("w0", 0)}" '
               f'data-pending1="{pending_counts.get("w1", 0)}"></div>')
    return controls + f'<div class="matrix-shell">{svg}<div class="matrix-tooltip" role="tooltip"></div></div>' + table + pending


plan_matrix_html = matrix_html(PLAN_MATRIX)


def plan_value_rows(items):
    if not items:
        return '<tr><td colspan="7" class="na" style="text-align:center">无符合条件的计划</td></tr>'
    rows = ''
    for idx, a in enumerate(items, 1):
        score_color = '#9B4A45' if a['score'] < 0 else '#467A3C'
        rows += f'''<tr><td class="r">{idx}</td><td style="font-weight:600" title="{attr(a['name'])}">{html_lib.escape(cut(a['name'], 30))}</td>
          <td>{a['target_group']}</td><td class="r">{a['target_weight']:.1f}</td><td class="r">{money(a['revenue'])}</td>
          <td class="r">{a['new_rate'] * 100:.1f}%</td><td class="r" style="font-weight:800;color:{score_color}">{money(a['score'])}</td></tr>'''
    return rows


def plan_value_section(data):
    if not data:
        return ''
    formula = html_lib.escape(data['formula'])
    eligible = data.get('eligible_count', 0)
    excluded = data.get('excluded_count', 0)
    head = ('<thead><tr><th class="r">排名</th><th>计划</th><th>名称识别</th><th class="r">目标权重</th>'
            '<th class="r">推广收入</th><th class="r">新客率</th><th class="r">评价指标</th></tr></thead>')
    highlights = f'''<div class="card reveal"><h3>业务亮点 <span style="font-size:12px;font-weight:600;color:#978DA3">指标最高 3 个计划</span></h3>
      <table>{head}<tbody>{plan_value_rows(data.get('highlights', []))}</tbody></table></div>'''
    needs_adjustment = f'''<div class="card reveal"><h3>需要调整 <span style="font-size:12px;font-weight:600;color:#978DA3">评价指标 &lt; 0</span></h3>
      <table>{head}<tbody>{plan_value_rows(data.get('needs_adjustment', []))}</tbody></table></div>'''
    return f'''<div class="note" style="margin:14px 0 10px"><b>计划贡献评价（本周）：</b>{formula}。毛利要求率=50%，边际缓冲=0；名称识别 US猫/US狗/CN猫/CN狗的目标权重依次为 1.5/1.8/1.8/2.0。已计算 {eligible} 个计划，未命中名称分类或无新客率的 {excluded} 个计划不参与计算。</div>
      <div class="grid g2">{highlights}{needs_adjustment}</div>'''


plan_value_html = plan_value_section(PLAN_VALUE)

kw_cards = ''.join([
    cat_card('品牌词', KC['品牌词'], '个词/包', '（补充承接，主承接=品销宝）'),
    cat_card('竞品词', KC['竞品词'], '个词/包', '（按策略不投）'),
    cat_card('行业词', KC['行业词'], '个词/包'),
    cat_card('智能词包', KC['智能词包'], '个词/包'),
])
au_cards = ''.join([cat_card(c, AC[c], '个人群包') for c in ['品牌人群', '竞品人群', '行业人群']])

px_g4 = [('品牌搜索量', PX['w1']['搜索量'], PX['w0']['搜索量']), ('展现量', PX['w1']['展现量'], PX['w0']['展现量']),
         ('点击量', PX['w1']['点击量'], PX['w0']['点击量']), ('进店访客数', PX['w1']['进店访客数'], PX['w0']['进店访客数'])]
px_g4_html = ''.join(f'''  <div class="card kpi reveal"><div class="lab">{l}</div><div class="val">{countup(a, 'int')}<small> </small></div><div>{chip(a, b)}</div><div class="prev">上周：{b:,.0f}</div></div>\n''' for l, a, b in px_g4)
px_g3_html = f'''  <div class="card kpi reveal"><div class="lab">成交金额</div><div class="val">{countup(PX['w1']['成交金额'], 'wan1')}<small> 元</small></div><div>{chip(PX['w1']['成交金额'], PX['w0']['成交金额'])}</div><div class="prev">上周：{money(PX['w0']['成交金额'])} 元</div></div>
  <div class="card kpi reveal"><div class="lab">成交笔数</div><div class="val">{countup(PX['w1']['成交笔数'], 'int')}<small> 笔</small></div><div>{chip(PX['w1']['成交笔数'], PX['w0']['成交笔数'])}</div><div class="prev">上周：{PX['w0']['成交笔数']:,.0f} 笔</div></div>
  <div class="card kpi reveal"><div class="lab">客单价</div><div class="val">{countup(PX['w1']['客单价'], 'yuan1')}<small> 元</small></div><div>{chip(PX['w1']['客单价'], PX['w0']['客单价'])}</div><div class="prev">上周：{PX['w0']['客单价']:.1f} 元</div></div>'''

PROD_SKU = J['prod_sku']


def product_fee_chart(items):
    """所有 SKU 推广费比横向直方图；费比=花费÷总成交金额。"""
    items = [a for a in items if any((d['fee_ratio'] or 0) > 0 for d in (a['w0'], a['w1']))]
    current_ratios = [a['w1']['fee_ratio'] for a in items if a['w1']['fee_ratio'] is not None]
    all_ratios = [d['fee_ratio'] for a in items for d in (a['w0'], a['w1']) if d['fee_ratio'] is not None]
    scale = max(max(current_ratios or all_ratios, default=0), 0.10)
    rows = ''
    for a in items:
        d1, d0 = a['w1'], a['w0']
        r1, r0 = d1['fee_ratio'], d0['fee_ratio']
        w1 = min((r1 or 0) / scale * 100, 100)
        w0 = min((r0 or 0) / scale * 100, 100)
        cap1 = ' capped' if r1 is not None and r1 > scale else ''
        cap0 = ' capped' if r0 is not None and r0 > scale else ''
        v1 = f'{r1*100:.1f}%' if r1 is not None else '—'
        v0 = f'{r0*100:.1f}%' if r0 is not None else '—'
        title1 = f"本周｜花费 {money(d1['spend'])} 元｜成交 {money(d1['gmv'])} 元｜费比 {v1}"
        title0 = f"上周｜花费 {money(d0['spend'])} 元｜成交 {money(d0['gmv'])} 元｜费比 {v0}"
        rows += f'''<div class="sku-fee-row">
          <div class="sku-name" title="{attr(a['name'])}">{html_lib.escape(a['name'])}</div>
          <div class="sku-bars">
            <div class="sku-bar-line" title="{attr(title1)}"><span class="sku-period">本周</span><div class="sku-track"><i class="sku-bar this{cap1}" style="--w:{w1:.2f}%"></i></div><b>{v1}</b></div>
            <div class="sku-bar-line" title="{attr(title0)}"><span class="sku-period">上周</span><div class="sku-track"><i class="sku-bar last{cap0}" style="--w:{w0:.2f}%"></i></div><b>{v0}</b></div>
          </div>
        </div>'''
    axis_max = scale * 100
    axis = f'''<div class="sku-fee-axis"><span>0%</span><span>{axis_max*0.25:.1f}%</span><span>{axis_max*0.5:.1f}%</span><span>{axis_max*0.75:.1f}%</span><span>{axis_max:.1f}%</span></div>'''
    scale_note = f'<div class="note sku-scale-note">图轴上限按本周最高可计算费比 {axis_max:.1f}% 设置；上周超过该上限的条形封顶，右侧标签仍显示实际值。</div>'
    return f'<div class="sku-fee-chart">{axis}{rows}{scale_note}</div>'


prod_fee_chart_html = product_fee_chart(PROD_SKU)

# ---------------- 08 优化清单 ----------------
OPT = J.get('optimize', {'kw': [], 'au': [], 'plan': []})


def opt_table(items, kind):
    if not items:
        return '<div style="font-size:12.5px;color:#978DA3;padding:6px 0">本周无达花费门槛且 ROI<5 的对象。</div>'
    show_new_rate = kind in ('au', 'plan')
    has_plan_link = kind in ('kw', 'au')
    head = ('<thead><tr><th>名称</th><th>分类</th>'
            + ('<th>关联计划</th>' if has_plan_link else '')
            + '<th class="r">本周花费</th><th class="r">花费环比</th>'
            '<th class="r">本周ROI</th><th class="r">上周ROI</th>'
            + ('<th class="r">新客率³</th>' if show_new_rate else '')
            + '</tr></thead>')
    rows = ''
    for a in items:
        spc = chip(a['sp1'], a['sp0']) if a['sp0'] else '<span class="chip neu">新增</span>'
        if show_new_rate:
            nr_text = f"{a['new_rate']*100:.1f}%" if a.get('new_rate') is not None else '—'
            nr = f'<td class="r">{nr_text}</td>'
        else:
            nr = ''
        plan_links = ''
        if has_plan_link:
            plan_name = a.get('plan_name', '')
            if not plan_name:
                fail(f"优化清单的{a['name']}缺少关联计划", code=3)
            plan_links = f'<td class="opt-plan-links"><span title="{attr(plan_name)}">{html_lib.escape(plan_name)}</span></td>'
        rows += f'''<tr title="{a['name']} ｜ 本周成交 {money(a['g1'])} 元">
      <td style="font-weight:600"><span title="{a['name']}">{cut(a['name'], 26)}</span></td>
      <td>{tag(a['cat']) if a['cat'] else ''}</td>
      {plan_links}
      <td class="r">{money(a['sp1'])}</td>
      <td class="r">{spc}</td>
      <td class="r">{roi_span(a['roi1'])}</td>
      <td class="r">{roi_span2(a['roi0'])}</td>
      {nr}
    </tr>'''
    return f'<table>{head}<tbody>{rows}</tbody></table>'


def opt_card(kind, title, unit):
    items = [i for i in OPT[kind] if i['sp0'] > 0]
    sp = sum(i['sp1'] for i in items)
    return (f'<div class="card reveal"><h3>{title}'
            f'<span style="font-size:12px;font-weight:600;color:#978DA3;margin-left:8px">{len(items)} {unit}，合计 {wan(sp)} 元</span></h3>'
            + opt_table(items, kind) + '</div>')


opt_html = (opt_card('kw', '关键词', '个词') + '\n'
            + opt_card('au', '人群包', '个人群包') + '\n'
            + opt_card('plan', '计划', '个计划'))

# ---------------- 模板 CSS ----------------
css_src = os.environ.get('HALO_TEMPLATE_HTML')
if not css_src:
    cands = sorted(glob.glob(r'C:\Users\24190\Desktop\Halo站内推广周报_*.html'), key=os.path.getmtime, reverse=True)
    css_src = cands[0] if cands else None
if not css_src or not os.path.exists(css_src):
    fail('未找到模板 CSS 来源（桌面周报或 HALO_TEMPLATE_HTML 指定的文件）')
CSS = open(css_src, encoding='utf-8').read()
css = CSS[CSS.index('<style>') + 7:CSS.index('</style>')]
# 结构化结论列表样式（模板外追加，与 VI 变量保持一致）
css += '''
ul.take{margin:2px 0 0 2px;list-style:none}
ul.take li{padding:6px 0 6px 18px;position:relative;font-size:13px;border-bottom:1px dashed var(--border,#E9E3F0)}
ul.take li:last-child{border-bottom:none}
ul.take li::before{content:"";position:absolute;left:2px;top:13px;width:6px;height:6px;border-radius:50%;background:var(--orange,#CC7D11)}
.insight ul.take li b,.callout ul.take li b{white-space:nowrap}
.matrix-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 10px}
.matrix-week{appearance:none;border:1px solid #D9CFE3;background:#fff;color:#592688;border-radius:999px;padding:7px 14px;font-size:12.5px;font-weight:800;cursor:pointer;transition:.2s ease}
.matrix-week:hover{border-color:#592688}.matrix-week.active{background:#592688;color:#fff;border-color:#592688;box-shadow:0 5px 14px #59268828}
.matrix-hint{font-size:11.5px;color:#978DA3;margin-left:4px}
.matrix-shell{position:relative}.matrix-svg{display:block;width:100%;height:auto;margin:4px 0 14px;border:1px solid var(--border,#E9E3F0);border-radius:12px;background:#fff}
.matrix-point{cursor:help;transition:opacity .3s ease}.matrix-point circle{transition:fill .35s ease,stroke .2s ease;stroke:#fff;stroke-width:2}.matrix-point:hover circle{stroke:#2A2333;stroke-width:3}.matrix-point.trend-down circle,.matrix-point.trend-down:hover circle{stroke:#E53935;stroke-width:4}.matrix-point.trend-up circle,.matrix-point.trend-up:hover circle{stroke:#2979FF;stroke-width:4}
.matrix-tooltip{position:absolute;z-index:10;display:none;max-width:340px;padding:9px 11px;border-radius:9px;background:#2A2333;color:#fff;box-shadow:0 10px 28px #2A233344;font-size:12px;line-height:1.55;pointer-events:none;transform:translate(12px,12px)}
.matrix-tooltip b{display:block;font-size:12.5px;margin-bottom:2px}.matrix-tooltip.show{display:block}
.matrix-table tbody[hidden]{display:none}.matrix-pending:empty{display:none}
.matrix-tag{display:inline-block;padding:3px 7px;border-radius:999px;color:var(--q);background:color-mix(in srgb,var(--q) 10%,white);font-weight:800;white-space:nowrap}
.sku-fee-chart{--label:230px;margin-top:4px}.sku-fee-axis{margin-left:calc(var(--label) + 72px);display:flex;justify-content:space-between;color:#978DA3;font-size:10.5px;border-bottom:1px solid #E9E3F0;padding-bottom:4px}
.sku-fee-row{display:grid;grid-template-columns:var(--label) 1fr;gap:12px;align-items:center;padding:8px 0;border-bottom:1px dashed #E9E3F0}.sku-fee-row:last-child{border-bottom:none}
.sku-name{font-size:12.5px;font-weight:700;color:#2A2333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sku-bars{display:grid;gap:4px}
.sku-bar-line{display:grid;grid-template-columns:34px 1fr 54px;gap:6px;align-items:center;font-size:10.5px}.sku-period{color:#978DA3}.sku-bar-line b{text-align:right;font-variant-numeric:tabular-nums;color:#5D5568}
.sku-track{height:10px;border-radius:5px;background:repeating-linear-gradient(90deg,#F6F3F9 0,#F6F3F9 calc(25% - 1px),#E9E3F0 25%);overflow:hidden}.sku-bar{display:block;width:var(--w);height:100%;border-radius:5px;transition:width .7s ease}.sku-bar.this{background:linear-gradient(90deg,#592688,#8B5CB0)}.sku-bar.last{background:#C4BBD1}.sku-bar.capped{background-image:repeating-linear-gradient(135deg,transparent 0,transparent 4px,#CC7D11 4px,#CC7D11 7px)}
.sku-scale-note{margin-top:10px}
.opt-plan-links{min-width:176px;line-height:1.6;font-size:11.5px;color:#5D5568}.opt-plan-links span{display:inline-block;max-width:270px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:760px){.sku-fee-chart{--label:130px}.sku-fee-axis{margin-left:calc(var(--label) + 58px)}.sku-bar-line{grid-template-columns:28px 1fr 44px}.matrix-hint{width:100%;margin-left:0}}
'''

js = '''<script>
(function(){
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(e.isIntersecting){
        e.target.classList.add('in');
        io.unobserve(e.target);
        e.target.querySelectorAll('.countup').forEach(runCount);
      }
    });
  },{threshold:.12});
  document.querySelectorAll('.reveal, section').forEach(function(el){io.observe(el);});
  function fmt(v,f){
    if(f==='wan1') return (v/10000).toFixed(1)+'万';
    if(f==='wan2') return (v/10000).toFixed(2)+'万';
    if(f==='int') return Math.round(v).toLocaleString('en-US');
    if(f==='f2') return v.toFixed(2);
    if(f==='pct') return v.toFixed(2)+'%';
    if(f==='yuan1') return v.toFixed(1);
    return String(v);
  }
  function runCount(el){
    if(el.dataset.done) return; el.dataset.done='1';
    var v=parseFloat(el.dataset.v), f=el.dataset.f, t0=null, dur=900;
    function step(t){
      if(!t0) t0=t;
      var p=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-p,3);
      el.textContent=fmt(v*e,f);
      if(p<1) requestAnimationFrame(step); else el.textContent=fmt(v,f);
    }
    requestAnimationFrame(step);
  }
  var matrixWeek='w1';
  var quadrantColors={'明星计划':'#467A3C','效率计划':'#592688','拉新潜力':'#CC7D11','待调整':'#9B4A45','待观察':'#978DA3'};
  function animateMatrixPoint(el,x,y){
    if(el._matrixRaf) cancelAnimationFrame(el._matrixRaf);
    var m=(el.getAttribute('transform')||'').match(/translate\\(([-\\d.]+)[ ,]+([-\\d.]+)\\)/);
    var sx=m?parseFloat(m[1]):x,sy=m?parseFloat(m[2]):y,start=performance.now(),dur=720;
    function tick(now){
      var p=Math.min(1,(now-start)/dur),e=1-Math.pow(1-p,3);
      el.setAttribute('transform','translate('+(sx+(x-sx)*e).toFixed(1)+' '+(sy+(y-sy)*e).toFixed(1)+')');
      if(p<1) el._matrixRaf=requestAnimationFrame(tick);
    }
    el._matrixRaf=requestAnimationFrame(tick);
  }
  function setMatrixWeek(week){
    matrixWeek=week;var n=week.slice(1);
    document.querySelectorAll('.matrix-week').forEach(function(b){var on=b.dataset.week===week;b.classList.toggle('active',on);b.setAttribute('aria-pressed',on?'true':'false');});
    document.querySelectorAll('.matrix-table tbody').forEach(function(tb){tb.hidden=tb.dataset.week!==week;});
    document.querySelectorAll('.matrix-point').forEach(function(p){
      var valid=p.dataset['valid'+n]==='1';
      if(valid){
        var x=parseFloat(p.dataset['x'+n]),y=parseFloat(p.dataset['y'+n]);
        animateMatrixPoint(p,x,y);p.style.opacity='1';p.style.pointerEvents='auto';
        p.querySelector('circle').setAttribute('fill',quadrantColors[p.dataset['quadrant'+n]]||'#978DA3');
      }else{p.style.opacity='0';p.style.pointerEvents='none';}
    });
    var note=document.querySelector('.matrix-pending');
    if(note){var count=parseInt(note.dataset['pending'+n]||'0',10);note.textContent=count?'当周有 '+count+' 个计划因成交人数为 0 无法计算新客率，暂列待观察且不显示矩阵点。':'';}
    var tip=document.querySelector('.matrix-tooltip');if(tip)tip.classList.remove('show');
  }
  document.querySelectorAll('.matrix-week').forEach(function(b){b.addEventListener('click',function(){setMatrixWeek(b.dataset.week);});});
  document.querySelectorAll('.matrix-point').forEach(function(p){
    var shell=p.closest('.matrix-shell'),tip=shell&&shell.querySelector('.matrix-tooltip');
    function tooltipText(){
      var n=matrixWeek.slice(1),roi=p.dataset['roi'+n],nr=p.dataset['new'+n],sp=parseFloat(p.dataset['spend'+n]||'0');
      return {name:p.dataset.name,meta:(matrixWeek==='w1'?'本周':'上周')+'｜'+p.dataset.scene+'｜'+p.dataset.cat,
        value:'ROI '+(roi?Number(roi).toFixed(2):'—')+'｜新客率 '+(nr?(Number(nr)*100).toFixed(1)+'%':'—')+'｜花费 '+sp.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})+' 元｜'+p.dataset['quadrant'+n]};
    }
    p.addEventListener('mouseenter',function(){if(!tip)return;var t=tooltipText();tip.textContent='';var b=document.createElement('b');b.textContent=t.name;var m=document.createElement('div');m.textContent=t.meta;var v=document.createElement('div');v.textContent=t.value;tip.append(b,m,v);tip.classList.add('show');});
    p.addEventListener('mousemove',function(e){if(!tip||!shell)return;var r=shell.getBoundingClientRect(),left=Math.min(e.clientX-r.left+12,Math.max(8,r.width-350));tip.style.left=left+'px';tip.style.top=(e.clientY-r.top+12)+'px';});
    p.addEventListener('mouseleave',function(){if(tip)tip.classList.remove('show');});
  });
  setMatrixWeek('w1');
  var links=Array.prototype.slice.call(document.querySelectorAll('.nav a'));
  var map={};
  links.forEach(function(a){var id=a.getAttribute('href').slice(1);if(document.getElementById(id))map[id]=a;});
  var spy=new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(e.isIntersecting){
        links.forEach(function(a){a.classList.remove('act');});
        var a=map[e.target.id]; if(a) a.classList.add('act');
      }
    });
  },{rootMargin:'-25% 0px -65% 0px'});
  Object.keys(map).forEach(id=>spy.observe(document.getElementById(id)));
})();
</script>'''

d1s = META['this']['start'][5:].replace('-', '-')
d1e = META['this']['end'][5:]
d0s = META['last']['start'][5:]
d0e = META['last']['end'][5:]
period_title = META['this']['start'] + '至' + META['this']['end'][5:].replace('-', '')
out_path = args.out or os.path.join(r'C:\Users\24190\Desktop', f'Halo站内推广周报_{period_title}.html')
html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Halo自然光环 · 站内推广周报 {META['this']['start']}至{META['this']['end']}</title><style>{css}</style></head><body>
<div class="hero"><div class="wrap">
  <div><span class="pill">本周 {d1s.replace('-', '-')}~{d1e} vs 上周 {d0s}~{d0e} 环比</span><span class="pill">万相台无界 + 品销宝</span></div>
  <h1 style="margin-top:12px">Halo 自然光环 · 站内推广周度汇报</h1>
  <div class="sub">数据周期 {META['this']['start']} 至 {META['this']['end']} ｜ 关键词 / 人群 / 货品全站 / 短视频 / 直播 + 品销宝 ｜ 金额单位：人民币元</div>
  <div class="prod">出品：Halo中国 ｜ 模型：{MODEL}</div>
</div></div>
<div class="nav"><div class="wrap">
  <a href="#overview">核心总览</a><a href="#brandzone">品销宝</a><a href="#scene">营销场景</a><a href="#plan">计划矩阵</a><a href="#keyword">关键词</a><a href="#audience">人群</a><a href="#product">商品主体</a><a href="#optimize">优化清单</a>
</div></div>
<div class="wrap">

<section id="overview" style="padding-top:36px"><div class="shead reveal"><div class="overline">01 · OVERVIEW</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13h4v8H3zM10 8h4v13h-4zM17 3h4v18h-4z"/></svg>核心总览</h2><div class="h2sub">万相台无界全场景合计（关键词 + 人群 + 货品全站 + 短视频/直播）；成交新客、收藏加购为分场景合计口径（未跨场景去重）</div></div>
<div class="grid g5">
{kpi_html}</div>
</section>

<section id="brandzone"><div class="shead reveal"><div class="overline">02 · BRAND ZONE</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l4 4 5-7 5 7 4-4v9H3z"/></svg>品销宝（品牌专区）</h2><div class="h2sub">品牌词的主要承接阵地；品销宝花费不在源表口径内，不计算 ROI</div></div>
<div class="grid g4">
{px_g4_html}</div>
<div class="grid g3" style="margin-top:14px">
{px_g3_html}
</div>
{render_insight(INS['brandzone'], exclude_titles=('承接',))}
</section>

<section id="scene"><div class="shead reveal"><div class="overline">03 · SCENES</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/></svg>营销场景表现</h2><div class="h2sub">条形为花费规模（灰=上周，紫=本周）；※ 货品全站推广成交含免费流量部分，其 ROI 与纯付费场景不可直接对比，仅作参考</div></div>
<div class="card reveal">
<table>
<thead><tr><th>场景</th><th>花费对比</th><th class="r">本周花费(元)</th><th class="r">花费环比</th><th class="r">本周成交(元)</th><th class="r">成交环比</th><th class="r">本周ROI</th><th class="r">上周ROI</th><th class="r">ROI环比</th><th class="r">本周CPC</th><th class="r">本周CTR</th><th class="r">新客率(本周)</th></tr></thead>
<tbody>{scene_rows}</tbody>
</table>
<div class="legend"><span><i style="background:#592688"></i>本周</span><span><i style="background:#C4BBD1"></i>上周</span></div>
{render_insight(INS['scene'], exclude_titles=('调整方向', '建议', '行动建议'))}
</div>
</section>

<section id="plan"><div class="shead reveal"><div class="overline">04 · CAMPAIGN MATRIX</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1.2"/><circle cx="4" cy="12" r="1.2"/><circle cx="4" cy="18" r="1.2"/></svg>推广计划波士顿矩阵</h2><div class="h2sub">以计划为评价中心：横轴 ROI（中线=5），纵轴新客率（中线=50%）；※ 全站推广成交含免费流量，ROI 仅作参考</div></div>
<div class="card reveal">
{plan_matrix_html}
{plan_value_html}
{render_insight(INS['plan'], exclude_titles=('调整方向', '建议', '行动建议'))}
</div>
</section>

<section id="keyword"><div class="shead reveal"><div class="overline">05 · KEYWORDS</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>关键词</h2><div class="h2sub">保留品牌词/竞品词/行业词/智能词包宏观统计；后续诊断围绕计划矩阵中的问题计划提出关键词调整方向</div></div>
<div class="grid g4">{kw_cards}</div>
<div class="card reveal" style="margin-top:14px">
<h3>计划导向诊断</h3>
<div class="note">ROI&lt;5 优化清单直接使用本周关键词报表的计划ID、计划名字，按“关键词 + 具体计划”逐行展示。</div>
{render_insight(INS['keyword'], exclude_titles=('调整方向', '建议', '行动建议'))}
</div>
</section>

<section id="audience"><div class="shead reveal"><div class="overline">06 · AUDIENCES</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3-5.5 5.5-5.5s4.7 2 5.5 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14.6c2.6.3 4.5 2.2 5.1 5.4"/></svg>人群</h2><div class="h2sub">保留品牌/竞品/行业人群宏观统计；后续诊断围绕计划矩阵中的问题计划提出人群调整方向</div></div>
<div class="grid g3">{au_cards}</div>
<div class="card reveal" style="margin-top:14px">
<h3>计划导向诊断</h3>
<div class="note">ROI&lt;5 优化清单直接使用本周人群报表的计划ID、计划名字，按“人群 + 具体计划”逐行展示。</div>
<div class="note" style="margin-top:10px"><b>人群包评价标准（8 月方案）：</b>合格线 = 单项 ROI≥5；<b>拉新类包</b>需同时满足 新客率≥50% 且 ROI≥5；<b>竞品拦截人群</b>按「首单转化率 + 新客客单价 + 30 天复购率」三件套评估（周报以新客率/新客成本代理），不单看短期 ROI；<b>品牌资产人群</b>看 ROI 与承接客单价。</div>
{render_insight(INS['audience'], 'callout', ('调整方向', '建议', '行动建议'))}
</div>
</section>

<section id="product"><div class="shead reveal"><div class="overline">07 · PRODUCTS</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l9-5 9 5v8l-9 5-9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>商品主体 · SKU 费比</h2><div class="h2sub">展示商品报表全部 SKU；推广费比 = 花费 ÷ 总成交金额，本周与上周并列显示；成交金额为 0 时记为“—”</div></div>
<div class="card reveal">
{prod_fee_chart_html}
{render_insight(INS['product'], exclude_titles=('调整方向', '建议', '行动建议'))}
</div>
</section>

<section id="optimize"><div class="shead reveal"><div class="overline">08 · OPTIMIZE</div><h2><svg class="sic" viewBox="0 0 24 24" fill="none" stroke="#592688" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4.5 4.5 0 0 0-6.1 5.6L3 17.4V21h3.6l5.5-5.6a4.5 4.5 0 0 0 5.6-6.1l-2.6 2.6-2.1-2.1 2.6-2.6z"/></svg>ROI&lt;5 优化清单</h2><div class="h2sub">判定标准（8 月方案）：单项合格线 ROI≥5；以下为本周花费≥500 元（词）/≥1,000 元（人群、计划）且 ROI&lt;5 的对象</div></div>
{opt_html}
<div class="note">³ 新客率 = 成交新客数 ÷ 成交人数（人群维度口径）；人群包按分类适用不同评价标准——拉新类包需 新客率≥50% 且 ROI≥5；竞品拦截人群以三件套评估、新客率作代理指标；品牌人群看 ROI 与承接客单价。</div>
<div class="callout" style="margin-top:12px">{INS['optimize']}</div>
</section>

<div class="footer">Halo 自然光环 · 站内推广周度汇报 ｜ {META['this']['start']} 至 {META['this']['end']} ｜ 出品：Halo中国 ｜ 模型：{MODEL} ｜ 品牌配色遵循 Halo VI GUIDE 2025</div>
</div>
{js}</body></html>'''

open(out_path, 'w', encoding='utf-8').write(html)
json.dump({'ok': True, 'out': out_path, 'bytes': len(html.encode('utf-8'))}, sys.stdout, ensure_ascii=False)
print()
