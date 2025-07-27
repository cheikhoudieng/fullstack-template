from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, escape
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from .models import SEOOverride

@admin.register(SEOOverride)
class SEOOverrideAdmin(admin.ModelAdmin):
    # --- Config Liste (Identique) ---
    list_display = (
        'display_target_with_status',
        'truncated_title',
        'last_update',
        'is_active',
    )
    list_filter = (
        'is_active',
        'content_type',
    )
    search_fields = (
        'title',
        'meta_description',
        'path',
        'object_id',
    )
    list_per_page = 25
    list_select_related = ('content_type',)

    # --- Config Formulaire ---
    fieldsets = (
        (None, {
            'fields': (
                'is_active',
                # Utilise la méthode mise à jour ci-dessous
                'display_target_info_readonly',
            )
        }),
         ('Ciblage Manuel (Si Non Pré-rempli)', {
             'classes': ('seo-manual-targeting',), # Masqué via get_fieldsets si pré-rempli
             'fields': (
                ('content_type', 'object_id'),
                'path',
              ),
              'description': _("Utilisez cette section **UNIQUEMENT** si vous ciblez une URL spécifique (path) ou si vous n'avez pas utilisé le lien 'Créer/Voir SEO Override' depuis l'objet cible."),
         }),
        # ... (Reste des fieldsets SEO, OG, Twitter, Avancé, Informations comme avant) ...
         (_('Contenu SEO Principal'), {
            'fields': ('title', 'meta_description', 'canonical_url', 'robots_meta'),
            'classes': ('collapse',) # Gardons collapse par défaut
        }),
        (_('Open Graph (Réseaux Sociaux)'), {
            'fields': ('og_title', 'og_description', 'og_image', 'og_type'),
            'classes': ('collapse',)
        }),
        (_('Twitter Cards'), {
            'fields': ('twitter_card', 'twitter_title', 'twitter_description', 'twitter_image'),
            'classes': ('collapse',)
        }),
         (_('Avancé'), {
            'fields': ('custom_json_ld',),
            'classes': ('collapse', 'wide'),
            'description': _("Attention : Surcharge JSON-LD avancée."),
        }),
        (_('Informations'), {
             'fields': ('added_date', 'last_update'),
             'classes': ('collapse',)
        }),
    )

    readonly_fields = (
        # Renommer pour clarté (même si le nom du champ dans fieldsets pointe vers la méthode)
        'display_target_info_readonly',
        'added_date',
        'last_update',
    )

    # --- Surcharge pour pré-remplir les champs en mode Ajout ---
    # Cette méthode est correcte et nécessaire
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        ct_id = request.GET.get('content_type')
        obj_id = request.GET.get('object_id')
        if ct_id and obj_id:
            try:
                initial['content_type'] = ContentType.objects.get(pk=ct_id)
                initial['object_id'] = int(obj_id)
            except (ContentType.DoesNotExist, ValueError):
                pass
        return initial

    # --- Rendre non modifiable si pré-rempli/modification ---
    # Cette méthode est correcte et utilise directement request.GET
    def get_readonly_fields(self, request, obj=None):
        # Lister d'abord les readonly standards définis dans la classe
        readonly = list(super().get_readonly_fields(request, obj))
        # Récupérer les params GET directement depuis la requête passée en argument
        ct_id_get = request.GET.get('content_type')
        obj_id_get = request.GET.get('object_id')

        # Si l'objet existe (modification) OU si les champs sont pré-remplis via GET
        if obj or (ct_id_get and obj_id_get):
            # Ajouter content_type et object_id à la liste des readonly
            # Si on cible un objet, le path ne doit pas être modifiable
            if 'content_type' not in readonly: readonly.append('content_type')
            if 'object_id' not in readonly: readonly.append('object_id')
            if 'path' not in readonly: readonly.append('path')
        # Si c'est un ajout SANS pré-remplissage d'objet, on ne veut pas éditer l'objet cible
        # mais on peut éditer le path.
        elif not obj and not (ct_id_get and obj_id_get):
             # On rend Ctype et ObjID modifiables (comportement par défaut, pas besoin d'ajouter ici)
             # Mais on s'assure que 'path' N'EST PAS dans readonly dans ce cas précis
             if 'path' in readonly: readonly.remove('path') # Normalement pas le cas
        # Si on est en ajout pré-rempli, on a déjà ajouté 'path' aux readonly
        elif not obj and (ct_id_get and obj_id_get):
             if 'path' not in readonly: readonly.append('path')

        return readonly


    # --- Masquer la section manuelle si pré-rempli ---
    # Cette méthode est correcte et utilise directement request.GET
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        ct_id_get = request.GET.get('content_type')
        obj_id_get = request.GET.get('object_id')

        # Si c'est un ajout ET que les champs sont pré-remplis via GET
        if not obj and (ct_id_get and obj_id_get):
            new_fieldsets = []
            for name, options in fieldsets:
                 # Ne pas inclure le fieldset marqué avec la classe 'seo-manual-targeting'
                if 'seo-manual-targeting' not in options.get('classes', ()):
                    new_fieldsets.append((name, options))
            return tuple(new_fieldsets) # Retourner un tuple
        return fieldsets

 
    @admin.display(description=_("Cible Actuelle"))
    def display_target_info_readonly(self, obj=None):
        """Affiche des informations claires sur la cible."""
        if obj: # Mode Modification (EXISTING object)
            if obj.content_type and obj.object_id:
                target_str = f"{obj.content_type.name} (ID: {obj.object_id})"
                linked_obj_repr = _("(Objet introuvable)") # Fallback
                admin_link = ""
                if obj.content_object:
                    linked_obj_repr = escape(obj.content_object)
                    try:
                        admin_url = reverse(f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change', args=[obj.object_id])
                        admin_link = format_html(' <a href="{}" target="_blank">({})</a>', admin_url, _("Voir Objet"))
                    except NoReverseMatch:
                        pass
                    except Exception:
                         pass # Ignorer les erreurs juste pour le lien optionnel
                return mark_safe(f"{target_str} {linked_obj_repr}{admin_link}")

            elif obj.path:
                return f"Chemin d'URL: {escape(obj.path)}"
            else:
                 # Ne devrait pas arriver si clean() est correct
                 # --- CORRECTION ICI ---
                 error_message = _('ERREUR: Aucune cible valide n\'est définie !')
                 return mark_safe(f"<strong style='color:red;'>{error_message}</strong>")
                 # --- FIN CORRECTION ---

        else: # Mode Ajout (NEW object)
            # Essayons de récupérer les infos depuis self.request (attaché par add_view)
            try:
                 # Vérification si self.request existe avant de l'utiliser
                 if not hasattr(self, 'request'):
                     print("WARN: self.request non disponible dans display_target_info_readonly en mode ajout initial.")
                     # Fallback générique si request n'est pas encore défini
                     return _("Utilisez la section 'Ciblage Manuel' pour définir la cible.")

                 ct_id = self.request.GET.get('content_type')
                 obj_id = self.request.GET.get('object_id')

                 if ct_id and obj_id:
                     # Si pré-rempli, on AFFICHE juste l'info récupérée
                     ct = ContentType.objects.get(pk=ct_id)
                     return mark_safe(f"<strong>{_('Création pour :')}</strong> {ct.name} (ID: {obj_id})<br><small>{_('Le ciblage a été pré-rempli et ne peut pas être modifié.')}</small>")
                 else:
                     # Si pas pré-rempli (URL /add/ normale)
                     return _("Aucune cible pré-remplie. Veuillez utiliser la section 'Ciblage Manuel'.")

            except ContentType.DoesNotExist:
                  # --- CORRECTION ICI (Optionnel mais bon usage) ---
                  # Utiliser %s formatting ou f-string pour éviter les erreurs si ct_id est None ou autre chose
                  error_message_ct = _('ERREUR: Type de contenu pré-rempli invalide (ID = %s)')
                  return mark_safe(f"<strong style='color:red;'>{error_message_ct % escape(ct_id or 'N/A')}</strong>")
                  # --- FIN CORRECTION ---
            except AttributeError as e:
                 # Si self.request n'est pas défini même après la vérification (ne devrait pas arriver avec add_view/change_view surchargés)
                 print(f"WARN: AttributeError in display_target_info_readonly (add mode): {e}")
                 return _("Utilisez la section 'Ciblage Manuel' pour définir la cible.")
            except Exception as e:
                 print(f"ERROR in display_target_info_readonly (add mode): {e}")
                 return _("Erreur lors de l'affichage des informations de ciblage.")


    # --- Méthodes liste et autres (display_target_with_status, truncated_title) ---
    # ... (Gardez les versions précédentes de ces méthodes pour la vue liste) ...
    @admin.display(description=_("Cible et Statut"), ordering='-is_active')
    def display_target_with_status(self, obj):
       # ... (code existant) ...
       status_icon = "✅" if obj.is_active else "❌"
       target_str = "Inconnue"
       if obj.content_type and obj.object_id:
            target_str = f"{obj.content_type.name} (ID: {obj.object_id})"
            # Optionnel: Ajouter tentative d'affichage nom objet (attention perf)
            # try:
            #     if obj.content_object: target_str += f": {str(obj.content_object)[:30]}"
            # except Exception: pass
       elif obj.path:
           target_str = f"Path: {obj.path[:50]}"
           if len(obj.path) > 50: target_str += "..."
       return format_html("{} {}", status_icon, target_str)

    @admin.display(description=_("Titre SEO"), ordering='title')
    def truncated_title(self, obj):
       # ... (code existant) ...
       limit = 60
       title = obj.title or ""
       if len(title) > limit:
           return title[:limit-3] + "..."
       return title or mark_safe("<em>" + _("(Utilise auto)") + "</em>")

    # Assurer que self.request est disponible
    def changelist_view(self, request, extra_context=None):
        self.request = request
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        self.request = request # Crucial pour que display_target_info_readonly ait accès
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.request = request
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

# --- Fin de l'extrait de code ---