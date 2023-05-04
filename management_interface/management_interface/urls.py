"""management_interface URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from .views import care_provider_search

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "care-provider-location/_search/",
        care_provider_search,
        name="care_provider_search",
    ),
    path("saml/", include("django_cognito_saml.urls")),
]

admin.site.site_header = "Hospital Activity Notification Service Management Interface"
admin.site.site_title = "HANS Management Interface"
admin.site.index_title = "Welcome to HANS Management Interface"
