from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from api.models import Hotel, Room, Package, Car, KnowledgeDocument
from api.services.chroma_service import chroma_client
from api.utils.vector_utils import get_document_id, get_vector_text, get_vector_metadata
import logging

logger = logging.getLogger(__name__)

MODELS_TO_SYNC = [Hotel, Room, Package, Car, KnowledgeDocument]

for model in MODELS_TO_SYNC:
    @receiver(post_save, sender=model)
    def sync_to_chroma_on_save(sender, instance, created, **kwargs):
        is_active = getattr(instance, 'is_active', getattr(instance, 'is_available', True))
        if not is_active:
            # If item was deactivated, remove from vector store
            chroma_client.delete_document(get_document_id(instance))
            return
            
        text = get_vector_text(instance)
        if text:
            chroma_client.upsert_document(
                doc_id=get_document_id(instance),
                text=text,
                metadata=get_vector_metadata(instance)
            )

    @receiver(post_delete, sender=model)
    def remove_from_chroma_on_delete(sender, instance, **kwargs):
        chroma_client.delete_document(get_document_id(instance))
