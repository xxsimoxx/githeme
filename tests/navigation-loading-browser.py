"""Read-only Firefox regression for navigation before delayed JavaScript loads.

Source Simo's env.sh. A loopback-only fixture server replays the existing local
header in memory with real theme CSS/JS and controlled asset response delays.
No site content/settings, browser tools or response bodies are saved or changed.
Use --baseline to record the old behavior before applying a correction.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit

from selenium import webdriver
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', required=True, type=Path)
parser.add_argument('--baseline', action='store_true')
parser.add_argument('--stylesheet', type=Path, help='Optional baseline stylesheet in the Simo artifact area.')
args = parser.parse_args()
ROOT = Path('/Volumes/Simo/Development/codex-browser-tools')
THEME = Path(__file__).resolve().parents[1]
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != ROOT / 'tmp':
    raise SystemExit('Source the existing Simo environment; no fallback.')
if not args.output_dir.resolve().is_relative_to(ROOT / 'artifacts'):
    raise SystemExit('Keep artifacts on Simo.')
if args.stylesheet and not args.stylesheet.resolve().is_relative_to(ROOT / 'artifacts'):
    raise SystemExit('Baseline stylesheets must stay in Simo artifacts.')
if not all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo('githeme', 8890)):
    raise SystemExit('Expected local CMS only.')
args.output_dir.mkdir(mode=0o700)
page = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--max-time', '30', 'https://githeme:8890/'],
                      capture_output=True, check=True, text=True).stdout
header = re.search(r'<header\b[^>]*class="site-header"[^>]*>.*?</header>', page, re.S)
inline = re.search(r'<style\b[^>]*id=[\'"]githeme-style-inline-css[\'"][^>]*>.*?</style>', page, re.S)
body_class = re.search(r'<body\b[^>]*class="([^"]*)"', page)
if not header or 'id="primary-menu"' not in header[0] or not inline or not body_class:
    raise SystemExit('Expected an existing public menu; no fixture content will be created in the CMS.')
header, inline, body_class = header[0], inline[0], body_class[1]
# Keep the selected local font same-origin in the replay. No CORS relaxation.
inline = inline.replace('https://githeme:8890/wp-content/themes/githeme/assets/fonts/', '/fonts/')
del page
css = (args.stylesheet or THEME / 'style.css').read_bytes()
javascript = (THEME / 'assets/js/navigation.js').read_bytes()
checks, samples, failures, errors = [], [], [], []


def check(ok, message, details=None):
    entry = {'check': message, 'ok': bool(ok), 'details': details}
    checks.append(entry)
    if not ok:
        failures.append(entry)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass

    def do_GET(self):
        target = urlsplit(self.path)
        query = parse_qs(target.query)
        delay = min(4, max(0, float(query.get('delay', ['0'])[0])))
        if target.path == '/style.css':
            time.sleep(delay)
            content, kind = css, 'text/css'
        elif target.path == '/navigation.js':
            time.sleep(delay)
            content, kind = javascript, 'application/javascript'
        elif target.path.startswith('/fonts/'):
            font_root = (THEME / 'assets/fonts').resolve()
            font = (font_root / target.path.removeprefix('/fonts/')).resolve()
            if not font.is_relative_to(font_root) or not font.is_file():
                self.send_error(404)
                return
            content, kind = font.read_bytes(), 'font/woff2'
        elif target.path == '/':
            css_delay = min(1, max(0, float(query.get('css-delay', ['0'])[0])))
            content = ('<!doctype html><html><head><meta charset="utf-8">'
                       '<meta name="viewport" content="width=device-width">'
                       '<link rel="stylesheet" href="/style.css?delay=' + str(css_delay) + '">' + inline +
                       '</head><body class="' + html.escape(body_class, quote=True) + '">' + header +
                       '<main id="main-content" tabindex="-1"><h1>Loading regression fixture</h1></main>'
                       '<script src="/navigation.js?delay=4"></script></body></html>').encode()
            kind = 'text/html'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass


def snapshot(driver):
    return driver.execute_script('''
        const n=document.querySelector('.primary-navigation'),m=document.querySelector('#primary-menu');
        if(!n||!m||!document.querySelector('link').sheet)return null;
        const roots=[...m.children].map(e=>e.getBoundingClientRect().top);
        return {time:performance.now(),ready:document.readyState,width:innerWidth,
            pageWidth:document.documentElement.scrollWidth,cssApplied:getComputedStyle(m).display==='flex',
            enhanced:n.classList.contains('is-enhanced'),compact:n.classList.contains('is-compact'),
            menuHidden:m.hidden,headerHeight:document.querySelector('.site-header').getBoundingClientRect().height,
            navigationHeight:n.getBoundingClientRect().height,
            logoLoaded:[...document.querySelectorAll('.site-branding img')].every(i=>i.complete&&i.naturalWidth>0),
            fontsLoaded:document.fonts.status==='loaded',
            rootRows:new Set(roots.map(y=>Math.round(y))).size,
            visibleSubmenus:[...m.querySelectorAll(':scope > li > ul')].filter(e=>e.getClientRects().length).length,
            resources:performance.getEntriesByType('resource').filter(e=>e.name.includes('/navigation.js')||e.name.includes('/style.css')).map(e=>({path:new URL(e.name).pathname,start:e.startTime,end:e.responseEnd}))};
    ''')


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    for scripting in ([True] if args.baseline else [True, False]):
        driver = None
        with tempfile.TemporaryDirectory(prefix='navigation-loading-', dir=ROOT / 'tmp') as profile:
            try:
                options = webdriver.FirefoxOptions()
                options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
                options.add_argument('-headless')
                options.add_argument('-no-remote')
                options.add_argument('-profile')
                options.add_argument(profile)
                options.page_load_strategy = 'none'
                options.enable_bidi = True
                options.accept_insecure_certs = False
                options.set_preference('javascript.enabled', scripting)
                options.set_preference('browser.cache.disk.enable', False)
                options.set_preference('browser.cache.memory.enable', False)
                service = Service(str(ROOT / 'drivers/geckodriver'),
                                  service_args=['--host', '127.0.0.1', '--profile-root', str(ROOT / 'tmp/driver-profiles'), '--log', 'fatal'],
                                  log_output=str(args.output_dir / ('driver-' + str(scripting) + '.log')), env=os.environ.copy())
                driver = webdriver.Firefox(options=options, service=service)
                driver.script.add_javascript_error_handler(lambda e: errors.append(str(getattr(e, 'text', ''))))
                widths = [1440, 390] if args.baseline else [1440, 1280, 768, 390, 320]
                for width in widths:
                    for css_delay in ([0] if args.baseline or not scripting else [0, 1]):
                        name = f'{"js" if scripting else "native"}-{width}-css{css_delay}'
                        driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
                        action = ActionBuilder(driver)
                        action.pointer_action.move_to_location(2, 850)
                        action.perform()
                        driver.get(f'http://127.0.0.1:{server.server_port}/?css-delay={css_delay}')
                        WebDriverWait(driver, 15).until(lambda d: snapshot(d))
                        before = snapshot(driver)
                        frames = [before]
                        if scripting:
                            check(not before['enhanced'] and before['cssApplied'], name + '/capture before JS with CSS applied', before)
                            driver.save_screenshot(str(args.output_dir / (name + '-before.png')))
                            until = time.monotonic() + 8
                            while time.monotonic() < until:
                                state = snapshot(driver)
                                frames.append(state)
                                if state['enhanced']:
                                    break
                                time.sleep(.12)
                            check(frames[-1]['enhanced'], name + '/enhancement eventually initialized')
                        else:
                            time.sleep(.2)
                        after = snapshot(driver)
                        samples.append({'case': name, 'before': before, 'after': after, 'frames': frames})
                        if args.baseline:
                            check(before['visibleSubmenus'] > 0 and after['visibleSubmenus'] == 0,
                                  name + '/reproduced JS-gated CSS flash', {'before': before, 'after': after})
                            driver.save_screenshot(str(args.output_dir / (name + '-after.png')))
                            continue
                        check(all(s['visibleSubmenus'] == 0 for s in frames), name + '/no expanded dropdowns at any loading stage')
                        check(before['width'] == width and before['pageWidth'] == width and after['pageWidth'] == width,
                              name + '/exact viewport without page overflow')
                        if width > 768:
                            check(before['rootRows'] == 1 and after['rootRows'] == 1, name + '/horizontal row before and after enhancement')
                            # Branding images can finish independently; measure
                            # navigation itself, not unrelated logo layout shifts.
                            check(abs(before['navigationHeight'] - after['navigationHeight']) < 1, name + '/stable desktop navigation height')
                        if scripting:
                            check(after['compact'] == (width <= 768), name + '/existing responsive mode')
                        if scripting and width <= 768:
                            toggle = driver.find_element(By.CSS_SELECTOR, '.menu-toggle')
                            toggle.send_keys(Keys.ENTER)
                            check(toggle.get_attribute('aria-expanded') == 'true' and not driver.find_element(By.ID, 'primary-menu').get_property('hidden'), name + '/keyboard opens mobile menu')
                            driver.find_element(By.CSS_SELECTOR, '#primary-menu a').send_keys(Keys.ESCAPE)
                            check(toggle.get_attribute('aria-expanded') == 'false' and driver.switch_to.active_element == toggle, name + '/Escape restores focus')
                        else:
                            check(not driver.find_element(By.CSS_SELECTOR, '.menu-toggle').is_displayed(), name + '/no inactive toggle')
                            parents = driver.find_elements(By.CSS_SELECTOR, '#primary-menu > li.menu-item-has-children')
                            check(bool(parents), name + '/existing dropdown coverage')
                            for item in parents:
                                link = item.find_element(By.CSS_SELECTOR, ':scope > a')
                                panel = item.find_element(By.CSS_SELECTOR, ':scope > ul')
                                link.send_keys(Keys.NULL)
                                check(panel.is_displayed(), name + '/focus opens dropdown')
                                check(driver.execute_script('const r=arguments[0].getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1', panel), name + '/dropdown stays inside viewport')
                                link.send_keys(Keys.TAB)
                                check(driver.execute_script('return arguments[0].contains(document.activeElement)&&document.activeElement.matches(":focus-visible")&&getComputedStyle(document.activeElement).outlineStyle!=="none"', panel), name + '/submenu reachable with visible keyboard focus')
                                if scripting:
                                    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                                    check(not panel.is_displayed() and driver.switch_to.active_element == link, name + '/desktop Escape dismisses')
                        driver.save_screenshot(str(args.output_dir / (name + '-after.png')))
                if scripting and not args.baseline:
                    # Interaction must also work during the delayed download,
                    # including focus preservation when enhancement arrives.
                    for width in [1440, 390]:
                        name = f'early-keyboard-{width}'
                        driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
                        action = ActionBuilder(driver)
                        action.pointer_action.move_to_location(2, 850)
                        action.perform()
                        driver.get(f'http://127.0.0.1:{server.server_port}/')
                        WebDriverWait(driver, 15).until(lambda d: snapshot(d))
                        check(not snapshot(driver)['enhanced'], name + '/script still pending')
                        parent = driver.find_element(By.CSS_SELECTOR, '#primary-menu > li.menu-item-has-children > a')
                        parent.send_keys(Keys.NULL)
                        parent.send_keys(Keys.TAB)
                        focused = driver.switch_to.active_element
                        check(driver.execute_script('return document.activeElement.closest(".sub-menu")!==null&&getComputedStyle(document.activeElement).outlineStyle!=="none"'), name + '/submenu usable before enhancement')
                        WebDriverWait(driver, 10).until(lambda d: snapshot(d)['enhanced'])
                        if width > 768:
                            check(driver.switch_to.active_element == focused and focused.is_displayed(), name + '/desktop focus retained')
                        else:
                            toggle = driver.find_element(By.CSS_SELECTOR, '.menu-toggle')
                            check(driver.switch_to.active_element == toggle and toggle.is_displayed() and toggle.get_attribute('aria-expanded') == 'false', name + '/mobile focus moves to visible toggle')
            finally:
                if driver:
                    driver.quit()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    (args.output_dir / 'report.json').write_text(json.dumps({'checks': checks, 'failures': failures, 'errors': errors, 'samples': samples}, indent=2))

check(not errors, 'No JavaScript errors', errors)
(args.output_dir / 'report.json').write_text(json.dumps({'checks': checks, 'failures': failures, 'errors': errors, 'samples': samples}, indent=2))
print(json.dumps({'checks': len(checks), 'failures': len(failures), 'baseline': args.baseline, 'output': str(args.output_dir)}))
raise SystemExit(bool(failures))
