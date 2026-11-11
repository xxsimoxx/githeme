# githeme

**A lightweight, accessibility-minded classic theme for ClassicPress, built with modern CSS and progressive enhancement.**

`githeme` combines a clean, adaptable foundation with native ClassicPress features. It favors readable typography, predictable navigation, and straightforward customization—without a frontend framework, a required asset build step, or mandatory plugins.

## Highlights

- **Accessibility-minded by design.** Semantic page structure, a skip link, visible keyboard focus, keyboard-accessible navigation, and support for reduced-motion preferences where applicable.
- **Readable, locally hosted typography.** Choose a system font stack, Source Sans 3, Source Serif 4, or **Atkinson Hyperlegible Next**. No external font service is required.
- **Modern, responsive CSS.** Custom properties, Grid, Flexbox, relative sizing, and configurable content widths help layouts adapt to different screens.
- **Progressive enhancement.** Navigation remains usable when JavaScript is disabled; scripts enhance behavior rather than provide the only route to content.
- **Native customization.** Adjust colors, typography, layout widths, header arrangement, logo presentation, and header/footer backgrounds through the ClassicPress Customizer.
- **ClassicPress-first architecture.** Traditional PHP templates, the classic editor, native menus, comments, and widget areas; no built-in page builder or block-editor dependency.
- **Optional plugin styling.** When FX Shortcodes is active, selected components inherit the theme’s visual language without changing the plugin’s rendering or overriding explicit shortcode styling.

## Customize your site

The Customizer provides a shared visual system for the site, including primary and secondary colors, text and link colors, independent header and footer backgrounds, font selection, heading scale, content widths, and header layout.

An informational contrast checker evaluates seven text/background combinations and provides feedback without silently changing the colors you choose. The classic editor also receives corresponding typography and color settings.

## Optional FX Shortcodes integration

`githeme` provides theme-aware styling for five [FX Shortcodes](https://getbutterfly.com/classicpress-plugins/fx-shortcodes/) components: **Button, Card, Cover, Details, and Separator**.

The integration uses the existing Customizer palette, respects explicit component attributes, and adds no separate settings or required plugin dependency. FX Shortcodes supplies the components and their behavior; `githeme` supplies visual consistency with the surrounding site. Other FX plugins may be used independently, without dedicated theme styling.

## Getting started

1. Install and activate `githeme` through **Appearance → Themes** in ClassicPress.
2. Assign a menu to the **Primary menu** location.
3. Optionally add a logo and adjust the theme’s appearance in the **Customizer**.
4. To use a static homepage, select a published page under **Settings → Reading**. Optional **Homepage Hero** and **Homepage Content** widget areas can complement its content.

The theme works without FX Shortcodes, FX Builder, or FX Builder Widgets. Content authored with a particular plugin may still require that plugin to render correctly.

## Static homepage widget areas

Select a static homepage under **Settings → Reading**, then add native widgets through **Appearance → Widgets**:

- **Homepage Hero** (`homepage-hero`) appears after the header and navigation, before the page content. Widgets can use the full available width.
- **Homepage Content** (`homepage-content`) appears after the page content, before the footer.

Both areas are optional and appear only on the static front page—not on the latest-posts homepage, a separate posts page, or internal pages. Areas without widget output add no empty wrappers. Leaving both areas empty keeps the normal static page rendering; the page’s own content remains editable in the classic editor. No plugin is required.

A native **Text** widget can also contain a [gallery slider](#native-gallery-slider), including in Homepage Hero.

## Per-page title visibility

In the page editor, enable **Hide page title** in the **Page title** box to omit the template heading for that page. Titles are visible by default. This does not change the saved title, document title, headings in the content, or builder-generated headings. Posts and archives are unaffected. Autosaves and revisions do not overwrite this page preference.

## Category archives

Category archives use a responsive card grid: three columns on desktop, two on tablet, and one on mobile, adapting to the available container width. Cards display a 16:9 featured image, a title, and the native excerpt, preferring a manual excerpt when provided. Posts without a featured image remain readable cards without artificial placeholders.

An image overlay names the most specific assigned subcategory relevant to the current archive, or the current category when no such subcategory is assigned. Colors and typography follow the theme settings. Centered native pagination shows 12 posts per page.

This layout applies only to category archives; other archive types keep their existing presentation.

## Native gallery slider

Add `layout="slider"` to the native gallery shortcode in the classic editor or a native **Text** widget:

```text
[gallery layout="slider" ids="12,34,56"]
```

Replace the example IDs with image attachment IDs from your media library. Galleries without `layout="slider"` keep their standard behavior, including the native `thumbnail` size default. Slider galleries default to `large` unless you explicitly provide `size`, such as `size="medium"` or `size="full"`.

When native dimensions are available for every image, slider images share a responsive height with proportional widths, without cropping or distortion. The common height is limited by the smallest source image, avoiding enlargement of small images; a low-resolution image can therefore reduce the height of the whole gallery. Missing dimension metadata or a browser without CSS container units keeps natural image heights instead.

The slider uses native horizontal scrolling and CSS Scroll Snap. With JavaScript, previous/next buttons appear when scrolling is needed, and focused image links are brought into view. Use Tab and Shift+Tab for links and controls, or arrow keys on the focusable scrolling area. Touch, trackpad, and the native scrollbar remain available. Button navigation uses smooth scrolling unless reduced motion is preferred; focus corrections are immediate. There is no autoplay.

Without JavaScript, the gallery remains usable through native scrolling and keyboard navigation, with no inactive buttons. Automatic focus correction is an enhancement: the browser may leave a focused image partially visible until you scroll further.

Use the shortcode in a Text widget to place a slider in a [homepage widget area](#static-homepage-widget-areas). The native **Gallery** widget renders a standard gallery and does not expose the slider option; use a Text widget instead. No gallery plugin is required.

Slider enhancement requires PHP’s DOM extension and recognizable native gallery markup. Empty, single-image, and feed output stays native; plugins that replace gallery markup may prevent enhancement.

## Compatibility and accessibility

Development and regression testing have been carried out with **PHP 8.2** and a **ClassicPress 2.7.4+dev** checkout containing the Customizer changes intended for ClassicPress 2.8. These are tested environment details, **not minimum version requirements or a general compatibility guarantee**.

Accessibility is a continuing design and testing goal, not a claim of WCAG certification. Automated and browser checks do not replace testing with screen readers, real touch devices, or browser zoom. Site content, color choices, and third-party plugins also affect accessibility.

## License

`githeme` is licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE). Bundled fonts retain their respective **SIL Open Font License 1.1** terms; their licenses and provenance are included with the font files.
