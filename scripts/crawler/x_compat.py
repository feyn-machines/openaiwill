"""Twikit 2.3.3 compatibility patches, required for any X GraphQL call.

Adapted from d60/twikit PRs #410 and #419 (MIT):
https://github.com/d60/twikit/pull/410
https://github.com/d60/twikit/pull/419

Copied into the project (from the former social-qingguo-collector skill) so the
crawler owns its dependency and does not import skill code. Importing this module
installs the patches onto twikit's ClientTransaction/GQLClient.
"""
import re

from twikit.x_client_transaction.transaction import ClientTransaction


async def compatible_indices(self, home_page_response, session, headers):
    response = self.validate_response(home_page_response) or self.home_page_response
    text = str(response)
    old = re.search(r'''["']ondemand\.s["']:\s*["'](\w+)["']''', text)
    index = re.search(r''',(\d+):["']ondemand\.s["']''', text)
    matched = old or (re.search(r',{}:"([0-9a-f]+)"'.format(index.group(1)), text) if index else None)
    if not matched:
        raise RuntimeError('ondemand_script_reference_missing')
    response = await session.get('https://abs.twimg.com/responsive-web/client-web/ondemand.s.' + matched.group(1) + 'a.js', headers=headers)
    response.raise_for_status()
    indices = [int(v) for v in re.findall(r'\[(\d+)\],\s*16', response.text)]
    if not indices:
        raise RuntimeError('key_byte_indices_missing_after_compatibility_patch')
    return indices[0], indices[1:]


ClientTransaction.get_indices = compatible_indices


# Search compatibility: upstream d60/twikit PR #419.
from twikit.client.gql import GQLClient

SEARCH_FEATURES = {'rweb_video_screen_enabled': False, 'rweb_cashtags_enabled': True, 'profile_label_improvements_pcf_label_in_post_enabled': True, 'responsive_web_profile_redirect_enabled': False, 'rweb_tipjar_consumption_enabled': False, 'verified_phone_label_enabled': False, 'creator_subscriptions_tweet_preview_api_enabled': True, 'responsive_web_graphql_timeline_navigation_enabled': True, 'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False, 'premium_content_api_read_enabled': False, 'communities_web_enable_tweet_community_results_fetch': True, 'c9s_tweet_anatomy_moderator_badge_enabled': True, 'responsive_web_grok_analyze_button_fetch_trends_enabled': False, 'responsive_web_grok_analyze_post_followups_enabled': True, 'responsive_web_jetfuel_frame': True, 'responsive_web_grok_share_attachment_enabled': True, 'responsive_web_grok_annotations_enabled': True, 'articles_preview_enabled': True, 'responsive_web_edit_tweet_api_enabled': True, 'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True, 'view_counts_everywhere_api_enabled': True, 'longform_notetweets_consumption_enabled': True, 'responsive_web_twitter_article_tweet_consumption_enabled': True, 'content_disclosure_indicator_enabled': True, 'content_disclosure_ai_generated_indicator_enabled': True, 'responsive_web_grok_show_grok_translated_post': True, 'responsive_web_grok_analysis_button_from_backend': True, 'post_ctas_fetch_enabled': True, 'freedom_of_speech_not_reach_fetch_enabled': True, 'standardized_nudges_misinfo': True, 'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True, 'longform_notetweets_rich_text_read_enabled': True, 'longform_notetweets_inline_media_enabled': False, 'responsive_web_grok_image_annotation_enabled': True, 'responsive_web_grok_imagine_annotation_enabled': True, 'responsive_web_grok_community_note_auto_translation_is_enabled': True, 'responsive_web_enhance_cards_enabled': False}


async def compatible_search(self, query, product, count, cursor):
    variables = {'rawQuery': query, 'count': count, 'querySource': 'typed_query', 'product': product, 'withGrokTranslatedBio': True}
    if cursor:
        variables['cursor'] = cursor
    return await self.gql_get('https://x.com/i/api/graphql/R0u1RWRf748KzyGBXvOYRA/SearchTimeline', variables, SEARCH_FEATURES)


GQLClient.search_timeline = compatible_search
