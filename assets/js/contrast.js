/* WCAG sRGB calculation. Constants come only from githeme_contrast_rules(). */
(function (root, factory) {
 'use strict';
 if (typeof module === 'object' && module.exports) { module.exports = factory; }
 else { root.githemeCreateContrast = factory; }
}(typeof globalThis !== 'undefined' ? globalThis : this, function (rules) {
 'use strict';
 function channels(value) {
  if (typeof value !== 'string' || ![4, 7].includes(value.length) || !/^#(?:[a-f0-9]{3}|[a-f0-9]{6})$/i.test(value)) { return null; }
  let hex = value.slice(1);
  if (hex.length === 3) { hex = hex.split('').map(c => c + c).join(''); }
  return [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16));
 }
 function luminance(value) {
  const rgb = channels(value);
  if (!rgb) { return null; }
  return rgb.map(c => {
   c /= rules.channelMax;
   return c <= rules.breakpoint ? c / rules.divisor : Math.pow((c + rules.offset) / rules.scale, rules.gamma);
  }).reduce((sum, c, i) => sum + c * rules.weights[i], 0);
 }
 function ratio(first, second) {
  const a = luminance(first), b = luminance(second);
  return a === null || b === null ? null : (Math.max(a, b) + rules.flare) / (Math.min(a, b) + rules.flare);
 }
 function buttonTextColor(background) {
  if (!channels(background)) { return null; }
  return ratio(background, '#000000') >= ratio(background, '#ffffff') ? '#000000' : '#ffffff';
 }
 function report(colors) {
  const pairs = {text: [colors.text, colors.background], link: [colors.link, colors.background], button: [buttonTextColor(colors.primary), colors.primary], header_text: [colors.text, colors.header_background], header_link: [colors.link, colors.header_background], footer_text: [colors.text, colors.footer_background], footer_link: [colors.link, colors.footer_background]};
  const result = {};
  Object.keys(pairs).forEach(key => {
   const pair = pairs[key], value = ratio(pair[0], pair[1]);
   result[key] = {ratio: value, minimum: rules.normalTextMinimum, status: value === null ? 'invalid' : (value >= rules.normalTextMinimum ? 'pass' : 'fail'), foreground: pair[0] === undefined ? null : pair[0], background: pair[1] === undefined ? null : pair[1]};
  });
  return result;
 }
 return {channels, luminance, ratio, buttonTextColor, report};
}));
