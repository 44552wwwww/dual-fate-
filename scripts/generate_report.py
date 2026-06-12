#!/usr/bin/env python3
"""
命运双鉴 · 统一生成器
用法: python generate_report.py <年> <月> <日> <时> <性别>
输出: 自包含HTML文件
"""
import sys, io, json, os, re, html as html_mod
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from bazi_calculator import compute_bazi
from ziwei_calculator import compute_ziwei

# ═══════════════════════════════════════
# HTML BUILDER HELPERS
# ═══════════════════════════════════════
def tag(name, cls='', style='', **attrs):
    a = ' '.join(f'{k}="{v}"' for k,v in attrs.items())
    return f'<{name} class="{cls}" style="{style}" {a}>' if cls or style or attrs else f'<{name}>'

def div(cls='', style='', **kw): return tag('div',cls,style,**kw)
def _d(s): return f'</{s}>'
def card(title, icon, verdict, vc, detail, source):
    bc = {'good':'74,222,128','warn':'232,93,117','ok':'201,169,110'}.get(vc,'201,169,110')
    return f'''<div class="vc" style="border-color:rgba({bc},0.2);">
    <div class="vc-icon">{icon}</div><h3>{title}</h3>
    <div class="big {vc}">{verdict}</div>
    <div class="detail">{detail}</div><div class="source">{source}</div></div>'''

def derivation(obs, principle, conclusion):
    return f'<div class="der"><div class="der-obs">🔍 {obs}</div><div class="der-princ">📜 {principle}</div><div class="der-conc">💡 {conclusion}</div></div>'

def fold_section(title, content, open=False):
    return f'''<div class="fold">
    <div class="fold-hd{(' open' if open else '')}" onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
    <h3>{title}</h3><span class="arr">▼</span></div>
    <div class="fold-bd{(' open' if open else '')}">{content}</div></div>'''

def wx_dot(wx):
    c = {'木':'4ade80','火':'f97316','土':'a78b5a','金':'e2e8a0','水':'38bdf8'}.get(wx,'888')
    return f'<span class="wx-d" style="background:#{c}"></span>{wx}'

# ═══════════════════════════════════════
# BAZI HTML GENERATION
# ═══════════════════════════════════════
def gen_bazi_html(bz):
    p = bz['四柱']; ss = bz['十神标注']; wx = bz['五行分布']
    yong = bz['用神分析']['用神']; ji = bz['用神分析']['忌神']
    riGan = bz['日主']['天干']; riWx = bz['日主']['五行']; sq = bz['用神分析']['身强身弱']
    sex = bz['输入']['性别']; dy = bz['大运']

    # --- Summary cards ---
    cards = ''
    cd = _bazi_card_data(bz)
    for c in cd:
        tags_html = ''.join(f'<span class="tg {t["c"]}">{t["t"]}</span>' for t in c['tags'])
        cards += card(c['title'], c['icon'], c['verdict'], c['vc'], c['reason'], '') + '\n'

    # --- Chart table ---
    chart = '<table class="pillars-table"><tr><th></th><th>年柱</th><th>月柱</th><th>日柱</th><th>时柱</th></tr>'
    for row_name, keys in [("天干",["天干","天干五行","天干十神"]),("地支",["地支","地支五行","藏干"]),("纳音",["纳音"]),("十二长生",["日主十二长生在此"])]:
        chart += f'<tr><td class="lbl">{row_name}</td>'
        for col in ["年柱","月柱","日柱","时柱"]:
            if row_name=="天干":
                dm = ' day-master' if col=="日柱" else ''
                chart += f'<td class="gz{dm}">{p[col]["天干"]} {wx_dot(p[col]["天干五行"])}<br><small>{ss[col]["天干十神"]}</small></td>'
            elif row_name=="地支":
                cg = '·'.join(p[col]["藏干"])
                chart += f'<td>{p[col]["地支"]} {wx_dot(p[col]["地支五行"])}<br><small>{cg}</small></td>'
            elif row_name=="纳音":
                chart += f'<td>{p[col]["纳音"]}</td>'
            else:
                chart += f'<td>{p[col]["日主十二长生在此"]}</td>'
        chart += '</tr>'
    chart += '</table>'

    # --- Wuxing bar ---
    wx_total = sum(wx.values())
    wx_bar = '<div class="wx-bar">'
    for w, c in [("木","4ade80"),("火","f97316"),("土","a78b5a"),("金","e2e8a0"),("水","38bdf8")]:
        pct = wx.get(w,0)/wx_total*100 if wx_total else 0
        if pct>0: wx_bar += f'<div style="width:{pct:.0f}%;background:#{c}"></div>'
    wx_bar += '</div><div class="wx-lab">'
    for w in ["木","火","土","金","水"]: wx_bar += f'<span>{wx_dot(w)} {wx.get(w,0)} ({wx.get(w,0)/wx_total*100:.0f}%)</span> '
    wx_bar += '</div>'

    # --- Yong Shen ---
    yong_ji_html = f'<div class="box"><p>身强身弱：<strong>{sq}</strong>（日主力量 {bz["用神分析"]["日主力量占比"]}）</p><p>用神：<span class="green">{"/".join(yong)}</span></p><p>忌神：<span class="red">{"/".join(ji)}</span></p>'
    if bz['用神分析']['调候需求']: yong_ji_html += f'<p>调候：{bz["用神分析"]["调候需求"]}</p>'
    yong_ji_html += '</div>'

    # --- Conflicts ---
    cf_html = ''
    for c in bz['地支关系']['冲突列表']:
        cf_html += f'<div class="box" style="margin-bottom:4px;"><span class="red">[{c["关系"]}]</span> {c["涉及"]} · {c["原理"]}</div>'

    # --- Analysis sections ---
    analysis = _bazi_analysis(bz)

    # --- Dayun ---
    dayun_html = '<div class="dy-row">'
    for d in dy['大运列表']:
        is_y = d['天干五行'] in yong; is_j = d['天干五行'] in ji
        cls = 'dy-y' if is_y else ('dy-j' if is_j else '')
        label = '用神运' if is_y else ('忌神运' if is_j else '平运')
        lc = 'var(--green)' if is_y else ('var(--red)' if is_j else '#888')
        dayun_html += f'<div class="dy-s {cls}"><div class="dy-a">{d["年龄段"]}</div><div class="dy-g">{d["干支"]}</div><div style="font-size:0.7em;color:{lc}">{label}</div></div>'
    dayun_html += '</div>'
    dayun_html += f'<p style="color:#888;margin:8px 0;">{dy["起运年龄"]}岁起运 · {dy["排法"]}</p>'
    for d in dy['大运列表']:
        is_y = d['天干五行'] in yong; is_j = d['天干五行'] in ji
        note = f'{d["天干五行"]}为用神→此运顺遂' if is_y else (f'{d["天干五行"]}为忌神→此运多阻' if is_j else '平运，靠自身努力')
        dayun_html += fold_section(f'{d["年龄段"]} · {d["干支"]} ({d["天干五行"]}+{d["地支五行"]})', f'<p>{note}</p>')

    # --- Assemble ---
    return f'''
    <div class="sum">{cards}</div>
    <h2 class="sh">📊 八字排盘</h2>
    {chart}
    <h2 class="sh">📐 五行力量</h2>
    {wx_bar}
    <h2 class="sh">🎯 用神忌神</h2>
    {yong_ji_html}
    <h2 class="sh">⚡ 地支关系</h2>
    {cf_html if cf_html else '<div class="box">无明显冲合刑害</div>'}
    <h2 class="sh">📋 命理推导</h2>
    {analysis}
    <h2 class="sh">⏳ 大运走势</h2>
    {dayun_html}
    '''

def _bazi_card_data(bz):
    p = bz['四柱']; wx = bz['五行分布']; y = bz['用神分析']['用神']; j = bz['用神分析']['忌神']
    g = bz['日主']['天干']; sq = bz['用神分析']['身强身弱']; sex = bz['输入']['性别']
    d = {'甲':'正直有领导力，直率固执','乙':'柔韧细腻，优柔寡断','丙':'热情光明，急躁爱面子','丁':'温和执着，内敛有心机','戊':'厚重诚信，保守稳重','己':'包容温和，多疑能忍','庚':'刚强果断，讲义气冲动','辛':'精致挑剔，有品位要面子','壬':'聪明通融，任性善变','癸':'细腻敏感，内向多情'}
    cs = [v['天干十神'] for v in bz['十神标注'].values()]
    target = '正官' if sex=='女' else '正财'; tn = '夫星' if sex=='女' else '妻星'
    has_target = target in cs; has_jc = '劫财' in cs
    weak = [w for w,c in wx.items() if c<=1]; strong = [w for w,c in wx.items() if c>=7]
    m = {'木':'肝胆/筋骨','火':'心血管/眼睛','土':'脾胃/消化','金':'肺/呼吸道','水':'肾/泌尿'}
    dirs = {'木':'东','火':'南','土':'中','金':'西','水':'北'}; cols = {'木':'青绿','火':'红紫','土':'黄棕','金':'白','水':'黑蓝'}
    good_dy = [d for d in bz['大运']['大运列表'] if d['天干五行'] in y]
    return [
        {'icon':'🧠','title':'性格','verdict':f'日主{g}({bz["日主"]["五行"]})，{sq}','vc':'ok',
         'reason':f'日主<em>{g}</em>→{d.get(g,"")}。{sq}。',
         'tags':[{'t':d.get(g,"")[:6],'c':'tag-good'},{'t':sq,'c':'tag-tip'}]},
        {'icon':'💰','title':'财运','verdict':'财星透出有机遇' if ('正财' in cs or '偏财' in cs) else '靠技能求财','vc':'ok',
         'reason':f'财星{"已透干" if ("正财" in cs or "偏财" in cs) else "不显"}。{"有劫财→注意破财。" if has_jc else ""}用神{"/".join(y)}行业最利。',
         'tags':[{'t':f'用{"·".join(y[:2])}','c':'tag-good'},{'t':'慎合伙' if has_jc else '稳求财','c':'tag-tip'}]},
        {'icon':'💍','title':'婚姻','verdict':f'{tn}{"有气" if has_target else "偏弱"}','vc':'ok' if has_target else 'warn',
         'reason':f'{sex}命以{target}为{tn}。{target}{"透出→配偶缘分不错。" if has_target else "不显→需大运流年引动。"}配偶宫日支为{p["日柱"]["地支"]}。',
         'tags':[{'t':f'{tn}有气' if has_target else '宜晚婚','c':'tag-good' if has_target else 'tag-tip'}]},
        {'icon':'🏥','title':'健康','verdict':f'{"·".join(strong)}偏旺' if strong else f'{"·".join(weak)}偏弱' if weak else '相对平衡','vc':'warn' if (strong or weak) else 'good',
         'reason':f'{"过旺："+"; ".join(f"{w}({m[w]})" for w in strong)+"。 " if strong else ""}{"偏弱："+"; ".join(f"{w}({m[w]})" for w in weak)+"。 " if weak else ""}定期体检，注意作息。',
         'tags':[{'t':f'注意{m[w]}' if (w:= (strong[0] if strong else weak[0] if weak else None)) else '保持','c':'tag-bad' if (strong or weak) else 'tag-good'}]},
        {'icon':'⏳','title':'运势','verdict':f'{good_dy[0]["年龄段"]}为黄金期' if good_dy else '各运起伏','vc':'ok',
         'reason':f'{bz["大运"]["起运年龄"]}岁起运{bz["大运"]["排法"]}。用神运：{"、".join(d["年龄段"] for d in good_dy[:3]) if good_dy else "无显著用神运"}。',
         'tags':[{'t':f'黄金期：{good_dy[0]["年龄段"]}' if good_dy else '把握各运','c':'tag-good'},{'t':'忌神运保守','c':'tag-tip'}]},
        {'icon':'🎯','title':'指南','verdict':f'用{"/".join(y)} · 忌{"/".join(j)}','vc':'ok',
         'reason':f'方位{"/".join(dirs[w] for w in y)}。颜色{"/".join(cols[w] for w in y)}。行业优先{"/".join(y)}属性。收敛急躁，婚姻示弱，拒绝合伙。',
         'tags':[{'t':f'用{"·".join(y)}','c':'tag-good'},{'t':f'忌{"·".join(j)}','c':'tag-bad'}]},
    ]

def _bazi_analysis(bz):
    p = bz['四柱']; wx = bz['五行分布']; y = '、'.join(bz['用神分析']['用神']); j = '、'.join(bz['用神分析']['忌神'])
    g = bz['日主']['天干']; rw = bz['日主']['五行']; sq = bz['用神分析']['身强身弱']; sex = bz['输入']['性别']; dy = bz['大运']
    target = '正官' if sex=='女' else '正财'; tn = '夫星' if sex=='女' else '妻星'
    m = {'木':'肝胆/筋骨','火':'心血管/眼睛','土':'脾胃/消化','金':'肺/呼吸道','水':'肾/泌尿'}
    wx_desc = '；'.join(f'{w}={c}({m.get(w,"")})' for w,c in sorted(wx.items(), key=lambda x:-x[1]))
    cs = [v['天干十神'] for v in bz['十神标注'].values()]
    has_target = target in cs
    good_dy = [d for d in dy['大运列表'] if d['天干五行'] in bz['用神分析']['用神']]

    secs = [
        ('🔍 一、日主强弱', f'{g}({rw})生于{p["月柱"]["地支"]}月。{rw}在月令处状态+地支根气+生扶数量综合分析→<strong>{sq}</strong>。'),
        ('🎯 二、用神忌神', f'{sq}需{"克泄耗" if "强" in sq else "生扶"}来平衡。结合调候→用神<strong>{y}</strong>，忌神<strong>{j}</strong>。'),
        ('🧠 三、性格', f'日主{g}({rw})五行定性+十神组合补充。印旺者仁厚，官旺者自律，食伤旺者聪慧，比劫旺者好胜。'),
        (f'💍 四、婚姻({sex}命)', f'{sex}命以{target}为{tn}。{tn}{"透出→配偶缘分不差" if has_target else "不显→大运流年引动"}。配偶宫日支{p["日柱"]["地支"]}决定婚姻稳定性。'),
        ('💰 五、事业财运', f'财星透干有根→求财机会；食伤生财→技能变现；比劫夺财→破财风险。适合{"/".join(bz["用神分析"]["用神"][:2])}属性行业。'),
        ('🏥 六、健康', f'五行配五脏：{wx_desc}。过旺或过弱的五行对应脏腑需多加关注。'),
        ('⏳ 七、大运', f'{dy["起运年龄"]}岁起运{dy["排法"]}。用神运：{"、".join(d["年龄段"] for d in good_dy[:3]) if good_dy else "各运起伏"}。用神运积极进取，忌神运保守。'),
    ]
    html = ''
    for title, desc in secs:
        html += fold_section(title, f'<p style="color:#bbb;line-height:1.8;">{desc}</p>')
    return html

# ═══════════════════════════════════════
# ZIWEI HTML GENERATION
# ═══════════════════════════════════════
def gen_ziwei_html(zw):
    gongs = zw['十二宫']; sex = zw['输入']['性别']

    # --- Palace grid ---
    # Traditional layout: 巳午未申 / 辰__酉 / 卯__戌 / 寅丑子亥
    order = ['巳','午','未','申','辰',None,None,'酉','卯',None,None,'戌','寅','丑','子','亥']
    gong_by_zhi = {g['地支']:g for g in gongs}
    grid = '<div class="zw-grid">'
    for z in order:
        if z is None:
            grid += f'<div class="zw-c"><div class="zw-ctr">☯ 紫微斗数<br><small>命宫·{zw["命宫"]}<br>身宫·{zw["身宫"]}<br>{zw["五行局"]}<br>紫微在{zw["紫微星在"]}</small></div></div>'
        else:
            g = gong_by_zhi.get(z)
            if g:
                is_empty = len(g['主星'])==0
                mjr = ''.join(f'<span class="st-mjr{" mi" if s["庙旺"]=="庙旺" else ""}">{s["星名"]}</span>' for s in g['主星'])
                aux = ''.join(f'<span class="st-{"ji" if s["类型"]=="吉" else "sha" if s["类型"]=="煞" else "za"}">{"☆" if s["类型"]=="吉" else "▲" if s["类型"]=="煞" else "◇"}{s["星名"]}</span>' for s in g['辅星'])
                si = ''.join(f'<span class="st-si">{s["化星"]}</span>' for s in g['四化'])
                grid += f'''<div class="zw-p{(' empty' if is_empty else '')}">
                <div class="zw-pn">{g["宫名"]}<span class="zw-pz">{g["干支"]}</span></div>
                <div class="zw-st">{mjr if mjr else '<span class="dim">(空宫)</span>'}</div>
                <div class="zw-st">{aux}</div>
                <div class="zw-st">{si}</div>
                <div class="zw-dx">{g["大限"] or ''}</div></div>'''
    grid += '</div>'

    # --- Sihua banner ---
    sh = zw['四化']
    hua_cls = {'化禄':('lu','🟢'),'化权':('quan','🟣'),'化科':('ke','🔵'),'化忌':('ji','🔴')}
    sihua_html = '<div class="sh-ban">'
    for hn, sn in sh.items():
        cls, em = hua_cls.get(hn,('',''))
        # Find which gong
        gn = '?'
        for g in gongs:
            if any(s['化星']==hn for s in g['四化']): gn = g['宫名']; break
        sihua_html += f'<div class="sh-c sh-{cls}"><div class="sh-l">{em} {hn}</div><div>{sn}</div><div class="dim" style="font-size:0.7em;">在{gn}</div></div>'
    sihua_html += '</div>'

    # --- Summary cards ---
    cards = _ziwei_cards(zw)

    # --- Analysis ---
    analysis = _ziwei_analysis(zw)

    # --- Daxian ---
    dx_html = ''
    for dx in zw['大限']['大限列表']:
        g = next((g for g in gongs if g['宫名']==dx['宫位']), None)
        stars = ', '.join(s['星名'] for s in g['主星']) if g and g['主星'] else '空宫'
        dx_html += fold_section(f'{dx["年龄段"]} · {dx["宫位"]}({dx["地支"]})', f'<p>宫内：{stars}</p>')

    # --- Assemble ---
    return f'''
    {sihua_html}
    {grid}
    <h2 class="sh">💬 白话解读</h2>
    <div class="sum">{cards}</div>
    <h2 class="sh">📋 宫位分析</h2>
    {analysis}
    <h2 class="sh">⏳ 大限走势</h2>
    <p style="color:#888;margin-bottom:8px;">{zw["大限"]["排法"]}</p>
    {dx_html}
    '''

def _ziwei_cards(zw):
    gongs = zw['十二宫']; sex = zw['输入']['性别']
    def find(name):
        for g in gongs:
            if g['宫名']==name: return g
        return None
    fugong = find('夫妻宫'); caibogong = find('财帛宫'); qianyi = find('迁移宫')
    jiqiong = find('疾厄宫'); zinv = find('子女宫'); minggong = find('命宫'); guanlu = find('官禄宫')
    def stars(g): return ', '.join(s['星名'] for s in g['主星']) if g and g['主星'] else '空宫'
    def sihua(g): return ', '.join(s['化星'] for s in g['四化']) if g and g['四化'] else '无'
    def aux_good(g): return sum(1 for s in g['辅星'] if s['类型']=='吉') if g else 0

    cards = []
    # Marriage
    f_good = fugong and len(fugong['主星'])>0
    cards.append({'title':'💍 婚姻','verdict':'配偶素质不错' if f_good else '婚姻需更多经营','vc':'good' if f_good else 'ok',
                  'detail':f'夫妻宫{fugong["干支"] if fugong else "?"}。主星：<em>{stars(fugong)}</em>。四化：{sihua(fugong)}。{"庙旺状态佳" if f_good else ""}',
                  'tags':[{'t':'配偶素质好' if f_good else '需经营','c':'tag-good' if f_good else 'tag-tip'}]})
    # Wealth
    cb_good = caibogong and any('化禄' in s['化星'] for s in caibogong['四化'])
    cards.append({'title':'💰 财运','verdict':'财源有信号' if cb_good else '财运需努力','vc':'good' if cb_good else 'ok',
                  'detail':f'财帛宫{caibogong["干支"] if caibogong else "?"}。主星：<em>{stars(caibogong)}</em>。{"有化禄→财源较好" if cb_good else "靠自身技能求财"}。',
                  'tags':[{'t':'化禄在财帛' if cb_good else '稳中求进','c':'tag-good' if cb_good else 'tag-tip'}]})
    # Career
    gl_good = guanlu and len(guanlu['主星'])>0
    cards.append({'title':'💼 事业','verdict':'事业宫有支撑' if gl_good else '事业需摸索','vc':'good' if gl_good else 'ok',
                  'detail':f'官禄宫{guanlu["干支"] if guanlu else "?"}。主星：<em>{stars(guanlu)}</em>。四化：{sihua(guanlu)}。',
                  'tags':[{'t':'有方向' if gl_good else '需探索','c':'tag-good' if gl_good else 'tag-tip'}]})
    # Health
    je_warn = jiqiong and len(jiqiong['辅星'])>0 and any(s['类型']=='煞' for s in jiqiong['辅星'])
    cards.append({'title':'🏥 健康','verdict':'需留意' if je_warn else '正常关注','vc':'warn' if je_warn else 'ok',
                  'detail':f'疾厄宫{jiqiong["干支"] if jiqiong else "?"}。主星：<em>{stars(jiqiong)}</em>。煞星：{sum(1 for s in jiqiong["辅星"] if s["类型"]=="煞") if jiqiong else 0}颗。',
                  'tags':[{'t':'注意健康' if je_warn else '定期体检','c':'tag-bad' if je_warn else 'tag-tip'}]})
    # Children
    zn_good = zinv and len(zinv['主星'])>0
    cards.append({'title':'👶 子女','verdict':'子女宫有信号' if zn_good else '子女运平','vc':'good' if zn_good else 'ok',
                  'detail':f'子女宫{zinv["干支"] if zinv else "?"}。主星：<em>{stars(zinv)}</em>。{"有主星坐守→子女运较好" if zn_good else "空宫→子女运需看大限引动"}。',
                  'tags':[{'t':'子女缘好' if zn_good else '顺其自然','c':'tag-good' if zn_good else 'tag-tip'}]})
    # Travel
    qy_ji = qianyi and any('化忌' in s['化星'] for s in qianyi['四化'])
    cards.append({'title':'✈️ 外出','verdict':'外出需谨慎' if qy_ji else '外出运正常','vc':'warn' if qy_ji else 'ok',
                  'detail':f'迁移宫{qianyi["干支"] if qianyi else "?"}。主星：<em>{stars(qianyi)}</em>。{"有化忌→外出/远行需做好心理准备" if qy_ji else "无不利信号"}。',
                  'tags':[{'t':'少折腾' if qy_ji else '可远行','c':'tag-bad' if qy_ji else 'tag-good'}]})
    return '\n'.join(card(c['title'], '', c['verdict'], c['vc'], c['detail'], '') for c in cards)

def _ziwei_analysis(zw):
    gongs = zw['十二宫']
    html = ''
    for g in gongs:
        mjr = ', '.join(f'{s["星名"]}({s["庙旺"]})' for s in g['主星']) or '空宫'
        aux = ', '.join(f'{s["星名"]}({s["类型"]})' for s in g['辅星']) or '无'
        si = ', '.join(s['化星'] for s in g['四化']) or '无'
        tris = f'对宫：{g["三方四正"]["对宫"]}，三合：{g["三方四正"]["三合1"]}、{g["三方四正"]["三合2"]}'
        content = f'<p style="color:#bbb;line-height:1.8;">主星：<em>{mjr}</em> | 辅星：{aux} | 四化：{si} | {tris}</p>'
        html += fold_section(f'{g["宫名"]} ({g["干支"]})', content)
    return html

# ═══════════════════════════════════════
# COMBINED CROSS-REF
# ═══════════════════════════════════════
def gen_cross_ref(bz, zw):
    sex = bz['输入']['性别']; y = bz['用神分析']['用神']
    cs = [v['天干十神'] for v in bz['十神标注'].values()]
    target = '正官' if sex=='女' else '正财'; tn = '夫星' if sex=='女' else '妻星'
    has_target = target in cs

    def find_zw(name):
        for g in zw['十二宫']:
            if g['宫名']==name: return g
        return None
    fugong = find_zw('夫妻宫'); caibogong = find_zw('财帛宫'); qianyi = find_zw('迁移宫')
    jiqiong = find_zw('疾厄宫'); zinv = find_zw('子女宫'); minggong = find_zw('命宫')
    def zs(g): return ', '.join(s['星名'] for s in g['主星']) if g and g['主星'] else '空宫'

    rows = [
        ('💍<br>婚姻',
         f'{target}{"透出→"+tn+"有气" if has_target else "不显→"+tn+"弱"}。配偶宫{bz["四柱"]["日柱"]["地支"]}。',
         f'夫妻宫{fugong["干支"] if fugong else "?"}。主星：{zs(fugong)}。四化：{"、".join(s["化星"] for s in fugong["四化"]) if fugong and fugong["四化"] else "无"}。',
         '<span class="agree">✅</span>' if (has_target and fugong and fugong['主星']) else '<span class="conflict">⚡ 需综合判断</span>'),
        ('💰<br>财运',
         f'{"财星透出" if ("正财" in cs or "偏财" in cs) else "财星不显"}。{"有劫财→破财风险" if "劫财" in cs else ""}。',
         f'财帛宫{caibogong["干支"] if caibogong else "?"}。主星：{zs(caibogong)}。{"化禄→财源好" if caibogong and any("化禄" in s["化星"] for s in caibogong["四化"]) else ""}。',
         '<span class="unique">🔵 互补参考</span>'),
        ('🧠<br>性格',
         f'日主{bz["日主"]["天干"]}({bz["日主"]["五行"]})→{bz["用神分析"]["身强身弱"]}。',
         f'命宫{minggong["干支"] if minggong else "?"}。主星：{zs(minggong)}。',
         '<span class="agree">✅ 互补</span>——八字看五行气质，紫微看星曜表现。'),
        ('🏥<br>健康',
         f'五行：{"/".join(f"{w}={c}" for w,c in bz["五行分布"].items())}。',
         f'疾厄宫{jiqiong["干支"] if jiqiong else "?"}。主星：{zs(jiqiong)}。',
         '<span class="unique">🔵 互补参考</span>'),
        ('✈️<br>外出',
         '地支冲合：'+('、'.join(c["关系"] for c in bz["地支关系"]["冲突列表"] if c["关系"] in ["六冲","六害"]) or '无明显不利'),
         f'迁移宫{qianyi["干支"] if qianyi else "?"}。主星：{zs(qianyi)}。{"化忌→外出需谨慎" if qianyi and any("化忌" in s["化星"] for s in qianyi["四化"]) else ""}。',
         '<span class="unique">🔵 紫微独到</span>'),
        ('👶<br>子女',
         f'时柱{bz["四柱"]["时柱"]["干支"]}。',
         f'子女宫{zinv["干支"] if zinv else "?"}。主星：{zs(zinv)}。',
         '<span class="agree">✅ 交叉参考</span>'),
        ('⏳<br>转折',
         f'{bz["大运"]["起运年龄"]}岁起运{bz["大运"]["排法"]}。用神运：{"、".join(d["年龄段"] for d in bz["大运"]["大运列表"] if d["天干五行"] in y)[:60]}',
         f'大限{zw["大限"]["排法"]}。',
         '<span class="agree">✅ 交叉验证</span>'),
    ]
    return ''.join(f'<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>' for r in rows)

def gen_verdict_cards(bz, zw):
    sex = bz['输入']['性别']; y = bz['用神分析']['用神']
    cs = [v['天干十神'] for v in bz['十神标注'].values()]
    def find_zw(name):
        for g in zw['十二宫']:
            if g['宫名']==name: return g
        return None
    fugong = find_zw('夫妻宫'); caibogong = find_zw('财帛宫'); qianyi = find_zw('迁移宫')
    zinv = find_zw('子女宫'); jiqiong = find_zw('疾厄宫')

    cards = [
        ('💍 婚姻', '婚姻需综合判断', 'ok',
         f'八字{"有" if ("正官" if sex=="女" else "正财") in cs else "无"}配偶星透干。紫微夫妻宫{"有主星" if fugong and fugong["主星"] else "为空宫" if fugong else "?"}。综合看需经营。',
         '八字+紫微综合'),
        ('💰 财富', '财运有机遇' if ('正财' in cs or '偏财' in cs) else '财运平稳', 'good' if ('正财' in cs or '偏财' in cs) else 'ok',
         f'用神{"/".join(y)}行业最利。{"财帛宫有化禄→财源好" if caibogong and any("化禄" in s["化星"] for s in caibogong["四化"]) else "靠自身技能求财"}。',
         f'八字用神{"/".join(y)} ｜ 紫微财帛宫'),
        ('👶 子女', '子女宫有信号' if (zinv and zinv['主星']) else '子女运正常', 'good' if (zinv and zinv['主星']) else 'ok',
         f'时柱{bz["四柱"]["时柱"]["干支"]}。紫微子女宫{"有主星" if zinv and zinv["主星"] else "空宫"}。',
         '八字+紫微'),
        ('🏥 健康', '需留意' if any(c<=1 for c in bz['五行分布'].values()) or any(c>=7 for c in bz['五行分布'].values()) else '正常关注', 'warn' if any(c<=1 for c in bz['五行分布'].values()) else 'ok',
         f'五行{"有偏枯" if any(c<=1 for c in bz["五行分布"].values()) else "相对平衡"}。紫微疾厄宫提供额外线索。',
         '八字五行+紫微疾厄'),
        ('✈️ 外出', '需谨慎' if (qianyi and any('化忌' in s['化星'] for s in qianyi['四化'])) else '正常', 'warn' if (qianyi and any('化忌' in s['化星'] for s in qianyi['四化'])) else 'ok',
         f'迁移宫{"有化忌→不宜远行" if qianyi and any("化忌" in s["化星"] for s in qianyi["四化"]) else "无不利信号"}。',
         '紫微迁移宫'),
        ('⏳ 人生节奏', f'{bz["大运"]["起运年龄"]}岁起运', 'ok',
         f'用神运积极进取，忌神运保守稳健。{bz["大运"]["起运年龄"]}岁起运{bz["大运"]["排法"]}。',
         '八字大运+紫微大限'),
    ]
    return '\n'.join(card(c[0], '', c[1], c[2], c[3], c[4]) for c in cards)

# ═══════════════════════════════════════
# NARRATIVE ANALYSIS (白话长文)
# ═══════════════════════════════════════
def gen_narrative(bz, zw):
    p = bz['四柱']; ss = bz['十神标注']; wx = bz['五行分布']
    yong = bz['用神分析']['用神']; ji = bz['用神分析']['忌神']; ji2 = ji
    riGan = bz['日主']['天干']; riWx = bz['日主']['五行']; sq = bz['用神分析']['身强身弱']
    sex = bz['输入']['性别']; dy = bz['大运']
    target = '正官' if sex=='女' else '正财'; tn = '夫星' if sex=='女' else '妻星'
    ta_val = '她' if sex=='女' else '他'
    cs = [v['天干十神'] for v in ss.values()]
    has_target = target in cs; has_jc = '劫财' in cs; has_sg = '伤官' in cs; has_ss = '食神' in cs
    has_cai = ('正财' in cs or '偏财' in cs); has_yin = ('正印' in cs or '偏印' in cs)
    has_guan = ('正官' in cs or '七杀' in cs); has_sha = '七杀' in cs

    def zfind(name):
        for g in zw['十二宫']:
            if g['宫名']==name: return g
        return None
    fugong = zfind('夫妻宫'); caibogong = zfind('财帛宫'); guanlu = zfind('官禄宫')
    qianyi = zfind('迁移宫'); jiqiong = zfind('疾厄宫'); zinv = zfind('子女宫')
    minggong = zfind('命宫'); fudegong = zfind('福德宫'); tianzhai = zfind('田宅宫')
    jiaoyou = zfind('交友宫'); fumu = zfind('父母宫')

    def mjr(g): return ', '.join(s['星名'] for s in g['主星']) if g and g['主星'] else '空宫'
    def sih(g): return ', '.join(s['化星'] for s in g['四化']) if g and g['四化'] else '无'
    def miao(g): return ', '.join(f'{s["星名"]}({s["庙旺"]})' for s in g['主星']) if g and g['主星'] else ''
    def miao_str(s_list): return ''.join(f'[{s["星名"]}·{s["庙旺"]}]' for s in s_list) if s_list else ''

    H = html = '<div class="nar">'

    # ══════════ 一、命盘总览 ══════════
    wx_detail = []
    gan_info = {c:[] for c in ['年柱','月柱','日柱','时柱']}
    for col in ['年柱','月柱','日柱','时柱']:
        gan = p[col]['天干']; zhi = p[col]['地支']
        gan_info[col] = f'{gan}({ss[col]["天干十神"]})'
    wx_detail = [f'{p[col]["天干"]}({p[col]["天干五行"]})' for col in ['年柱','月柱','日柱','时柱']]
    wx_detail += [f'{p[col]["地支"]}({p[col]["地支五行"]})' for col in ['年柱','月柱','日柱','时柱']]
    for w in ['木','火','土','金','水']:
        items = [f'{p[col]["干支"]}' for col in ['年柱','月柱','日柱','时柱'] if p[col]['天干五行']==w or p[col]['地支五行']==w]
        wx_detail.append(f'{w}({"/".join(items) if items else "无"})')
    wx_summary = f'火={wx["火"]}、木={wx["木"]}、土={wx["土"]}、金={wx["金"]}、水={wx["水"]}'

    html += '<h3>一、命盘总览</h3>'
    html += f'<p><b>八字：</b>{bz["八字"]}。年柱{p["年柱"]["干支"]}（{p["年柱"]["纳音"]}），月柱{p["月柱"]["干支"]}（{p["月柱"]["纳音"]}），日柱{p["日柱"]["干支"]}（{p["日柱"]["纳音"]}），时柱{p["时柱"]["干支"]}（{p["时柱"]["纳音"]}）。</p>'
    html += f'<p><b>日主：</b>{riGan}{riWx}（{"阳" if bz["日主"]["阴阳"]=="阳" else "阴"}），代表命主本人。生于{p["月柱"]["地支"]}月（{bz["节气"]}后），{sq}。</p>'
    html += f'<p><b>五行分布：</b>{wx_summary}。{"其中"+riWx+"偏旺" if sq=="身强" else riWx+"偏弱" if sq=="身弱" else "中和"}，{"水五行缺失需调候" if wx.get("水",0)==0 else ""}{"火五行缺失需暖局" if wx.get("火",0)==0 else ""}。</p>'
    html += f'<p><b>格局：</b>{riGan}{riWx}{sq}。用神为<b>{"、".join(yong)}</b>（有利五行），忌神为<b>{"、".join(ji)}</b>（不利五行）。</p>'
    html += f'<p><b>紫微：</b>命宫<b>{zw["命宫"]}</b>（{minggong["干支"] if minggong else ""}），身宫<b>{zw["身宫"]}</b>，{zw["五行局"]}。紫微星在{zw["紫微星在"]}宫。{"身命同宫→一生目标明确" if zw["命宫"]==zw["身宫"] else "身宫与命宫不同→后天发展重心与先天禀赋有差异"}。</p>'

    # ══════════ 二、性格特质 ══════════
    char_map = {
        '甲':'正直、上进、有领导力，像参天大树般直率，但偶尔固执己见、不肯变通。',
        '乙':'柔韧、适应力强、心思细腻，如藤蔓般灵活，但有时优柔寡断、缺乏主见。',
        '丙':'热情开朗、光明磊落，如太阳般有感染力，但急躁、爱面子、容易冲动。',
        '丁':'温和细腻、有耐心、执着内敛，如烛火般持久，但有时过于拘谨、有心机。',
        '戊':'厚重、诚信、稳重可靠，如城墙般坚固，但保守固执、不喜变通。',
        '己':'包容、温和、善解人意，如田园般滋养，但多疑琐碎、容易纠结小事。',
        '庚':'刚强果断、讲义气、雷厉风行，如刀斧般锋锐，但冲动直接、容易伤人不自知。',
        '辛':'精致、挑剔、有品位、爱面子，如首饰般精美，但虚荣心强、容易斤斤计较。',
        '壬':'聪明、通融、灵活善变，如江河般奔放自由，但任性、缺乏持久力。',
        '癸':'细腻、敏感、内向、善谋略，如雨露般润物无声，但多愁善感、优柔内向。'
    }
    char = char_map.get(riGan, '')

    char_points = []
    char_points.append(f'<b>1. 日主{riGan}{riWx}——</b>{char}')
    if sq == '身强':
        char_points.append('<b>2. 身强——</b>自我意识强、有主见、不甘人后。火旺则急性子，木旺则犟脾气，金旺则刚硬，水旺则善变，土旺则固执。')
    else:
        char_points.append('<b>2. 身弱——</b>相对随和、善借力、不喜硬碰硬。但日主有根则不卑不亢。')
    if has_yin:
        yin_cols = [k for k,v in ss.items() if '印' in v['天干十神']]
        char_points.append(f'<b>3. 印星加持——</b>出现在{"、".join(yin_cols)}。印星代表仁慈、学识、长辈缘。骨子里重情义、有感恩心，悟性好、爱琢磨，学习和理解能力强。')
    if has_sha:
        sha_cols = [k for k,v in ss.items() if '杀' in v['天干十神']]
        char_points.append(f'<b>4. 七杀透干——</b>出现在{"、".join(sha_cols)}。七杀代表野心、压力和不服输的劲头。内心有抱负，一辈子闲不住，总想做出一番事业，很难长期安逸躺平。')
    if has_sg:
        char_points.append('<b>5. 伤官在命——</b>聪明、有才华、表达欲强，但也恃才傲物、说话直接甚至刻薄。创造性思维强，不喜欢被条条框框约束。')
    if p['日柱']['地支'] in ['午','子','卯','酉']:
        char_points.append(f'<b>6. 日坐{p["日柱"]["地支"]}桃花/羊刃——</b>日柱为配偶宫也是自身性格的延伸。羊刃坐日→脾气来得快、遇事不愿示弱、习惯自己硬扛，不爱求人。')
    conflicts = bz['地支关系']['冲突列表']
    zx = [c for c in conflicts if c['关系']=='自刑']
    if zx:
        char_points.append(f'<b>7. {zx[0]["涉及"]}——</b>自刑代表内心纠结，容易对现状不满、自寻烦恼。需要学会与自己和解。')
    if minggong:
        char_points.append(f'<b>8. 紫微视角——</b>命宫{miao(minggong) if minggong["主星"] else "空宫，借对宫为用"}。{"命宫空宫→性格弹性大，易受环境影响" if not minggong["主星"] else ""}。')

    html += '<h3>二、性格特质</h3>'
    for pt in char_points:
        html += f'<p>{pt}</p>'

    # ══════════ 三、婚姻感情 ══════════
    html += f'<h3>三、婚姻感情（{sex}命重点）</h3>'
    marry_pts = []
    if sex == '女':
        if has_target:
            marry_pts.append(f'<b>1. 夫星定位——</b>正官为夫星，{target}透出天干→夫星有气，配偶缘分不差。')
        else:
            marry_pts.append(f'<b>1. 夫星定位——</b>正官癸水为夫星，夫星仅藏于地支不透天干→夫缘偏弱。配偶能力一般，或在家中话语权不强，需大运流年引动才会有明显的感情机会。')
        if '七杀' in cs:
            marry_pts.append('<b>2. 官杀混杂——</b>正官和七杀同时出现→感情纠葛较多，容易遇到烂桃花干扰。需要主动避嫌、把握边界。')
        # 夫宫
        ri_zhi = p['日柱']['地支']
        if ri_zhi in ['午','子']:
            marry_pts.append(f'<b>3. 日坐{ri_zhi}羊刃——</b>日支为夫宫，坐羊刃意味着自身个性强势、主见大，在家容易主导话语权，对伴侣标准高，容易挑剔和争执。传统命理认为此日柱婚姻多波折。')
        elif ri_zhi in ['卯','酉']:
            marry_pts.append(f'<b>3. 日坐{ri_zhi}桃花——</b>夫宫坐桃花，配偶外貌不错或异性缘好，但也意味着婚姻中容易出现第三者干扰，需双方共同维护。')
    else:
        if has_target:
            marry_pts.append(f'<b>1. 妻星定位——</b>正财为妻星，{target}透出天干→妻星有气，配偶缘分不差。')
        else:
            marry_pts.append(f'<b>1. 妻星定位——</b>正财为妻星，正财不透天干→妻星偏弱。配偶缘分需大运流年引动。')
        ri_zhi = p['日柱']['地支']
        if ri_zhi in ['午','子']:
            marry_pts.append(f'<b>2. 日坐{ri_zhi}羊刃——</b>日支为妻宫，坐羊刃意味着自身个性较强，在家中容易占据主导地位，需要学会包容和让步。')

    # Check for 自刑 in 日支
    zx_ri = [c for c in conflicts if '日柱' in c['涉及'] and c['关系']=='自刑']
    if zx_ri:
        marry_pts.append(f'<b>4. 婚姻宫自刑——</b>{zx_ri[0]["涉及"]}处于自刑状态→内心容易对伴侣不满、心生隔阂。早婚更容易爆发矛盾，晚婚能大幅缓解。')
    # Check for 冲
    chong_ri = [c for c in conflicts if '日柱' in c['涉及'] and c['关系']=='六冲']
    if chong_ri:
        marry_pts.append(f'<b>5. 婚姻宫逢冲——</b>{chong_ri[0]["涉及"]}→婚姻易动荡、分居或争吵。需要双方有足够的包容和理解。')

    # Ziwei marriage
    if fugong:
        if fugong['主星']:
            marry_pts.append(f'<b>6. 紫微夫妻宫——</b>{miao(fugong)}坐守→配偶素质不错。{"天梁为荫星→配偶稳重有担当。" if any(s["星名"]=="天梁" for s in fugong["主星"]) else ""}{"紫微为帝星→配偶有领导气质。" if any(s["星名"]=="紫微" for s in fugong["主星"]) else ""}四化：{sih(fugong)}。')
        if any('化忌' in s['化星'] for s in fugong['四化']):
            marry_pts.append('<b>7. 夫妻宫化忌——</b>婚姻中需注意沟通方式，避免冷战和误会积累。化忌不代表婚姻失败，只是需要更多经营。')

    marry_pts.append('<b>总结建议：</b>{"晚婚、择性格沉稳包容之人，能大幅改善婚姻质量。主动和异性保持边界，规避烂桃花。婚姻中学会示弱包容，不要事事争输赢。" if sex=="女" else "选择性格温和顾家之人。婚姻中学会包容让步，不要事事争主导权。"}')
    for pt in marry_pts:
        html += f'<p>{pt}</p>'

    # ══════════ 四、事业财运 ══════════
    html += '<h3>四、事业财运</h3>'
    html += '<h4 style="color:var(--g);margin-top:12px;">💼 事业</h4>'
    career_pts = []
    if has_yin and has_sha:
        career_pts.append('<b>1. 印+杀组合——</b>适合自主做事、管理岗位、个体生意。不适合长期死板坐班、完全听人管束的岗位，容易感到压抑。')
    elif has_yin:
        career_pts.append('<b>1. 印星旺——</b>适合教育、研究、文化、咨询类工作。学习能力强，适合需要深度思考的行业。')
    elif has_sha:
        career_pts.append('<b>1. 七杀在命——</b>有冲劲和执行力，适合军警、管理、销售、创业等需要魄力的领域。')

    industry_map = {'木':'教育、医疗、林业、文化、出版','火':'能源、餐饮、美容、演艺、互联网','土':'房地产、建筑、农业、陶瓷、畜牧','金':'金融、法律、机械、汽车、珠宝、军警','水':'贸易、物流、旅游、水利、传媒'}
    career_pts.append(f'<b>2. 适合行业——</b>用神{"、".join(yong)}属性行业最利：{"；".join(industry_map[w] for w in yong)}。')
    career_pts.append(f'<b>3. 忌神行业——</b>避免{"、".join(industry_map[w] for w in ji)}类行业长期深耕，容易付出多收获少。')

    if has_sg or has_ss:
        career_pts.append('<b>4. 食伤才艺——</b>有技能和创意天赋，适合靠手艺、设计、写作、自媒体等方式变现。')
    if guanlu and guanlu['主星']:
        career_pts.append(f'<b>5. 紫微官禄宫——</b>{miao(guanlu)}→事业方向有明确信号。{"天同在官禄→适合轻松型工作，不宜高压环境。" if any(s["星名"]=="天同" for s in guanlu["主星"]) else ""}{"紫微在官禄→有领导潜质。" if any(s["星名"]=="紫微" for s in guanlu["主星"]) else ""}')
    for pt in career_pts:
        html += f'<p>{pt}</p>'

    html += '<h4 style="color:var(--g);margin-top:12px;">💰 财运</h4>'
    wealth_pts = []
    if has_cai:
        cai_cols = [k for k,v in ss.items() if '财' in v['天干十神']]
        wealth_pts.append(f'<b>1. 财星透出——</b>出现在{"、".join(cai_cols)}。一生不缺赚钱机会，中年财运走强，靠自身辛苦打拼得财。')
    else:
        wealth_pts.append('<b>1. 财星不显——</b>不是不赚钱，而是需要通过技能和努力来求财。食伤生财或官印相生的路径更合适。')
    if has_jc:
        wealth_pts.append('<b>2. 劫财破财——</b>八字有劫财→容易因亲友借钱、合伙生意、冲动消费、人情往来而耗财。不宜和朋友大额合伙投资，容易破财扯皮。')
    if has_ss:
        wealth_pts.append('<b>3. 食神生财——</b>食神是生财之源→有稳定的收入渠道。靠技术、手艺、服务赚钱，细水长流型。')
    if caibogong:
        has_lu = any('化禄' in s['化星'] for s in caibogong['四化'])
        wealth_pts.append(f'<b>4. 紫微财帛宫——</b>{miao(caibogong)}。{"化禄在财帛→财运加成，赚钱相对顺利。" if has_lu else "财帛宫平稳→财运需自身努力创造。"}')
    wealth_pts.append(f'<b>5. 求财方向——</b>全局喜{"、".join(yong)}→从事{"、".join(industry_map[w][:6] for w in yong)}等{"、".join(yong)}属性行业更利求财。')
    for pt in wealth_pts:
        html += f'<p>{pt}</p>'

    # ══════════ 五、六亲 ══════════
    html += '<h3>五、六亲简析</h3>'
    relative_pts = []
    nian_ss = ss['年柱']['天干十神']
    relative_pts.append(f'<b>1. 年柱——</b>{p["年柱"]["干支"]}为父母宫。年干为{bz["日主"]["天干"]}之{nian_ss}→与父母{"缘分深，长辈多帮扶" if "印" in nian_ss else "关系较为独立" if "财" in nian_ss else "缘分正常"}。')
    relative_pts.append(f'<b>2. 时柱——</b>{p["时柱"]["干支"]}为子女宫→子女个性参考时柱{p["时柱"]["天干五行"]}。{"时柱帝旺→子女个性较强" if p["时柱"]["日主十二长生在此"] in ["帝旺","临官"] else ""}')
    if zinv:
        relative_pts.append(f'<b>3. 紫微子女宫——</b>{miao(zinv) if zinv["主星"] else "空宫"}→子女运参考。{"紫相同宫→子女尊贵有出息" if any(s["星名"]=="紫微" for s in zinv["主星"]) and any(s["星名"]=="天相" for s in zinv["主星"]) else ""}')
    if has_jc:
        relative_pts.append('<b>4. 同辈关系——</b>比劫旺→同辈朋友多，但真心贵人少。多有借钱、拖累、竞争之事，钱财上少和亲友深度往来。')
    for pt in relative_pts:
        html += f'<p>{pt}</p>'

    # ══════════ 六、健康 ══════════
    html += '<h3>六、健康</h3>'
    health_pts = []
    m = {'木':'肝胆、筋骨、神经系统','火':'心血管、血压、眼睛、炎症','土':'脾胃、消化、肌肉','金':'肺、呼吸道、皮肤、大肠','水':'肾、膀胱、泌尿、腰膝'}
    for w in ['火','木','土','金','水']:
        c = wx.get(w,0)
        if c >= 7: health_pts.append(f'<b>{w}过旺（{c}）——</b>注意{m[w]}。易出现{"心火失眠、头疼" if w=="火" else "肝火旺、易怒" if w=="木" else "脾胃湿热、胀气" if w=="土" else "呼吸道敏感" if w=="金" else "水肿、尿频" if w=="水" else ""}等症状。')
        elif c <= 1: health_pts.append(f'<b>{w}偏弱（{c}）——</b>注意{m[w]}。平时需注意{"补肾养腰、少熬夜" if w=="水" else "养肝护胆、少饮酒" if w=="木" else "养胃健脾、饮食规律" if w=="土" else "润肺护肤" if w=="金" else "养心护血管" if w=="火" else ""}。')
    if jiqiong and jiqiong['主星']:
        jq_info = miao(jiqiong)
        health_pts.append(f'<b>紫微疾厄宫——</b>{jq_info}。{"贪狼在疾厄→注意因欲望（饮食/情欲/情绪）导致的健康问题" if any(s["星名"]=="贪狼" for s in jiqiong["主星"]) else ""}')
    health_pts.append('<b>日常建议——</b>少熬夜、饮食清淡均衡、多喝水、适量运动、定期体检。命理提示的健康方向可作为体检重点关注项目。')
    for pt in health_pts:
        html += f'<p>{pt}</p>'

    # ══════════ 七、大运简析 ══════════
    html += '<h3>七、大运简析</h3>'
    html += f'<p>{dy["起运年龄"]}岁起运，{dy["排法"]}。共8步大运：</p>'
    for i, d in enumerate(dy['大运列表']):
        is_y = d['天干五行'] in yong; is_j = d['天干五行'] in ji
        label = '用神运 ✓' if is_y else ('忌神运 ✗' if is_j else '平运')
        lc = 'var(--green)' if is_y else ('var(--r)' if is_j else '#888')
        # Dynamic description
        desc = ''
        if i == 0: desc = '童年阶段，读书求学。' + ('长辈照顾周到' if has_yin else '')
        elif i == 1: desc = '青少年时期，性格成型阶段。' + ('学业或感情波动较多' if is_j else '')
        elif i == 2: desc = '青年阶段，事业起步、婚恋重要期。' + ('财运逐步好转' if is_y else '')
        elif i == 3: desc = '壮年阶段，人生黄金期。' + ('事业上升、收入提升' if is_y else '多阻多难' if is_j else '')
        elif i == 4: desc = '中年稳定期。' + ('稳中有升' if is_y else '宜守不宜攻' if is_j else '')
        elif i == 5: desc = '中晚年过渡。' + ('花销增多，宜保守理财' if is_j else '')
        elif i == 6: desc = '晚年阶段。' + ('贵人运增强' if is_y else '')
        else: desc = '晚年收尾。' + ('整体安稳' if is_y else '')
        html += f'<p><b>{d["年龄段"]} {d["干支"]}</b>（<span style="color:{lc}">{label}</span>）——{d["天干五行"]}+{d["地支五行"]}。{desc}</p>'

    # ══════════ 八、核心建议 ══════════
    html += '<h3>八、核心喜忌与建议</h3>'
    dirs = {'木':'东','火':'南','土':'中','金':'西','水':'北'}
    colors = {'木':'青绿','火':'红紫','土':'黄棕','金':'白','水':'黑蓝'}
    html += f'<p><b>喜用神（有利五行）：</b><span style="color:var(--gr)">{"、".join(yong)}</span>。喜用神五行代表对命主有利的能量和方向。</p>'
    html += f'<p><b>忌神（不利五行）：</b><span style="color:var(--r)">{"、".join(ji)}</span>。忌神五行代表可能加重命局失衡的能量，需要规避或制化。</p>'

    advice = []
    advice.append('<b>1. 性格方面——</b>收敛急躁，少直言伤人。遇事不要事事争输赢，学会适当退让能大幅减少人际冲突。')
    if has_jc:
        advice.append('<b>2. 求财方面——</b>拒绝合伙大额投资、少借钱给亲友。优先用神五行相关行业，避开忌神五行行业长期深耕。')
    else:
        advice.append('<b>2. 求财方面——</b>靠技能和努力稳定求财，不宜投机。优先用神五行相关行业。')
    if sex == '女' and has_sg:
        advice.append('<b>3. 感情方面——</b>尽量晚婚，择偶优先性格沉稳包容、年纪稍长之人。主动和异性保持边界，规避烂桃花。')
    elif sex == '男' and has_jc:
        advice.append('<b>3. 感情方面——</b>择偶优先性格温和顾家之人。婚姻中学会包容让步，不要事事争主导权。')
    else:
        advice.append('<b>3. 感情方面——</b>关注配偶星和配偶宫状态，主动经营婚姻关系。理解命理提示的性格倾向。')
    advice.append('<b>4. 健康方面——</b>少熬夜、少吃辛辣燥热食物、多补水。定期体检，重点关注命理提示的脏腑方向。')
    advice.append(f'<b>5. 风水穿搭——</b>日常多用{"、".join(colors[w] for w in yong)}色系衣物饰品。居家和工作方位优先{"、".join(dirs[w] for w in yong)}，少长期久居忌神方位。')
    advice.append('<b>6. 人生节奏——</b>用神运期间积极进取、把握机遇；忌神运期间保守稳健、以守为攻、注意健康和财务安全。')
    for a in advice:
        html += f'<p>{a}</p>'

    html += f'<p style="margin-top:16px;color:#888;font-style:italic;">提示：命理仅为传统民俗参考，人生最终走向仍取决于个人选择、努力与现实环境，不可全盘宿命看待。以上内容完全基于八字和紫微星盘的实际数据动态生成。</p>'
    html += '</div>'
    return html


# ═══════════════════════════════════════
# TEMPLATE
# ═══════════════════════════════════════
HTML = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>命运双鉴 __DATE__</title>
<style>
:root{--bg:#0f0f14;--card:#1a1a24;--c2:#222232;--t:#d4d4dc;--g:#c9a96e;--p:#8b5cf6;--r:#e85d75;--b:#60a5fa;--gr:#4ade80;--bd:#2a2a3a;--wx-wood:#4ade80;--wx-fire:#f97316;--wx-earth:#a78b5a;--wx-metal:#e2e8a0;--wx-water:#38bdf8}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--t);font-family:'Segoe UI','Noto Sans SC','Microsoft YaHei',sans-serif;line-height:1.7;min-height:100vh}
.top-nav{display:flex;background:#12121a;border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:100}
.nav-btn{flex:1;padding:16px 10px;background:none;border:none;color:#777;cursor:pointer;font-size:1em;transition:all .25s;border-bottom:2px solid transparent;font-family:inherit;text-align:center}
.nav-btn:hover{color:#aaa}.nav-btn.on{color:var(--g);border-bottom-color:var(--g);background:rgba(201,169,110,.04)}
.nav-btn .sub{font-size:.65em;display:block;color:#555;margin-top:2px}.nav-btn.on .sub{color:var(--g)}
.section-panel{display:none}.section-panel.on{display:block}
.wrap{max-width:1100px;margin:0 auto;padding:30px 20px 60px}

/* HEADER */
.hdr{text-align:center;padding:40px 20px;margin-bottom:36px;background:linear-gradient(135deg,rgba(201,169,110,.06),rgba(139,92,246,.06));border:1px solid var(--bd);border-radius:18px}
.hdr h1{font-size:2.2em;background:linear-gradient(135deg,var(--g),#e2c98a,var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.hdr .sub{color:#888;font-size:.9em}.hdr .meta{display:inline-block;margin-top:12px;padding:6px 18px;background:var(--card);border:1px solid var(--bd);border-radius:20px;color:#888;font-size:.82em}
.info-row{display:flex;justify-content:center;gap:16px;margin-top:14px;flex-wrap:wrap}
.info-badge{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:6px 14px;font-size:.85em}
.info-badge span{color:var(--g);font-weight:600}
.sh{font-size:1.2em;color:var(--g);margin:36px 0 14px;padding-bottom:10px;border-bottom:1px solid var(--bd)}
.box{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:8px}
.green{color:var(--gr)}.red{color:var(--r)}.dim{color:#666}

/* BAZI TABLE */
.pillars-table{width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:12px;overflow:hidden}
.pillars-table th{background:#2F5496;color:#fff;padding:14px 12px;font-size:.9em;text-align:center}
.pillars-table td{padding:12px;background:var(--card);border:1px solid var(--bd);text-align:center;font-size:.9em}
.pillars-table .day-master{color:var(--g);font-weight:700;font-size:1.1em}
.wx-d{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}
.wx-bar{height:20px;border-radius:10px;display:flex;overflow:hidden;margin-bottom:8px}
.wx-lab{display:flex;gap:16px;flex-wrap:wrap;font-size:.82em;color:#888;margin-bottom:16px}

/* VERDICT CARDS */
.sum{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}
.vc{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:26px 22px;transition:all .25s;display:flex;flex-direction:column}
.vc:hover{border-color:var(--g);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.3)}
.vc .vc-icon{font-size:2em;margin-bottom:8px}
.vc h3{font-size:1.05em;color:#bbb;margin-bottom:6px;font-weight:500}
.vc .big{font-size:1.35em;font-weight:700;margin:6px 0 12px;line-height:1.3}
.big.good{color:var(--gr)}.big.warn{color:var(--r)}.big.ok{color:var(--g)}
.vc .detail{color:#999;font-size:.84em;line-height:1.75}.vc .detail em{color:#ccc;font-style:normal;font-weight:600}
.vc .source{font-size:.72em;color:#555;margin-top:14px;padding-top:12px;border-top:1px solid var(--bd)}

/* TAGS */
.tg{display:inline-block;padding:3px 10px;border-radius:6px;font-size:.75em;margin:2px}
.tag-good{background:rgba(74,222,128,.1);color:var(--gr);border:1px solid rgba(74,222,128,.2)}
.tag-bad{background:rgba(232,93,117,.1);color:var(--r);border:1px solid rgba(232,93,117,.2)}
.tag-tip{background:rgba(96,165,250,.08);color:var(--b);border:1px solid rgba(96,165,250,.2)}

/* FOLD */
.fold{margin-bottom:10px}
.fold-hd{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px 20px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:all .25s}
.fold-hd:hover{border-color:var(--g)}.fold-hd h3{font-size:1em;color:#ddd}
.fold-hd .arr{transition:transform .3s;color:#666}.fold-hd.open .arr{transform:rotate(180deg)}
.fold-bd{max-height:0;overflow:hidden;transition:max-height .4s;background:var(--card);border-radius:0 0 10px 10px;padding:0 20px}
.fold-bd.open{max-height:2000px;padding:16px 20px;border:1px solid var(--bd);border-top:0}
.der{padding:12px 16px;margin:8px 0;border-radius:8px;background:rgba(139,92,246,.05);border-left:3px solid var(--p);font-size:.9em;line-height:1.8}
.der-obs{color:var(--b)}.der-princ{color:var(--g)}.der-conc{color:#ddd}

/* DAYUN */
.dy-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.dy-s{flex:1;min-width:100px;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px;text-align:center;transition:all .25s}
.dy-s:hover{border-color:var(--g)}.dy-s.dy-y{border-color:rgba(74,222,128,.3)}.dy-s.dy-j{border-color:rgba(232,93,117,.3)}
.dy-a{font-size:.68em;color:#666}.dy-g{font-size:1.05em;color:var(--g);font-weight:600;margin:3px 0}

/* ZIWEI GRID */
.zw-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:20px}
.zw-p,.zw-c{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px;min-height:100px;transition:all .25s}
.zw-p:hover{border-color:var(--g);box-shadow:0 0 16px rgba(201,169,110,.08)}
.zw-p.empty{opacity:.6}.zw-ctr{text-align:center;color:var(--g);font-size:.9em;font-weight:700;line-height:1.8}.zw-ctr small{color:#666;font-weight:400}
.zw-pn{font-size:.75em;color:var(--g);font-weight:700;margin-bottom:4px}.zw-pz{float:right;color:#666;font-size:.7em}
.zw-st{display:flex;flex-wrap:wrap;gap:2px;margin:2px 0}
.st-mjr{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.7em;color:var(--g);background:rgba(201,169,110,.1);border:1px solid rgba(201,169,110,.25)}.st-mjr.mi{color:#f59e0b}
.st-ji{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.68em;color:var(--gr);background:rgba(74,222,128,.08)}
.st-sha{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.68em;color:var(--r);background:rgba(232,93,117,.08)}.st-za{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.68em;color:#a78bfa;background:rgba(139,92,246,.08)}
.st-si{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.68em;color:var(--b);background:rgba(96,165,250,.1);font-weight:700;border:1px solid rgba(96,165,250,.2)}
.zw-dx{font-size:.65em;color:#666;margin-top:2px}

/* SIHUA BANNER */
.sh-ban{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.sh-c{flex:1;min-width:160px;border-radius:10px;padding:14px;text-align:center;border:1px solid var(--bd)}
.sh-lu{background:rgba(74,222,128,.05);border-color:rgba(74,222,128,.2)}
.sh-quan{background:rgba(139,92,246,.05);border-color:rgba(139,92,246,.2)}
.sh-ke{background:rgba(96,165,250,.05);border-color:rgba(96,165,250,.2)}
.sh-ji{background:rgba(232,93,117,.05);border-color:rgba(232,93,117,.2)}
.sh-l{font-size:1.1em;font-weight:700}

/* CROSS-REF TABLE */
.xref{overflow-x:auto;margin-bottom:20px}
.xref table{width:100%;border-collapse:separate;border-spacing:0;border-radius:14px;overflow:hidden;font-size:.85em}
.xref th{background:#2F5496;color:#fff;padding:12px 14px;font-size:.85em;font-weight:600;text-align:center}
.xref td{padding:12px 14px;background:var(--card);border-bottom:1px solid var(--bd);vertical-align:top;line-height:1.6}
.xref tr:last-child td{border-bottom:none}.xref tr:hover td{background:var(--c2)}
.xref tr td:first-child{font-weight:700;color:var(--g);text-align:center;font-size:1em}
.agree{color:var(--gr);font-weight:600}.conflict{color:var(--r);font-weight:600}.unique{color:var(--b);font-weight:600}

/* NARRATIVE */
.nar{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:28px 24px;margin-bottom:20px;line-height:1.9}
.nar h3{color:var(--g);font-size:1.05em;margin:20px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--bd)}
.nar h3:first-child{margin-top:0}
.nar p{color:#bbb;font-size:.88em;margin:6px 0}
.nar b{color:#ddd}

/* ACTIONS */
.acts{background:linear-gradient(135deg,rgba(201,169,110,.05),rgba(139,92,246,.05));border:1px solid var(--bd);border-radius:14px;padding:28px 24px;margin-top:16px}
.act-list{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.act-item{background:var(--card);border-radius:10px;padding:16px 14px;border-left:3px solid var(--g);font-size:.85em;line-height:1.6}
.act-item em{color:#ddd;font-style:normal;font-weight:600}
.act-item .num{display:inline-block;width:20px;height:20px;border-radius:50%;background:var(--g);color:#1a1a24;text-align:center;line-height:20px;font-size:.72em;font-weight:700;margin-right:6px}
.ft{text-align:center;color:#555;font-size:.75em;margin-top:24px;line-height:1.8}

/* GUIDE */
.guide-btn{position:fixed;bottom:24px;right:24px;z-index:1000;width:48px;height:48px;border-radius:50%;border:none;background:var(--g);color:#1a1a24;font-size:1.4em;cursor:pointer;box-shadow:0 4px 18px rgba(201,169,110,.3);transition:all .25s;display:flex;align-items:center;justify-content:center}
.guide-btn:hover{transform:scale(1.08)}
.guide-panel{position:fixed;top:0;right:-400px;width:380px;height:100vh;background:#16161f;border-left:1px solid var(--bd);z-index:999;transition:right .35s;overflow-y:auto;padding:28px 22px;box-shadow:-6px 0 28px rgba(0,0,0,.4)}
.guide-panel.open{right:0}
.guide-panel h3{color:var(--g);font-size:1.15em;margin-bottom:16px}
.guide-panel .tip{background:#1e1e2c;border-radius:10px;padding:12px 14px;margin-bottom:10px;border-left:3px solid var(--g);font-size:.85em;line-height:1.7}
.guide-panel .tip .n{display:inline-block;width:20px;height:20px;border-radius:50%;background:var(--g);color:#1a1a24;text-align:center;line-height:20px;font-size:.75em;font-weight:700;margin-right:6px}
.guide-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:998}.guide-overlay.show{display:block}

@media(max-width:900px){.sum{grid-template-columns:repeat(2,1fr)}.act-list{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.sum{grid-template-columns:1fr}.act-list{grid-template-columns:1fr}.zw-grid{grid-template-columns:repeat(2,1fr)}.wrap{padding:16px 8px 40px}}
</style></head><body>
<div class="top-nav">
  <button class="nav-btn on" onclick="sw('bazi')">八字命盘<span class="sub">子平术</span></button>
  <button class="nav-btn" onclick="sw('ziwei')">紫微斗数<span class="sub">星盘分析</span></button>
  <button class="nav-btn" onclick="sw('dual')">双鉴总结<span class="sub">交叉验证</span></button>
</div>

<!-- TAB 1: BAZI -->
<div id="tb-bazi" class="section-panel on"><div class="wrap">
<div class="hdr"><h1>八字命盘 · 子平术</h1><div class="sub">Ba Zi · Four Pillars of Destiny</div><div class="meta">__BZ_DATE__ · __BZ_SEX__命 · __BZ_YEAR__年 · 日主 __BZ_RIGAN__(__BZ_RIWX__) · __BZ_SQ__</div></div>
__BAZI_CONTENT__
<div class="ft">⚠ 命理仅为传统民俗文化参考，人生走向取决于你自己的选择和努力。</div>
</div></div>

<!-- TAB 2: ZIWEI -->
<div id="tb-ziwei" class="section-panel"><div class="wrap">
<div class="hdr"><h1>紫微斗数 · 星盘命理</h1><div class="sub">Zi Wei Dou Shu · Star Chart</div><div class="meta">__ZW_DATE__ · __ZW_SEX__命 · __ZW_YEAR__年 · 命宫__ZW_MING__ · 身宫__ZW_SHEN__ · __ZW_WXJ__</div></div>
__ZIWEI_CONTENT__
<div class="ft">⚠ 命理仅为传统民俗文化参考，人生走向取决于你自己的选择和努力。</div>
</div></div>

<!-- TAB 3: DUAL -->
<div id="tb-dual" class="section-panel"><div class="wrap">
<div class="hdr"><h1>命运双鉴 · 综合交叉验证</h1><div class="sub">八字（子平术）× 紫微斗数 —— 两套独立命理体系互相印证</div><div class="meta">__DUAL_DATE__ · __DUAL_SEX__命 · __DUAL_YEAR__年</div></div>
<div class="sh">📊 七维交叉验证表</div>
<div class="xref"><table><tr><th></th><th>八字（子平术）</th><th>紫微斗数</th><th>一致性</th></tr>__CROSS_REF__</table></div>
<div class="sh">🎯 综合定论</div>
<div class="sum">__VERDICTS__</div>
<div class="sh">📝 详细命理分析</div>
__NARRATIVE__
<div class="sh">📋 行动建议</div>
<div class="acts"><div class="act-list">
  <div class="act-item"><span class="num">1</span><em>用神方向：</em>有利五行 <strong>__YONG__</strong>。方位__DIRS__。颜色__COLORS__。</div>
  <div class="act-item"><span class="num">2</span><em>行业选择：</em>优先 __YONG__ 属性相关行业，忌神五行行业需谨慎。</div>
  <div class="act-item"><span class="num">3</span><em>健康管理：</em>定期体检，关注五行偏枯对应的脏腑。作息规律，饮食均衡。</div>
  <div class="act-item"><span class="num">4</span><em>感情经营：</em>关注配偶星和配偶宫状态，理解命理提示的性格倾向，主动经营关系。</div>
  <div class="act-item"><span class="num">5</span><em>运势节奏：</em>用神运期间积极进取；忌神运期间保守稳健，以守为攻。</div>
  <div class="act-item"><span class="num">6</span><em>理性看待：</em>命理为传统民俗文化参考，提供自我认知视角，人生取决于选择与努力。</div>
</div>
<div class="ft">⚠ 以上分析综合了八字（子平术）和紫微斗数两套独立命理体系。<br>两者推算方法完全不同，当结论趋于一致时可信度更高。命理仅为传统民俗文化参考。</div>
</div></div></div>

<button class="guide-btn" onclick="toggleGuide()">?</button>
<div class="guide-overlay" id="guideOverlay" onclick="toggleGuide()"></div>
<div class="guide-panel" id="guidePanel">
  <h3>📖 怎么看这个页面</h3>
  <div class="tip"><span class="n">1</span> 顶部有 <b style="color:var(--g)">3 个标签</b>，点它们切换八字/紫微/双鉴。</div>
  <div class="tip"><span class="n">2</span> 八字标签：上面是排盘表和五行图，下面是<b style="color:var(--g)">白话卡片</b>和折叠分析。</div>
  <div class="tip"><span class="n">3</span> 紫微标签：中间大方块是<b style="color:var(--g)">十二宫星盘</b>，每个格子代表人生的一个方面。</div>
  <div class="tip"><span class="n">4</span> <b style="color:var(--b)">点击折叠面板的标题</b>可以展开看详细分析。</div>
  <div class="tip"><span class="n">5</span> 双鉴标签：交叉验证表告诉你<b style="color:var(--g)">八字和紫微的结论是否一致</b>。</div>
  <div class="tip"><span class="n">6</span> <b style="color:var(--gr)">绿色=好事</b>，<b style="color:var(--r)">红色=需注意</b>，<b style="color:var(--g)">金色=一般</b>。</div>
  <div class="tip"><span class="n">7</span> 右下角这个 <b style="color:var(--g)">? 按钮</b>，随时点它就能重新看到这份指南。</div>
  <div class="tip"><span class="n">8</span> 命理仅为<b>传统民俗文化参考</b>，不可全信。人生走向取决于你自己的选择和努力。</div>
</div>
<script>
function sw(n){document.querySelectorAll('.nav-btn').forEach(function(b){b.classList.remove('on')});document.querySelectorAll('.section-panel').forEach(function(t){t.classList.remove('on')});document.getElementById('tb-'+n).classList.add('on');event.target.classList.add('on')}
function toggleGuide(){document.getElementById('guidePanel').classList.toggle('open');document.getElementById('guideOverlay').classList.toggle('show')}
setTimeout(function(){document.getElementById('guidePanel').classList.add('open');document.getElementById('guideOverlay').classList.add('show')},600)
</script>
</body></html>'''


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
def wrap_standalone(title, content, extra_css=''):
    """Wrap content as standalone HTML document"""
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title}</title><style>
:root{{--bg:#0f0f14;--card:#1a1a24;--c2:#222232;--t:#d4d4dc;--g:#c9a96e;--p:#8b5cf6;--r:#e85d75;--b:#60a5fa;--gr:#4ade80;--bd:#2a2a3a;--wx-wood:#4ade80;--wx-fire:#f97316;--wx-earth:#a78b5a;--wx-metal:#e2e8a0;--wx-water:#38bdf8}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--t);font-family:'Segoe UI','Noto Sans SC','Microsoft YaHei',sans-serif;line-height:1.7;min-height:100vh}}
.hdr{{text-align:center;padding:36px 20px;margin-bottom:30px;background:linear-gradient(135deg,rgba(201,169,110,.06),rgba(139,92,246,.06));border:1px solid var(--bd);border-radius:18px}}
.hdr h1{{font-size:2em;background:linear-gradient(135deg,var(--g),#e2c98a,var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}}
.hdr .sub{{color:#888;font-size:.9em}}.hdr .meta{{display:inline-block;margin-top:12px;padding:6px 18px;background:var(--card);border:1px solid var(--bd);border-radius:20px;color:#888;font-size:.82em}}
.sh{{font-size:1.2em;color:var(--g);margin:32px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--bd)}}
.box{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:8px}}
.green{{color:var(--gr)}}.red{{color:var(--r)}}.dim{{color:#666}}
.bzt{{width:100%;border-collapse:collapse;margin-bottom:16px;border-radius:12px;overflow:hidden}}
.bzt th{{background:#2F5496;color:#fff;padding:12px;font-size:.85em}}.bzt td{{padding:12px;background:var(--card);border:1px solid var(--bd);text-align:center;font-size:.88em}}
.bzt .day-master{{color:var(--g);font-weight:700;font-size:1.05em}}
.wx-d{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:3px}}
.wx-bar{{height:18px;border-radius:9px;display:flex;overflow:hidden;margin-bottom:6px}}
.wx-lab{{display:flex;gap:14px;flex-wrap:wrap;font-size:.8em;color:#888;margin-bottom:16px}}
.sum{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}}
.vc{{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:24px 20px;transition:all .25s}}
.vc:hover{{border-color:var(--g);transform:translateY(-2px)}}
.vc .vc-icon{{font-size:1.8em;margin-bottom:6px}}
.vc h3{{font-size:1em;color:#bbb;margin-bottom:4px}}
.vc .big{{font-size:1.25em;font-weight:700;margin:6px 0 10px}}
.big.good{{color:var(--gr)}}.big.warn{{color:var(--r)}}.big.ok{{color:var(--g)}}
.vc .detail{{color:#999;font-size:.82em;line-height:1.7}}.vc .detail em{{color:#ccc;font-style:normal;font-weight:600}}
.vc .source{{font-size:.7em;color:#555;margin-top:10px;padding-top:10px;border-top:1px solid var(--bd)}}
.tg{{display:inline-block;padding:2px 8px;border-radius:5px;font-size:.75em;margin:2px}}
.tag-good{{background:rgba(74,222,128,.1);color:var(--gr);border:1px solid rgba(74,222,128,.2)}}
.tag-bad{{background:rgba(232,93,117,.1);color:var(--r);border:1px solid rgba(232,93,117,.2)}}
.tag-tip{{background:rgba(96,165,250,.08);color:var(--b);border:1px solid rgba(96,165,250,.2)}}
.fold{{margin-bottom:8px}}
.fold-hd{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 18px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:all .25s}}
.fold-hd:hover{{border-color:var(--g)}}.fold-hd h3{{font-size:.95em;color:#ddd}}
.fold-hd .arr{{transition:transform .3s;color:#666}}.fold-hd.open .arr{{transform:rotate(180deg)}}
.fold-bd{{max-height:0;overflow:hidden;transition:max-height .4s;background:var(--card);border-radius:0 0 10px 10px;padding:0 18px}}
.fold-bd.open{{max-height:2000px;padding:14px 18px;border:1px solid var(--bd);border-top:0}}
.dy-row{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}}
.dy-s{{flex:1;min-width:90px;background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:10px;text-align:center;transition:all .25s}}
.dy-s:hover{{border-color:var(--g)}}.dy-s.dy-y{{border-color:rgba(74,222,128,.3)}}.dy-s.dy-j{{border-color:rgba(232,93,117,.3)}}
.dy-a{{font-size:.65em;color:#666}}.dy-g{{font-size:1em;color:var(--g);font-weight:600;margin:2px 0}}
{extra_css}
</style></head><body><div class="wrap">{content}</div></body></html>'''

def generate(y, m, d, h, sex):
    bz = compute_bazi(y, m, d, h, sex)
    zw = compute_ziwei(y, m, d, h, sex)

    # Generate standalone bazi HTML
    bazi_standalone = wrap_standalone('八字命盘', gen_bazi_html(bz))
    # Generate standalone ziwei HTML
    ziwei_standalone = wrap_standalone('紫微斗数', gen_ziwei_html(zw),
        '.zw-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:20px}}'
        '.zw-p,.zw-c{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px;min-height:100px}}'
        '.zw-p.empty{{opacity:.6}}.zw-ctr{{text-align:center;color:var(--g);font-size:.9em;font-weight:700;line-height:1.8}}'
        '.zw-pn{{font-size:.75em;color:var(--g);font-weight:700;margin-bottom:4px}}.zw-pz{{float:right;color:#666;font-size:.7em}}'
        '.st-mjr{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.7em;color:var(--g);background:rgba(201,169,110,.1);border:1px solid rgba(201,169,110,.25)}}'
        '.st-mjr.mi{{color:#f59e0b}}.st-ji{{color:var(--gr);font-size:.68em}}.st-sha{{color:var(--r);font-size:.68em}}.st-si{{color:var(--b);font-size:.68em;font-weight:700}}'
        '.sh-ban{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}}'
        '.sh-c{{flex:1;min-width:160px;border-radius:10px;padding:14px;text-align:center;border:1px solid var(--bd)}}')

    bazi_escaped = html_mod.escape(bazi_standalone, quote=True)
    ziwei_escaped = html_mod.escape(ziwei_standalone, quote=True)

    # Load preferred wrapper template
    tpl_path = os.path.join(os.path.dirname(BASE), 'assets', 'preferred_template.html')
    with open(tpl_path, 'r', encoding='utf-8') as f:
        wrapper = f.read()

    # Replace srcdoc content
    import re
    # Find the two srcdoc iframes and replace their content
    srcdoc_matches = list(re.finditer(r'srcdoc=\"', wrapper))
    if len(srcdoc_matches) >= 2:
        # Replace first srcdoc (bazi)
        s1 = srcdoc_matches[0].end()
        e1 = wrapper.find('\" style=\"width:', s1)
        wrapper = wrapper[:s1] + bazi_escaped + wrapper[e1:]
        # Re-find second srcdoc (positions shifted)
        srcdoc_matches2 = list(re.finditer(r'srcdoc=\"', wrapper))
        s2 = srcdoc_matches2[1].end()
        e2 = wrapper.find('\" style=\"width:', s2)
        wrapper = wrapper[:s2] + ziwei_escaped + wrapper[e2:]

    # Replace hardcoded combined panel with dynamic content
    ch_start = wrapper.find('<div class="combined-header">')
    ch_end = wrapper.find('switchPanel', ch_start)
    if ch_start > 0 and ch_end > 0:
        combined_content = f'''<div class="combined-header">
      <h1>命运双鉴 · 综合交叉验证</h1>
      <div class="subtitle">八字（子平术）× 紫微斗数 —— 两套独立命理体系互相印证</div>
      <div style="margin-top:10px;color:#888;font-size:0.8em;">{bz['输入']['公历']} · {bz['输入']['性别']}命 · {bz['四柱']['年柱']['干支']}年</div>
    </div>
    <h2 style="color:var(--gold);margin-bottom:12px;font-size:1.1em;">📊 七维交叉验证表</h2>
    <table class="xref-table"><tr><th></th><th>八字（子平术）</th><th>紫微斗数</th><th>一致性分析</th></tr>
    {gen_cross_ref(bz, zw)}
    </table>
    <h2 style="color:var(--gold);margin:24px 0 12px;font-size:1.1em;">🎯 综合定论</h2>
    <div class="verdict-grid">
    {gen_verdict_cards(bz, zw)}
    </div>
    {gen_narrative(bz, zw)}
    <div class="actions"><h3 style="color:var(--gold);">📋 行动建议</h3>
    <div class="action-list">'''
        yong_str = ' · '.join(bz['用神分析']['用神'])
        combined_content += f'''<div class="action-item"><span class="num">1</span><em>用神方向：</em>有利五行 <strong>{yong_str}</strong>。方位{' · '.join({'木':'东','火':'南','土':'中','金':'西','水':'北'}[w] for w in bz['用神分析']['用神'])}。颜色{' · '.join({'木':'青绿','火':'红紫','土':'黄棕','金':'白','水':'黑蓝'}[w] for w in bz['用神分析']['用神'])}。</div>
    <div class="action-item"><span class="num">2</span><em>行业选择：</em>优先{yong_str}属性相关行业。</div>
    <div class="action-item"><span class="num">3</span><em>健康管理：</em>定期体检，关注五行偏枯对应的脏腑。</div>
    <div class="action-item"><span class="num">4</span><em>感情经营：</em>关注配偶星和配偶宫状态，主动经营关系。</div>
    <div class="action-item"><span class="num">5</span><em>运势节奏：</em>用神运积极进取，忌神运保守稳健。</div>
    <div class="action-item"><span class="num">6</span><em>理性看待：</em>命理为传统民俗文化参考，人生走向取决于自己的选择和努力。</div>
    </div></div>
    '''
        wrapper = wrapper[:ch_start-1] + combined_content + wrapper[ch_end:]

    # Cross-ref & verdicts
    xref_html = gen_cross_ref(bz, zw)
    verdict_html = gen_verdict_cards(bz, zw)
    narrative_html = gen_narrative(bz, zw)

    # Metadata
    bz_date = bz['输入']['公历']; bz_sex = bz['输入']['性别']
    bz_year = bz['四柱']['年柱']['干支']
    bz_rigan = bz['日主']['天干']; bz_riwx = bz['日主']['五行']; bz_sq = bz['用神分析']['身强身弱']

    zw_date = zw['输入']['公历']; zw_sex = zw['输入']['性别']
    zw_year = zw['年干支']; zw_ming = zw['命宫']; zw_shen = zw['身宫']; zw_wxj = zw['五行局']

    dual_date = bz_date; dual_sex = bz_sex; dual_year = bz_year

    yong = bz['用神分析']['用神']; yong_str = ' · '.join(yong)
    dirs = {'木':'东','火':'南','土':'中','金':'西','水':'北'}
    colors = {'木':'青绿','火':'红紫','土':'黄棕','金':'白','水':'黑蓝'}
    dirs_str = ' · '.join(dirs[w] for w in yong)
    colors_str = ' · '.join(colors[w] for w in yong)

    # Save wrapper HTML with replaced srcdoc content
    fname = f'命运双鉴_{y}{m:02d}{d:02d}_{sex}.html'
    out = os.path.join(os.path.dirname(BASE), fname)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(wrapper)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("用法: python generate_report.py <年> <月> <日> <时> <性别>")
        print("示例: python generate_report.py 2006 4 10 1 男")
        sys.exit(1)
    try:
        y, m, d, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        sex = sys.argv[5]
        if sex not in ('男', '女'):
            print("性别请输入「男」或「女」")
            sys.exit(1)
        if y < 1900 or y > 2100:
            print(f'⚠️  警告：{y}年超出精确计算范围(1900-2100)，农历转换和节气计算可能不够准确。')
        if m < 1 or m > 12 or d < 1 or d > 31 or h < 0 or h > 23:
            print("日期或时间不合法，请检查输入。")
            sys.exit(1)
        out = generate(y, m, d, h, sex)
        print(f'✅ 已生成: {out}')
        print(f'   大小: {os.path.getsize(out)/1024:.0f}KB')
    except Exception as e:
        print(f'❌ 错误: {e}')
        sys.exit(1)
