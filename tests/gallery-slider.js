/** Run with node tests/gallery-slider.js. No browser or CMS state is changed. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/js/gallery-slider.js'), 'utf8');
let checks = 0;
function scenario({ left, width, rtl = false, stale = false, connected = true, client = 300 }) {
	const frames = [], moves = [];
	let listener;
	class Element {}
	const image = { isConnected: true, getBoundingClientRect: () => ({ left, right: left + width, width }) };
	const viewport = { isConnected: connected, clientLeft: 0, clientWidth: client,
		getBoundingClientRect: () => ({ left: 100 }), scrollBy: (options) => moves.push(options) };
	const link = new Element();
	link.closest = () => viewport;
	link.querySelector = () => image;
	const target = new Element();
	target.closest = () => link;
	const document = { activeElement: link, querySelectorAll: () => [], addEventListener: (type, callback) => {
		assert.equal(type, 'focusin'); listener = callback;
	} };
	vm.runInNewContext(source, { document, window: {}, Element, getComputedStyle: () => ({ direction: rtl ? 'rtl' : 'ltr' }),
		requestAnimationFrame: (callback) => frames.push(callback) });
	listener({ target });
	assert.equal(frames.length, 1); ++checks;
	if (stale) document.activeElement = target;
	frames[0]();
	assert.equal(document.activeElement, stale ? target : link); ++checks;
	return moves;
}
for (const rtl of [false, true]) {
	for (const [left, width, expected] of [[120, 200, null], [350, 100, 50], [50, 200, -50], [100, 0, null]]) {
		const moves = scenario({ left, width, rtl });
		assert.equal(moves.length, expected === null ? 0 : 1); ++checks;
		if (expected !== null) {
			assert.equal(moves[0].left, expected); ++checks;
			assert.equal(moves[0].behavior, 'instant'); ++checks;
		}
	}
	const oversize = scenario({ left: -100, width: 600, rtl });
	assert.equal(oversize[0].left, rtl ? 100 : -200); ++checks;
}
assert.equal(scenario({ left: 350, width: 100, stale: true }).length, 0); ++checks;
assert.equal(scenario({ left: 350, width: 100, connected: false }).length, 0); ++checks;
assert.equal(scenario({ left: 350, width: 100, client: 0 }).length, 0); ++checks;
console.log(`${checks} gallery focus assertions passed.`);

// Exercise the actual controls with deterministic, variable-width DOM geometry.
for (const rtl of [false, true]) {
	let position = 0, client = 300, resize, reduced = true;
	const frames = [], moves = [];
	class Node {
		constructor() { this.attributes = {}; this.listeners = {}; this.children = []; this.disabled = false; this.isConnected = true; }
		setAttribute(k, v) { this.attributes[k] = v; }
		getAttribute(k) { return this.attributes[k]; }
		addEventListener(k, v) { this.listeners[k] = v; }
		append(...nodes) { nodes.forEach(n => { this.children.push(n); n.parent = this; }); }
		remove() { this.parent.children = this.parent.children.filter(n => n !== this); }
	}
	const wrapper = new Node(); wrapper.style = { setProperty() {} }; wrapper.getBoundingClientRect = () => ({ top: 0 });
	const widths = [100, 200, 150]; let start = 8;
	const images = widths.map(width => {
		const offset = start; start += width + 16;
		const image = new Node();
		image.getBoundingClientRect = () => ({ left: (rtl ? 400 - offset - width : 100 + offset) - position,
			right: (rtl ? 400 - offset : 100 + offset + width) - position, width, height: 150 });
		return image;
	});
	const viewport = new Node(); viewport.id = 'unit-gallery'; viewport.clientLeft = viewport.clientTop = 0;
	viewport.closest = () => wrapper; viewport.querySelectorAll = () => images;
	viewport.getBoundingClientRect = () => ({ left: 100, top: 0 });
	Object.defineProperties(viewport, { clientWidth: { get: () => client }, scrollWidth: { get: () => 498 } });
	viewport.scrollBy = options => { moves.push(options); position = rtl ? Math.max(-198, Math.min(0, position + options.left)) : Math.max(0, Math.min(198, position + options.left)); };
	const document = { readyState: 'complete', activeElement: viewport, querySelectorAll: () => [viewport],
		addEventListener() {}, createElement: () => new Node(), createElementNS: () => new Node() };
	const window = { githemeGalleryLabels: { previous: 'Previous image', next: 'Next image' }, addEventListener: (name, callback) => { resize = callback; } };
	vm.runInNewContext(source, { document, window, Element: Node, getComputedStyle: () => ({ direction: rtl ? 'rtl' : 'ltr', paddingTop: '8px', scrollPaddingLeft: '8px', scrollPaddingRight: '8px' }),
		requestAnimationFrame: callback => frames.push(callback), matchMedia: () => ({ matches: reduced }) });
	const flush = () => { while (frames.length) frames.shift()(); };
	const [previous, next] = wrapper.children;
	assert.equal(wrapper.children.length, 2); ++checks;
	assert.equal(previous.disabled, true); ++checks;
	assert.equal(next.getAttribute('aria-controls'), 'unit-gallery'); ++checks;
	assert.equal(next.getAttribute('aria-label'), 'Next image'); ++checks;
	document.activeElement = next;
	next.listeners.click(); flush();
	assert.equal(moves[0].left, rtl ? -116 : 116); ++checks;
	assert.equal(moves[0].behavior, 'instant'); ++checks;
	next.listeners.click(); flush();
	assert.equal(next.getAttribute('aria-disabled'), 'true'); ++checks;
	assert.equal(next.disabled, false); ++checks;
	const count = moves.length; next.listeners.click();
	assert.equal(moves.length, count); ++checks;
	document.activeElement = previous;
	previous.listeners.click(); flush(); previous.listeners.click(); flush();
	assert.equal(previous.getAttribute('aria-disabled'), 'true'); ++checks;
	assert.equal(previous.disabled, false); ++checks;
	document.activeElement = viewport; previous.listeners.blur(); flush();
	assert.equal(previous.disabled, true); ++checks;
	client = 1000; resize(); flush();
	assert.equal(wrapper.children.length, 0); ++checks;
	client = 300; resize(); flush();
	assert.equal(wrapper.children.length, 2); ++checks;
	const focused = wrapper.children[1]; document.activeElement = focused;
	client = 1000; resize(); flush();
	assert.equal(wrapper.children.length, 2); ++checks;
	assert.equal(focused.getAttribute('aria-disabled'), 'true'); ++checks;
	document.activeElement = viewport; focused.listeners.blur(); flush();
	assert.equal(wrapper.children.length, 0); ++checks;
	client = 300; reduced = false; resize(); flush();
	document.activeElement = wrapper.children[1]; wrapper.children[1].listeners.click();
	assert.equal(moves[moves.length - 1].behavior, 'smooth'); ++checks;
}
console.log(`${checks} total gallery focus/control assertions passed.`);

// Firefox regression: 352px common height, 720px scrollport, third/fourth snap tie.
for (const rtl of [false, true]) {
	let position = rtl ? -464 : 464, requested;
	const frames = [];
	class Node {
		constructor() { this.attributes = {}; this.listeners = {}; this.children = []; this.disabled = false; }
		setAttribute(k, v) { this.attributes[k] = v; }
		getAttribute(k) { return this.attributes[k]; }
		addEventListener(k, v) { this.listeners[k] = v; }
		append(...nodes) { this.children.push(...nodes); }
	}
	const wrapper = new Node(); wrapper.style = { setProperty() {} }; wrapper.getBoundingClientRect = () => ({ top: 0 });
	let offset = 8;
	const images = [704, 88, 352, 528, 704].map(width => {
		const start = offset; offset += width + 16;
		const image = new Node();
		image.getBoundingClientRect = () => ({ left: (rtl ? 744 - start - width : 24 + start) - position,
			right: (rtl ? 744 - start : 24 + start + width) - position, width, height: 352 });
		return image;
	});
	const viewport = new Node(); Object.assign(viewport, { id: 'regression', clientWidth: 720, scrollWidth: 2448, clientLeft: 0, clientTop: 0 });
	viewport.closest = () => wrapper; viewport.querySelectorAll = () => images;
	viewport.getBoundingClientRect = () => ({ left: 24, top: 0 });
	viewport.scrollBy = options => {
		requested = position + options.left;
		const points = [0, 720, 824, 1192, 1728].map(x => rtl ? -x : x);
		position = points.reduce((a, b) => Math.abs(b - requested) < Math.abs(a - requested) ? b : a);
	};
	const document = { readyState: 'complete', activeElement: viewport, querySelectorAll: () => [viewport], addEventListener() {},
		createElement: () => new Node(), createElementNS: () => new Node() };
	const window = { githemeGalleryLabels: { previous: 'Previous image', next: 'Next image' }, addEventListener() {} };
	vm.runInNewContext(source, { document, window, Element: Node, getComputedStyle: () => ({ direction: rtl ? 'rtl' : 'ltr', paddingTop: '8px', scrollPaddingLeft: '8px', scrollPaddingRight: '8px' }),
		requestAnimationFrame: callback => frames.push(callback), matchMedia: () => ({ matches: true }) });
	const next = wrapper.children[1]; document.activeElement = next; next.listeners.click();
	assert.equal(requested, rtl ? -1192 : 1192); ++checks;
	assert.equal(position, requested); ++checks;
	const target = images[3].getBoundingClientRect();
	assert.ok(target.left >= 24 && target.right <= 744); ++checks;
}
console.log(`${checks} total assertions including the 768px snap regression passed.`);
