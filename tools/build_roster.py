#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端名单库 · 自动构建脚本
==========================
把 source/ 目录下的所有 .csv / .txt 合并，生成客户端要用的两个文件：

  roster.js    window.__ROSTER__ = "id1\nid2\n..."      （真正的名单库）
  version.js   window.__ROSTER_VERSION__ = "<内容指纹>"  （客户端比对用）

由 GitHub Actions 在 source/ 有变动时自动运行，平时不需要手动执行。
用法：python tools/build_roster.py
"""
import glob
import hashlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, 'source')


def decode(raw):
    """UTF-8 优先；乱码太多就回退 GBK（与工具端的判断口径保持一致）"""
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('utf-8', 'replace')
    if text.count('\ufffd') == 0:
        return text
    best, best_bad = text, text.count('\ufffd')
    for enc in ('gbk', 'gb18030'):
        try:
            got = raw.decode(enc)
        except Exception:
            continue
        if got.count('\ufffd') < best_bad:
            best, best_bad = got, got.count('\ufffd')
    return best


def ids_from(text):
    """CSV 取第一列；纯文本整行即一个数据ID"""
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        v = line.split(',')[0].replace('\ufeff', '').strip().strip('"').strip()
        if v:
            out.append(v)
    return out


def main():
    files = sorted(glob.glob(os.path.join(SRC_DIR, '*.csv')) +
                   glob.glob(os.path.join(SRC_DIR, '*.txt')))
    if not files:
        print('!! source/ 里没有找到 .csv 或 .txt')
        sys.exit(1)

    seen = {}          # 小写 -> 原始写法（先出现的为准，保证同一份数据指纹稳定）
    raw_total = 0
    for p in files:
        with open(p, 'rb') as f:
            got = ids_from(decode(f.read()))
        raw_total += len(got)
        for v in got:
            k = v.lower()
            if k not in seen:
                seen[k] = v
        print('  读入 %-36s %8d 条' % (os.path.basename(p), len(got)))

    ids = list(seen.values())
    body = '\n'.join(ids)

    # 版本号用「内容指纹」而不是时间戳 —— 内容没变就不会产生新版本，客户端不会白下载
    ver = hashlib.sha1(body.encode('utf-8')).hexdigest()[:12]
    built = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())

    with open(os.path.join(ROOT, 'version.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('window.__ROSTER_VERSION__="%s";\n' % ver)
        f.write('window.__ROSTER_COUNT__=%d;\n' % len(ids))
        f.write('window.__ROSTER_BUILT__="%s";\n' % built)

    with open(os.path.join(ROOT, 'roster.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('window.__ROSTER__="')
        f.write('\\n'.join(ids))
        f.write('";\n')

    print('')
    print('源文件     : %d 个' % len(files))
    print('原始行数   : %d' % raw_total)
    print('去重后     : %d（丢弃重复 %d）' % (len(ids), raw_total - len(ids)))
    print('版本指纹   : %s' % ver)
    print('生成时间   : %s' % built)
    print('roster.js  : %d bytes' % os.path.getsize(os.path.join(ROOT, 'roster.js')))
    print('version.js : %d bytes' % os.path.getsize(os.path.join(ROOT, 'version.js')))


if __name__ == '__main__':
    main()
