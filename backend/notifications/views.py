from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "kind", "read"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related("workspace").all()

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notif = self.get_object()
        notif.read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["read", "read_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = Notification.objects.filter(user=request.user, read=False).update(
            read=True, read_at=timezone.now())
        return Response({"marked_read": updated})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": Notification.objects.filter(user=request.user, read=False).count()})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user).all()

    @action(detail=False, methods=["get"])
    def all(self, request):
        """All kinds with current prefs (defaults True/True when unset)."""
        from .services import prefs_for

        return Response([
            {"kind": kind, "in_app": prefs_for(request.user, kind)[0], "email": prefs_for(request.user, kind)[1]}
            for kind, _ in Notification.Kind.choices
        ])
