# Accessibility

WCAG 2.2 AA accessibility, performance, and technical SEO are development goals, not certifications. Automated tests and viewport checks do not establish full conformance.

## Structure, navigation, and focus

Semantic header/footer, a `main` element, and a skip link to `#main-content`. Optional widgets use level-two headings; content must maintain a consistent hierarchy. Navigation uses a single list and a native button with `aria-expanded` and `aria-controls`; submenus are accessible by mouse and keyboard, with Escape handling and focus restoration. There are no application ARIA roles or focus-trapping dialogs. All links remain usable without JavaScript. See [Architecture](architecture.md) for implementation details.

CSS includes `:focus-visible`. Manual testing must consider author-provided content and explicit styles as well as theme defaults. Relative sizing and unrestricted zoom are supported; a narrow viewport is not equivalent to actual browser zoom.

## Contrast and informational warnings

The “Color contrast” informational control in Colors displays textual status, ratio, and threshold for text/background, links/background, normal button text/primary, and text/links against header and footer backgrounds. The 4.5:1 reference applies to normal-sized text: it does not verify logos, icons, component borders, plugin styles, or whole-site conformance. Hover/focus states and link identification need separate checks. Comparisons use the unrounded ratio; displayed values have two decimal places.

The PHP panel remains readable in server-delivered HTML if the theme script is unavailable. Its static note advises reloading after saving; when the script is available, this is replaced by an explanation of immediate updates. This informational fallback does not make the core Customizer fully usable without JavaScript.

Visual updates follow native `input` and `change` events on theme-rendered fields using the color control and public `link()` binding. There is no access to the Customizer's internal DOM, Backbone, or proxy. A separate, initially empty live region uses `role="status"`, `aria-live="polite"`, and `aria-atomic="true"`; it reports only changed results after a 750 ms pause without moving focus. Identical updates are not announced. Actual announcements still require manual screen-reader testing.

See [WCAG 2.2, Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). sRGB constants and the threshold are defined once in `githeme_contrast_rules()` and passed to JavaScript. PHP and JS implementations of the same WCAG formula are checked with shared cases and parity tests. `githeme_contrast_report()` also returns an uncomputable state for invalid input. Advice neither changes selected colors nor blocks saving; existing syntax validation is separate. Button text automatically chooses whichever of black or white provides better contrast. Surfaces, borders, and secondary text remain derived from the palette.

`githeme_contrast_ratio()` calculates the ratio, `githeme_button_text_color()` selects the automatic foreground, and `githeme_contrast_warnings()` produces PHP warnings. The seven checked pairs do not cover every interaction state or plugin content. FX hover on the secondary color uses a separate automatic foreground; see [FX Shortcodes](fx-shortcodes.md).

## Typography and locally hosted fonts

WOFF2 fonts are local and unmodified, licensed under SIL OFL 1.1, with sources documented in [font sources and licenses](../assets/fonts/SOURCES.md). The theme declares only the two variable faces, upright and italic, of the selected family; the browser downloads files as content needs them. There is no forced preload, and the theme loads no fonts when the system stack is selected. Plugins may configure their fonts independently.

Atkinson Hyperlegible Next is one available option; it is not imposed, and choosing it does not establish content accessibility. The system stack, Source Sans 3, and Source Serif 4 are also available.

## Reduced motion

Navigation does not depend on animation. The optional FX stylesheet removes button transitions under `prefers-reduced-motion: reduce`; the Details indicator does not require a transition. Plugins and external content may have their own behavior to check.

The native slider uses Scroll Snap and horizontal scrolling without autoplay. JavaScript adds labeled buttons and adjusts visibility of focused images; reduced-motion settings make button-triggered movement immediate. Without scripts, links and native scrolling remain: Firefox may leave a focused image partly visible until the user scrolls. Offscreen images are not hidden from assistive technology.

## Checks requiring human review

- Activation, pages/posts, listings, search, 404 pages, and password-protected content.
- Static homepage with and without FX Builder; theme with FX plugins disabled.
- Nested menus, keyboard, Escape, width changes, zoom, and JavaScript disabled.
- Logo, long headings, images, tables, and Classic Editor content.
- Customizer: preview and publication of logo, menus, and widgets; adding the first widget, reordering, editing, and removing the last.
- Comments, nested replies, and pagination.

Screen readers, real touch devices, magnification, and review of actual content are still required. Live-region DOM mutations do not establish what VoiceOver or other readers announce. Test procedures and limitations are documented in [Development](development.md).
