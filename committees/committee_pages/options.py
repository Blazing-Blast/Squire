from django.urls import path, include


from committees.models import AssociationGroup
from committees.committee_pages.views import *
from committees.options import SettingsOptionBase, settings_options, SimpleFormSettingsOption
from committees.forms import AssociationGroupUpdateForm


class HomeScreenTextOptions(SimpleFormSettingsOption):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.BOARD, AssociationGroup.ORDER]
    name = 'Home screen'
    option_form_class = AssociationGroupUpdateForm
    url_keyword = "group_update"


class MemberOptions(SettingsOptionBase):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.ORDER]
    name = 'Members'
    option_template_name = "committees/committee_pages/setting_blocks/members.html"
    url_keyword = "members"
    url_name = "group_members"

    def build_url_pattern(self, config):
        return [
            path('', AssociationGroupMembersView.as_view(config=config, settings_option=self), name='group_members'),
            path('edit/', AssociationGroupMemberUpdateView.as_view(config=config, settings_option=self), name='group_members_edit'),
        ]


class QuicklinkOptions(SettingsOptionBase):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.ORDER]
    name = 'External sources'
    option_template_name = "committees/committee_pages/setting_blocks/quicklinks.html"
    url_keyword = "hyperlinks"
    url_name = "group_quicklinks"

    def build_url_pattern(self, config):
        return [
            path('', AssociationGroupQuickLinksView.as_view(config=config, settings_option=self), name='group_quicklinks'),
            path('edit/', AssociationGroupQuickLinksAddOrUpdateView.as_view(config=config, settings_option=self), name='group_quicklinks_edit'),
            path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(config=config, settings_option=self), name='group_quicklink_delete'),
        ]


settings_options.add_setting_option(HomeScreenTextOptions)
settings_options.add_setting_option(MemberOptions)
settings_options.add_setting_option(QuicklinkOptions)
