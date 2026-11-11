<?php
/** Native content and media in a category card. @package githeme */

$githeme_term = githeme_category_card_term( get_the_ID(), (int) ( $args['category_id'] ?? 0 ) );
$githeme_title_id = wp_unique_id( 'category-card-title-' );
$githeme_card_id = $args['card_id'] ?? 'post-' . get_the_ID();
$githeme_heading = 3 === ( $args['heading_level'] ?? 2 ) ? 'h3' : 'h2';
$githeme_thumbnail = has_post_thumbnail() ? get_the_post_thumbnail( get_the_ID(), 'large' ) : '';
?>
<article id="<?php echo esc_attr( $githeme_card_id ); ?>" <?php post_class( 'category-card' ); ?>>
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
		<?php // The heading tag is restricted to h2/h3 above. ?>
		<<?php echo $githeme_heading; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Fixed tag allowlist. ?> id="<?php echo esc_attr( $githeme_title_id ); ?>" class="category-card__title"><?php echo esc_html( get_the_title() ?: __( 'Untitled', 'githeme' ) ); ?></<?php echo $githeme_heading; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Fixed tag allowlist. ?>>
	</a>
	<div class="category-card__excerpt"><?php the_excerpt(); ?></div>
</article>
