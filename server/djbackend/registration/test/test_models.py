from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestCustomUser(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        cls.test_user_pk = User.objects.create_user(
            username=cls.test_user,
            password=cls.test_password,
        ).pk

    def test_checked_by_admin_false_by_default(self):
        user = User.objects.get(pk=self.test_user_pk)
        self.assertFalse(user.admin_checked)
