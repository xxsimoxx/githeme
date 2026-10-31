<?php
/**
 * Standard pages, including a static homepage.
 *
 * @package githeme
 */

get_header();
while ( have_posts() ) :
	the_post();
	get_template_part( 'template-parts/content', 'singular' );
	if ( comments_open() || get_comments_number() ) {
		comments_template();
	}
endwhile;
get_footer();
