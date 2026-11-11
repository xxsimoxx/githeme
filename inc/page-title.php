<?php
/** Per-page template title visibility. @package githeme */

defined( 'ABSPATH' ) || exit;

/** Only an explicit page preference hides the template heading. */
function githeme_page_title_hidden( $post_id ) {
	return 'page' === get_post_type( $post_id ) && '1' === get_post_meta( $post_id, '_githeme_hide_page_title', true );
}

/** Add a native page editor control, independent of content builders. */
function githeme_page_title_meta_box() {
	add_meta_box( 'githeme-page-title', __( 'Page title', 'githeme' ), 'githeme_page_title_control', 'page', 'side' );
}
add_action( 'add_meta_boxes_page', 'githeme_page_title_meta_box' );

/** Render the checkbox and its save nonce. */
function githeme_page_title_control( $post ) {
	wp_nonce_field( 'githeme_page_title_' . $post->ID, 'githeme_page_title_nonce' );
	?>
	<label for="githeme-hide-page-title"><input type="checkbox" id="githeme-hide-page-title" name="githeme_hide_page_title" value="1" <?php checked( githeme_page_title_hidden( $post->ID ) ); ?>> <?php esc_html_e( 'Hide page title', 'githeme' ); ?></label>
	<?php
}

/** Ignore autosaves/revision records and requests not submitted by this control. */
function githeme_save_page_title( $post_id ) {
	if ( 'page' !== get_post_type( $post_id ) || wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) || ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) ) {
		return;
	}
	if ( ! isset( $_POST['githeme_page_title_nonce'] ) || ! is_string( $_POST['githeme_page_title_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['githeme_page_title_nonce'] ) ), 'githeme_page_title_' . $post_id ) || ! current_user_can( 'edit_post', $post_id ) ) {
		return;
	}
	if ( isset( $_POST['githeme_hide_page_title'] ) && is_string( $_POST['githeme_hide_page_title'] ) && '1' === wp_unslash( $_POST['githeme_hide_page_title'] ) ) {
		update_post_meta( $post_id, '_githeme_hide_page_title', '1' );
	} else {
		delete_post_meta( $post_id, '_githeme_hide_page_title' );
	}
}
add_action( 'save_post_page', 'githeme_save_page_title' );
