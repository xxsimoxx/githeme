"""Local frontend integration tests; existing published fixtures only.
Source the external browser tools env.sh. All modified options are snapshotted,
including raw values, autoload flags, types and absence, and restored in finally.
"""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import socket
import ipaddress
import subprocess
import time
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--wp-path', required=True)
parser.add_argument('--front-page-id', required=True, type=int)
parser.add_argument('--posts-page-id', required=True, type=int)
parser.add_argument('--internal-page-id', required=True, type=int)
parser.add_argument('--post-id', required=True, type=int)
parser.add_argument('--fx-content-id', type=int)
parser.add_argument('--fx-page-id', type=int)
args = parser.parse_args()
root = Path(os.environ['CODEX_BROWSER_ROOT']).resolve()
assert os.path.ismount('/Volumes/Simo') and root.is_relative_to(Path('/Volumes/Simo'))
assert Path(os.environ['TMPDIR']).resolve() == root / 'tmp'
site = args.url.rstrip('/')
u = urlsplit(site)
assert u.scheme == 'https' and not u.username and not u.password
assert all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(u.hostname, u.port or 443))
os.umask(0o077)
lock = (root / 'tmp/browser.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
run = root / 'artifacts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-homepage-widgets')
run.mkdir(mode=0o700)
wp = ['wp', '--path=' + str(Path(args.wp_path).resolve())]

def cli(code):
    return subprocess.run(wp + ['eval', code], capture_output=True, text=True, check=True).stdout.strip()

def php_json(data):
    # Quoted PHP literal, never shell-interpolated. Values contain no credentials.
    return "json_decode('" + json.dumps(data).replace('\\', '\\\\').replace("'", "\\'") + "',true)"

ids = [args.front_page_id, args.posts_page_id, args.internal_page_id, args.post_id]
ids += [i for i in [args.fx_content_id, args.fx_page_id] if i]
assert len({args.front_page_id,args.posts_page_id,args.internal_page_id}) == 3
preconditions = cli("$ids=" + php_json(ids) + ";foreach($ids as $id){$p=get_post($id);if(!$p||$p->post_status!=='publish'||$p->post_password!==''){throw new Exception('Use existing public fixtures only');}}if(get_option('stylesheet')!=='githeme'){throw new Exception('Wrong active theme');}echo 'OK';")
option_names = ['show_on_front','page_on_front','page_for_posts','sidebars_widgets','widget_custom_html','theme_mods_githeme']
if args.fx_content_id: option_names.append('widget_fx_builder_widgets')
# Read the database representation and the public API representation before writes.
snapshot = json.loads(cli("global $wpdb;$names=" + php_json(option_names) + ";$s=array();foreach($names as $n){$row=$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A);$s[$n]=array('row'=>$row,'api'=>base64_encode(serialize(get_option($n))));}echo wp_json_encode($s);"))
(run / 'original-options.json').write_text(json.dumps(snapshot,indent=2))
guard_code = "$ids=" + php_json(ids) + ";$v=array();foreach($ids as $id){$v[$id]=array(get_post($id)->to_array(),get_post_meta($id));}echo hash('sha256',serialize(array($v,get_option('active_plugins'))));"
guard_hash = cli(guard_code)
state = json.loads(cli("echo wp_json_encode(array('sidebars'=>get_option('sidebars_widgets',array()),'html'=>get_option('widget_custom_html',array()),'fx'=>get_option('widget_fx_builder_widgets',array())));"))
def next_id(values):
    return max([1] + [int(k) for k in values if str(k).isdigit()]) + 1
html = state['html'] if isinstance(state['html'],dict) else {}
hero_num = next_id(html); content_num = hero_num + 1
html[str(hero_num)] = {'title':'Homepage Hero test','content':'<p>githeme-home-hero-marker <a href="#main-content">Hero keyboard link</a></p>'}
html[str(content_num)] = {'title':'Homepage Content test','content':'<p>githeme-home-content-marker <a href="#main-content">Content keyboard link</a></p>'}
html.setdefault('_multiwidget',1)
hero_id = 'custom_html-' + str(hero_num); content_id = 'custom_html-' + str(content_num)
fx = state['fx'] if isinstance(state['fx'],dict) else {}
fx_num = next_id(fx)
if args.fx_content_id:
    fx[str(fx_num)] = {'post_id':args.fx_content_id,'show_title':'on'}
    fx.setdefault('_multiwidget',1)
results=[]; errors=[]; failed_http=[]; documents=[]; driver=None; service=None; top=None

def record(test,**data):
    results.append({'test':test,**data})
    (run/'results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results[-1]),flush=True)

def set_options(values):
    cli("$v="+php_json(values)+";foreach($v as $n=>$value){update_option($n,$value);}echo 'OK';")

def configure(hero=True,content=True,mode='page',front=None,fx_content=False):
    sidebars=dict(state['sidebars'])
    sidebars['homepage-hero']=[hero_id] if hero else []
    sidebars['homepage-content']=[('fx_builder_widgets-'+str(fx_num)) if fx_content else content_id] if content else []
    set_options({'show_on_front':mode,'page_on_front':front or args.front_page_id,'page_for_posts':args.posts_page_id,'sidebars_widgets':sidebars})

def response(event):
    data = event if isinstance(event,dict) else vars(event)
    req = data.get('request',{}); resp = data.get('response',{})
    url = urlsplit(req.get('url','')); status = resp.get('status',0)
    item={'url':url.scheme+'://'+url.netloc+url.path,'status':status}
    if status>=400:failed_http.append(item)
    if data.get('context')==top and data.get('navigation') is not None:documents.append(item)

def js_error(event,kind):
    stack=getattr(event,'stacktrace',None) or getattr(event,'stack_trace',None) or {}
    frames=stack.get('callFrames',[]) if isinstance(stack,dict) else []
    errors.append({'kind':kind,'network':'network' in str(getattr(event,'text','')).lower(),
                   'frames':[{'path':urlsplit(f.get('url','')).path,'line':f.get('lineNumber')} for f in frames[:4]]})

def inspect(name,url,hero,content,screenshot=False):
    count=len(documents);driver.get(url)
    driver.execute_async_script('document.fonts.ready.then(arguments[0])')
    assert len(documents)>count and documents[-1]['status']==200,'No successful document response'
    assert not any(s in driver.page_source for s in ['Fatal error:', 'PHP Warning:', 'PHP Deprecated:'])
    data=driver.execute_script("""const m=document.querySelector('main'),h=document.getElementById('homepage-hero'),c=document.getElementById('homepage-content'),a=m?.querySelector('article.entry'),r=getComputedStyle(document.documentElement);
    return {mainCount:document.querySelectorAll('main').length,h1:m?.querySelectorAll('h1').length,hero:!!h,content:!!c,
    heroBeforePage:!!(h&&a&&(h.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_FOLLOWING)),contentAfterPage:!!(c&&a&&(a.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)),
    emptyAreas:[...document.querySelectorAll('.homepage-widget-area')].filter(e=>!e.innerHTML.trim()).length,
    skip:document.querySelector('.skip-link')?.getAttribute('href'),target:!!document.getElementById('main-content'),
    width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,heroWidth:h?.getBoundingClientRect().width,
    pageWidth:a?.getBoundingClientRect().width,mainClasses:m?.className,
    vars:Object.fromEntries(['--width-content','--width-wide','--width-layout','--font-body','--font-size-base','--color-text','--color-background'].map(k=>[k,r.getPropertyValue(k)]))};""")
    assert data['mainCount']==1 and data['h1']==1 and (hero is None or data['hero']==hero) and (content is None or data['content']==content)
    assert data['skip']=='#main-content' and data['target'] and data['emptyAreas']==0
    if hero:assert data['heroBeforePage'] and abs(data['heroWidth']-data['width'])<1
    if content:assert data['contentAfterPage']
    assert data['scroll']<=data['width'],'Horizontal overflow'
    if baseline_vars:assert data['vars']==baseline_vars,'Existing theme settings changed'
    record(name,http=documents[-1]['status'],**data)
    if screenshot:
        driver.execute_script("const b=document.getElementById('wpadminbar');if(b)b.style.visibility='hidden'")
        driver.save_screenshot(str(run/(name+'.png')))
        driver.execute_script("const b=document.getElementById('wpadminbar');if(b)b.style.visibility=''")
    return data

log_offsets={p:p.stat().st_size for p in [Path('/Applications/MAMP/logs/php_error.log'),Path('/Applications/MAMP/logs/apache_error.log')] if p.exists()}
baseline_vars=None
original_state=None
try:
    options=webdriver.FirefoxOptions()
    options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi=True;options.accept_insecure_certs=False
    options.add_argument('-headless');options.add_argument('-profile');options.add_argument(str(root/'profiles/firefox'))
    options.set_preference('browser.cache.disk.parent_directory',str(root/'cache/firefox'))
    service=Service(executable_path=str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(root/'tmp/driver-profiles'),'--log','fatal'],log_output=os.devnull,env=os.environ.copy())
    driver=webdriver.Firefox(options=options,service=service)
    assert Path(driver.capabilities['moz:profile']).resolve()==root/'profiles/firefox'
    driver.set_page_load_timeout(30);top=driver.current_window_handle
    driver.network.set_cache_behavior('bypass')
    driver.network.add_event_handler('response_started',response)
    driver.script.add_javascript_error_handler(lambda e:js_error(e,'uncaught'))
    driver.script.add_console_message_handler(lambda e:js_error(e,'console') if getattr(e,'level',None)=='error' else None)
    driver.browsing_context.set_viewport(context=top,viewport={'width':1440,'height':1000})
    original_state=inspect('original-homepage',site+'/',None,None)
    baseline_vars=original_state['vars']
    values={'widget_custom_html':html}
    if args.fx_content_id:values['widget_fx_builder_widgets']=fx
    set_options(values)
    for hero,content,label in [(True,True,'both'),(True,False,'hero-only'),(False,True,'content-only'),(False,False,'none')]:
        configure(hero,content)
        inspect('static-'+label,site+'/',hero,content,screenshot=True)
    configure()
    for width in [390,375,320]:
        driver.browsing_context.set_viewport(context=top,viewport={'width':width,'height':900})
        data=inspect('mobile-'+str(width),site+'/',True,True,screenshot=True)
        assert data['width']==width and data['height']==900
    driver.browsing_context.set_viewport(context=top,viewport={'width':1440,'height':1000})
    driver.get(site+'/')
    found=False
    for i in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        if driver.execute_script("return document.activeElement.matches('a.skip-link')"):
            found=True;break
    assert found,'Skip link not keyboard reachable'
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    assert driver.execute_script("return document.activeElement.id==='main-content'")
    link=driver.find_element(By.CSS_SELECTOR,'#homepage-hero a');link.send_keys(Keys.TAB)
    focused=driver.execute_script("const e=document.activeElement;return {focusVisible:e.matches(':focus-visible'),outline:getComputedStyle(e).outline,tag:e.tagName}")
    assert focused['focusVisible']
    record('keyboard',skip_target='main-content',**focused)
    inspect('separate-posts-page',site+'/?page_id='+str(args.posts_page_id),False,False)
    inspect('internal-page',site+'/?page_id='+str(args.internal_page_id),False,False)
    inspect('single-post',site+'/?p='+str(args.post_id),False,False)
    configure(mode='posts')
    inspect('latest-posts',site+'/',False,False)
    if args.fx_content_id:
        configure(fx_content=True)
        inspect('fx-widget',site+'/',True,True,screenshot=True)
        rendered=driver.find_element(By.ID,'homepage-content').get_attribute('innerHTML')
        assert 'githeme-test-nested-content' in rendered and 'githeme-test-ordinary-content' in rendered
        assert '[element' not in rendered and '[caption' not in rendered
        record('fx-parsing',nested_elements=True,ordinary_shortcode=True)
        for width in [390,375,320]:
            driver.browsing_context.set_viewport(context=top,viewport={'width':width,'height':900})
            inspect('fx-mobile-'+str(width),site+'/',True,True,screenshot=True)
    if args.fx_page_id:
        configure(front=args.fx_page_id)
        inspect('fx-static-page',site+'/',True,True)
        assert 'githeme-test-fx-content' in driver.find_element(By.CSS_SELECTOR,'main').text
        record('fx-page-editor-content',present=True)
finally:
    try:
        if driver is not None:driver.get('about:blank')
        restoration=cli("global $wpdb;$s="+php_json(snapshot)+";foreach($s as $n=>$v){if($v['row']===null){delete_option($n);}else{update_option($n,maybe_unserialize($v['row']['option_value']),$v['row']['autoload']);}$now=$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A);if($now!==$v['row']){throw new Exception('EXACT RESTORATION FAILED: '.$n);}}echo 'EXACT';")
        assert restoration=='EXACT','Stop: restoration failed'
        verification=cli("$s="+php_json(snapshot)+";foreach($s as $n=>$v){if(base64_encode(serialize(get_option($n)))!==$v['api']){throw new Exception('API RESTORATION FAILED: '.$n);}}echo 'EXACT';")
        assert verification=='EXACT','Stop: API restoration failed'
        assert cli(guard_code)==guard_hash,'Editorial fixtures or plugin activation changed'
        record('restoration',exact=True,editorial_and_plugins_unchanged=True,options=option_names)
        if driver is not None and original_state is not None:
            driver.browsing_context.set_viewport(context=top,viewport={'width':1440,'height':1000})
            inspect('restored-homepage',site+'/',original_state['hero'],original_state['content'])
    finally:
        if driver is not None:driver.quit()
        elif service is not None:service.stop()
        logs={}
        for p,offset in log_offsets.items():
            with p.open('rb') as f:f.seek(offset);logs[p.name]=len(f.read().splitlines())
        (run/'diagnostics.json').write_text(json.dumps({'errors':errors,'failed_http':failed_http,'new_log_lines':logs},indent=2))
        fcntl.flock(lock,fcntl.LOCK_UN)
        print('EVIDENCE '+str(run),flush=True)
