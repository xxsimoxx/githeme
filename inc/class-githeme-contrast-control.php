<?php
/**
 * Theme-owned Customizer contrast control.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/** Informational control: no setting, validation or database write. */
class Githeme_Contrast_Control extends WP_Customize_Control {
	/**
	 * Informational control type.
	 *
	 * @var string
	 */
	public $type = 'githeme-contrast';

	/** Load the controls-pane assets through the public enqueue hook. */
	public function enqueue() {
		githeme_enqueue_contrast_assets();
	}

	/** Render all results on the server, without a setting or validation errors. */
	public function render_content() {
		$strings = githeme_contrast_strings();
		$report  = githeme_contrast_report( githeme_palette() );
		?>
		<section id="githeme-contrast-panel" class="githeme-contrast-panel" aria-labelledby="githeme-contrast-title">
			<h3 id="githeme-contrast-title"><?php echo esc_html( $strings['title'] ); ?></h3>
			<p><?php esc_html_e( 'WCAG AA reference for normal-size text. These results do not assess logos, icons, component borders or the whole site.', 'githeme' ); ?></p>
			<ul class="githeme-contrast-results">
				<?php foreach ( $report as $key => $result ) : ?>
					<li data-githeme-contrast-row="<?php echo esc_attr( $key ); ?>" data-status="<?php echo esc_attr( $result['status'] ); ?>">
						<h4><?php echo esc_html( $strings[ $key ] ); ?></h4>
						<p><span data-githeme-icon aria-hidden="true"><?php echo 'pass' === $result['status'] ? '✓' : ( 'fail' === $result['status'] ? '!' : '?' ); ?></span> <strong data-githeme-status><?php echo esc_html( $strings[ $result['status'] ] ); ?></strong><br>
							<span data-githeme-ratio><?php echo esc_html( null === $result['ratio'] ? $strings['invalidHelp'] : sprintf( $strings['ratio'], number_format_i18n( $result['ratio'], 2 ), number_format_i18n( $result['minimum'], 1 ) ) ); ?></span><br>
							<small data-githeme-pair><?php echo esc_html( null === $result['ratio'] ? '' : sprintf( $strings['pair'], $result['foreground'], $result['background'] ) ); ?></small>
						</p>
					</li>
				<?php endforeach; ?>
			</ul>
			<p><?php esc_html_e( 'Button text uses whichever of black or white has better contrast. Results are compared before rounding. Link identification, hover states and plugin styles need separate checks. Contrast advice does not block saving.', 'githeme' ); ?></p>
			<p data-githeme-update-help><?php esc_html_e( 'Values shown were calculated when this screen loaded. Reload after saving to check updated results.', 'githeme' ); ?></p>
			<p data-githeme-live class="screen-reader-text" role="status" aria-live="polite" aria-atomic="true"></p>
		</section>
		<?php
	}
}
