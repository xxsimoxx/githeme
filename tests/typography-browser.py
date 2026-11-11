"""Targeted read-only typography regression. Source Simo env.sh; --baseline before CSS edits."""
import argparse
import json
import os
from pathlib import Path
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true');parser.add_argument('--settings-only',action='store_true');parser.add_argument('--components-only',action='store_true');args=parser.parse_args()
root=Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR','')).resolve()!=root/'tmp':raise SystemExit('Source Simo env.sh first.')
run=root/'artifacts/20261111-typography';run.mkdir(exist_ok=True)
checks=[];samples=[];errors=[];driver=None

def check(ok,label,details=None):
 checks.append({'ok':bool(ok),'label':label,'details':details})
 if not ok:raise RuntimeError(label)

measure='''const root=getComputedStyle(document.documentElement);const pick=s=>[...document.querySelectorAll(s)].map(e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return {tag:e.tagName,text:e.textContent.trim().slice(0,40),width:r.width,height:r.height,top:r.top+scrollY,bottom:r.bottom+scrollY,font:parseFloat(c.fontSize),line:parseFloat(c.lineHeight),mt:parseFloat(c.marginTop),mb:parseFloat(c.marginBottom),pt:parseFloat(c.paddingTop),pb:parseFloat(c.paddingBottom),decoration:c.textDecorationLine,columns:c.gridTemplateColumns,gap:c.gap}});return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,customCSS:document.querySelector('#wp-custom-css')?.textContent,root:Object.fromEntries(['--font-size-base','--heading-scale','--heading-1','--heading-2','--heading-3','--heading-4','--heading-5','--space'].map(k=>[k,root.getPropertyValue(k)])),main:pick('.site-main'),title:pick('.entry-header h1'),meta:pick('.entry-meta'),prose:pick('.entry-content h1,.entry-content h2,.entry-content h3,.entry-content h4,.entry-content h5,.entry-content h6'),paragraphs:pick('.entry-content p').slice(0,3),links:pick('.entry-content p a:not(.fx-button),.entry-content li a'),menu:pick('.primary-menu > li > a'),rows:pick('.fxb-row > .fxb-wrap'),slider:pick('.githeme-gallery-slider img,.githeme-gallery-slider figcaption'),widgets:pick('.widget-title'),cards:pick('.category-card__media,.category-card__title'),header:pick('.site-header'),footer:pick('.site-footer')}'''
profile=None
try:
 profile=tempfile.TemporaryDirectory(prefix='typography-anonymous-',dir=root/'tmp')
 options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox';options.enable_bidi=True;options.accept_insecure_certs=False
 for arg in ('-headless','-no-remote','-profile',profile.name):options.add_argument(arg)
 driver=webdriver.Firefox(options=options,service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1'],log_output=str(run/'driver.log')))
 driver.script.add_javascript_error_handler(lambda e:errors.append(str(getattr(e,'text',e))))
 baseline=[] if args.baseline else json.loads((run/'baseline.json').read_text())['samples']
 for width in (() if args.settings_only or args.components_only else (1440,768,390,320)):
  driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
  for path in ('/','/?p=286','/?page_id=224','/category/news/'):
   driver.get('https://githeme:8890'+path)
   driver.execute_script('document.querySelectorAll("img").forEach(i=>i.loading="eager")')
   driver.execute_async_script('document.fonts.ready.then(()=>arguments[0]())')
   state=driver.execute_script(measure);samples.append({'path':path,**state})
   if args.baseline:continue
   before=next(s for s in baseline if s['path']==path and s['width']==width)
   check(not state['overflow'],'No overflow '+path+'/'+str(width))
   check(state['customCSS']==before['customCSS'],'Additional CSS unchanged')
   for component in ('header','footer','rows','slider','widgets','cards'):
    a=state[component];b=before[component]
    check(len(a)==len(b) and all(all(abs(x[k]-y[k])<1 for k in (('width','font') if component=='rows' else ('width','height','font'))) and x['gap']==y['gap'] and x['columns']==y['columns'] for x,y in zip(a,b)), 'Preserved '+component+' geometry/styles '+path+'/'+str(width))
   if state['title']:
    check(state['title'][0]['mt']==0,'Template title has no top margin')
    check(abs(state['main'][0]['pt']-(32 if width>=768 else 24))<1,'Singular top padding')
    if state['meta']:check(abs(state['meta'][0]['top']-state['title'][0]['bottom']-8)<1,'Title to metadata is 8px')
   if state['prose']:
    expected={'H1':39.81312 if width>=768 else 31.850496,'H2':27.648 if width>=768 else 24.192,'H3':23.04 if width>=768 else 20.736}
    check(all(abs(h['font']-expected[h['tag']])<.1 for h in state['prose'] if h['tag'] in expected),'Responsive editorial heading sizes')
   check(all(a['decoration']=='underline' for a in state['links']),'Editorial text links underlined')
   check(all(a['decoration']=='none' for a in state['menu']),'Menu links not underlined')
   focus=driver.find_elements(By.CSS_SELECTOR,'.entry-content p a:not(.fx-button),.entry-content li a,.category-card__link')
   if focus:
    focus[0].send_keys(Keys.NULL);driver.switch_to.active_element.send_keys(Keys.TAB);driver.switch_to.active_element.send_keys(Keys.SHIFT+Keys.TAB)
    check(driver.execute_script('const e=document.activeElement;return e===arguments[0]&&e.matches(":focus-visible")&&getComputedStyle(e).outlineStyle!=="none"',focus[0]),'Visible keyboard focus')
   if width in (1440,320):
    driver.execute_script('scrollTo(0,0)');driver.save_screenshot(str(run/(('home' if path=='/' else 'post' if 'p=286' in path else 'page' if '224' in path else 'news')+'-'+str(width)+'.png')))
 if args.settings_only:
  matrix=json.loads((run/'settings-matrix.json').read_text())
  for width in (1440,320):
   driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
   driver.get('https://githeme:8890/?page_id=224')
   driver.execute_script("const p=document.createElement('section');p.id='typography-probe';p.className='entry-content';p.innerHTML='<h1>Heading one</h1><h2>Heading two</h2><h3>Heading three</h3><h4>Heading four</h4><h5>Heading five</h5><h6>Heading six</h6><p><a href=\"#main-content\">Editorial link</a></p>';document.body.append(p)")
   driver.execute_script("const f=document.createElement('iframe');f.id='editor-probe';f.style.cssText='position:absolute;left:0;top:0;width:'+innerWidth+'px;height:800px;border:0;opacity:0;pointer-events:none';document.body.append(f);const doc=f.contentDocument;doc.head.innerHTML='<link rel=\"stylesheet\" href=\"https://githeme:8890/wp-content/themes/githeme/assets/css/editor.css\">';doc.body.className='mce-content-body';doc.body.innerHTML=document.querySelector('#typography-probe').innerHTML")
   from selenium.webdriver.support.ui import WebDriverWait
   WebDriverWait(driver,10).until(lambda d:d.execute_script("return !!document.querySelector('#editor-probe').contentDocument.querySelector('link').sheet"))
   for case in matrix:
    driver.execute_script("let s=document.querySelector('#typography-settings');if(!s){s=document.createElement('style');s.id='typography-settings';document.head.append(s)}s.textContent=arguments[0];const doc=document.querySelector('#editor-probe').contentDocument;let e=doc.querySelector('style');if(!e){e=doc.createElement('style');doc.head.append(e)}e.textContent=arguments[0]",case['css'])
    result=driver.execute_script("const read=(doc,sel)=>[...doc.querySelectorAll(sel)].map(e=>{const c=doc.defaultView.getComputedStyle(e);return {font:parseFloat(c.fontSize),mb:parseFloat(c.marginBottom),line:parseFloat(c.lineHeight)}});return {front:read(document,'#typography-probe h1,#typography-probe h2,#typography-probe h3,#typography-probe h4,#typography-probe h5,#typography-probe h6'),editor:read(document.querySelector('#editor-probe').contentDocument,'h1,h2,h3,h4,h5,h6')}")
    b=case['base']*16;scale=case['scale'];desktop=width>=768
    expected=[b*scale**5*(1 if desktop else .8),b*scale**3*(1 if desktop else .875),b*scale**2*(1 if desktop else .9),b*scale,b*(1+scale)/2,b]
    label=str(width)+' / '+str(case['base'])+' / '+str(scale)
    check(all(abs(x['font']-e)<.12 for x,e in zip(result['front'],expected)),'Configured base/scale respected '+label,result)
    check(all(abs(x['font']-y['font'])<.1 and abs(x['mb']-y['mb'])<.1 and abs(x['line']-y['line'])<.1 for x,y in zip(result['front'],result['editor'])),'Classic Editor typography matches frontend '+label)
    check(all(result['front'][i]['font']>=result['front'][i+1]['font'] for i in range(5)),'Heading hierarchy not inverted '+label)
    check(all(abs(x['mb']-(16 if desktop else 12))<.1 for x in result['front']),'Explicit heading bottom spacing '+label)
    samples.append({'width':width,'base':case['base'],'scale':scale,**result})
 if args.components_only:
  from selenium.webdriver.common.action_chains import ActionChains
  for width in (1440,768,390,320):
   driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
   driver.get('https://githeme:8890/')
   if width in (1440,320):
    driver.execute_script("document.querySelector('.entry-content h2').scrollIntoView({block:'center'})");driver.save_screenshot(str(run/('home-headings-'+str(width)+'.png')))
   before=driver.execute_script(measure)
   driver.execute_script("document.querySelector('.entry-content > .fxb-container > .fxb-default').classList.add('githeme-wide')")
   after=driver.execute_script(measure)
   check(abs(after['rows'][0]['width']-min(width-48,1216))<1,'githeme-wide width retained '+str(width))
   check(before['rows'][1]['width']==after['rows'][1]['width'] and before['rows'][1]['columns']==after['rows'][1]['columns'] and before['rows'][1]['gap']==after['rows'][1]['gap'],'Other FX Builder rows unchanged '+str(width))
   check(not after['overflow'],'No overflow with wide row '+str(width))
   driver.get('https://githeme:8890/?page_id=456')
   check(bool(driver.find_elements(By.CSS_SELECTOR,'.fx-button')),'Real FX Button present')
   driver.execute_script("const p=document.createElement('div');p.className='entry-content';p.innerHTML='<a class=\"fx-button fx-button--text\" href=\"#main-content\">Text fixture</a><a class=\"fx-button fx-button--outline\" href=\"#main-content\">Outline fixture</a><h2 class=\"widget-title\">Widget fixture</h2>';document.body.append(p)")
   check(driver.execute_script('return Math.abs(parseFloat(getComputedStyle(document.querySelector(".entry-content .widget-title")).fontSize)-33.1776)<.1'),'Nested widget heading retains original size')
   check(driver.execute_script('return [...document.querySelectorAll(".fx-button,.fx-card__link")].every(e=>getComputedStyle(e).textDecorationLine==="none")'),'FX component links not underlined '+str(width))
   for selector in ('.fx-button:not(.fx-button--text):not(.fx-button--outline)','.fx-button--text','.fx-button--outline'):
    elements=driver.find_elements(By.CSS_SELECTOR,selector)
    if elements:
     e=elements[0];driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",e);ActionChains(driver).move_to_element(e).perform()
     check(driver.execute_script('return getComputedStyle(arguments[0]).textDecorationLine==="none"',e),'Button hover without underline '+selector+'/'+str(width))
     e.send_keys(Keys.NULL);driver.switch_to.active_element.send_keys(Keys.SHIFT+Keys.TAB);driver.switch_to.active_element.send_keys(Keys.TAB)
     focus_state=driver.execute_script('const e=arguments[0],s=getComputedStyle(e);return {active:e===document.activeElement,visible:e.matches(":focus-visible"),outline:s.outlineStyle,decoration:s.textDecorationLine}',e)
     check(focus_state['active'] and focus_state['visible'] and focus_state['outline']!='none' and focus_state['decoration']=='none','Button focus visible without underline '+selector+'/'+str(width),focus_state)
   check(driver.execute_script('return [...document.querySelectorAll(".fx-card__title")].every(e=>Math.abs(parseFloat(getComputedStyle(e).fontSize)-19.2)<.1&&Math.abs(parseFloat(getComputedStyle(e).lineHeight)-24.96)<.1)'),'FX Card title keeps component typography '+str(width))
 check(not errors,'No JavaScript errors',errors)
except Exception as exc:checks.append({'ok':False,'label':'Exception','details':str(exc)})
finally:
 if driver:
  try:driver.quit()
  except Exception as exc:checks.append({'ok':False,'label':'Browser cleanup','details':str(exc)})
 if profile:
  try:profile.cleanup()
  except Exception as exc:checks.append({'ok':False,'label':'Profile cleanup','details':str(exc)})
 (run/('baseline.json' if args.baseline else 'settings-report.json' if args.settings_only else 'components-report.json' if args.components_only else 'report.json')).write_text(json.dumps({'checks':checks,'samples':samples,'errors':errors},indent=2))
failed=[c for c in checks if not c['ok']];print(json.dumps({'checks':len(checks),'failed':failed,'artifacts':str(run)},indent=2));raise SystemExit(bool(failed))
