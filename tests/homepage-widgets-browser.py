"""Local frontend integration tests; existing published fixtures only.
Source the external browser tools env.sh. All modified options are snapshotted,
including raw values, autoload flags, types and absence, and restored in finally.
"""
import argparse
import dataclasses
import hashlib
import re
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
parser.add_argument('--front-page-id', required=True, type=int)
parser.add_argument('--posts-page-id', required=True, type=int)
parser.add_argument('--internal-page-id', required=True, type=int)
parser.add_argument('--post-id', required=True, type=int)
parser.add_argument('--fx-content-id', type=int)
parser.add_argument('--fx-page-id', type=int)
args = parser.parse_args()
root = Path(os.environ['CODEX_BROWSER_ROOT']).resolve()
require(os.path.ismount('/Volumes/Simo') and root.is_relative_to(Path('/Volumes/Simo')), 'Check failed at original line 32')
require(Path(os.environ['TMPDIR']).resolve() == root / 'tmp', 'Check failed at original line 33')
site = args.url.rstrip('/')
u = urlsplit(site)
require(u.scheme == 'https' and not u.username and not u.password, 'Check failed at original line 36')
require(all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(u.hostname, u.port or 443)), 'Check failed at original line 37')
os.umask(0o077)
lock = (root / 'tmp/browser.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
run = root / 'artifacts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-homepage-widgets')
run.mkdir(mode=0o700)
profile_js_initial = profile_scripting_state()
(run / 'original-profile-javascript.json').write_text(json.dumps(profile_js_initial, indent=2))
wp = ['wp', '--path=' + str(Path(args.wp_path).resolve())]

def cli(code):
    return subprocess.run(wp + ['eval', code], capture_output=True, text=True, check=True, timeout=60).stdout.strip()

def php_json(data):
    # Quoted PHP literal, never shell-interpolated. Values contain no credentials.
    return "json_decode('" + json.dumps(data).replace('\\', '\\\\').replace("'", "\\'") + "',true)"

ids = [args.front_page_id, args.posts_page_id, args.internal_page_id, args.post_id]
ids += [i for i in [args.fx_content_id, args.fx_page_id] if i]
require(len({args.front_page_id,args.posts_page_id,args.internal_page_id}) == 3, 'Check failed at original line 54')
preconditions = cli("$ids=" + php_json(ids) + ";foreach($ids as $id){$p=get_post($id);if(!$p||$p->post_status!=='publish'||$p->post_password!==''){throw new Exception('Use existing public fixtures only');}}if(get_option('stylesheet')!=='githeme'){throw new Exception('Wrong active theme');}echo 'OK';")
option_names = ['show_on_front','page_on_front','page_for_posts','sidebars_widgets','widget_custom_html','theme_mods_githeme']
if args.fx_content_id: option_names.append('widget_fx_builder_widgets')
# Read the database representation and the public API representation before writes.
snapshot = snapshot_options(option_names)
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
failures=[];fetch_failures=[];navigating=False

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
    data = event_data(event)
    req = data.get('request',{}); resp = data.get('response',{})
    url = urlsplit(req.get('url','')); status = resp.get('status',0)
    item={'url':safe_url(req.get('url','')),'status':status}
    if status>=400:failed_http.append(item)
    if data.get('context')==top and data.get('navigation') is not None:documents.append(item)

def inspect(name,url,hero,content,screenshot=False):
    count=len(documents);navigate(url)
    driver.execute_async_script('document.fonts.ready.then(arguments[0])')
    require(len(documents)>count and documents[-1]['status']==200, 'No successful document response')
    require(not any(s in driver.page_source for s in ['Fatal error:', 'PHP Warning:', 'PHP Deprecated:']), 'Check failed at original line 111')
    data=driver.execute_script("""const m=document.querySelector('main'),h=document.getElementById('homepage-hero'),c=document.getElementById('homepage-content'),a=m?.querySelector('article.entry'),r=getComputedStyle(document.documentElement);
    return {mainCount:document.querySelectorAll('main').length,h1:m?.querySelectorAll('h1').length,hero:!!h,content:!!c,
    heroBeforePage:!!(h&&a&&(h.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_FOLLOWING)),contentAfterPage:!!(c&&a&&(a.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)),
    emptyAreas:[...document.querySelectorAll('.homepage-widget-area')].filter(e=>!e.innerHTML.trim()).length,
    skip:document.querySelector('.skip-link')?.getAttribute('href'),target:!!document.getElementById('main-content'),
    width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,heroWidth:h?.getBoundingClientRect().width,
    pageWidth:a?.getBoundingClientRect().width,mainClasses:m?.className,
    vars:Object.fromEntries(['--width-content','--width-wide','--width-layout','--font-body','--font-size-base','--color-text','--color-background'].map(k=>[k,r.getPropertyValue(k)]))};""")
    require(data['mainCount']==1 and data['h1']==1 and (hero is None or data['hero']==hero) and (content is None or data['content']==content), 'Check failed at original line 120')
    require(data['skip']=='#main-content' and data['target'] and data['emptyAreas']==0, 'Check failed at original line 121')
    if hero:require(data['heroBeforePage'] and abs(data['heroWidth']-data['width'])<1, 'Check failed at original line 122')
    if content:require(data['contentAfterPage'], 'Check failed at original line 123')
    require(data['scroll']<=data['width'], 'Horizontal overflow')
    if baseline_vars:require(data['vars']==baseline_vars, 'Existing theme settings changed')
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
    options.set_preference('javascript.enabled', True)
    options.add_argument('-headless');options.add_argument('-profile');options.add_argument(str(root/'profiles/firefox'))
    options.set_preference('browser.cache.disk.parent_directory',str(root/'cache/firefox'))
    service=Service(executable_path=str(root/'drivers/geckodriver'),service_args=['--host','127.0.0.1','--profile-root',str(root/'tmp/driver-profiles'),'--log','fatal'],log_output=os.devnull,env=os.environ.copy())
    driver=webdriver.Firefox(options=options,service=service)
    require(Path(driver.capabilities['moz:profile']).resolve()==root/'profiles/firefox', 'Check failed at original line 144')
    driver.set_page_load_timeout(30);top=driver.current_window_handle
    driver.network.set_cache_behavior('bypass')
    driver.network.add_event_handler('response_started',response)
    driver.network.add_event_handler('fetch_error',capture_fetch)
    driver.network.add_event_handler('response_completed',capture_document)
    driver.script.add_javascript_error_handler(lambda e:capture_js(e,'uncaught'))
    driver.script.add_console_message_handler(lambda e:capture_js(e,'console') if getattr(e,'level',None)=='error' else None)
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
        require(data['width']==width and data['height']==900, 'Check failed at original line 163')
    driver.browsing_context.set_viewport(context=top,viewport={'width':1440,'height':1000})
    navigate(site+'/')
    found=False
    for i in range(80):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        if driver.execute_script("return document.activeElement.matches('a.skip-link')"):
            found=True;break
    require(found, 'Skip link not keyboard reachable')
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    require(driver.execute_script("return document.activeElement.id==='main-content'"), 'Check failed at original line 173')
    link=driver.find_element(By.CSS_SELECTOR,'#homepage-hero a');link.send_keys(Keys.TAB)
    focused=driver.execute_script("const e=document.activeElement;return {focusVisible:e.matches(':focus-visible'),outline:getComputedStyle(e).outline,tag:e.tagName}")
    require(focused['focusVisible'], 'Check failed at original line 176')
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
        require('githeme-test-nested-content' in rendered and 'githeme-test-ordinary-content' in rendered, 'Check failed at original line 187')
        require('[element' not in rendered and '[caption' not in rendered, 'Check failed at original line 188')
        record('fx-parsing',nested_elements=True,ordinary_shortcode=True)
        for width in [390,375,320]:
            driver.browsing_context.set_viewport(context=top,viewport={'width':width,'height':900})
            inspect('fx-mobile-'+str(width),site+'/',True,True,screenshot=True)
    if args.fx_page_id:
        configure(front=args.fx_page_id)
        inspect('fx-static-page',site+'/',True,True)
        require('githeme-test-fx-content' in driver.find_element(By.CSS_SELECTOR,'main').text, 'Check failed at original line 196')
        record('fx-page-editor-content',present=True)
except Exception as exc:
    failures.append(error_info('functional', exc))
finally:
    # Each operation is independent: even a dead browser cannot skip the DB.
    if driver is not None:
        attempt('browser-blank', lambda: navigate('about:blank'), failures)
    for name, saved in snapshot.items():
        attempt('restore-option-' + name, lambda name=name, saved=saved: restore_option(name, saved), failures)
    exact = attempt('verify-options', lambda: verify_options(snapshot), failures)
    unchanged = attempt('verify-existing-data', lambda: require(cli(guard_code) == guard_hash, 'Editorial fixtures or activation changed'), failures)
    attempt('record-restoration', lambda: record('restoration', exact=exact, editorial_and_plugins_unchanged=unchanged, options=option_names), failures)
    if exact and driver is not None and original_state is not None:
        def restored_frontend():
            driver.browsing_context.set_viewport(context=top,viewport={'width':1440,'height':1000})
            inspect('restored-homepage',site+'/',original_state['hero'],original_state['content'])
        attempt('restored-frontend', restored_frontend, failures)
    if driver is not None:
        attempt('browser-quit', driver.quit, failures)
    if service is not None:
        attempt('driver-stop', service.stop, failures)
    attempt('restore-profile-javascript', lambda: restore_profile_scripting(failures), failures)
    attempt('verify-profile-javascript', lambda: require(profile_scripting_state() == profile_js_initial, 'Profile JavaScript preference was not restored'), failures)
    finish_report(failures, errors, failed_http, fetch_failures, log_offsets)
