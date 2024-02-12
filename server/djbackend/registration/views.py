from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .forms import UserRegistrationForm
from .tasks import aprove_user


User = get_user_model()


def registration_view(request):

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()            
            aprove_user(user)
            return redirect('registration-confirm-view')
    else:
        form = UserRegistrationForm()
    users = User.objects.all()
    context = {
            'form':form,
            'users':users,
        }
    return render(request, 'registration/registration.html', context)


def registration_confirm_view(request):
    return render(
        request,
        'registration/registration_confirm.html',
    )