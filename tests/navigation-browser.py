"""Authorized local navigation tests: temporary native menus, exact option restoration.
Source the external Selenium env.sh; use --baseline before changing theme code.
"""
import argparse
import datetime
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.service import Service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--wp-path', required=True)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(os.environ['CODEX_BROWSER_ROOT']).resolve()
assert os.path.ismount('/Volumes/Simo') and root.is_relative_to(Path('/Volumes/Simo'))
assert Path(os.environ['TMPDIR']).resolve() == root/'tmp'
site = args.url.rstrip('/')
u = urlsplit(site)
assert u.scheme == 'https' and not u.username and not u.password
assert all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(u.hostname,u.port or 443))
os.umask(0o077)
lock = (root/'tmp/browser.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
run = root/'artifacts'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-navigation'+('-baseline' if args.baseline else ''))
run.mkdir(mode=0o700)
wp = ['wp','--path='+str(Path(args.wp_path).resolve())]
def cli(code):
    return subprocess.run(wp+['eval',code],capture_output=True,text=True,check=True).stdout.strip()
def literal(data):
    return "json_decode('"+json.dumps(data).replace('\\','\\\\').replace("'","\\'")+"',true)"
assert cli("echo get_stylesheet();")=='githeme'
snapshot = json.loads(cli("global $wpdb;$s=array();foreach(array('theme_mods_githeme','nav_menu_options') as $n){$s[$n]=array('row'=>$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A),'api'=>base64_encode(serialize(get_option($n))));}echo wp_json_encode($s);"))
(run/'original-options.json').write_text(json.dumps(snapshot,indent=2))
assert json.loads((run/'original-options.json').read_text())==snapshot
# Check all pre-existing posts/menus, their metadata, relationships and relevant options.
guard_code="global $wpdb;echo hash('sha256',serialize(array($wpdb->get_results('SELECT * FROM '.$wpdb->posts.' ORDER BY ID',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->postmeta.' ORDER BY meta_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->terms.' ORDER BY term_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->term_taxonomy.' ORDER BY term_taxonomy_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->term_relationships.' ORDER BY object_id,term_taxonomy_id',ARRAY_A),get_option('sidebars_widgets'),get_option('show_on_front'),get_option('page_on_front'),get_option('page_for_posts'),get_option('active_plugins'))));"
guard = cli(guard_code)
menus=[];driver=None;results=[];errors=[];failed=[];disabled_scripts=False
logs={p:p.stat().st_size for p in [Path('/Applications/MAMP/logs/php_error.log'),Path('/Applications/MAMP/logs/apache_error.log')] if p.exists()}
def record(name,**values):
    results.append({'test':name,**values});(run/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results[-1]),flush=True)
def assign(menu,layout='inline'):
    cli("$l=get_theme_mod('nav_menu_locations',array());$l['primary']="+str(menu)+";set_theme_mod('nav_menu_locations',$l);set_theme_mod('githeme_header_layout',"+literal(layout)+");")
def start(javascript=True):
    options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi=True;options.accept_insecure_certs=False
    options.add_argument('-headless');options.add_argument('-profile');options.add_argument(str(root/'profiles/firefox'))
    # Per-process preference is restored before quitting the no-JS test.
    options.set_preference('javascript.enabled',javascript)
    service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(root/'tmp/driver-profiles'),'--log','fatal'],log_output=os.devnull)
    d=webdriver.Firefox(options=options,service=service)
    assert Path(d.capabilities['moz:profile']).resolve()==root/'profiles/firefox'
    d.set_page_load_timeout(30)
    d.network.set_cache_behavior('bypass')
    d.script.add_javascript_error_handler(lambda e:errors.append({'kind':'uncaught','type':type(e).__name__}))
    d.script.add_console_message_handler(lambda e:errors.append({'kind':'console','type':type(e).__name__}) if getattr(e,'level',None)=='error' else None)
    def response(e):
        v=e if isinstance(e,dict) else vars(e);status=v.get('response',{}).get('status',0)
        if status>=400:
            x=urlsplit(v.get('request',{}).get('url',''));failed.append({'url':x.scheme+'://'+x.netloc+x.path,'status':status})
    d.network.add_event_handler('response_started',response)
    return d

def viewport(width):
    driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':1000})
    time.sleep(.15)
def inspect(name,width,expected_links=7,nojs=False):
    viewport(width);driver.get(site+'/');time.sleep(.2)
    data=driver.execute_script("""const n=document.querySelector('.primary-navigation'),m=document.getElementById('primary-menu'),t=n?.querySelector('button'),b=document.querySelector('.site-branding'),r=e=>e.getBoundingClientRect();return {width:innerWidth,scroll:document.documentElement.scrollWidth,links:m?.querySelectorAll('a').length||0,toggle:!!t&&!t.hidden,expanded:t?.getAttribute('aria-expanded'),menuHidden:m?.hidden,buttonName:t?.textContent.trim(),controls:t?.getAttribute('aria-controls'),nested:!!m?.querySelector('ul ul'),navTop:n?r(n).top:null,brandingBottom:r(b).bottom,topRows:m?[...m.children].map(e=>r(e).top):[],roles:!!m?.querySelector('[role="menu"]'),oneMenu:document.querySelectorAll('#primary-menu').length};""")
    assert data['width']==width and data['scroll']<=width and data['links']==expected_links
    assert not data['roles'] and data['oneMenu']==(1 if expected_links else 0)
    if expected_links:
        assert data['controls']=='primary-menu' and data['buttonName']
        if nojs:assert not data['toggle'] and not data['menuHidden']
        elif width<=768:assert data['toggle'] and data['menuHidden'] and data['expanded']=='false'
    record(name,**data)
    driver.execute_script("document.getElementById('wpadminbar')?.style.setProperty('visibility','hidden')")
    driver.save_screenshot(str(run/(name+'.png')))
    return data

def keyboard(name):
    toggle=driver.find_element(By.CSS_SELECTOR,'.menu-toggle')
    assert toggle.get_attribute('type')=='button'
    # Tab through actual document: hidden menu links must not be in the tab order.
    driver.execute_script('document.activeElement.blur()')
    for _ in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        active=driver.switch_to.active_element
        assert not driver.execute_script("return !!document.activeElement.closest('#primary-menu')")
        if active==toggle:break
    else:raise AssertionError('Toggle not reachable')
    assert driver.execute_script("return document.activeElement.matches(':focus-visible')&&getComputedStyle(document.activeElement).outlineStyle!=='none'")
    toggle.send_keys(Keys.SPACE)
    assert toggle.get_attribute('aria-expanded')=='true'
    assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth')
    assert driver.execute_script("return getComputedStyle(document.querySelector('#primary-menu')).flexDirection==='column'")
    driver.save_screenshot(str(run/(name+'-open.png')))
    links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
    for link in links:
        assert link.is_displayed()
        driver.switch_to.active_element.send_keys(Keys.TAB)
        assert driver.switch_to.active_element==link
        assert driver.execute_script("return document.activeElement.matches(':focus-visible')")
    for link in reversed(links[:-1]):
        driver.switch_to.active_element.send_keys(Keys.SHIFT,Keys.TAB)
        assert driver.switch_to.active_element==link
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    assert driver.switch_to.active_element==toggle and toggle.get_attribute('aria-expanded')=='false'
    toggle.send_keys(Keys.ENTER);assert toggle.get_attribute('aria-expanded')=='true'
    toggle.click();assert toggle.get_attribute('aria-expanded')=='false'
    toggle.click();assert toggle.get_attribute('aria-expanded')=='true'
    for link in links:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'})",link)
        assert driver.execute_script("const e=arguments[0],r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))",link),'Link obscured'
        ActionChains(driver).move_to_element(link).perform()
    toggle.click();assert toggle.get_attribute('aria-expanded')=='false'
    record(name,space=True,enter=True,tab_and_shift_tab=True,escape=True,hidden_links_skipped=True,focus_visible=True)
def dynamic_header():
    viewport(1440);driver.get(site+'/')
    driver.execute_async_script('document.fonts.ready.then(arguments[0])')
    driver.execute_script("""window.navProbe={frames:0,states:[],changes:0};
    const n=document.querySelector('.primary-navigation');
    new MutationObserver(records=>navProbe.changes+=records.length).observe(n,{attributes:true,subtree:true,attributeFilter:['class','hidden','aria-expanded']});
    """)
    failures=[]
    def check(name,compact):
        # Sample final layout over many frames; observer loops cannot pass a snapshot.
        samples=driver.execute_async_script("""const done=arguments[0],samples=[];let last=0;
        function sample(t){if(t-last>=40){last=t;const n=document.querySelector('.primary-navigation'),b=n.querySelector('button');samples.push({compact:n.classList.contains('is-compact'),expanded:b.getAttribute('aria-expanded'),width:innerWidth,scroll:document.documentElement.scrollWidth,changes:navProbe.changes});}if(samples.length<15)requestAnimationFrame(sample);else done(samples);}requestAnimationFrame(sample);""")
        stable=samples[5:]
        ok=all(x['compact']==compact and x['width']==1440 and x['scroll']<=1440 for x in stable)
        settled=stable[-1]['changes']==stable[0]['changes']
        record(name,expected_compact=compact,passed=ok,settled=settled,final=stable[-1])
        if not ok or not settled:failures.append(name)
    # A logo is a transient DOM probe, never a media-library or theme_mod write.
    driver.execute_script("""const b=document.querySelector('.site-branding'),i=document.createElement('img');i.id='navigation-test-logo';i.alt='';i.width=650;i.height=80;i.src='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="650" height="80"></svg>';b.prepend(i);""")
    check('dynamic-logo-large',True)
    driver.execute_script("document.getElementById('navigation-test-logo').remove()")
    check('dynamic-logo-removed',False)
    driver.execute_script("document.querySelector('.header-inner').style.width='800px'")
    check('dynamic-container-narrow',True)
    driver.execute_script("document.querySelector('.header-inner').style.removeProperty('width')")
    check('dynamic-container-restored',False)
    driver.execute_script("document.querySelector('.site-branding').style.width='400px'")
    check('dynamic-branding-wide',True)
    driver.execute_script("document.body.classList.add('githeme-header-stacked')")
    check('dynamic-layout-stacked',False)
    driver.execute_script("document.body.classList.remove('githeme-header-stacked')")
    check('dynamic-layout-inline',True)
    driver.execute_script("document.querySelector('.site-branding').style.removeProperty('width')")
    check('dynamic-branding-restored',False)
    # Fix branding metrics to isolate font changes in the navigation itself.
    driver.execute_script("""const b=document.querySelector('.site-branding');b.style.fontFamily=getComputedStyle(b).fontFamily;b.style.width='100px';document.querySelector('.header-inner').style.width='1100px';""")
    check('dynamic-font-system',False)
    driver.execute_script("document.documentElement.style.setProperty('--font-body','monospace')")
    check('dynamic-font-monospace',True)
    driver.execute_script("document.documentElement.style.removeProperty('--font-body')")
    check('dynamic-font-restored',False)
    # Load a real local font only after the page and document.fonts.ready have settled.
    driver.execute_script("document.documentElement.style.setProperty('--font-body', '\"Navigation Late Font\", monospace')")
    check('dynamic-font-before-load',True)
    loaded=driver.execute_async_script("""const done=arguments[0],url=new URL('/wp-content/themes/githeme/assets/fonts/source-sans-3/SourceSans3VF-Upright.ttf.woff2',location.href);const f=new FontFace('Navigation Late Font','url("'+url.href+'")');document.fonts.add(f);f.load().then(()=>done(f.status),()=>done('error'));""")
    assert loaded=='loaded'
    check('dynamic-local-font-loaded',False)
    driver.execute_script("document.documentElement.style.removeProperty('--font-body')")
    check('dynamic-local-font-reset',False)
    driver.get(site+'/')
    assert not failures,'Dynamic header checks failed: '+', '.join(failures)

try:
    for flat in [False,True]:
        labels=['Home','Servizi','Una etichetta lunga per informazioni approfondite e risorse del sito','Contatti','Articoli']
        if not flat:labels+=['Dettagli','Approfondimenti']
        # Only these newly created menu objects are removed at exit.
        code="$m=wp_create_nav_menu('githeme-test-navigation-"+run.name+('-flat' if flat else '-nested')+"');if(is_wp_error($m)){throw new Exception('Menu creation failed');}try{$ids=array();$labels="+literal(labels)+";$pages=get_posts(array('post_type'=>'page','post_status'=>'publish','numberposts'=>5,'orderby'=>'ID','order'=>'ASC'));if(!$pages){throw new Exception('Existing pages required');}foreach($labels as $i=>$label){$parent=$i===5?$ids[1]:($i===6?$ids[5]:0);$id=wp_update_nav_menu_item($m,0,array('menu-item-title'=>$label,'menu-item-object-id'=>$pages[$i%count($pages)]->ID,'menu-item-object'=>'page','menu-item-type'=>'post_type','menu-item-status'=>'publish','menu-item-parent-id'=>$parent,'menu-item-position'=>$i+1));if(is_wp_error($id)){throw new Exception('Menu item creation failed');}$ids[]=$id;}echo $m;}catch(Throwable $e){wp_delete_nav_menu($m);throw $e;}"
        menus.append(int(cli(code)))
        (run/'temporary-menu-ids.json').write_text(json.dumps(menus))
    driver=start()
    assign(0);inspect('unassigned',390,0)
    assign(menus[0])
    if not args.baseline:
        dynamic_header()
    if not args.baseline:
        viewport(390);driver.get(site+'/');time.sleep(.2)
        driver.find_element(By.CSS_SELECTOR,'.menu-toggle').click()
        viewport(375)
        assert driver.execute_script("return document.activeElement.matches('.menu-toggle')"),'Compact resize lost toggle focus'
        assert driver.find_element(By.CSS_SELECTOR,'.menu-toggle').get_attribute('aria-expanded')=='true'
        record('compact-resize-focus',passed=True,expanded_preserved=True)
    for width in [1440,1024,820,768,390,375,320]:
        data=inspect('nested-'+str(width),width)
        if width in [1024,820] and not args.baseline:
            assert data['toggle'],'Insufficient space must collapse the navigation'
        if data['toggle']:keyboard('keyboard-'+str(width))
        else:
            links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
            ActionChains(driver).move_to_element(links[1]).perform()
            assert all(link.is_displayed() for link in links)
            links[0].send_keys(Keys.TAB)
            for link in links[2:]:
                driver.switch_to.active_element.send_keys(Keys.TAB);assert driver.switch_to.active_element==link
            record('desktop-mouse-keyboard-'+str(width),all_nested_links_visible=True)
    # Skip link remains the first frontend tab stop after the authenticated toolbar.
    driver.get(site+'/')
    for _ in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        if driver.execute_script("return document.activeElement.matches('.skip-link')"):break
    else:raise AssertionError('Skip link not found')
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    assert driver.execute_script("return document.activeElement.id==='main-content'")
    record('skip-link',passed=True)
    assign(menus[1]);inspect('flat-desktop',1440,5);inspect('flat-mobile',375,5);keyboard('flat-keyboard')
    assign(menus[0],'stacked');inspect('stacked-desktop',1440);inspect('stacked-mobile',390);keyboard('stacked-keyboard')
    # Crossing the breakpoint must never strand focus inside a hidden subtree.
    viewport(1440);driver.get(site+'/');driver.find_element(By.CSS_SELECTOR,'#primary-menu a').send_keys(Keys.TAB)
    viewport(320)
    assert driver.execute_script("return document.activeElement.matches('.menu-toggle')")
    viewport(1440)
    assert driver.execute_script("return document.activeElement.matches('#primary-menu a')")
    record('resize-focus',passed=True)
    driver.quit();driver=None
    assign(menus[0])
    disabled_scripts=True
    driver=start(False)
    # Marionette execute_script remains usable even when page scripts are disabled.
    for width in [1440,820,390,375,320]:
        inspect('no-js-'+str(width),width,nojs=True)
        links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
        assert all(link.is_displayed() for link in links)
        links[0].send_keys(Keys.TAB)
        for link in links[2:]:
            driver.switch_to.active_element.send_keys(Keys.TAB);assert driver.switch_to.active_element==link
    record('no-js-keyboard',passed=True)
finally:
    try:
        browser_cleanup_error=None
        try:
            if driver:
                driver.quit();driver=None
            if disabled_scripts:
                driver=start(True);driver.quit();driver=None
        except Exception as exc:
            browser_cleanup_error=exc
        for menu in menus:
            assert cli("$r=wp_delete_nav_menu("+str(menu)+");if(is_wp_error($r)||!$r){throw new Exception('Cleanup failed');}echo 'OK';")=='OK'
        assert cli("$s="+literal(snapshot)+";foreach($s as $n=>$v){if($v['row']===null){delete_option($n);}else{update_option($n,maybe_unserialize($v['row']['option_value']),$v['row']['autoload']);}}echo 'OK';")=='OK'
        assert cli("global $wpdb;$s="+literal(snapshot)+";foreach($s as $n=>$v){$r=$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A);if($r!==$v['row']||base64_encode(serialize(get_option($n)))!==$v['api']){throw new Exception('Exact restoration failed: '.$n);}}echo 'EXACT';")=='EXACT'
        assert cli(guard_code)==guard,'Existing data differs after cleanup'
        record('restoration',exact=True,temporary_menus_removed=True,preexisting_data_unchanged=True)
        if browser_cleanup_error:raise browser_cleanup_error
    finally:
        newlogs={}
        for p,offset in logs.items():
            with p.open('rb') as f:f.seek(offset);newlogs[p.name]=len(f.read().splitlines())
        (run/'diagnostics.json').write_text(json.dumps({'errors':errors,'failed_http':failed,'new_log_lines':newlogs},indent=2))
        print('EVIDENCE '+str(run),flush=True)
