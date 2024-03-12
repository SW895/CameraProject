from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class TestRegistrationView(TestCase):
    @classmethod
    def tearDown(cls):
        users = User.objects.all()
        for user in users:
            user.delete()

    def test_view_accessible_by_name(self):
        response = self.client.get(reverse('registration'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/registration/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('registration'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/registration.html')

    def test_success_registration(self):
        response = self.client.post(reverse('registration'), {'username':'test_user_1', 
                                                              'email':'test_email@mail.ru',
                                                              'password1':'1X<ISRUkw+tuK',
                                                              'password2':'1X<ISRUkw+tuK',
                                                              } )
        self.assertRedirects(response, reverse('registration-confirm'))

    def test_username_alredy_registered(self):
        user = User.objects.create_user(username='test_user_1',
                                        password='1X<ISRUkw+tuK',
                                        email='test_email2@mail.ru')
        response = response = self.client.post(reverse('registration'), {'username':'test_user_1', 
                                                              'email':'test_email@mail.ru',
                                                              'password1':'1X<ISRUkw+tuK',
                                                              'password2':'1X<ISRUkw+tuK',
                                                              })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'A user with that username already exists.')

    def test_user_email_already_registered(self):
        user = User.objects.create_user(username='test_user_2',
                                        password='1X<ISRUkw+tuK',
                                        email='test_email@mail.ru')
        response = response = self.client.post(reverse('registration'), {'username':'test_user_1', 
                                                              'email':'test_email@mail.ru',
                                                              'password1':'1X<ISRUkw+tuK',
                                                              'password2':'1X<ISRUkw+tuK',
                                                              })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'User with this Email Adress already exists.')
    
    def test_password_are_not_equal(self):
        response = response = self.client.post(reverse('registration'), {'username':'test_user', 
                                                              'email':'test_email@mail.ru',
                                                              'password1':'1X<ISRUkw+tuK',
                                                              'password2':'1X<ISRUkw+tuK11',
                                                              })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'password2', 'The two password fields didn’t match.')


class TestRegistrationConfirm(TestCase):

    def test_view_accessible_by_name(self):
        response = self.client.get(reverse('registration-confirm'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/registration_confirm/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('registration-confirm'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/registration_confirm.html')