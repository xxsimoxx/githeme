<?php
/**
 * Shared page and post content.
 *
 * @package githeme
 */
$githeme_hide_title = is_page() && githeme_page_title_hidden( get_the_ID() );
$githeme_show_image = has_post_thumbnail() && ! post_password_required();
?>
<article id="post-<?php the_ID(); ?>" <?php post_class( 'entry' ); ?>>
	<?php if ( ! $githeme_hide_title || $githeme_show_image ) : ?>
	<header class="entry-header content-column">
		<?php if ( ! $githeme_hide_title ) : ?>
		<h1><?php echo esc_html( get_the_title() ?: __( 'Untitled', 'githeme' ) ); ?></h1>
		<?php endif; ?>
		<?php if ( is_singular( 'post' ) ) : ?>
			<p class="entry-meta"><time datetime="<?php echo esc_attr( get_the_date( DATE_W3C ) ); ?>"><?php echo esc_html( get_the_date() ); ?></time> · <?php the_author_posts_link(); ?></p>
		<?php endif; ?>
		<?php if ( $githeme_show_image ) : ?>
			<div class="featured-image"><?php the_post_thumbnail( 'large' ); ?></div>
		<?php endif; ?>
	</header>
	<?php endif; ?>
	<div class="entry-content">
		<?php
		the_content();
		wp_link_pages( array( 'before' => '<nav class="page-links" aria-label="' . esc_attr__( 'Page sections', 'githeme' ) . '">', 'after' => '</nav>' ) );
		?>
	</div>
</article>
