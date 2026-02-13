import requests
import xml.etree.ElementTree as ET
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class CurrentAffairsView(APIView):
    """
    Fetch current affairs from multiple sources.
    Supports International, National, and State-wise news (all Indian states).
    Includes pagination support.
    """
    
    # List of all Indian states and UTs
    INDIAN_STATES = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
    ]

    def get(self, request):
        news_type = request.query_params.get('type', 'national')
        state = request.query_params.get('state', 'Andhra Pradesh')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        
        # Validate state
        if state not in self.INDIAN_STATES:
            state = 'Andhra Pradesh'
        
        cache_key = f"current_affairs_v5_{news_type}_{state.replace(' ', '_')}"
        cached_data = cache.get(cache_key)
        
        if not cached_data:
            try:
                if news_type == 'international':
                    all_articles = self._fetch_international()
                elif news_type == 'national':
                    all_articles = self._fetch_national()
                elif news_type == 'statewide':
                    all_articles = self._fetch_statewide(state)
                else:
                    all_articles = self._fetch_national()
                
                # Cache for 1 hour
                cache.set(cache_key, all_articles, 3600)
                cached_data = all_articles
            except Exception as e:
                logger.error(f"Error fetching {news_type} news: {e}")
                return Response(
                    {"error": f"Failed to fetch news: {str(e)}"},
                    status=status.HTTP_502_BAD_GATEWAY
                )
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_articles = cached_data[start_idx:end_idx]
        
        result = {
            "articles": paginated_articles,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": len(cached_data),
                "has_more": end_idx < len(cached_data)
            }
        }
        
        return Response(result)

    def _fetch_international(self):
        """Fetch international news from ok.surf"""
        url = 'https://ok.surf/api/v1/cors/news-feed'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        
        news_items = raw_data.get('World', [])
        
        articles = []
        for item in news_items:
            articles.append({
                "title": item.get('title'),
                "description": item.get('title'),
                "url": item.get('link'),
                "image": item.get('og'),
                "publishedAt": item.get('timestamp'),
                "source": {
                    "name": item.get('source'),
                    "icon": item.get('source_icon')
                }
            })
        return articles

    def _fetch_national(self):
        """Fetch national India news from Google News RSS"""
        url = 'https://news.google.com/rss/search?q=India+when:1d&hl=en-IN&gl=IN&ceid=IN:en'
        return self._parse_rss(url, 'Google News India')

    def _fetch_statewide(self, state):
        """Fetch state-specific news from Google News RSS"""
        state_query = state.replace(' ', '+')
        url = f'https://news.google.com/rss/search?q={state_query}+when:1d&hl=en-IN&gl=IN&ceid=IN:en'
        return self._parse_rss(url, f'Google News {state}')

    def _parse_rss(self, url, default_source_name):
        """Parse RSS feed and return articles"""
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        articles = []
        
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Google News RSS format: "Title - Source"
            actual_title = title
            item_source = default_source_name
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                actual_title = parts[0]
                item_source = parts[1]

            # Extract image
            image_url = ""
            media_content = item.find('{http://search.yahoo.com/mrss/}content')
            if media_content is not None:
                image_url = media_content.get('url', '')
            
            if not image_url:
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    image_url = enclosure.get('url', '')

            articles.append({
                "title": actual_title,
                "description": description[:300] if description else actual_title[:200],
                "url": link,
                "image": image_url,
                "publishedAt": pub_date,
                "source": {
                    "name": item_source,
                    "icon": ""
                }
            })
        return articles
