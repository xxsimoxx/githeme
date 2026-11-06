<?php
/** Checkbox markup using the native control row and public binding API. */
defined( 'ABSPATH' ) || exit;

class Githeme_Checkbox_Control extends WP_Customize_Control {
	public $type = 'checkbox';

	public function render_content() {
		$id          = '_customize-input-' . $this->id;
		$description = '_customize-description-' . $this->id;
		$value       = githeme_sanitize_checkbox( $this->value() );
		?>
		<span class="customize-inside-control-row">
			<input id="<?php echo esc_attr( $id ); ?>" type="checkbox" value="1"
				<?php $this->link(); ?> <?php checked( null === $value ? $this->setting->default : $value ); ?>
				<?php if ( $this->description ) : ?>aria-describedby="<?php echo esc_attr( $description ); ?>"<?php endif; ?>>
			<label for="<?php echo esc_attr( $id ); ?>"><?php echo esc_html( $this->label ); ?></label>
			<?php if ( $this->description ) : ?>
				<span id="<?php echo esc_attr( $description ); ?>" class="description customize-control-description"><?php echo esc_html( $this->description ); ?></span>
			<?php endif; ?>
		</span>
		<?php
	}
}
