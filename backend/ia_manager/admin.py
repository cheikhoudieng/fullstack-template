from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json

try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

from ia_manager.models import IAInteraction


@admin.register(IAInteraction)
class IAInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'created_at', 'model_name', 'has_error', 'short_input_preview', 'short_output_preview') # Changé: timestamp -> created_at
    list_filter = ('model_name', 'created_at', 'user') # Changé: timestamp -> created_at
    search_fields = ('id__iexact', 'user__username', 'user__email', 'model_name', 'input_data__icontains', 'output_data__icontains', 'error__icontains')
    # Ajout de 'created_at' et 'updated_at' aux readonly_fields
    readonly_fields = ('id', 'created_at', 'updated_at', 'formatted_input_data', 'formatted_output_data', 'formatted_metadata')
    ordering = ('-created_at',) # Correspond au Meta.ordering, mais explicite ici

    fieldsets = (
        (None, {
            # Changé: timestamp -> created_at. Ajout de updated_at
            'fields': ('id', 'user', 'created_at', 'updated_at', 'model_name')
        }),
        ('Données d\'Entrée', {
            'fields': ('formatted_input_data',),
        }),
        ('Données de Sortie', {
            'fields': ('formatted_output_data',),
        }),
        ('Métadonnées et Erreur', {
            'fields': ('formatted_metadata', 'error'),
            'classes': ('collapse',),
        }),
    )

    def user_display(self, obj):
        return str(obj.user) if obj.user else "N/A (Système)"
    user_display.short_description = 'Utilisateur'
    user_display.admin_order_field = 'user'

    def has_error(self, obj):
        return bool(obj.error)
    has_error.boolean = True
    has_error.short_description = 'Erreur Présente'

    def _format_json_field(self, data, field_name_for_style="json_data"):
        if data is None:
            return "N/A"
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if PYGMENTS_AVAILABLE:
            formatter = HtmlFormatter(style='friendly', cssclass=f'highlight-{field_name_for_style}')
            html_code = highlight(json_str, JsonLexer(), formatter)
            # Pour une meilleure performance, ajouter ces styles via Media class de ModelAdmin.
            css = formatter.get_style_defs(f'.highlight-{field_name_for_style}')
            return mark_safe(f"<style>{css}</style>{html_code}")
        else:
            return format_html('<pre>{}</pre>', json_str)

    def formatted_input_data(self, obj):
        return self._format_json_field(obj.input_data, "input_data")
    formatted_input_data.short_description = 'Données d\'Entrée (Formatées)'

    def formatted_output_data(self, obj):
        return self._format_json_field(obj.output_data, "output_data")
    formatted_output_data.short_description = 'Données de Sortie (Formatées)'

    def formatted_metadata(self, obj):
        return self._format_json_field(obj.metadata, "metadata")
    formatted_metadata.short_description = 'Métadonnées (Formatées)'
    
    def short_preview(self, data, max_len=50):
        if data is None:
            return "N/A"
        s = json.dumps(data)
        return (s[:max_len] + '...') if len(s) > max_len else s

    def short_input_preview(self, obj):
        return self.short_preview(obj.input_data)
    short_input_preview.short_description = 'Aperçu Entrée'

    def short_output_preview(self, obj):
        return self.short_preview(obj.output_data)
    short_output_preview.short_description = 'Aperçu Sortie'