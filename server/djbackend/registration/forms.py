from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(label='Username', max_length=50)
    email = forms.EmailField(label='Email',
                             max_length=50,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
