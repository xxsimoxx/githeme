/* Run from any directory: node path/to/githeme/tests/contrast.js */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const theme = path.resolve(__dirname, '..');
const data = JSON.parse(execFileSync('wp', ['--path=' + path.resolve(theme, '../../..'), 'eval-file', path.join(__dirname, 'contrast.php'), 'json'], {encoding: 'utf8'}));
const model = require('../assets/js/contrast.js')(data.rules);
let assertions = 0;
function equal(a, b) { assert.deepEqual(a, b); assertions++; }
function close(a, b) { if (a === null || b === null) { equal(a, b); } else { assert.ok(Math.abs(a - b) < 1e-10); assertions++; } }
data.cases.forEach(c => {
 close(model.ratio(c.first, c.second), c.ratio);
 close(model.ratio(c.first, c.second), c.phpRatio);
 equal(model.ratio(c.first, c.second), model.ratio(c.second, c.first));
});
data.reports.forEach(c => {
 const actual = model.report(c.colors);
 equal(model.buttonTextColor(c.colors.primary), c.buttonText);
 Object.keys(actual).forEach(key => {
  close(actual[key].ratio, c.report[key].ratio);
  ['status', 'minimum', 'foreground', 'background'].forEach(field => equal(actual[key][field], c.report[key][field]));
 });
});
equal(model.report({text:'#777777',background:'#fff'}).text.status, 'fail');
equal(model.ratio(Infinity, '#fff'), null);
equal(model.ratio({}, '#fff'), null);
console.log(data.phpAssertions + ' PHP assertions and ' + assertions + ' JS/parity assertions passed. No settings saved.');
