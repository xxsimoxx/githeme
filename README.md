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

## Compatibility and accessibility

Development and regression testing have been carried out with **PHP 8.2** and a **ClassicPress 2.7.4+dev** checkout containing the Customizer changes intended for ClassicPress 2.8. These are tested environment details, **not minimum version requirements or a general compatibility guarantee**.

Accessibility is a continuing design and testing goal, not a claim of WCAG certification. Automated and browser checks do not replace testing with screen readers, real touch devices, or browser zoom. Site content, color choices, and third-party plugins also affect accessibility.

## License

`githeme` is licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE). Bundled fonts retain their respective **SIL Open Font License 1.1** terms; their licenses and provenance are included with the font files.
