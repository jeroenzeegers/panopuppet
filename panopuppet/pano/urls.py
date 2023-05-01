from django.conf.urls import patterns, url

from panopuppet.pano.views.analytics import analytics
from panopuppet.pano.views.catalogue import catalog
from panopuppet.pano.views.dashboard import dashboard
from panopuppet.pano.views.event_analytics import event_analytics
from panopuppet.pano.views.filebucket import filebucket
from panopuppet.pano.views.logout import logout_view
from panopuppet.pano.views.node_facts import facts
from panopuppet.pano.views.nodes import nodes
from panopuppet.pano.views.radiator import radiator
from panopuppet.pano.views.report_agent_logs import agent_logs
from panopuppet.pano.views.report_events import detailed_events
from panopuppet.pano.views.reports import reports
from panopuppet.pano.views.splash import splash
# API Imports
from panopuppet.pano.views.api.node_data import nodes_json, search_nodes_json
from panopuppet.pano.views.api.fact_data import facts_json
from panopuppet.pano.views.api.dashboard_data import dashboard_status_json, dashboard_nodes_json, dashboard_json
from panopuppet.pano.views.api.report_data import reports_json, reports_search_json
from panopuppet.pano.views.api.catalogue_data import catalogue_json, catalogue_compare_json, catalogue_history_list, \
    catalogue_history_fetch
from panopuppet.pano.views.api.report_agent_log import report_log_json
from panopuppet.pano.views.api.query_filters import filter_json

__author__ = 'etaklar'

urlpatterns = patterns('',
                       url(r'^$', splash, name='index'),
                       url(r'^login/$', splash, name='login'),
                       url(r'^logout/$', logout_view, name='logout'),
                       url(r'^dashboard/$', dashboard, name='dashboard'),
                       url(r'^filebucket/$', filebucket, name='filebucket'),
                       url(r'^nodes/$', nodes, name='nodes'),
                       url(r'^reports/(?P<certname>[\w\.-]+)/$', reports, name='reports'),
                       url(r'^events/(?P<hashid>[\w\.-]+)/$', detailed_events, name='events'),
                       url(r'^events/(?P<certname>[\w\.-]+)/(?P<report_hash>[\w]+)/$', agent_logs, name='agent_logs'),
                       url(r'^analytics/$', analytics, name='analytics'),
                       url(r'^eventanalytics/$', event_analytics, name='event_analytics'),
                       url(r'^eventanalytics/(?P<view>[\w]+)/$', event_analytics, name='event_analytics'),
                       url(r'^facts/(?P<certname>[\w\.-]+)/$', facts, name='facts'),
                       url(r'^radiator/$', radiator, name='radiator'),
                       url(r'^catalog/$', catalog, name='catalog'),
                       # API URLS
                       url(r'^api/nodes/$', nodes_json, name='api_nodes'),
                       url(r'^api/nodes/search/$', search_nodes_json, name='api_search_nodes'),
                       url(r'^api/facts/$', facts_json, name='api_facts'),
                       url(r'^api/filters/$', filter_json, name='api_filter'),
                       url(r'^api/reports/(?P<certname>[\w\.-]+)/$', reports_json, name='api_reports'),
                       url(r'^api/catalogue/get/(?P<certname>[\w\.-]+)/$', catalogue_json,
                           name='api_catalogues'),
                       url(r'^api/catalogue/saved/list/(?P<certname>[\w\.-]+)/$', catalogue_history_list,
                           name='api_saved_catalogues'),
                       url(r'^api/catalogue/saved/fetch/(?P<certname>[\w\.-]+)/(?P<catalogue_hash>[\w]+)$',
                           catalogue_history_fetch,
                           name='api_saved_catalogues'),
                       url(r'^api/catalogue/compare/(?P<certname1>[\w\.-]+)/(?P<certname2>[\w\.-]+)/$',
                           catalogue_compare_json,
                           name='api_compare_catalogues'),
                       url(r'^api/report/search/$', reports_search_json, name='api_search_reports'),
                       url(r'^api/reports/(?P<report_hash>[\w]+)/agent_log$', report_log_json, name='api_report_logs'),
                       # url(r'^api/reports/(?P<report_hash>[a-z0-9]+)/metrics$', report_metrics_json, name='api_report_metrics'),
                       url(r'^api/dashboard/$', dashboard_json, name='api_dashboard'),
                       url(r'^api/dashboard/status$', dashboard_status_json, name='api_dashboard_status'),
                       url(r'^api/status$', dashboard_status_json, name='api_dashboard_status'),
                       url(r'^api/dashboard/nodes/$', dashboard_nodes_json, name='api_dashboard_nodes'),
                       )
