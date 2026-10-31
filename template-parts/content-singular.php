<?php
/**
 * Shared page and post content.
 *
 * @package githeme
 */
?>
<article id="post-<?php the_ID(); ?>" <?php post_class( 'entry' ); ?>>
	<header class="entry-header content-column">
		<h1><?php echo esc_html( get_the_title() ?: __( 'Untitled', 'githeme' ) ); ?></h1>
		<?php if ( is_singular( 'post' ) ) : ?>
			<p class="entry-meta"><time datetime="<?php echo esc_attr( get_the_date( DATE_W3C ) ); ?>"><?php echo esc_html( get_the_date() ); ?></time> · <?php the_author_posts_link(); ?></p>
		<?php endif; ?>
		<?php if ( has_post_thumbnail() && ! post_password_required() ) : ?>
			<div class="featured-image"><?php the_post_thumbnail( 'large' ); ?></div>
		<?php endif; ?>
	</header>
	<div class="entry-content">
		<?php
		the_content();
		wp_link_pages( array( 'before' => '<nav class="page-links" aria-label="' . esc_attr__( 'Page sections', 'githeme' ) . '">', 'after' => '</nav>' ) );
		?>
	</div>
</article>
