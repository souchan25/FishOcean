from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SellerProfile

class BuyerRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_buyer = True
        if commit:
            user.save()
        return user

class SellerRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True)
    shop_name = forms.CharField(max_length=100, required=True)
    municipality = forms.ChoiceField(choices=SellerProfile.LOCATION_CHOICES)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    # QR Codes
    gcash_qr_image = forms.ImageField(required=False)
    maya_qr_image = forms.ImageField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_seller = True
        if commit:
            user.save()
            SellerProfile.objects.create(
                user=user,
                shop_name=self.cleaned_data['shop_name'],
                municipality=self.cleaned_data['municipality'],
                address=self.cleaned_data['address'],
                gcash_qr_image=self.cleaned_data['gcash_qr_image'],
                maya_qr_image=self.cleaned_data['maya_qr_image']
            )
        return user
