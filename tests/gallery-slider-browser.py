"""Read-only gallery CSS tests on exported native HTML and synthetic DOM fixtures.

Source the existing Simo env.sh. First export gallery-slider.php json via WP-CLI
with --url=https://githeme:8890. No CMS content, options or profiles are changed.
"""
import argparse
import base64
import ipaddress
import socket
import dataclasses
import datetime
import html
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
from selenium.webdriver.support.ui import WebDriverWait

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixtures', required=True, type=Path)
parser.add_argument('--page-url', help='Optional read-only local HTTPS page with sliders')
parser.add_argument('--javascript', action='store_true', help='Test the actual focus enhancement; default tests native behavior with JS disabled')
parser.add_argument('--output-dir', type=Path, help='New artifact subdirectory on Simo')
parser.add_argument('--compare-fixtures', type=Path, help='Earlier fixture export for CSS-only comparison screenshots')
args = parser.parse_args()
if args.page_url:
    target = urlsplit(args.page_url)
    if target.scheme != 'https' or not all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(target.hostname, target.port or 443)):
        raise SystemExit('Only local HTTPS pages are permitted.')
root = Path('/Volumes/Simo/Development/codex-browser-tools')
if not os.path.ismount('/Volumes/Simo') or Path(os.environ.get('TMPDIR', '')).resolve() != root / 'tmp':
    raise SystemExit('Source the existing Simo browser environment; no fallback.')
if not args.fixtures.resolve().is_relative_to(root / 'artifacts'):
    raise SystemExit('Keep fixture exports and artifacts in the existing Simo artifact area.')
data = json.loads(args.fixtures.read_text())
fixtures = data['fixtures']
run = root / 'artifacts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-gallery-slider')
if args.output_dir:
    run = args.output_dir.resolve()
    if not run.is_relative_to(root / 'artifacts'):
        raise SystemExit('Output must remain in Simo artifacts.')
run.mkdir(mode=0o700)
checks, failures, errors, network, samples = [], [], [], [], []
driver = service = None
profile = tempfile.TemporaryDirectory(prefix='gallery-anonymous-', dir=root / 'tmp')


def require(ok, label, details=None):
    checks.append({'check': label, 'ok': bool(ok), 'details': details})
    if not ok:
        raise AssertionError(label + ': ' + str(details))


def event(e, kind):
    v = e if isinstance(e, dict) else dataclasses.asdict(e)
    request, response = v.get('request', {}), v.get('response', {})
    u = urlsplit(request.get('url', ''))
    network.append({'kind': kind, 'path': u.path if u.scheme in ('http', 'https') else u.scheme + ':',
                    'origin': u.scheme + '://' + u.netloc, 'status': response.get('status'), 'error': v.get('errorText')})


def metrics(selector='#slider .githeme-gallery-slider__viewport'):
    return driver.execute_script('''
        const v=document.querySelector(arguments[0]),g=v.querySelector(':scope > .gallery'),r=v.getBoundingClientRect(),s=getComputedStyle(v);
        return {width:innerWidth,height:innerHeight,pageScroll:document.documentElement.scrollWidth,client:v.clientWidth,scroll:v.scrollWidth,
            left:r.left,right:r.right,padding:parseFloat(s.paddingLeft),snap:s.scrollSnapType,behavior:s.scrollBehavior,
            direction:s.direction,wrap:getComputedStyle(g).flexWrap,gap:parseFloat(getComputedStyle(g).columnGap),focus:document.activeElement===v,
            outline:s.outlineStyle,offset:s.outlineOffset,
            items:[...g.children].map(e=>{const r=e.getBoundingClientRect(),i=e.querySelector('img'),c=e.querySelector('.gallery-caption');
                return {left:r.left,right:r.right,width:r.width,align:getComputedStyle(e).scrollSnapAlign,
                    natural:i.naturalWidth/i.naturalHeight,ratio:i.getBoundingClientRect().width/i.getBoundingClientRect().height,
                    naturalWidth:i.naturalWidth,naturalHeight:i.naturalHeight,sourceWidth:Number(i.getAttribute('width')),sourceHeight:Number(i.getAttribute('height')),imageWidth:i.getBoundingClientRect().width,imageHeight:i.getBoundingClientRect().height,
                    imageLeft:i.getBoundingClientRect().left,imageRight:i.getBoundingClientRect().right,
                    caption:c?.textContent,captionOverflow:c?c.scrollHeight>c.clientHeight+1:false};})};
    ''', selector)


def check_geometry(state, label):
    require(all(abs(i['width'] - i['imageWidth']) < 1 for i in state['items']), 'Slide follows rendered image width ' + label, state)
    expected=min(state['height']*.7,650,min(i['sourceHeight'] for i in state['items']),(state['client']-2*state['padding'])/max(i['sourceWidth']/i['sourceHeight'] for i in state['items']))
    require(all(abs(i['imageHeight']-expected)<1 for i in state['items']), 'Common height bounded by source and container '+label, expected)
    gaps = [(a['left'] - b['right'] if state['direction'] == 'rtl' else b['left'] - a['right']) for a,b in zip(state['items'], state['items'][1:])]
    require(all(abs(g - state['gap']) < 1 for g in gaps), 'Regular gap without empty panels ' + label, gaps)
    used = sum(i['width'] for i in state['items']) + state['gap'] * (len(state['items']) - 1)
    # Firefox can use the trailing padding for a few pixels of nested flex
    # overflow; content still fully inside the scrollport needs no scrollbar.
    overflow = used > state['client'] - state['padding'] + 1
    require((state['scroll'] > state['client'] + 1) == overflow, 'Overflow only when images need it ' + label, {'used':used,'client':state['client'],'scroll':state['scroll']})
    require(state['pageScroll'] == state['width'] and all(i['width'] <= state['client'] - 2 * state['padding'] + 1 for i in state['items']), 'Images and captions bounded by component ' + label)


def inspect_link(port, label):
    def snapshot():
        return driver.execute_script("""
        const v=arguments[0],e=document.activeElement,i=e.querySelector('img'),p=v.getBoundingClientRect(),r=e.getBoundingClientRect(),s=getComputedStyle(e);
        return {link:e.tagName==='A'&&v.contains(e),focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,
            inside:r.left>=p.left-1&&r.right<=p.left+v.clientWidth+1,scrollLeft:v.scrollLeft,
            visible:Math.max(0,Math.min(r.right,p.left+v.clientWidth)-Math.max(r.left,p.left)),width:r.width,
            image:i?{width:i.getBoundingClientRect().width,left:i.getBoundingClientRect().left,right:i.getBoundingClientRect().right}:null,
            hasFocus:document.hasFocus(),viewport:innerWidth};
        """,port)
    time.sleep(.12)
    frames=[snapshot()]
    if args.javascript:
        time.sleep(.55);frames.append(snapshot());time.sleep(1.45);frames.append(snapshot())
    else:
        time.sleep(.55);frames.append(snapshot())
    f=frames[-1]
    samples.append({'case':label,'keyboardFrames':frames})
    require(f['link'] and f['hasFocus'] and f['focusVisible'] and f['outline']!='none' and f['visible']>1, 'Focused link and outline perceivable '+label, f)
    if args.javascript:
        require(f['inside'], 'Enhancement fully reveals focused image '+label, f)
        require(max(x['scrollLeft'] for x in frames)-min(x['scrollLeft'] for x in frames)<.5, 'Stable beyond two seconds '+label, frames)
    # No-JS retains the full-visibility measurement, without treating Firefox's
    # documented partial-focus behavior as a failure of native usability.


def check_manual(port,label):
    from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
    driver.execute_script("""const v=arguments[0];v.scrollLeft=0;window.galleryCalls=0;
        if(!v.originalScrollBy){v.originalScrollBy=v.scrollBy;v.scrollBy=function(...a){galleryCalls++;return this.originalScrollBy(...a)}}""",port)
    port.send_keys(Keys.NULL);driver.switch_to.active_element.send_keys(Keys.TAB);time.sleep(.12)
    require(driver.execute_script('return galleryCalls===0'), 'Already visible image needs no corrective scroll '+label)
    for _ in range(2):driver.switch_to.active_element.send_keys(Keys.TAB);time.sleep(.12)
    before=driver.execute_script('return {left:arguments[0].scrollLeft,count:galleryCalls,active:document.activeElement}',port)
    second=driver.find_element(By.CSS_SELECTOR,'#second .githeme-gallery-slider__viewport')
    other=driver.execute_script('return arguments[0].scrollLeft',second)
    rtl=driver.execute_script('return getComputedStyle(arguments[0]).direction==="rtl"',port)
    driver.switch_to.active_element.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
    time.sleep(.5)
    x,y=driver.execute_script('const r=arguments[0].getBoundingClientRect();return [(r.left+r.right)/2,Math.max(30,Math.min(800,r.top+60))]',port)
    webdriver.ActionChains(driver).scroll_from_origin(ScrollOrigin.from_viewport(int(x),int(y)),-600 if rtl else 600,0).perform()
    time.sleep(.7);left=driver.execute_script('return arguments[0].scrollLeft',port);time.sleep(2.1)
    final=driver.execute_script('return {left:arguments[0].scrollLeft,count:galleryCalls,same:document.activeElement===arguments[1]}',port,before['active'])
    require(abs(left-before['left'])>1 and abs(final['left']-left)<.5 and final['count']==before['count'] and final['same'], 'Manual arrows/wheel remain free without repeated corrections '+label, final)
    require(driver.execute_script('return arguments[0].scrollLeft',second)==other, 'Second slider independent after focused manual scroll '+label)


def check_buttons(port,label):
    wrapper=port.find_element(By.XPATH,'..')
    previous=wrapper.find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__previous')
    next_button=wrapper.find_element(By.CSS_SELECTOR,'.githeme-gallery-slider__next')
    for button in (previous,next_button):
        require(button.get_attribute('type')=='button' and button.get_attribute('aria-controls')==port.get_attribute('id') and bool(button.get_attribute('aria-label')), 'Named native controls associated with viewport '+label)
    rtl=driver.execute_script('return getComputedStyle(arguments[0]).direction==="rtl"',port)
    driver.execute_script('arguments[0].scrollLeft=0',port);time.sleep(.2)
    require(previous.get_attribute('aria-disabled')=='true' and next_button.get_attribute('aria-disabled')=='false', 'Initial button state '+label)
    other=driver.find_element(By.CSS_SELECTOR,'#second .githeme-gallery-slider__viewport')
    other_left=driver.execute_script('return arguments[0].scrollLeft',other)
    positions=[]
    for direction,button in [('next',next_button),('previous',previous)]:
        for _ in range(12):
            if button.get_attribute('aria-disabled')=='true':break
            before=driver.execute_script('return arguments[0].scrollLeft',port)
            target=driver.execute_script('''const v=arguments[0],forward=arguments[1],r=v.getBoundingClientRect(),rtl=getComputedStyle(v).direction==='rtl';let a=[...v.querySelectorAll('.gallery-icon img')];if(!forward)a.reverse();return a.find(i=>{const b=i.getBoundingClientRect();return forward!==rtl?b.right>r.left+v.clientWidth+1:b.left<r.left-1})''',port,direction=='next')
            require(target is not None, 'Available button has a target image '+label+'/'+direction)
            button.click();time.sleep(.3)
            require(driver.execute_script('const r=arguments[0].getBoundingClientRect(),v=arguments[1].getBoundingClientRect();return r.left>=v.left-1&&r.right<=v.left+arguments[1].clientWidth+1',target,port), 'Button reveals target image '+label+'/'+direction)
            after=driver.execute_script('return arguments[0].scrollLeft',port)
            positions.append(after)
            require(abs(after-before)>1, 'Variable-width navigation makes progress '+label+'/'+direction)
        require(button.get_attribute('aria-disabled')=='true', 'Navigation reaches logical boundary '+label+'/'+direction,positions)
        require(driver.switch_to.active_element==button and button.is_enabled(), 'Focused unavailable button retained with aria-disabled '+label+'/'+direction)
        left=driver.execute_script('return arguments[0].scrollLeft',port)
        button.click();time.sleep(.15)
        require(abs(driver.execute_script('return arguments[0].scrollLeft',port)-left)<.5, 'Unavailable focused button is inert '+label+'/'+direction)
    require(driver.execute_script('return arguments[0].scrollLeft',other)==other_left, 'Buttons affect only their own slider '+label)
    # Return focus to the scrollport; native disabled follows on blur.
    port.send_keys(Keys.NULL);time.sleep(.1)
    require(not previous.is_enabled(), 'Native disabled applied after blur '+label)
    require(driver.execute_script('return document.documentElement.scrollWidth===innerWidth'), 'Controls create no page overflow '+label)
    samples.append({'case':label+'/buttons','positions':positions,'rtl':rtl})


def extra_fixture(name, sizes, captions=False):
    items = []
    for index, (w,h) in enumerate(sizes):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="silver"/></svg>'
        src = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
        caption = f'<figcaption class="gallery-caption">{html.escape("A complete long caption with a link-like-unbreakable-string_" * 12)}</figcaption>' if captions else ''
        items.append(f'<figure class="gallery-item"><div class="gallery-icon"><img src="{src}" width="{w}" height="{h}" alt="{name} {index}"></div>{caption}</figure>')
    return f'<section id="{name}"><h2>{name}</h2><div class="githeme-gallery-slider" data-githeme-gallery-uniform style="--githeme-gallery-source-height:{min(h for w,h in sizes)}px;--githeme-gallery-max-ratio:{max(w/h for w,h in sizes)}"><div id="{name}-viewport" class="githeme-gallery-slider__viewport" tabindex="0" role="group" aria-label="{name}"><div class="gallery">'+''.join(items)+'</div></div></div></section>'


try:
    # File fixtures never add CMS content. Only the explicit --javascript mode
    # loads the actual theme enhancement; the default verifies native behavior.
    document = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    document += '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data: https://githeme:8890; style-src \'unsafe-inline\'; script-src \'none\'">'
    document += '<style>' + fixtures['css'] + '</style>'
    if args.javascript:
        document = document.replace("script-src 'none'", "script-src 'unsafe-inline'")
        document += '<script>' + fixtures['javascript'] + '</script>'
    document += '</head><body><main class="site-container">'
    for key, title in [('syntheticSlider', 'slider'), ('syntheticSecond', 'second'), ('syntheticClassic', 'classic'), ('syntheticSingle', 'single'), ('nativeSlider', 'native')]:
        fragment = fixtures[key]
        # Repeated synthetic source material is given distinct fixture IDs;
        # the exported native fragment is never altered.
        if key in ('syntheticClassic', 'syntheticSingle'):
            fragment = fragment.replace('gallery-fixture', 'gallery-fixture-' + title).replace('fixture-caption-', 'fixture-caption-' + title + '-')
        document += '<section id="' + title + '"><h2>' + html.escape(title) + '</h2>' + fragment + '</section>'
    for name,sizes,captions in [('covers-two',[(300,1200)]*2,True),('covers-many',[(300,1200)]*8,False),('landscape',[(1200,600),(900,600)],True),('squares',[(500,500)]*2,False),('large-squares',[(1600,1600)]*2,False),('small',[(80,40),(60,60)],True),('panorama',[(4000,400),(3200,500)],True)]:
        document += extra_fixture(name,sizes,captions)
    document += '<p id="after"><a href="#slider">After galleries</a></p></main></body></html>'
    path = run / 'fixture.html'
    path.write_text(document)
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.add_argument('-headless')
    options.add_argument('-no-remote')
    options.add_argument('-profile')
    options.add_argument(profile.name)
    options.enable_bidi = True
    options.accept_insecure_certs = False
    options.set_preference('javascript.enabled', args.javascript)
    options.set_preference('browser.cache.disk.enable', False)
    options.set_preference('ui.prefersReducedMotion', 1)
    service = Service(str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=str(run / 'driver.log'), env=os.environ.copy())
    driver = webdriver.Firefox(options=options, service=service)
    driver.set_page_load_timeout(30)
    driver.script.add_javascript_error_handler(lambda e: errors.append(str(getattr(e, 'text', ''))))
    driver.network.add_event_handler('response_completed', lambda e: event(e, 'response'))
    driver.network.add_event_handler('fetch_error', lambda e: event(e, 'fetch_error'))
    for rtl in [False, True]:
        for width in [1440, 768, 390, 320]:
            label = ('rtl' if rtl else 'ltr') + '/' + str(width)
            driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': width, 'height': 900})
            driver.get(path.as_uri())
            if rtl:
                driver.execute_script('document.documentElement.dir="rtl"')
            WebDriverWait(driver, 15).until(lambda d: d.execute_script('return [...document.querySelectorAll("#slider img")].every(i=>i.complete&&i.naturalWidth>0)'))
            state = metrics()
            samples.append({'case': label, **state})
            require(driver.execute_script('const ids=[...document.querySelectorAll("[id]")].map(e=>e.id);return ids.length===new Set(ids).size'), 'No duplicate IDs across galleries ' + label)
            require(state['width'] == width and state['pageScroll'] == width, 'Exact viewport/no page overflow ' + label, state)
            require(state['scroll'] > state['client'] and state['wrap'] == 'nowrap', 'Native horizontal overflow ' + label)
            check_geometry(state, label)
            # CSSOM may omit the default "proximity" keyword when serializing.
            require('scroll-snap-type: x proximity;' in fixtures['css'] and state['snap'] in ('x', 'x proximity') and all(i['align'] == 'start' for i in state['items']), 'Scroll Snap styles ' + label)
            require(all(abs(i['natural'] / i['ratio'] - 1) < .01 for i in state['items']), 'Natural image proportions ' + label)
            require(all(i['imageHeight'] <= min(state['height'] * .7, 650) + 1 for i in state['items']), 'Responsive image height cap ' + label)
            require(max(i['imageHeight'] for i in state['items'])-min(i['imageHeight'] for i in state['items'])<1, 'Mixed images share the same height '+label)
            require(all(i['imageWidth'] <= i['naturalWidth'] + 1 and i['imageHeight'] <= i['naturalHeight'] + 1 for i in state['items']), 'No unnecessary intrinsic-size enlargement ' + label)
            require(all(i['imageWidth']<=i['sourceWidth']+1 and i['imageHeight']<=i['sourceHeight']+1 for i in state['items']), 'Common height never enlarges source images '+label)
            require(all(not i['captionOverflow'] for i in state['items']) and len(state['items'][-1]['caption']) > 500, 'Complete long captions ' + label)
            if state['items'][0]['width'] + state['gap'] + state['items'][1]['width'] <= state['client'] - 2 * state['padding']:
                second = state['items'][1]
                require(second['left'] >= state['left'] and second['right'] <= state['right'], 'Next image fully visible when space allows ' + label)
            viewport = driver.find_element(By.CSS_SELECTOR, '#slider .githeme-gallery-slider__viewport')
            require(viewport.get_attribute('role') == 'group' and bool(viewport.get_attribute('aria-label')), 'Named scrollport ' + label)
            viewport.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
            time.sleep(.6)
            require(metrics()['focus'] and metrics()['outline'] != 'none' and float(metrics()['offset'].replace('px', '')) < 0, 'Keyboard focus visible inside scrollport ' + label)
            for _ in range(6):
                viewport.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
            time.sleep(.7)
            require(abs(metrics()['items'][0]['left'] - state['items'][0]['left']) > 2, 'Native keyboard scrolling without JavaScript ' + label)
            other = metrics('#second .githeme-gallery-slider__viewport')
            require(abs(other['items'][0]['left'] - (other['right'] - other['padding'] - other['items'][0]['width'] if rtl else other['left'] + other['padding'])) < 2, 'Other slider remains at start ' + label)
            # Deliberately offset the second item from its snap position. The
            # browser, not theme JavaScript, performs the subsequent snapping.
            driver.execute_script('''const v=arguments[0],i=v.querySelectorAll('.gallery-item')[1],r=v.getBoundingClientRect(),s=i.getBoundingClientRect(),rtl=getComputedStyle(v).direction==='rtl',p=parseFloat(getComputedStyle(v).paddingLeft);v.scrollBy({left:(rtl?s.right-r.right+p:s.left-r.left-p)+(rtl?-8:8),behavior:'auto'});''', viewport)
            time.sleep(.5)
            snapped = metrics()
            delta = snapped['items'][1]['right'] - snapped['right'] + snapped['padding'] if rtl else snapped['items'][1]['left'] - snapped['left'] - snapped['padding']
            require(abs(delta) < 2, 'Native proximity snap settles at item start ' + label, delta)
            viewport.send_keys(Keys.TAB)
            for _ in state['items']:
                inspect_link(viewport, label + '/Tab')
                driver.switch_to.active_element.send_keys(Keys.TAB)
            second_port = driver.find_element(By.CSS_SELECTOR, '#second .githeme-gallery-slider__viewport')
            if args.javascript:
                for _ in range(3):
                    if driver.switch_to.active_element == second_port: break
                    require(driver.switch_to.active_element.tag_name == 'button', 'Native button in gallery tab order '+label)
                    driver.switch_to.active_element.send_keys(Keys.TAB)
            require(driver.switch_to.active_element == second_port, 'Tab leaves slider without focus trap ' + label)
            if args.javascript:
                for _ in range(3):
                    driver.switch_to.active_element.send_keys(Keys.SHIFT + Keys.TAB)
                    if driver.execute_script('return arguments[0].contains(document.activeElement)&&document.activeElement.tagName==="A"',viewport): break
                inspect_link(viewport, label + '/ShiftTab')
                remaining = state['items'][1:]
            else:
                remaining = state['items']
            for _ in remaining:
                driver.switch_to.active_element.send_keys(Keys.SHIFT + Keys.TAB)
                inspect_link(viewport, label + '/ShiftTab')
            if args.javascript:
                check_manual(viewport, label)
            classic = driver.execute_script('return getComputedStyle(document.querySelector("#classic .gallery")).flexWrap')
            require(classic == 'wrap', 'Traditional gallery stays wrapping ' + label)
            require(not driver.find_elements(By.CSS_SELECTOR, '#single .githeme-gallery-slider'), 'Single image is static ' + label)
            require(driver.execute_script('return matchMedia("(prefers-reduced-motion: reduce)").matches') and state['behavior'] == 'auto', 'Reduced motion ' + label)
            require(not driver.find_elements(By.CSS_SELECTOR, '.gallery [aria-hidden]') and len(driver.find_elements(By.TAG_NAME,'script')) == (1 if args.javascript else 0), 'No hidden slides; only expected enhancement script ' + label)
            if not args.javascript:
                require(not driver.find_elements(By.TAG_NAME,'button'), 'No inactive controls without JavaScript '+label)
            else:
                check_buttons(viewport,label)
            # The native fragment was exported from a real, read-only shortcode
            # render. Only presentation takes place in this file fixture.
            native = driver.find_element(By.CSS_SELECTOR, '#native .githeme-gallery-slider__viewport')
            native.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
            native_state = metrics('#native .githeme-gallery-slider__viewport')
            check_geometry(native_state, 'Exported core HTML ' + label)
            for case in ['covers-two','covers-many','landscape','squares','small','panorama']:
                selector = '#' + case + ' .githeme-gallery-slider__viewport'
                WebDriverWait(driver,10).until(lambda d: d.execute_script('return [...document.querySelector(arguments[0]).querySelectorAll("img")].every(i=>i.complete&&i.naturalWidth>0)',selector))
                sample = metrics(selector)
                samples.append({'case':label+'/'+case,**sample})
                check_geometry(sample,label+'/'+case)
                if args.javascript:
                    count=len(driver.find_element(By.CSS_SELECTOR,selector).find_element(By.XPATH,'..').find_elements(By.TAG_NAME,'button'))
                    require(count==(2 if sample['scroll']>sample['client']+1 else 0), 'Controls exist only for overflowing components '+label+'/'+case)
                require(all(abs(i['natural']/i['ratio']-1)<.01 and i['imageWidth']<=i['naturalWidth']+1 and i['imageHeight']<=min(sample['height']*.7,650)+1 and not i['captionOverflow'] for i in sample['items']), 'Case proportions/captions/intrinsic sizes '+label+'/'+case)
                if case=='small':
                    require(sample['scroll']==sample['client'],'Small sequence entirely visible without scrolling '+label)
                if case=='covers-two' and width>=768:
                    require(sample['scroll']==sample['client'],'Two vertical covers fit together '+label)
            if width in [1440, 320]:
                driver.execute_script('const v=arguments[0];v.scrollLeft=0;window.scrollTo(0,v.getBoundingClientRect().top+scrollY-30)', viewport)
                time.sleep(.2)
                driver.save_screenshot(str(run / (label.replace('/', '-') + '.png')))
                if args.compare_fixtures and not rtl:
                    previous_css = json.loads(args.compare_fixtures.read_text())['fixtures']['css']
                    driver.execute_script('document.querySelector("style").textContent=arguments[0]',previous_css)
                    time.sleep(.2)
                    driver.save_screenshot(str(run / ('before-'+str(width)+'.png')))
                    driver.execute_script('document.querySelector("style").textContent=arguments[0]',fixtures['css'])
    # Exercise the absolute cap branch too: the usual 900px viewport uses 70vh.
    driver.browsing_context.set_viewport(context=driver.current_window_handle, viewport={'width': 1440, 'height': 1200})
    time.sleep(.2)
    tall = metrics('#large-squares .githeme-gallery-slider__viewport')
    require(abs(tall['items'][1]['imageHeight'] - 650) < 1 and all(i['imageHeight'] <= 651 for i in tall['items']), '650px maximum on a tall viewport', tall)
    # A widget-like narrow component on a wide page, without changing any widget.
    driver.execute_script('document.querySelector("#slider .githeme-gallery-slider").style.maxWidth="14rem"')
    time.sleep(.2)
    narrow = metrics()
    require(narrow['client'] <= 224 and narrow['pageScroll'] == 1440, 'Narrow component without page overflow', narrow)
    require(all(i['imageWidth'] <= i['width'] + 1 and i['imageHeight'] <= 651 and abs(i['natural'] / i['ratio'] - 1) < .01 for i in narrow['items']), 'Image constraints in a narrow component', narrow)
    if args.page_url:
        for rtl in [False, True]:
            for width in [1440,768,390,320]:
                driver.browsing_context.set_viewport(context=driver.current_window_handle,viewport={'width':width,'height':900})
                driver.get(args.page_url)
                if rtl:
                    driver.execute_script('document.documentElement.dir="rtl"')
                ports = driver.find_elements(By.CSS_SELECTOR,'.githeme-gallery-slider__viewport')
                require(bool(ports),'Real page contains enhanced native gallery '+str(width))
                for index,port in enumerate(ports):
                    for image in port.find_elements(By.CSS_SELECTOR,'.gallery-icon img'):
                        driver.execute_script('arguments[0].scrollIntoView({block:"nearest",inline:"nearest"})',image)
                        WebDriverWait(driver,15).until(lambda d:image.get_property('complete') and image.get_property('naturalWidth')>0)
                    driver.execute_script('arguments[0].scrollLeft=0',port)
                    selector = '#'+port.get_attribute('id')
                    sample = metrics(selector)
                    samples.append({'case':'real-page/'+str(width)+'/'+str(index),**sample})
                    check_geometry(sample,'Real page '+str(width)+'/'+str(index))
                    require(all(abs(i['natural']/i['ratio']-1)<.02 and i['imageWidth']<=i['naturalWidth']+1 and i['imageHeight']<=min(sample['height']*.7,650)+1 and not i['captionOverflow'] for i in sample['items']),'Real page proportions, captions and image constraints '+str(width))
                    visible = [i for i in sample['items'] if i['left']>=sample['left']-1 and i['right']<=sample['right']+1]
                    if len(sample['items'])>=2 and sample['items'][0]['width']+sample['gap']+sample['items'][1]['width']<=sample['client']-2*sample['padding']:
                        require(len(visible)>=2,'Multiple real images visible when their measured widths fit '+str(width),len(visible))
                    if sample['scroll']>sample['client']+1:
                        port.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
                        time.sleep(.3)
                        for _ in range(6):port.send_keys(Keys.ARROW_LEFT if rtl else Keys.ARROW_RIGHT)
                        time.sleep(.5)
                        require(abs(metrics(selector)['items'][0]['left']-sample['items'][0]['left'])>2,'Real page native keyboard scrolling '+str(width))
                        require(metrics(selector)['focus'] and metrics(selector)['outline']!='none','Real page visible focus '+str(width))
                    require(len(driver.find_elements(By.CSS_SELECTOR,'script[src*="/assets/js/gallery-slider.js"]')) == 1, 'Real slider conditionally delivers one theme script ' + str(width))
                    port.send_keys(Keys.NULL)
                    links = port.find_elements(By.CSS_SELECTOR, '.gallery-icon a')
                    for _ in links:
                        driver.switch_to.active_element.send_keys(Keys.TAB)
                        inspect_link(port, 'Real/' + ('rtl/' if rtl else 'ltr/') + str(width) + '/Tab')
                    # Stay in the document: Tab after its last link can enter browser chrome.
                    for _ in links[1:]:
                        driver.switch_to.active_element.send_keys(Keys.SHIFT + Keys.TAB)
                        inspect_link(port, 'Real/' + ('rtl/' if rtl else 'ltr/') + str(width) + '/ShiftTab')
                    driver.execute_script('const v=arguments[0];v.scrollLeft=0;scrollTo(0,v.getBoundingClientRect().top+scrollY-40)',port)
                    time.sleep(.2)
                    driver.save_screenshot(str(run/('real-page-'+('rtl-' if rtl else 'ltr-')+str(width)+'-'+str(index)+'.png')))
except Exception as exc:
    failures.append(type(exc).__name__ + ': ' + str(exc))
    if driver:
        try:
            samples.append({'case':'failure','geometry':metrics(),'focus':driver.execute_script('const e=document.activeElement,r=e.getBoundingClientRect(),v=document.querySelector("#slider .githeme-gallery-slider__viewport");return {tag:e.tagName,left:r.left,right:r.right,width:r.width,focusVisible:e.matches(":focus-visible"),hasFocus:v.matches(":has(a:focus-visible)"),snap:getComputedStyle(v).scrollSnapType,hasSupported:CSS.supports("selector(:has(a))")};')})
            driver.save_screenshot(str(run / 'failure.png'))
        except Exception as exc:
            failures.append('Failure screenshot: ' + str(exc))
finally:
    for label, action in [('browser', lambda: driver.quit() if driver else None), ('driver', lambda: service.stop() if service else None), ('profile', profile.cleanup)]:
        try:
            action()
        except Exception as exc:
            failures.append(label + ': ' + str(exc))
    unexpected = [e for e in network if e['error'] or ((e['status'] or 0) >= 400 and not(e['path']=='/favicon.ico' and e['origin']=='https://githeme:8890' and e['status']==404))]
    if errors or unexpected:
        failures.append('JavaScript or network failures')
    (run / 'report.json').write_text(json.dumps({'scope': ('JS-enabled' if args.javascript else 'No-JS') + ' DOM fixtures and read-only real page; no persistent changes', 'checks': checks, 'samples': samples, 'failures': failures, 'js_errors': errors, 'network': network}, indent=2) + '\n')
    print(json.dumps({'artifacts': str(run), 'checks': len(checks), 'failures': failures, 'js_errors': errors, 'network_failures': unexpected}))
raise SystemExit(bool(failures))
