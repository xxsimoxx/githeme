# Development and testing

Technical material for a complete checkout; test tools are not production theme dependencies. Operational instructions for Codex remain in [AGENTS.md](../AGENTS.md).

## Environment and compatibility

Declared minimum requirements are ClassicPress 2.7 and PHP 8.2. The maintainer accepted ClassicPress 2.7 after manually checking Customizer controls, separately from automated tests. Automated functional tests on 2.7.0 were not completed because an isolated database was unavailable; no comprehensive compatibility matrix is claimed.

Customizer changes were checked against a ClassicPress development checkout and in an isolated browser environment. Versions and hashes for individual test runs belong in their respective commits and ClassicPress PRs, not in the theme's requirements.

Unless stated otherwise, the commands below assume a ClassicPress checkout with sources in `src/` and the theme in `src/wp-content/themes/githeme/`. Adapt `--path` and the theme path for other layouts.

## Checkout, ZIP, and project checks

The installable ZIP produced by the release workflow contains the theme and font licenses. It excludes `tests/`, `docs/`, and `.github/` through `.gitattributes`.

Run tests from a complete checkout of the [development repository](https://github.com/xxsimoxx/githeme), which includes PHP, JavaScript, and Selenium scripts. The commands documented here require that checkout and the indicated development tools; they cannot run from the installable ZIP alone. These tools are not production theme dependencies.

The ZIP uses `git archive` in `.github/workflows/zip.yml`, triggered when a release is published. Actual exclusions are defined in `.gitattributes`, including `AGENTS.md`, `docs/`, and listed operational files. The README, screenshot, runtime components, and font licenses remain included. References to tests in these documents apply to the complete checkout, not the reduced ZIP. Packaging rules and workflows have not been changed.

The `.github/workflows/cpcs.yml` workflow runs ClassicPress Directory Coding Standards on pushes/PRs and excludes `tests/`. This does not replace the functional suites below. Do not automatically install dependencies to run checks.

## Browser tests: prerequisites and safety

Selenium/Firefox and WebDriver BiDi must already be configured in a separate environment. Read that environment's README/AGENTS before use; set `BROWSER_TOOLS` to its actual path and `TEST_URL` to the authorized local HTTPS URL. Its `env.sh` must define `CODEX_BROWSER_ROOT` and `TMPDIR` consistently with script checks. Do not use personal browser profiles or record credentials or cookies. The anonymous launcher must not be used to bypass authenticated-session controls.

Current scripts have explicit restrictions tied to an external volume and dedicated macOS environment: they are not portable runners without review. `navigation-readonly-browser.py` also hardcodes its URL and loopback resolution; it does not accept `--url`. Its command below documents the existing procedure, not a promise that it runs on arbitrary hosts. Keep installation-specific details out of general documentation.

Tests that write options or menus require explicit authorization, complete snapshots of existence, values, types, keys, and autoload, independent cleanup, and final verification in a new WP-CLI process. Do not put essential operations inside `assert`: optimized Python must still execute tests and restoration. Do not create permanent content or delete existing content to prepare fixtures. Screenshots, logs, and snapshots stay outside repositories.

## Settings tests

With ClassicPress loaded and PHP 8.2, from the project root:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/global-settings.php
```

The test uses real APIs and values overridden only in memory: it saves no settings and creates no content. It checks boundary values, width ordering, invalid input, nonblocking warnings, selected fonts, editor CSS, and header classes. Preview/publication in the Customizer and actual font requests are checked separately with an authenticated browser.

WCAG 2.2 AA accessibility, performance, and technical SEO are development goals, not certifications of the initial release.

## Homepage tests

From the ClassicPress root:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
wp --path=src --skip-plugins eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
```

The PHP test does not write to the database: it checks registration, empty/populated areas, and allowed contexts, including widget callbacks that produce no output.

The browser test requires the existing external Selenium environment and authorization to temporarily change only the options listed in the script. It uses **already published** test pages/posts without changing their content. Before running, set the ID variables to existing published content on the test site:

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/homepage-widgets-browser.py \
  --url "$TEST_URL" --wp-path src \
  --front-page-id "$FRONT_PAGE_ID" --posts-page-id "$POSTS_PAGE_ID" \
  --internal-page-id "$INTERNAL_PAGE_ID" --post-id "$POST_ID"
```

The optional `--fx-content-id` and `--fx-page-id` arguments refer to local fixtures marked `githeme-test-*`; omit them when unavailable. The test explicitly uses a dedicated Firefox profile, taking screenshots and BiDi observations without recording credentials. It saves private option snapshots in the external environment's artifacts area and restores values, types, absence, and autoload, verifying them in a new WP-CLI process. It also checks that fixture content and plugin activation remain unchanged. Narrow headless viewports test responsive behavior but do not fully emulate a smartphone.

## Contrast tests

From the ClassicPress root, with WP-CLI, PHP, and Node already available:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/contrast.php
node src/wp-content/themes/githeme/tests/contrast.js
```

Tests cover identical color pairs, black/white, thresholds, intermediate values, invalid input, automatic foreground, PHP fallback markup, and cross-language parity. They do not write to the database.

The browser test requires installed Selenium, an external environment with `CODEX_BROWSER_ROOT`/`TMPDIR` configured, and an authorized session in the dedicated profile. It does not use the anonymous launcher or collect credentials. Run it only with permission to temporarily change `theme_mod` values, since it also tests publishing. It preserves complete snapshots of the affected `theme_mod` values and Site Health transients, deletes its temporary changesets, and verifies restoration in a new WP-CLI process:

```sh
"$CODEX_BROWSER_ROOT/venv/bin/python" tests/customizer-contrast-browser.py --url https://local-site:port --wp-path /path/to/ClassicPress/src
```

The script path is relative to the theme directory. Screenshots and results are stored in the external artifacts area, outside repositories. The server-fallback test examines HTML without executing scripts; it is not a complete check of the Customizer with JavaScript disabled. Announcements are tested as DOM mutations, not spoken VoiceOver output.

## Navigation tests

The browser test requires available Selenium, the dedicated profile, and authorization for temporary menu changes:

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/navigation-browser.py \
  --url "$TEST_URL" --wp-path src
```

It creates two temporary menus using existing published pages without modifying those pages. It checks absent, simple, and nested menus, long labels, both header layouts, mouse, Tab/Shift+Tab, Enter/Space, Escape, focus after width changes, and narrow viewports. At a constant viewport it varies logo, container, arrangement, font family, and delayed local font loading; it samples layout across frames to verify stability and return to horizontal mode. These changes occur only in the DOM and disappear on reload. The no-JavaScript check uses a preference in the dedicated profile only; afterward it restores and verifies that profile's original JavaScript preference. It removes only menus created by the test and restores original options, checking types, absence, and autoload in a new WP-CLI process. Screenshots, snapshots, and results remain in external artifacts. The `--baseline` option records earlier behavior without requiring additional collapse at 1024/820 px.

These are desktop Firefox viewport and keyboard tests, not real smartphone tests or accessibility certifications; screen-reader review remains necessary.

## Read-only navigation checks

`tests/navigation-readonly-browser.py` checks the actually assigned menu at 1440, 1280, 768, 390, and 320 CSS px with mouse, Tab/Shift+Tab, Escape, Enter/Space, and focus checks. Short, flat, nested, overlong, and absent menus are fixtures in an isolated iframe using the same CSS/JavaScript: no database menu, content, or assignment changes are made. The script also checks no-script fallback, available-space changes without resize, and observer stability. Fixtures do not replace authenticated checks of menu-assignment screens. Temporary anonymous profiles and results remain in the external environment; tool configuration is unchanged.

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/navigation-readonly-browser.py
```

Use this test when no database modifications are authorized; `navigation-browser.py` instead creates native fixtures and requires explicit authorization.

## Other focused checks

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/header-surfaces.php
wp --path=src eval-file src/wp-content/themes/githeme/tests/fx-shortcodes.php
wp --path=src --skip-plugins eval-file src/wp-content/themes/githeme/tests/fx-shortcodes.php
```

The first covers eight logo/title/tagline combinations, backgrounds, and controls with in-memory overrides. The FX test checks optional dependencies and contrast without saving options. Also run PHP 8.2 lint, `node --check` for JavaScript, Python parsing/syntax checks without repository artifacts, and `git diff --check`. Never report a check as passed unless it was run.

Frontend regression checks should include homepage, page and post, five FX components, viewports 1440/1280/768/390/320, no overflow, keyboard, focus, menus without JS, console/network, and new PHP errors. Contrast-only testing does not cover all Customizer controls: separately verify preview/publication/persistence for fonts, widths, header, and identity. Remaining manual checks are in [Accessibility](accessibility.md).

## Component checks

The PHP suites `tests/gallery-slider.php`, `tests/gallery-widget.php`, `tests/featured-posts.php`, `tests/category-archives.php`, `tests/footer.php`, and `tests/page-title-integration.php` run with `wp eval-file` in a ClassicPress checkout. They use reads and in-memory fixtures; existing local content is required as specified by each script. `tests/page-title.php` is instead an isolated test runnable directly with PHP.

Corresponding browser checks, including typography and `githeme-wide`, use the existing Firefox/Selenium environment and external artifacts. DOM fixtures do not equal adding and saving a widget in administration. Featured Posts and Gallery Slider persistence also requires a real administrative check: edit the widget, save, reload, inspect frontend output, and restore original settings. DOM fixtures do not substitute for this check.

## Customizer compatibility

GiTheme's global settings use `refresh`; menus use ClassicPress's native Selective Refresh. The theme does not modify core or introduce workarounds that alter signed menu contexts. Navigation JavaScript handles menu markup replacement during preview.

Some updated Customizer issues are documented and addressed by ClassicPress PRs [#2826](https://github.com/ClassicPress/ClassicPress/pull/2826), [#2827](https://github.com/ClassicPress/ClassicPress/pull/2827), and [#2828](https://github.com/ClassicPress/ClassicPress/pull/2828). These are core changes, not requirements or patches bundled with GiTheme.

Checks against ClassicPress 2.7 and the development branch are separate; they do not establish a comprehensive compatibility matrix across plugin, browser, and core-version combinations.

## Optional integration checks

Check FX Builder CSS and formatting, FX Shortcodes parsing in different contexts, and widget updates in the rewritten Customizer. The reference regression does not cover every plugin combination. FX Builder Widgets may expose its content type and archive publicly: check their use and publication on the destination site without introducing theme dependencies.

## Contributor guidelines

Preserve native APIs, contextual escaping, and validation; avoid mandatory dependencies or site-specific customizations. Make focused fixes with relevant tests, without purely cosmetic refactoring. Do not change environments, plugins, data, or workflows to make a test pass without authorization. Distinguish core/tool limitations from theme defects and retain them in reports.
