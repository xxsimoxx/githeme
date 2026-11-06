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

	navigation.classList.add('is-enhanced');
	const mobile = window.matchMedia('(max-width: 48rem)');
	let compact = false;
	const setExpanded = (expanded) => {
		toggle.setAttribute('aria-expanded', String(expanded));
		menu.hidden = compact && !expanded;
	};
	const positionDropdowns = () => {
		// Keep the top-level dropdown panel inside either viewport edge. Deeper
		// lists remain nested in that panel instead of creating off-screen flyouts.
		menu.querySelectorAll(':scope > li > ul').forEach((submenu) => {
			submenu.style.removeProperty('--submenu-offset');
			if (compact || !submenu.getClientRects().length) return;
			const bounds = submenu.getBoundingClientRect();
			const offset = Math.max(8 - bounds.left, Math.min(0, window.innerWidth - 8 - bounds.right));
			if (offset) submenu.style.setProperty('--submenu-offset', `${offset}px`);
		});
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
		const bounds = navigation.getBoundingClientRect();
		// scrollWidth includes open, absolutely positioned dropdowns. Only root
		// links determine whether the horizontal navigation itself fits.
		const overflowing = items.some((item) => {
			const link = item.querySelector(':scope > a');
			const rect = (link || item).getBoundingClientRect();
			return rect.left < bounds.left - 1 || rect.right > bounds.right + 1;
		});
		compact = mobile.matches || wrapped || belowBranding || overflowing;
		if (compact !== wasCompact) {
			items.forEach((item) => item.classList.remove('submenu-dismissed'));
		}
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
		positionDropdowns();
	};

	toggle.addEventListener('click', () => {
		setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
	});
	navigation.addEventListener('focusin', (event) => {
		const item = event.target.closest('#primary-menu > li');
		if (item && !item.contains(event.relatedTarget)) item.classList.remove('submenu-dismissed');
		positionDropdowns();
	});
	navigation.addEventListener('pointerover', (event) => {
		const item = event.target.closest('#primary-menu > li');
		if (item && !item.contains(event.relatedTarget)) {
			item.classList.remove('submenu-dismissed');
			positionDropdowns();
		}
	});
	document.addEventListener('keydown', (event) => {
		if (event.key !== 'Escape') return;
		if (compact) {
			if (navigation.contains(event.target) && toggle.getAttribute('aria-expanded') === 'true') {
				setExpanded(false);
				toggle.focus();
			}
			return;
		}
		// Dismiss hover/focus content without requiring the pointer to move.
		menu.querySelectorAll(':scope > li > ul').forEach((submenu) => {
			if (!submenu.getClientRects().length) return;
			const item = submenu.parentElement;
			if (submenu.contains(document.activeElement)) item.querySelector(':scope > a')?.focus();
			item.classList.add('submenu-dismissed');
			event.preventDefault();
		});
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
