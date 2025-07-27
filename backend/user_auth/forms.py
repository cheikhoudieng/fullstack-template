from django import forms

class SetNewPasswordForm(forms.Form):
    password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput,
        min_length=8,
        required=True
    )
    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput,
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
