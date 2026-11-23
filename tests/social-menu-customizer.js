/* Isolated execution of the local core's actual setting-event handler.
 * Run: node tests/social-menu-customizer.js
 * No browser/CMS bootstrap, settings writes, or production JavaScript changes.
 */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');

const php = process.env.GITHEME_TEST_PHP || '/Applications/MAMP/bin/php/php8.2.13/bin/php';
const fixtures = JSON.parse(execFileSync(php, [path.join(__dirname, 'social-menu.php'), '--json'], { encoding: 'utf8' }));
const coreOnly = JSON.parse(execFileSync(php, [path.join(__dirname, 'customizer-menu-settings.php')], { encoding: 'utf8' }));
const core = process.env.GITHEME_TEST_CORE || path.resolve(__dirname, '../../../..');
const source = fs.readFileSync(path.join(core, 'wp-includes/js/customize-preview.js'), 'utf8');
const start = source.indexOf("api.preview.bind( 'setting', function( args ) {");
const end = source.indexOf("api.preview.bind( 'sync',", start);
assert.ok(start >= 0 && end > start, 'Actual local core setting handler is available');
const handlerSource = source.slice(start, end);
let checks = 1;

function probe(settings, id, value) {
    const state = { refreshes: 0, fullRefreshes: 0, valueUpdates: 0, handler: null };
    const partial = {
        id: 'isolated-native-menu', params: { settings },
        refresh() { state.refreshes++; },
        placements() { return [{ context: { menu_id: 100 } }]; }
    };
    const sandbox = {
        window: {},
        api: { _settings: {}, preview: { bind(event, fn) { state.handler = fn; } } },
        setValue() { state.valueUpdates++; },
        wp: { customize: { selectiveRefresh: {
            partial: { each(fn) { fn(partial); } },
            requestFullRefresh() { state.fullRefreshes++; }
        } } }
    };
    vm.runInNewContext(handlerSource, sandbox, { filename: 'native-customize-setting-handler.js' });
    state.handler([id, value]);
    return state;
}

assert.ok(Array.isArray(fixtures.menu_partial_settings)); checks++;
const primary = probe(fixtures.menu_partial_settings, 'githeme_color_primary', '#123456');
assert.equal(primary.fullRefreshes, 1, 'Healthy native menu settings do not prevent the existing color refresh path'); checks++;
assert.equal(primary.valueUpdates, 1, 'Color preview value is updated'); checks++;
const assignment = probe(fixtures.menu_partial_settings, 'nav_menu_locations[social]', 101);
assert.ok(assignment.refreshes > 0, 'Existing Social placement takes the native partial update path'); checks++;
assert.equal(assignment.fullRefreshes, 0, 'Existing Social assignment does not demand full preview refresh in this handler'); checks++;
const item = probe(fixtures.menu_partial_settings, 'nav_menu_item[11]', { title: 'Call the team', url: 'tel:+1-202-555-0123', nav_menu_term_id: 100 });
assert.ok(item.refreshes > 0, 'Native handler dispatches menu item changes'); checks++;
assert.throws(() => probe({ default: 'githeme_color_primary' }, 'githeme_color_primary', '#123456'), /indexOf is not a function/, 'Malformed object reproduces the reported exception independently of theme registration'); checks++;
assert.doesNotThrow(() => probe('another_setting', 'githeme_color_primary', '#123456'), 'A JavaScript string alone does not explain this indexOf exception'); checks++;
assert.equal(coreOnly.theme_loaded, false, 'Core export diagnostic does not load GiTheme or Social'); checks++;
let malformedCoreExports = 0;
for (const [name, sample] of Object.entries(coreOnly.cases)) {
    if (Array.isArray(sample.export.settings)) {
        assert.doesNotThrow(() => probe(sample.export.settings, 'githeme_color_primary', '#123456'), name + ': list permits the native color-refresh path'); checks++;
    } else {
        assert.throws(() => probe(sample.export.settings, 'githeme_color_primary', '#123456'), /indexOf is not a function/, name + ': actual core export reproduces the exception without GiTheme'); checks++;
        malformedCoreExports++;
    }
}
console.log(JSON.stringify({ checks, malformedCoreExports, cause: malformedCoreExports ? 'Core explicit-menu partial exports a sparse settings array as a JSON object, independent of GiTheme' : 'Core test exports are all lists; legacy sparse-array defect not present in this checkout', liveOpaquePartialIdCaptured: false }));
