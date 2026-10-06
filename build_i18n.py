#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build language versions of the hand-written pages + patch German pages with
hreflang cluster, language switcher and browser-language redirect."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import (LANGS, LOCALES, T, F, fmt, tr, tr_cuisine,
                  lang_prefix, localized, hreflang_block, lang_switcher,
                  LANGSW_CSS, REDIRECT_SCRIPT, CHOICE_SCRIPT)

ROOT = os.path.dirname(os.path.abspath(__file__))
HANDWRITTEN = ['index.html',
               'restaurants/anatolia-nendeln/index.html',
               'orte/nendeln/index.html',
               'impressum/index.html',
               'datenschutz/index.html']

def page_path(rel):
    d = os.path.dirname(rel)
    return '/' + (d + '/' if d else '')

# replacement keys: longest first so specific phrases win over fragments
KEYS = sorted(T.keys(), key=len, reverse=True)
# exact-match map for whole text nodes (keys without HTML entities and with)
EXACT = {}
for k in KEYS:
    EXACT[k] = k
    if '&amp;' in k:
        EXACT[k.replace('&amp;', '&')] = k
SHORT = 24  # keys shorter than this only match whole text nodes, never substrings

TAG_RE = re.compile(r'(<[^>]+>)')
ATTR_RE = re.compile(r'((?:content|placeholder|alt|title|aria-label)=")([^"]*)(")')

def _tr_node(text, lang):
    """Translate one text node. Exact match preferred; substring only for long keys."""
    if not text.strip():
        return text
    stripped = text.strip()
    key = EXACT.get(stripped)
    if key and lang in T[key]:
        return text.replace(stripped, T[key][lang])
    out = text
    for k in KEYS:
        if len(k) < SHORT or lang not in T[k]:
            continue
        if k in out:
            out = out.replace(k, T[k][lang])
        elif '&amp;' in k and k.replace('&amp;', '&') in out:
            out = out.replace(k.replace('&amp;', '&'), T[k][lang].replace('&amp;', '&'))
    # "Essen bestellen in X" patterns (whole-node matches)
    def sub_town_plz(m):
        return fmt('order_in_town_plz', lang, city=m.group(1).strip(), postal=m.group(2))
    stripped2 = re.sub(r'^Essen bestellen in ([^<()]{2,40}) \((\d{4})\)$', sub_town_plz, stripped)
    if stripped2 != stripped:
        return text.replace(stripped, stripped2)
    m = re.match(r'^Essen bestellen in ([A-ZÄÖÜ][\wäöüÄÖÜéè .\-]{1,40})$', stripped)
    if m:
        return text.replace(stripped, fmt('order_in_town', lang, city=m.group(1).strip()))
    return out

def _tr_attr(m, lang):
    val = m.group(2)
    key = EXACT.get(val)
    if key and lang in T[key]:
        return m.group(1) + T[key][lang] + m.group(3)
    out = val
    for k in KEYS:
        if len(k) < SHORT or lang not in T[k]:
            continue
        if k in out:
            out = out.replace(k, T[k][lang])
    return m.group(1) + out + m.group(3)

def translate_text(html_doc, lang):
    """Translate only real text nodes + attributes. Scripts, styles and
    data-URIs are never touched."""
    # protect script/style blocks and base64 payloads
    protected = []
    def stash(m):
        protected.append(m.group(0))
        return '\x00%d\x00' % (len(protected) - 1)
    doc = re.sub(r'<script.*?</script>', stash, html_doc, flags=re.S)
    doc = re.sub(r'<style.*?</style>', stash, doc, flags=re.S)
    doc = re.sub(r'data:image/[^"\']+', stash, doc)
    # translate attributes inside tags
    doc = TAG_RE.sub(lambda m: ATTR_RE.sub(lambda a: _tr_attr(a, lang), m.group(1))
                     if m.group(1).startswith('<') else m.group(1), doc)
    # translate text nodes (segments between tags)
    parts = TAG_RE.split(doc)
    for i, p in enumerate(parts):
        if p and not p.startswith('<'):
            parts[i] = _tr_node(p, lang)
    doc = ''.join(parts)
    # <title> content
    doc = re.sub(r'(<title>)([^<]+)(</title>)',
                 lambda m: m.group(1) + _tr_node(m.group(2), lang) + m.group(3), doc)
    # homepage JS data: cuisine labels (inside the protected script — restore first)
    def unstash(m):
        return protected[int(m.group(1))]
    doc = re.sub(r'\x00(\d+)\x00', unstash, doc)
    def sub_kueche(m):
        return 'kueche: "' + tr_cuisine(m.group(1), lang) + '"'
    doc = re.sub(r'kueche: "([^"]+)"', sub_kueche, doc)
    return doc

def rewrite_urls(html_doc, lang):
    """Prefix internal absolute links with the language folder."""
    pre = '/' + lang
    html_doc = html_doc.replace('https://clickandfood.global/', 'https://clickandfood.global' + pre + '/')
    html_doc = re.sub(r'href="/(?!' + lang + r'/)', 'href="' + pre + '/', html_doc)
    html_doc = re.sub(r'src="/(?!' + lang + r'/)', 'src="' + pre + '/', html_doc)
    return html_doc

def patch_head(html_doc, path, lang, is_de):
    # html lang attribute
    html_doc = html_doc.replace('<html lang="de">', '<html lang="%s">' % lang, 1)
    # og:locale
    html_doc = re.sub(r'(<meta property="og:locale" content=")[a-z_]+(")', r'\g<1>' + LOCALES[lang] + r'\g<2>', html_doc)
    # replace existing alternate links with the full cluster
    html_doc = re.sub(r'[ \t]*<link rel="alternate"[^>]*>\n?', '', html_doc)
    html_doc = html_doc.replace('</head>', hreflang_block(path) + '\n</head>', 1)
    # switcher CSS
    html_doc = html_doc.replace('</style>', LANGSW_CSS + '</style>', 1)
    # redirect / choice script
    script = REDIRECT_SCRIPT if is_de else CHOICE_SCRIPT
    html_doc = html_doc.replace('</head>', script + '\n</head>', 1)
    return html_doc

def inject_switcher(html_doc, path, lang):
    sw = lang_switcher(path, lang)
    # insert after the header nav </ul>
    m = re.search(r'(</ul>)', html_doc)
    if m:
        html_doc = html_doc[:m.end()] + '\n    ' + sw + html_doc[m.end():]
    return html_doc

def build():
    de_report = {}
    for rel in HANDWRITTEN:
        src = open(os.path.join(ROOT, rel)).read()
        path = page_path(rel)
        # --- German original: add switcher + hreflang + redirect (idempotent) ---
        if 'class="langsw"' not in src:
            de = patch_head(src, path, 'de', True)
            de = inject_switcher(de, path, 'de')
            open(os.path.join(ROOT, rel), 'w').write(de)
            de_report[rel] = 'patched'
            src = de
        else:
            de_report[rel] = 'already patched'
        # --- other languages ---
        for lang in LANGS:
            if lang == 'de':
                continue
            doc = translate_text(src, lang)
            doc = rewrite_urls(doc, lang)
            doc = patch_head(doc, path, lang, False)
            # German source already has switcher (injected above) with wrong 'on' state;
            # rebuild switcher: replace existing langsw block
            doc = re.sub(r'<nav class="langsw".*?</nav>', lang_switcher(path, lang), doc, flags=re.S)
            # remove the DE redirect script from translated copies, use choice-only
            doc = doc.replace(REDIRECT_SCRIPT, CHOICE_SCRIPT)
            out = os.path.join(ROOT, lang, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, 'w').write(doc)
    print(json.dumps(de_report, indent=1))

    # --- sitemap with hreflang alternates ---
    urls = []
    for base, dirs, files in os.walk(ROOT):
        if any(base.startswith(os.path.join(ROOT, l)) for l in ('en', 'fr', 'it', 'rm')):
            continue
        if 'index.html' in files:
            rel = os.path.relpath(base, ROOT)
            urls.append('/' if rel == '.' else '/' + rel.replace(os.sep, '/') + '/')
    urls.sort()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for u in urls:
        sm.append(' <url>')
        for l in LANGS:
            sm.append('  <xhtml:link rel="alternate" hreflang="%s" href="https://clickandfood.global%s"/>' % (l, localized(u, l)))
        sm.append('  <xhtml:link rel="alternate" hreflang="x-default" href="https://clickandfood.global%s"/>' % localized(u, 'en'))
        sm.append('  <loc>https://clickandfood.global%s</loc>' % u)
        sm.append(' </url>')
    sm.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('\n'.join(sm) + '\n')
    print('sitemap:', len(urls), 'DE urls x', len(LANGS), 'languages =', len(urls)*len(LANGS))

if __name__ == '__main__':
    build()
