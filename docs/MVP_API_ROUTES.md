# MVP API route reference

October 27, 2026: 179 declared route entries. Generated from decorators, not an authorization proof. Blueprints and handlers add session/CSRF/object checks; inspect them directly. HEAD/OPTIONS and app-factory static/health routes are not expanded.

## backend/app/api/__init__.py

| Method | Route | Handler | Declared guards |
| --- | --- | --- | --- |
| GET | `/api/` | [index](../backend/app/api/__init__.py#L541) | See handler / blueprint |
| GET | `/api/auth/csrf` | [csrf](../backend/app/api/__init__.py#L546) | See handler / blueprint |
| POST | `/api/auth/register` | [register](../backend/app/api/__init__.py#L552) | See handler / blueprint |
| POST | `/api/auth/login` | [login](../backend/app/api/__init__.py#L581) | See handler / blueprint |
| POST | `/api/auth/support/login` | [support_login](../backend/app/api/__init__.py#L607) | See handler / blueprint |
| POST | `/api/auth/support/accept-invitation` | [accept_support_invitation](../backend/app/api/__init__.py#L624) | See handler / blueprint |
| POST | `/api/auth/logout` | [logout](../backend/app/api/__init__.py#L669) | authenticated |
| GET | `/api/auth/me` | [current_user](../backend/app/api/__init__.py#L697) | authenticated |
| PATCH | `/api/auth/profile` | [update_account](../backend/app/api/__init__.py#L716) | authenticated |
| POST | `/api/auth/password` | [change_password](../backend/app/api/__init__.py#L747) | authenticated |
| GET | `/api/households` | [list_households](../backend/app/api/__init__.py#L765) | authenticated |
| POST | `/api/households` | [create_household](../backend/app/api/__init__.py#L777) | authenticated |
| GET | `/api/households/<int:household_id>` | [get_household](../backend/app/api/__init__.py#L823) | authenticated |
| PATCH | `/api/households/<int:household_id>` | [rename_household](../backend/app/api/__init__.py#L865) | authenticated |
| POST | `/api/households/<int:household_id>/photo` | [upload_household_photo](../backend/app/api/__init__.py#L888) | authenticated |
| POST | `/api/profiles/<int:profile_id>/photo` | [upload_profile_photo](../backend/app/api/__init__.py#L904) | authenticated |
| GET | `/api/uploads/<path:filename>` | [get_uploaded_image](../backend/app/api/__init__.py#L918) | authenticated |
| GET | `/api/households/<int:household_id>/members` | [list_members](../backend/app/api/__init__.py#L939) | authenticated |
| DELETE | `/api/households/<int:household_id>/members/<int:user_id>` | [remove_member](../backend/app/api/__init__.py#L972) | authenticated |
| POST | `/api/households/<int:household_id>/profiles/<int:profile_id>/share` | [share_profile](../backend/app/api/__init__.py#L989) | authenticated |
| POST | `/api/households/<int:household_id>/invitations` | [invite_member](../backend/app/api/__init__.py#L1017) | authenticated |
| DELETE | `/api/households/<int:household_id>/invitations/<int:invitation_id>` | [revoke_invitation](../backend/app/api/__init__.py#L1084) | authenticated |
| POST | `/api/invitations/accept` | [accept_invitation](../backend/app/api/__init__.py#L1102) | authenticated |
| POST | `/api/households/<int:household_id>/profiles` | [create_profile](../backend/app/api/__init__.py#L1245) | authenticated |
| GET | `/api/profiles/<int:profile_id>` | [get_profile](../backend/app/api/__init__.py#L1267) | authenticated |
| PATCH | `/api/profiles/<int:profile_id>` | [update_profile](../backend/app/api/__init__.py#L1280) | authenticated |
| GET | `/api/profiles/<int:profile_id>/occasions` | [list_occasions](../backend/app/api/__init__.py#L1363) | authenticated |
| POST | `/api/households/<int:household_id>/occasions` | [create_occasion](../backend/app/api/__init__.py#L1385) | authenticated |
| GET | `/api/profiles/<int:profile_id>/wishlists` | [list_wishlists](../backend/app/api/__init__.py#L1433) | authenticated |
| POST | `/api/profiles/<int:profile_id>/wishlists` | [create_wishlist](../backend/app/api/__init__.py#L1445) | authenticated |
| GET | `/api/wishlists/<int:wishlist_id>/items` | [list_wishlist_items](../backend/app/api/__init__.py#L1508) | authenticated |
| POST | `/api/wishlists/<int:wishlist_id>/items` | [create_gift](../backend/app/api/__init__.py#L1528) | authenticated |
| PATCH | `/api/items/<int:item_id>` | [update_gift](../backend/app/api/__init__.py#L1595) | authenticated |
| GET | `/api/wish-edit-targets` | [wish_edit_targets](../backend/app/api/__init__.py#L1658) | authenticated |
| POST | `/api/items/<int:item_id>/organize` | [organize_wish](../backend/app/api/__init__.py#L1667) | authenticated |
| DELETE | `/api/items/<int:item_id>` | [delete_gift](../backend/app/api/__init__.py#L1711) | authenticated |
| POST | `/api/items/<int:item_id>/wishlists` | [link_gift_to_wishlist](../backend/app/api/__init__.py#L1725) | authenticated |
| POST | `/api/items/<int:item_id>/reservations` | [reserve_gift](../backend/app/api/__init__.py#L1821) | authenticated |
| GET | `/api/my-shopping` | [my_shopping](../backend/app/api/__init__.py#L1866) | authenticated |
| PATCH | `/api/reservations/<int:reservation_id>` | [update_reservation](../backend/app/api/__init__.py#L1887) | authenticated |
| GET, PATCH | `/api/notification-preferences` | [notification_preferences](../backend/app/api/__init__.py#L1959) | authenticated |
| GET | `/api/notifications` | [list_notifications](../backend/app/api/__init__.py#L1974) | authenticated |
| POST | `/api/notifications/<int:notification_id>/read` | [mark_notification_read](../backend/app/api/__init__.py#L2016) | authenticated |
| GET | `/api/shopping` | [shopping_hub](../backend/app/api/__init__.py#L2030) | authenticated |
| PUT | `/api/budgets` | [put_budget](../backend/app/api/__init__.py#L2129) | authenticated |
| GET | `/api/budgets` | [list_budgets](../backend/app/api/__init__.py#L2171) | authenticated |
| GET | `/api/support/staff-invitations` | [list_support_staff_invitations](../backend/app/api/__init__.py#L2183) | superuser_required |
| POST | `/api/support/staff-invitations` | [create_support_staff_invitation](../backend/app/api/__init__.py#L2207) | superuser_required |
| POST | `/api/support/family-setup-invitations` | [create_support_family_setup_invitation](../backend/app/api/__init__.py#L2253) | support_required |
| POST | `/api/support/access-requests` | [create_support_access_request](../backend/app/api/__init__.py#L2357) | support_required |
| GET | `/api/support/access-requests` | [list_support_access_requests](../backend/app/api/__init__.py#L2401) | authenticated |
| PATCH | `/api/support/access-requests/<int:request_id>` | [decide_support_access_request](../backend/app/api/__init__.py#L2431) | authenticated |
| DELETE | `/api/support/grants/<int:grant_id>` | [revoke_support_access](../backend/app/api/__init__.py#L2472) | authenticated |
| GET | `/api/support/requests` | [support_request_queue](../backend/app/api/__init__.py#L2494) | support_required |
| GET | `/api/support/grants` | [support_active_grants](../backend/app/api/__init__.py#L2511) | support_required |
| GET | `/api/support/grants/<int:grant_id>/snapshot` | [support_household_snapshot](../backend/app/api/__init__.py#L2528) | support_required |
| PATCH | `/api/support/grants/<int:grant_id>/profiles/<int:profile_id>` | [support_edit_profile](../backend/app/api/__init__.py#L2574) | support_required |
| POST | `/api/help/chat` | [log_help_chat](../backend/app/api/__init__.py#L2671) | authenticated |
| POST | `/api/help/chat/escalate` | [escalate_help_chat](../backend/app/api/__init__.py#L2693) | authenticated |
| GET | `/api/support/help-chats` | [list_help_chats](../backend/app/api/__init__.py#L2725) | superuser_required |
| GET | `/api/support/tickets` | [list_support_tickets](../backend/app/api/__init__.py#L2758) | authenticated |
| GET | `/api/support/staff` | [list_support_staff](../backend/app/api/__init__.py#L2772) | superuser_required |
| POST | `/api/support/tickets` | [create_support_ticket](../backend/app/api/__init__.py#L2780) | authenticated |
| POST | `/api/support/tickets/<int:ticket_id>/messages` | [reply_support_ticket](../backend/app/api/__init__.py#L2812) | authenticated |
| PATCH | `/api/support/tickets/<int:ticket_id>` | [update_support_ticket](../backend/app/api/__init__.py#L2845) | support_required |
| GET | `/api/support/tickets/<int:ticket_id>/merge-candidates` | [ticket_merge_candidates](../backend/app/api/__init__.py#L2893) | support_required |
| POST | `/api/support/tickets/<int:ticket_id>/merge-login` | [merge_ticket_login](../backend/app/api/__init__.py#L2909) | support_required |
| GET | `/api/support/audit-logs` | [list_support_audit_logs](../backend/app/api/__init__.py#L2943) | support_required |
| GET | `/api/households/<int:household_id>/support-audit-logs` | [household_support_audit_logs](../backend/app/api/__init__.py#L2959) | authenticated |
| GET | `/api/households/search` | [search_families](../backend/app/api/__init__.py#L2977) | authenticated |
| GET | `/api/reservations/<int:reservation_id>/co-buyers/options` | [co_buyer_options](../backend/app/api/__init__.py#L3002) | authenticated |
| POST | `/api/reservations/<int:reservation_id>/co-buyers` | [invite_co_buyer](../backend/app/api/__init__.py#L3014) | authenticated |
| GET | `/api/co-buy-invitations` | [co_buy_invitations](../backend/app/api/__init__.py#L3052) | authenticated |
| POST | `/api/co-buy-invitations/<int:invitation_id>/accept` | [accept_co_buy](../backend/app/api/__init__.py#L3060) | authenticated |
| PATCH | `/api/households/<int:household_id>/profiles/<int:profile_id>/relationship` | [update_family_relationship](../backend/app/api/__init__.py#L3073) | authenticated |
| GET | `/api/households/<int:household_id>/holds` | [list_household_holds](../backend/app/api/__init__.py#L3121) | authenticated |
| DELETE | `/api/households/<int:household_id>/holds/<int:reservation_id>` | [release_household_hold](../backend/app/api/__init__.py#L3130) | authenticated |
| GET | `/api/support/grants/<int:grant_id>/holds` | [list_support_holds](../backend/app/api/__init__.py#L3144) | support_required |
| DELETE | `/api/support/grants/<int:grant_id>/holds/<int:reservation_id>` | [release_support_hold](../backend/app/api/__init__.py#L3155) | support_required |
| GET | `/api/gift-recommendations` | [gift_recommendations](../backend/app/api/__init__.py#L3165) | authenticated |
| GET | `/api/gift-discovery` | [gift_discovery](../backend/app/api/__init__.py#L3198) | authenticated |
| PUT, DELETE | `/api/items/<int:item_id>/availability-alert` | [watch_gift_availability](../backend/app/api/__init__.py#L3213) | authenticated |
| POST | `/api/availability-alerts/<int:alert_id>/read` | [read_availability_alert](../backend/app/api/__init__.py#L3235) | authenticated |
| PUT | `/api/items/<int:item_id>/heart` | [heart_gift](../backend/app/api/__init__.py#L3262) | authenticated |
| DELETE | `/api/items/<int:item_id>/heart` | [unheart_gift](../backend/app/api/__init__.py#L3274) | authenticated |
| GET | `/api/wishlist` | [personal_wishlist](../backend/app/api/__init__.py#L3290) | authenticated |
| POST | `/api/private-gifts` | [create_private_gift](../backend/app/api/__init__.py#L3321) | authenticated |
| PATCH | `/api/private-gifts/<int:gift_id>` | [update_private_gift](../backend/app/api/__init__.py#L3351) | authenticated |
| DELETE | `/api/private-gifts/<int:gift_id>` | [delete_private_gift](../backend/app/api/__init__.py#L3365) | authenticated |
| POST | `/api/auth/forgot-password` | [forgot_password](../backend/app/api/__init__.py#L3376) | See handler / blueprint |
| POST | `/api/auth/reset-password` | [reset_password](../backend/app/api/__init__.py#L3402) | See handler / blueprint |
| POST | `/api/households/<int:household_id>/child-accounts` | [create_child_account](../backend/app/api/__init__.py#L3437) | authenticated |
| GET | `/api/households/<int:household_id>/child-accounts` | [list_child_accounts](../backend/app/api/__init__.py#L3475) | authenticated |
| PATCH | `/api/households/<int:household_id>/child-accounts/<int:child_id>` | [manage_child_account](../backend/app/api/__init__.py#L3493) | authenticated |
| POST | `/api/child/login` | [child_login](../backend/app/api/__init__.py#L3529) | See handler / blueprint |
| GET | `/api/child/gift-search` | [child_gift_search](../backend/app/api/__init__.py#L3574) | authenticated |
| GET | `/api/child/me` | [child_me](../backend/app/api/__init__.py#L3592) | authenticated |
| POST | `/api/child/pets/<int:profile_id>/items` | [child_pet_add_gift](../backend/app/api/__init__.py#L3632) | authenticated |
| DELETE | `/api/child/pets/<int:profile_id>/items/<int:item_id>` | [child_pet_remove_gift](../backend/app/api/__init__.py#L3664) | authenticated |
| POST | `/api/child/wishlists/<int:wishlist_id>/items` | [child_add_gift](../backend/app/api/__init__.py#L3681) | authenticated |
| POST | `/api/child/wishlists/<int:wishlist_id>/links` | [child_add_link](../backend/app/api/__init__.py#L3724) | authenticated |
| PATCH | `/api/auth/theme` | [update_account_theme](../backend/app/api/__init__.py#L3754) | authenticated |
| POST | `/api/auth/theme/photo` | [upload_account_background](../backend/app/api/__init__.py#L3768) | authenticated |
| DELETE | `/api/auth/theme/photo` | [remove_account_background](../backend/app/api/__init__.py#L3774) | authenticated |
| POST | `/api/link-preview` | [product_link_preview](../backend/app/api/__init__.py#L3785) | authenticated |
| GET | `/api/households/<int:household_id>/shopper-preview` | [registry_shopper_preview](../backend/app/api/__init__.py#L3795) | authenticated |
| GET | `/api/personal-wishes` | [list_personal_wishes](../backend/app/api/__init__.py#L3870) | authenticated |
| POST | `/api/personal-wishes` | [create_personal_wish](../backend/app/api/__init__.py#L3915) | authenticated |
| PATCH | `/api/personal-wishes/<int:wish_id>` | [update_personal_wish](../backend/app/api/__init__.py#L3953) | authenticated |
| DELETE | `/api/personal-wishes/<int:wish_id>` | [delete_personal_wish](../backend/app/api/__init__.py#L3995) | authenticated |
| GET | `/api/household-session` | [household_session](../backend/app/api/__init__.py#L4012) | authenticated |
| POST | `/api/household-session/pin` | [set_parent_pin](../backend/app/api/__init__.py#L4028) | authenticated |
| POST | `/api/household-session/switch` | [switch_household_profile](../backend/app/api/__init__.py#L4043) | authenticated |
| POST | `/api/household-session/pin/reset` | [request_parent_pin_reset](../backend/app/api/__init__.py#L4105) | authenticated |
| POST | `/api/household-session/pin/reset/confirm` | [confirm_parent_pin_reset](../backend/app/api/__init__.py#L4120) | authenticated |
| POST | `/api/household-session/exit-child` | [exit_child_mode](../backend/app/api/__init__.py#L4136) | authenticated |
| POST | `/api/auth/recovery-code` | [request_recovery_code](../backend/app/api/__init__.py#L4187) | See handler / blueprint |
| POST | `/api/auth/recovery-code/verify` | [verify_recovery_code](../backend/app/api/__init__.py#L4204) | See handler / blueprint |
| POST | `/api/auth/email-change-code` | [request_email_change_code](../backend/app/api/__init__.py#L4225) | authenticated |
| POST | `/api/auth/change-approval/details` | [change_approval_details](../backend/app/api/__init__.py#L4295) | See handler / blueprint |
| GET | `/api/auth/change-approval/photo` | [change_approval_photo](../backend/app/api/__init__.py#L4304) | See handler / blueprint |
| POST | `/api/auth/change-approval` | [confirm_account_change](../backend/app/api/__init__.py#L4317) | See handler / blueprint |
| POST | `/api/households/<int:household_id>/identify-me` | [identify_household_owner](../backend/app/api/__init__.py#L4344) | authenticated |
| GET | `/api/family-connections` | [family_connections](../backend/app/api/__init__.py#L4372) | authenticated |
| POST | `/api/family-connections/<int:other_id>/share` | [share_back_with_connection](../backend/app/api/__init__.py#L4392) | authenticated |
| GET | `/api/child/profiles` | [child_profiles](../backend/app/api/__init__.py#L4440) | authenticated |
| POST | `/api/child/profiles/switch` | [switch_child_profile](../backend/app/api/__init__.py#L4448) | authenticated |
| GET | `/api/themes` | [theme_catalog](../backend/app/api/__init__.py#L4469) | authenticated |
| POST | `/api/support/themes` | [create_shared_theme](../backend/app/api/__init__.py#L4476) | authenticated |
| GET | `/api/themes/<int:theme_id>/art` | [theme_art](../backend/app/api/__init__.py#L4499) | authenticated |
| GET | `/api/families/<int:user_id>/public-wishes` | [family_public_wishes](../backend/app/api/__init__.py#L4510) | authenticated |
| POST | `/api/families/name-search` | [search_adult_families](../backend/app/api/__init__.py#L4522) | authenticated |
| POST | `/api/families/lookup` | [lookup_invite_family](../backend/app/api/__init__.py#L4543) | authenticated |
| GET | `/api/families/lookup-photo/<int:home_id>` | [invite_lookup_photo](../backend/app/api/__init__.py#L4555) | authenticated |
| GET | `/api/invitations/<int:invitation_id>/photo` | [invitation_family_photo](../backend/app/api/__init__.py#L4583) | authenticated |
| GET | `/api/invitations` | [invitation_inbox](../backend/app/api/__init__.py#L4600) | authenticated |
| POST | `/api/invitations/<int:invitation_id>/decline` | [decline_family_invitation](../backend/app/api/__init__.py#L4615) | authenticated |
| GET | `/api/public-wishes` | [public_wish_catalog](../backend/app/api/__init__.py#L4637) | authenticated |
| GET | `/api/public/wishes` | [public_wish_preview](../backend/app/api/__init__.py#L4643) | See handler / blueprint |
| PATCH | `/api/wishlists/<int:list_id>` | [rename_wishlist](../backend/app/api/__init__.py#L4651) | authenticated |
| GET | `/api/child/game-notifications` | [child_game_notifications](../backend/app/api/__init__.py#L4678) | authenticated |
| POST | `/api/child/game-notifications/<int:game_id>/read` | [child_game_notification_read](../backend/app/api/__init__.py#L4689) | authenticated |
| POST | `/api/co-buy-invitations/<int:invitation_id>/decline` | [decline_co_buy](../backend/app/api/__init__.py#L4704) | authenticated |
| GET, PATCH | `/api/wishlists/<int:list_id>/delivery` | [list_delivery](../backend/app/api/__init__.py#L4716) | authenticated |
| GET | `/api/items/<int:item_id>/delivery` | [item_delivery](../backend/app/api/__init__.py#L4743) | authenticated |
| GET | `/api/avatars` | [avatar_catalog](../backend/app/api/__init__.py#L4755) | authenticated |
| POST | `/api/support/avatars` | [publish_avatar](../backend/app/api/__init__.py#L4762) | authenticated |
| GET | `/api/avatars/<int:avatar_id>/art` | [avatar_art](../backend/app/api/__init__.py#L4779) | authenticated |
| GET | `/api/child/profiles/<int:child_id>/photo` | [child_profile_photo](../backend/app/api/__init__.py#L4791) | authenticated |
| DELETE | `/api/households/<int:household_id>/profiles/<int:profile_id>/member` | [remove_linked_family_profile](../backend/app/api/__init__.py#L4804) | authenticated |
| GET, PATCH | `/api/wishlist-budget-preferences` | [wishlist_budget_preferences](../backend/app/api/__init__.py#L4840) | authenticated |

## backend/app/advertising.py

| Method | Route | Handler | Declared guards |
| --- | --- | --- | --- |
| GET | `/api/ads/creative/<int:campaign_id>` | [creative](../backend/app/advertising.py#L115) | See handler / blueprint |
| GET | `/api/ads/config` | [ad_config](../backend/app/advertising.py#L139) | See handler / blueprint |
| POST | `/api/ads/campaigns` | [submit_campaign](../backend/app/advertising.py#L145) | See handler / blueprint |
| POST | `/api/ads/campaigns/<int:campaign_id>/status` | [campaign_status](../backend/app/advertising.py#L182) | See handler / blueprint |
| POST | `/api/ads/campaigns/<int:campaign_id>/checkout` | [campaign_checkout](../backend/app/advertising.py#L194) | See handler / blueprint |
| POST | `/api/ads/stripe-webhook` | [stripe_webhook](../backend/app/advertising.py#L227) | See handler / blueprint |
| GET | `/api/support/ads` | [review_campaigns](../backend/app/advertising.py#L261) | superuser_required |
| PATCH | `/api/support/ads/<int:campaign_id>` | [review_campaign](../backend/app/advertising.py#L267) | superuser_required |
| GET | `/api/ads/active` | [active_ads](../backend/app/advertising.py#L289) | See handler / blueprint |
| POST | `/api/ads/requests` | [submit_advertising_request](../backend/app/advertising.py#L353) | See handler / blueprint |
| GET | `/api/support/advertising-requests` | [advertising_requests](../backend/app/advertising.py#L370) | superuser_required |
| PATCH | `/api/support/advertising-requests/<int:request_id>` | [update_advertising_request](../backend/app/advertising.py#L377) | superuser_required |
| GET, PATCH | `/api/support/advertising-alerts` | [advertising_alert_preferences](../backend/app/advertising.py#L391) | superuser_required |
| POST | `/api/support/advertising-alerts/verify-email` | [request_advertising_alert_verification](../backend/app/advertising.py#L407) | superuser_required |
| POST | `/api/support/advertising-alerts/confirm-email` | [confirm_advertising_alert_email](../backend/app/advertising.py#L439) | superuser_required |

## backend/app/gift_games.py

| Method | Route | Handler | Declared guards |
| --- | --- | --- | --- |
| GET | `/api/games/options` | [game_options](../backend/app/gift_games.py#L141) | authenticated |
| GET | `/api/games` | [list_games](../backend/app/gift_games.py#L147) | authenticated |
| GET | `/api/games/<int:game_id>` | [get_game](../backend/app/gift_games.py#L155) | authenticated |
| POST | `/api/games` | [create_game](../backend/app/gift_games.py#L165) | authenticated |
| POST | `/api/games/<int:game_id>/gifts` | [add_wrapped_gift](../backend/app/gift_games.py#L217) | authenticated |
| POST | `/api/games/<int:game_id>/start` | [start_game](../backend/app/gift_games.py#L243) | authenticated |
| POST | `/api/games/<int:game_id>/assignment` | [my_assignment](../backend/app/gift_games.py#L272) | authenticated |
| POST | `/api/games/<int:game_id>/turn` | [take_turn](../backend/app/gift_games.py#L286) | authenticated |
| POST | `/api/games/<int:game_id>/cancel` | [cancel_game](../backend/app/gift_games.py#L312) | authenticated |
| POST | `/api/games/<int:game_id>/leave` | [leave_game](../backend/app/gift_games.py#L323) | authenticated |
| POST | `/api/games/<int:game_id>/join` | [join_game](../backend/app/gift_games.py#L350) | authenticated |

## backend/app/money.py

| Method | Route | Handler | Declared guards |
| --- | --- | --- | --- |
| GET | `/api/support/money` | [money_overview](../backend/app/money.py#L102) | superuser_required |
| GET | `/api/support/users` | [list_user_accounts](../backend/app/money.py#L108) | superuser_required |

