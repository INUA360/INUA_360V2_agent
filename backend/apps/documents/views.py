from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView, no_content
from apps.common.pagination import StandardPagination
from apps.common.permissions import IsBusinessOwner, IsMerchant
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from apps.documents.services import (
    checklist,
    delete_document,
    open_document,
    signed_download_url,
    upload_document,
)


class DocumentListCreateView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        rows = Document.objects.for_user(request.user).filter(business=business)  # type: ignore[attr-defined]
        paginator = StandardPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        payload = {
            "checklist": checklist(business),
            "documents": DocumentSerializer(page if page is not None else rows, many=True).data,
        }
        if page is not None:
            paginated = paginator.get_paginated_response(payload["documents"]).data
            paginated["checklist"] = payload["checklist"]
            return Response(paginated)
        return Response(payload)

    def post(self, request: Any) -> Response:
        business = self.get_business()
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = upload_document(
            business,
            request.user,
            serializer.validated_data["doc_type"],
            serializer.validated_data["file"],
            serializer.validated_data.get("expiry_date"),
        )
        from apps.audit.services import log_event
        from apps.businesses.onboarding import advance_onboarding_step
        from apps.opportunities.services import recompute_matches
        from apps.readiness.services import recompute_readiness

        advance_onboarding_step(request.user, 4)
        log_event(
            actor=request.user,
            business=business,
            action="document.uploaded",
            entity=f"document:{document.id}",
            metadata={"doc_type": document.doc_type, "size": document.size},
        )
        recompute_readiness(business)
        recompute_matches(business)
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentChecklistView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        return Response({"checklist": checklist(self.get_business())})


class DocumentDetailView(MerchantAPIView):
    permission_classes = [IsAuthenticated, IsMerchant, IsBusinessOwner]

    def _get(self, request: Any, pk: Any) -> Document:
        document = (
            Document.objects.for_user(request.user)  # type: ignore[attr-defined]
            .filter(pk=pk)
            .first()
        )
        if document is None:
            raise NotFound("Not found.")
        self.check_object_permissions(request, document)
        return cast(Document, document)

    def delete(self, request: Any, pk: Any) -> Response:
        document = self._get(request, pk)
        business = document.business
        delete_document(document)
        from apps.audit.services import log_event
        from apps.opportunities.services import recompute_matches
        from apps.readiness.services import recompute_readiness

        log_event(
            actor=request.user,
            business=business,
            action="document.deleted",
            entity=f"document:{pk}",
        )
        recompute_readiness(business)
        recompute_matches(business)
        return no_content()


class DocumentDownloadURLView(MerchantAPIView):
    permission_classes = [IsAuthenticated, IsMerchant, IsBusinessOwner]

    def get(self, request: Any, pk: Any) -> Response:
        document = (
            Document.objects.for_user(request.user)  # type: ignore[attr-defined]
            .filter(pk=pk)
            .first()
        )
        if document is None:
            raise NotFound("Not found.")
        self.check_object_permissions(request, document)
        url, ttl = signed_download_url(document)
        return Response({"url": url, "expires_in": ttl})


class DocumentFileView(MerchantAPIView):
    permission_classes = [IsAuthenticated, IsMerchant, IsBusinessOwner]

    def get(self, request: Any, pk: Any):  # type: ignore[no-untyped-def]
        document = (
            Document.objects.for_user(request.user)  # type: ignore[attr-defined]
            .filter(pk=pk)
            .first()
        )
        if document is None:
            raise NotFound("Not found.")
        self.check_object_permissions(request, document)
        return open_document(document)
