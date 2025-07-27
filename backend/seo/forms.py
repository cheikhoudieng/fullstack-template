from django import forms
from seo.models import SEOOverride
from django.utils.translation import gettext_lazy as _

class SEOOverrideAdminForm(forms.ModelForm):
    """
    Formulaire personnalisé pour l'admin SEOOverride.
    Définit explicitement les champs à inclure.
    """
    class Meta:
        model = SEOOverride
        # Lister EXPLICITEMENT tous les champs modifiables qu'on veut dans le formulaire
        fields = [
            'is_active',
            'content_type',
            'object_id',
            'path',
            'title',
            'meta_description', # <-- Le voilà
            'canonical_url',    # <-- Le voilà
            'robots_meta',      # <-- Le voilà
            'og_title',
            'og_description',
            'og_image',
            'og_type',
            'twitter_card',
            'twitter_title',
            'twitter_description',
            'twitter_image',
            'custom_json_ld',
            # Ne pas inclure 'added_date', 'last_update' car ils seront readonly
        ]
        # Optionnel: Ajouter des widgets pour améliorer l'affichage
        widgets = {
            'meta_description': forms.Textarea(attrs={'rows': 4}),
            'og_description': forms.Textarea(attrs={'rows': 4}),
            'twitter_description': forms.Textarea(attrs={'rows': 4}),
            'custom_json_ld': forms.Textarea(attrs={'rows': 6}),
            'path': forms.TextInput(attrs={'placeholder': "/chemin/exact/url/"}),
            'robots_meta': forms.TextInput(attrs={'placeholder': "ex: noindex, nofollow"}),
        }

    def clean(self):
        """
        Ajouter ici la validation spécifique au formulaire si nécessaire,
        mais la validation clean() du modèle sera aussi appelée.
        """
        cleaned_data = super().clean()

        # Ré-appliquer la validation exclusive car elle est cruciale
        # (même si elle est aussi dans le modèle, une double vérif ne fait pas de mal)
        content_type = cleaned_data.get('content_type')
        object_id = cleaned_data.get('object_id')
        path = cleaned_data.get('path')

        has_object_target = content_type is not None and object_id is not None
        has_path_target = path is not None and path.strip() != ""

        if not has_object_target and not has_path_target:
             raise forms.ValidationError(
                 _("Ciblage requis: Vous devez fournir soit un 'Type de Contenu' et 'ID d'Objet', soit un 'Chemin d'URL spécifique'."),
                 code='target_required'
             )

        if has_object_target and has_path_target:
             raise forms.ValidationError(
                 _("Ciblage Exclusif: Vous ne pouvez pas cibler à la fois un objet (Type/ID) et un Chemin d'URL. Choisissez l'un des deux."),
                 code='target_exclusive'
             )

        # Validation optionnelle du path
        if path and not path.startswith('/'):
              self.add_error('path', _("Le chemin d'URL doit commencer par un '/'.") )

        return cleaned_data