from django.test import TestCase
from ..templatetags.get_url import get_url


class TestGetUrl(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = '/archive/'

    def test_if_no_query_params(self):
        result = get_url(self.url, 'human_det')
        self.assertEqual('/archive/?human_det=True',
                         result)

    def test_if_query_param_already_in_url(self):
        result = get_url(self.url + '?human_det=True', 'human_det')
        self.assertEqual('/archive/?human_det=True',
                         result)

    def test_if_multiple_query_params(self):
        result = get_url(self.url + '?cat_det=True&car_det=True', 'human_det')
        self.assertEqual('/archive/?cat_det=True&car_det=True&human_det=True',
                         result)
