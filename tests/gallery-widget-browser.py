"""Read-only widget slider fixture using actual theme CSS/JS. Source Simo env.sh."""
import argparse
import base64
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

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixtures',type=Path);args=parser.parse_args()
root=Path('/Volumes/Simo/Development/codex-browser-tools');theme=Path(__file__).resolve().parents[1]
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR','')).resolve()!=root/'tmp':raise SystemExit('Source Simo env.sh.')
if not args.fixtures.resolve().is_relative_to(root/'artifacts'):raise SystemExit('Keep artifacts on Simo.')
run=args.fixtures.resolve().parent;data=json.loads(args.fixtures.read_text());checks=[];errors=[];driver=None;profile=None

def font(match):
 u=urlsplit(match.group(1));prefix='/wp-content/themes/githeme/'
 if u.netloc!='githeme:8890' or not u.path.startswith(prefix):raise ValueError('Unexpected font origin')
 p=(theme/u.path[len(prefix):]).resolve()
 if not p.is_relative_to(theme/'assets/fonts') or p.suffix!='.woff2':raise ValueError('Unexpected font path')
 return 'url(data:font/woff2;base64,'+base64.b64encode(p.read_bytes()).decode()+')'
css=(theme/'style.css').read_text()+data['css']
css=re.sub(r'url\([\"\']?(https://[^)\"\']+\.woff2)[\"\']?\)',font,css)
path=run/'widget-fixture.html'
path.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https://githeme:8890 data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline' https://githeme:8890"><style>'''+css+'''</style><body><main class="site-container" id="widget-fixture">'''+data['html']+data['second']+data['single']+'</main>'+data['script']+'</body></html>')

def check(ok,label,details=None):
 checks.append({'ok':bool(ok),'label':label,'details':details})
 if not ok:raise RuntimeError(label)

def start(javascript=True,reduce=False):
 global profile,driver
 profile=tempfile.TemporaryDirectory(prefix='gallery-widget-',dir=root/'tmp')
 o=webdriver.FirefoxOptions();o.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox';o.enable_bidi=True;o.accept_insecure_certs=False
 for a in ('-headless','-no-remote','-profile',profile.name):o.add_argument(a)
 o.set_preference('javascript.enabled',javascript);o.set_preference('ui.prefersReducedMotion',1 if reduce else 0)
 driver=webdriver.Firefox(options=o,service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1'],log_output=str(run/'driver.log')))
 driver.script.add_javascript_error_handler(lambda e:errors.append(str(getattr(e,'text',e))))

def stop():
 global driver,profile
 try:
  if driver:driver.quit()
 finally:
  driver=None
  if profile:profile.cleanup();profile=None

try:
 start()
 for width in (1440,768,390,320):
  driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
  for direction in ('ltr','rtl'):
   driver.get(path.as_uri());driver.execute_script('document.documentElement.dir=arguments[0];document.querySelectorAll("img").forEach(i=>i.loading="eager")',direction)
   WebDriverWait(driver,15).until(lambda d:d.execute_script('return [...document.images].every(i=>i.complete&&i.naturalWidth>0)'))
   ports=driver.find_elements(By.CSS_SELECTOR,'.githeme-gallery-slider__viewport')
   check(len(ports)==2,'Two enhanced widgets, single image static')
   check(driver.execute_script('const ids=[...document.querySelectorAll("[id]")].map(e=>e.id);return ids.length===new Set(ids).size'),'Unique native/slider IDs')
   check(driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'No page overflow '+str(width)+'/'+direction)
   first,second=ports
   WebDriverWait(driver,10).until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'.githeme-gallery-slider__button'))>=2)
   snap=driver.execute_script('return getComputedStyle(arguments[0]).scrollSnapType',first)
   check(snap in ('x','x proximity'),'Shared proximity scroll snap retained (default proximity may be omitted in CSSOM)',snap)
   before=driver.execute_script('return arguments[0].scrollLeft',first)
   untouched=driver.execute_script('return arguments[0].scrollLeft',second)
   next_button=first.find_element(By.XPATH,'..').find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__next')
   check(next_button.get_attribute('aria-controls')==first.get_attribute('id') and bool(next_button.get_attribute('aria-label')),'Native labels and control association')
   next_button.click();time.sleep(.8)
   check(abs(driver.execute_script('return arguments[0].scrollLeft',first)-before)>1,'Next scrolls variable-width images')
   check(driver.execute_script('return arguments[0].scrollLeft',second)==untouched,'Second widget stays independent')
   first.send_keys(Keys.NULL);first.send_keys(Keys.TAB)
   check(driver.execute_script('const e=document.activeElement;return e.matches(".gallery-icon a")&&e.matches(":focus-visible")&&getComputedStyle(e).outlineStyle!=="none"'),'Keyboard image focus visible')
   links=first.find_elements(By.CSS_SELECTOR,'.gallery-icon a')
   for _ in range(len(links)-1):driver.switch_to.active_element.send_keys(Keys.TAB)
   time.sleep(2)
   check(driver.execute_script('const p=arguments[0],i=document.activeElement.querySelector("img");if(!i)return false;const r=i.getBoundingClientRect(),b=p.getBoundingClientRect(),l=b.left+p.clientLeft;return r.width>p.clientWidth||r.left>=l-1&&r.right<=l+p.clientWidth+1',first),'Focus correction stable after two seconds')
   driver.execute_script('document.querySelector("main").style.width="280px";document.querySelector("main").style.maxWidth="calc(100% - 2 * var(--space))"')
   check(driver.execute_script('return document.documentElement.scrollWidth<=innerWidth&&arguments[0].clientWidth<=280',first),'Narrow widget area without overflow')
   if width in (1440,320) and direction=='ltr':driver.save_screenshot(str(run/f'widget-{width}.png'))
 stop();start(False)
 driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':320,'height':900});driver.get(path.as_uri())
 check(not driver.find_elements(By.CSS_SELECTOR,'.githeme-gallery-slider__button'),'No inactive buttons without JavaScript')
 port=driver.find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__viewport');port.send_keys(Keys.NULL);port.send_keys(Keys.TAB)
 check(driver.execute_script('return document.activeElement.matches(".gallery-icon a")'),'Native image links keyboard-reachable without JavaScript')
 check(driver.execute_script('return arguments[0].scrollWidth>arguments[0].clientWidth&&getComputedStyle(arguments[0]).overflowX==="auto"',port),'Native horizontal scrolling without JavaScript')
 stop();start(True,True)
 driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':320,'height':900});driver.get(path.as_uri())
 check(driver.execute_script('return matchMedia("(prefers-reduced-motion: reduce)").matches'),'Reduced motion browser preference active')
 WebDriverWait(driver,10).until(lambda d:d.find_elements(By.CSS_SELECTOR,'.githeme-gallery-slider__next'))
 port=driver.find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__viewport');before=driver.execute_script('return arguments[0].scrollLeft',port)
 driver.find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__next').click()
 check(abs(driver.execute_script('return arguments[0].scrollLeft',port)-before)>1,'Reduced-motion next navigation completes immediately')
 check(not errors,'No JavaScript errors',errors)
except Exception as exc:checks.append({'ok':False,'label':'Exception','details':str(exc)})
finally:
 try:stop()
 except Exception as exc:checks.append({'ok':False,'label':'Cleanup','details':str(exc)})
 (run/'browser-report.json').write_text(json.dumps(checks,indent=2))
failed=[c for c in checks if not c['ok']];print(json.dumps({'checks':len(checks),'failed':failed,'artifacts':str(run)},indent=2));raise SystemExit(bool(failed))
