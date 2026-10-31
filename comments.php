<?php
/**
 * Native comment list and form.
 *
 * @package githeme
 */

if ( post_password_required() ) {
	return;
}
?>
<section id="comments" class="comments-area content-column" aria-label="<?php esc_attr_e( 'Comments', 'githeme' ); ?>">
	<?php if ( have_comments() ) : ?>
		<h2><?php esc_html_e( 'Comments', 'githeme' ); ?></h2>
		<ol class="comment-list">
			<?php wp_list_comments( array( 'style' => 'ol', 'short_ping' => true, 'avatar_size' => 48 ) ); ?>
		</ol>
		<?php the_comments_pagination(); ?>
	<?php endif; ?>
	<?php if ( ! comments_open() && get_comments_number() ) : ?>
		<p><?php esc_html_e( 'Comments are closed.', 'githeme' ); ?></p>
	<?php endif; ?>
	<?php comment_form(); ?>
</section>
