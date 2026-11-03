<?php
/**
 * Progressive contrast information, with markup owned by the theme.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/** Own the input markup; retain the native color type and public link() binding. */
class Githeme_Contrast_Color_Control extends WP_Customize_Color_Control {
	/**
	 * Palette key supplied by the theme registration.
	 *
	 * @var string
	 */
	public $color_name = '';

	/** Render the accessible input owned by the theme. */
	public function render_content() {
		$id    = 'githeme-color-' . $this->color_name;
		$value = $this->value();
		$value = is_string( $value ) ? $value : $this->setting->default;
		?>
		<label for="<?php echo esc_attr( $id ); ?>" class="customize-control-title"><?php echo esc_html( $this->label ); ?></label>
		<input id="<?php echo esc_attr( $id ); ?>" type="text" class="color-picker-hex" maxlength="7"
			data-githeme-color="<?php echo esc_attr( $this->color_name ); ?>"
			data-coloris data-default-color="<?php echo esc_attr( $this->setting->default ); ?>"
			value="<?php echo esc_attr( $value ); ?>" <?php $this->link(); ?>>
		<?php
	}
}
