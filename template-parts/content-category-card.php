<?php
/** Native content and media in a category card. @package githeme */

$githeme_term = githeme_category_card_term( get_the_ID(), (int) ( $args['category_id'] ?? 0 ) );
$githeme_title_id = wp_unique_id( 'category-card-title-' );
$githeme_thumbnail = has_post_thumbnail() ? get_the_post_thumbnail( get_the_ID(), 'large' ) : '';
?>
<article id="post-<?php the_ID(); ?>" <?php post_class( 'category-card' ); ?>>
	<a class="category-card__link" href="<?php echo esc_url( get_permalink() ); ?>" aria-labelledby="<?php echo esc_attr( $githeme_title_id ); ?>">
		<?php if ( '' !== trim( $githeme_thumbnail ) ) : ?>
			<div class="category-card__media">
				<?php echo $githeme_thumbnail; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Preserve native image markup. ?>
				<?php if ( $githeme_term ) : ?>
					<span class="category-card__term"><?php echo esc_html( $githeme_term->name ); ?></span>
				<?php endif; ?>
			</div>
		<?php elseif ( $githeme_term ) : ?>
			<span class="category-card__term-plain"><?php echo esc_html( $githeme_term->name ); ?></span>
		<?php endif; ?>
		<h2 id="<?php echo esc_attr( $githeme_title_id ); ?>" class="category-card__title"><?php echo esc_html( get_the_title() ?: __( 'Untitled', 'githeme' ) ); ?></h2>
	</a>
	<div class="category-card__excerpt"><?php the_excerpt(); ?></div>
</article>
