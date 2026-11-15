"""Focused, read-only Firefox checks for gallery caption overlays.

Source Simo's env.sh; pass --fixtures and --widget exported by the existing
gallery-slider.php / gallery-widget.php tests, and a new --output-dir on Simo.
No CMS content, widget settings or browser installation is changed.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixtures', required=True, type=Path)
parser.add_argument('--widget', required=True, type=Path)
parser.add_argument('--output-dir', required=True, type=Path)
parser.add_argument('--page-url', choices=['https://githeme:8890/?page_id=490'])
args = parser.parse_args()
root = Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != root / 'tmp':
    raise SystemExit('Source the existing Simo browser environment; no fallback.')
if not args.output_dir.resolve().is_relative_to(root / 'artifacts'):
    raise SystemExit('Keep artifacts on Simo.')
run = args.output_dir
run.mkdir(mode=0o700)
theme = Path(__file__).resolve().parents[1]
fixtures = json.loads(args.fixtures.read_text())['fixtures']
widget = json.loads(args.widget.read_text())
css = (theme / 'style.css').read_text()
checks, failures, errors, samples = [], [], [], []


def check(ok, label, details=None):
    entry = {'check': label, 'ok': bool(ok), 'details': details}
    checks.append(entry)
    if not ok:
        failures.append(entry)


def prefixed(fragment, prefix):
    return re.sub(r'(id|aria-describedby)="([^"]+)"',
                  lambda m: m[1] + '="' + prefix + m[2] + '"', fragment)


def metrics(driver, selector):
    return driver.execute_script('''
        return [...document.querySelectorAll(arguments[0]+' .gallery-item')].map(item=>{
            const image=item.querySelector('img'),caption=item.querySelector('.gallery-caption');
            const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
            const s=caption?getComputedStyle(caption):null;
            return {image:box(image),item:box(item),natural:[image.naturalWidth,image.naturalHeight],
                caption:caption?{...box(caption),text:caption.textContent,position:s.position,
                    overflow:s.overflowY,scrollHeight:caption.scrollHeight,clientHeight:caption.clientHeight,
                    scrollWidth:caption.scrollWidth,clientWidth:caption.clientWidth,display:s.display}:null};
        });''', selector)


def geometry(driver, selector, label):
    state = metrics(driver, selector)
    samples.append({'case': label, 'items': state})
    for i, item in enumerate(state):
        image, caption = item['image'], item['caption']
        check(abs(item['item']['w'] - image['w']) < 1 and abs(item['item']['h'] - image['h']) < 1,
              label + '/image-sized slide/' + str(i))
        if caption and caption['text']:
            check(caption['position'] == 'absolute', label + '/overlay/' + str(i))
            check(abs((caption['x'] + caption['w'] / 2) - (image['x'] + image['w'] / 2)) < 1,
                  label + '/centred on own image/' + str(i))
            check(caption['x'] >= image['x'] - .5 and caption['right'] <= image['right'] + .5
                  and caption['y'] >= image['y'] - .5 and caption['bottom'] <= image['bottom'] + .5,
                  label + '/inside own image/' + str(i))
            check(caption['scrollWidth'] <= caption['clientWidth'] + 1 and caption['overflow'] == 'auto',
                  label + '/wrap and full text available/' + str(i))
    return state


def document(javascript):
    main = fixtures['syntheticSlider']
    legacy = prefixed(main, 'legacy-').replace('<figure ', '<dl ').replace('</figure>', '</dl>')
    legacy = legacy.replace('<div class="gallery-icon">', '<dt class="gallery-icon">').replace('</a></div>', '</a></dt>')
    legacy = legacy.replace('<figcaption ', '<dd ').replace('</figcaption>', '</dd>')
    absent = re.sub(r'<figcaption\b.*?</figcaption>', '', prefixed(main, 'absent-'), flags=re.S)
    absent = re.sub(r' aria-describedby="[^"]+"', '', absent)
    classic = prefixed(fixtures['syntheticClassic'], 'classic-')
    tiny = '<div class="githeme-gallery-slider" data-githeme-gallery-uniform style="--githeme-gallery-source-height:40px;--githeme-gallery-max-ratio:2"><div class="githeme-gallery-slider__viewport" tabindex="0"><div class="gallery">'
    for w, h in [(80, 40), (60, 60)]:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="silver"/></svg>'
        src = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
        tiny += f'<figure class="gallery-item"><div class="gallery-icon"><img src="{src}" width="{w}" height="{h}" alt="Small source"></div><figcaption class="gallery-caption">' + 'Small image with a complete long caption. ' * 8 + '</figcaption></figure>'
    tiny += '</div></div></div>'
    # A caption link must remain interactive and readable on the overlay.
    linked = main.replace('Caption 0:', '<a href="#after">Caption 0:</a>', 1)
    policy = "default-src 'none'; img-src data: https://githeme:8890; style-src 'unsafe-inline'; script-src "
    policy += "'unsafe-inline'" if javascript else "'none'"
    result = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    result += '<meta http-equiv="Content-Security-Policy" content="' + policy + '"><style>' + css + '</style>'
    if javascript:
        result += '<script>' + fixtures['javascript'] + '</script>'
    result += '</head><body><main class="site-container">'
    for name, fragment in [('slider', linked), ('widget', widget['html']), ('legacy', legacy), ('tiny', tiny), ('absent', absent), ('classic', classic)]:
        result += '<section id="' + name + '"><h2>' + name + '</h2>' + fragment + '</section>'
    return result + '<p id="after"><a href="#slider">After galleries</a></p></main></body></html>'


for javascript in [True, False]:
    driver = None
    with tempfile.TemporaryDirectory(prefix='gallery-captions-', dir=root / 'tmp') as profile:
        try:
            options = webdriver.FirefoxOptions()
            options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
            options.add_argument('-headless')
            options.add_argument('-no-remote')
            options.add_argument('-profile')
            options.add_argument(profile)
            options.enable_bidi = True
            options.accept_insecure_certs = False
            options.set_preference('javascript.enabled', javascript)
            options.set_preference('ui.prefersReducedMotion', 0 if javascript else 1)
            service = Service(str(root / 'drivers/geckodriver'),
                              service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'],
                              log_output=str(run / ('driver-' + str(javascript) + '.log')), env=os.environ.copy())
            driver = webdriver.Firefox(options=options, service=service)
            driver.set_page_load_timeout(30)
            driver.script.add_javascript_error_handler(lambda e: errors.append(str(getattr(e, 'text', ''))))
            fixture = run / ('fixture-' + str(javascript) + '.html')
            fixture.write_text(document(javascript))
            for rtl in [False, True]:
                for width in [1440, 768, 390, 320]:
                    label = f'{"js" if javascript else "native"}/{"rtl" if rtl else "ltr"}/{width}'
                    driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
                    driver.get(fixture.as_uri())
                    if rtl:
                        driver.execute_script('document.documentElement.dir="rtl"')
                    # Native widget images retain loading="lazy"; load them by
                    # scrolling instead of changing their real CMS attributes.
                    for image in driver.find_elements(By.CSS_SELECTOR, 'img[loading="lazy"]'):
                        driver.execute_script('arguments[0].scrollIntoView({block:"center",inline:"center"})', image)
                        WebDriverWait(driver, 15).until(lambda d: image.get_property('complete') and image.get_property('naturalWidth') > 0)
                    driver.execute_script('document.querySelectorAll(".githeme-gallery-slider__viewport").forEach(v=>v.scrollLeft=0);window.scrollTo(0,0)')
                    WebDriverWait(driver, 15).until(lambda d: d.execute_script('return [...document.images].every(i=>i.complete&&i.naturalWidth>0)'))
                    for region in ['slider', 'widget', 'legacy', 'tiny']:
                        geometry(driver, '#' + region, label + '/' + region)
                    tiny_state = metrics(driver, '#tiny')
                    check(all(i['image']['w'] <= i['natural'][0] + 1 and i['image']['h'] <= i['natural'][1] + 1 for i in tiny_state), label + '/small sources never enlarged')
                    if not rtl and width == 1440:
                        for color in ['#202833', '#ffffff', '#ffff00']:
                            ratio = driver.execute_script('''
                                document.documentElement.style.setProperty('--color-text',arguments[0]);
                                const s=getComputedStyle(document.querySelector('#slider .gallery-caption'));
                                const c=document.createElement('canvas');c.width=c.height=1;const x=c.getContext('2d');
                                x.fillStyle='white';x.fillRect(0,0,1,1);x.fillStyle=s.backgroundColor;x.fillRect(0,0,1,1);
                                const rgb=[...x.getImageData(0,0,1,1).data].slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});
                                return 1.05/(rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722+.05);
                            ''', color)
                            check(ratio >= 4.5, label + '/caption contrast on white image/' + color, ratio)
                        driver.execute_script('document.documentElement.style.removeProperty("--color-text")')
                    after = metrics(driver, '#slider')
                    before_css = (args.fixtures.parent / 'before.css').read_text()
                    driver.execute_script('document.querySelector("style").textContent=arguments[0]', before_css)
                    before = metrics(driver, '#slider')
                    check(all(abs(a['image']['w']-b['image']['w']) < 1 and abs(a['image']['h']-b['image']['h']) < 1
                              and a['caption']['text'] == b['caption']['text'] for a,b in zip(after,before)),
                          label + '/image sizing and complete text unchanged')
                    driver.execute_script('document.querySelector("style").textContent=arguments[0]', css)
                    check(driver.execute_script('return innerWidth===arguments[0]&&document.documentElement.scrollWidth===innerWidth', width), label + '/exact viewport without page overflow')
                    check(driver.execute_script('return !document.querySelector("#absent .gallery-caption")'), label + '/no invented empty caption')
                    check(driver.execute_script('return getComputedStyle(document.querySelector("#classic .gallery-caption")).position==="static"'), label + '/traditional gallery unchanged')
                    port = driver.find_element(By.CSS_SELECTOR, '#slider .githeme-gallery-slider__viewport')
                    port.send_keys(Keys.NULL)
                    check(driver.execute_script('return document.activeElement===arguments[0]&&getComputedStyle(arguments[0]).outlineStyle!=="none"', port), label + '/scrollport keyboard focus')
                    seen, scrollable_focus = set(), False
                    for _ in range(22):
                        driver.switch_to.active_element.send_keys(Keys.TAB)
                        active = driver.switch_to.active_element
                        kind = driver.execute_script('const e=document.activeElement;return {inside:arguments[0].contains(e),image:!!e.querySelector("img"),caption:e.classList.contains("gallery-caption"),outline:getComputedStyle(e).outlineStyle}', port)
                        if not kind['inside']:
                            break
                        if kind['image']:
                            seen.add(active.id)
                            check(kind['outline'] != 'none', label + '/image link focus visible')
                            if javascript:
                                time.sleep(.12)
                                check(driver.execute_script('const v=arguments[0].getBoundingClientRect(),i=document.activeElement.querySelector("img").getBoundingClientRect();return i.left>=v.left-1&&i.right<=v.left+arguments[0].clientWidth+1', port), label + '/focused image fully revealed')
                                if len(seen) == 5:
                                    position = driver.execute_script('return arguments[0].scrollLeft', port)
                                    time.sleep(2)
                                    check(abs(driver.execute_script('return arguments[0].scrollLeft', port)-position) < .5, label + '/focus correction remains stable')
                        if kind['caption']:
                            scrollable_focus = True
                            active.send_keys(Keys.END)
                            # Firefox animates keyboard scrolling independently
                            # of the slider's JavaScript scroll correction.
                            time.sleep(.3)
                            focus_state = driver.execute_script('return {top:arguments[0].scrollTop,height:arguments[0].clientHeight,scroll:arguments[0].scrollHeight,outline:getComputedStyle(arguments[0]).outlineStyle}', active)
                            check(focus_state['top'] > 0 and focus_state['outline'] != 'none', label + '/long caption keyboard scroll and focus', focus_state)
                    check(len(seen) == 5, label + '/Tab reaches every image without trap')
                    check(scrollable_focus, label + '/overflow caption natively keyboard reachable')
                    if javascript:
                        next_button = driver.find_element(By.CSS_SELECTOR, '#slider .githeme-gallery-slider__next')
                        driver.execute_script('arguments[0].scrollLeft=0', port)
                        time.sleep(.15)
                        next_button.click()
                        time.sleep(1)
                        check(abs(driver.execute_script('return arguments[0].scrollLeft', port)) > 1, label + '/Next navigation works')
                        driver.execute_script('arguments[0].scrollIntoView({block:"center"})', next_button)
                        check(driver.execute_script('const r=arguments[0].getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("button")===arguments[0]', next_button), label + '/caption does not intercept navigation control')
                    else:
                        check(not driver.find_elements(By.TAG_NAME, 'button'), label + '/no inactive controls without JS')
                    if not rtl and width in [1440,390]:
                        driver.execute_script('arguments[0].scrollLeft=0;window.scrollTo(0,0)', port)
                        time.sleep(.15)
                        driver.save_screenshot(str(run / (label.replace('/', '-') + '.png')))
                        driver.execute_script('arguments[0].scrollLeft=arguments[0].scrollWidth;arguments[0].querySelectorAll(".gallery-caption").forEach(c=>c.scrollTop=0)', port)
                        time.sleep(.3)
                        if javascript:
                            check(driver.execute_script('const c=arguments[0].querySelector(".gallery-item:last-child .gallery-caption").getBoundingClientRect(),b=arguments[1].getBoundingClientRect();return c.top>=b.bottom-1', port, next_button), label + '/long caption below navigation band')
                        driver.save_screenshot(str(run / ('long-' + label.replace('/', '-') + '.png')))
            # A real widget's markup is also exercised in a narrow containing block.
            driver.execute_script('document.querySelector("#widget").style.maxWidth="14rem"')
            geometry(driver, '#widget', 'narrow-widget/' + str(javascript))
            if args.page_url:
                for width in [1440,390]:
                    driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width':width,'height':900})
                    driver.get(args.page_url)
                    ports = driver.find_elements(By.CSS_SELECTOR, '.githeme-gallery-slider__viewport')
                    check(bool(ports), f'real-page/{javascript}/{width}/slider exists')
                    for index,port in enumerate(ports):
                        for image in port.find_elements(By.CSS_SELECTOR, 'img'):
                            driver.execute_script('arguments[0].scrollIntoView({block:"center",inline:"center"})', image)
                            WebDriverWait(driver,15).until(lambda d: image.get_property('complete') and image.get_property('naturalWidth') > 0)
                        driver.execute_script('arguments[0].scrollLeft=0', port)
                        geometry(driver, '#' + port.get_attribute('id'), f'real-page/{javascript}/{width}/{index}')
                    check(driver.execute_script('return document.documentElement.scrollWidth===innerWidth'), f'real-page/{javascript}/{width}/no overflow')
                    if ports:
                        driver.execute_script('window.scrollTo(0,arguments[0].getBoundingClientRect().top+scrollY-25)', ports[0])
                        driver.save_screenshot(str(run / f'real-{javascript}-{width}.png'))
        except Exception:
            (run / 'report.json').write_text(json.dumps({'checks': checks, 'failures': failures, 'errors': errors, 'samples': samples}, indent=2))
            raise
        finally:
            if driver:
                driver.quit()

check(not errors, 'No JavaScript errors', errors)
(run / 'report.json').write_text(json.dumps({'checks': checks, 'failures': failures, 'errors': errors, 'samples': samples}, indent=2))
print(json.dumps({'checks': len(checks), 'failures': len(failures), 'output': str(run)}))
raise SystemExit(bool(failures))
