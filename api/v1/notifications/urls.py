from django.urls import path

from api.v1.notifications.views import NotificationListView, NotificationReadView

notification_urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("read/", NotificationReadView.as_view(), name="read"),
]
