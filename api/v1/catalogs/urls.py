from django.urls import path

from api.v1.catalogs.views import CatalogsView

app_name = "catalogs"

urlpatterns = [
    path("", CatalogsView.as_view(), name="list"),
]
