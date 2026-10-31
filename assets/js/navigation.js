/** Progressive enhancement: the entire menu remains visible without JavaScript. */
(() => {
	'use strict';

	const navigation = document.querySelector('.primary-navigation');
	if (!navigation) return;
	const toggle = navigation.querySelector('.menu-toggle');
	const menu = navigation.querySelector('#primary-menu');
	if (!toggle || !menu) return;

	const mobile = window.matchMedia('(max-width: 48rem)');
	const setExpanded = (expanded) => {
		toggle.setAttribute('aria-expanded', String(expanded));
		menu.hidden = mobile.matches && !expanded;
	};
	const synchronize = () => {
		// Keep focus on a visible control when crossing the breakpoint.
		if (mobile.matches && menu.contains(document.activeElement)) {
			toggle.hidden = false;
			toggle.focus();
		} else if (!mobile.matches && document.activeElement === toggle) {
			menu.hidden = false;
			menu.querySelector('a')?.focus();
		}
		toggle.hidden = !mobile.matches;
		setExpanded(false);
	};
	toggle.addEventListener('click', () => {
		setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
	});
	navigation.addEventListener('keydown', (event) => {
		if (event.key === 'Escape' && mobile.matches && toggle.getAttribute('aria-expanded') === 'true') {
			setExpanded(false);
			toggle.focus();
		}
	});
	mobile.addEventListener('change', synchronize);
	synchronize();
})();
