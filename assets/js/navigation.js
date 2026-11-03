/** Progressive enhancement: the entire menu remains visible without JavaScript. */
(() => {
	'use strict';

	const navigation = document.querySelector('.primary-navigation');
	if (!navigation) return;
	const toggle = navigation.querySelector('.menu-toggle');
	const menu = navigation.querySelector('#primary-menu');
	const header = navigation.closest('.header-inner');
	const branding = header?.querySelector('.site-branding');
	if (!toggle || !menu || !header || !branding) return;

	const mobile = window.matchMedia('(max-width: 48rem)');
	let compact = false;
	const setExpanded = (expanded) => {
		toggle.setAttribute('aria-expanded', String(expanded));
		menu.hidden = compact && !expanded;
	};
	const synchronize = () => {
		const focused = document.activeElement;
		const wasCompact = compact;
		const wasExpanded = toggle.getAttribute('aria-expanded') === 'true';
		// Measure the existing desktop layout without duplicating the menu.
		navigation.classList.remove('is-compact');
		toggle.hidden = true;
		menu.hidden = false;
		const items = [...menu.children];
		const wrapped = items.some((item) => Math.abs(item.getBoundingClientRect().top - items[0].getBoundingClientRect().top) > 1);
		const stacked = document.body.classList.contains('githeme-header-stacked');
		const belowBranding = !stacked && navigation.getBoundingClientRect().top >= branding.getBoundingClientRect().bottom;
		compact = mobile.matches || wrapped || belowBranding || menu.scrollWidth > navigation.clientWidth;
		navigation.classList.toggle('is-compact', compact);
		toggle.hidden = !compact;
		const expanded = compact && wasCompact && wasExpanded;
		// Keep focus on a visible control when changing navigation mode.
		if (compact && !expanded && menu.contains(focused)) {
			toggle.focus();
		} else if (!compact && focused === toggle) {
			menu.querySelector('a')?.focus();
		}
		setExpanded(expanded);
	};

	toggle.addEventListener('click', () => {
		setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
	});
	navigation.addEventListener('keydown', (event) => {
		if (event.key === 'Escape' && compact && toggle.getAttribute('aria-expanded') === 'true') {
			setExpanded(false);
			toggle.focus();
		}
	});
	// Batch geometry checks outside ResizeObserver delivery. Measuring the desktop
	// layout temporarily changes dimensions; only the final layout is observed.
	let pending = false;
	const schedule = () => {
		if (pending) return;
		pending = true;
		window.requestAnimationFrame(() => {
			pending = false;
			synchronize();
		});
	};
	mobile.addEventListener('change', schedule);
	window.addEventListener('resize', schedule);
	if ('ResizeObserver' in window) {
		const observer = new ResizeObserver(schedule);
		observer.observe(header);
		observer.observe(branding);
		observer.observe(menu);
	}
	// Theme layout classes and inherited font variables can change while the
	// menu is hidden, when no menu resize notification is possible.
	const attributes = new MutationObserver(schedule);
	attributes.observe(document.body, { attributes: true, attributeFilter: ['class', 'style'] });
	attributes.observe(document.documentElement, { attributes: true, attributeFilter: ['style'] });
	document.fonts?.ready.then(schedule);
	document.fonts?.addEventListener('loadingdone', schedule);
	branding.querySelector('img')?.addEventListener('load', schedule);

	synchronize();
})();
