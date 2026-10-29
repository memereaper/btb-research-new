<?php
/**
 * Plugin Name: BTB Data Platform
 * Description: Version-pinned, paginated investigation explorer. Does not alter existing Explore pages.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) { exit; }
add_shortcode('btb_data_explorer', function($attrs) {
    $attrs=shortcode_atts(array('release'=>'','congress'=>'118'),$attrs,'btb_data_explorer');
    $api=defined('BTB_DATA_API_URL') ? untrailingslashit(BTB_DATA_API_URL) : '';
    if (!preg_match('#^https://[a-z0-9.-]+(?::443)?(?:/[a-z0-9/_-]*)?$#i',$api) || !preg_match('/^btb-v1-[0-9a-f]{24}$/',$attrs['release'])) {
        return current_user_can('manage_options') ? '<p>Set BTB_DATA_API_URL and a verified release before enabling this explorer.</p>' : '';
    }
    $congress=absint($attrs['congress']);
    if ($congress<113 || $congress>118) { return ''; }
    wp_enqueue_script('btb-data-platform',plugins_url('explorer.js',__FILE__),array(),'1.0.0',true);
    ob_start(); ?>
    <section class="btb-data-explorer bx" data-btb-explorer data-api="<?php echo esc_url($api); ?>" data-release="<?php echo esc_attr($attrs['release']); ?>" data-congress="<?php echo esc_attr($congress); ?>" aria-label="Explore the legislative evidence">
      <h2>Explore the evidence</h2>
      <form aria-label="Filter legislative records">
        <label>Search <input type="search" name="q" maxlength="120"></label>
        <label>Congress <select name="congress"><?php for($c=113;$c<=118;$c++): ?><option value="<?php echo esc_attr($c); ?>" <?php selected($c,$congress); ?>><?php echo esc_html($c); ?>th Congress</option><?php endfor; ?></select></label>
        <label>Chamber <select name="chamber"><option value="">Both chambers</option><option value="house">House</option><option value="senate">Senate</option></select></label>
        <label>Policy area <select name="policy_area"><option value="">All policy areas</option></select></label>
        <label>Bipartisan at introduction <select name="bipartisan"><option value="">Either</option><option value="true">Yes</option><option value="false">No</option></select></label>
        <button type="submit">Search</button><button type="reset">Reset</button>
      </form>
      <p data-status role="status" aria-live="polite">Loading the published record…</p>
      <div data-summary aria-label="Matching outcomes"></div>
      <div style="overflow-x:auto"><table><caption>Matching measures</caption><thead><tr><th scope="col">Measure</th><th scope="col">Title</th><th scope="col">Introduced</th><th scope="col">Furthest stage</th></tr></thead><tbody data-rows></tbody></table></div>
      <button type="button" data-more hidden>Show more</button>
      <p data-evidence role="status"></p>
      <p><small>Published data release: <span data-version><?php echo esc_html($attrs['release']); ?></span>. Results load in pages of 50; the complete record stays on the server.</small></p>
      <noscript>Enable JavaScript to search. The investigation’s narrative and existing data downloads remain available.</noscript>
    </section>
    <?php return ob_get_clean();
});
