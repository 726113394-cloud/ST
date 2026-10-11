# -*- coding: utf-8 -*-
"""audio/ 瘦身：只保留这个工具真正会用到的文件。

保留：
  1. 工具能生成的全部句子 → 对应的整句录音
  2. 这些句子里出现过的所有单词 → 对应的单词录音（离线逐词拼接兜底要用）
删除：
  - 别的工具留下的整句录音（本工具生成不出来的）
  - 用不到的单词录音

用法：python trim_audio.py --dry-run   只看会删什么
      python trim_audio.py             真删
"""
import io, json, os, re, itertools, sys

PROJ = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(PROJ, 'audio')
pools = json.loads(io.open(os.path.join(PROJ, 'data', 'pools.json'), encoding='utf-8').read())
tpls = json.loads(io.open(os.path.join(PROJ, 'data', 'templates.json'), encoding='utf-8').read())
DRY = '--dry-run' in sys.argv


def items(p):
    return pools['pools'].get(p, {}).get('items', []) if isinstance(p, str) else p


def fnv1a8(t):
    h = 0x811C9DC5
    for b in t.encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return '%08x' % h


def sentence_file_name(t):
    s = ''
    for ch in t:
        s += ch if re.match(r'[A-Za-z0-9]', ch) else '_'
        if len(s) >= 40:
            break
    return s + '__' + fnv1a8(t) + '.mp3'


def fill(t, c):
    en = t['en']
    for k, v in c.items():
        en = en.replace('{%s}' % k, v['en'])
    subs = [v for v in c.values() if v.get('num')]
    en = en.replace('{be}', 'are' if subs and subs[0]['num'] == 'p' else 'is')
    if not re.search(r'[.?!]$', en):
        en += '.'
    return en


keep_sent = set()
keep_word = set()
for u in tpls['order']:
    for t in tpls['units'][u]['templates']:
        sl = t.get('slots') or {}
        ks = list(sl.keys())
        combos = [dict(zip(ks, c)) for c in itertools.product(*[items(sl[k]) for k in ks])] if ks else [{}]
        for c in combos:
            s = fill(t, c)
            keep_sent.add(sentence_file_name(s))
            for w in re.findall(r"[A-Za-z'\-]+", s):
                keep_word.add(w.lower())

files = os.listdir(A)
drop = []
for f in files:
    if '__' in f:
        if f not in keep_sent:
            drop.append(f)
    else:
        if f[:-4].lower() not in keep_word:
            drop.append(f)

size = sum(os.path.getsize(os.path.join(A, f)) for f in drop)
total = sum(os.path.getsize(os.path.join(A, f)) for f in files)
print('现有 %d 个文件 %.1f MB' % (len(files), total / 1048576))
print('要删 %d 个 %.1f MB（其中整句 %d 个，单词 %d 个）' % (
    len(drop), size / 1048576,
    len([f for f in drop if '__' in f]), len([f for f in drop if '__' not in f])))
print('保留 %d 个 %.1f MB' % (len(files) - len(drop), (total - size) / 1048576))
if DRY:
    print('（dry-run，未删除）')
    for f in drop[:10]:
        print('   会删: ' + f)
    sys.exit(0)
for f in drop:
    os.remove(os.path.join(A, f))
print('已删除。')
