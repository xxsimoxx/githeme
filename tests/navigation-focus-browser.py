"""Firefox focus regression fixtures, using actual theme CSS/JS and PHP-generated colors.
Usage: python navigation-focus-browser.py PHP_JSON ARTIFACT_DIRECTORY
No production requests, settings writes or new dependencies.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

root = Path(os.environ['CODEX_BROWSER_ROOT'])
theme = Path(__file__).resolve().parents[1]
data = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
profile = root / 'profiles/firefox'
lock = (root / 'tmp/browser.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
user_file = profile / 'user.js'
original_user = user_file.read_bytes() if user_file.exists() else None
original_prefs = (profile / 'prefs.js').read_text()
match = re.search(r'user_pref\("javascript.enabled", (true|false)\);', original_prefs)
original_js = match.group(1) if match else None
report = {'checks': 0, 'cases': []}
driver = None

def check(condition, message):
    if not condition:
        raise AssertionError(message)
    report['checks'] += 1

def ratio(first, second):
    def luminance(channels):
        values = [c / 255 for c in channels[:3]]
        values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(values, [.2126, .7152, .0722]))
    a, b = luminance(first), luminance(second)
    return (max(a, b) + .05) / (min(a, b) + .05)

try:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.accept_insecure_certs = False
    options.enable_bidi = True
    options.add_argument('-headless')
    options.add_argument('-profile'); options.add_argument(str(profile))
    options.set_preference('javascript.enabled', True)
    service = Service(executable_path=str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=os.devnull)
    driver = webdriver.Firefox(options=options, service=service)
    for index, fixture in enumerate(data['fixtures']):
        html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>Navigation focus fixture</title><style>''' + (theme / 'style.css').read_text() + fixture['css'] + '''</style>
<body><header class="site-header"><div class="site-container header-inner"><div class="site-branding"><p class="site-title"><a href="#home">Theme</a></p></div>
<nav class="primary-navigation" aria-label="Primary menu"><button class="menu-toggle" type="button" aria-expanded="false" aria-controls="primary-menu" hidden>Menu</button>
<ul id="primary-menu" class="primary-menu"><li><a id="first" href="#one">First</a></li><li class="menu-item-has-children"><a id="parent" href="#two">Parent</a><ul class="sub-menu"><li><a id="child" href="#three">Child</a></li></ul></li><li><a href="#four">Last</a></li></ul></nav></div></header>
<main id="main-content" tabindex="-1"><h1>Focus checks</h1></main><script>''' + (theme / 'assets/js/navigation.js').read_text() + '</script></body></html>'
        path = out / f'fixture-{index}.html'; path.write_text(html)
        for width in (1440, 390):
            driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
            driver.get(path.as_uri())
            toggle = driver.find_element(By.CSS_SELECTOR, '.menu-toggle')
            compact = toggle.is_displayed()
            if compact:
                toggle.send_keys(Keys.ENTER, Keys.TAB)
            else:
                driver.find_element(By.CSS_SELECTOR, '.site-title a').send_keys(Keys.TAB)
            result = {'name': fixture['name'], 'width': width, 'states': []}
            for expected_id in ('first', 'parent', 'child'):
                active = driver.switch_to.active_element
                check(active.get_attribute('id') == expected_id, 'Native Tab order: ' + expected_id)
                state = driver.execute_script('''const e=document.activeElement,s=getComputedStyle(e),canvas=document.createElement('canvas'),c=canvas.getContext('2d');function rgb(v){c.clearRect(0,0,1,1);c.fillStyle=v;c.fillRect(0,0,1,1);return [...c.getImageData(0,0,1,1).data];} const surface=e.id==='child'&&!arguments[0]?getComputedStyle(e.closest('ul')).backgroundColor:getComputedStyle(document.querySelector('.site-header')).backgroundColor;return {id:e.id,outline:rgb(s.outlineColor),background:rgb(surface),focusVisible:e.matches(':focus-visible'),outlineWidth:parseFloat(s.outlineWidth),offset:s.outlineOffset,hoverBackground:rgb(s.backgroundColor),expectedHoverBackground:rgb(getComputedStyle(document.documentElement).getPropertyValue('--color-surface')),pageOverflow:document.documentElement.scrollWidth>innerWidth};''', compact)
                state['ratio'] = ratio(state['outline'], state['background'])
                check(state['ratio'] >= 3, fixture['name'] + '/' + expected_id + '/contrast')
                check(state['focusVisible'] and state['outlineWidth'] == 3 and state['offset'] == '2px', 'Focus stays visible and unchanged in size')
                check(state['hoverBackground'] == state['expectedHoverBackground'], 'Existing hover/focus fill preserved')
                check(not state['pageOverflow'], 'No page overflow')
                result['states'].append(state)
                if expected_id != 'child':
                    active.send_keys(Keys.TAB)
            if index < 4:
                driver.save_screenshot(str(out / f'palette-{index}-{width}.png'))
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            if compact:
                check(toggle.get_attribute('aria-expanded') == 'false', 'Escape closes compact menu')
                check(driver.switch_to.active_element == toggle, 'Escape restores toggle focus')
            else:
                check(driver.find_element(By.ID, 'child').is_displayed() is False, 'Escape dismisses dropdown')
            report['cases'].append(result)
    report['status'] = 'passed'
finally:
    if driver:
        driver.quit()
    if original_user is None:
        if user_file.exists(): user_file.unlink()
    else:
        user_file.write_bytes(original_user)
    prefs = (profile / 'prefs.js').read_text()
    prefs = re.sub(r'user_pref\("javascript.enabled", (true|false)\);', 'user_pref("javascript.enabled", ' + original_js + ');' if original_js else '', prefs)
    (profile / 'prefs.js').write_text(prefs)
    (out / 'browser-report.json').write_text(json.dumps(report, indent=2))
    fcntl.flock(lock, fcntl.LOCK_UN); lock.close()
    print(json.dumps({'status': report.get('status', 'failed'), 'checks': report['checks'], 'cases': len(report['cases'])}))
