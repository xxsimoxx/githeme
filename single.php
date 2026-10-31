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
		<?php the_post_navigation(); ?>
	</div>
	<?php
	if ( comments_open() || get_comments_number() ) {
		comments_template();
	}
endwhile;
get_footer();
