from datetime import datetime, timedelta
from django.test import TestCase

from pano.puppetdb.pdbutils import is_unreported

__author__ = 'etaklar'


class CheckIfUnreported(TestCase):
    def test_none_date(self):
        """
        Should fail because if there is no report timestamp
        the node has not managed to complete a puppet run.
        """
        """
        :return:
        """
        date = None
        results = is_unreported(date)
        self.assertEquals(results, True)

    def test_date_reported_within_two_hours(self):
        """
        Should return False since the node has reported within
        the default value of 2 hours.
        """
        date = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        results = is_unreported(date)
        self.assertEquals(results, False)

    def test_date_unreported_within_two_hours(self):
        """
        Should return True since the node has not reported within
        the default value of 2 hours.
        """
        date = (datetime.utcnow() - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        results = is_unreported(date)
        self.assertEquals(results, True)

    def test_invalid_formatted_date(self):
        """
        Since a date in the incorrect format can not be read
        datetime should raise an error because it does not
        match the format %Y-%m-%dT%H:%M:%S.%fZ
        """
        date = 'not_a_real_date'
        self.assertRaises(ValueError, is_unreported, node_report_timestamp=date)

    def test_unreported_date_with_hours_set_to_24_hours(self):
        """
        Test timestamp set to 25 hours ago, it should
        count as a unreported timestamp since the unreported
        time is set to 24 hours.
        """
        date = (datetime.utcnow() - timedelta(hours=25)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        results = is_unreported(date, unreported=24*60)
        self.assertEquals(results, True)
