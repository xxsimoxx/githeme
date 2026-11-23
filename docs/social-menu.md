# Social menu integration

The optional native `social` menu location is rendered in its own footer row by
`githeme_get_social_links_menu()`. It uses the standard menu walker. Item order,
hierarchy, URLs, targets and link attributes stay native; only recognized item
titles receive an icon and a screen-reader text label. Unknown links retain their
visible label, without an underline in this menu. Hover borders and keyboard
outlines remain visible. No JavaScript is required on the frontend.

## Extending `githeme_social_links_icons`

This filter receives and returns an associative array of service rules. It is
applied when resolving the original menu item's URL, before rendering its title.
It does not receive or search rendered HTML. No network lookup or federated
service discovery is performed.

| Key | Accepted value | Behavior |
| --- | --- | --- |
| Service identifier | Associative array key, e.g. `community` | Identifies a rule for additions, edits or removal. |
| `hosts` | Array of exact lowercase ASCII/punycode hostnames | Used for HTTP/HTTPS links, including protocol-relative URLs. Omit `www.`: the URL host is lowercased, validated and stripped of a leading `www.` and a valid trailing root dot. Subdomains must be listed explicitly. |
| `path_prefix` | Optional nonempty string, e.g. `/community` | Case-sensitive path match: the path must equal the prefix or continue with `/`. Query strings and fragments do not determine the service. |
| `icon` | Local SVG basename matching `[a-z0-9-]+`, without `.svg` | Resolved under `assets/icons/social/` using `get_theme_file_path()`: a child-theme asset takes precedence. URLs and directory traversal are not accepted. |
| `scheme` | Optional `mailto` or `tel`, instead of `hosts` | Matches a valid single email recipient or a numeric telephone URI. This is not a general-purpose arbitrary-scheme matcher. |

Rules are evaluated in array order; the first valid matching rule wins. Modify an
existing rule to change its matching rather than appending a competing rule after
it. Unrecognized URLs and missing/unusable SVGs keep their original visible text.
URL user information is rejected for icon matching. Matching never rewrites the
link URL. Telephone links support ordinary global/local numbers, visual
separators, and parameters such as `;ext=42` or `;phone-context=example.test`.

### Example: add a Mastodon instance and a custom service

Place this in a child theme's `functions.php` or another appropriate local PHP
extension. The first rule reuses a bundled icon; the second uses a child-theme SVG.

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

For example, `https://social.example.org/@team` uses the Mastodon icon.
`https://community.example.org/members/team` uses `community.svg`;
`/members-other` does not match. Replace the example hosts with your own hosts.

## Child-theme SVG files

Save the second example's artwork as:

```text
your-child-theme/assets/icons/social/community.svg
```

Provide a valid `viewBox` and flattened `<path d="…">` artwork. The renderer
sanitizes SVG/path markup and enforces `currentColor`, fixed intrinsic dimensions,
`aria-hidden="true"` and `focusable="false"`. External references, scripts, event
handlers, styles, images, text and transforms are not supported. Do not rely on
group transforms or multicolor fills; flatten artwork before supplying it. The
accessible link name comes from the menu item label, not an SVG title.

Retain the source artwork's license and attribution. Bundled icons are Font
Awesome Free 7.1.0; see [asset provenance](../assets/icons/social/README.md).
`phone.svg` follows the same conventions as the other solid icons.

## Customizer: menu updates versus colors

### Theme-side menu correction

The original Social helper called `wp_nav_menu()` with `echo => false` to decide
whether the footer had content. Core's
`WP_Customize_Nav_Menus::filter_wp_nav_menu_args()` explicitly excludes such calls
from native selective refresh. The helper now uses `echo => true` inside output
buffering, returning the captured HTML unchanged. This enables core's native menu
partial without adding a theme partial, setting, or JavaScript subscription.

Core supplies the location and menu-item setting dependencies. An existing menu
can therefore use the native partial update path where the core implementation
works. First assignment/removal or an empty footer may still require core's full
preview refresh because there is no existing placement to replace. The theme
does not leave an empty frontend footer or hidden placeholder for this purpose.

### Color previews

GiTheme's color settings are registered with `transport => 'refresh'` in
`githeme_customize_register()` (`inc/customizer.php`), just like its other global
presentation settings. Social's link and focus colors are derived in
`githeme_custom_properties_css()` from the previewed link/primary/footer colors.
They are not a separate live JavaScript palette. A successfully refreshed preview
recalculates them; instantaneous CSS updates are not an existing theme feature.
No new color transport, partial or JavaScript workaround has been introduced.

### Local core limitations and verification boundary

On the local development core examined on 23 November 2026:

- `WP_Customize_Nav_Menus::filter_wp_nav_menu_args()` calculates `args_hmac`, then
  adds `menu_id` to the exported placement context. Its
  `render_nav_menu_partial()` checks the whole context against that earlier hash
  and returns `false`. This roundtrip failure is reproduced with the native PHP
  methods and in-memory menu lookups. It is independent of theme color changes;
  the theme does not strip or rewrite core's signed context to bypass the check.
- The `partial.params.settings.indexOf is not a function` exception at
  `wp-includes/js/customize-preview.js:682` has now been reproduced using an
  **actual core-generated export, without loading GiTheme or Social**. The affected
  partial is a `nav_menu_instance[...]` for a menu rendered by explicit menu ID or
  object **without a theme location**, as in the native Navigation Menu widget.
  `WP_Customize_Nav_Menus::filter_wp_nav_menu_args()` initially adds `nav_menu[ID]`
  to `$settings`, then appends the same ID again. Its `array_unique($settings)`
  removes the duplicate but preserves the key gap. `WP_Customize_Partial::json()`
  exports this array unchanged, so JSON produces an object such as
  `{"0":"nav_menu[100]","2":"nav_menu_item[11]"}`. The preview loops over every
  partial on a primary-color change and calls `.indexOf()` on that object, throwing
  before the normal color-refresh fallback runs. This can block unrelated settings.
- A location-based Primary or Social menu produces a consecutive list in the same
  diagnostic and does not trigger this exception. A PHP string is normally
  normalized to an array by `WP_Customize_Partial`; a JavaScript string also has
  `indexOf`. The confirmed malformed type here is an **object caused by sparse
  numeric PHP keys**, not a string supplied by GiTheme.
- An anonymous request to the local homepage confirmed a native Navigation Menu
  widget, `nav_menu-1`, as well as the Social row. This is a matching local render
  path. The opaque live `nav_menu_instance[...]` ID has not been read from the
  authenticated preview, so identifying its exact hash still needs the console
  inspection below. The dedicated Firefox profile required login; no credentials
  were entered and no settings were published.
- No runtime theme fix is applied for this core export defect. Reindexing the
  core settings list after deduplication is the appropriate correction at its
  registration/export boundary, not a JavaScript guard or a change to the theme's
  color transport. Core files remain untouched. Actual color and menu preview
  success is **not** claimed while that core defect is present.

### Comparison with the known-good theme commit

Reference: `6a3118c87e7bb42d595668e73d21bee58309e710`. On the examined working tree,
`inc/customizer.php` is byte-identical to that reference; color registrations,
validation and refresh transport have not changed. Theme frontend/Customizer
JavaScript and `header.php` are also unchanged.

Subsequent committed changes are `f58a665` (computed navigation focus colors and
focus CSS), `4bd8dc9` (1.0.2 metadata/catalog version headers), and `335e97c` (release
notes). None changes partial registration, settings-list types or preview event
handling. Uncommitted Social work adds native location registration, URL/icon
rendering, footer output and derived CSS colors, but no theme-owned partials.
Buffered native echo enables Social's core menu partial; it does not create the
explicit-menu/no-location duplicate setting demonstrated above.

The production site's theme commit alone does not establish the same core,
plugins, widget configuration or preview page. Production was not accessed.
This core-only reproduction is stronger evidence than inferring a theme
regression from the two sites' different behavior.

To identify the exact offending partial, run the following **read-only diagnostic**
in the preview iframe's console while authenticated. It does not modify settings:

```js
const partialTypes = [];
wp.customize.selectiveRefresh.partial.each(function (partial) {
    const settings = partial.params.settings;
    partialTypes.push({
        id: partial.id,
        isArray: Array.isArray(settings),
        type: typeof settings,
        hasIndexOf: settings != null && typeof settings.indexOf === 'function',
        settings: settings
    });
});
console.table(partialTypes);
```

Compare any malformed entry with
`_customizePartialRefreshExports.partials[partialId].settings` to distinguish a
PHP export from subsequent client-side mutation, then trace that partial ID to its
registration. Do not normalize all partials or guard the exception in theme JS:
that would hide the owner/type error. These observations are scoped to the local
core, not a claim about every supported ClassicPress version. No core changes or
issue/PR creation are part of this feature.

## Focused checks

`tests/social-menu.php` uses native URL parsing, KSES, the menu walker and menu
Customizer filters with in-memory dependencies. It covers URL matching, telephone
links, accessibility, empty-footer behavior, preview eligibility and the signed
context roundtrip. `tests/social-menu-browser.py` checks isolated footer fixtures,
responsive wrapping, scoped text decoration, hover and keyboard focus. `tests/customizer-menu-settings.php` separately executes native partial
registration and `json()` with no theme bootstrap. `tests/social-menu-customizer.js`
passes those exports to the actual local core setting-event handler: the
explicit-menu object reproduces the exception, whereas location-based list
settings reach the normal preview path. These are not a saved-menu or
authenticated Customizer end-to-end test.
