# ClassicPress 2.8 controls-frame JavaScript API regression

Observed on local `fix/customizer-regressions`, commit `79193cbb98bb4bd4a286cc37cba1a221940396f0`. No core modification is included in this theme change.

## Minimal reproduction, independent of githeme

Open the authenticated Customizer with a theme using the core Site Identity section. In the **controls window**, run the customary public subscription:

```js
wp.customize('blogname', function (setting) {
    setting.bind(function (value) { console.log('Title changed'); });
});
```

Expected: the setting callback is available and remains subscribed when the title changes. Actual: `TypeError`, because `typeof wp.customize === 'object'`, not `'function'`.

A second issue affects the proxy's Value objects:

```js
const before = wp.customize.instance('blogname');
before.bind(function () { console.log('Title changed'); });
// Change Site Title through its control, without publishing.
console.log(before === wp.customize.instance('blogname'));
```

The UI path replaces the Value instead of updating the existing instance, so existing subscriptions are lost. Do not publish this reproduction; restore the input or leave without saving.

## Evidence and source

The authenticated browser probe used `githeme_color_text`, without publishing: `wp.customize` was an object; calling it threw TypeError; the initial Value was undefined; changing the input replaced the Value object; the previously registered callback ran zero times while the new Value contained the changed color. The input was restored before browser shutdown.

- `wp-admin/js/customize-controls-proxy.js`: lines 17–24 create an object and a no-op `bind`; lines 101–104 (`api.add`) replace the Value; the `_updatedControlsWatcher` setter calls that `add` path.
- `wp-admin/js/customize-controls.js`: native input events drive its internal publishing/preview state.
- The `ready` binder is visibly a no-op in source. The late browser-ready probe is **not** evidence about ready-event timing.

These are compatibility regressions of the public setting subscription contract. The internal proxy state, DOM structure, `_values`, `_updatedControlsWatcher` and preview messaging are not suitable replacement APIs for a theme.

## Interface summary

| Interface | Finding |
|---|---|
| PHP add_setting/add_control, render_content, link, enqueue | Working in the authenticated preview/publish cycle |
| Callable wp.customize(id, callback) | Missing; TypeError reproduced |
| Value get/set/bind surface | Present as a shim; UI subscriptions lose their object identity |
| wp.customize.bind readiness/event surface | No-op in the controls proxy source |
| control/section/panel collections | Objects in the proxy source, rather than the callable public collection interface |
| Standard DOM input/change on theme-owned fields | Working; used for progressive theme UI only |

## Theme boundary

The theme does not patch/polyfill `wp.customize` and does not subscribe to the incomplete proxy. Its native color-control subclass owns the input HTML and exposes it with `data-githeme-color`. PHP `WP_Customize_Control::link()` retains the standard setting binding; standard DOM `input`/`change` events update theme-owned informational markup. The native color-control type/enqueue and Coloris's existing public `data-coloris` opt-in retain the core picker. No selectors referring to the core's section layout, wrappers or picker internals are used in production JS.

This covers user interaction with these controls. Silent programmatic writes by third-party code without a DOM event cannot be observed reliably on this core; supporting arbitrary public setting subscriptions requires the core API regression to be resolved. A change to the internal proxy is deliberately not emulated here.

Public subscription contract reference: [The Customizer JavaScript API](https://developer.wordpress.org/themes/classic-themes/customize-api/the-customizer-javascript-api/). The theme uses public PHP controls and native DOM events; it does not claim the missing JavaScript contract is compatible.

## Additional browser diagnostic (not fixed here)

Rapid navigation/reloading while the Customizer lock refresh is in flight can log a fetch/network TypeError from `refreshLockState()` in `wp-admin/js/customize-controls.js` (catch near line 355). This was observed through BiDi during the tests; the theme scripts were not in its captured stack. Reproduction is timing-dependent: open the authenticated Customizer and leave/reload while the lock refresh request is pending. No PHP patch is proposed here. An uncaught network/fetch TypeError was also captured during initial navigation without a stack; its origin remains unconfirmed. The exact reason for the interrupted network request was not diagnosed. These are separate diagnostics, not evidence of a failure in the theme contrast calculation.
