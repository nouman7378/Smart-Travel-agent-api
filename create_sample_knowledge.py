"""
Test script to add sample knowledge documents for RAG testing.
Run this script to populate the database with travel tips and guides.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import KnowledgeDocument

def create_sample_knowledge():
    """Create sample KnowledgeDocument items for RAG context."""
    print("Creating sample knowledge documents...")
    
    sample_docs = [
        {
            'title': 'Islamabad General Travel Guide',
            'destination': 'Islamabad',
            'category': 'guide',
            'content': (
                "Islamabad is the capital city of Pakistan. It is a modern, clean, and extremely secure city. "
                "The best time to visit is from October to April when the weather is cool and pleasant. "
                "Key tourist spots include Faisal Mosque, Daman-e-Koh viewpoint, Margalla Hills for hiking, "
                "and Monal Restaurant. It is highly recommended to use ridesharing services like Yango or Indrive "
                "to get around. Safe travel is ensured by extensive CCTV coverage and police checkposts."
            ),
            'tags': ['islamabad', 'guide', 'margalla', 'tourism'],
            'source': 'internal_guide',
            'is_active': True,
        },
        {
            'title': 'Lahore Cultural and Food Guide',
            'destination': 'Lahore',
            'category': 'guide',
            'content': (
                "Lahore is known as the cultural capital of Pakistan. Famous for its vibrant food culture and historic Mughlai architecture. "
                "Top attractions include the Lahore Fort, Badshahi Mosque, Shalimar Gardens, and the Walled City (Androon Shehar). "
                "For food lovers, the famous Food Street in Fort Road offers stunning views of Badshahi Mosque alongside traditional Lahori "
                "dishes like Siri Paye, Karahi, and Halwa Puri. The weather in summers can be extremely hot, so winter (November to February) "
                "is the ideal time to explore Lahore."
            ),
            'tags': ['lahore', 'food', 'culture', 'history'],
            'source': 'internal_guide',
            'is_active': True,
        },
        {
            'title': 'Bali Travel Safety and Best Tips',
            'destination': 'Bali',
            'category': 'safety',
            'content': (
                "Bali is a peaceful, tropical destination in Indonesia. General safety precautions include: "
                "1. Drink only bottled or filtered water to avoid 'Bali Belly'. "
                "2. When visiting temples (like Uluwatu or Besakih), always wear a sarong and sash to respect local culture. "
                "3. Renting scooters is cheap, but ensure you have an international driving permit and always wear a helmet. "
                "The currency is Indonesian Rupiah (IDR). Visa-on-arrival is available for travelers from many countries."
            ),
            'tags': ['bali', 'safety', 'tips', 'temple'],
            'source': 'faq',
            'is_active': True,
        },
        {
            'title': 'Maldives Weather and Transfer Guide',
            'destination': 'Maldives',
            'category': 'weather',
            'content': (
                "The Maldives enjoys a tropical climate with hot temperatures year-round. "
                "The dry season (Northeast Monsoon) runs from November to April and is the peak travel period with clear blue skies. "
                "The wet season (Southwest Monsoon) is from May to October, bringing occasional rain and wind. "
                "Transfer from Malé airport to luxury private resorts is typically done via speedboats (for closer islands) "
                "or scenic seaplanes (for distant atolls). Ensure seaplane flights are booked in advance as they only fly during daylight."
            ),
            'tags': ['maldives', 'weather', 'seaplane', 'resort'],
            'source': 'faq',
            'is_active': True,
        }
    ]
    
    for doc_data in sample_docs:
        existing_doc = KnowledgeDocument.objects.filter(title=doc_data['title']).first()
        if existing_doc:
            print(f"  - Document '{doc_data['title']}' already exists, updating...")
            for key, value in doc_data.items():
                setattr(existing_doc, key, value)
            existing_doc.save()
        else:
            print(f"  - Creating document '{doc_data['title']}'...")
            KnowledgeDocument.objects.create(**doc_data)
            
    print(f"\nSample knowledge documents created successfully! Total: {KnowledgeDocument.objects.count()}")

if __name__ == '__main__':
    create_sample_knowledge()
