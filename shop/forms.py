from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Order


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100,
        required=True
    )

    last_name = forms.CharField(
        max_length=100,
        required=True
    )

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


class CheckoutForm(forms.ModelForm):

    class Meta:
        model = Order

        fields = [
            'full_name',
            'email',
            'phone_number',
            'state',
            'city',
            'address',
            'additional_information',
        ]

        widgets = {
            'full_name': forms.TextInput(
                attrs={'placeholder': 'Full name'}
            ),

            'email': forms.EmailInput(
                attrs={'placeholder': 'Email address'}
            ),

            'phone_number': forms.TextInput(
                attrs={'placeholder': 'Phone number'}
            ),

            'state': forms.TextInput(
                attrs={'placeholder': 'State'}
            ),

            'city': forms.TextInput(
                attrs={'placeholder': 'City / Town'}
            ),

            'address': forms.Textarea(
                attrs={
                    'placeholder': 'Complete delivery address',
                    'rows': 4
                }
            ),

            'additional_information': forms.Textarea(
                attrs={
                    'placeholder': 'Landmark or extra delivery instructions',
                    'rows': 3
                }
            ),
        }