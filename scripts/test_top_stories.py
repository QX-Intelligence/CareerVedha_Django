import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from apps.articles.models import TopStory, TopStoryMedia
from apps.taxonomy.models import Category, Section
from apps.media.models import MediaAsset
from unittest.mock import patch

def run_tests():
    client = APIClient(HTTP_HOST='localhost')
    
    # Setup test data
    section, _ = Section.objects.get_or_create(name='Test Section', slug='test-section')
    category, _ = Category.objects.get_or_create(name='Test Category', slug='test-category', section=section)
    
    # Grab existing media to bypass constraint errors
    media_assets = list(MediaAsset.objects.all()[:2])
    if len(media_assets) < 2:
        print("Not enough media assets in DB, please make sure at least 2 exist.")
        return
        
    media1, media2 = media_assets[0], media_assets[1]
    
    user = {'user_id': 1, 'role': 'ROLE_ADMIN', 'username': 'admin'}
    
    print("--- STARTING CRUD TESTS ---")
    
    with patch('apps.common.authentication.JWTAuthentication.authenticate', return_value=(user, None)):
        # 1. CREATE
        payload = {
            'title_en': 'Test En',
            'title_te': 'Test Te',
            'category': category.id,
            'media_ids': [media1.id, media2.id]
        }
        res_post = client.post('/api/django/cms/articles/top-stories-cms/', payload, format='json')
        print('POST /top-stories-cms/ ->', res_post.status_code)
        if res_post.status_code != 201:
            print("POST FAILED:", res_post.data)
            return

        story_id = res_post.data['id']
        print(f"Created Story ID: {story_id}")
        
        # 2. READ (Admin)
        res_get = client.get('/api/django/cms/articles/top-stories-cms/')
        print('GET /top-stories-cms/ ->', res_get.status_code)
        
        # 3. UPDATE
        patch_payload = {
            'title_en': 'Updated En',
            'media_ids': [media2.id] # keep only 1 media
        }
        res_patch = client.patch(f'/api/django/cms/articles/top-stories-cms/{story_id}/', patch_payload, format='json')
        print('PATCH /top-stories-cms/<id>/ ->', res_patch.status_code)
        if res_patch.status_code == 200:
            print("Updated Title:", res_patch.data.get('title_en'))
            print("Media Count:", len(res_patch.data.get('media', [])))
        
        # 4. GET (Public List)
        res_public = client.get(f'/api/django/cms/articles/top-stories/list/?category=test-category')
        print('GET /top-stories/list/ ->', res_public.status_code)
        if res_public.status_code == 200:
            print("Public List Results Count:", len(res_public.data.get('results', [])))
            
        # 5. DELETE
        res_del = client.delete(f'/api/django/cms/articles/top-stories-cms/{story_id}/')
        print('DELETE /top-stories-cms/<id>/ ->', res_del.status_code)

if __name__ == "__main__":
    run_tests()
