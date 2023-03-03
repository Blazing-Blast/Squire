from django.test import TestCase

from committees.models import AssociationGroup

from activity_calendar.constants import *
from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.managers import MeetingManager


class TestActivityTags(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots', 'activity_calendar/test_meetings']

    def setUp(self):
        self.manager = MeetingManager()
        self.manager.model = ActivityMoment

    def test_get_queryset(self):
        meeting = self.manager.first()
        self.assertIsInstance(meeting, ActivityMoment)
        self.assertEqual(meeting.parent_activity.type, ACTIVITY_MEETING)

    def test_filter_group(self):
        association_group = AssociationGroup.objects.get(id=40)
        meetings = self.manager.filter_group(association_group)
        self.assertIn(42, meetings.values_list('id', flat=True))
        self.assertNotIn(46, meetings.values_list('id', flat=True))

