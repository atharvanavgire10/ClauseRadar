from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from audit.services import log_event
from .models import Organization, OrganizationMembership
from .serializers import OrganizationSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["slug"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.prefetch_related("memberships__user").all()
        return Organization.objects.filter(memberships__user=user).prefetch_related("memberships__user").distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        org = serializer.save(created_by=self.request.user)
        OrganizationMembership.objects.create(organization=org, user=self.request.user, role="OWNER")
        log_event(
            actor=self.request.user,
            organization=org,
            entity_type="organization",
            entity_id=org.id,
            action="organization.created",
            metadata={"name": org.name},
        )
