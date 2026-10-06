#!/usr/bin/env python3
"""
Clickandfood.global Seiten-Generator
------------------------------------
Rendert aus den extrahierten Partner-Daten (/tmp/partner_data.json)
+ manuellen Ergänzungen (hier unten) alle Restaurant- und Ortsseiten
im Template-Design. Templates: die bestehenden index.html-Dateien
als Referenz; hier als Python-String-Templates verdichtet.
"""
import json, os, re, html, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import LANGS, LOCALES, tr, fmt, tr_cuisine, DAY_FULL, PLURAL, lang_prefix, localized, hreflang_block, lang_switcher, LANGSW_CSS, REDIRECT_SCRIPT, CHOICE_SCRIPT

ROOT = '/home/user/workspace/clickandfood-global'
CAF_WHITE = 'data:image/png;base64,' + open('/tmp/caf-white.b64').read().strip()

DAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

def fmt_hours(hours, lang='de'):
    """group ['Friday 11:00-14:00',...] -> ordered localized list"""
    DAY = DAY_FULL[lang]
    by={d:[] for d in DAY_ORDER}
    for h in hours or []:
        m=re.match(r'(\w+)\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})',h)
        if m and m.group(1) in by:
            by[m.group(1)].append(f"{m.group(2)}–{m.group(3)}")
    rows=[]
    for d in DAY_ORDER:
        if by[d]:
            rows.append((DAY[d], ' &amp; '.join(by[d])))
    return rows

def fmt_cuisine(c):
    if not c: return None
    items=[x.get('de') for x in c if isinstance(x,dict) and x.get('de')]
    items=[i for i in items if i not in ('Top Deals','Getränke','Alkoholische Getränke','Nachspeise')]
    return ' · '.join(items[:4]) if items else None

def esc(s): return html.escape(str(s)) if s else ''

# ---------- manual additions / fixes ----------
# Restaurants without ordering-platform match: cashback-page data + order link = cashback page
EXTRA = {
  'pizzeria-langgasse-19': {
    'name':'Pizzeria Länggasse 19','street':'Länggasse 19','postal':'3012','city':'Bern','country':'CH',
    'telephone':None,'cuisine_label':'Pizza · Pasta · Italienisch',
    'order_url':'https://cashback.sparissimo.world/regional-shop/pizzeria-langgasse-19',
    'note':'Cashback-Partner — QR-Code im Restaurant scannen und Cashback erhalten.'},
  'restaurant-pizzeria-muhli': {
    'name':'Restaurant & Pizzeria Mühli','street':None,'postal':None,'city':None,'country':'CH',
    'telephone':None,'cuisine_label':'Pizza · Italienisch',
    'order_url':'https://cashback.sparissimo.world/regional-shop/restaurant-pizzeria-muhli',
    'note':'Cashback-Partner — QR-Code im Restaurant scannen und Cashback erhalten.'},
}
# platform detail-page URLs (for order buttons)
PLATFORM_URL = {
 'krua-thailand-restaurant-takeaway-1':'https://clickandfood.sparissimo.world/restaurants/krua-thailand-restaurant-takeaway',
 'pho-saigon-bui-1':'https://clickandfood.sparissimo.world/restaurants/pho-saigon-bi',
 'hot-momo-bern':'https://clickandfood.sparissimo.world/restaurants/hot-momo-bern',
 'pizza-kebab-haus-1':'https://clickandfood.sparissimo.world/restaurants/pizza-kebab-haus-urtenenschoenbuehl',
 'pizzeria-adler':'https://clickandfood.sparissimo.world/restaurants/pizzeria-adler',
 'pizzeria-durango':'https://clickandfood.sparissimo.world/restaurants/pizzeria-durango',
 'anaterra-grill':'https://clickandfood.sparissimo.world/restaurants/anaterra-grill-zuchwil-4528',
 'panini-bar':'https://clickandfood.sparissimo.world/restaurants/panini-bar-solothurn-4500',
 'su-mo-day':'https://clickandfood.sparissimo.world/restaurants/su-mo-days',
 'restaurant-tyrol':'https://clickandfood.sparissimo.world/restaurants/restaurant-tyrol',
 'ristorante-pizzeria-gasthof-kreuz':'https://clickandfood.sparissimo.world/restaurants/ristorante-pizzeria-gasthof-kreuz',
 'first-class':'https://clickandfood.sparissimo.world/restaurants/first-class',
}

def build_partners():
    data=json.load(open('/tmp/partner_data.json'))
    partners=[]
    for slug,d in data.items():
        p={
          'slug':slug,
          'name':d.get('name'),
          'street':(d.get('street') or '').split('\n')[0].strip() or None,
          'postal':d.get('postal'),'city':d.get('city'),'country':d.get('country') or 'CH',
          'telephone':d.get('telephone'),
          'cuisine_label':fmt_cuisine(d.get('cuisine')) or d.get('cuisine_from_title'),
          'hours_raw':d.get('hours'),
          'lat':d.get('lat'),'lng':d.get('lng'),
          'order_url':PLATFORM_URL[slug],
          'cashback_url':f'https://cashback.sparissimo.world/regional-shop/{slug}',
          'platform':True,
        }
        partners.append(p)
    for slug,e in EXTRA.items():
        partners.append(dict(slug=slug, hours_raw=[], lat=None,lng=None,
                             cashback_url=e['order_url'], platform=False, **e))
    return partners

def fmt_hours_raw(p, lang):
    return fmt_hours(p.get('hours_raw'), lang)

# ---------- page templates ----------
def _extract_css(path):
    a=open(path).read()
    s=a.find('<style>')+len('<style>')
    return a[s:a.find('</style>',s)]
CSS = _extract_css(f'{ROOT}/restaurants/anatolia-nendeln/index.html') + _extract_css(f'{ROOT}/orte/nendeln/index.html')

def page_head(p, title, desc, path, schema, lang='de'):
    canonical = f'https://clickandfood.global{localized(path, lang)}'
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{LOCALES[lang]}">
<meta name="twitter:card" content="summary_large_image">
{hreflang_block(path)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650;9..144,750&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
{schema}
<style>{CSS}{LANGSW_CSS}</style>
{REDIRECT_SCRIPT if lang=='de' else CHOICE_SCRIPT}
</head>
<body>
'''

def header(active_order_url, path='/', lang='de'):
    home = f'https://clickandfood.global{lang_prefix(lang)}/'
    return f'''<header>
  <div class="wrap nav">
    <a href="{home}" aria-label="ClickandFood"><img class="logo" src="{CAF_WHITE}" alt="ClickandFood Logo"></a>
    <ul>
      <li><a href="{home}#restaurants">{tr('Restaurants', lang)}</a></li>
      <li><a href="{home}#orte">{tr('Orte', lang)}</a></li>
      <li><a href="{home}#cashback">{tr('Cashback', lang)}</a></li>
    </ul>
    {lang_switcher(path, lang)}
    <a class="btn btn-gold" href="{active_order_url}" rel="noopener">{tr('Jetzt bestellen', lang)}</a>
  </div>
</header>
'''

def footer(cityline, lang='de'):
    home = f'https://clickandfood.global{lang_prefix(lang)}/'
    return f'''<footer>
  <div class="wrap foot">
    <div>
      <img src="{CAF_WHITE}" alt="ClickandFood Logo">
      <p style="margin-top:12px">{cityline}<br>{tr('Ein Partner im ClickandFood-Netzwerk — Cashback bei jeder Bestellung.', lang)}</p>
    </div>
    <div>
      <a href="{home}">clickandfood.global</a>
      <a href="https://www.sparissimofood.com/" rel="noopener" target="_blank">Sparissimo Food</a>
      <a href="{lang_prefix(lang)}/impressum/">{tr('Impressum', lang)}</a>
      <a href="{lang_prefix(lang)}/datenschutz/">{tr('Datenschutz', lang)}</a>
    </div>
  </div>
</footer>
</body>
</html>
'''

def restaurant_page(p, lang='de'):
    city=p['city'] or ''
    name=p['name']
    slug=p['slug']
    path=f'/restaurants/{slug}/'
    url=f'https://clickandfood.global{localized(path, lang)}'
    cuisine=tr_cuisine(p.get('cuisine_label') or 'Restaurant', lang)
    title=fmt('r_title', lang, name=name, city_suffix=(' '+city if city else ''), cuisine=cuisine)
    adr=f"{p['street']}, {p['postal']} {city}" if p.get('street') else city
    desc=fmt('r_desc', lang, name=name, city_infix=(' in '+city if city else ''), cuisine=cuisine)
    hours_rows=''.join(f'<div class="row"><span>{esc(d)}</span><span>{t}</span></div>' for d,t in fmt_hours_raw(p, lang))
    if not hours_rows:
        hours_rows=f'<div class="row"><span>{tr("Öffnungszeiten", lang)}</span><span>{tr("siehe Restaurant", lang)}</span></div>'
    tel_html=f'<dt>{tr("Telefon", lang)}</dt><dd><a href="tel:{p["telephone"].replace(" ","")}">{esc(p["telephone"])}</a></dd>' if p.get('telephone') else ''
    maps=''
    if p.get('lat') and p.get('lng'):
        maps=f'<dt>{tr("Anfahrt", lang)}</dt><dd><a href="https://www.google.com/maps/search/?api=1&amp;query={p["lat"]},{p["lng"]}" rel="noopener" target="_blank">{tr("Route in Google Maps →", lang)}</a></dd>'
    order=p['order_url']
    schema_rest={
      "@context":"https://schema.org","@type":"Restaurant","name":name,
      "url":url,"servesCuisine":[s.strip() for s in cuisine.split('·')],
    }
    if p.get('street'): schema_rest['address']={"@type":"PostalAddress","streetAddress":p['street'],"postalCode":p.get('postal'),"addressLocality":city,"addressCountry":p.get('country') or 'CH'}
    if p.get('telephone'): schema_rest['telephone']=p['telephone']
    if p.get('lat') and p.get('lng'): schema_rest['geo']={"@type":"GeoCoordinates","latitude":p['lat'],"longitude":p['lng']}
    schema_rest['sameAs']=[p['cashback_url']]+([order] if p.get('platform') else [])
    home = f'https://clickandfood.global{lang_prefix(lang)}/'
    crumbs=f'{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"ClickandFood","item":"{home}"}},{{"@type":"ListItem","position":2,"name":"{tr("Restaurants", lang)}","item":"{home}#restaurants"}},{{"@type":"ListItem","position":3,"name":"{name}","item":"{url}"}}]}}'
    schema=(f'<script type="application/ld+json">{json.dumps(schema_rest,ensure_ascii=False)}</script>\n'
            f'<script type="application/ld+json">{crumbs}</script>')
    reserve_btn = f'<a class="btn btn-ghost" href="{order}" rel="noopener">{tr("Tisch reservieren", lang)}</a>' if p.get('platform') else ''
    country = tr('Liechtenstein', lang) if p.get('country')=='LI' else tr('Schweiz', lang)
    body=f'''{header(order, path, lang)}
<main>
<div class="wrap crumbs">
  <a href="{home}">ClickandFood</a><span>›</span><a href="{home}#restaurants">{tr('Restaurants', lang)}</a><span>›</span><b>{esc(name)}</b>
</div>
<section class="hero">
  <div class="wrap hero-grid">
    <div>
      <p class="eyebrow">{esc(city)} · {esc(p.get('postal') or '')} · {country}</p>
      <h1>{esc(name)} — <em>{esc(cuisine)}</em></h1>
      <p class="lede">{fmt('r_lede', lang, name=esc(name), city_infix=(' in '+esc(city) if city else ''))}</p>
      <div class="hero-ctas">
        <a class="btn btn-gold" href="{order}" rel="noopener">{tr('Jetzt bestellen', lang)}</a>
        {reserve_btn}
      </div>
      {f'<p class="status"><span class="dot"></span> <a href="tel:{p["telephone"].replace(" ","")}" style="color:var(--gold);text-decoration:none;font-weight:600">{esc(p["telephone"])}</a></p>' if p.get('telephone') else ''}
    </div>
    <aside class="hero-side">
      <div class="factcard">
        <h3>{tr('Adresse & Kontakt', lang)}</h3>
        <dl>
          {f'<dt>{tr("Adresse", lang)}</dt><dd>{esc(p["street"])}<br>{esc(p.get("postal") or "")} {esc(city)}</dd>' if p.get('street') else ''}
          {tel_html}
          {maps}
        </dl>
      </div>
      <div class="factcard hours-card">
        <h3>{tr('Öffnungszeiten', lang)}</h3>
        {hours_rows}
      </div>
    </aside>
  </div>
</section>
<section class="cta-band">
  <div class="wrap">
    <h2 class="serif">{fmt('r_hungry', lang, name=esc(name))}</h2>
    <p>{tr('Bestelle online und sammle Cashback bei jeder Bestellung.', lang) if False else fmt('r_cta', lang)}</p>
    <div class="hero-ctas">
      <a class="btn btn-gold" href="{order}" rel="noopener">{tr('Jetzt bestellen', lang)}</a>
    </div>
  </div>
</section>
</main>
{footer(f'{esc(name)} · {esc(adr)}', lang)}
'''
    return page_head(p, title, desc, path, schema, lang) + body

def slugify(s):
    s=s.lower()
    for a,b in {'ä':'ae','ö':'oe','ü':'ue','é':'e','è':'e','à':'a','â':'a','ç':'c','ß':'ss'}.items():
        s=s.replace(a,b)
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def place_page(city, postal, partners, lang='de'):
    slug_city=slugify(city)
    path=f'/orte/{slug_city}/'
    url=f'https://clickandfood.global{localized(path, lang)}'
    n=len(partners)
    plural = '' if n==1 else PLURAL[lang][1]
    if n==1: plural = PLURAL[lang][0]
    title=fmt('t_title', lang, city=city)
    desc=fmt('t_desc', lang, city=city, postal=postal or '', n=n, plural=plural)
    cards=''
    for p in partners:
        cards+=f'''<article class="rcard">
        <div class="rtop"><h3 class="serif">{esc(p['name'])}</h3><span class="tag">{esc(p.get('postal') or '')} {esc(city)}</span></div>
        <p class="rcuisine">{esc(tr_cuisine(p.get('cuisine_label') or 'Restaurant', lang))}</p>
        <p class="rmeta">{esc(p.get('street') or '')} · {tr('Lieferung, Abholung & Tischreservierung', lang).replace('&','&amp;')}</p>
        <div class="ractions">
          <a class="btn btn-gold" href="{p['order_url']}" rel="noopener">{tr('Bestellen', lang)}</a>
        </div>
        <a class="rmore" href="https://clickandfood.global{localized('/restaurants/'+p['slug']+'/', lang)}">{fmt('more_about', lang, name=esc(p['name']))}</a>
      </article>\n'''
    home = f'https://clickandfood.global{lang_prefix(lang)}/'
    crumbs=f'{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"ClickandFood","item":"{home}"}},{{"@type":"ListItem","position":2,"name":"{tr("Orte", lang)}","item":"{home}#orte"}},{{"@type":"ListItem","position":3,"name":"{city}","item":"{url}"}}]}}'
    schema=f'<script type="application/ld+json">{crumbs}</script>'
    body=f'''{header('https://clickandfood.ch/', path, lang)}
<main>
<div class="wrap crumbs">
  <a href="{home}">ClickandFood</a><span>›</span><a href="{home}#orte">{tr('Orte', lang)}</a><span>›</span><b>{esc(city)}</b>
</div>
<section class="hero">
  <div class="wrap">
    <p class="eyebrow">{esc(city)} · {esc(postal or '')} · {tr('Schweiz', lang)}</p>
    <h1>{fmt('t_h1_pre', lang)}<em>{esc(city)}</em>{fmt('t_h1_post', lang)}</h1>
    <p class="lede">{fmt('t_lede', lang, n=n, plural=plural, city=esc(city))}</p>
    <div class="hero-ctas">
      <a class="btn btn-gold" href="https://clickandfood.ch/" rel="noopener">{tr('Jetzt bestellen', lang)}</a>
      <a class="btn btn-ghost" href="#restaurants">{tr('Restaurants im Ort', lang)}</a>
    </div>
  </div>
</section>
<section id="restaurants" style="padding-top:0">
  <div class="wrap">
    <div class="dir-head"><div><p class="eyebrow">{fmt('t_restaurants_in', lang, city=esc(city))}</p><h2>{tr('Wer heute kocht, wenn du es nicht tust.', lang)}</h2></div></div>
    <div class="dir-grid">
{cards}    </div>
    <p class="dir-note">{fmt('t_more', lang, city=esc(city))} <a href="https://www.sparissimofood.com/" rel="noopener" target="_blank">{tr('Dein Restaurant fehlt? Werde Partner →', lang)}</a></p>
  </div>
</section>
</main>
{footer(fmt('t_footer', lang, city=esc(city)), lang)}
'''
    return slug_city, page_head({}, title, desc, path, schema, lang) + body

def main():
    partners=build_partners()
    n=0
    for lang in LANGS:
        base = ROOT + lang_prefix(lang)
        for p in partners:
            d=f'{base}/restaurants/{p["slug"]}'
            os.makedirs(d,exist_ok=True)
            open(f'{d}/index.html','w').write(restaurant_page(p, lang))
            n+=1
        by_city={}
        for p in partners:
            if p.get('city'):
                by_city.setdefault(p['city'],[]).append(p)
        places=[]
        for city,ps in sorted(by_city.items()):
            slug_city,page=place_page(city, ps[0].get('postal'), ps, lang)
            d=f'{base}/orte/{slug_city}'
            os.makedirs(d,exist_ok=True)
            open(f'{d}/index.html','w').write(page)
            places.append((city,slug_city,len(ps)))
    print(f'{n} restaurant pages ({len(LANGS)} languages), {len(places)} place pages per language')
    for c in places: print('  ',c)
    # manifest for the directory on the homepage
    json.dump([{k:p.get(k) for k in ('slug','name','city','postal','country','cuisine_label','order_url')} for p in partners],
              open(f'{ROOT}/partners.json','w'),ensure_ascii=False,indent=1)

if __name__=='__main__':
    main()
