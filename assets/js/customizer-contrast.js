/* Progressive controls-pane UI. Only theme-owned markup and native DOM events. */
(function () {
	'use strict';
	function init() {
		const panel = document.getElementById('githeme-contrast-panel');
		const config = window.githemeContrastConfig;
		if (!panel || !config || typeof window.githemeCreateContrast !== 'function') { return; }
		const fields = Array.from(document.querySelectorAll('input[data-githeme-color]'));
		if (!fields.length) { return; }
		const model = window.githemeCreateContrast(config.rules);
		const strings = config.strings;
		const live = panel.querySelector('[data-githeme-live]');
		const rows = Array.from(panel.querySelectorAll('[data-githeme-contrast-row]'));
		const ratioFormat = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
		const minimumFormat = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 1});
		let timer, previous = {}, lastAnnounced = {};
		function format(template, first, second) { return template.replace('%1$s', first).replace('%2$s', second); }
		function text(node, value) { if (node.textContent !== value) { node.textContent = value; } }
		function render(announce) {
			const colors = {};
			fields.forEach(input => {
				const key = input.dataset.githemeColor;
				// Empty means the explicit setting default, matching PHP sanitization.
				colors[key] = input.value === '' ? config.defaults[key] : input.value;
			});
			const report = model.report(colors), summaries = {};
			rows.forEach(row => {
				const key = row.dataset.githemeContrastRow, result = report[key];
				const ratio = result.ratio === null ? strings.invalidHelp : format(strings.ratio, ratioFormat.format(result.ratio), minimumFormat.format(result.minimum));
				row.dataset.status = result.status;
				text(row.querySelector('[data-githeme-status]'), strings[result.status]);
				text(row.querySelector('[data-githeme-icon]'), result.status === 'pass' ? '✓' : (result.status === 'fail' ? '!' : '?'));
				text(row.querySelector('[data-githeme-ratio]'), ratio);
				text(row.querySelector('[data-githeme-pair]'), result.ratio === null ? '' : format(strings.pair, result.foreground, result.background));
				summaries[key] = strings[key] + ': ' + strings[result.status] + '. ' + ratio;
			});
			const changed = Object.keys(summaries).some(key => summaries[key] !== previous[key]);
			previous = summaries;
			if (!announce) { lastAnnounced = summaries; return; }
			if (!changed) { return; }
			clearTimeout(timer);
			timer = setTimeout(() => {
				const updates = Object.keys(previous).filter(key => previous[key] !== lastAnnounced[key]).map(key => previous[key]);
				if (updates.length) { text(live, updates.join(' ')); }
				lastAnnounced = previous;
			}, 750);
		}
		render(false); // Never announce the whole panel on initial load.
		text(panel.querySelector('[data-githeme-update-help]'), strings.liveHelp);
		fields.forEach(input => {
			input.addEventListener('input', () => render(true));
			input.addEventListener('change', () => render(true));
		});
		panel.dataset.githemeEnhanced = 'true';
	}
	if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
	else { init(); }
}());
