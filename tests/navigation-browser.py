"""Authorized local navigation tests: temporary native menus, exact option restoration.
Source the external Selenium env.sh; use --baseline before changing theme code.
"""
import argparse
import dataclasses
import hashlib
import re
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

# Explicit checks and cleanup run equally under Python, -O and PYTHONOPTIMIZE.
def require(condition, message='Check failed'):
    if not condition:
        raise AssertionError(message)


def error_info(phase, exc):
    # CalledProcessError contains its command, which can include private snapshots.
    if isinstance(exc, subprocess.CalledProcessError):
        message = 'WP-CLI failed with exit ' + str(exc.returncode)
    elif isinstance(exc, subprocess.TimeoutExpired):
        message = 'WP-CLI timed out after ' + str(exc.timeout) + ' seconds'
    else:
        message = str(exc)
    message = re.sub(r'https?://[^\s\"\']+', lambda m: safe_url(m.group()), message)
    frames = []
    trace = exc.__traceback__
    while trace:
        frames.append({'file': trace.tb_frame.f_code.co_filename, 'line': trace.tb_lineno, 'function': trace.tb_frame.f_code.co_name})
        trace = trace.tb_next
    return {'phase': phase, 'type': type(exc).__name__, 'message': message[:1500], 'frames': frames[-4:]}


def attempt(phase, action, failures):
    try:
        action()
        return True
    except Exception as exc:
        failures.append(error_info(phase, exc))
        return False


def safe_url(value):
    try:
        u = urlsplit(value)
        return u.scheme + '://' + (u.hostname or '') + (':' + str(u.port) if u.port else '') + u.path
    except ValueError:
        return '<invalid-url>'


def event_data(event):
    return event if isinstance(event, dict) else dataclasses.asdict(event) if dataclasses.is_dataclass(event) else vars(event)


def capture_js(event, kind):
    data = event_data(event)
    message = str(data.get('text', ''))
    category = re.search(r'(?:Type|Reference|Syntax|Network|Abort|Range|Security)?Error', message)
    stack = data.get('stacktrace') or data.get('stack_trace') or {}
    frames = stack.get('callFrames', stack.get('call_frames', [])) if isinstance(stack, dict) else []
    errors.append({'kind': kind, 'category': category.group() if category else 'unspecified',
                   'network_failure': 'fetch' in message.lower() or 'network' in message.lower(),
                   'navigating': navigating, 'phase': results[-1]['test'] if results else 'startup',
                   'frames': [{'path': urlsplit(f.get('url', '')).path,
                               'function': f.get('functionName', f.get('function_name')),
                               'line': f.get('lineNumber', f.get('line_number'))} for f in frames[:5]]})


preview_contexts = set()
completed_documents = []


def capture_document(event):
    data = event_data(event)
    status = data.get('response', {}).get('status', 0)
    if data.get('navigation') and 200 <= status < 300:
        completed_documents.append({'context': data.get('context'), 'navigation': data['navigation'],
                                    'timestamp': data.get('timestamp', 0),
                                    'url': safe_url(data.get('request', {}).get('url', ''))})


def capture_fetch(event):
    data = event_data(event)
    fetch_failures.append({'url': safe_url(data.get('request', {}).get('url', '')),
                           'error': str(data.get('errorText', data.get('error_text', 'unknown')))[:200],
                           'navigating': navigating, 'context': data.get('context'), 'navigation': data.get('navigation'),
                           'timestamp': data.get('timestamp', 0)})


def navigate(url):
    global navigating
    navigating = True
    try:
        driver.get(url)
    finally:
        navigating = False


def profile_scripting_state():
    # Inspect this preference only, never cookies, logins or other profile data.
    state = {}
    for name in ('user.js', 'prefs.js'):
        path = root / 'profiles/firefox' / name
        matches = re.findall(r'user_pref\("javascript\.enabled",\s*(true|false)\)', path.read_text()) if path.exists() else []
        state[name] = matches[-1] if matches else None
    return state


def restore_profile_scripting(failures):
    if profile_scripting_state() == profile_js_initial:
        return
    require(set(profile_js_initial.values()) <= {'true', 'false', None}, 'Invalid profile preference snapshot')
    # Geckodriver restores user.js itself; Firefox flushes the running value
    # to prefs.js. An absent prefs.js key denotes Firefox's true default.
    restored_value = profile_js_initial['prefs.js'] != 'false'
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.accept_insecure_certs = False
    options.add_argument('-headless')
    options.add_argument('-profile')
    options.add_argument(str(root / 'profiles/firefox'))
    options.set_preference('javascript.enabled', restored_value)
    reset_service = Service(str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=os.devnull)
    browser = None
    try:
        browser = webdriver.Firefox(options=options, service=reset_service)
        browser.set_page_load_timeout(15)
        # Finish a real document load before shutdown; quitting during startup
        # does not reliably flush the restored Firefox preference to disk.
        browser.get('data:text/html,<p>Profile preference restoration</p>')
        require(browser.find_element(By.TAG_NAME, 'p').text == 'Profile preference restoration', 'Profile restoration session did not finish loading')
    finally:
        if browser is not None:
            attempt('profile-reset-browser-quit', browser.quit, failures)
        attempt('profile-reset-driver-stop', reset_service.stop, failures)
    deadline = time.monotonic() + 5
    while profile_scripting_state() != profile_js_initial and time.monotonic() < deadline:
        time.sleep(0.1)
    require(profile_scripting_state() == profile_js_initial, 'Profile preference reset was not verified')


def snapshot_options(names):
    value = json.loads(cli("global $wpdb;$s=array();foreach(" + php_json(names) + " as $n){"
        "$v=get_option($n);$a=serialize($v);if(serialize(unserialize($a,array('allowed_classes'=>false)))!==$a){throw new Exception('Unsupported snapshot type');}"
        "$s[$n]=array('row'=>$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A),'api'=>base64_encode($a));}echo wp_json_encode($s);"))
    require(set(value) == set(names), 'Incomplete option snapshot')
    path = run / 'original-options.json'
    path.write_text(json.dumps(value, indent=2))
    require(json.loads(path.read_text()) == value, 'Snapshot file could not be verified')
    return value


def restore_option(name, saved):
    # Restore the exact DB representation, without sanitizers changing types or
    # update_option() skipping an autoload-only change. Only snapshotted names.
    code = "global $wpdb;$n=" + php_json(name) + ";$v=" + php_json(saved) + ";"
    code += "$row=$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A);"
    code += "if($v['row']===null){$ok=$wpdb->delete($wpdb->options,array('option_name'=>$n));}"
    code += "elseif($row===null){$ok=$wpdb->insert($wpdb->options,array_merge(array('option_name'=>$n),$v['row']));}"
    code += "else{$ok=$wpdb->update($wpdb->options,$v['row'],array('option_name'=>$n));}"
    code += "if(false===$ok){throw new Exception('Option restoration write failed: '.$n);}"
    code += "wp_cache_delete($n,'options');wp_cache_delete('alloptions','options');wp_cache_delete('notoptions','options');echo 'OK';"
    require(cli(code) == 'OK', 'Option restoration failed: ' + name)


def verify_options(saved):
    # A new CLI process avoids update-time cache/type artifacts.
    code = "global $wpdb;$s=" + php_json(saved) + ";foreach($s as $n=>$v){"
    code += "$row=$wpdb->get_row($wpdb->prepare('SELECT option_value,autoload FROM '.$wpdb->options.' WHERE option_name=%s',$n),ARRAY_A);"
    code += "if($row!==$v['row']||base64_encode(serialize(get_option($n)))!==$v['api']){throw new Exception('Exact verification failed: '.$n);}}echo 'EXACT';"
    require(cli(code) == 'EXACT', 'Exact option verification failed')


def diagnostics(js, http, fetches, offsets):
    fatal, known, logs = [], [], {}
    origin = urlsplit(site)
    for item in http:
        url = urlsplit(item.get('url', site + item.get('path', '')))
        favicon = (url.scheme, url.netloc) == (origin.scheme, origin.netloc) and url.path == '/favicon.ico' and item['status'] == 404
        (known if favicon else fatal).append({'source': 'http', 'reason': 'known-favicon-404' if favicon else 'http-error', **item})
    for item in js:
        lock_abort = item.get('navigating') and item.get('network_failure') and any(
            f.get('path') == '/wp-admin/js/customize-controls.js' and
            (f.get('function') or '').startswith('refreshLockState') for f in item.get('frames', []))
        (known if lock_abort else fatal).append({'source': 'javascript', 'reason': 'known-lock-refresh-navigation' if lock_abort else 'javascript-error', **item})
    for item in fetches:
        url = urlsplit(item['url'])
        lock_abort = (url.scheme, url.netloc) == (origin.scheme, origin.netloc) and url.path == '/wp-admin/admin-ajax.php' and item['navigating'] and item['error'] in ('NS_BINDING_ABORTED', 'NS_ERROR_ABORT')
        # Only confirmed preview document navigations may be superseded by a
        # later successful document in that same iframe. Never exempt assets.
        preview_abort = item.get('context') in globals().get('preview_contexts', set()) and bool(item.get('navigation')) and item['error'] == 'NS_BINDING_ABORTED' and (url.scheme, url.netloc) == (origin.scheme, origin.netloc) and (
            item['navigating'] or any(d['context'] == item['context'] and d['navigation'] != item['navigation'] and
                d['timestamp'] >= item.get('timestamp', 0) and d['url'] == item['url'] for d in globals().get('completed_documents', [])))
        reason = 'known-ajax-navigation-abort' if lock_abort else 'superseded-preview-document' if preview_abort else 'transport-error'
        (known if lock_abort or preview_abort else fatal).append({'source': 'fetch', 'reason': reason, **item})
    for path, offset in offsets.items():
        require(path.stat().st_size >= offset, 'Log rotated/truncated; diagnostic coverage lost: ' + str(path))
        with path.open('rb') as stream:
            stream.seek(offset)
            delta = stream.read()
        lines = [line for line in delta.decode('utf-8', errors='replace').splitlines() if line.strip()]
        logs[path.name] = {'offset': offset, 'bytes': len(delta), 'lines': len(lines), 'sha256': hashlib.sha256(delta).hexdigest()}
        for number, line in enumerate(lines, 1):
            # No raw log payloads: they may contain user data or request parameters.
            favicon = path.name == 'apache_error.log' and bool(re.search(r'(File does not exist|not found).*[/\\]favicon\.ico\b', line, re.I))
            level = re.search(r'Fatal error|Parse error|Warning|Notice|Deprecated|Uncaught|error|crit|alert|emerg', line, re.I)
            (known if favicon else fatal).append({'source': 'server-log', 'file': str(path), 'line_after_offset': number,
                'category': level.group() if level else 'new-log-entry', 'reason': 'known-favicon-log' if favicon else 'new-server-log-entry',
                'sha256': hashlib.sha256(line.encode()).hexdigest()})
    return {'fatal': fatal, 'known': known, 'logs': logs, 'errors': js, 'failed_http': http, 'fetch_failures': fetches, 'completed_documents': globals().get('completed_documents', []), 'preview_contexts': sorted(globals().get('preview_contexts', set()))}


def finish_report(failures, js, http, fetches, offsets):
    report = {'fatal': [], 'known': [], 'errors': js, 'failed_http': http, 'fetch_failures': fetches, 'completed_documents': globals().get('completed_documents', []), 'preview_contexts': sorted(globals().get('preview_contexts', set()))}
    def collect():
        report.update(diagnostics(js, http, fetches, offsets))
    attempt('collect-diagnostics', collect, failures)
    if report['fatal']:
        failures.append({'phase': 'diagnostics', 'type': 'DiagnosticFailure',
                         'message': str(len(report['fatal'])) + ' unexpected diagnostic events; see diagnostics.json'})
    attempt('unlock-profile', lambda: fcntl.flock(lock, fcntl.LOCK_UN), failures)
    report['failures'] = failures.copy()
    report['passed'] = not failures
    attempt('write-diagnostics', lambda: (run / 'diagnostics.json').write_text(json.dumps(report, indent=2)), failures)
    print('EVIDENCE ' + str(run), flush=True)
    if failures:
        raise RuntimeError('Test failed: ' + json.dumps(failures)) from None


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--wp-path', required=True)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(os.environ['CODEX_BROWSER_ROOT']).resolve()
require(os.path.ismount('/Volumes/Simo') and root.is_relative_to(Path('/Volumes/Simo')), 'Check failed at original line 27')
require(Path(os.environ['TMPDIR']).resolve() == root/'tmp', 'Check failed at original line 28')
site = args.url.rstrip('/')
u = urlsplit(site)
require(u.scheme == 'https' and not u.username and not u.password, 'Check failed at original line 31')
require(all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(u.hostname,u.port or 443)), 'Check failed at original line 32')
os.umask(0o077)
lock = (root/'tmp/browser.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
run = root/'artifacts'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-navigation'+('-baseline' if args.baseline else ''))
run.mkdir(mode=0o700)
profile_js_initial = profile_scripting_state()
(run / 'original-profile-javascript.json').write_text(json.dumps(profile_js_initial, indent=2))
wp = ['wp','--path='+str(Path(args.wp_path).resolve())]
def cli(code):
    return subprocess.run(wp+['eval',code],capture_output=True,text=True,check=True,timeout=60).stdout.strip()
def php_json(data):
    return "json_decode('"+json.dumps(data).replace('\\','\\\\').replace("'","\\'")+"',true)"
require(cli("echo get_stylesheet();")=='githeme', 'Check failed at original line 43')
snapshot = snapshot_options(['theme_mods_githeme', 'nav_menu_options'])
# Check all pre-existing posts/menus, their metadata, relationships and relevant options.
guard_code="global $wpdb;echo hash('sha256',serialize(array($wpdb->get_results('SELECT * FROM '.$wpdb->posts.' ORDER BY ID',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->postmeta.' ORDER BY meta_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->terms.' ORDER BY term_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->term_taxonomy.' ORDER BY term_taxonomy_id',ARRAY_A),$wpdb->get_results('SELECT * FROM '.$wpdb->term_relationships.' ORDER BY object_id,term_taxonomy_id',ARRAY_A),get_option('sidebars_widgets'),get_option('show_on_front'),get_option('page_on_front'),get_option('page_for_posts'),get_option('active_plugins'))));"
guard = cli(guard_code)
menus=[];driver=None;service=None;results=[];errors=[];failed=[]
failures=[];fetch_failures=[];navigating=False
logs={p:p.stat().st_size for p in [Path('/Applications/MAMP/logs/php_error.log'),Path('/Applications/MAMP/logs/apache_error.log')] if p.exists()}
def record(name,**values):
    results.append({'test':name,**values});(run/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results[-1]),flush=True)
def assign(menu,layout='inline'):
    cli("$l=get_theme_mod('nav_menu_locations',array());$l['primary']="+str(menu)+";set_theme_mod('nav_menu_locations',$l);set_theme_mod('githeme_header_layout',"+php_json(layout)+");")
def start(javascript=True):
    global driver, service
    options=webdriver.FirefoxOptions();options.binary_location='/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi=True;options.accept_insecure_certs=False
    options.add_argument('-headless');options.add_argument('-profile');options.add_argument(str(root/'profiles/firefox'))
    # Geckodriver restores the original preference when the session quits.
    options.set_preference('javascript.enabled',javascript)
    service=Service(str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(root/'tmp/driver-profiles'),'--log','fatal'],log_output=os.devnull)
    d=webdriver.Firefox(options=options,service=service)
    driver=d
    require(Path(d.capabilities['moz:profile']).resolve()==root/'profiles/firefox', 'Check failed at original line 64')
    d.set_page_load_timeout(30)
    d.network.set_cache_behavior('bypass')
    d.script.add_javascript_error_handler(lambda e:capture_js(e,'uncaught'))
    d.script.add_console_message_handler(lambda e:capture_js(e,'console') if getattr(e,'level',None)=='error' else None)
    def response(e):
        v=event_data(e);status=v.get('response',{}).get('status',0)
        if status>=400:
            x=urlsplit(v.get('request',{}).get('url',''));failed.append({'url':safe_url(v.get('request',{}).get('url','')),'status':status})
    d.network.add_event_handler('response_started',response)
    d.network.add_event_handler('fetch_error',capture_fetch)
    d.network.add_event_handler('response_completed',capture_document)
    return d

def viewport(width):
    driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':1000})
    time.sleep(.15)
def inspect(name,width,expected_links=7,nojs=False):
    viewport(width);navigate(site+'/');time.sleep(.2)
    data=driver.execute_script("""const n=document.querySelector('.primary-navigation'),m=document.getElementById('primary-menu'),t=n?.querySelector('button'),b=document.querySelector('.site-branding'),r=e=>e.getBoundingClientRect();return {width:innerWidth,scroll:document.documentElement.scrollWidth,links:m?.querySelectorAll('a').length||0,toggle:!!t&&!t.hidden,expanded:t?.getAttribute('aria-expanded'),menuHidden:m?.hidden,buttonName:t?.textContent.trim(),controls:t?.getAttribute('aria-controls'),nested:!!m?.querySelector('ul ul'),navTop:n?r(n).top:null,brandingBottom:r(b).bottom,topRows:m?[...m.children].map(e=>r(e).top):[],roles:!!m?.querySelector('[role="menu"]'),oneMenu:document.querySelectorAll('#primary-menu').length};""")
    require(data['width']==width and data['scroll']<=width and data['links']==expected_links, 'Check failed at original line 82')
    require(not data['roles'] and data['oneMenu']==(1 if expected_links else 0), 'Check failed at original line 83')
    if expected_links:
        require(data['controls']=='primary-menu' and data['buttonName'], 'Check failed at original line 85')
        if nojs:require(not data['toggle'] and not data['menuHidden'], 'Check failed at original line 86')
        elif width<=768:require(data['toggle'] and data['menuHidden'] and data['expanded']=='false', 'Check failed at original line 87')
    record(name,**data)
    driver.execute_script("document.getElementById('wpadminbar')?.style.setProperty('visibility','hidden')")
    driver.save_screenshot(str(run/(name+'.png')))
    return data

def keyboard(name):
    toggle=driver.find_element(By.CSS_SELECTOR,'.menu-toggle')
    require(toggle.get_attribute('type')=='button', 'Check failed at original line 95')
    # Tab through actual document: hidden menu links must not be in the tab order.
    driver.execute_script('document.activeElement.blur()')
    for _ in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        active=driver.switch_to.active_element
        require(not driver.execute_script("return !!document.activeElement.closest('#primary-menu')"), 'Check failed at original line 101')
        if active==toggle:break
    else:raise AssertionError('Toggle not reachable')
    require(driver.execute_script("return document.activeElement.matches(':focus-visible')&&getComputedStyle(document.activeElement).outlineStyle!=='none'"), 'Check failed at original line 104')
    toggle.send_keys(Keys.SPACE)
    require(toggle.get_attribute('aria-expanded')=='true', 'Check failed at original line 106')
    require(driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'), 'Check failed at original line 107')
    require(driver.execute_script("return getComputedStyle(document.querySelector('#primary-menu')).flexDirection==='column'"), 'Check failed at original line 108')
    driver.save_screenshot(str(run/(name+'-open.png')))
    links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
    for link in links:
        require(link.is_displayed(), 'Check failed at original line 112')
        driver.switch_to.active_element.send_keys(Keys.TAB)
        require(driver.switch_to.active_element==link, 'Check failed at original line 114')
        require(driver.execute_script("return document.activeElement.matches(':focus-visible')"), 'Check failed at original line 115')
    for link in reversed(links[:-1]):
        driver.switch_to.active_element.send_keys(Keys.SHIFT,Keys.TAB)
        require(driver.switch_to.active_element==link, 'Check failed at original line 118')
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    require(driver.switch_to.active_element==toggle and toggle.get_attribute('aria-expanded')=='false', 'Check failed at original line 120')
    toggle.send_keys(Keys.ENTER);require(toggle.get_attribute('aria-expanded')=='true', 'Check failed at original line 121')
    toggle.click();require(toggle.get_attribute('aria-expanded')=='false', 'Check failed at original line 122')
    toggle.click();require(toggle.get_attribute('aria-expanded')=='true', 'Check failed at original line 123')
    for link in links:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'})",link)
        require(driver.execute_script("const e=arguments[0],r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))",link), 'Link obscured')
        ActionChains(driver).move_to_element(link).perform()
    toggle.click();require(toggle.get_attribute('aria-expanded')=='false', 'Check failed at original line 128')
    record(name,space=True,enter=True,tab_and_shift_tab=True,escape=True,hidden_links_skipped=True,focus_visible=True)
def dynamic_header():
    viewport(1440);navigate(site+'/')
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
    require(loaded=='loaded', 'Check failed at original line 175')
    check('dynamic-local-font-loaded',False)
    driver.execute_script("document.documentElement.style.removeProperty('--font-body')")
    check('dynamic-local-font-reset',False)
    navigate(site+'/')
    require(not failures, 'Dynamic header checks failed: '+', '.join(failures))

try:
    for flat in [False,True]:
        labels=['Home','Servizi','Una etichetta lunga per informazioni approfondite e risorse del sito','Contatti','Articoli']
        if not flat:labels+=['Dettagli','Approfondimenti']
        # Only these newly created menu objects are removed at exit.
        code="$m=wp_create_nav_menu('githeme-test-navigation-"+run.name+('-flat' if flat else '-nested')+"');if(is_wp_error($m)){throw new Exception('Menu creation failed');}try{$ids=array();$labels="+php_json(labels)+";$pages=get_posts(array('post_type'=>'page','post_status'=>'publish','numberposts'=>5,'orderby'=>'ID','order'=>'ASC'));if(!$pages){throw new Exception('Existing pages required');}foreach($labels as $i=>$label){$parent=$i===5?$ids[1]:($i===6?$ids[5]:0);$id=wp_update_nav_menu_item($m,0,array('menu-item-title'=>$label,'menu-item-object-id'=>$pages[$i%count($pages)]->ID,'menu-item-object'=>'page','menu-item-type'=>'post_type','menu-item-status'=>'publish','menu-item-parent-id'=>$parent,'menu-item-position'=>$i+1));if(is_wp_error($id)){throw new Exception('Menu item creation failed');}$ids[]=$id;}echo $m;}catch(Throwable $e){wp_delete_nav_menu($m);throw $e;}"
        menus.append(int(cli(code)))
        (run/'temporary-menu-ids.json').write_text(json.dumps(menus))
    driver=start()
    assign(0);inspect('unassigned',390,0)
    assign(menus[0])
    if not args.baseline:
        dynamic_header()
    if not args.baseline:
        viewport(390);navigate(site+'/');time.sleep(.2)
        driver.find_element(By.CSS_SELECTOR,'.menu-toggle').click()
        viewport(375)
        require(driver.execute_script("return document.activeElement.matches('.menu-toggle')"), 'Compact resize lost toggle focus')
        require(driver.find_element(By.CSS_SELECTOR,'.menu-toggle').get_attribute('aria-expanded')=='true', 'Check failed at original line 200')
        record('compact-resize-focus',passed=True,expanded_preserved=True)
    for width in [1440,1024,820,768,390,375,320]:
        data=inspect('nested-'+str(width),width)
        if width in [1024,820] and not args.baseline:
            require(data['toggle'], 'Insufficient space must collapse the navigation')
        if data['toggle']:keyboard('keyboard-'+str(width))
        else:
            links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
            ActionChains(driver).move_to_element(links[1]).perform()
            require(all(link.is_displayed() for link in links), 'Check failed at original line 210')
            links[0].send_keys(Keys.TAB)
            for link in links[2:]:
                driver.switch_to.active_element.send_keys(Keys.TAB);require(driver.switch_to.active_element==link, 'Check failed at original line 213')
            record('desktop-mouse-keyboard-'+str(width),all_nested_links_visible=True)
    # Skip link remains the first frontend tab stop after the authenticated toolbar.
    navigate(site+'/')
    for _ in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        if driver.execute_script("return document.activeElement.matches('.skip-link')"):break
    else:raise AssertionError('Skip link not found')
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    require(driver.execute_script("return document.activeElement.id==='main-content'"), 'Check failed at original line 222')
    record('skip-link',passed=True)
    assign(menus[1]);inspect('flat-desktop',1440,5);inspect('flat-mobile',375,5);keyboard('flat-keyboard')
    assign(menus[0],'stacked');inspect('stacked-desktop',1440);inspect('stacked-mobile',390);keyboard('stacked-keyboard')
    # Crossing the breakpoint must never strand focus inside a hidden subtree.
    viewport(1440);navigate(site+'/');driver.find_element(By.CSS_SELECTOR,'#primary-menu a').send_keys(Keys.TAB)
    viewport(320)
    require(driver.execute_script("return document.activeElement.matches('.menu-toggle')"), 'Check failed at original line 229')
    viewport(1440)
    require(driver.execute_script("return document.activeElement.matches('#primary-menu a')"), 'Check failed at original line 231')
    record('resize-focus',passed=True)
    driver.quit();driver=None
    assign(menus[0])
    driver=start(False)
    # Marionette execute_script remains usable even when page scripts are disabled.
    for width in [1440,820,390,375,320]:
        inspect('no-js-'+str(width),width,nojs=True)
        links=driver.find_elements(By.CSS_SELECTOR,'#primary-menu a')
        require(all(link.is_displayed() for link in links), 'Check failed at original line 241')
        links[0].send_keys(Keys.TAB)
        for link in links[2:]:
            driver.switch_to.active_element.send_keys(Keys.TAB);require(driver.switch_to.active_element==link, 'Check failed at original line 244')
    record('no-js-keyboard',passed=True)
except Exception as exc:
    failures.append(error_info('functional', exc))
finally:
    if driver is not None:
        attempt('browser-quit', driver.quit, failures)
    if service is not None:
        attempt('driver-stop', service.stop, failures)
    for menu in menus:
        attempt('delete-test-menu-' + str(menu), lambda menu=menu: require(
            cli("$m=wp_get_nav_menu_object("+str(menu)+");if($m){$r=wp_delete_nav_menu($m);if(is_wp_error($r)||!$r){throw new Exception('Menu cleanup failed');}}echo 'OK';") == 'OK',
            'Menu cleanup failed'), failures)
    for name, saved in snapshot.items():
        attempt('restore-option-' + name, lambda name=name, saved=saved: restore_option(name, saved), failures)
    exact = attempt('verify-options', lambda: verify_options(snapshot), failures)
    unchanged = attempt('verify-existing-data', lambda: require(cli(guard_code) == guard, 'Preexisting data changed'), failures)
    attempt('record-restoration', lambda: record('restoration', exact=exact, preexisting_data_unchanged=unchanged,
        cleanup_errors=[f['phase'] for f in failures if f['phase'] != 'functional']), failures)
    attempt('restore-profile-javascript', lambda: restore_profile_scripting(failures), failures)
    attempt('verify-profile-javascript', lambda: require(profile_scripting_state() == profile_js_initial, 'Profile JavaScript preference was not restored'), failures)
    finish_report(failures, errors, failed, fetch_failures, logs)
