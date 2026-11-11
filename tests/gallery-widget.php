<?php
/** WP-CLI eval-file [json]. Read-only media queries and runtime widget instances. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
global $wpdb;
$count=0;$check=static function($ok,$label)use(&$count){if(!$ok){throw new RuntimeException($label);}++$count;};
$widget=new Githeme_Gallery_Slider_Widget();
$state=static function()use($wpdb){return $wpdb->get_results("SELECT option_name, option_value, autoload FROM $wpdb->options WHERE option_name IN ('widget_githeme-gallery-slider-widget','widget_githeme-featured-posts','sidebars_widgets','theme_mods_githeme') ORDER BY option_name",ARRAY_A);};
$initial=$state();$scripts=clone wp_scripts();$callback=$GLOBALS['shortcode_tags']['gallery'];
$args_display=array('before_widget'=>'<section class="widget githeme-gallery-widget">','after_widget'=>'</section>','before_title'=>'<h2 class="widget-title">','after_title'=>'</h2>');
$render=static function($settings)use($widget,$args_display){static $number=0;$display=$args_display;$display['before_widget']='<section id="'.$widget->id_base.'-'.(++$number).'" class="widget githeme-gallery-widget">';ob_start();try{$widget->widget($display,$settings);return ob_get_contents();}finally{ob_end_clean();}};
$calls=0;$observer=static function($out)use(&$calls){++$calls;return $out;};
$seen=array();$attrs=static function($out)use(&$seen){$seen=$out;return $out;};
add_filter('post_gallery',$observer,-100);add_filter('shortcode_atts_gallery',$attrs,20);
try{
 $check(isset($GLOBALS['wp_widget_factory']->widgets['Githeme_Gallery_Slider_Widget']),'Native widget registered');
 $check('githeme-gallery-slider'!==$widget->id_base,'Native sidebar instance IDs use a prefix distinct from slider viewport IDs');
 $check(isset($GLOBALS['wp_widget_factory']->widgets['Githeme_Featured_Posts_Widget'],$GLOBALS['wp_widget_factory']->widgets['WP_Widget_Media_Gallery']),'Featured Posts and native Gallery remain registered');
 $widget->get_settings();$check($state()===$initial,'Registration/settings read does not initialize or change options');
 $check(array('title'=>'','ids'=>'')===$widget::settings(null),'Empty defaults');
 $clean=$widget->update(array('title'=>'<b>A & B</b>','ids'=>' 0012,0,-9,13,12,14x,<b>15</b>,99999999999999999999999'),array());
 $check('A & B'===$clean['title']&&'12,13'===$clean['ids'],'Canonical ordered IDs and sanitized title');
 $check($clean===unserialize(serialize($clean),array('allowed_classes'=>false)),'Settings survive native serialized-option format');
 $check(''===$widget::settings(array('ids'=>array(12)))['ids'],'Malformed settings rejected');
 $ids=get_posts(array('post_type'=>'attachment','post_status'=>'inherit','post_mime_type'=>'image','numberposts'=>5,'fields'=>'ids'));
 $check(count($ids)>=3,'Existing images available; no fixture content created');
 wp_dequeue_script('githeme-gallery-slider');$before=$calls;
 $check(''===$render(array())&&''===$render(array('ids'=>'-1,0,invalid'))&&''===$render(array('ids'=>(string)PHP_INT_MAX)),'Invalid/missing image selections emit no widget wrappers');
 $check($before===$calls&&!wp_script_is('githeme-gallery-slider','enqueued'),'No shortcode rendering or slider script for empty input');
 $single=$render(array('ids'=>(string)$ids[0]));
 $check(str_contains($single,'<img')&&!str_contains($single,'githeme-gallery-slider__viewport'),'Single image keeps native static gallery');
 $check(!wp_script_is('githeme-gallery-slider','enqueued'),'Single image does not enqueue slider script');
 $ordered=array_reverse($ids);$instance=array('title'=>'Gallery <b>selection</b>','ids'=>implode(',',array_merge(array($ordered[0],224,PHP_INT_MAX),$ordered,array($ordered[0]))));
 $before=$calls;$html=$render($instance);
 $check($calls===$before+1,'Widget invokes native gallery exactly once');
 $check('large'===$seen['size']&&implode(',',$ordered)===$seen['include']&&'post__in'===$seen['orderby'],'Shared slider defaults and specified image order preserved');
 $check(str_contains($html,'Gallery selection')&&!str_contains($html,'<b>selection</b>'),'Optional title sanitized');
 $check(str_contains($html,'githeme-gallery-slider__viewport')&&str_contains($html,'tabindex="0"')&&str_contains($html,'aria-label='),'Existing accessible slider markup reused');
 $check(wp_script_is('githeme-gallery-slider','enqueued'),'Enhanced slider enqueues existing handle');
 $second=$render($instance);$queue=wp_scripts()->queue;
 $check(1===count(array_keys($queue,'githeme-gallery-slider',true)),'Multiple widgets enqueue the script only once');
 preg_match_all('/\sid=[\'"]([^\'"]+)[\'"]/',$html.$second,$matches);
 $check(count($matches[1])===count(array_unique($matches[1])),'Multiple widget/native gallery viewport IDs unique');
 $labels=wp_scripts()->get_data('githeme-gallery-slider','data');
 $check(1===substr_count($labels,'var githemeGalleryLabels'),'Localized button labels added once');
 $plain=$render(array('ids'=>implode(',',$ordered)));
 $check(!str_contains($plain,'widget-title'),'Widget title optional');
 ob_start();$widget->form(array('title'=>'" onfocus="unsafe','ids'=>'1"] [unexpected]'));$form=ob_get_clean();
 $check(str_contains($form,'&quot;')&&!str_contains($form,' onfocus="unsafe')&&str_contains($form,'aria-describedby='),'Form attributes escaped and instructions associated');
 $check($callback===$GLOBALS['shortcode_tags']['gallery'],'Native shortcode callback unchanged');
 $check($state()===$initial,'Widget/sidebar/theme options and autoload unchanged');
 ob_start();wp_print_scripts(array('githeme-gallery-slider'));$script=ob_get_clean();
 $result=array('checks'=>$count,'html'=>$html,'second'=>$second,'single'=>$single,'script'=>$script,'form'=>$form,'css'=>githeme_font_faces_css().githeme_custom_properties_css());
}finally{remove_filter('post_gallery',$observer,-100);remove_filter('shortcode_atts_gallery',$attrs,20);$GLOBALS['wp_scripts']=$scripts;}
if(in_array('json',$args??array(),true)){echo wp_json_encode($result);}else{WP_CLI::success($count.' gallery widget checks passed. No database writes.');}
