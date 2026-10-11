# -*- coding: utf-8 -*-
"""内容审计：把 30 个单元所有可生成句子跑一遍，挑出这类数据问题 —— 
连续重复词、重复标点、空槽位、标点开头、双空格、连续两个 the/a 等。
（这类问题代码审查看不出来，必须逐句扫。）
"""
import io, json, os, re, itertools

PROJ = r"C:\Users\Administrator\Desktop\句型建筑师"
pools = json.loads(io.open(os.path.join(PROJ, 'data', 'pools.json'), encoding='utf-8').read())
tpls = json.loads(io.open(os.path.join(PROJ, 'data', 'templates.json'), encoding='utf-8').read())


def items(p):
    return pools['pools'].get(p, {}).get('items', []) if isinstance(p, str) else p


def fill(t, c):
    en = t['en']
    for k, v in c.items():
        en = en.replace('{%s}' % k, v['en'])
    subs = [v for v in c.values() if v.get('num')]
    en = en.replace('{be}', 'are' if subs and subs[0]['num'] == 'p' else 'is')
    if not re.search(r'[.?!]$', en):
        en += '.'
    return en


problems = []
total = 0
for u in tpls['order']:
    for t in tpls['units'][u]['templates']:
        sl = t.get('slots') or {}
        ks = list(sl.keys())
        combos = [dict(zip(ks, c)) for c in itertools.product(*[items(sl[k]) for k in ks])] if ks else [{}]
        for c in combos:
            s = fill(t, c)
            total += 1
            issues = []
            low = s.lower()
            if re.search(r'\b(\w+)\s+\1\b', low):
                issues.append('连续重复词: ' + re.search(r'\b(\w+)\s+\1\b', low).group(0))
            if re.search(r'[.,!?]{2,}', s):
                issues.append('重复标点: ' + re.search(r'[.,!?]{2,}', s).group(0))
            if re.search(r'\{[^}]*\}', s):
                issues.append('未替换的槽位')
            if re.search(r'\b(the|a|an)\s+(the|a|an)\b', low):
                issues.append('连续冠词: ' + re.search(r'\b(the|a|an)\s+(the|a|an)\b', low).group(0))
            if s.startswith(('.', ',', '?', '!')):
                issues.append('以标点开头')
            if '  ' in s:
                issues.append('双空格')
            if not re.match(r'^[A-Z]', s):
                issues.append('首字母未大写: ' + s[:12])
            if issues:
                problems.append((u, t['en'], s, issues))

print('句子总数 %d，有问题 %d 条' % (total, len(problems)))
seen_tpl = set()
for u, tpl, s, iss in problems:
    key = (u, tpl, tuple(iss))
    print('  [%s] %-46s %s' % (u, s[:46], '; '.join(iss)))
    seen_tpl.add(key)
print('\n按模板归类（共 %d 个模板受影响）:' % len(set((u, t) for u, t, _, _ in problems)))
for u, t in sorted(set((u, t) for u, t, _, _ in problems)):
    print('  [%s] %s' % (u, t))
