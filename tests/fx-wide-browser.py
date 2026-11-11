"""Read-only Firefox checks: source Simo env.sh, then run with its venv Python."""
import json
import os
from pathlib import Path
import tempfile
from selenium import webdriver
from selenium.webdriver.firefox.service import Service

root = Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != root / 'tmp':
    raise SystemExit('Source the existing Simo environment first.')
run = root / 'artifacts/20261111-fx-wide'
run.mkdir(exist_ok=True)
checks = []
errors = []
measure = '''const root=document.querySelector('.entry-content'), rows=[...root.querySelectorAll(':scope > .fxb-container > .fxb-row')];return {overflow:document.documentElement.scrollWidth>innerWidth, available:root.getBoundingClientRect().width, rows:rows.map(e=>{const r=e.getBoundingClientRect(),w=e.querySelector(':scope > .fxb-wrap'),s=getComputedStyle(w);return {left:r.left,width:r.width,columns:s.gridTemplateColumns.split(' ').length,gap:s.gap,padding:[...e.querySelectorAll('.fxb-col')].map(c=>getComputedStyle(c).padding)}})}'''

def check(ok, label, details=None):
    checks.append({'ok': bool(ok), 'label': label, 'details': details})
    if not ok:
        raise RuntimeError(label)

with tempfile.TemporaryDirectory(dir=root / 'tmp', prefix='fx-wide-anonymous-') as profile:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi = True
    options.accept_insecure_certs = False
    for arg in ('-headless', '-no-remote', '-profile', profile):
        options.add_argument(arg)
    driver = None
    try:
        driver = webdriver.Firefox(options=options, service=Service(str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1'], log_output=str(run / 'driver.log')))
        driver.script.add_javascript_error_handler(lambda e: errors.append(str(getattr(e, 'text', e))))
        for width in (1440, 768, 390, 320):
            driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
            for custom in (False, True):
                driver.get('https://githeme:8890/')
                driver.execute_async_script('document.fonts.ready.then(()=>arguments[0]())')
                if custom:
                    driver.execute_script("document.documentElement.style.setProperty('--width-layout','60rem');document.documentElement.style.setProperty('--width-content','40rem')")
                baseline = driver.execute_script(measure)
                check(len(baseline['rows']) >= 2, 'At least two real Default rows available')
                driver.execute_script("document.querySelector('.entry-content > .fxb-container > .fxb-default').classList.add('githeme-wide')")
                wide = driver.execute_script(measure)
                first = wide['rows'][0]
                check(abs(first['width'] - wide['available']) < 1, 'Wide row uses available configured layout width', {'viewport': width, 'custom': custom, 'before': baseline, 'after': wide})
                check(abs(first['left'] + first['width']/2 - width/2) < 1, 'Wide row centered')
                check(not wide['overflow'], 'No horizontal page overflow')
                check(all(abs(a['left']-b['left'])<1 and abs(a['width']-b['width'])<1 for a,b in zip(baseline['rows'][1:],wide['rows'][1:])), 'Unmarked Default rows unchanged')
                check(all(a['columns']==b['columns'] and a['gap']==b['gap'] and a['padding']==b['padding'] for a,b in zip(baseline['rows'],wide['rows'])), 'Plugin column count, gap and padding unchanged')
                if not custom and width in (1440,320):
                    driver.save_screenshot(str(run / f'wide-{width}.png'))
                # DOM-only Full Width probe: compare the same plugin row with/without the opt-in class.
                driver.execute_script("const r=document.querySelector('.entry-content > .fxb-container > .fxb-default');r.classList.remove('githeme-wide','fxb-default');r.classList.add('fxb-fullwidth')")
                full = driver.execute_script(measure)
                driver.execute_script("document.querySelector('.fxb-fullwidth').classList.add('githeme-wide')")
                ignored = driver.execute_script(measure)
                check(full == ignored, 'Full Width ignores githeme-wide and keeps native geometry')
        driver.get('https://githeme:8890/?p=286')
        check(not driver.find_elements('css selector', '.entry-content > .fxb-container'), 'Ordinary post outside integration selectors')
        check(not driver.execute_script('return document.documentElement.scrollWidth>innerWidth'), 'Ordinary post has no overflow')
        check(not errors, 'No JavaScript errors', errors)
    except Exception as exc:
        checks.append({'ok':False,'label':'Exception','details':str(exc)})
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as exc:
                checks.append({'ok':False,'label':'Browser cleanup','details':str(exc)})
        (run / 'report.json').write_text(json.dumps(checks, indent=2))
failed = [c for c in checks if not c['ok']]
print(json.dumps({'checks':len(checks),'failed':failed,'artifacts':str(run)},indent=2))
raise SystemExit(bool(failed))
