# Optional FX Shortcodes integration

The theme continues to work without the plugin. `githeme_enqueue_fx_shortcodes_style()` loads `assets/css/fx-shortcodes.css` only when the `fx-shortcodes` stylesheet is enqueued; dependencies are `githeme-style` and `fx-shortcodes`, on `wp_enqueue_scripts` at priority 20. No new Customizer options or calls to plugin APIs are required by the theme.

## Supported components

| Component | Integration |
|---|---|
| Button | Primary color and `--color-button-text`; hover/focus-visible fill and outline use the secondary color, with `--color-button-hover-text` calculated for contrast. Text remains transparent and without underline; its border becomes visible on hover. Focus keeps its own indicator. Sizes and variants are not rewritten. |
| Card | `--color-footer-background` background, inherited text, `--color-border` border, subtle corners, and shadow derived from `--color-text`. Plugin images and proportions are preserved. |
| Cover | Default `--color-background` background, inherited text, and responsive padding. The plugin retains control of structure, image, and overlay. Nested elements keep their own rules. |
| Details | `--color-background` background, `--color-border` border, inherited text, subtle hover/focus from `currentColor`; native open/close behavior. |
| Separator | Default `--color-secondary`; plugin sizing, alignment, and variants remain available. |

Group is organizational and has no dedicated visual treatment. There is no dedicated visual integration for FX Builder or FX Builder Widgets.

## Customization precedence

Renderer attributes are applied inline: supported colors, padding, margins, radius, and other properties take precedence over the theme stylesheet. `!important` is not used. Button exposes `--fx-button-bg` and `--fx-button-color`: if either appears in its `style` attribute, the theme does not apply its secondary-color hover/focus-visible rule and retains the plugin's hover behavior. Explicit Card, Cover, and Details backgrounds and explicit Separator colors are not overridden.

The theme reuses `githeme_button_text_color()` for primary and secondary colors, choosing whichever of white or black gives better contrast. It does not recalculate text color for arbitrary inline backgrounds. Explicit customizations and text over Cover images require editorial contrast checks. Separator thickness depends on its variants: the inspected renderer does not expose a separate thickness attribute.

## Accessibility and verification

Visible focus, native Details controls, no additional JavaScript dependency, and respect for reduced-motion preferences. This integration is not a claim of WCAG conformance for plugin content.

The [tests/fx-shortcodes.php](../tests/fx-shortcodes.php) test checks conditional loading, CSS order/cache, and automatic contrast in memory, including when plugins are skipped. Browser checks should include default and customized components at the viewport sizes listed in [Development](development.md). Do not modify the plugin to accommodate the theme's presentation.

## Rendering boundary

FX Shortcodes does not register `[element]` as an ordinary shortcode: `do_shortcode()` alone does not process it. Rendering belongs to the plugin, not the theme integration stylesheet. The theme continues to use `the_content()` and standard widget APIs; content created with a plugin may depend on that plugin to display.
