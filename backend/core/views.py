from django.shortcuts import  render
from django.http import Http404, HttpResponse
from django.urls import reverse
from seo.services import SEOOrchestrator
from seo.data import PageContext
from django.views import View
import os
from django.conf import settings

def robots_txt():
    file_path = os.path.join(settings.BASE_DIR, 'template', 'build', 'static', 'robots.txt')
    try:
        with open(file_path, 'r') as fichier:
            contenu = fichier.read()  # Lire le contenu du fichier
        return contenu
    except FileNotFoundError:
        return """User-agent: *\nDisallow: """
    

def custom_404_view(request, exception):
    return render(request, "build/index.html", {}, status=404)

def custom_500_view(request):
    return render(request, "build/index.html", {}, status=500)

def robots_txt(request):
    response = HttpResponse(robots_txt(), content_type='text/plain')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

class BasePageView(View):
    page_type: str = 'website'
    seo_orchestrator = SEOOrchestrator()

    def get_object(self): return None
    def get_extra_seo_data(self) -> dict: return {}

    def get_page_context(self, request, *args, **kwargs) -> PageContext:
         return PageContext(
             request=request,
             obj=self.get_object(),
             page_type=self.page_type,
             view_kwargs=kwargs,
             extra_data=self.get_extra_seo_data()
         )

    def get(self, request, *args, **kwargs):
        page_context = self.get_page_context(request, *args, **kwargs)
        seo_context_data = self.seo_orchestrator.get_seo_context(page_context)

        context = {
            'seo': seo_context_data,
        }
      
        return render(request, "build/index.html", context)
