"""Read-only category archive checks. Source Simo env.sh; pass PHP JSON fixture export."""
import argparse
import base64
import dataclasses
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('fixtures',type=Path)
args=parser.parse_args()
root=Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR','')).resolve()!=root/'tmp':
    raise SystemExit('Source the existing Simo environment; no fallback.')
if not args.fixtures.resolve().is_relative_to(root/'artifacts'):raise SystemExit('Keep artifacts on Simo.')
data=json.loads(args.fixtures.read_text());run=args.fixtures.resolve().parent
# Embed local theme fonts in file fixtures to avoid a file:// to HTTPS CORS request.
theme=Path(__file__).resolve().parents[1]
def fixture_font(match):
    parsed=urlsplit(match.group(1))
    prefix='/wp-content/themes/githeme/'
    if parsed.netloc!='githeme:8890' or not parsed.path.startswith(prefix):
        raise ValueError('Unexpected fixture font URL')
    source=(theme/parsed.path[len(prefix):]).resolve()
    if not source.is_relative_to(theme/'assets/fonts') or source.suffix!='.woff2':
        raise ValueError('Unexpected fixture font path')
    return 'url(data:font/woff2;base64,'+base64.b64encode(source.read_bytes()).decode()+')'
fixture_css=re.sub(r'url\([\"\']?(https://[^)\"\']+\.woff2)[\"\']?\)',fixture_font,data['fixtures']['css'])
checks=[];samples=[];errors=[];network=[];driver=None;profiles=[]

def check(ok,label,details=None):
    checks.append({'check':label,'ok':bool(ok),'details':details})
    if not ok:raise AssertionError(label+': '+str(details))

def event(e,kind):
    value=e if isinstance(e,dict) else dataclasses.asdict(e)
    request=value.get('request',{});response=value.get('response',{});url=urlsplit(request.get('url',''))
    if url.scheme in ('https','http'):
        network.append({'kind':kind,'url':url.scheme+'://'+url.netloc+url.path,'status':response.get('status'),'error':value.get('errorText')})

def start(javascript=True):
    profile=tempfile.TemporaryDirectory(prefix='category-anonymous-',dir=root/'tmp');profiles.append(profile)
    options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox'
    for arg in ('-headless','-no-remote','-profile',profile.name):options.add_argument(arg)
    options.enable_bidi=True;options.accept_insecure_certs=False
    options.set_preference('javascript.enabled',javascript);options.set_preference('browser.cache.disk.enable',False)
    service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(root/'tmp/driver-profiles'),'--log','fatal'],log_output=str(run/('driver-'+str(javascript)+'.log')),env=os.environ.copy())
    browser=webdriver.Firefox(options=options,service=service);browser.set_page_load_timeout(30)
    browser.script.add_javascript_error_handler(lambda e:errors.append(str(getattr(e,'text',e))))
    browser.network.add_event_handler('response_completed',lambda e:event(e,'response'))
    browser.network.add_event_handler('fetch_error',lambda e:event(e,'fetch_error'))
    return browser

def inspect(label,expected_columns):
    driver.execute_script('document.querySelectorAll(".category-card img").forEach(i=>i.loading="eager")')
    WebDriverWait(driver,15).until(lambda d:d.execute_script('return [...document.querySelectorAll(".category-card img")].every(i=>i.complete&&i.naturalWidth>0)'))
    state=driver.execute_script('''const g=document.querySelector('.category-grid');return {width:innerWidth,pageWidth:document.documentElement.scrollWidth,columns:getComputedStyle(g).gridTemplateColumns.split(' ').length,
        cards:[...g.children].map(a=>{const m=a.querySelector('.category-card__media'),i=a.querySelector('img'),l=a.querySelector('.category-card__link'),h=a.querySelector('h2'),r=m?.getBoundingClientRect();return {id:a.id,media:!!m,image:!!i,ratio:r?r.width/r.height:null,fit:i?getComputedStyle(i).objectFit:null,
            label:l.getAttribute('aria-labelledby'),heading:h.id,title:h.textContent,links:a.querySelectorAll('a').length,excerpt:!!a.querySelector('.category-card__excerpt').textContent.trim(),badge:a.querySelector('.category-card__term,.category-card__term-plain')?.textContent.trim()}})}''')
    samples.append({'case':label,**state})
    check(state['width']==driver.execute_script('return innerWidth') and state['pageWidth']<=state['width'],'No horizontal page overflow '+label,state)
    check(state['columns']==expected_columns,'Responsive column count '+label,state['columns'])
    check(all(c['label']==c['heading'] and c['title'].strip() and c['links']>=1 for c in state['cards']),'Named card links and h2 headings '+label)
    check(all(not c['media'] or (c['image'] and abs(c['ratio']-16/9)<.01 and c['fit']=='cover') for c in state['cards']),'16:9 cover images '+label)
    check(all(c['image'] or not c['media'] for c in state['cards']),'No empty image placeholders '+label)
    check(all(c['excerpt'] for c in state['cards']),'Excerpts rendered '+label)
    check(all(not c['image'] or c['badge'] for c in state['cards']),'Every image card has a category label '+label)
    link=driver.find_element(By.CSS_SELECTOR,'.category-card__link');link.send_keys(Keys.NULL)
    driver.switch_to.active_element.send_keys(Keys.TAB);driver.switch_to.active_element.send_keys(Keys.SHIFT+Keys.TAB)
    check(driver.execute_script('const e=document.activeElement;return e===arguments[0]&&e.matches(":focus-visible")&&getComputedStyle(e).outlineStyle!=="none"',link),'Visible keyboard focus '+label)
    return state

try:
    driver=start()
    fixture_cards=[]
    for index in range(6):
        fragment=data['fixtures']['image' if index%2==0 else 'plain']
        fragment=re.sub(r'category-card-title-\d+',f'fixture-title-{index}',fragment)
        fragment=re.sub(r'id="post-\d+"',f'id="fixture-post-{index}"',fragment)
        fixture_cards.append(fragment)
    for sidebar in (False,True):
        document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src https://githeme:8890 data:; font-src data:; style-src \'unsafe-inline\'; script-src \'none\'"><style>'+fixture_css+'.fixture-layout{display:grid;grid-template-columns:minmax(0,1fr) 8rem;gap:1.5rem}@media(max-width:48rem){.fixture-layout{display:block}}</style><body><main class="site-container">'
        if sidebar:document+='<div class="fixture-layout">'
        document+='<div class="category-archive'+(' category-archive--with-sidebar' if sidebar else '')+'"><h1>Category fixture</h1><div class="category-grid">'+''.join(fixture_cards)+'</div></div>'
        if sidebar:document+='<aside aria-label="Fixture sidebar">Sidebar fixture</aside></div>'
        document+='</main></body></html>'
        path=run/('fixture-sidebar.html' if sidebar else 'fixture.html');path.write_text(document)
        for width,columns in ((1440,2 if sidebar else 3),(768,2),(390,1),(320,1)):
            driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900});driver.get(path.as_uri())
            state=inspect('fixture/'+str(sidebar)+'/'+str(width),columns)
            check(any(not c['image'] for c in state['cards']),'No-image fixture actually exercised')
            if width in (1440,320):driver.save_screenshot(str(run/f'fixture-{sidebar}-{width}.png'))
    base='https://githeme:8890/category/news/'
    for width,columns in ((1440,3),(768,2),(390,1),(320,1)):
        driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900});driver.get(base)
        state=inspect('real/'+str(width),columns)
        check([int(c['id'].split('-')[-1]) for c in state['cards']]==data['pages'][0]['ids'],'Real page 1 matches native query '+str(width))
        check(driver.execute_script('return document.querySelectorAll("main").length===1&&document.querySelectorAll("h1").length===1'),'Single main and h1 '+str(width))
        if width in (1440,320):
            driver.execute_script('scrollTo(0,0)');driver.save_screenshot(str(run/f'real-{width}.png'))
    for width in (1440,320):
        driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
        nav=driver.find_element(By.CSS_SELECTOR,'.pagination')
        driver.execute_script('arguments[0].scrollIntoView({block:"center"})',nav)
        check(driver.execute_script('const n=arguments[0],l=n.querySelector(".nav-links"),c=n.querySelector("[aria-current=page]");return n.tagName==="NAV"&&getComputedStyle(l).display==="flex"&&getComputedStyle(l).justifyContent==="center"&&!!c&&getComputedStyle(c).fontWeight>=600&&document.documentElement.scrollWidth<=innerWidth',nav),'Centered semantic pagination and visible current page '+str(width))
        driver.save_screenshot(str(run/f'pagination-{width}.png'))
    driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':320,'height':900})
    driver.find_element(By.CSS_SELECTOR,'a.next.page-numbers').click()
    WebDriverWait(driver,10).until(lambda d:d.find_element(By.CSS_SELECTOR,'.page-numbers.current').text=='2')
    page2=inspect('real/page2',1)
    check([int(c['id'].split('-')[-1]) for c in page2['cards']]==data['pages'][1]['ids'],'Real page 2 IDs and count match native pagination')
    check(not set(data['pages'][0]['ids'])&set(int(c['id'].split('-')[-1]) for c in page2['cards']),'No repeated articles across pages')
    driver.find_element(By.CSS_SELECTOR,'a.next.page-numbers').click()
    WebDriverWait(driver,10).until(lambda d:d.find_element(By.CSS_SELECTOR,'.page-numbers.current').text=='3')
    page3=inspect('real/page3',1)
    check(len(page3['cards'])==7 and not driver.find_elements(By.CSS_SELECTOR,'a.next.page-numbers'),'Last page has remaining seven articles and no next link')
    if data['fixtures']['child_url']:
        driver.get(data['fixtures']['child_url']);child=inspect('real/child-category',1)
        current=driver.find_element(By.CSS_SELECTOR,'.page-header h1').text.split(':')[-1].strip()
        check(all(c['badge'] for c in child['cards'] if c['image']),'Child archive image cards retain category labels')
    driver.get('https://githeme:8890/?s=stampa')
    check(not driver.find_elements(By.CSS_SELECTOR,'.category-grid'),'Search listing remains unchanged')
    driver.quit();driver=None
    driver=start(False)
    driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':320,'height':900});driver.get(base)
    inspect('real/without-js/320',1)
except Exception as exc:
    checks.append({'check':'Unexpected exception','ok':False,'details':type(exc).__name__+': '+str(exc)})
    if driver:
        try:driver.save_screenshot(str(run/'failure.png'))
        except Exception as capture:checks.append({'check':'Failure screenshot','ok':False,'details':str(capture)})
finally:
    cleanup=[]
    try:
        if driver:driver.quit()
    except Exception as exc:cleanup.append('browser: '+str(exc))
    for profile in profiles:
        try:profile.cleanup()
        except Exception as exc:cleanup.append('profile: '+str(exc))
    check_network=[n for n in network if n['error'] or ((n['status'] or 0)>=400 and not(n['url']=='https://githeme:8890/favicon.ico' and n['status']==404))]
    checks.append({'check':'No JavaScript errors','ok':not errors,'details':errors})
    checks.append({'check':'No unexpected failed HTTP requests','ok':not check_network,'details':check_network})
    checks.append({'check':'Browser/profile cleanup','ok':not cleanup,'details':cleanup})
    (run/'browser-report.json').write_text(json.dumps({'checks':checks,'samples':samples,'errors':errors,'network':network},indent=2))
failed=[c for c in checks if not c['ok']]
print(json.dumps({'checks':len(checks),'failed':failed,'artifacts':str(run)},indent=2))
raise SystemExit(bool(failed))
