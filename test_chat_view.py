"""
Test script to mock ChatView POST request and verify full RAG query end-to-end.
"""

import os
import sys
import json
import django
from django.test import RequestFactory

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.views import ChatView

def test_chat_view():
    print("Testing ChatView RAG end-to-end...")
    
    # 1. Prepare request body
    body = {
        "question": "Can you recommend hotels in Islamabad?",
        "session_id": None
    }
    
    # 2. Create mock request using RequestFactory
    factory = RequestFactory()
    request = factory.post(
        '/api/chat/',
        data=json.dumps(body),
        content_type='application/json'
    )
    
    # 3. Call ChatView post method
    view = ChatView()
    response = view.post(request)
    
    # 4. Parse response
    print(f"Status Code: {response.status_code}")
    res_data = json.loads(response.content.decode('utf-8'))
    print("Response JSON data:")
    print(json.dumps(res_data, indent=2))

if __name__ == '__main__':
    test_chat_view()
