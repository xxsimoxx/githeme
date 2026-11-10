"""Read-only footer regression: real pages plus exported native-widget fixtures.
Source the Simo env.sh, export tests/footer.php json to artifacts, then pass its path.
"""
import argparse
import dataclasses
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('fixtures', type=Path)
args = parser.parse_args()
root = Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != root / 'tmp':
    raise SystemExit('Source the existing Simo environment; no fallback.')
if not args.fixtures.resolve().is_relative_to(root / 'artifacts'):
    raise SystemExit('Artifacts must remain on Simo.')
run = args.fixtures.resolve().parent
fixtures = json.loads(args.fixtures.read_text())['fixtures']
checks, samples, errors, network = [], [], [], []

def check(ok, name, state=None):
    checks.append({'name': name, 'ok': bool(ok), 'details': state})

def event(e, kind):
    value = e if isinstance(e, dict) else dataclasses.asdict(e)
    request, response = value.get('request', {}), value.get('response', {})
    url = urlsplit(request.get('url', ''))
    if url.scheme in ('http', 'https'):
        network.append({'kind': kind, 'url': url.scheme + '://' + url.netloc + url.path,
                        'status': response.get('status'), 'error': value.get('errorText')})

profile = tempfile.TemporaryDirectory(prefix='footer-anonymous-', dir=root / 'tmp')
driver = None
try:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.add_argument('-headless')
    options.add_argument('-no-remote')
    options.add_argument('-profile')
    options.add_argument(profile.name)
    options.enable_bidi = True
    options.accept_insecure_certs = False
    options.set_preference('browser.cache.disk.enable', False)
    service = Service(str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=str(run / 'footer-driver.log'), env=os.environ.copy())
    driver = webdriver.Firefox(options=options, service=service)
    driver.set_page_load_timeout(30)
    driver.script.add_javascript_error_handler(lambda e: errors.append(str(getattr(e, 'text', e))))
    driver.network.add_event_handler('response_completed', lambda e: event(e, 'response'))
    driver.network.add_event_handler('fetch_error', lambda e: event(e, 'fetch_error'))
    for width in (1440, 768, 390, 320):
        driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
        cases = [('real-short', 'https://githeme:8890/?page_id=494'), ('real-long', 'https://githeme:8890/?p=257')]
        for label, sidebar, long, footer, admin in [
            ('fixture-short', False, False, True, False), ('fixture-long', False, True, True, False),
            ('fixture-sidebar', True, False, True, False), ('fixture-no-footer', False, False, False, False),
            ('fixture-adminbar', False, False, True, True)]:
            bar = 46 if width <= 782 else 32
            extra = 'html{margin-top:%dpx;--wp-admin--admin-bar--height:%dpx}' % (bar, bar) if admin else ''
            content = '<p>Short content.</p>' if not long else '<p>Long content.</p>' * 150
            if sidebar:
                content = '<div style="display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:1rem"><article>' + content + '</article><aside aria-label="Fixture sidebar">Sidebar</aside></div>'
            doc = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Footer fixture</title><style>' + fixtures['css'] + extra + '</style><body' + (' class="admin-bar"' if admin else '') + '><header class="site-header"><div class="site-container">Header fixture</div></header><main id="main-content" class="site-main site-container">' + content + '</main>' + (fixtures['footer'] if footer else '') + '</body></html>'
            path = run / (label + '.html')
            path.write_text(doc)
            cases.append((label, path.as_uri()))
        for label, url in cases:
            driver.get(url)
            time.sleep(.6)
            state = driver.execute_script('''
                const m=document.querySelector('main'),f=document.querySelector('.site-footer');
                const rect=e=>e?{top:e.getBoundingClientRect().top+scrollY,bottom:e.getBoundingClientRect().bottom+scrollY}:null;
                return {width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,
                docHeight:document.documentElement.scrollHeight,main:rect(m),footer:rect(f),
                footerPosition:f?getComputedStyle(f).position:null,credits:!!document.querySelector('.site-credits'),
                mains:document.querySelectorAll('main').length,title:document.title,body:document.body.className};
            ''')
            samples.append({'case': label, 'requestedWidth': width, **state})
            check(state['width'] == width and state['scroll'] <= width, 'Exact viewport/no horizontal overflow ' + label + '/' + str(width), state)
            check(state['mains'] == 1 and not state['credits'], 'Single main/no automatic credits ' + label + '/' + str(width))
            if label.startswith('real'):
                check('error404' not in state['body'] and state['main'] is not None, 'Real CMS page rendered ' + label + '/' + str(width))
            if state['footer']:
                check(state['footerPosition'] not in ('fixed', 'sticky') and state['footer']['top'] >= state['main']['bottom'] - 1, 'Footer follows main in flow ' + label + '/' + str(width))
                if label in ('fixture-short', 'fixture-sidebar', 'fixture-adminbar'):
                    check(abs(state['footer']['bottom'] - state['height']) <= 1 and state['docHeight'] <= state['height'] + 1, 'Short footer at viewport bottom ' + label + '/' + str(width), state)
                if label == 'fixture-long':
                    check(state['footer']['bottom'] > state['height'] and abs(state['footer']['bottom'] - state['docHeight']) <= 1, 'Long footer after content ' + str(width), state)
                if label == 'fixture-short':
                    link = driver.find_element(By.CSS_SELECTOR, '.footer-widgets a')
                    driver.find_element(By.TAG_NAME, 'body').click()
                    webdriver.ActionChains(driver).send_keys(Keys.TAB).perform()
                    check(driver.execute_script('return document.activeElement===arguments[0]&&getComputedStyle(arguments[0]).outlineStyle!=="none"', link), 'Footer link keyboard focus visible ' + str(width))
            else:
                check(state['main']['bottom'] >= state['height'] - 1, 'Main fills viewport without footer ' + label + '/' + str(width), state)
            if width in (1440, 320) and label in ('real-short', 'real-long', 'fixture-short', 'fixture-sidebar'):
                driver.save_screenshot(str(run / (label + '-' + str(width) + '.png')))
    check(not errors, 'No JavaScript errors', errors)
    failures = [e for e in network if e['kind'] == 'fetch_error' or (e.get('status', 0) >= 400 and not (e['url'] == 'https://githeme:8890/favicon.ico' and e['status'] == 404))]
    check(not failures, 'No unexpected failed HTTP requests', failures)
finally:
    try:
        if driver:
            driver.quit()
    finally:
        profile.cleanup()
        (run / 'browser-report.json').write_text(json.dumps({'checks': checks, 'samples': samples, 'javascriptErrors': errors, 'network': network}, indent=2))
failed = [c for c in checks if not c['ok']]
print(json.dumps({'checks': len(checks), 'failed': failed, 'artifacts': str(run)}, indent=2))
if failed:
    raise SystemExit(1)
