"""Focused Firefox checks for navigation list replacement; no CMS settings saved.

Source the existing Simo env.sh. Real frontend checks are separate from DOM
fixtures, which dispatch the public Selective Refresh event through a small stub.
"""
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

ROOT = Path('/Volumes/Simo/Development/codex-browser-tools')
THEME = Path(__file__).resolve().parents[1]
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != ROOT / 'tmp':
    raise SystemExit('Source the existing Simo environment; no fallback.')
checks = []


def check(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})
    if not ok:
        raise AssertionError(label)


instrumentation = """
window.probe = {listeners: 0, observers: [], events: {}, errors: []};
addEventListener('error', event => probe.errors.push(event.message));
const originalAdd = EventTarget.prototype.addEventListener;
EventTarget.prototype.addEventListener = function(...args) {
    probe.listeners++; return originalAdd.apply(this, args);
};
const NativeObserver = ResizeObserver;
window.ResizeObserver = class {
    constructor(callback) { this.targets = new Set(); this.native = new NativeObserver(callback); probe.observers.push(this); }
    observe(node) { this.targets.add(node); this.native.observe(node); }
    unobserve(node) { this.targets.delete(node); this.native.unobserve(node); }
};
window.wp = {customize: {selectiveRefresh: {
    bind(event, callback) { (probe.events[event] ||= []).push(callback); }
}}};
window.refreshMenu = () => {
    const old = document.querySelector('#primary-menu');
    const fresh = old.cloneNode(true);
    fresh.hidden = false;
    fresh.querySelectorAll('[style]').forEach(node => node.removeAttribute('style'));
    fresh.prepend(fresh.lastElementChild);
    old.replaceWith(fresh);
    probe.events['partial-content-rendered'].forEach(callback => callback({container: fresh}));
    return {oldDetached: !old.isConnected, hidden: fresh.hidden};
};
"""
links = ''.join(f'<li><a href="#item-{i}">Menu item {i}</a></li>' for i in range(1, 5))
menu = '<ul id="primary-menu" class="primary-menu"><li class="menu-item-has-children"><a href="#parent">Parent</a><ul class="sub-menu"><li><a href="#child">Child</a></li></ul></li>' + links + '</ul>'
header = '<header class="site-header"><div class="site-container header-inner"><div class="site-branding"><p class="site-title"><a href="#">Example</a></p></div><nav class="primary-navigation" aria-label="Primary menu"><button class="menu-toggle" type="button" aria-controls="primary-menu" aria-expanded="false" hidden>Menu</button>' + menu + '</nav></div></header>'
source = (THEME / 'assets/js/navigation.js').read_text()
fixture = '<!doctype html><html lang="en"><meta charset="utf-8"><style>' + (THEME / 'style.css').read_text() + '</style><body>' + header + '<main><h1>Navigation fixture</h1></main><script>' + instrumentation + source + '</script></body></html>'

with tempfile.TemporaryDirectory(prefix='navigation-refresh-', dir=ROOT / 'tmp') as profile:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.add_argument('-headless')
    options.add_argument('-profile')
    options.add_argument(profile)
    options.enable_bidi = True
    options.accept_insecure_certs = False
    service = Service(str(ROOT / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(ROOT / 'tmp/driver-profiles'), '--log', 'error'], log_output=os.devnull)
    driver = webdriver.Firefox(options=options, service=service)
    try:
        for width in (1440, 768, 320):
            driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
            driver.get('https://githeme:8890/')
            time.sleep(.3)
            check(driver.execute_script('return !!document.querySelector(".primary-navigation.is-enhanced #primary-menu")'), f'Real frontend enhanced at {width}')
            if driver.execute_script('return document.querySelector(".primary-navigation").classList.contains("is-compact")'):
                button = driver.find_element(By.CSS_SELECTOR, '.menu-toggle')
                button.click()
                check(not driver.find_element(By.ID, 'primary-menu').get_property('hidden'), f'Real frontend opens at {width}')
                button.click()
                check(driver.find_element(By.ID, 'primary-menu').get_property('hidden'), f'Real frontend closes at {width}')

            driver.get('data:text/html;charset=utf-8,' + quote(fixture))
            time.sleep(.3)
            baseline = driver.execute_script('return probe.listeners')
            compact = width <= 768
            check(driver.execute_script('return innerWidth') == width, f'Exact fixture viewport {width}')
            check(driver.execute_script('return document.querySelector(".primary-navigation").classList.contains("is-compact")') == compact, f'Fixture mode {width}')
            for replacement in range(5):
                result = driver.execute_script('return refreshMenu()')
                check(result['oldDetached'] and result['hidden'] == compact, f'Immediate replacement state {width}/{replacement}')
                check(driver.execute_script('return probe.observers.length === 1 && probe.observers[0].targets.size === 3 && [...probe.observers[0].targets].every(node => node.isConnected)'), f'Observer transfers without retaining removed list {width}/{replacement}')
                check(driver.execute_script('return probe.listeners') == baseline, f'No listener accumulation {width}/{replacement}')
                check(driver.execute_script('return probe.events["partial-content-rendered"].length === 1'), f'Single refresh handler {width}/{replacement}')
                if compact:
                    button = driver.find_element(By.CSS_SELECTOR, '.menu-toggle')
                    button.click()
                    check(not driver.find_element(By.ID, 'primary-menu').get_property('hidden'), f'One click opens replacement {width}/{replacement}')
                    driver.execute_script('refreshMenu()')
                    check(driver.find_element(By.CSS_SELECTOR, '.menu-toggle').get_attribute('aria-expanded') == 'true' and not driver.find_element(By.ID, 'primary-menu').get_property('hidden'), f'Open state survives replacement {width}/{replacement}')
                    driver.find_element(By.CSS_SELECTOR, '#primary-menu a').send_keys(Keys.ESCAPE)
                    check(driver.find_element(By.ID, 'primary-menu').get_property('hidden'), f'Escape closes replacement {width}/{replacement}')
                    check(driver.switch_to.active_element == button, f'Escape restores toggle focus {width}/{replacement}')
                else:
                    parent = driver.find_element(By.CSS_SELECTOR, '#primary-menu .menu-item-has-children > a')
                    driver.execute_script('arguments[0].focus()', parent)
                    parent.send_keys(Keys.TAB)
                    child = driver.find_element(By.CSS_SELECTOR, '#primary-menu .sub-menu a')
                    check(child.is_displayed() and driver.switch_to.active_element == child, f'Desktop focus opens dropdown {replacement}')
                    child.send_keys(Keys.ESCAPE)
                    check(not child.is_displayed(), f'Desktop Escape uses replacement {replacement}')
            check(driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'), f'No fixture overflow {width}')
            check(driver.execute_script('return probe.errors.length === 0'), f'No fixture JS errors {width}')
    finally:
        driver.quit()

print(json.dumps({'checks': len(checks), 'passed': sum(row['passed'] for row in checks), 'coverage': 'Real anonymous frontend plus DOM replacement fixtures; not authenticated Customizer AJAX'}, indent=2))
