<?php
/**
 * Single posts.
 *
 * @package githeme
 */

get_header();
while ( have_posts() ) :
	the_post();
	get_template_part( 'template-parts/content', 'singular' );
	?>
	<div class="content-column">
		<?php
		// Reuse the core archive pagination translations and their contexts.
		the_post_navigation( array(
			// phpcs:ignore WordPress.WP.I18n.MissingArgDomain -- Intentionally use the core default text domain for its existing pagination translation.
			'prev_text' => esc_html_x( 'Previous', 'previous set of posts' ),
			// phpcs:ignore WordPress.WP.I18n.MissingArgDomain -- Intentionally use the core default text domain for its existing pagination translation.
			'next_text' => esc_html_x( 'Next', 'next set of posts' ),
		) );
		?>
	</div>
	<?php
	if ( comments_open() || get_comments_number() ) {
		comments_template();
	}
endwhile;
get_footer();
