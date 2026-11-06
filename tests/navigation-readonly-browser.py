"""Read-only navigation regression checks; DOM fixtures never save CMS data.
Source the existing Simo env.sh and run with its venv Python. --baseline only diagnoses.
"""
import argparse
import dataclasses
import datetime
import json
import os
from pathlib import Path
import socket
import ipaddress
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
ROOT=Path('/Volumes/Simo/Development/codex-browser-tools');URL='https://githeme:8890/'
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR','')).resolve()!=ROOT/'tmp':raise SystemExit('Source the existing Simo env.sh; no fallback.')
if not all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo('githeme',8890)):raise SystemExit('Expected loopback site')
run=ROOT/'artifacts'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-navigation-readonly'+('-baseline'if args.baseline else''));run.mkdir(mode=0o700)
profile=tempfile.TemporaryDirectory(prefix='navigation-anonymous-',dir=ROOT/'tmp');driver=None;service=None;checks=[];failures=[];samples=[];events=[];errors=[]
def require(ok,message):
 checks.append({'check':message,'ok':bool(ok)})
 if not ok:raise AssertionError(message)
def event(e):
 data=e if isinstance(e,dict)else dataclasses.asdict(e);r=data.get('request',{});u=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(r.get('url',''));response=data.get('response',{})
 events.append({'origin':u.scheme+'://'+u.netloc,'path':u.path if u.scheme!='data'else'[embedded data]','status':response.get('status'),'error':data.get('errorText')})
def js_error(e):errors.append({'text':str(getattr(e,'text',''))})
def console(e):
 if 'error' in str(getattr(e,'level','')).lower():errors.append({'console_error':str(getattr(e,'text',''))})
def dimensions():
 return driver.execute_script('''const n=document.querySelector('.primary-navigation'),m=document.querySelector('#primary-menu'),t=n?.querySelector('button');const rect=e=>{let r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};return {width:innerWidth,scroll:document.documentElement.scrollWidth,mobile:matchMedia('(max-width:48rem)').matches,classes:n?.className,compact:n?.classList.contains('is-compact')||false,toggleVisible:!!t&&!t.hidden,expanded:t?.getAttribute('aria-expanded'),menuHidden:m?.hidden,header:rect(document.querySelector('.header-inner')),branding:rect(document.querySelector('.site-branding')),navigation:n?rect(n):null,menu:m?rect(m):null,roots:m?[...m.children].map(li=>({label:li.querySelector('a')?.textContent.trim(),rect:rect(li),href:li.querySelector('a')?.getAttribute('href')})):[],submenus:m?[...m.querySelectorAll('ul')].map(u=>({depth:(()=>{let d=0,p=u;while((p=p.parentElement?.closest('ul')))d++;return d})(),display:getComputedStyle(u).display,position:getComputedStyle(u).position,rect:rect(u),labels:[...u.children].map(li=>li.querySelector('a')?.textContent.trim())})):[]};''')
def viewport(width):
 driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900});time.sleep(.25)
def wait_ready():
 WebDriverWait(driver,15).until(lambda d:d.execute_script('return document.readyState==="complete" && !!document.querySelector(".header-inner")'));time.sleep(.3)
try:
 options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox';options.add_argument('-headless');options.add_argument('-profile');options.add_argument(profile.name);options.enable_bidi=True;options.accept_insecure_certs=False;options.set_preference('browser.cache.disk.parent_directory',str(ROOT/'cache/firefox'));options.set_preference('browser.cache.disk.enable',False);options.set_preference('browser.cache.memory.enable',False)
 service=Service(str(ROOT/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(ROOT/'tmp/driver-profiles'),'--log','error'],log_output=str(run/'geckodriver.log'),env=os.environ.copy());driver=webdriver.Firefox(options=options,service=service);driver.set_page_load_timeout(30);driver.script.add_javascript_error_handler(js_error);driver.script.add_console_message_handler(console);driver.network.add_event_handler('before_request',event);driver.network.add_event_handler('response_completed',event);driver.network.add_event_handler('fetch_error',event)
 for width in ([1280,1440]if args.baseline else[1440,1280,768,390,320]):
  viewport(width);driver.get(URL);wait_ready();require(not driver.execute_script("return document.body.classList.contains('logged-in')"),'Anonymous public page');state=dimensions();state['scenario']='actual';samples.append(state);driver.save_screenshot(str(run/f'actual-{width}.png'))
  if args.baseline:
   state['measurement']=driver.execute_script('''const n=document.querySelector('.primary-navigation'),m=document.querySelector('#primary-menu'),t=n.querySelector('button');const old={c:n.className,m:m.hidden,t:t.hidden};n.classList.remove('is-compact');m.hidden=false;t.hidden=true;const get=()=>({navWidth:n.clientWidth,menuScroll:m.scrollWidth,navTop:n.getBoundingClientRect().top,brandingBottom:document.querySelector('.site-branding').getBoundingClientRect().bottom,items:[...m.children].map(e=>({top:e.getBoundingClientRect().top,width:e.getBoundingClientRect().width,label:e.querySelector('a').textContent.trim()}))});const original=get();const sub=[...m.querySelectorAll('ul')];const styles=sub.map(e=>e.getAttribute('style'));sub.forEach(e=>e.style.display='none');const withoutSubmenus=get();sub.forEach((e,i)=>styles[i]===null?e.removeAttribute('style'):e.setAttribute('style',styles[i]));n.className=old.c;m.hidden=old.m;t.hidden=old.t;return {original,withoutSubmenus};''')
   continue
  require(state['width']==width and state['scroll']==width,f'Viewport and overflow {width}')
  require(state['compact']==(width<=768),f'Desktop row / mobile compact {width}')
  require(driver.execute_script("return document.querySelectorAll('#primary-menu').length===1"),f'Single menu DOM {width}')
  if state['compact']:
   toggle=driver.find_element(By.CSS_SELECTOR,'.menu-toggle');require(toggle.get_attribute('aria-controls')=='primary-menu',f'aria-controls {width}');require(toggle.tag_name=='button'and bool(toggle.text.strip()),f'Accessible named button {width}')
   toggle.send_keys(Keys.ENTER);require(toggle.get_attribute('aria-expanded')=='true'and not driver.find_element(By.ID,'primary-menu').get_property('hidden'),f'Enter opens {width}');driver.save_screenshot(str(run/f'expanded-{width}.png'));toggle.send_keys(Keys.SPACE);require(toggle.get_attribute('aria-expanded')=='false',f'Space closes {width}');toggle.click();driver.find_element(By.CSS_SELECTOR,'#primary-menu a').send_keys(Keys.ESCAPE);require(toggle.get_attribute('aria-expanded')=='false'and driver.switch_to.active_element==toggle,f'Escape returns focus {width}')
  else:
   roots=state['roots'];require(max(r['rect']['y']for r in roots)-min(r['rect']['y']for r in roots)<1,f'One horizontal row {width}')
   # Check every actual dropdown with the pointer, including viewport-edge panels.
   for index in [i for i in range(len(roots)) if driver.find_elements(By.CSS_SELECTOR,f'#primary-menu > li:nth-child({i+1}) > ul')]:
    item=driver.find_elements(By.CSS_SELECTOR,'#primary-menu > li')[index];anchor=item.find_element(By.CSS_SELECTOR,':scope > a');submenu=item.find_element(By.CSS_SELECTOR,':scope > ul')
    ActionChains(driver).move_to_element(anchor).perform();require(submenu.is_displayed(),f'Pointer opens dropdown {width}/{index}')
    edges=driver.execute_script('const r=arguments[0].getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth}',submenu);require(edges['left']>=7 and edges['right']<=edges['width']-7,f'Dropdown within viewport {width}/{index}')
    ActionChains(driver).move_to_element_with_offset(anchor,0,anchor.size['height']/2+8).move_to_element(submenu.find_element(By.CSS_SELECTOR,'a')).perform();require(submenu.is_displayed(),f'Pointer can enter dropdown {width}/{index}')
    driver.execute_script("window.dispatchEvent(new Event('resize'))");time.sleep(.2);require(not dimensions()['compact']and submenu.is_displayed(),f'Open dropdown excluded from fit measurement {width}/{index}')
    if index==5:driver.save_screenshot(str(run/f'dropdown-{width}.png'))
    ActionChains(driver).send_keys(Keys.ESCAPE).perform();require(not submenu.is_displayed(),f'Escape dismisses hover without pointer movement {width}/{index}')
    ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR,'main h1')).perform()
   links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a');driver.execute_script('arguments[0].focus()',links[0])
   for index,link in enumerate(links[1:],1):
    driver.switch_to.active_element.send_keys(Keys.TAB);require(driver.switch_to.active_element==link and link.is_displayed(),f'Desktop Tab order {width}/{index}');require(driver.execute_script("return document.activeElement.matches(':focus-visible')&&getComputedStyle(document.activeElement).outlineStyle!=='none'"),f'Desktop focus visible {width}/{index}')
   driver.switch_to.active_element.send_keys(Keys.TAB);require(not driver.execute_script("return !!document.activeElement.closest('.primary-navigation')"),f'No focus trap {width}')
   parent=driver.find_element(By.CSS_SELECTOR,'#primary-menu > li:nth-child(3) > a');driver.execute_script('arguments[0].focus()',parent);parent.send_keys(Keys.TAB);first=driver.switch_to.active_element;first.send_keys(Keys.TAB);second=driver.switch_to.active_element;second.send_keys(Keys.SHIFT,Keys.TAB);require(driver.switch_to.active_element==first,f'Shift Tab in submenu {width}');first.send_keys(Keys.ESCAPE);require(driver.switch_to.active_element==parent and not parent.find_element(By.XPATH,'following-sibling::ul').is_displayed(),f'Escape closes and returns to parent {width}')
  if state['compact']:
   toggle=driver.find_element(By.CSS_SELECTOR,'.menu-toggle');toggle.send_keys(Keys.TAB);require(not driver.execute_script("return !!document.activeElement.closest('#primary-menu')"),f'Closed menu links skipped {width}');driver.switch_to.active_element.send_keys(Keys.SHIFT,Keys.TAB);require(driver.switch_to.active_element==toggle,f'Shift Tab returns to toggle {width}');toggle.send_keys(Keys.ENTER)
   links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
   for index,link in enumerate(links):
    driver.switch_to.active_element.send_keys(Keys.TAB);require(driver.switch_to.active_element==link and link.is_displayed(),f'Mobile Tab includes submenu {width}/{index}');require(driver.execute_script("return document.activeElement.matches(':focus-visible')&&getComputedStyle(document.activeElement).outlineStyle!=='none'"),f'Mobile focus visible {width}/{index}')
   for index,link in enumerate(reversed(links[:-1])):
    driver.switch_to.active_element.send_keys(Keys.SHIFT,Keys.TAB);require(driver.switch_to.active_element==link,f'Mobile reverse order {width}/{index}')
   driver.switch_to.active_element.send_keys(Keys.ESCAPE);require(driver.switch_to.active_element==toggle and toggle.get_attribute('aria-expanded')=='false',f'Mobile Escape after keyboard traversal {width}')
 if not args.baseline:
  # Pure DOM fixtures in a fresh iframe realm. No menu assignment or CMS writes.
  driver.switch_to.default_content();viewport(1440);driver.get(URL);wait_ready()
  template=driver.execute_script("""return {header:document.querySelector('.site-header').outerHTML,styles:[...document.querySelectorAll('link[rel=stylesheet],style')].map(e=>e.outerHTML).join(''),bodyClass:document.body.className,script:document.querySelector('script[src*="navigation.js"]').src};""")
  def fixture(kind,width,nojs=False):
   driver.switch_to.default_content();viewport(width)
   driver.execute_script("""const old=document.getElementById('navigation-fixture');if(old)old.remove();const t=arguments[0],kind=arguments[1],nojs=arguments[2];const doc=new DOMParser().parseFromString(t.header,'text/html');const n=doc.querySelector('.primary-navigation'),m=doc.querySelector('#primary-menu'),b=doc.querySelector('.menu-toggle');n.classList.remove('is-enhanced','is-compact');m.hidden=false;b.hidden=true;b.setAttribute('aria-expanded','false');m.querySelectorAll('.submenu-dismissed').forEach(e=>e.classList.remove('submenu-dismissed'));m.querySelectorAll('ul').forEach(e=>e.style.removeProperty('--submenu-offset'));if(kind==='none')n.remove();if(kind==='short'||kind==='nested'){[...m.children].slice(3).forEach(e=>e.remove());}if(kind==='flat'){[...m.children].slice(2).forEach(e=>e.remove());m.querySelectorAll('ul').forEach(e=>e.remove());}if(kind==='long'){m.firstElementChild.querySelector('a').textContent='Long navigation label '.repeat(30);}if(kind==='nested'){const li=m.querySelector(':scope > li > ul > li'),u=doc.createElement('ul');u.className='sub-menu';u.innerHTML='<li><a href="#main-content">Nested fixture link</a></li>';li.append(u);}const frame=document.createElement('iframe');frame.id='navigation-fixture';frame.title='Read-only menu fixture';frame.style.cssText='position:fixed;inset:0;width:100vw;height:100vh;border:0;z-index:200000;';frame.srcdoc='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'+t.styles+'</head><body class="'+t.bodyClass+'">'+doc.body.innerHTML+'<main id="main-content" tabindex="-1"><h1>Navigation test fixture</h1><a href="#main-content">Main link</a></main>'+(nojs?'':'<script src="'+t.script+'"></script>')+'</body></html>';document.body.append(frame);""",template,kind,nojs)
   WebDriverWait(driver,15).until(lambda d:len(d.find_elements(By.ID,'navigation-fixture'))==1);driver.switch_to.frame(driver.find_element(By.ID,'navigation-fixture'));wait_ready()
  for kind in ['short','flat','nested','none']:
   for width in [1440,1280,768,390,320]:
    fixture(kind,width);state=dimensions();state['scenario']=kind;samples.append(state);require(state['width']==width and state['scroll']==width,f'Fixture viewport/overflow {kind}/{width}')
    if kind=='none':require(not driver.find_elements(By.CSS_SELECTOR,'.primary-navigation,.menu-toggle'),f'No menu markup or toggle {width}');continue
    require(state['compact']==(width<=768),f'Short/flat/nested mode {kind}/{width}')
    if state['compact']:driver.find_element(By.CSS_SELECTOR,'.menu-toggle').click()
    if kind in ['short','nested']:
     parent=driver.find_element(By.CSS_SELECTOR,'#primary-menu > li:last-child > a');driver.execute_script('arguments[0].focus()',parent);submenu=parent.find_element(By.XPATH,'following-sibling::ul');require(submenu.is_displayed(),f'Short submenu accessible {kind}/{width}');edges=driver.execute_script('const r=arguments[0].getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth}',submenu);require(edges['left']>=0 and edges['right']<=edges['width'],f'Short submenu edge alignment {kind}/{width}')
     if kind=='nested':require(driver.find_element(By.CSS_SELECTOR,'.sub-menu .sub-menu a').is_displayed(),f'Second-level links remain accessible {width}')
    driver.save_screenshot(str(run/f'{kind}-{width}.png'))
  fixture('long',1440);require(dimensions()['compact'], 'Long root label requires compact even on desktop');require(dimensions()['scroll']==1440,'Long compact menu has no overflow')
  fixture('short',1440)
  # Dynamic geometry must switch in both directions without a window resize.
  driver.execute_script("document.querySelector('.header-inner').style.width='350px'");time.sleep(.35);require(dimensions()['compact'],'Dynamic narrow container compacts');driver.execute_script("document.querySelector('.header-inner').style.removeProperty('width')");time.sleep(.35);require(not dimensions()['compact'],'Dynamic container restored to row')
  driver.execute_script("document.querySelector('.site-branding').style.width='1100px'");time.sleep(.35);require(dimensions()['compact'],'Wider branding compacts');driver.execute_script("document.body.classList.add('githeme-header-stacked')");time.sleep(.35);require(not dimensions()['compact'],'Stacked header restores available row');driver.execute_script("document.body.classList.remove('githeme-header-stacked');document.querySelector('.site-branding').style.removeProperty('width')");time.sleep(.35);require(not dimensions()['compact'],'Original inline geometry restored')
  fixture('nested',1440)
  for width in [1440,390]:
   driver.switch_to.default_content();viewport(width);driver.switch_to.frame(driver.find_element(By.ID,'navigation-fixture'));time.sleep(.3)
   if dimensions()['compact']:driver.find_element(By.CSS_SELECTOR,'.menu-toggle').click()
   driver.execute_script("window.navChanges=0;new MutationObserver(r=>navChanges+=r.length).observe(document.querySelector('.primary-navigation'),{attributes:true,subtree:true,attributeFilter:['class','hidden','aria-expanded']});")
   state=driver.execute_async_script("""const done=arguments[0],out=[];function sample(){out.push({changes:navChanges,compact:document.querySelector('.primary-navigation').classList.contains('is-compact')});if(out.length<30)requestAnimationFrame(sample);else done(out);}requestAnimationFrame(sample);""");require(state[-1]['changes']==state[10]['changes'],f'No observer oscillations {width}')
  for width in [1440,390,320]:
   fixture('actual',width,nojs=True);require(not driver.find_element(By.CSS_SELECTOR,'.menu-toggle').is_displayed(),f'No-JS no dead button {width}');links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a');require(all(a.is_displayed()for a in links),f'No-JS every link visible {width}');require(dimensions()['scroll']==width,f'No-JS no overflow {width}')
  require(not errors,'No JavaScript errors')
  unexpected=[e for e in events if e['error']or((e['status']or 0)>=400 and not(e['origin']=='https://githeme:8890'and e['path']=='/favicon.ico'and e['status']==404))];require(not unexpected,'No new network failures (known favicon 404 retained in report)')
except Exception as e:
 failures.append(type(e).__name__+': '+str(e))
 if driver:
  try:
   driver.save_screenshot(str(run/'failure.png'));samples.append({'scenario':'failure','state':dimensions()})
  except Exception as diagnostic_error:failures.append('Failure diagnostics: '+str(diagnostic_error))
finally:
 if driver:
  try:driver.quit()
  except Exception as e:failures.append('Browser cleanup: '+str(e))
 if service:
  try:service.stop()
  except Exception as e:failures.append('Driver cleanup: '+str(e))
 try:profile.cleanup()
 except Exception as e:failures.append('Profile cleanup: '+str(e))
 result={'mode':'baseline'if args.baseline else'test','samples':samples,'checks':checks,'failures':failures,'js_errors':errors,'network':events};(run/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'artifacts':str(run),'samples':len(samples),'checks':len(checks),'failures':failures,'js_errors':errors}))

raise SystemExit(bool(failures or errors or any(not c["ok"] for c in checks)))
