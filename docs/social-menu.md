# GiTheme social menu

GiTheme provides an optional menu location named `social`, displayed in a dedicated footer row by `githeme_get_social_links_menu()`.

The menu uses ClassicPress's standard walker: item order, hierarchy, URLs, targets, and link attributes retain their native behavior. Recognized links receive an SVG icon and a screen-reader-accessible label; unrecognized links retain their visible text. Links in the social menu have no underline, while pointer-hover borders and keyboard-focus indicators remain visible. No frontend JavaScript is required.

## Customize icons with `githeme_social_links_icons`

The `githeme_social_links_icons` filter receives and returns an associative array of service-matching rules. Rules are applied to the menu item's original URL before its title is rendered: the filter does not inspect generated HTML, make network requests, or discover services.

| Field | Accepted value | Behavior |
| --- | --- | --- |
| Service identifier | Associative key, e.g. `community` | Adds, edits, or removes a rule. |
| `hosts` | Array of exact lowercase ASCII/punycode hostnames | For HTTP/HTTPS URLs, including protocol-relative (`//`) URLs. Omit `www.`: host normalization removes a leading `www.` and any valid trailing dot. List subdomains explicitly. |
| `path_prefix` | Optional nonempty string, e.g. `/community` | Case-sensitive match: the path must equal the prefix or continue with `/`. Query strings and fragments do not determine the service. |
| `icon` | Local SVG basename without an extension, matching `[a-z0-9-]+` | Located under `assets/icons/social/` through `get_theme_file_path()`; a child-theme asset takes precedence. URLs and directory traversal are rejected. |
| `scheme` | `mailto` or `tel`, instead of `hosts` | Recognizes one valid email recipient or a numeric telephone URI; arbitrary URI schemes are not supported. |

Rules are evaluated in array order: **the first valid matching rule wins**. To change an existing service, edit its rule rather than appending a competing rule.

If a URL is unrecognized or its SVG is missing or unusable, the original label remains visible. URLs containing user information (`user:password@host`) are not matched to icons. Matching never changes the link URL.

Telephone links support international and local numbers, visual separators, and parameters such as `;ext=42` and `;phone-context=example.test`.

### Example: a Mastodon instance and a custom service

Add the following code to a child theme's `functions.php` or another suitable local PHP extension:

```php
add_filter( 'githeme_social_links_icons', 'example_child_social_icons' );

function example_child_social_icons( $icons ) {
    $icons['mastodon']['hosts'][] = 'social.example.org';

    $icons['community'] = array(
        'hosts'       => array( 'community.example.org' ),
        'path_prefix' => '/members',
        'icon'        => 'community',
    );

    return $icons;
}
```

With these rules, `https://social.example.org/@team` uses the Mastodon icon, while `https://community.example.org/members/team` uses `community.svg`. The path `/members-other` does not match `/members`. Replace example domains with your own.

## Custom SVGs in child themes

For the `community` service above, save the file at:

```text
your-child-theme/assets/icons/social/community.svg
```

The SVG must contain a valid `viewBox` and flattened `<path d="…">` paths. The renderer sanitizes SVG and path markup and enforces `currentColor`, fixed intrinsic dimensions, `aria-hidden="true"`, and `focusable="false"`.

External references, scripts, event handlers, styles, images, text, and transforms are unsupported. Avoid group transforms and multicolor fills: convert artwork into compatible flattened paths first. The link's accessible name comes from the menu item label, not the SVG title.

Preserve original asset licenses and attribution. Bundled icons come from Font Awesome Free 7.1.0; see [icon sources and licenses](../assets/icons/social/README.md). `phone.svg` follows the conventions of the other solid icons.

## Customizer integration

### Menu updates

GiTheme relies on **ClassicPress's native Selective Refresh** to update menus already present in the preview, without registering additional theme partials, settings, or JavaScript listeners.

The social menu helper calls `wp_nav_menu()` with `echo => true` inside an output buffer and returns the captured HTML. This allows core to recognize the menu as eligible for its partial-update mechanism.

Initially assigning or removing a menu, or starting with an empty footer, may require a full preview refresh because there is no existing element to replace. GiTheme does not insert hidden placeholders or empty footer rows to work around this behavior.

### Color previews

GiTheme color settings are registered by `githeme_customize_register()` (`inc/customizer.php`) with `transport => 'refresh'`, like other global presentation settings.

Social-menu link and focus colors are derived by `githeme_custom_properties_css()` from link, primary, and footer colors. After a successful full preview refresh, these colors are recalculated. The theme does not implement a separate JavaScript palette or instantaneous CSS updates.

## Checks and tests

Relevant tests include:

- `tests/social-menu.php`: URL matching, telephone links, accessibility, empty footer, menu rendering, and interaction with Customizer filters;
- `tests/social-menu-browser.py`: footer presentation, responsive behavior, link decoration, hover, and keyboard focus.

Tests of internal ClassicPress Customizer defects and their diagnostic history are outside this feature documentation. For the related core fixes, see PRs [#2826](https://github.com/ClassicPress/ClassicPress/pull/2826), [#2827](https://github.com/ClassicPress/ClassicPress/pull/2827), and [#2828](https://github.com/ClassicPress/ClassicPress/pull/2828).
