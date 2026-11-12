from django.http import JsonResponse
from django.urls import path
def health_check(request):
    return JsonResponse({"status": "ok", "message": "Django est en ligne !"})
urlpatterns = [path('api/v1/health', health_check)]
