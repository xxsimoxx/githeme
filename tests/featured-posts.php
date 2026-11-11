<?php
/** WP-CLI eval-file [json]: runtime fixtures and read-only queries; no database writes. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
global $wpdb;
$count = 0;
$check = static function ( $ok, $label ) use ( &$count ) { if ( ! $ok ) { throw new RuntimeException( $label ); } ++$count; };
$widget = new Githeme_Featured_Posts_Widget();
$snapshot = static function () use ( $wpdb, $widget ) { return $wpdb->get_row( $wpdb->prepare( "SELECT option_value, autoload FROM $wpdb->options WHERE option_name = %s", $widget->option_name ), ARRAY_A ); };
$initial = $snapshot();
$widget->get_settings();
$check( $snapshot() === $initial, 'Reading/registering widget settings does not initialize a database option' );
$check( isset( $GLOBALS['wp_widget_factory']->widgets['Githeme_Featured_Posts_Widget'] ), 'Native widget factory registration' );
$check( isset( $GLOBALS['wp_widget_factory']->widgets['WP_Widget_Recent_Posts'] ), 'Native widgets remain registered' );
$check( 3 === $widget::settings( array() )['number'] && 'latest' === $widget::settings( null )['mode'], 'Defaults: three latest posts' );
foreach ( array( -3 => 1, 0 => 1, 51 => 50, 3 => 3 ) as $input => $expected ) {
 $check( $expected === $widget->update( array( 'number' => $input ), array() )['number'], 'Automatic count range' );
}
$clean = $widget->update( array( 'title' => '<script>unsafe</script> A & B', 'mode' => array('manual'), 'number' => array(9), 'category' => -4, 'ids' => '286, 0, -4, 000285, 286, 2x, <b>284</b>, 99999999999999999999999999' ), array() );
$check( ! str_contains( $clean['title'], '<' ) && 'latest' === $clean['mode'] && 3 === $clean['number'] && 0 === $clean['category'], 'Malformed fields sanitized safely' );
$check( '286,285' === $clean['ids'], 'IDs validated, deduplicated and order preserved without guessing invalid tokens' );
$check( null === $widget::query_args( array('mode'=>'manual','ids'=>'invalid') ), 'Empty manual list never falls back to latest posts' );
$check( null === $widget::query_args( array('mode'=>'category','category'=>PHP_INT_MAX) ), 'Deleted/invalid category gives no query' );
$latest_args = $widget::query_args(array());
$check( 'publish' === $latest_args['post_status'] && 'post' === $latest_args['post_type'] && $latest_args['ignore_sticky_posts'] && $latest_args['no_found_rows'], 'Published posts only; no sticky promotion or pagination count' );
$latest = new WP_Query( $latest_args );
$check( count($latest->posts) === 3 && array_reduce($latest->posts, static function($ok,$p){return $ok && 'post'===$p->post_type && 'publish'===$p->post_status;},true), 'Latest query selects three published posts' );
$ids = wp_list_pluck($latest->posts,'ID');
$check( $latest->posts[0]->post_date >= $latest->posts[1]->post_date, 'Latest date ordering' );
$manual_ids = array($ids[2],224,PHP_INT_MAX,$ids[0],517,$ids[1]);
$manual = array('mode'=>'manual','ids'=>implode(',',$manual_ids),'number'=>1,'title'=>'Featured <b>selection</b>');
$manual_query = new WP_Query($widget::query_args($manual));
$check( wp_list_pluck($manual_query->posts,'ID') === array($ids[2],$ids[0],$ids[1]), 'Manual ordering; missing IDs, pages and attachments skipped; automatic count ignored' );
$category = get_category_by_slug('news');
$cat_instance = array('mode'=>'category','category'=>$category->term_id,'number'=>2);
$cat_query = new WP_Query($widget::query_args($cat_instance));
$check( count($cat_query->posts) === 2, 'Category widget count remains independent of main archive page size' );
foreach($cat_query->posts as $item){
 $match=false;foreach(get_the_category($item->ID) as $term){if((int)$term->term_id===(int)$category->term_id||in_array((int)$category->term_id,array_map('intval',get_ancestors($term->term_id,'category')),true)){$match=true;}}
 $check($match,'Category selection includes its descendants');
}
// Synthetic category assignments, without creating or editing terms.
$make = static function($id){return new WP_Term((object)array('term_id'=>$id,'taxonomy'=>'category','name'=>'Category '.$id));};
$terms=array($make(900001),$make(900002),$make(900003));
$term_filter=static function()use(&$terms){return $terms;};
$ancestors=static function($old,$id){return array(900001=>array(),900002=>array(900001),900003=>array(900002,900001),900004=>array(900002,900001))[$id]??$old;};
add_filter('get_the_categories',$term_filter);add_filter('get_ancestors',$ancestors,10,2);
try{
 $check(900003===githeme_category_card_term(0)->term_id,'No-context label chooses deepest assigned category');
 $terms=array($make(900004),$make(900003));$check(900003===githeme_category_card_term(0)->term_id,'No-context tie-break is stable');
 $check(900003===githeme_category_card_term(0,900002)->term_id,'Archive branch logic preserved');
 $terms=array();$check(null===githeme_category_card_term(0),'No assigned terms handled without a fabricated label');
}finally{remove_filter('get_the_categories',$term_filter);remove_filter('get_ancestors',$ancestors,10);}
$display=array('before_widget'=>'<section class="widget githeme-featured-posts">','after_widget'=>'</section>','before_title'=>'<h2 class="widget-title">','after_title'=>'</h2>');
$render=static function($instance)use($widget,$display){ob_start();try{$widget->widget($display,$instance);return ob_get_contents();}finally{ob_end_clean();}};
$globals=array();foreach(array('wp_query','wp_the_query','post','id','authordata','currentday','currentmonth','page','pages','multipage','more','numpages') as $key){$globals[$key]=array(array_key_exists($key,$GLOBALS),$GLOBALS[$key]??null);}
$html=$render($manual);
foreach($globals as $key=>$value){$check($value===array(array_key_exists($key,$GLOBALS),$GLOBALS[$key]??null),'Post/query context restored: '.$key);}
$check(3===substr_count($html,'class="category-card__link"')&&3===substr_count($html,'<h3 '),'Shared cards rendered under optional h2 widget title');
$check(str_contains($html,'Featured selection')&&!str_contains($html,'<b>selection</b>'),'Saved widget title sanitized');
$check(3===substr_count($html,'category-card__excerpt'),'Native excerpts retained');
$untitled=$render(array('mode'=>'manual','ids'=>implode(',',$ids)));
$check(!str_contains($untitled,'widget-title')&&3===substr_count($untitled,'<h2 '),'Untitled widget cards use h2');
$twice=$html.$render($manual);preg_match_all('/\sid="([^"]+)"/',$twice,$matches);
$check(count($matches[1])===count(array_unique($matches[1])),'Repeated widgets have unique article/title IDs');
$check(''===$render(array('mode'=>'manual','ids'=>(string)PHP_INT_MAX))&&''===$render(array('mode'=>'manual','ids'=>''))&&''===$render(array('mode'=>'category','category'=>PHP_INT_MAX)),'Empty results/configurations produce no empty widget wrappers');
$forced_no_image=static function(){return false;};add_filter('has_post_thumbnail',$forced_no_image);
try{$plain=$render(array('number'=>1));$check(!str_contains($plain,'category-card__media')&&str_contains($plain,'category-card__excerpt'),'No-image widget reuses the plain card without placeholders');}finally{remove_filter('has_post_thumbnail',$forced_no_image);}
ob_start();$widget->form(array('title'=>'" onfocus="unsafe','ids'=>'286,285'));$form=ob_get_clean();
$check(str_contains($form,'&quot;')&&!str_contains($form,' onfocus="unsafe'),'Form field values escaped');
$check(3===substr_count($form,'<option value="latest"')+substr_count($form,'<option value="category"')+substr_count($form,'<option value="manual"'),'Three native selection options');
$check($snapshot()===$initial,'Widget option existence/value/autoload unchanged');
$image_ids=get_posts(array('post_type'=>'post','post_status'=>'publish','numberposts'=>1,'fields'=>'ids','meta_key'=>'_thumbnail_id','meta_compare'=>'>','meta_value'=>0,'meta_type'=>'NUMERIC'));
$check(!empty($image_ids),'Existing image post available without creating content');
$fixture_ids=array_slice(array_values(array_unique(array_merge($image_ids,$ids))),0,3);
$image_html=$render(array('mode'=>'manual','ids'=>implode(',',$fixture_ids),'title'=>'Featured selection'));
$check(str_contains($image_html,'category-card__media')&&str_contains($image_html,'<img'),'Widget uses native featured image markup through shared template');
$result=array('checks'=>$count,'html'=>$image_html,'plain'=>$plain,'css'=>file_get_contents(get_template_directory().'/style.css').githeme_font_faces_css().githeme_custom_properties_css(),'form'=>$form);
if(in_array('json',$args??array(),true)){echo wp_json_encode($result);}else{WP_CLI::success($count.' featured posts checks passed. No database writes.');}
