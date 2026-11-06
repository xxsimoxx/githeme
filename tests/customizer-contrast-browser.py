"""Authenticated, local-only Selenium test. Source the external tools env.sh first.
No content writes, cookie export, credentials, personal profile or global config.
"""
import argparse
import uuid
import dataclasses
import hashlib
import re
import datetime
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlsplit, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

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
        if not isinstance(value, str):
            return '<unavailable-url>'
        u = urlsplit(value)
        if u.scheme not in ('http', 'https'):
            return u.scheme + ':' + ('blank' if value == 'about:blank' else '<local>')
        return u.scheme + '://' + (u.hostname or '') + (':' + str(u.port) if u.port else '') + u.path
    except ValueError:
        return '<invalid-url>'


def event_data(event):
    return event if isinstance(event, dict) else dataclasses.asdict(event) if dataclasses.is_dataclass(event) else vars(event)


# Only metadata is retained: no headers, bodies, cookies or query values.
preview_contexts = set()
completed_documents = []
network_events = []
navigation_events = []
leave_events = []
rejections = []
collection_failures = []
rejection_marker = 'githeme-rejection-' + uuid.uuid4().hex + ':'


def observe(callback, *args):
    # BiDi callbacks run on background threads; their failures must fail the test.
    try:
        callback(*args)
    except Exception as exc:
        collection_failures.append(error_info('collector-' + callback.__name__, exc))


def request_metadata(data):
    request = data.get('request') or {}
    raw = request.get('url') or ''
    query = parse_qs(urlsplit(raw).query, keep_blank_values=True)
    stable = sorted((k, v) for k, v in query.items() if k != 'customized')
    route = query.get('rest_route', [''])[0]
    return {'request': request.get('request'), 'method': request.get('method'),
            'destination': request.get('destination'), 'url': safe_url(raw),
            'query_keys': sorted(query),
            'target_identity': hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest(),
            'rest_route': route if re.fullmatch(r'/[A-Za-z0-9_./-]+', route) else None,
            'context': data.get('context'), 'navigation': data.get('navigation'),
            'redirect_count': data.get('redirectCount', data.get('redirect_count')),
            'timestamp': data.get('timestamp', 0)}


def capture_request(event):
    network_events.append({'kind': 'request', **request_metadata(event_data(event))})


def capture_headers(event):
    data = event_data(event)
    network_events.append({'kind': 'headers', 'status': data.get('response', {}).get('status', 0), **request_metadata(data)})


def capture_document(event):
    data = event_data(event)
    status = data.get('response', {}).get('status', 0)
    item = {'kind': 'response', 'status': status, **request_metadata(data)}
    network_events.append(item)
    if item['navigation'] and 200 <= status < 300:
        completed_documents.append(item)


def capture_navigation(event, kind):
    data = event_data(event)
    navigation_events.append({'kind': kind, 'context': data.get('context'),
        'navigation': data.get('navigation'), 'timestamp': data.get('timestamp', 0),
        'url': safe_url(data.get('url'))})


def capture_js(event, kind):
    data = event_data(event)
    message = str(data.get('text', ''))
    category = re.search(r'(?:Type|Reference|Syntax|Network|Abort|Range|Security)?Error', message)
    stack = data.get('stacktrace') or data.get('stack_trace') or {}
    frames = stack.get('callFrames', stack.get('call_frames', [])) if isinstance(stack, dict) else []
    source = data.get('source') or {}
    errors.append({'kind': kind, 'category': category.group() if category else 'unspecified',
        'context': source.get('context'), 'timestamp': data.get('timestamp', 0),
        'network_signature': message == 'TypeError: NetworkError when attempting to fetch resource.',
        'network_failure': 'fetch' in message.lower() or 'network' in message.lower(),
        'navigating': navigating, 'phase': results[-1]['test'] if results else 'startup',
        'frames': [{'path': urlsplit(f.get('url', '')).path,
                    'function': f.get('functionName', f.get('function_name')),
                    'line': f.get('lineNumber', f.get('line_number'))} for f in frames[:5]]})


def capture_console(event):
    data = event_data(event)
    text = data.get('text') or ''
    if text.startswith(rejection_marker):
        item = json.loads(text[len(rejection_marker):])
        require(set(item) == {'kind', 'timestamp', 'path'}, 'Unexpected rejection observer payload')
        require(item['kind'] == 'firefox-network-rejection', 'Unknown rejection observer event')
        rejections.append({**item, 'context': (data.get('source') or {}).get('context')})
    elif data.get('level') == 'error':
        capture_js(event, 'console_error')


def capture_fetch(event):
    data = event_data(event)
    fetch_failures.append({'error': str(data.get('errorText', data.get('error_text', 'unknown')))[:200],
                          'navigating': navigating, **request_metadata(data)})


def pending_fetches(context, timestamp):
    starts = {e['request']: e for e in network_events if e['kind'] == 'request' and
              e['context'] == context and e['timestamp'] <= timestamp}
    pending = []
    for key, start in starts.items():
        if start['destination'] not in ('', None):
            continue
        answered = any(e['request'] == key and e['context'] == context and e['timestamp'] <= timestamp and
                       (e['kind'] == 'response' or e['kind'] == 'headers' and not 300 <= e['status'] < 400)
                       for e in network_events)
        failed = any(e['request'] == key and e['context'] == context and e['timestamp'] <= timestamp for e in fetch_failures)
        if not answered and not failed:
            pending.append(key)
    return sorted(pending)


def navigate(url):
    global navigating
    context = driver.current_window_handle
    timestamp = int(time.time() * 1000)
    leave_events.append({'context': context, 'timestamp': timestamp,
        'from_url': safe_url(driver.current_url), 'to_url': safe_url(url),
        'pending_fetches': pending_fetches(context, timestamp)})
    navigating = True
    try:
        driver.get(url)
    finally:
        navigating = False


def same_origin(url):
    parsed, origin = urlsplit(url), urlsplit(site)
    return (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc)


def dashboard(url):
    return same_origin(url) and urlsplit(url).path in ('/wp-admin/', '/wp-admin/index.php')


def site_health_correlation(js, fetches):
    """Known core defect only with all four observed links; timing alone is not proof."""
    fetch_matches, js_matches = {}, {}
    used_rejections = set()
    route = '/wp-site-health/v1/tests/http-protocol-data'
    for cancelled in fetches:
        if cancelled.get('error') != 'NS_BINDING_ABORTED' or cancelled.get('method') != 'POST' or not same_origin(cancelled['url']):
            continue
        if cancelled.get('rest_route') != route and urlsplit(cancelled['url']).path != '/wp-json' + route:
            continue
        key, context, stamp = cancelled.get('request'), cancelled.get('context'), cancelled.get('timestamp', 0)
        starts = [e for e in network_events if e['kind'] == 'request' and e['request'] == key and
                  e['context'] == context and e['method'] == 'POST' and e['url'] == cancelled['url'] and
                  (e.get('rest_route') == route or urlsplit(e['url']).path == '/wp-json' + route) and
                  e['redirect_count'] == cancelled.get('redirect_count') and e['timestamp'] <= stamp]
        if not key or not context or not starts or not stamp:
            continue
        # A fetch Promise that already received final headers cannot be the
        # rejected pending Promise, even if its response body was later aborted.
        if any(e['kind'] in ('headers', 'response') and e['request'] == key and e['context'] == context and
               e['timestamp'] <= stamp and not 300 <= e['status'] < 400 for e in network_events):
            continue
        for leave in leave_events:
            if leave['context'] != context or not dashboard(leave['from_url']) or leave['to_url'] == leave['from_url']:
                continue
            if leave['pending_fetches'] != [key] or not starts[-1]['timestamp'] <= leave['timestamp'] <= stamp:
                continue
            # Verify the pending proof against network data as well as the action marker.
            if pending_fetches(context, leave['timestamp']) != [key]:
                continue
            exits = [e for e in navigation_events if e['kind'] == 'start' and e['context'] == context and
                     e['url'] == leave['to_url'] and leave['timestamp'] <= e['timestamp'] <= leave['timestamp'] + 2000 and
                     abs(e['timestamp'] - stamp) <= 1000]
            native = [(i, e) for i, e in enumerate(rejections) if i not in used_rejections and e['context'] == context and
                      e['path'] in ('/wp-admin/', '/wp-admin/index.php') and 0 <= e['timestamp'] - stamp <= 500]
            if not exits or len(native) != 1:
                continue
            number, rejection = native[0]
            used_rejections.add(number)
            proof = {'request': key, 'context': context, 'method': 'POST', 'route': route,
                     'request_timestamp': starts[-1]['timestamp'], 'leave_timestamp': leave['timestamp'],
                     'navigation_timestamp': exits[0]['timestamp'], 'cancel_timestamp': stamp,
                     'rejection_timestamp': rejection['timestamp']}
            fetch_matches[key] = proof
            paired = [i for i, error in enumerate(js) if error.get('category') == 'TypeError' and
                      error.get('network_signature') and error.get('context') == context and not error.get('frames') and
                      abs(error.get('timestamp', 0) - rejection['timestamp']) <= 100]
            if len(paired) == 1 and paired[0] not in js_matches:
                js_matches[paired[0]] = proof
            break
    return fetch_matches, js_matches


def preview_correlation(cancelled):
    """A distinct replacement request must finish and load the same preview iframe."""
    if (cancelled.get('error') != 'NS_BINDING_ABORTED' or cancelled.get('method') != 'GET' or
        cancelled.get('destination') != 'iframe' or not cancelled.get('request') or
        cancelled.get('context') not in preview_contexts or not cancelled.get('navigation') or
        not same_origin(cancelled['url']) or not cancelled.get('target_identity') or not cancelled.get('timestamp')):
        return None
    starts = [e for e in network_events if e['kind'] == 'request' and e['request'] == cancelled['request'] and
              e['context'] == cancelled['context'] and e['redirect_count'] == cancelled['redirect_count']]
    if not starts or not starts[-1]['timestamp'] or starts[-1]['timestamp'] > cancelled['timestamp']:
        return None
    for replacement in network_events:
        if (replacement['kind'] != 'request' or replacement['request'] == cancelled['request'] or
            replacement['context'] != cancelled['context'] or replacement['method'] != 'GET' or
            replacement['destination'] != 'iframe' or not replacement['navigation'] or
            replacement['url'] != cancelled['url'] or replacement['target_identity'] != cancelled['target_identity'] or
            replacement['timestamp'] <= starts[-1]['timestamp'] or
            abs(replacement['timestamp'] - cancelled['timestamp']) > 1000):
            continue
        responses = [e for e in network_events if e['kind'] == 'response' and e['request'] == replacement['request'] and
                     e['redirect_count'] == replacement['redirect_count'] and e['context'] == replacement['context'] and
                     e['navigation'] == replacement['navigation'] and e['url'] == replacement['url'] and
                     e['target_identity'] == replacement['target_identity'] and 200 <= e['status'] < 300 and
                     e['timestamp'] >= replacement['timestamp']]
        loaded = [e for e in navigation_events if e['kind'] == 'load' and e['context'] == replacement['context'] and
                  e['navigation'] == replacement['navigation'] and e['url'] == replacement['url'] and
                  any(response['timestamp'] <= e['timestamp'] for response in responses)]
        if responses and loaded:
            return {'cancelled_request': cancelled['request'], 'replacement_request': replacement['request'],
                    'context': cancelled['context'], 'cancelled_navigation': cancelled['navigation'],
                    'replacement_navigation': replacement['navigation'], 'cancel_timestamp': cancelled['timestamp'],
                    'replacement_timestamp': replacement['timestamp'], 'response_timestamp': responses[-1]['timestamp'],
                    'load_timestamp': loaded[-1]['timestamp'], 'url': replacement['url']}
    return None


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
    health_fetches, health_js = site_health_correlation(js, fetches)
    for failure in collection_failures:
        fatal.append({'source': 'collector', **failure})
    for item in http:
        url = urlsplit(item.get('url', site + item.get('path', '')))
        favicon = (url.scheme, url.netloc) == (origin.scheme, origin.netloc) and url.path == '/favicon.ico' and item['status'] == 404
        (known if favicon else fatal).append({'source': 'http', 'reason': 'known-favicon-404' if favicon else 'http-error', **item})
    for index, item in enumerate(js):
        lock_abort = item.get('navigating') and item.get('network_failure') and any(
            f.get('path') == '/wp-admin/js/customize-controls.js' and
            (f.get('function') or '').startswith('refreshLockState') for f in item.get('frames', []))
        health = health_js.get(index)
        reason = 'known-site-health-exit-rejection' if health else 'known-lock-refresh-navigation' if lock_abort else 'javascript-error'
        (known if lock_abort or health else fatal).append({'source': 'javascript', 'reason': reason, **item, **({'evidence': health} if health else {})})
    for item in fetches:
        url = urlsplit(item['url'])
        preview = preview_correlation(item)
        health = health_fetches.get(item.get('request'))
        reason = 'known-site-health-exit-cancellation' if health else 'replaced-preview-request' if preview else 'transport-error'
        (known if health or preview else fatal).append({'source': 'fetch', 'reason': reason, **item,
            **({'evidence': health or preview} if health or preview else {})})
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
    return {'fatal': fatal, 'known': known, 'logs': logs, 'errors': js, 'failed_http': http, 'fetch_failures': fetches, 'completed_documents': globals().get('completed_documents', []), 'preview_contexts': sorted(preview_contexts), 'network_events': network_events, 'navigation_events': navigation_events, 'leave_events': leave_events, 'rejections': rejections, 'collection_failures': collection_failures}


def finish_report(failures, js, http, fetches, offsets):
    report = {'fatal': [], 'known': [], 'errors': js, 'failed_http': http, 'fetch_failures': fetches, 'completed_documents': globals().get('completed_documents', []), 'preview_contexts': sorted(preview_contexts), 'network_events': network_events, 'navigation_events': navigation_events, 'leave_events': leave_events, 'rejections': rejections, 'collection_failures': collection_failures}
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
args = parser.parse_args()
root = Path(os.environ['CODEX_BROWSER_ROOT']).resolve()
require(os.path.ismount('/Volumes/Simo') and root.is_relative_to(Path('/Volumes/Simo')), 'Check failed at original line 27')
require(Path(os.environ['TMPDIR']).resolve() == root / 'tmp', 'Check failed at original line 28')
site = args.url.rstrip('/')
u = urlsplit(site)
require(u.scheme == 'https' and not u.username and not u.password, 'Check failed at original line 31')
require(all(ipaddress.ip_address(a[4][0]).is_loopback for a in socket.getaddrinfo(u.hostname, u.port or 443)), 'Check failed at original line 32')
os.umask(0o077)
lock = (root / 'tmp/browser.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
run = root / 'artifacts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-live-contrast')
run.mkdir(mode=0o700)
profile_js_initial = profile_scripting_state()
(run / 'original-profile-javascript.json').write_text(json.dumps(profile_js_initial, indent=2))
wp = ['wp', '--path=' + str(Path(args.wp_path).resolve())]

def cli(code):
    return subprocess.run(wp + ['eval', code], capture_output=True, text=True, check=True, timeout=60).stdout.strip()

def php_json(data):
    return "json_decode('" + json.dumps(data).replace('\\', '\\\\').replace("'", "\\'") + "',true)"

require(cli("echo get_stylesheet();") == 'githeme', 'Wrong active theme')
protocol_options = json.loads(cli("$names=array('theme_mods_githeme');foreach(get_users(array('fields'=>'ID')) as $id){$names[]='_transient_cp_http_protocol_'.$id;$names[]='_transient_timeout_cp_http_protocol_'.$id;}echo wp_json_encode($names);"))
snapshot = snapshot_options(protocol_options)
verify_options(snapshot)
changesets = []
guard_code = "global $wpdb;$posts=$wpdb->get_results(\"SELECT * FROM {$wpdb->posts} WHERE post_type='customize_changeset' ORDER BY ID\",ARRAY_A);$meta=$wpdb->get_results(\"SELECT m.* FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID=m.post_id WHERE p.post_type='customize_changeset' ORDER BY m.meta_id\",ARRAY_A);echo hash('sha256',serialize(array($posts,$meta,get_option('sidebars_widgets'),get_option('nav_menu_options'),get_option('show_on_front'),get_option('page_on_front'),get_option('page_for_posts'),get_option('active_plugins'))));"
guard_hash = cli(guard_code)
results = []
errors = []
http_failures = []
driver = None
service = None
failures=[];fetch_failures=[];navigating=False

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
    changeset = str(uuid.uuid4())
    require(cli("$p=get_page_by_path(" + php_json(changeset) + ",OBJECT,'customize_changeset');echo $p?'EXISTS':'NEW';") == 'NEW', 'Changeset already exists')
    changesets.append(changeset)
    navigate(site + '/wp-admin/customize.php?customize_changeset_uuid=' + changeset)
    driver.find_element(By.CSS_SELECTOR, '#accordion-section-colors a').click()
    WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, 'githeme-contrast-panel').get_attribute('data-githeme-enhanced') == 'true')
    # Identify the actual preview iframe through BiDi, not a guessed URL rule.
    source = safe_url(driver.find_element(By.CSS_SELECTOR, '#customize-preview iframe').get_attribute('src'))
    def identify_preview(browser):
        tree = browser.browsing_context.get_tree(max_depth=1, root=browser.current_window_handle)
        matches = [child.context for parent in tree for child in (parent.children or []) if safe_url(child.url) == source]
        if len(matches) == 1:
            preview_contexts.update(matches)
            return True
        return False
    WebDriverWait(driver, 15).until(identify_preview)


def response(event):
    capture_headers(event)
    data = event_data(event)
    url = urlsplit(data.get('request', {}).get('url', ''))
    status = data.get('response', {}).get('status', 0)
    if status >= 400:
        http_failures.append({'url': safe_url(data.get('request', {}).get('url', '')), 'status': status})

log_offsets={p:p.stat().st_size for p in [Path('/Applications/MAMP/logs/php_error.log'),Path('/Applications/MAMP/logs/apache_error.log')] if p.exists()}
try:
    options = webdriver.FirefoxOptions()
    options.binary_location = '/Applications/Firefox.app/Contents/MacOS/firefox'
    options.enable_bidi = True
    options.set_preference('javascript.enabled', True)
    options.accept_insecure_certs = False
    options.add_argument('-profile')
    options.add_argument(str(root / 'profiles/firefox'))
    options.set_preference('browser.cache.disk.parent_directory', str(root / 'cache/firefox'))
    service = Service(executable_path=str(root / 'drivers/geckodriver'), service_args=['--host', '127.0.0.1', '--profile-root', str(root / 'tmp/driver-profiles'), '--log', 'fatal'], log_output=os.devnull, env=os.environ.copy())
    driver = webdriver.Firefox(options=options, service=service)
    require(Path(driver.capabilities['moz:profile']).resolve() == root / 'profiles/firefox', 'Check failed at original line 93')
    require(not driver.capabilities['acceptInsecureCerts'], 'Check failed at original line 94')
    listeners = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', ','.join(map(str, [service.process.pid, driver.capabilities['moz:processID']])), '-iTCP', '-sTCP:LISTEN'], capture_output=True, text=True).stdout.splitlines()[1:]
    require(listeners and all('127.0.0.1:' in row or '[::1]:' in row for row in listeners), 'Check failed at original line 96')
    driver.script.add_javascript_error_handler(lambda event: observe(capture_js, event, 'javascript_error'))
    driver.script.add_console_message_handler(lambda event: observe(capture_console, event))
    driver.network.add_event_handler('before_request_sent', lambda event: observe(capture_request, event))
    driver.network.add_event_handler('response_started', lambda event: observe(response, event))
    driver.network.add_event_handler('fetch_error', lambda event: observe(capture_fetch, event))
    driver.network.add_event_handler('response_completed', lambda event: observe(capture_document, event))
    driver.browsing_context.add_event_handler('navigation_started', lambda event: observe(capture_navigation, event, 'start'))
    driver.browsing_context.add_event_handler('load', lambda event: observe(capture_navigation, event, 'load'))
    # Passive observer only: never wrap fetch(), cancel events or change Promise handling.
    driver.script.add_preload_script(function_declaration="""() => {
        addEventListener('unhandledrejection', event => {
            const reason = event.reason;
            if (reason instanceof TypeError && reason.message === 'NetworkError when attempting to fetch resource.') {
                console.debug(__MARKER__ + JSON.stringify({kind: 'firefox-network-rejection', timestamp: Date.now(), path: location.pathname}));
            }
        });
    }""".replace('__MARKER__', json.dumps(rejection_marker)))
    driver.set_page_load_timeout(30)
    driver.set_window_rect(width=1440, height=1100)
    navigate(site + '/wp-admin/')
    require(driver.execute_script("return !!document.querySelector('body.wp-admin #adminmenu')"), 'Check failed at original line 113')
    open_colors()
    origin = driver.execute_script('return performance.timeOrigin')
    require(driver.find_element(By.CSS_SELECTOR, '[data-githeme-live]').get_attribute('textContent') == '', 'Check failed at original line 116')
    record('initial-panel',rows=state(),api_type=driver.execute_script('return typeof wp.customize'))
    # Parse a fresh server response without executing its scripts: PHP fallback.
    fallback = driver.execute_async_script("const done=arguments[0];fetch(location.href).then(r=>r.text()).then(html=>{const d=new DOMParser().parseFromString(html,'text/html'),p=d.querySelector('#githeme-contrast-panel');done({rows:p.querySelectorAll('[data-githeme-contrast-row]').length,help:p.querySelector('[data-githeme-update-help]').textContent,live:p.querySelector('[data-githeme-live]').textContent});}).catch(()=>done(null));")
    require(fallback and fallback['rows'] == len(state()) == 7 and fallback['live'] == '', 'Seven server-rendered contrast pairs, including header and footer')
    record('server-fallback',**fallback)
    for background, text, expected in [('#ffffff','#eaf5af','fail'),('#ffffff','#000000','pass'),('#000000','#000000','fail'),('#000000','#ffffff','pass')]:
        change('background', background)
        change('text', text)
        rows = state()
        require(rows[0]['status'] == expected, 'Check failed at original line 126')
        require(driver.execute_script('return document.activeElement === arguments[0]', field('text')), 'Check failed at original line 127')
        require(driver.execute_script('return performance.timeOrigin') == origin, 'Check failed at original line 128')
        record('live-text',text=text,background=background,rows=rows,focus_retained=True,no_reload=True)
    change('link','#000000')
    require(state()[1]['status'] == 'fail', 'Check failed at original line 131')
    change('link','#ffffff')
    require(state()[1]['status'] == 'pass', 'Check failed at original line 133')
    for primary, foreground in [('#ffffff','#000000'),('#000000','#ffffff')]:
        change('primary',primary)
        rows=state()
        require(rows[2]['status']=='pass' and foreground in rows[2]['pair'], 'Check failed at original line 137')
        record('automatic-button',primary=primary,rows=rows)
    # Typing an invalid value does not substitute a guessed contrast or NaN.
    change('text','#zzzzzz')
    require(state()[0]['status']=='invalid', 'Check failed at original line 141')
    record('invalid-input',rows=state())
    change('background','#ffffff');change('link','#14569a');change('primary','#14569a');change('text','#202833')
    time.sleep(1)
    # Observe only the theme live region, never user data or the core proxy.
    driver.execute_script("window.githemeAnnouncements=[];window.githemeObserver=new MutationObserver(()=>{githemeAnnouncements.push(document.querySelector('[data-githeme-live]').textContent);});githemeObserver.observe(document.querySelector('[data-githeme-live]'),{childList:true,subtree:true,characterData:true});")
    driver.execute_async_script("const input=arguments[0],done=arguments[1];let i=0;const timer=setInterval(()=>{input.value='#'+(0x202833+i*0x030301).toString(16).padStart(6,'0');input.dispatchEvent(new Event('input',{bubbles:true}));i++;if(i===20){clearInterval(timer);done();}},30);",field('text'))
    time.sleep(1)
    announcements=driver.execute_script('return githemeAnnouncements.slice()')
    require(len(announcements)==1, 'Check failed at original line 150')
    driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",field('text'))
    time.sleep(0.9)
    require(driver.execute_script('return githemeAnnouncements.length')==1, 'Check failed at original line 153')
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
        require(after != before, 'Picker keyboard did not change the selected color')
        require(state()[0]['status']==check['status'] and after in state()[0]['pair'], 'Check failed at original line 169')
        record('picker-hue-keyboard',before=before,after=after,rows=state())
        sliders[0].send_keys(Keys.ESCAPE)
    else:
        record('picker-hue-keyboard',not_executed=True,reason='Picker slider has no interactive geometry',sliders_found=len(sliders))
    # Keyboard navigation from the owned input remains usable and visibly focused.
    element=field('text');element.click();element.send_keys(Keys.TAB)
    keyboard=driver.execute_script("const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,outline:s.outline,shadow:s.boxShadow,focusVisible:e.matches(':focus-visible'),inBody:e===document.body}")
    require(not keyboard['inBody'] and keyboard['focusVisible'], 'Check failed at original line 177')
    record('keyboard',**keyboard)
    # Low contrast stays publishable; verify preview, reload and persisted frontend.
    open_colors();change('background','#ffffff');change('text','#eaf5af');time.sleep(2)
    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR,'#customize-preview iframe'))
    preview_color=driver.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--color-text')")
    driver.switch_to.default_content()
    require(preview_color=='#eaf5af', 'Check failed at original line 184')
    panel=driver.find_element(By.ID,'githeme-contrast-panel')
    panel.screenshot(str(run/'contrast-panel.png'))
    driver.find_element(By.ID,'save').click()
    WebDriverWait(driver,20).until(lambda d:not d.find_element(By.ID,'save').is_enabled())
    open_colors()
    require(field('text').get_attribute('value')=='#eaf5af' and state()[0]['status']=='fail', 'Check failed at original line 190')
    navigate(site+'/')
    frontend_color=driver.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--color-text')")
    require(frontend_color=='#eaf5af', 'Check failed at original line 193')
    record('publish-persist',preview=preview_color,frontend=frontend_color,reloaded='#eaf5af',low_contrast_did_not_block=True)
except Exception as exc:
    failures.append(error_info('functional', exc))
finally:
    if driver is not None:
        attempt('browser-blank', lambda: navigate('about:blank'), failures)
        attempt('browser-quit', driver.quit, failures)
    if service is not None:
        attempt('driver-stop', service.stop, failures)
    for index, changeset in enumerate(changesets):
        def delete_changeset(changeset=changeset):
            require(cli("$p=get_page_by_path(" + php_json(changeset) + ",OBJECT,'customize_changeset');if($p&&!wp_delete_post($p->ID,true)){throw new Exception('Changeset cleanup failed');}echo 'OK';") == 'OK', 'Changeset cleanup failed')
        attempt('delete-test-changeset-' + str(index), delete_changeset, failures)
    for name, saved in snapshot.items():
        attempt('restore-option-' + name, lambda name=name, saved=saved: restore_option(name, saved), failures)
    exact = attempt('verify-options', lambda: verify_options(snapshot), failures)
    unchanged = attempt('verify-existing-data', lambda: require(cli(guard_code) == guard_hash, 'Preexisting changesets or protected configuration changed'), failures)
    attempt('record-restoration', lambda: record('restoration', exact=exact, preexisting_data_unchanged=unchanged), failures)
    attempt('restore-profile-javascript', lambda: restore_profile_scripting(failures), failures)
    attempt('verify-profile-javascript', lambda: require(profile_scripting_state() == profile_js_initial, 'Profile JavaScript preference was not restored'), failures)
    finish_report(failures, errors, http_failures, fetch_failures, log_offsets)
