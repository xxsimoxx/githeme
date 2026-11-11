<?php
/** Category-only card listing. @package githeme */

get_header();
?>
<div class="category-archive">
	<header class="page-header">
		<?php the_archive_title( '<h1>', '</h1>' ); ?>
		<?php the_archive_description( '<div class="archive-description">', '</div>' ); ?>
	</header>
	<?php if ( have_posts() ) : ?>
		<div class="category-grid">
			<?php while ( have_posts() ) : ?>
				<?php the_post(); ?>
				<?php get_template_part( 'template-parts/content', 'category-card', array( 'category_id' => get_queried_object_id() ) ); ?>
			<?php endwhile; ?>
		</div>
		<?php the_posts_pagination(); ?>
	<?php else : ?>
		<p><?php esc_html_e( 'No content found.', 'githeme' ); ?></p>
		<?php get_search_form(); ?>
	<?php endif; ?>
</div>
<?php get_footer(); ?>
