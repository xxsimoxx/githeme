"""Isolated Social menu Firefox checks; never loads a website or connects to a CMS.
Run with the existing Selenium environment, e.g. its venv/bin/python -B this-file.
All fixtures, anonymous profiles and logs are temporary under this tests directory.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

THEME = Path(__file__).resolve().parent.parent
TOOLS = Path('/Volumes/Simo/Development/codex-browser-tools')
PHP = os.environ.get('GITHEME_TEST_PHP', '/Applications/MAMP/bin/php/php8.2.13/bin/php')
fixture = json.loads(subprocess.check_output([PHP, str(THEME / 'tests/social-menu.php'), '--json'], text=True))
checks = 0
samples = []

def check(ok, label):
    global checks
    if not ok:
        raise AssertionError(label)
    checks += 1

with tempfile.TemporaryDirectory(prefix='.social-menu-browser-', dir=THEME / 'tests') as tmp:
    temp = Path(tmp)
    for js in (True, False):
        profile = temp / ('profile-js' if js else 'profile-no-js')
        profile.mkdir()
        options = webdriver.FirefoxOptions()
        options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
        options.add_argument('-headless')
        options.add_argument('-no-remote')
        options.add_argument('-profile')
        options.add_argument(str(profile))
        options.enable_bidi = True
        options.accept_insecure_certs = False
        options.set_preference('javascript.enabled', js)
        env = os.environ.copy()
        env.update(TMPDIR=tmp, TMP=tmp, TEMP=tmp, XDG_CACHE_HOME=str(temp / 'cache'))
        service = Service(str(TOOLS / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', tmp, '--log', 'fatal'], log_output=str(temp / 'driver.log'), env=env)
        driver = webdriver.Firefox(options=options, service=service)
        try:
            for width in (1440, 768, 390, 320):
                driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
                for direction in ('ltr', 'rtl'):
                    palette = fixture['palettes'][0 if direction == 'ltr' else 3]
                    doc = '<!doctype html><html lang="en" dir="' + direction + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Social menu fixture</title><style>' + fixture['css'] + palette['css'] + '</style></head><body><main class="site-main site-container"><a id="before" href="#before">Before social menu</a>' + fixture['fixtures']['both']
                    path = temp / 'fixture.html'
                    path.write_text(doc)
                    driver.get(path.as_uri())
                    check(driver.execute_script('return innerWidth') == width, 'Exact viewport')
                    check(driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'), 'No horizontal overflow')
                    nav = driver.find_element(By.CSS_SELECTOR, '.githeme-social-navigation')
                    check(nav.accessible_name == 'Social', 'Named navigation landmark')
                    links = nav.find_elements(By.TAG_NAME, 'a')
                    check([a.accessible_name for a in links] == ['Our photographs', 'Our code', 'Visit our information page with a longer label', 'Email the team'], 'Original accessible labels and native nested order')
                    check(len(nav.find_elements(By.TAG_NAME, 'svg')) == 3, 'Icons only on recognized URLs')
                    check(driver.execute_script('return getComputedStyle(arguments[0]).textDecorationLine', links[2]) == 'none', 'Text fallback has no underline inside Social')
                    check('underline' in driver.execute_script('return getComputedStyle(document.getElementById("before")).textDecorationLine'), 'Editorial links outside Social remain underlined')
                    ActionChains(driver).move_to_element(links[2]).perform()
                    check(driver.execute_script('let s=getComputedStyle(arguments[0]);return s.borderTopColor===s.color&&parseFloat(s.borderTopWidth)>=1', links[2]), 'Fallback link retains visible hover border')
                    for link in links:
                        rect = link.rect
                        check(rect['width'] >= 44 and rect['height'] >= 44, 'Adequate link hit area')
                        check(driver.execute_script('const r=arguments[0].getBoundingClientRect();return r.left>=0&&r.right<=innerWidth', link), 'Link within viewport')
                    check(links[0].get_attribute('target') == '_blank' and 'noopener' in links[0].get_attribute('rel'), 'Native target/relationship retained')
                    driver.execute_script('document.getElementById("before").focus()')
                    # Widget fixture has no links: native Tab must enter Social in DOM order.
                    for link in links:
                        driver.switch_to.active_element.send_keys(Keys.TAB)
                        check(driver.switch_to.active_element == link, 'Native Tab order, SVG not focusable')
                        focus = driver.execute_script('const s=getComputedStyle(arguments[0]);const r=arguments[0].getBoundingClientRect();return {style:s.outlineStyle,width:parseFloat(s.outlineWidth),offset:parseFloat(s.outlineOffset),top:r.top,bottom:r.bottom}', link)
                        check(focus['style'] == 'solid' and focus['width'] >= 3 and focus['offset'] >= 0, 'Visible keyboard focus')
                        check(focus['top'] >= 3 and focus['bottom'] <= 897, 'Focus ring not clipped at viewport edge')
                    driver.switch_to.active_element.send_keys(Keys.SHIFT, Keys.TAB)
                    check(driver.switch_to.active_element == links[-2], 'Native reverse Tab')
                    samples.append({'width': width, 'direction': direction, 'javascript': js})
        finally:
            driver.quit()
print(json.dumps({'checks': checks, 'samples': samples, 'kind': 'isolated native-walker fixtures; no CMS or external pages', 'temporary_files_removed': True}))
