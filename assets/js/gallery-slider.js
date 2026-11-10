/** Keep focused gallery images horizontally visible without controlling native scrolling. */
(() => {
	'use strict';

	document.addEventListener('focusin', (event) => {
		if (!(event.target instanceof Element)) return;
		const link = event.target.closest('.gallery-icon a');
		const viewport = link?.closest('.githeme-gallery-slider__viewport');
		const image = link?.querySelector('img');
		if (!viewport || !image) return;

		requestAnimationFrame(() => {
			if (document.activeElement !== link || !viewport.isConnected || !image.isConnected) return;
			const bounds = viewport.getBoundingClientRect();
			const picture = image.getBoundingClientRect();
			const left = bounds.left + viewport.clientLeft;
			const right = left + viewport.clientWidth;
			if (!viewport.clientWidth || !picture.width) return;

			// Physical rectangle differences work in either direction without
			// assuming an origin or positive range for RTL scrollLeft.
			const rtl = getComputedStyle(viewport).direction === 'rtl';
			const delta = picture.width > right - left
				? (rtl ? picture.right - right : picture.left - left)
				: picture.left < left - .5 ? picture.left - left
					: picture.right > right + .5 ? picture.right - right : 0;
			if (Math.abs(delta) > .5) viewport.scrollBy({ left: delta, behavior: 'instant' });
		});
	});

	function enhance(viewport) {
		const wrapper = viewport.closest('.githeme-gallery-slider');
		const images = [...viewport.querySelectorAll(':scope > .gallery > .gallery-item .gallery-icon img')];
		const labels = window.githemeGalleryLabels;
		if (!wrapper || images.length < 2 || !viewport.id || !labels?.previous || !labels?.next) return;
		let previous, next, pending = false, controlTop;

		function button(direction) {
			const element = document.createElement('button');
			element.type = 'button';
			element.className = 'githeme-gallery-slider__button githeme-gallery-slider__' + direction;
			element.setAttribute('aria-label', labels[direction]);
			element.setAttribute('aria-controls', viewport.id);
			const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
			svg.setAttribute('viewBox', '0 0 24 24');
			svg.setAttribute('aria-hidden', 'true');
			svg.setAttribute('focusable', 'false');
			const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
			path.setAttribute('d', direction === 'previous' ? 'm15 6-6 6 6 6' : 'm9 6 6 6-6 6');
			svg.append(path);
			element.append(svg);
			element.addEventListener('click', () => {
				if (element.getAttribute('aria-disabled') === 'true') return;
				const bounds = viewport.getBoundingClientRect();
				const left = bounds.left + viewport.clientLeft, right = left + viewport.clientWidth;
				const rtl = getComputedStyle(viewport).direction === 'rtl';
				const forward = direction === 'next';
				// Start from the corresponding edge, skipping fully visible images.
				const candidates = forward ? images : [...images].reverse();
				const image = candidates.find((candidate) => {
					const rect = candidate.getBoundingClientRect();
					const beyond = forward !== rtl ? rect.right > right + 1 : rect.left < left - 1;
					const leading = rtl ? rect.right - right : rect.left - left;
					return beyond && !(rect.width > viewport.clientWidth && Math.abs(leading) <= 1);
				});
				// An oversized final image already aligned at its start can still
				// be panned to its far edge, rather than leaving an inert next button.
				const rect = (image || (forward ? images[images.length - 1] : images[0])).getBoundingClientRect();
				const padding = parseFloat(getComputedStyle(viewport)[rtl ? 'scrollPaddingRight' : 'scrollPaddingLeft']) || 0;
				const delta = !image ? (forward !== rtl ? rect.right - right : rect.left - left)
					: rect.width > viewport.clientWidth
					? (rtl ? rect.right - right : rect.left - left)
					// Aim at the target's native start snap point. A minimal edge
					// delta can snap to a neighbour and leave the target clipped.
					: rtl ? rect.right - right + padding : rect.left - left - padding;
				viewport.scrollBy({ left: delta, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
				schedule();
			});
			element.addEventListener('blur', schedule);
			return element;
		}

		function disable(element, unavailable) {
			const value = String(unavailable);
			if (element.getAttribute('aria-disabled') !== value) element.setAttribute('aria-disabled', value);
			// Disabling the focused native button can discard keyboard focus.
			// Keep it focusable but inert until blur, then apply native disabled.
			const nativeDisabled = unavailable && document.activeElement !== element;
			if (element.disabled !== nativeDisabled) element.disabled = nativeDisabled;
		}

		function update() {
			pending = false;
			const focused = document.activeElement === previous || document.activeElement === next;
			if (viewport.scrollWidth <= viewport.clientWidth + 1 || !viewport.clientWidth) {
				if (previous && !focused) {
					previous.remove(); next.remove(); previous = next = undefined;
				} else if (previous) {
					disable(previous, true); disable(next, true);
				}
				return;
			}
			if (!previous) {
				previous = button('previous'); next = button('next');
				wrapper.append(previous, next);
			}
			const bounds = viewport.getBoundingClientRect(), left = bounds.left + viewport.clientLeft, right = left + viewport.clientWidth;
			const rtl = getComputedStyle(viewport).direction === 'rtl';
			const first = images[0].getBoundingClientRect(), last = images[images.length - 1].getBoundingClientRect();
			disable(previous, rtl ? first.right <= right + 1 : first.left >= left - 1);
			disable(next, rtl ? last.left >= left - 1 : last.right <= right + 1);
			// Center on the image row, not on potentially very long captions.
			const top = bounds.top - wrapper.getBoundingClientRect().top + viewport.clientTop
				+ parseFloat(getComputedStyle(viewport).paddingTop) + Math.max(...images.map(image => image.getBoundingClientRect().height)) / 2;
			if (top !== controlTop) {
				wrapper.style.setProperty('--githeme-gallery-control-top', top + 'px');
				controlTop = top;
			}
		}

		function schedule() {
			if (!pending) { pending = true; requestAnimationFrame(update); }
		}
		viewport.addEventListener('scroll', schedule, { passive: true });
		images.forEach(image => image.addEventListener('load', schedule));
		if ('ResizeObserver' in window) {
			const observer = new ResizeObserver(schedule);
			observer.observe(viewport);
			images.forEach(image => observer.observe(image));
		} else window.addEventListener('resize', schedule, { passive: true });
		update();
	}

	const initialize = () => document.querySelectorAll('.githeme-gallery-slider__viewport').forEach(enhance);
	if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
	else initialize();
})();
