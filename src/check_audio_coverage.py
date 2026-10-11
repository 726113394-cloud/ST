# -*- coding: utf-8 -*-
"""检查「工具能生成的所有句子」在 audio/ 里有多少整句录音，并列出缺的。

用法：python check_audio_coverage.py
"""
import io, json, os, re, itertools, sys

PROJ = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(PROJ, 'audio')
pools = json.loads(io.open(os.path.join(PROJ, 'data', 'pools.json'), encoding='utf-8').read())
tpls = json.loads(io.open(os.path.join(PROJ, 'data', 'templates.json'), encoding='utf-8').read())


def items(p):
    return pools['pools'].get(p, {}).get('items', []) if isinstance(p, str) else p


def fnv1a8(t):
    h = 0x811C9DC5
    for b in t.encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return '%08x' % h


def sentence_file_name(t):
    slug = ''
    for ch in t:
        slug += ch if re.match(r'[A-Za-z0-9]', ch) else '_'
        if len(slug) >= 40:
            break
    return slug + '__' + fnv1a8(t) + '.mp3'


def fill(t, c):
    en = t['en']
    for k, v in c.items():
        en = en.replace('{%s}' % k, v['en'])
    subs = [v for v in c.values() if v.get('num')]
    en = en.replace('{be}', 'are' if subs and subs[0]['num'] == 'p' else 'is')
    if not re.search(r'[.?!]$', en):
        en += '.'
    return en


sents = set()
for u in tpls['order']:
    for t in tpls['units'][u]['templates']:
        sl = t.get('slots') or {}
        ks = list(sl.keys())
        combos = [dict(zip(ks, c)) for c in itertools.product(*[items(sl[k]) for k in ks])] if ks else [{}]
        for c in combos:
            sents.add(fill(t, c))

have = [s for s in sents if os.path.exists(os.path.join(A, sentence_file_name(s)))]
miss = [s for s in sents if not os.path.exists(os.path.join(A, sentence_file_name(s)))]
print('可生成句子 %d，有整句录音 %d (%.1f%%)，缺 %d' % (len(sents), len(have), 100.0 * len(have) / max(1, len(sents)), len(miss)))
for s in miss[:20]:
    print('   缺: ' + s)
sys.exit(1 if miss else 0)
