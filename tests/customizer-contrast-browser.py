"""Authenticated, local-only Selenium test. Source the external tools env.sh first.
No content writes, cookie export, credentials, personal profile or global config.
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
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--wp-path', required=True)
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
run = root / 'artifacts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-live-contrast')
run.mkdir(mode=0o700)
wp = ['wp', '--path=' + str(Path(args.wp_path).resolve())]

def cli(code):
    return subprocess.run(wp + ['eval', code], capture_output=True, text=True, check=True).stdout.strip()

initial = cli("if(get_option('stylesheet')!=='githeme'){throw new Exception('Wrong active theme');}$v=get_option('theme_mods_githeme');$s=serialize($v);if(unserialize($s,array('allowed_classes'=>false))!==$v){throw new Exception('Snapshot invalid');}echo base64_encode($s);")
(run / 'initial-theme-mods.base64').write_text(initial)
results = []
errors = []
http_failures = []
driver = None

def record(test, **data):
    results.append({'test': test, **data})
    (run / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results[-1]), flush=True)

def field(key):
    return driver.find_element(By.CSS_SELECTOR, 'input[data-githeme-color="' + key + '"]')

def change(key, value):
    element = field(key)
    element.send_keys(Keys.COMMAND, 'a')
    element.send_keys(value)
    # No blur is needed for live advice; keep the focus to verify no focus theft.

def state():
    return driver.execute_script("return [...document.querySelectorAll('[data-githeme-contrast-row]')].map(e=>({key:e.dataset.githemeContrastRow,status:e.dataset.status,ratio:e.querySelector('[data-githeme-ratio]').textContent,pair:e.querySelector('[data-githeme-pair]').textContent}))")

def open_colors():
    driver.get(site + '/wp-admin/customize.php')
    driver.find_element(By.CSS_SELECTOR, '#accordion-section-colors a').click()
    WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, 'githeme-contrast-panel').get_attribute('data-githeme-enhanced') == 'true')

def response(event):
    import dataclasses
    data = event if isinstance(event, dict) else dataclasses.asdict(event)
    url = urlsplit(data.get('request', {}).get('url', ''))
    status = data.get('response', {}).get('status', 0)
    if status >= 400:
        http_failures.append({'path': url.path, 'status': status})

for name in ['php_error.log', 'apache_error.log']:
    log = Path('/Applications/MAMP/logs') / name
    if log.exists(): (run / (name + '.offset')).write_text(str(log.stat().st_size))
try:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi = True
    options.accept_insecure_certs = False
    options.add_argument('-profile')
    options.add_argument(str(root / 'profiles/firefox'))
    options.set_preference('browser.cache.disk.parent_directory', str(root / 'cache/firefox'))
    service = Service(executable_path=str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=os.devnull, env=os.environ.copy())
    driver = webdriver.Firefox(options=options, service=service)
    assert Path(driver.capabilities['moz:profile']).resolve() == root / 'profiles/firefox'
    assert not driver.capabilities['acceptInsecureCerts']
    listeners = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', ','.join(map(str, [service.process.pid, driver.capabilities['moz:processID']])), '-iTCP', '-sTCP:LISTEN'], capture_output=True, text=True).stdout.splitlines()[1:]
    assert listeners and all('127.0.0.1:' in row or '[::1]:' in row for row in listeners)
    def log_error(entry, kind):
        import re
        message = str(getattr(entry, 'text', ''))
        found = re.search(r'(?:Type|Reference|Syntax|Network|Abort|Range|Security)?Error', message)
        stack = getattr(entry, 'stacktrace', None) or getattr(entry, 'stack_trace', None) or {}
        frames = stack.get('callFrames', []) if isinstance(stack, dict) else []
        errors.append({'kind': kind, 'category': found.group(0) if found else 'unspecified',
                       'network_failure': 'fetch' in message.lower() or 'network' in message.lower(),
                       'dead_object': 'dead object' in message.lower(),
                       'phase': results[-1]['test'] if results else 'initial-load',
                       'frames': [{'path': urlsplit(f.get('url', '')).path, 'function': f.get('functionName'), 'line': f.get('lineNumber')} for f in frames[:5]]})
    driver.script.add_javascript_error_handler(lambda event: log_error(event, 'javascript_error'))
    driver.script.add_console_message_handler(lambda event: log_error(event, 'console_error') if getattr(event, 'level', None) == 'error' else None)
    driver.network.add_event_handler('response_started', response)
    driver.set_window_rect(width=1440, height=1100)
    driver.get(site + '/wp-admin/')
    assert driver.execute_script("return !!document.querySelector('body.wp-admin #adminmenu')")
    open_colors()
    origin = driver.execute_script('return performance.timeOrigin')
    assert driver.find_element(By.CSS_SELECTOR, '[data-githeme-live]').get_attribute('textContent') == ''
    record('initial-panel',rows=state(),api_type=driver.execute_script('return typeof wp.customize'))
    # Parse a fresh server response without executing its scripts: PHP fallback.
    fallback = driver.execute_async_script("const done=arguments[0];fetch(location.href).then(r=>r.text()).then(html=>{const d=new DOMParser().parseFromString(html,'text/html'),p=d.querySelector('#githeme-contrast-panel');done({rows:p.querySelectorAll('[data-githeme-contrast-row]').length,help:p.querySelector('[data-githeme-update-help]').textContent,live:p.querySelector('[data-githeme-live]').textContent});}).catch(()=>done(null));")
    assert fallback and fallback['rows'] == 3 and fallback['live'] == ''
    record('server-fallback',**fallback)
    for background, text, expected in [('#ffffff','#eaf5af','fail'),('#ffffff','#000000','pass'),('#000000','#000000','fail'),('#000000','#ffffff','pass')]:
        change('background', background)
        change('text', text)
        rows = state()
        assert rows[0]['status'] == expected
        assert driver.execute_script('return document.activeElement === arguments[0]', field('text'))
        assert driver.execute_script('return performance.timeOrigin') == origin
        record('live-text',text=text,background=background,rows=rows,focus_retained=True,no_reload=True)
    change('link','#000000')
    assert state()[1]['status'] == 'fail'
    change('link','#ffffff')
    assert state()[1]['status'] == 'pass'
    for primary, foreground in [('#ffffff','#000000'),('#000000','#ffffff')]:
        change('primary',primary)
        rows=state()
        assert rows[2]['status']=='pass' and foreground in rows[2]['pair']
        record('automatic-button',primary=primary,rows=rows)
    # Typing an invalid value does not substitute a guessed contrast or NaN.
    change('text','#zzzzzz')
    assert state()[0]['status']=='invalid'
    record('invalid-input',rows=state())
    change('background','#ffffff');change('link','#14569a');change('primary','#14569a');change('text','#202833')
    time.sleep(1)
    # Observe only the theme live region, never user data or the core proxy.
    driver.execute_script("window.githemeAnnouncements=[];window.githemeObserver=new MutationObserver(()=>{githemeAnnouncements.push(document.querySelector('[data-githeme-live]').textContent);});githemeObserver.observe(document.querySelector('[data-githeme-live]'),{childList:true,subtree:true,characterData:true});")
    driver.execute_async_script("const input=arguments[0],done=arguments[1];let i=0;const timer=setInterval(()=>{input.value='#'+(0x202833+i*0x030301).toString(16).padStart(6,'0');input.dispatchEvent(new Event('input',{bubbles:true}));i++;if(i===20){clearInterval(timer);done();}},30);",field('text'))
    time.sleep(1)
    announcements=driver.execute_script('return githemeAnnouncements.slice()')
    assert len(announcements)==1
    driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",field('text'))
    time.sleep(0.9)
    assert driver.execute_script('return githemeAnnouncements.length')==1
    record('announcement-debounce',input_events=20,live_mutations=len(announcements),duplicate_change_announced=False,messages=announcements)
    driver.execute_script('githemeObserver.disconnect()')
    # Real picker interaction via its accessible hue slider (test-only locator).
    field('text').click()
    time.sleep(0.4)  # Let the native picker opening transition finish.
    sliders=driver.find_elements(By.CSS_SELECTOR,'input[aria-label="Hue slider"]')
    # The range is intentionally transparent; keyboard focusability is distinct
    # from Selenium's opacity-based is_displayed() result.
    if sliders and sliders[0].is_enabled() and driver.execute_script('return arguments[0].getBoundingClientRect().height > 0', sliders[0]):
        before=field('text').get_attribute('value')
        sliders[0].send_keys(*([Keys.ARROW_RIGHT] * 12))
        time.sleep(0.1)
        after=field('text').get_attribute('value')
        check=driver.execute_script("const c=githemeCreateContrast(githemeContrastConfig.rules);const r=c.ratio(arguments[0],arguments[1]);return {status:r===null?'invalid':(r>=githemeContrastConfig.rules.normalTextMinimum?'pass':'fail')};",after,field('background').get_attribute('value'))
        assert after != before, 'Picker keyboard did not change the selected color'
        assert state()[0]['status']==check['status'] and after in state()[0]['pair']
        record('picker-hue-keyboard',before=before,after=after,rows=state())
        sliders[0].send_keys(Keys.ESCAPE)
    else:
        record('picker-hue-keyboard',not_executed=True,reason='Picker slider has no interactive geometry',sliders_found=len(sliders))
    # Keyboard navigation from the owned input remains usable and visibly focused.
    element=field('text');element.click();element.send_keys(Keys.TAB)
    keyboard=driver.execute_script("const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,outline:s.outline,shadow:s.boxShadow,focusVisible:e.matches(':focus-visible'),inBody:e===document.body}")
    assert not keyboard['inBody'] and keyboard['focusVisible']
    record('keyboard',**keyboard)
    # Low contrast stays publishable; verify preview, reload and persisted frontend.
    open_colors();change('background','#ffffff');change('text','#eaf5af');time.sleep(2)
    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR,'#customize-preview iframe'))
    preview_color=driver.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--color-text')")
    driver.switch_to.default_content()
    assert preview_color=='#eaf5af'
    panel=driver.find_element(By.ID,'githeme-contrast-panel')
    panel.screenshot(str(run/'contrast-panel.png'))
    driver.find_element(By.ID,'save').click()
    WebDriverWait(driver,20).until(lambda d:not d.find_element(By.ID,'save').is_enabled())
    open_colors()
    assert field('text').get_attribute('value')=='#eaf5af' and state()[0]['status']=='fail'
    driver.get(site+'/')
    frontend_color=driver.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--color-text')")
    assert frontend_color=='#eaf5af'
    record('publish-persist',preview=preview_color,frontend=frontend_color,reloaded='#eaf5af',low_contrast_did_not_block=True)
finally:
    try:
        if driver is not None: driver.get('about:blank')
        restored=cli("$s=base64_decode('"+initial+"',true);$v=unserialize($s,array('allowed_classes'=>false));update_option('theme_mods_githeme',$v);if(get_option('theme_mods_githeme')!==$v||serialize(get_option('theme_mods_githeme'))!==$s){throw new Exception('RESTORATION FAILED');}echo 'EXACT';")
        record('restoration',exact=restored=='EXACT')
    finally:
        if driver is not None: driver.quit()
        (run/'diagnostics.json').write_text(json.dumps({'errors':errors,'failed_http':http_failures},indent=2))
        fcntl.flock(lock,fcntl.LOCK_UN)
        print('EVIDENCE '+str(run),flush=True)
