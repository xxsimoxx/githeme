"""Read-only responsive widget fixtures and real category regression. Source Simo env.sh."""
import argparse
import json
import os
from pathlib import Path
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixtures',type=Path);args=parser.parse_args()
root=Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR','')).resolve()!=root/'tmp':raise SystemExit('Source Simo env.sh.')
if not args.fixtures.resolve().is_relative_to(root/'artifacts'):raise SystemExit('Keep artifacts on Simo.')
run=args.fixtures.resolve().parent;fixture=json.loads(args.fixtures.read_text());checks=[];errors=[];driver=None;profile=None

def check(ok,label,details=None):
 checks.append({'ok':bool(ok),'label':label,'details':details})
 if not ok:raise RuntimeError(label)

measure='''const root=arguments[0],grid=root.querySelector('.category-grid');return {width:root.getBoundingClientRect().width,columns:getComputedStyle(grid).gridTemplateColumns.split(' ').length,cards:[...grid.children].map(e=>{const i=e.querySelector('img'),m=e.querySelector('.category-card__media'),t=e.querySelector('.category-card__title'),a=e.querySelector('.category-card__link'),r=m?.getBoundingClientRect(),s=getComputedStyle(t);return {tag:t.tagName,font:s.fontSize,line:s.lineHeight,image:!!i,media:!!m,ratio:r?r.width/r.height:null,fit:i?getComputedStyle(i).objectFit:null,label:!!e.querySelector('.category-card__term,.category-card__term-plain')?.textContent.trim(),excerpt:!!e.querySelector('.category-card__excerpt').textContent.trim(),decoration:getComputedStyle(a).textDecorationLine}})}'''
try:
 profile=tempfile.TemporaryDirectory(prefix='featured-anonymous-',dir=root/'tmp')
 options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox';options.enable_bidi=True;options.accept_insecure_certs=False
 for arg in ('-headless','-no-remote','-profile',profile.name):options.add_argument(arg)
 driver=webdriver.Firefox(options=options,service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1'],log_output=str(run/'driver.log')))
 driver.script.add_javascript_error_handler(lambda e:errors.append(str(getattr(e,'text',e))))
 for width,columns in ((1440,3),(768,2),(390,1),(320,1)):
  driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900});driver.get('https://githeme:8890/')
  driver.execute_script("const m=document.querySelector('main');m.className='site-main site-container';m.innerHTML='<div id=\"featured-fixture\">'+arguments[0]+arguments[1]+'</div>';document.querySelectorAll('img').forEach(i=>i.loading='eager')",fixture['html'],fixture['plain'])
  WebDriverWait(driver,15).until(lambda d:d.execute_script("return [...document.querySelectorAll('.category-card img')].every(i=>i.complete&&i.naturalWidth>0)"))
  driver.execute_async_script('document.fonts.ready.then(()=>arguments[0]())')
  widget=driver.find_element(By.CSS_SELECTOR,'.githeme-post-cards');state=driver.execute_script(measure,widget)
  check(state['columns']==columns,'Responsive widget grid '+str(width),state)
  check(len(state['cards'])==3 and all(c['tag']=='H3' and c['label'] and c['excerpt'] and c['decoration']=='none' for c in state['cards']),'Shared card semantics/content '+str(width))
  check(all(not c['media'] or abs(c['ratio']-16/9)<.01 and c['fit']=='cover' for c in state['cards']),'Native 16:9 cover images '+str(width))
  check(driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'No page overflow '+str(width))
  check(driver.execute_script("const ids=[...document.querySelectorAll('#featured-fixture [id]')].map(e=>e.id);return new Set(ids).size===ids.length"),'Multiple widget IDs unique')
  plain=driver.find_elements(By.CSS_SELECTOR,'.githeme-post-cards')[1];plain_state=driver.execute_script(measure,plain)
  check(all(not c['media'] and c['excerpt'] and c['tag']=='H2' for c in plain_state['cards']),'No-image untitled widget presentation')
  if width in (1440,320):driver.save_screenshot(str(run/f'widget-{width}.png'))
  link=widget.find_element(By.CSS_SELECTOR,'.category-card__link');link.send_keys(Keys.NULL);driver.switch_to.active_element.send_keys(Keys.SHIFT+Keys.TAB);driver.switch_to.active_element.send_keys(Keys.TAB)
  check(driver.execute_script('const e=arguments[0];return e===document.activeElement&&e.matches(":focus-visible")&&getComputedStyle(e).outlineStyle!=="none"',link),'Visible keyboard focus')
  # Compare the very same template output under the archive CSS scope.
  driver.execute_script("const original=arguments[0],clone=original.cloneNode(true);clone.className='category-archive';clone.querySelectorAll('[id]').forEach(e=>e.id='archive-'+e.id);clone.querySelectorAll('[aria-labelledby]').forEach(e=>e.setAttribute('aria-labelledby','archive-'+e.getAttribute('aria-labelledby')));original.closest('section').after(clone)",widget)
  archive=driver.find_element(By.CSS_SELECTOR,'.category-archive');equivalent=driver.execute_script(measure,archive)
  check(state==equivalent,'Archive and widget share card/grid presentation '+str(width))
  driver.execute_script("const f=document.querySelector('#featured-fixture');f.classList.add('entry-content');f.style.cssText='width:280px;max-width:100%;margin-inline:auto'")
  narrow=driver.execute_script(measure,widget)
  check(narrow['columns']==1 and narrow['width']<=280 and driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'Narrow editorial container stays one column without overflow')
  check(all(c['font']==state['cards'][0]['font'] for c in narrow['cards']),'Shared component typography survives editorial nesting')
  driver.get('https://githeme:8890/category/news/')
  archive=driver.find_element(By.CSS_SELECTOR,'.category-archive');real=driver.execute_script(measure,archive)
  check(real['columns']==columns and len(real['cards'])==12 and all(c['tag']=='H2' for c in real['cards']),'Real category archive grid/count/headings preserved '+str(width))
  check(driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'Real archive no overflow')
 driver.find_element(By.CSS_SELECTOR,'a.next.page-numbers').click()
 WebDriverWait(driver,10).until(lambda d:d.find_element(By.CSS_SELECTOR,'.page-numbers.current').text=='2')
 check(len(driver.find_elements(By.CSS_SELECTOR,'.category-archive .category-card'))==12,'Native category pagination still returns 12 on page two')
 check(not errors,'No JavaScript errors',errors)
except Exception as exc:checks.append({'ok':False,'label':'Exception','details':str(exc)})
finally:
 if driver:
  try:driver.quit()
  except Exception as exc:checks.append({'ok':False,'label':'Browser cleanup','details':str(exc)})
 if profile:
  try:profile.cleanup()
  except Exception as exc:checks.append({'ok':False,'label':'Profile cleanup','details':str(exc)})
 (run/'browser-report.json').write_text(json.dumps(checks,indent=2))
failed=[c for c in checks if not c['ok']];print(json.dumps({'checks':len(checks),'failed':failed,'artifacts':str(run)},indent=2));raise SystemExit(bool(failed))
