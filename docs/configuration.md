# Configuration

Technical reference separate from the README; values checked against current definitions in `inc/settings.php` and `inc/customizer.php`. See [Architecture](architecture.md) for integration boundaries and editor behavior, and [Accessibility](accessibility.md) for warnings.

## Global settings

The Colors, Typography, Widths and layout, and Header sections use `theme_mod`. Site Identity retains native controls and the theme's two visibility options. Registration: `githeme_customize_register()`; defaults: `githeme_defaults()`.

| Setting | Default | Allowed values |
|---|---|---|
| Primary | `#14569a` | Hex color |
| Secondary | `#4b5563` | Hex color |
| Text | `#202833` | Hex color |
| Background | `#ffffff` | Hex color |
| Link | `#14569a` | Hex color |
| Header background | `#ffffff` | Hex color |
| Footer background | `#ffffff` | Hex color |
| Show title | Visible | Boolean; always visible without a logo |
| Show tagline | Hidden on new activations | Boolean, independent of logo |
| Font | System stack | System, Source Sans 3, Source Serif 4, Atkinson Hyperlegible Next |
| Base font size | `1rem` | `1–1.375rem`, step `0.0625` |
| Heading scale | `1.25` | `1.125`, `1.2`, `1.25`, `1.333` |
| Content width | `46rem` | `36–60rem`, step `1` |
| Wide width | `68rem` | `48–90rem`, step `1` |
| Maximum layout | `76rem` | `60–100rem`, step `1` |
| Maximum logo height | `5rem` | `2–8rem`, step `0.25` |
| Header | Identity left, menu right | Inline, or centered identity with menu below |

Sizes remain relative to browser preferences; zoom is unrestricted. Heading scale uses consistent ratios across all levels, shared with the Classic Editor. Widths are maximums, not fixed dimensions: `content ≤ wide ≤ layout`. Direct content elements with `alignwide` or `alignfull` can use the wide width or available layout width respectively.

Inconsistent width values trigger Customizer validation errors, including when multiple settings change together. Previously saved invalid values are bounded only during rendering, reported in the section and Themes screen, and **never rewritten automatically**.

## Public CSS custom properties

GiTheme exposes **24 public CSS custom properties** for colors, typography, and layout. They are intended for child themes, custom CSS, and third-party integrations. Their names and meanings form the theme's supported CSS interface; component-specific and internal properties are implementation details and may change between releases.

`githeme_custom_properties_css()` generates these values from validated theme settings and publishes them on `:root`. They also reach the Classic Editor through `content_style`. The Customizer remains the source of truth: use these properties rather than duplicating `theme_mod` values or palette calculations.

| Property | Value and intended use |
|---|---|
| `--color-primary` | Customizer primary color; theme accents and primary actions. |
| `--color-secondary` | Customizer secondary color; secondary accents and hover states. |
| `--color-text` | Global text color. |
| `--color-background` | Global background color. |
| `--color-link` | Global link color. |
| `--color-header-background` | Independent header background color. |
| `--color-footer-background` | Independent footer background color. |
| `--color-surface` | Subtle surface color, derived by blending 6% secondary with 94% background. |
| `--color-muted` | Secondary text color, derived from text and background; falls back to text if its contrast is insufficient. |
| `--color-border` | Border color derived from text and background. |
| `--color-button-text` | Automatically selected black or white text for the primary button background. |
| `--color-button-hover-text` | Automatically selected black or white text for the secondary button/hover background. |
| `--font-body` | Selected font-family stack, including the system stack option. |
| `--font-size-base` | Configured base font size, expressed in `rem`. |
| `--heading-scale` | Unitless heading scale ratio. |
| `--heading-1` … `--heading-6` | Six **unitless scale factors**, not font sizes; `--heading-6` equals `1`, and each preceding level applies another heading-scale step. |
| `--width-content` | Maximum editorial content width in `rem`. |
| `--width-wide` | Maximum width for wide content in `rem`. |
| `--width-layout` | Maximum overall layout width in `rem`. |

Widths are maximums rather than fixed dimensions and satisfy `content ≤ wide ≤ layout` after rendering safeguards. Heading factors must be combined with a length, for example `calc(var(--font-size-base) * var(--heading-3))`; using `var(--heading-3)` alone as `font-size` would be invalid.

Example for a custom component:

```css
.custom-card {
    max-width: var(--width-content);
    padding: 1rem;
    background: var(--color-surface);
    color: var(--color-text);
    border: 1px solid var(--color-border);
}

.custom-card h3 {
    font-family: var(--font-body);
    font-size: calc(var(--font-size-base) * var(--heading-3));
}
```

**Component-specific generated properties** are available but are *not* part of this general-purpose public interface: `--color-navigation-focus`, `--color-navigation-submenu-focus`, `--color-social-link`, `--color-social-focus`, `--color-header-muted`, and `--logo-max-height`. They implement particular theme components, including context-dependent contrast decisions, and may change as those components evolve.

**Internal implementation properties** such as `--submenu-offset`, `--with-sidebar`, `--space`, `--githeme-prose-h1` … `--githeme-prose-h3`, `--githeme-heading-after`, and `--githeme-gallery-*` are not supported extension points. Their presence in stylesheets does not make them a stable API. The public list above does not include variables owned by plugins or the ClassicPress admin interface.

## Fonts and Classic Editor

WOFF2 fonts are local and unmodified, with SIL OFL 1.1 licenses and provenance documented in [assets/fonts/SOURCES.md](../assets/fonts/SOURCES.md). The theme declares only the two variable faces, upright and italic, of the selected family; the browser downloads files as content needs them. There is no forced preload and no theme font loading for the system stack. Plugins can configure fonts independently.

The Classic Editor receives family, size, scale, colors, and width through `tiny_mce_before_init` / `teeny_mce_before_init` and the local editor stylesheet. Inline content styles or plugin settings may take precedence.

## Header, footer, and identity

Colors includes independent header and footer backgrounds, both white by default (`githeme_color_header_background`, `githeme_color_footer_background`). These are validated `theme_mod` values like other colors and become `--color-header-background` and `--color-footer-background`; the footer no longer uses the surface derived from the secondary color. That derived surface remains available for hover and other elements. Text and links continue to use the global palette: the informational panel also calculates their contrast against header and footer separately, without blocking saving.

In Site Identity, “Show site title” and “Show tagline” are independent. The title is visible by default and always shown when there is no logo; the tagline is hidden by default on new activations. An existing configuration with a nonempty tagline retains its visibility: the choice is initialized once in theme settings during administration/activation without rewriting `blogname` or `blogdescription`. To hide it, uncheck the option and publish; saving another control does not hide it. An explicitly stored value always takes precedence. An empty tagline produces no empty container.

The tagline flag is initialized by `githeme_initialize_identity_visibility()` on `admin_init` and `after_switch_theme`; `githeme_initial_tagline_visibility()` distinguishes a new activation from an existing configuration. `githeme_identity_visible()` applies a read fallback without modifying title or tagline.

## Basic setup

1. Activate GiTheme under Appearance → Themes.
2. Assign a menu to “Primary menu” and optionally configure a logo under Site Identity.
3. For a static homepage, select a regular page in Reading settings.
4. The “Footer” widget area is optional and configurable through standard widget APIs; its stable ID remains `footer-experimental`. Without widget output, no empty row or automatic credits are added.

## Social menu

Besides “Primary menu”, GiTheme registers an optional “Social” location. Assign a menu under **Appearance → Menus** to show links in the footer. Recognized services automatically receive a local SVG icon and accessible label; unrecognized links retain their original text. The menu requires no frontend JavaScript. For supported services, the extension filter, and custom icons, see [Social menu](social-menu.md).

## Static homepage and widgets

1. Create or choose a published page, with content in the Classic Editor or optionally FX Builder.
2. Under Settings → Reading, choose a static homepage and assign that page; optionally select a separate posts page.
3. Under Appearance → Widgets or the Customizer's widget areas, add widgets to **Homepage Hero** and/or **Homepage Content**.

The order is header, Homepage Hero, page content, Homepage Content, footer. Both areas are independent and optional: without widgets, they create no empty containers. The homepage still displays normal page content; its template title is visible by default and can be hidden with “Hide page title” in the individual page editor. Use level-two widget headings and a consistent content hierarchy.

Hero spans the viewport width; the widget determines its own internal layout. Homepage Content respects the theme's configured maximum layout width. Colors, typography, and widths still use global settings. Third-party content may require its own responsive adjustments.

Stable area IDs are `homepage-hero` and `homepage-content`. They use `register_sidebar()` and `dynamic_sidebar()`, without plugin-specific APIs. They do not appear on the latest-posts homepage, separate posts page, internal pages, or single posts.

No `front-page.php` is added: native hierarchy and assigned page templates using the theme's standard header and footer remain valid. External templates that replace the entire header/footer must handle rendering themselves. No proprietary ordering, new Customizer options, or section systems are introduced.

## Widgets, archives, and page titles

The [README](../README.md) describes the native GiTheme – Featured Posts and GiTheme – Gallery Slider widgets, selection modes, category archives with 12 posts per page, and `[gallery layout="slider"]` shortcode. Widgets reuse existing cards and galleries without additional visual options. FX Builder Default rows can use `githeme-wide` to reach `--width-layout`; this does not change `--width-wide` or the plugin's Full Width rendering.

“Hide page title” uses the `_githeme_hide_page_title` post meta only for pages. It does not change the saved title, document title, or content headings; autosaves and revisions do not rewrite the preference. Responsive editorial typography and margins shared with the Classic Editor respect configured base size and scale without changing semantic heading levels.
