<?php
/** Native widget adapter for the existing gallery shortcode slider. @package githeme */

defined( 'ABSPATH' ) || exit;

class Githeme_Gallery_Slider_Widget extends WP_Widget {
	public function __construct() {
		parent::__construct( 'githeme-gallery-slider-widget', __( 'GiTheme – Gallery Slider', 'githeme' ), array( 'classname' => 'githeme-gallery-widget', 'description' => __( 'A native gallery slider using an ordered list of image attachment IDs.', 'githeme' ) ) );
	}

	/** Registration alone must not create an empty widget option. */
	public function get_settings() {
		return false === get_option( $this->option_name, false ) ? array() : parent::get_settings();
	}

	/** Widget API values are already unslashed; validate IDs before constructing a shortcode. */
	public static function settings( $instance ) {
		$instance = is_array( $instance ) ? $instance : array();
		$ids = array();
		foreach ( explode( ',', is_string( $instance['ids'] ?? null ) ? $instance['ids'] : '' ) as $token ) {
			$token = ltrim( trim( $token ), '0' );
			$id = preg_match( '/^[1-9][0-9]*$/D', $token ) ? filter_var( $token, FILTER_VALIDATE_INT, array( 'options' => array( 'min_range' => 1 ) ) ) : false;
			if ( false !== $id ) {
				$ids[] = $id;
			}
		}
		return array(
			'title' => is_scalar( $instance['title'] ?? null ) ? sanitize_text_field( (string) $instance['title'] ) : '',
			'ids' => implode( ',', array_unique( $ids ) ),
		);
	}

	public function update( $new_instance, $old_instance ) {
		return self::settings( $new_instance );
	}

	public function widget( $args, $instance ) {
		$instance = self::settings( $instance );
		$ids = array();
		foreach ( array_filter( array_map( 'intval', explode( ',', $instance['ids'] ) ) ) as $id ) {
			$attachment = get_post( $id );
			if ( $attachment && 'attachment' === $attachment->post_type && in_array( $attachment->post_status, array( 'inherit', 'publish' ), true ) && wp_attachment_is_image( $attachment ) ) {
				$ids[] = $id;
			}
		}
		if ( ! $ids || ! shortcode_exists( 'gallery' ) ) {
			return;
		}
		// Use the complete shortcode pipeline, including the existing do_shortcode_tag enhancement.
		$html = do_shortcode( '[gallery layout="slider" ids="' . implode( ',', $ids ) . '"]' );
		if ( '' === trim( $html ) ) {
			return;
		}
		$title = apply_filters( 'widget_title', $instance['title'], $instance, $this->id_base );
		echo $args['before_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native registered sidebar markup.
		if ( is_string( $title ) && '' !== trim( $title ) ) {
			echo $args['before_title'] . wp_kses_post( $title ) . $args['after_title']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native sidebar wrappers and sanitized title.
		}
		echo $html; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native shortcode output; preserve media markup and filters.
		echo $args['after_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native registered sidebar markup.
	}

	public function form( $instance ) {
		$instance = self::settings( $instance );
		?>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'title' ) ); ?>"><?php esc_html_e( 'Title (optional)', 'githeme' ); ?></label>
		<input class="widefat" id="<?php echo esc_attr( $this->get_field_id( 'title' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'title' ) ); ?>" type="text" value="<?php echo esc_attr( $instance['title'] ); ?>"></p>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'ids' ) ); ?>"><?php esc_html_e( 'Image attachment IDs', 'githeme' ); ?></label>
		<input class="widefat" id="<?php echo esc_attr( $this->get_field_id( 'ids' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'ids' ) ); ?>" type="text" value="<?php echo esc_attr( $instance['ids'] ); ?>" aria-describedby="<?php echo esc_attr( $this->get_field_id( 'ids-help' ) ); ?>">
		<small id="<?php echo esc_attr( $this->get_field_id( 'ids-help' ) ); ?>"><?php esc_html_e( 'Comma-separated attachment IDs, displayed in this order. Missing, deleted, and non-image attachments are skipped. One image remains a static gallery.', 'githeme' ); ?></small></p>
		<?php
	}
}

function githeme_register_gallery_slider_widget() {
	register_widget( 'Githeme_Gallery_Slider_Widget' );
}
add_action( 'widgets_init', 'githeme_register_gallery_slider_widget' );
