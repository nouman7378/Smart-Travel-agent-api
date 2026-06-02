from django.core.management.base import BaseCommand
from api.models import Hotel, Room, Package, Car, KnowledgeDocument
from api.services.chroma_service import chroma_client
from api.utils.vector_utils import get_document_id, get_vector_text, get_vector_metadata
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Syncs all active catalog models to ChromaDB vector store.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting ChromaDB synchronization...")
        
        if not chroma_client.ensure_initialized():
            self.stdout.write(self.style.ERROR("ChromaDB client failed to initialize. Check your settings and dependencies."))
            return
            
        models_to_sync = [
            (Hotel, 'is_active'),
            (Room, 'is_active'),
            (Package, 'is_active'),
            (Car, 'is_available'),
            (KnowledgeDocument, 'is_active')
        ]
        
        total_synced = 0
        for model_class, active_field in models_to_sync:
            self.stdout.write(f"Syncing {model_class.__name__}s...")
            # Fetch only active models
            filter_kwargs = {active_field: True}
            instances = model_class.objects.filter(**filter_kwargs)
            
            count = 0
            for instance in instances:
                text = get_vector_text(instance)
                if text:
                    chroma_client.upsert_document(
                        doc_id=get_document_id(instance),
                        text=text,
                        metadata=get_vector_metadata(instance)
                    )
                    count += 1
            total_synced += count
            self.stdout.write(f"Successfully synced {count} {model_class.__name__} records.")
            
        self.stdout.write(self.style.SUCCESS(f"Finished vector sync! Total documents: {total_synced}"))
