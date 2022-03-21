from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as drf_token_views
from . import views
from . import consumers

router = routers.DefaultRouter()
router.register(r"c2", views.C2sViewSet, basename="c2s")
router.register(r"listeners", views.ListenersViewSet, basename="listeners")
router.register(r"launchers", views.LaunchersViewSet, basename="launchers")
router.register(r"agents", views.AgentsViewSet, basename="agents")
router.register(r"tasks", views.TasksViews, basename="tasks")
router.register(r"users", views.UserViewSet, basename="users")

urlpatterns = [
    path("api-auth", include("rest_framework.urls", namespace="rest_framework")),
    path("", include(router.urls)),
    path("api-token-auth/", drf_token_views.obtain_auth_token),
    path("change_password/", views.ChangePassword.as_view()),
]

websocket_urlpatterns = [
    path("agents/<int:agent_id>/interact/", consumers.AgentConsumer.as_asgi()),
]
