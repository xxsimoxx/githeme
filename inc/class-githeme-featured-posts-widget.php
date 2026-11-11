<?php
/** Native featured posts widget using the shared archive cards. @package githeme */

defined( 'ABSPATH' ) || exit;

class Githeme_Featured_Posts_Widget extends WP_Widget {
	public function __construct() {
		parent::__construct( 'githeme-featured-posts', __( 'GiTheme – Featured Posts', 'githeme' ), array( 'classname' => 'githeme-featured-posts', 'description' => __( 'Post cards selected by date, category, or an ordered list of IDs.', 'githeme' ) ) );
	}

	/** Do not initialize an empty database option just by registering an unused widget. */
	public function get_settings() {
		return false === get_option( $this->option_name, false ) ? array() : parent::get_settings();
	}

	/** Normalize both saved and incoming instances; native widget APIs handle authorization. */
	public static function settings( $instance ) {
		$instance = is_array( $instance ) ? $instance : array();
		$mode = $instance['mode'] ?? 'latest';
		$number = $instance['number'] ?? 3;
		$category = $instance['category'] ?? 0;
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
			'mode' => in_array( $mode, array( 'latest', 'category', 'manual' ), true ) ? $mode : 'latest',
			'number' => is_scalar( $number ) && false !== filter_var( $number, FILTER_VALIDATE_INT ) ? max( 1, min( 50, (int) $number ) ) : 3,
			'category' => is_scalar( $category ) ? (int) filter_var( $category, FILTER_VALIDATE_INT, array( 'options' => array( 'min_range' => 1 ) ) ) : 0,
			'ids' => implode( ',', array_unique( $ids ) ),
		);
	}

	/** Return no query for an empty manual list or an unavailable category. */
	public static function query_args( $instance ) {
		$instance = self::settings( $instance );
		$args = array( 'post_type' => 'post', 'post_status' => 'publish', 'posts_per_page' => $instance['number'], 'no_found_rows' => true, 'ignore_sticky_posts' => true, 'orderby' => array( 'date' => 'DESC', 'ID' => 'DESC' ) );
		if ( 'category' === $instance['mode'] ) {
			$term = get_term( $instance['category'], 'category' );
			if ( ! $term instanceof WP_Term ) {
				return null;
			}
			$args['cat'] = $term->term_id;
		} elseif ( 'manual' === $instance['mode'] ) {
			if ( '' === $instance['ids'] ) {
				return null;
			}
			$args['post__in'] = array_map( 'intval', explode( ',', $instance['ids'] ) );
			$args['posts_per_page'] = count( $args['post__in'] );
			$args['orderby'] = 'post__in';
			$args['order'] = 'ASC';
		}
		return $args;
	}

	public function update( $new_instance, $old_instance ) {
		return self::settings( $new_instance );
	}

	public function widget( $args, $instance ) {
		$instance = self::settings( $instance );
		$query_args = self::query_args( $instance );
		if ( null === $query_args ) {
			return;
		}
		$query = new WP_Query( $query_args );
		if ( ! $query->have_posts() ) {
			return;
		}
		$title = apply_filters( 'widget_title', $instance['title'], $instance, $this->id_base );
		$has_title = is_string( $title ) && '' !== trim( $title );
		// Preserve an enclosing custom loop as well as the main query's post data.
		$original = array();
		foreach ( array( 'post', 'id', 'authordata', 'currentday', 'currentmonth', 'page', 'pages', 'multipage', 'more', 'numpages' ) as $key ) {
			$original[ $key ] = array( array_key_exists( $key, $GLOBALS ), $GLOBALS[ $key ] ?? null );
		}
		try {
			echo $args['before_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native registered sidebar markup.
			if ( $has_title ) {
				echo $args['before_title'] . wp_kses_post( $title ) . $args['after_title']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native sidebar wrappers, sanitized title.
			}
			echo '<div class="githeme-post-cards"><div class="category-grid">';
			while ( $query->have_posts() ) {
				$query->the_post();
				get_template_part( 'template-parts/content', 'category-card', array( 'category_id' => 'category' === $instance['mode'] ? $instance['category'] : 0, 'card_id' => wp_unique_id( 'githeme-card-' ), 'heading_level' => $has_title ? 3 : 2 ) );
			}
			echo '</div></div>';
			echo $args['after_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native registered sidebar markup.
		} finally {
			foreach ( $original as $key => $value ) {
				if ( $value[0] ) {
					$GLOBALS[ $key ] = $value[1];
				} else {
					unset( $GLOBALS[ $key ] );
				}
			}
		}
	}

	public function form( $instance ) {
		$instance = self::settings( $instance );
		?>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'title' ) ); ?>"><?php esc_html_e( 'Title (optional)', 'githeme' ); ?></label>
		<input class="widefat" id="<?php echo esc_attr( $this->get_field_id( 'title' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'title' ) ); ?>" type="text" value="<?php echo esc_attr( $instance['title'] ); ?>"></p>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'mode' ) ); ?>"><?php esc_html_e( 'Selection', 'githeme' ); ?></label>
		<select class="widefat" id="<?php echo esc_attr( $this->get_field_id( 'mode' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'mode' ) ); ?>">
			<?php foreach ( array( 'latest' => __( 'Latest published posts', 'githeme' ), 'category' => __( 'Posts in a category', 'githeme' ), 'manual' => __( 'Manual post IDs', 'githeme' ) ) as $value => $label ) : ?>
				<option value="<?php echo esc_attr( $value ); ?>" <?php selected( $instance['mode'], $value ); ?>><?php echo esc_html( $label ); ?></option>
			<?php endforeach; ?>
		</select></p>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'category' ) ); ?>"><?php esc_html_e( 'Category (category mode)', 'githeme' ); ?></label>
		<?php wp_dropdown_categories( array( 'show_option_none' => __( 'Select a category', 'githeme' ), 'option_none_value' => 0, 'hide_empty' => false, 'hierarchical' => true, 'name' => $this->get_field_name( 'category' ), 'id' => $this->get_field_id( 'category' ), 'class' => 'widefat', 'selected' => $instance['category'] ) ); ?></p>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'number' ) ); ?>"><?php esc_html_e( 'Number of posts (automatic modes, 1–50)', 'githeme' ); ?></label>
		<input id="<?php echo esc_attr( $this->get_field_id( 'number' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'number' ) ); ?>" type="number" min="1" max="50" value="<?php echo esc_attr( $instance['number'] ); ?>"></p>
		<p><label for="<?php echo esc_attr( $this->get_field_id( 'ids' ) ); ?>"><?php esc_html_e( 'Post IDs (manual mode)', 'githeme' ); ?></label>
		<input class="widefat" id="<?php echo esc_attr( $this->get_field_id( 'ids' ) ); ?>" name="<?php echo esc_attr( $this->get_field_name( 'ids' ) ); ?>" type="text" value="<?php echo esc_attr( $instance['ids'] ); ?>">
		<small><?php esc_html_e( 'Comma-separated IDs, displayed in this order. Missing or unpublished posts are skipped; the automatic count is ignored.', 'githeme' ); ?></small></p>
		<?php
	}
}

function githeme_register_featured_posts_widget() {
	register_widget( 'Githeme_Featured_Posts_Widget' );
}
add_action( 'widgets_init', 'githeme_register_featured_posts_widget' );
