from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Make sure .as_asgi() is at the end!
    path("websocket/calls/<int:user_id>/", consumers.CallConsumer.as_asgi()),
]