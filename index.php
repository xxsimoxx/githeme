<?php
/**
 * Default listing and template fallback.
 *
 * @package githeme
 */

get_header();
?>
<div class="content-column">
	<header class="page-header">
		<?php if ( is_search() ) : ?>
			<h1><?php
			/* translators: %s: search query. */
			printf( esc_html__( 'Search results for: %s', 'githeme' ), esc_html( get_search_query( false ) ) );
			?></h1>
		<?php elseif ( is_archive() ) : ?>
			<?php the_archive_title( '<h1>', '</h1>' ); ?>
			<?php the_archive_description( '<div class="archive-description">', '</div>' ); ?>
		<?php else : ?>
			<h1><?php echo esc_html( is_home() && get_option( 'page_for_posts' ) ? get_the_title( (int) get_option( 'page_for_posts' ) ) : __( 'Latest posts', 'githeme' ) ); ?></h1>
		<?php endif; ?>
	</header>
	<?php if ( have_posts() ) : ?>
		<?php while ( have_posts() ) : ?>
			<?php the_post(); ?>
			<article id="post-<?php the_ID(); ?>" <?php post_class( 'entry entry-summary' ); ?>>
				<h2><a href="<?php the_permalink(); ?>"><?php echo esc_html( get_the_title() ?: __( 'Untitled', 'githeme' ) ); ?></a></h2>
				<?php the_excerpt(); ?>
			</article>
		<?php endwhile; ?>
		<?php the_posts_pagination(); ?>
	<?php else : ?>
		<p><?php esc_html_e( 'No content found.', 'githeme' ); ?></p>
		<?php get_search_form(); ?>
	<?php endif; ?>
</div>
<?php get_footer(); ?>
