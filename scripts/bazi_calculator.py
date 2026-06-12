#!/usr/bin/env python3
"""八字计算引擎 - 纯Python，零依赖"""
import json, sys, io
from datetime import date, timedelta
from math import floor
from typing import Dict, List, Tuple

TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DI_ZHI   = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
SHENGXIAO = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]

GAN_WX = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
ZHI_WX = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
GAN_YY = {"甲":1,"丙":1,"戊":1,"庚":1,"壬":1,"乙":0,"丁":0,"己":0,"辛":0,"癸":0}

ZHI_CANG = {"子":["癸"],"丑":["己","癸","辛"],"寅":["甲","丙","戊"],"卯":["乙"],"辰":["戊","乙","癸"],"巳":["丙","戊","庚"],"午":["丁","己"],"未":["己","丁","乙"],"申":["庚","壬","戊"],"酉":["辛"],"戌":["戊","辛","丁"],"亥":["壬","甲"]}

NAYIN = ["海中金","炉中火","大林木","路旁土","剑锋金","山头火","涧下水","城头土","白蜡金","杨柳木","泉中水","屋上土","霹雳火","松柏木","长流水","沙中金","山下火","平地木","壁上土","金箔金","覆灯火","天河水","大驿土","钗钏金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]

CHANGSHENG_ORDER = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]
CHANGSHENG_START = {"甲":"亥","乙":"午","丙":"寅","丁":"酉","戊":"寅","己":"酉","庚":"巳","辛":"子","壬":"申","癸":"卯"}

# ── 节气计算 ──
def _solar_term_date(year, degrees):
    """太阳到达指定黄经的近似日期"""
    spring_eq = 20.69115 + 0.2422*(year-1900) - floor((year-1900)/4)
    sd = max(19, min(22, int(spring_eq)))
    spr = date(year, 3, sd)
    off = (degrees // 15) * 15.218425
    return spr + timedelta(days=int(off))

JIE_NAMES = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
JIE_ZHI   = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]
JIE_DEG   = [315,345,15,45,75,105,135,165,195,225,255,285]

def get_jie_dates(year):
    result = []
    for i in range(12):
        d = _solar_term_date(year, JIE_DEG[i])
        result.append((JIE_NAMES[i], JIE_ZHI[i], d))
    # 添加次年小寒用于1月判断
    d2 = _solar_term_date(year+1, 285)
    result.append(("小寒(次年)", "丑", d2))
    result.sort(key=lambda x: x[2])
    return result

def get_month_pillar(year, month, day):
    d = date(year, month, day)
    jies = get_jie_dates(year)
    eff_year, month_zhi, jie_name = year, "寅", "立春"
    for i, (jn, jz, jd) in enumerate(jies):
        if d >= jd:
            month_zhi, jie_name = jz, jn
            if jn in ("小寒", "小寒(次年)") and month <= 2:
                ni = i+1
                if ni < len(jies) and jies[ni][0] == "立春" and d < jies[ni][2]:
                    eff_year = year-1
                    break
            eff_year = year
        else:
            if i == 0: eff_year, month_zhi, jie_name = year-1, "丑", "小寒"
            break
    return eff_year, month_zhi, jie_name

# ── 核心计算 ──
def _ganzhi_year(year):
    idx = (year-4)%60
    return TIAN_GAN[idx%10], DI_ZHI[idx%12]

def _day_ganzhi_idx(d):
    return ((d - date(1900,1,1)).days + 10) % 60

def _yue_gan(year_gan, month_zhi):
    start = {"甲":2,"己":2, "乙":4,"庚":4, "丙":6,"辛":6, "丁":8,"壬":8, "戊":0,"癸":0}
    mz_idx = DI_ZHI.index(month_zhi)
    return TIAN_GAN[(start[year_gan] + (mz_idx-2)%12) % 10]

def _shi_gan(ri_gan, shi_zhi):
    start = {"甲":0,"己":0, "乙":2,"庚":2, "丙":4,"辛":4, "丁":6,"壬":6, "戊":8,"癸":8}
    return TIAN_GAN[(start[ri_gan] + DI_ZHI.index(shi_zhi)) % 10]

def _shishen(ri_gan, other_gan):
    rw, ow = GAN_WX[ri_gan], GAN_WX[other_gan]
    same_yy = "+" if GAN_YY[ri_gan]==GAN_YY[other_gan] else "-"
    order_s = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    order_k = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    if rw==ow: rel=("同",same_yy)
    elif order_s.get(ow)==rw: rel=("生我",same_yy)
    elif order_s.get(rw)==ow: rel=("我生",same_yy)
    elif order_k.get(ow)==rw: rel=("克我",same_yy)
    elif order_k.get(rw)==ow: rel=("我克",same_yy)
    else: return "?"
    names = {("同","+"):"比肩",("同","-"):"劫财",("生我","+"):"偏印",("生我","-"):"正印",("我生","+"):"食神",("我生","-"):"伤官",("克我","+"):"七杀",("克我","-"):"正官",("我克","+"):"偏财",("我克","-"):"正财"}
    return names.get(rel,"?")

def _changsheng(gan, zhi):
    start = CHANGSHENG_START[gan]
    s_idx, z_idx = DI_ZHI.index(start), DI_ZHI.index(zhi)
    if GAN_YY[gan]==1: offset = (z_idx-s_idx)%12
    else: offset = (s_idx-z_idx)%12
    return CHANGSHENG_ORDER[offset]

def _nayin(gz_idx):
    return NAYIN[gz_idx//2%30]

def _dayun(year_gan, sex, month_gz, birth):
    is_yang = GAN_YY[year_gan]==1
    shun = (is_yang and sex=="男") or (not is_yang and sex=="女")
    all_jies = []
    for y in [birth.year-1, birth.year, birth.year+1]:
        for jn, jz, jd in get_jie_dates(y):
            all_jies.append((jn, jd))
    all_jies.sort(key=lambda x: x[1])
    if shun:
        target = next((jd for _, jd in all_jies if jd > birth), None)
        days = (target-birth).days if target else 30
    else:
        rev = [(jd, jn) for jn, jd in reversed(all_jies) if jd < birth]
        target = rev[0][0] if rev else birth-timedelta(days=30)
        days = (birth-target).days
    qiyun = max(1, round(days/3))
    mg, mz = month_gz[0], month_gz[1]
    mgi, mzi = TIAN_GAN.index(mg), DI_ZHI.index(mz)
    dayun = []
    for i in range(1, 9):
        step = i if shun else -i
        gi, zi = (mgi+step)%10, (mzi+step)%12
        gz = TIAN_GAN[gi]+DI_ZHI[zi]
        age = qiyun+(i-1)*10
        dayun.append({"步":i,"干支":gz,"天干":TIAN_GAN[gi],"地支":DI_ZHI[zi],"天干五行":GAN_WX[TIAN_GAN[gi]],"地支五行":ZHI_WX[DI_ZHI[zi]],"纳音":_nayin(gi*12+zi),"起运年龄":age,"年龄段":f"{age}-{age+9}岁"})
    return {"排法":"顺排" if shun else "逆排","起运年龄":qiyun,"大运列表":dayun}

def _yongshen(ri_gan, month_zhi, wx_count):
    ri_wx = GAN_WX[ri_gan]; total = sum(wx_count.values())
    ratio = wx_count.get(ri_wx,0)/total if total else 0
    order_k = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    order_s = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    if ratio > 0.3:
        sq = "身强"; yong = []
        for w in ["木","火","土","金","水"]:
            if w==ri_wx: continue
            if order_k.get(w,None)==ri_wx: yong.append(w)
            if order_s.get(ri_wx,None)==w: yong.append(w)
            if order_k.get(ri_wx,None)==w: yong.append(w)
        yong = list(set(yong))
    else:
        sq = "身弱"; yong = []
        for w in ["木","火","土","金","水"]:
            if order_s.get(w,None)==ri_wx: yong.append(w)
        yong.append(ri_wx)
    mwx = ZHI_WX[month_zhi]; th = None
    if mwx=="火" and "水" not in yong: th="水(调候降温)"; yong.append("水")
    if mwx=="水" and "火" not in yong: th="火(调候暖局)"; yong.append("火")
    ji = [w for w in ["木","火","土","金","水"] if w not in yong]
    return {"身强身弱":sq,"日主力量占比":f"{ratio:.0%}","用神":yong[:3],"忌神":ji,"调候需求":th}

def check_conflicts(zhis):
    chong = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
    hai = {"子":"未","未":"子","丑":"午","午":"丑","寅":"巳","巳":"寅","卯":"辰","辰":"卯","申":"亥","亥":"申","酉":"戌","戌":"酉"}
    triples = [(["申","子","辰"],"水局"),(["亥","卯","未"],"木局"),(["寅","午","戌"],"火局"),(["巳","酉","丑"],"金局")]
    names = list(zhis.keys()); vals = list(zhis.values()); conflicts = []
    for i in range(4):
        for j in range(i+1,4):
            a, b = vals[i], vals[j]
            if chong.get(a)==b: conflicts.append({"关系":"六冲","涉及":f"{names[i]}({a})↔{names[j]}({b})","原理":f"{a}与{b}对冲"})
            if hai.get(a)==b: conflicts.append({"关系":"六害","涉及":f"{names[i]}({a})↔{names[j]}({b})","原理":f"{a}与{b}相害"})
    for tri, nm in triples:
        found = [v for v in tri if v in vals]
        if len(found)>=2: conflicts.append({"关系":"三合" if len(found)==3 else "半合","涉及":f"{'·'.join(found)}合{nm}","原理":f"力量凝聚增强"})
    for v in {"辰","午","酉","亥"}:
        if vals.count(v)>=2:
            for i,n in enumerate(names):
                if vals[i]==v: conflicts.append({"关系":"自刑","涉及":f"{n}({v})","原理":f"{v}自刑→内心纠结"})
    return conflicts

def compute_bazi(year, month, day, hour, sex):
    birth = date(year, month, day)
    eff_year, month_zhi, jie_name = get_month_pillar(year, month, day)
    year_gan, year_zhi = _ganzhi_year(eff_year)
    month_gan = _yue_gan(year_gan, month_zhi)
    ri_idx = _day_ganzhi_idx(birth)
    ri_gan, ri_zhi = TIAN_GAN[ri_idx%10], DI_ZHI[ri_idx%12]
    shi_zhi = DI_ZHI[((hour+1)//2)%12]
    shi_gan = _shi_gan(ri_gan, shi_zhi)
    cols = [("年柱",year_gan,year_zhi,eff_year),("月柱",month_gan,month_zhi,None),("日柱",ri_gan,ri_zhi,None),("时柱",shi_gan,shi_zhi,None)]
    pillars, wx_count = {}, {"木":0,"火":0,"土":0,"金":0,"水":0}
    for name, gan, zhi, yr in cols:
        p = {"天干":gan,"地支":zhi,"干支":gan+zhi,"天干五行":GAN_WX[gan],"地支五行":ZHI_WX[zhi],"藏干":ZHI_CANG[zhi],"纳音":_nayin((TIAN_GAN.index(gan)*12+DI_ZHI.index(zhi))%60),"藏干十神":[{"干":c,"十神":_shishen(ri_gan,c)} for c in ZHI_CANG[zhi]],"日主十二长生在此":_changsheng(ri_gan,zhi)}
        if name=="年柱": p["生肖"]=SHENGXIAO[DI_ZHI.index(zhi)]
        if name=="日柱": p["日主"]=ri_gan; p["日主五行"]=GAN_WX[ri_gan]; p["日主阴阳"]="阳" if GAN_YY[ri_gan] else "阴"
        pillars[name] = p
        wx_count[GAN_WX[gan]] += 2; wx_count[ZHI_WX[zhi]] += 3
    shishen_map = {n:{"天干十神":_shishen(ri_gan,pillars[n]["天干"]),"本气十神":_shishen(ri_gan,pillars[n]["藏干"][0])} for n in ["年柱","月柱","日柱","时柱"]}
    zhis = {n:pillars[n]["地支"] for n in ["年柱","月柱","日柱","时柱"]}
    conflicts = check_conflicts(zhis)
    dayun = _dayun(year_gan, sex, month_gan+month_zhi, birth)
    yongshen = _yongshen(ri_gan, month_zhi, wx_count)
    return {"输入":{"公历":f"{year}年{month}月{day}日 {hour}时","性别":sex},"节气":jie_name,"八字":f"{pillars['年柱']['干支']} {pillars['月柱']['干支']} {pillars['日柱']['干支']} {pillars['时柱']['干支']}","四柱":pillars,"十神标注":shishen_map,"日主":{"天干":ri_gan,"五行":GAN_WX[ri_gan],"阴阳":"阳" if GAN_YY[ri_gan] else "阴"},"五行分布":wx_count,"地支关系":{"冲突列表":conflicts},"大运":dayun,"用神分析":yongshen}

if __name__=="__main__":
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
    if len(sys.argv)<6: print("用法: python bazi_calculator.py <年> <月> <日> <时> <性别>"); sys.exit(1)
    y,m,d,h=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]); sex=sys.argv[5]
    print(json.dumps(compute_bazi(y,m,d,h,sex),ensure_ascii=False,indent=2))
