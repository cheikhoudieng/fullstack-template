
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _ # Pour l'internationalisation (bonnes pratiques)

# --- Modèle de base pour les Timestamps ---
class TimestampedModel(models.Model):
    """Modèle abstrait ajoutant les champs de date de création et de mise à jour."""
    added_date = models.DateTimeField(
        _("Date d'ajout"),
        auto_now_add=True,
        help_text=_("Date et heure de création de l'enregistrement.")
    )
    last_update = models.DateTimeField(
        _("Dernière mise à jour"),
        auto_now=True,
        help_text=_("Date et heure de la dernière modification de l'enregistrement.")
    )

    class Meta:
        abstract = True
        ordering = ['-last_update', '-added_date'] # Ordre par défaut utile

# --- Modèle principal pour les surcharges SEO ---
class SEOOverride(TimestampedModel):
    """
    Permet de surcharger les métadonnées SEO générées automatiquement
    pour un objet spécifique (via GenericForeignKey) ou une URL spécifique (path).
    """

    # --- Mécanisme de Ciblage ---
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True, blank=True, # Permet de cibler par path uniquement
        verbose_name=_("Type de Contenu"),
        help_text=_("Le type de modèle à cibler (ex: Produit, Catégorie). Laisser vide si ciblage par URL (path).")
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True,
        db_index=True, # Index utile pour les recherches
        verbose_name=_("ID de l'Objet"),
        help_text=_("L'identifiant unique de l'objet à cibler. Laisser vide si ciblage par URL (path).")
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    path = models.CharField(
        _("Chemin d'URL spécifique"),
        max_length=500,
        unique=True, # Un seul override par path exact
        db_index=True,
        blank=True, null=True, # Permet de cibler par objet uniquement
        help_text=_("Cible une URL exacte (ex: '/connexion/', '/page/a-propos/'). Sensible à la casse et au slash final. Laisser vide si ciblage par objet.")
    )

    is_active = models.BooleanField(
        _("Actif"),
        default=True,
        db_index=True,
        help_text=_("Décocher pour désactiver cette surcharge sans la supprimer.")
    )

    # --- Champs SEO à surcharger ---
    # Laissez vide un champ pour utiliser la valeur générée automatiquement.
    title = models.CharField(
        _("Titre SEO (Title Tag)"),
        max_length=255, blank=True, null=True,
        help_text=_("Idéalement ~60 caractères.")
    )
    meta_description = models.TextField(
        _("Meta Description"),
        blank=True, null=True,
        help_text=_("Idéalement ~160 caractères.")
    )
    # meta_keywords = models.CharField( # Généralement peu utile aujourd'hui
    #     _("Meta Keywords"),
    #     max_length=255, blank=True, null=True,
    #     help_text=_("Surcharge <meta name='keywords'>. Utilité SEO très limitée.")
    # )
    canonical_url = models.URLField(
        _("URL Canonique"),
        max_length=2000, # Les URLs peuvent être longues
        blank=True, null=True,
        help_text=_("Utile pour le contenu dupliqué.")
    )
    robots_meta = models.CharField(
        _("Meta Robots"),
        max_length=150, blank=True, null=True,
        help_text=_("(ex: 'noindex, nofollow', 'max-snippet:-1').")
    )

    # --- Open Graph (Facebook, LinkedIn, etc.) ---
    og_title = models.CharField(
        _("Titre Open Graph (og:title)"),
        max_length=255, blank=True, null=True,
        help_text=_("Titre affiché lors du partage sur les réseaux sociaux (si vide, utilise le Titre SEO).")
    )
    og_description = models.TextField(
        _("Description Open Graph (og:description)"),
        blank=True, null=True,
        help_text=_("Description affichée lors du partage (si vide, utilise la Meta Description).")
    )
    og_image = models.URLField(
        _("Image Open Graph (og:image)"),
        max_length=2000, blank=True, null=True,
        help_text=_("URL absolue de l'image pour le partage. Dimensions recommandées : 1200x630px.")
    )
    og_type = models.CharField(
        _("Type Open Graph (og:type)"),
        max_length=50, blank=True, null=True,
        help_text=_("Type de contenu (ex: 'website', 'article', 'product').")
    )

    # --- Twitter Cards ---
    twitter_card = models.CharField(
        _("Type de Carte Twitter (twitter:card)"),
        max_length=50, blank=True, null=True,
        help_text=_("Type de carte ('summary', 'summary_large_image', 'app', 'player').")
    )
    twitter_title = models.CharField(
        _("Titre Carte Twitter (twitter:title)"),
        max_length=255, blank=True, null=True,
        help_text=_("Titre pour la carte Twitter (si vide, utilise og:title ou Titre SEO).")
    )
    twitter_description = models.TextField(
        _("Description Carte Twitter (twitter:description)"),
        blank=True, null=True,
        help_text=_("Description pour la carte Twitter (si vide, utilise og:description ou Meta Description). ~200 caractères max.")
    )
    twitter_image = models.URLField(
        _("Image Carte Twitter (twitter:image)"),
        max_length=2000, blank=True, null=True,
        help_text=_("URL absolue de l'image pour Twitter (si vide, utilise og:image). Doit respecter les ratios selon le type de carte.")
    )

    # --- Optionnel : Données Structurées (JSON-LD) ---
    # Si vous voulez permettre une surcharge complète du JSON-LD (cas avancé)
    custom_json_ld = models.JSONField(
        _("JSON-LD Personnalisé"),
        blank=True, null=True,
        help_text=_("(Avancé) Surcharge complètement le(s) script(s) JSON-LD généré(s). Entrez un objet JSON valide ou une liste d'objets JSON.")
    )

    # --- Optionnel : Meta Tags Additionnels ---
    # Si besoin d'ajouter des tags non standards
    # extra_meta_tags = models.JSONField(
    #     _("Meta Tags Additionnels"),
    #     blank=True, null=True,
    #     help_text=_("Ajouter des balises meta spécifiques. Format: [{'type': 'name'/'property', 'name_or_property': '...', 'content': '...'}]")
    # )


    class Meta:
        verbose_name = _("Surcharge SEO")
        verbose_name_plural = _("Surcharges SEO")
        ordering = ['-is_active', '-last_update'] # Actifs et récents en premier

        # Contraintes pour assurer l'intégrité du ciblage
        constraints = [
            # Un override doit cibler SOIT un objet SOIT un path, mais pas les deux.
            models.CheckConstraint(
                check=(models.Q(content_type__isnull=False, object_id__isnull=False, path__isnull=True) |
                       models.Q(content_type__isnull=True, object_id__isnull=True, path__isnull=False)),
                name='seo_target_exclusive',
                violation_error_message=_("Une surcharge SEO doit cibler soit un objet (Type/ID) soit un chemin d'URL (Path), mais pas les deux.")
            ),
        ]
        # Assure qu'on ne peut pas créer deux surcharges pour le même objet
        unique_together = [('content_type', 'object_id')]

    def clean(self):
        """Validation personnalisée avant sauvegarde."""
        super().clean()
        # Vérifie la contrainte 'seo_target_exclusive' manuellement car CheckConstraint
        # n'empêche pas toujours la création via l'admin si les champs sont juste laissés vides.
        has_object_target = self.content_type is not None and self.object_id is not None
        has_path_target = self.path is not None and self.path.strip() != ""

        if not has_object_target and not has_path_target:
            raise ValidationError(_("Vous devez spécifier une cible : soit un Type de Contenu/ID d'Objet, soit un Chemin d'URL (Path)."))

        if has_object_target and has_path_target:
            raise ValidationError(_("Vous ne pouvez pas cibler à la fois un objet (Type/ID) et un Chemin d'URL (Path). Choisissez l'un ou l'autre."))

        # Validation optionnelle du path (doit commencer par / ?)
        if self.path and not self.path.startswith('/'):
             raise ValidationError({'path': _("Le chemin d'URL doit commencer par un '/'.")})


    def __str__(self):
        """Représentation textuelle claire de l'override."""
        target = "Cible inconnue"
        if self.content_object:
            try:
                # Essayer d'obtenir un nom plus parlant de l'objet cible
                obj_str = str(self.content_object)
                if len(obj_str) > 50: obj_str = obj_str[:47] + '...'
                target = f"{self.content_type.name}: {obj_str} (ID: {self.object_id})"
            except Exception: # Gérer les cas où str(content_object) échoue
                 target = f"{self.content_type.name} (ID: {self.object_id})"
        elif self.path:
            target = f"Path: {self.path}"

        status = "Actif" if self.is_active else "Inactif"
        return f"Override SEO [{status}] pour {target}"