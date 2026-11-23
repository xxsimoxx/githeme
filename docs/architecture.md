# Architecture

A classic PHP theme for ClassicPress, without a framework, mandatory build step, Gutenberg, or required plugin dependencies. Content belongs in pages and posts; global presentation options belong in the Customizer. There is no built-in page builder, proprietary section ordering, or site-specific variant.

## Organization and rendering

| Path | Responsibility |
|---|---|
| `functions.php` | Loads settings, setup, Customizer, galleries, categories, page-title handling, and widgets. |
| `inc/setup.php` | Theme supports, menus, assets, and widget-area registration. |
| `inc/settings.php` | Validated values, contrast, fonts, CSS properties, and Classic Editor integration. |
| `inc/customizer.php` | Registration, validation, warnings, and informational assets. |
| `inc/class-githeme-*-control.php` | Customizer controls with their own markup and public binding. |
| `inc/gallery.php`, `assets/js/gallery-slider.js` | Optional native gallery wrapper and progressive navigation. |
| `inc/category.php`, `category.php` | Main category query and dedicated grid. |
| `template-parts/content-category-card.php` | Cards shared by archives and Featured Posts. |
| `inc/page-title.php` | Page-only meta box and title preference. |
| `inc/class-githeme-*-widget.php` | Native Featured Posts and Gallery Slider widgets. |
| `header.php`, `footer.php` | Shared header/footer and conditional homepage widget areas. |
| `page.php`, `single.php` | Singular content through `template-parts/content-singular.php`. |
| `index.php`, `404.php`, `comments.php` | Listings, archives/search, missing page, and comments. |
| `template-parts/homepage-widgets.php` | Reusable rendering of active homepage areas without empty containers. |
| `style.css`, `assets/` | CSS, vanilla JavaScript, and local fonts. |
| `tests/` | Development-checkout tests. |

There is no `front-page.php` or `home.php`: native template hierarchy applies. A static homepage displays normal page content and, optionally, the areas described in [Configuration](configuration.md). Pages built with an optional plugin remain possible without making that plugin a theme dependency.

## CSS and variables

`githeme_custom_properties_css()` generates properties from validated values, without accepting arbitrary CSS strings from controls. `githeme_rendered_widths()` applies defensive bounds without rewriting stored values. CSS Grid, Flexbox, and relative units keep the layout responsive.

| Variables | Source |
|---|---|
| `--color-primary`, `--color-secondary`, `--color-text`, `--color-background`, `--color-link` | Customizer palette. |
| `--color-header-background`, `--color-footer-background` | Independent Customizer backgrounds. |
| `--color-button-text`, `--color-button-hover-text` | Better-contrast black/white on primary and secondary. |
| `--color-surface`, `--color-muted`, `--color-border` | Derived palette variants, without a separate palette. |
| `--font-body`, `--font-size-base`, `--heading-scale`, `--heading-1` … `--heading-6` | Selected font and heading scale. |
| `--width-content`, `--width-wide`, `--width-layout` | Validated and rendering-bounded widths. |
| `--logo-max-height` | Configured maximum logo height. |

The derived surface blends secondary and background (6%/94%). The footer uses its independent color instead. Muted text blends text/background and falls back to the original text color if the blend fails the normal-text threshold; this cannot fix an insufficient original palette.

## Assets and editor

`githeme_enqueue_assets()` uses native APIs. Frontend CSS, navigation, Classic Editor stylesheet, and FX integration use the `style.css` version for caching; Customizer informational assets use `filemtime()`. The slider script also uses the theme version and is enqueued only when an enhanced gallery is actually rendered, without duplication between shortcode and widget.

`githeme_editor_settings()` appends fonts and properties to `content_style` through `tiny_mce_before_init` and `teeny_mce_before_init`, preserving existing styles. Double quotes in the generated CSS alone are replaced with single quotes before appending, preventing TinyMCE initialization errors with families such as “Segoe UI”. `assets/css/editor.css` does not load the frontend layout into the editor.

## Navigation and progressive enhancement

Navigation keeps a single list in the DOM, a native button with `aria-expanded` and `aria-controls`, and mouse- and keyboard-accessible submenus. On desktop, panels are out of flow: only top-level items determine required space, not the width of open submenus. Escape closes desktop panels and restores focus to the parent link when focus came from within a panel. Further levels stay nested inside the panel rather than opening offscreen flyouts. The indicator switches from hamburger to close without changing the accessible name “Menu”. Escape closes compact navigation and restores focus to its button. Centered identity with navigation below can use the full row; inline layout also accounts for site-identity width. Without JavaScript, the menu can wrap and every link remains usable.

Recalculations are batched with `requestAnimationFrame`: `ResizeObserver` watches header, identity, and menu, while changes to layout classes and inline variables are detected separately. Completion of local font loading triggers another check even after initial rendering. The script does not observe menu attributes it changes itself.

## Social menu

The optional `social` location uses ClassicPress's native menu system and renders in a dedicated footer row. Recognized links display local SVG icons and retain accessible names; unrecognized links retain visible labels. Matching can be extended through `githeme_social_links_icons`. See [Social menu](social-menu.md) for configuration, rules, and child-theme SVGs.

## Customizer controls and boundaries

Public PHP APIs, standard controls where possible, one setting per control, sanitization, and validation. Global theme settings use `refresh`. Menus instead use ClassicPress's native Selective Refresh, without registering custom partials. After markup replacement, the navigation script reacquires the menu and resynchronizes the button, submenus, and observers. The theme's informational interface listens to standard DOM events on its own inputs; it does not depend on Backbone, the incomplete JavaScript proxy, or the core's internal DOM. See [Accessibility](accessibility.md) and [Development](development.md).

Checkboxes use `WP_Customize_Control`, the native `customize-inside-control-row` container, `for`/`id` labels, and `aria-describedby` descriptions; the HTML value remains `1` even when unchecked. There is no CSS override or internal JavaScript API. The focused `tests/header-surfaces.php` test uses only in-memory overrides for the eight logo/title/tagline combinations and validation of new settings.

## Optional plugins

The theme uses `the_content()` and standard widget APIs; it works without FX Builder, FX Shortcodes, and FX Builder Widgets. It does not directly call their APIs. Content created with a plugin may still require that plugin to render.

The only dedicated visual integration covers the five components in [FX Shortcodes](fx-shortcodes.md). Group, FX Builder, and FX Builder Widgets have no dedicated visual integration in the theme.

## Licenses

Code is GPL-3.0-or-later, as stated in [LICENSE](../LICENSE). Fonts retain SIL OFL 1.1, with licenses in their directories and [documented provenance](../assets/fonts/SOURCES.md).

## Shared components

Featured Posts uses the same template and styles as categories; only the query, IDs, and card heading level depend on context. Gallery Slider invokes the normal gallery shortcode once, without a second implementation. The `shortcode_atts_gallery` filter supplies `large` only to sliders without a `size`; `do_shortcode_tag` preserves native HTML and wraps it only when recognizable. Without DOM or with incompatible output, native rendering remains.

Editorial typography shares a CSS block between frontend and editor, with a 48rem breakpoint and values derived from existing variables; widget and component headings retain their own rules. `githeme-wide` expands only containers with explicitly enabled Default rows and preserves the editorial width of other rows. No new Customizer JavaScript APIs or plugin dependencies are introduced.
