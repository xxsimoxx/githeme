/** Run: PHP_BINARY=/path/to/php8.2 node tests/i18n.js. No CMS bootstrap or database. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const theme = path.resolve(__dirname, '..');
const data = JSON.parse(execFileSync(process.env.PHP_BINARY || 'php', ['-r', `
define('ABSPATH', '/unused/');
$hooks = array();
function add_action($hook, $callback, ...$args) { $GLOBALS['hooks'][$hook][] = $callback; }
function __($text, $domain) {
    if ('githeme' !== $domain) { throw new RuntimeException('Incorrect text domain'); }
    return $text;
}
function get_template_directory() { return $GLOBALS['argv'][1]; }
function load_theme_textdomain($domain, $directory) { $GLOBALS['loaded'] = array($domain, $directory); }
function add_theme_support(...$args) {}
function register_nav_menus(...$args) {}
function add_editor_style(...$args) {}
function add_query_arg(...$args) { return ''; }
function get_template_directory_uri() { return ''; }
function get_template() { return 'githeme'; }
function wp_get_theme(...$args) { return new class { function get($field) { return '0.5.0'; } }; }
require $argv[1] . '/inc/setup.php';
require $argv[1] . '/inc/customizer.php';
githeme_setup();
echo json_encode(array('strings' => githeme_contrast_strings(), 'loaded' => $loaded, 'setup' => $hooks['after_setup_theme']));
`, theme], { encoding: 'utf8' }));
let checks = 0;
function equal(actual, expected) { assert.deepEqual(actual, expected); ++checks; }
equal(data.loaded, ['githeme', path.join(theme, 'languages')]);
equal(data.setup, ['githeme_setup']);
const pot = fs.readFileSync(path.join(theme, 'languages/githeme.pot'), 'utf8');
for (const text of [...Object.values(data.strings), 'GiTheme – Featured Posts', 'GiTheme – Gallery Slider', 'Image attachment IDs', 'Show tagline', 'Hide page title', 'Skip to content', 'Page not found', 'Previous image', 'Next image', 'Scrollable image gallery']) {
    equal(pot.includes('msgid ' + JSON.stringify(text)), true);
}

// Exercise the actual controls-pane script with translated message templates.
function scenario(reordered) {
    const handlers = {}, timers = [];
    const strings = { ...data.strings };
    if (reordered) {
        strings.summary = '%3$s | %2$s | %1$s';
        strings.ratio = 'minimum %2$s:1; ratio %1$s:1';
        strings.text = 'Text $& / background'; // Replacement-string metacharacters are literal text.
    }
    const nodes = {};
    const node = selector => nodes[selector] || (nodes[selector] = { textContent: '' });
    const row = { dataset: { githemeContrastRow: 'text' }, querySelector: node };
    const panel = { dataset: {}, querySelector: node, querySelectorAll: () => [row] };
    const input = { value: '#000', dataset: { githemeColor: 'text' }, addEventListener: (name, handler) => { handlers[name] = handler; } };
    let invalid = false;
    const window = {
        githemeContrastConfig: { strings, rules: {}, defaults: {}, locale: 'en' },
        githemeCreateContrast: () => ({ report: () => ({ text: { ratio: invalid ? null : 21, minimum: 4.5, status: invalid ? 'invalid' : 'pass', foreground: '#000', background: '#fff' } }) })
    };
    const document = { readyState: 'complete', getElementById: () => panel, querySelectorAll: () => [input] };
    vm.runInNewContext(fs.readFileSync(path.join(theme, 'assets/js/customizer-contrast.js'), 'utf8'), {
        document, window, Intl, setTimeout: callback => { timers.push(callback); return timers.length; }, clearTimeout() {}
    });
    equal(node('[data-githeme-live]').textContent, ''); // No initial announcement.
    equal(panel.dataset.githemeEnhanced, 'true');
    equal(node('[data-githeme-ratio]').textContent, reordered ? 'minimum 4.5:1; ratio 21.00:1' : '21.00:1 · minimum 4.5:1');
    invalid = true;
    handlers.input();
    equal(node('[data-githeme-live]').textContent, ''); // Preserve deferred announcements.
    timers.shift()();
    equal(node('[data-githeme-live]').textContent, reordered
        ? strings.invalidHelp + ' | ' + strings.invalid + ' | ' + strings.text
        : strings.text + ': ' + strings.invalid + '. ' + strings.invalidHelp);
    equal(node('[data-githeme-status]').textContent, strings.invalid);
    equal(node('[data-githeme-pair]').textContent, '');
}
scenario(false);
scenario(true);
console.log(`${checks} i18n assertions passed. No site state changed.`);
