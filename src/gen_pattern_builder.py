#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""句型建筑师 数据生成脚本

把 data/pools.json + data/templates.json 渲染成 HTML 里的两个数据块。

    python gen_pattern_builder.py            # 渲染写回 HTML
    python gen_pattern_builder.py --check     # 只校验：HTML 与 JSON 源是否一致（不一致退出码 1）

HTML 里被管理的两块（首次运行 --init 时自动插入标记）：
    /* ===== VOCAB:BEGIN ===== */   ... 词池 / 短语 / 旧词   /* ===== VOCAB:END ===== */
    /* ===== TEMPLATE:BEGIN ===== */ ... TEMPLATES_DATA      /* ===== TEMPLATE:END ===== */

标记之间的内容一律由本脚本生成，手改会被下次渲染覆盖。
"""
import io, re, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, '句型建筑师.html')
POOLS = os.path.join(HERE, 'data', 'pools.json')
TEMPLATES = os.path.join(HERE, 'data', 'templates.json')

VOCAB_BEGIN = '    /* ===== VOCAB:BEGIN (由 gen_pattern_builder.py 生成，勿手改) ===== */\n'
VOCAB_END = '    /* ===== VOCAB:END ===== */'
TPL_BEGIN = '    /* ===== TEMPLATE:BEGIN (由 gen_pattern_builder.py 生成，勿手改) ===== */\n'
TPL_END = '    /* ===== TEMPLATE:END ===== */'


def js_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def render_pool(pool):
    name = pool['name']
    kind = pool.get('kind', 'items')
    items = pool['items']
    out = []
    if kind == 'items':
        out.append('    const %s = [' % name)
        line = '        '
        for it in items:
            parts = ['en: %s' % js_str(it['en']), 'zh: %s' % js_str(it.get('zh', ''))]
            for k, v in it.items():
                if k in ('en', 'zh'):
                    continue
                if isinstance(v, bool):
                    parts.append('%s: %s' % (k, 'true' if v else 'false'))
                else:
                    parts.append('%s: %s' % (k, js_str(str(v))))
            item = '{ %s }' % ', '.join(parts)
            if len(line) + len(item) + 2 > 100 and line.strip():
                out.append(line.rstrip())
                line = '        '
            line += item + ', '
        if line.strip():
            out.append(line.rstrip())
        out.append('    ];')
    elif kind == 'strings':
        out.append('    const %s = [' % name)
        line = '        '
        for it in items:
            tok = js_str(it) + ', '
            if len(line) + len(tok) > 100 and line.strip():
                out.append(line.rstrip())
                line = '        '
            line += tok
        if line.strip():
            out.append(line.rstrip())
        out.append('    ];')
    elif kind == 'set':
        out.append('    const %s = new Set([' % name)
        line = '        '
        for it in items:
            tok = js_str(it) + ', '
            if len(line) + len(tok) > 100 and line.strip():
                out.append(line.rstrip())
                line = '        '
            line += tok
        if line.strip():
            out.append(line.rstrip())
        out.append('    ]);')
    else:
        raise ValueError('未知 kind: %s' % kind)
    return '\n'.join(out)


def render_vocab(pools_data):
    return '\n'.join(render_pool(pools_data['pools'][n]) for n in pools_data['order'])


def render_slots(slots, indent):
    """槽位对象。值可以是池名（标识符）或内联数组。"""
    keys = list(slots.keys())
    if not keys:
        return '{}'
    simple = all(isinstance(slots[k], str) and slots[k] for k in keys)
    if simple:
        return '{ %s }' % ', '.join('%s: %s' % (js_str(k), slots[k]) for k in keys)
    out = ['{']
    for k in keys:
        v = slots[k]
        if isinstance(v, str):
            out.append('%s%s: %s,' % (indent, js_str(k), v))
        else:
            out.append('%s%s: [' % (indent, js_str(k)))
            line = indent + '    '
            for it in v:
                parts = ['en: %s' % js_str(it['en']), 'zh: %s' % js_str(it.get('zh', ''))]
                for kk, vv in it.items():
                    if kk in ('en', 'zh'):
                        continue
                    parts.append('%s: %s' % (kk, 'true' if vv is True else js_str(str(vv))))
                item = '{ %s }, ' % ', '.join(parts)
                if len(line) + len(item) > 104 and line.strip():
                    out.append(line.rstrip())
                    line = indent + '    '
                line += item
            if line.strip():
                out.append(line.rstrip())
            out.append('%s],' % indent)
    out.append(indent[:-4] + '}')
    return '\n'.join(out)


def render_templates(tpl_data):
    out = ['    const TEMPLATES_DATA = {']
    order = tpl_data['order']
    for ui, u in enumerate(order):
        unit = tpl_data['units'][u]
        out.append('        %s: {' % js_str(u))
        out.append('            desc: %s,' % js_str(unit.get('desc', '')))
        out.append('            templates: [')
        tpls = unit['templates']
        for ti, t in enumerate(tpls):
            body = 'en: %s, zh: %s' % (js_str(t['en']), js_str(t['zh']))
            if t.get('hint'):
                body += ', hint: %s' % js_str(t['hint'])
            if t.get('swap'):
                body += ', swap: { en: %s, zh: %s }' % (js_str(t['swap']['en']), js_str(t['swap']['zh']))
            slots = render_slots(t.get('slots') or {}, ' ' * 20)
            if '\n' in slots:
                out.append('                { %s, slots: %s },' % (body, slots))
            else:
                out.append('                { %s, slots: %s },' % (body, slots))
        if out[-1].endswith(','):
            out[-1] = out[-1][:-1]
        out.append('            ]')
        out.append('        }%s' % ('' if ui == len(order) - 1 else ','))
    out.append('    };')
    return '\n'.join(out)


def balance(t, i, o, c):
    d = 0
    while i < len(t):
        if t[i] == o: d += 1
        elif t[i] == c:
            d -= 1
            if d == 0: return i
        i += 1
    raise ValueError('unbalanced')


def find_decl_span(html, names):
    lo, hi = None, None
    for n in names:
        m = re.search(r'\n    const ' + re.escape(n) + r' = ', html)
        if not m:
            continue
        st = m.start() + 1
        eq = html.index('[', m.end())
        en = html.index(';', balance(html, eq, '[', ']')) + 1
        lo = st if lo is None else min(lo, st)
        hi = en if hi is None else max(hi, en)
    return lo, hi


def main():
    check = '--check' in sys.argv
    html = io.open(HTML, encoding='utf-8').read()
    pools_data = json.loads(io.open(POOLS, encoding='utf-8').read())
    tpl_data = json.loads(io.open(TEMPLATES, encoding='utf-8').read())

    vocab = render_vocab(pools_data)
    tpls = render_templates(tpl_data)

    if 'VOCAB:BEGIN' in html:
        html = re.sub(r'    /\* ===== VOCAB:BEGIN.*?\*/.*?    /\* ===== VOCAB:END ===== \*/',
                      lambda m: VOCAB_BEGIN + vocab + '\n' + VOCAB_END, html, flags=re.S)
    else:
        lo, hi = find_decl_span(html, pools_data['order'])
        if lo is None:
            raise SystemExit('找不到词池声明，无法插入标记')
        html = html[:lo] + VOCAB_BEGIN + vocab + '\n' + VOCAB_END + html[hi:]

    if 'TEMPLATE:BEGIN' in html:
        html = re.sub(r'    /\* ===== TEMPLATE:BEGIN.*?\*/.*?    /\* ===== TEMPLATE:END ===== \*/',
                      lambda m: TPL_BEGIN + tpls + '\n' + TPL_END, html, flags=re.S)
    else:
        m = re.search(r'    const TEMPLATES_DATA = \{', html)
        st = m.start()
        eq = html.index('{', m.end() - 1)
        en = html.index(';', balance(html, eq, '{', '}')) + 1
        html = html[:st] + TPL_BEGIN + tpls + '\n' + TPL_END + html[en:]

    cur = io.open(HTML, encoding='utf-8').read()
    if check:
        if cur == html:
            print('OK: HTML 与 JSON 源一致')
            return 0
        print('DRIFT: HTML 与 JSON 源不一致 —— 要么跑一次不带 --check 的渲染，'
              '要么你手改过被管理的块（会被覆盖）')
        return 1
    io.open(HTML, 'w', encoding='utf-8', newline='').write(html)
    print('已渲染：词池 %d 个 / 单元 %d 个 / 模板 %d 条'
          % (len(pools_data['order']), len(tpl_data['order']),
             sum(len(u['templates']) for u in tpl_data['units'].values())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
