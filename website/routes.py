# -*- coding: utf-8 -*-
import httplib as http

from flask import redirect

import framework
from framework import status
from framework.exceptions import HTTPError
from framework import (Rule, process_rules,
                       WebRenderer, json_renderer,
                       render_mako_string)
from framework.auth import views as auth_views
from framework.auth import get_current_user

from website import settings, language, util
from website import views as website_views
from website.addons.base import views as addon_views
from website.search import views as search_views
from website.discovery import views as discovery_views
from website.profile import views as profile_views
from website.project import views as project_views
from website.assets import env as assets_env


def get_globals():
    """Context variables that are available for every template rendered by
    OSFWebRenderer.

    """
    user = framework.auth.get_current_user()
    return {
        'user_name': user.username if user else '',
        'user_full_name': user.fullname if user else '',
        'user_id': user._primary_key if user else '',
        'user_url': user.url if user else '',
        'user_api_url': user.api_url if user else '',
        'display_name': framework.auth.get_display_name(user.username) if user else '',
        'use_cdn': settings.USE_CDN_FOR_CLIENT_LIBS,
        'piwik_host': settings.PIWIK_HOST,
        'piwik_site_id': settings.PIWIK_SITE_ID,
        'dev_mode': settings.DEV_MODE,
        'allow_login': settings.ALLOW_LOGIN,
        'status': framework.status.pop_status_messages(),
        'js_all': assets_env['js'].urls(),
        'css_all': assets_env['css'].urls(),
        'js_bottom': assets_env['js_bottom'].urls(),
        'domain': settings.DOMAIN,
        'language': language,
        'web_url_for': util.web_url_for,
        'api_url_for': util.api_url_for,
    }


class OsfWebRenderer(WebRenderer):

    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)

#: Use if a view only redirects or raises error
notemplate = OsfWebRenderer('', render_mako_string)


def favicon():
    return framework.send_from_directory(
        settings.STATIC_FOLDER,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


def goodbye(**kwargs):
    # Redirect to dashboard if logged in
    if get_current_user():
        return redirect(util.web_url_for('dashboard'))
    status.push_status_message(language.LOGOUT, 'info')
    return {}


def make_url_map(app):
    '''Set up all the routes for the OSF app.

    :param app: A Flask/Werkzeug app to bind the rules to.
    '''

    # Set default views to 404, using URL-appropriate renderers
    process_rules(app, [
        Rule('/<path:_>', ['get', 'post'], HTTPError(http.NOT_FOUND),
             OsfWebRenderer('', render_mako_string)),
        Rule('/api/v1/<path:_>', ['get', 'post'],
             HTTPError(http.NOT_FOUND), json_renderer),
    ])

    ### GUID ###
    process_rules(app, [

        Rule(
            [
                '/<guid>/',
                '/<guid>/<path:suffix>',
            ],
            ['get', 'post', 'put', 'patch', 'delete'],
            website_views.resolve_guid,
            OsfWebRenderer('', render_mako_string),
        ),

        Rule(
            [
                '/api/v1/<guid>/',
                '/api/v1/<guid>/<path:suffix>',
            ],
            ['get', 'post', 'put', 'patch', 'delete'],
            website_views.resolve_guid,
            json_renderer,
        ),

    ])

    process_rules(app, [
        Rule('/favicon.ico', 'get', favicon, json_renderer),
    ])

    ### Base ###

    process_rules(app, [

        Rule('/dashboard/', 'get', website_views.dashboard, OsfWebRenderer('dashboard.mako')),
        Rule('/reproducibility/', 'get', website_views.reproducibility, OsfWebRenderer('', render_mako_string)),

        Rule('/about/', 'get', {}, OsfWebRenderer('public/pages/about.mako')),
        Rule('/howosfworks/', 'get', {}, OsfWebRenderer('public/pages/howosfworks.mako')),
        Rule('/faq/', 'get', {}, OsfWebRenderer('public/pages/faq.mako')),
        Rule('/getting-started/', 'get', {}, OsfWebRenderer('public/pages/getting_started.mako')),
        Rule('/explore/', 'get', {}, OsfWebRenderer('public/explore.mako')),
        Rule(['/messages/', '/help/'], 'get', {}, OsfWebRenderer('public/comingsoon.mako')),

        Rule(
            '/view/<meeting>/',
            'get',
            project_views.email.conference_results,
            OsfWebRenderer('public/pages/meeting.mako'),
        ),

        Rule(
            '/view/<meeting>/plain/',
            'get',
            project_views.email.conference_results,
            OsfWebRenderer('public/pages/meeting_plain.mako'),
            endpoint_suffix='__plain',
        ),

        Rule('/news/', 'get', {}, OsfWebRenderer('public/pages/news.mako')),

    ])

    process_rules(app, [
        Rule(
            [
                '/project/<pid>/<addon>/settings/disable/',
                '/project/<pid>/node/<nid>/<addon>/settings/disable/',
            ],
            'post',
            addon_views.disable_addon,
            json_renderer,
        ),

        Rule(
            '/profile/<uid>/<addon>/settings/',
            'get',
            addon_views.get_addon_user_config,
            json_renderer,
        ),
    ], prefix='/api/v1')

    process_rules(app, [
        Rule('/dashboard/get_nodes/', 'get', website_views.get_dashboard_nodes, json_renderer),
        Rule([
                 '/dashboard/get_dashboard/<nid>',
                 '/dashboard/get_dashboard/',
                 ],
             'get', website_views.get_dashboard, json_renderer),
        Rule('/dashboard/get_all_projects/', 'get', website_views.get_all_projects_smart_folder, json_renderer),
        Rule('/dashboard/get_all_registrations/', 'get', website_views.get_all_registrations_smart_folder, json_renderer),
    ], prefix='/api/v1')

    ### Meta-data ###

    process_rules(app, [

        Rule(
            [
                '/project/<pid>/comments/',
                '/project/<pid>/node/<nid>/comments/',
            ],
            'get',
            project_views.comment.list_comments,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comments/discussion/',
                '/project/<pid>/node/<nid>/comments/discussion/',
            ],
            'get',
            project_views.comment.comment_discussion,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/',
                '/project/<pid>/node/<nid>/comment/',
            ],
            'post',
            project_views.comment.add_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/',
                '/project/<pid>/node/<nid>/comment/<cid>/',
            ],
            'put',
            project_views.comment.edit_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/',
                '/project/<pid>/node/<nid>/comment/<cid>/',
            ],
            'delete',
            project_views.comment.delete_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/undelete/',
                '/project/<pid>/node/<nid>/comment/<cid>/undelete/',
            ],
            'put',
            project_views.comment.undelete_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/report/',
                '/project/<pid>/node/<nid>/comment/<cid>/report/',
            ],
            'post',
            project_views.comment.report_abuse,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/unreport/',
                '/project/<pid>/node/<nid>/comment/<cid>/unreport/',
            ],
            'post',
            project_views.comment.unreport_abuse,
            json_renderer,
        ),

    ], prefix='/api/v1')

    ### Forms ###

    process_rules(app, [
        Rule('/forms/registration/', 'get', website_views.registration_form, json_renderer),
        Rule('/forms/signin/', 'get', website_views.signin_form, json_renderer),
        Rule('/forms/forgot_password/', 'get', website_views.forgot_password_form, json_renderer),
        Rule('/forms/reset_password/', 'get', website_views.reset_password_form, json_renderer),
        Rule('/forms/new_project/', 'get', website_views.new_project_form, json_renderer),
        Rule('/forms/new_folder/', 'get', website_views.new_folder_form, json_renderer),
    ], prefix='/api/v1')

    ### Discovery ###

    process_rules(app, [

        Rule('/explore/activity/', 'get', discovery_views.activity, OsfWebRenderer('public/pages/active_nodes.mako')),

    ])

    ### Auth ###

    # Web

    process_rules(app, [

        Rule(
            '/confirm/<uid>/<token>/',
            'get',
            auth_views.confirm_email_get,
            # View will either redirect or display error message
            OsfWebRenderer('error.mako', render_mako_string)
        ),

        Rule(
            '/resend/',
            ['get', 'post'],
            auth_views.resend_confirmation,
            OsfWebRenderer('resend.mako', render_mako_string)
        ),

        Rule(
            '/resetpassword/<verification_key>/',
            ['get', 'post'],
            auth_views.reset_password,
            OsfWebRenderer('public/resetpassword.mako', render_mako_string)
        ),

        # TODO: Remove `auth_register_post`
        Rule('/register/', 'post', auth_views.auth_register_post, OsfWebRenderer('public/login.mako')),
        Rule('/api/v1/register/', 'post', auth_views.register_user, json_renderer),

        Rule(['/login/', '/account/'], 'get', auth_views.auth_login, OsfWebRenderer('public/login.mako')),
        Rule('/login/', 'post', auth_views.auth_login, OsfWebRenderer('public/login.mako'), endpoint_suffix='__post'),
        Rule('/login/first/', 'get', auth_views.auth_login, OsfWebRenderer('public/login.mako'), endpoint_suffix='__first', view_kwargs={'first': True}),

        Rule('/logout/', 'get', auth_views.auth_logout, notemplate),

        Rule('/forgotpassword/', 'post', auth_views.forgot_password, OsfWebRenderer('public/login.mako')),

        Rule([
            '/midas/', '/summit/', '/accountbeta/', '/decline/'
        ], 'get', auth_views.auth_registerbeta, OsfWebRenderer('', render_mako_string)),

    ])

    ### Profile ###

    # Web

    process_rules(app, [
        Rule('/profile/', 'get', profile_views.profile_view, OsfWebRenderer('profile.mako')),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, OsfWebRenderer('profile.mako')),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, OsfWebRenderer('profile/key_history.mako')),
        Rule('/addons/', 'get', profile_views.profile_addons, OsfWebRenderer('profile/addons.mako')),
        Rule(["/user/merge/"], 'get', auth_views.merge_user_get, OsfWebRenderer("merge_accounts.mako")),
        Rule(["/user/merge/"], 'post', auth_views.merge_user_post, OsfWebRenderer("merge_accounts.mako")),
        # Route for claiming and setting email and password. Verification token must be querystring argument
        Rule(['/user/<uid>/<pid>/claim/'], ['get', 'post'],
            project_views.contributor.claim_user_form, OsfWebRenderer('claim_account.mako')),
        Rule(['/user/<uid>/<pid>/claim/verify/<token>/'], ['get', 'post'],
            project_views.contributor.claim_user_registered, OsfWebRenderer('claim_account_registered.mako')),


        Rule(
            '/settings/',
            'get',
            profile_views.user_profile,
            OsfWebRenderer('profile/settings.mako'),
        ),

        Rule(
            '/settings/addons/',
            'get',
            profile_views.user_addons,
            OsfWebRenderer('profile/addons.mako'),
        ),

    ])

    # API

    process_rules(app, [

        Rule('/profile/', 'get', profile_views.profile_view, json_renderer),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, json_renderer),

        # Used by profile.html
        Rule('/profile/<uid>/edit/', 'post', profile_views.edit_profile, json_renderer),
        Rule('/profile/<uid>/public_projects/', 'get', profile_views.get_public_projects, json_renderer),
        Rule('/profile/<uid>/public_components/', 'get', profile_views.get_public_components, json_renderer),

        Rule('/settings/keys/', 'get', profile_views.get_keys, json_renderer),
        Rule('/settings/create_key/', 'post', profile_views.create_user_key, json_renderer),
        Rule('/settings/revoke_key/', 'post', profile_views.revoke_user_key, json_renderer),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, json_renderer),

        Rule('/profile/<user_id>/summary/', 'get', profile_views.get_profile_summary, json_renderer),
        Rule('/user/<uid>/<pid>/claim/email/', 'post', project_views.contributor.claim_user_post, json_renderer),

        # Rules for user profile configuration
        Rule('/settings/names/', 'get', profile_views.serialize_names, json_renderer),
        Rule('/settings/names/', 'put', profile_views.unserialize_names, json_renderer),
        Rule('/settings/names/impute/', 'get', profile_views.impute_names, json_renderer),

        Rule(
            [
                '/settings/social/',
                '/settings/social/<uid>/',
            ],
            'get',
            profile_views.serialize_social,
            json_renderer,
        ),

        Rule(
            [
                '/settings/jobs/',
                '/settings/jobs/<uid>/',
            ],
            'get',
            profile_views.serialize_jobs,
            json_renderer,
        ),

        Rule(
            [
                '/settings/schools/',
                '/settings/schools/<uid>/',
            ],
            'get',
            profile_views.serialize_schools,
            json_renderer,
        ),

        Rule(
            [
                '/settings/social/',
                '/settings/social/<uid>/',
            ],
            'put',
            profile_views.unserialize_social,
            json_renderer
        ),

        Rule(
            [
                '/settings/jobs/',
                '/settings/jobs/<uid>/',
            ],
            'put',
            profile_views.unserialize_jobs,
            json_renderer
        ),

        Rule(
            [
                '/settings/schools/',
                '/settings/schools/<uid>/',
            ],
            'put',
            profile_views.unserialize_schools,
            json_renderer
        ),

    ], prefix='/api/v1',)

    ### Search ###

    # Web

    process_rules(app, [

        Rule('/search/', 'get', search_views.search_search, OsfWebRenderer('search.mako')),

        Rule('/api/v1/user/search/', 'get', search_views.search_contributor, json_renderer),

        Rule(
            '/api/v1/search/node/',
            'post',
            project_views.node.search_node,
            json_renderer,
        ),

    ])

    # API

    process_rules(app, [

        Rule('/search/', 'get', search_views.search_search, json_renderer),
        Rule('/search/projects/', 'get', search_views.search_projects_by_title, json_renderer),

    ], prefix='/api/v1')

    # Project

    # Web

    process_rules(app, [

        Rule('/', 'get', website_views.index, OsfWebRenderer('index.mako')),
        Rule('/goodbye/', 'get', goodbye, OsfWebRenderer('index.mako')),

        Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', project_views.node.view_project, OsfWebRenderer('project/project.mako')),

        # Create
        Rule('/project/<pid>/newnode/', 'post', project_views.node.project_new_node, OsfWebRenderer('', render_mako_string)),

        Rule([
            '/project/<pid>/key_history/<kid>/',
            '/project/<pid>/node/<nid>/key_history/<kid>/',
        ], 'get', project_views.key.node_key_history, OsfWebRenderer('project/key_history.mako')),

        # TODO: Add API endpoint for tags
        Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, OsfWebRenderer('tags.mako')),

        Rule('/project/new/', 'get', project_views.node.project_new, OsfWebRenderer('project/new.mako')),
        Rule('/project/new/', 'post', project_views.node.project_new_post, OsfWebRenderer('project/new.mako')),
        Rule('/folder/new/<nid>', 'get', project_views.node.folder_new, OsfWebRenderer('project/new_folder.mako')),
        Rule('/folder/new/<nid>', 'post', project_views.node.folder_new_post, OsfWebRenderer('project/new_folder.mako')),
        Rule('/api/v1/folder/new/', 'post', project_views.node.add_folder, json_renderer),
        Rule(
            [
                '/project/<pid>/contributors/',
                '/project/<pid>/node/<nid>/contributors/',
            ],
            'get',
            project_views.node.node_contributors,
            OsfWebRenderer('project/contributors.mako'),
        ),

        Rule(
            [
                '/project/<pid>/settings/',
                '/project/<pid>/node/<nid>/settings/',
            ],
            'get',
            project_views.node.node_setting,
            OsfWebRenderer('project/settings.mako')
        ),

        # Permissions
        Rule(
            [
                '/project/<pid>/permissions/<permissions>/',
                '/project/<pid>/node/<nid>/permissions/<permissions>/',
            ],
            'post',
            project_views.node.project_set_privacy,
            OsfWebRenderer('project/project.mako')
        ),

        ### Logs ###

        Rule('/log/<log_id>/', 'get', project_views.log.get_log, OsfWebRenderer('util/render_log.mako')),

        Rule([
            '/project/<pid>/log/',
            '/project/<pid>/node/<nid>/log/',
        ], 'get', project_views.log.get_logs, OsfWebRenderer('util/render_logs.mako')),

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, OsfWebRenderer('project/forks.mako')),

        # Registrations
        Rule([
            '/project/<pid>/register/',
            '/project/<pid>/node/<nid>/register/',
        ], 'get', project_views.register.node_register_page, OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'get', project_views.register.node_register_template_page, OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/registrations/',
            '/project/<pid>/node/<nid>/registrations/',
        ], 'get', project_views.node.node_registrations, OsfWebRenderer('project/registrations.mako')),

        # Statistics
        Rule([
            '/project/<pid>/statistics/',
            '/project/<pid>/node/<nid>/statistics/',
        ], 'get', project_views.node.project_statistics, OsfWebRenderer('project/statistics.mako')),

        ### Files ###

        # Note: Web endpoint for files view must pass `mode` = `page` to
        # include project view data and JS includes
        Rule(
            [
                '/project/<pid>/files/',
                '/project/<pid>/node/<nid>/files/',
            ],
            'get',
            project_views.file.collect_file_trees,
            OsfWebRenderer('project/files.mako'),
            endpoint_suffix='__page', view_kwargs={'mode': 'page'},
        ),


    ])

    # API

    process_rules(app, [

        Rule(
            '/email/meeting/',
            'post',
            project_views.email.meeting_hook,
            json_renderer,
        ),

        Rule([
            '/project/<pid>/contributors_abbrev/',
            '/project/<pid>/node/<nid>/contributors_abbrev/',
        ], 'get', project_views.contributor.get_node_contributors_abbrev, json_renderer),

        Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, json_renderer),

        Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', project_views.node.view_project, json_renderer),

        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>/pointer/',
            ],
            'get',
            project_views.node.get_pointed,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>/pointer/',
            ],
            'post',
            project_views.node.add_pointers,
            json_renderer,
        ),
        Rule(
            [
                '/pointer/',
            ],
            'post',
            project_views.node.add_pointer,
            json_renderer,
        ),
        Rule(
            [
                '/pointer/move/',
            ],
            'post',
            project_views.node.move_pointer,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>pointer/',
            ],
            'delete',
            project_views.node.remove_pointer,
            json_renderer,
        ),
        Rule(
            [
                '/folder/<pid>/pointer/<pointer_id>',
            ],
            'delete',
            project_views.node.remove_pointer_from_folder,
            json_renderer,
        ),

        Rule(
            [
                '/folder/<pid>',
            ],
            'delete',
            project_views.node.delete_folder,
            json_renderer,
        ),

        Rule([
            '/project/<pid>/get_summary/',
            '/project/<pid>/node/<nid>/get_summary/',
        ], 'get', project_views.node.get_summary, json_renderer),

        Rule([
            '/project/<pid>/get_children/',
            '/project/<pid>/node/<nid>/get_children/',
        ], 'get', project_views.node.get_children, json_renderer),
        Rule([
            '/project/<pid>/get_forks/',
            '/project/<pid>/node/<nid>/get_forks/',
        ], 'get', project_views.node.get_forks, json_renderer),
        Rule([
            '/project/<pid>/get_registrations/',
            '/project/<pid>/node/<nid>/get_registrations/',
        ], 'get', project_views.node.get_registrations, json_renderer),

        Rule('/log/<log_id>/', 'get', project_views.log.get_log, json_renderer),

        Rule([
            '/project/<pid>/log/',
            '/project/<pid>/node/<nid>/log/',
        ], 'get', project_views.log.get_logs, json_renderer),

        Rule([
            '/project/<pid>/get_contributors/',
            '/project/<pid>/node/<nid>/get_contributors/',
        ], 'get', project_views.contributor.get_contributors, json_renderer),

        Rule([
            '/project/<pid>/get_contributors_from_parent/',
            '/project/<pid>/node/<nid>/get_contributors_from_parent/',
        ], 'get', project_views.contributor.get_contributors_from_parent, json_renderer),

        # Reorder contributors
        Rule(
            [
                '/project/<pid>/contributors/manage/',
                '/project/<pid>/node/<nid>/contributors/manage/',
            ],
            'POST',
            project_views.contributor.project_manage_contributors,
            json_renderer,
        ),

        Rule([
            '/project/<pid>/get_recently_added_contributors/',
            '/project/<pid>/node/<nid>/get_recently_added_contributors/',
        ], 'get', project_views.contributor.get_recently_added_contributors, json_renderer),

        Rule([
            '/project/<pid>/get_editable_children/',
            '/project/<pid>/node/<nid>/get_editable_children/',
        ], 'get', project_views.node.get_editable_children, json_renderer),

        # Create
        Rule(
            [
                '/project/new/',
                '/project/<pid>/newnode/',
            ],
            'post',
            project_views.node.project_new_node,
            json_renderer,
        ),

        # Private Link
        Rule([
            '/project/<pid>/private_link/',
            '/project/<pid>/node/<nid>/private_link/',
        ], 'post', project_views.node.project_generate_private_link_post, json_renderer),

        Rule([
            '/project/<pid>/private_link/',
            '/project/<pid>/node/<nid>/private_link/',
        ], 'delete', project_views.node.remove_private_link, json_renderer),

        Rule([
            '/project/<pid>/private_link/config/',
            '/project/<pid>/node/<nid>/private_link/config/',
        ], 'get', project_views.node.private_link_config, json_renderer),

        Rule([
            '/project/<pid>/private_link/table/',
            '/project/<pid>/node/<nid>/private_link/table/',
        ], 'get', project_views.node.private_link_table, json_renderer),

        # Create, using existing project as a template
        Rule([
            '/project/new/<nid>/',
        ], 'post', project_views.node.project_new_from_template, json_renderer),

        # Remove
        Rule(
            [
                '/project/<pid>/',
                '/project/<pid>/node/<nid>/',
            ],
            'delete',
            project_views.node.component_remove,
            json_renderer,
        ),

        # API keys
        Rule([
            '/project/<pid>/create_key/',
            '/project/<pid>/node/<nid>/create_key/',
        ], 'post', project_views.key.create_node_key, json_renderer),
        Rule([
            '/project/<pid>/revoke_key/',
            '/project/<pid>/node/<nid>/revoke_key/'
        ], 'post', project_views.key.revoke_node_key,  json_renderer),
        Rule([
            '/project/<pid>/keys/',
            '/project/<pid>/node/<nid>/keys/',
        ], 'get', project_views.key.get_node_keys, json_renderer),

        # Reorder components
        Rule('/project/<pid>/reorder_components/', 'post', project_views.node.project_reorder_components, json_renderer),

        # Edit node
        Rule([
            '/project/<pid>/edit/',
            '/project/<pid>/node/<nid>/edit/',
        ], 'post', project_views.node.edit_node, json_renderer),

        # Tags
        Rule([
            '/project/<pid>/addtag/<tag>/',
            '/project/<pid>/node/<nid>/addtag/<tag>/',
        ], 'post', project_views.tag.project_addtag, json_renderer),
        Rule([
            '/project/<pid>/removetag/<tag>/',
            '/project/<pid>/node/<nid>/removetag/<tag>/',
        ], 'post', project_views.tag.project_removetag, json_renderer),

        # Add / remove contributors
        Rule([
            '/project/<pid>/contributors/',
            '/project/<pid>/node/<nid>/contributors/',
        ], 'post', project_views.contributor.project_contributors_post, json_renderer),
        Rule([
            '/project/<pid>/beforeremovecontributors/',
            '/project/<pid>/node/<nid>/beforeremovecontributors/',
        ], 'post', project_views.contributor.project_before_remove_contributor, json_renderer),
        # TODO(sloria): should be a delete request to /contributors/
        Rule([
            '/project/<pid>/removecontributors/',
            '/project/<pid>/node/<nid>/removecontributors/',
        ], 'post', project_views.contributor.project_removecontributor, json_renderer),

        # Forks
        Rule(
            [
                '/project/<pid>/fork/before/',
                '/project/<pid>/node/<nid>/fork/before/',
            ], 'get', project_views.node.project_before_fork, json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/fork/',
                '/project/<pid>/node/<nid>/fork/',
            ], 'post', project_views.node.node_fork_page, json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/fork/',
                '/project/<pid>/node/<nid>/pointer/fork/',
            ], 'post', project_views.node.fork_pointer, json_renderer,
        ),

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, json_renderer),

        # Registrations
        Rule([
            '/project/<pid>/beforeregister/',
            '/project/<pid>/node/<nid>/beforeregister',
        ], 'get', project_views.register.project_before_register, json_renderer),
        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'get', project_views.register.node_register_template_page, json_renderer),

        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'post', project_views.register.node_register_template_page_post, json_renderer),

        # Statistics
        Rule([
            '/project/<pid>/statistics/',
            '/project/<pid>/node/<nid>/statistics/',
        ], 'get', project_views.node.project_statistics, json_renderer),

        # Permissions
        Rule([
            '/project/<pid>/permissions/<permissions>/',
            '/project/<pid>/node/<nid>/permissions/<permissions>/',
        ], 'post', project_views.node.project_set_privacy, json_renderer),


        ### Wiki ###

        ### Watching ###
        Rule([
            '/project/<pid>/watch/',
            '/project/<pid>/node/<nid>/watch/'
        ], 'post', project_views.node.watch_post, json_renderer),

        Rule([
            '/project/<pid>/unwatch/',
            '/project/<pid>/node/<nid>/unwatch/'
        ], 'post', project_views.node.unwatch_post, json_renderer),

        Rule([
            '/project/<pid>/togglewatch/',
            '/project/<pid>/node/<nid>/togglewatch/'
        ], 'post', project_views.node.togglewatch_post, json_renderer),

        Rule([
            '/watched/logs/'
        ], 'get', website_views.watched_logs_get, json_renderer),
        ### Accounts ###
        Rule([
            '/user/merge/'
        ], 'post', auth_views.merge_user_post, json_renderer),

        # Combined files
        Rule(
            [
                '/project/<pid>/files/',
                '/project/<pid>/node/<nid>/files/'
            ],
            'get',
            project_views.file.collect_file_trees,
            json_renderer,
        ),

        # Endpoint to fetch Rubeus.JS/Hgrid-formatted data
        Rule(
            ['/project/<pid>/files/grid/',
            '/project/<pid>/node/<nid>/files/grid/'
            ],
            'get',
            project_views.file.grid_data,
            json_renderer
        ),

        # Settings

        Rule(
            '/settings/addons/',
            'post',
            profile_views.user_choose_addons,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/settings/addons/',
                '/project/<pid>/node/<nid>/settings/addons/',
            ],
            'post',
            project_views.node.node_choose_addons,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/settings/comments/',
                '/project/<pid>/node/<nid>/settings/comments/',
            ],
            'post',
            project_views.node.configure_comments,
            json_renderer,
        ),

        # Invite Users
        Rule(
            [
                '/project/<pid>/invite_contributor/',
                '/project/<pid>/node/<nid>/invite_contributor/'
            ],
            'post',
            project_views.contributor.invite_contributor_post,
            json_renderer
        ),
    ], prefix='/api/v1')
