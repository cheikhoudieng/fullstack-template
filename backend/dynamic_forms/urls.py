from django.urls import path
from dynamic_forms import form_views

urlpatterns = [
    # path('form/<str:form_key>/', views.DynamicFormView.as_view(), name='dynamic_form_metadata'),
    # path('form/<str:form_key>/submit/', views.DynamicFormView.as_view(), name='dynamic_form_submit'),

    # URLs spécifiques si on préfère (plus lisible, permet différentes permissions/logiques par URL)
    # path('contact/', views.ContactFormView.as_view(), name='contact_form'),
    # path('users/create/', form_views.UserCreateView.as_view(), name='user_create_form'),

    # Exemple URL pour mise à jour (nécessite PK)
    # Assure-toi que le nom du kwarg correspond à `instance_lookup_field` dans la vue
    # path('profile/<int:user_pk>/edit/', views.UserProfileUpdateView.as_view(), name='user_profile_update'),
]