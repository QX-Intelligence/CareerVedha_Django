from django.utils.timezone import now
from django.utils.html import strip_tags
from django.conf import settings
from .models import Article
from apps.media.s3 import get_s3_client


def get_article_translation(article, lang="te"):
    """
    Returns the translation for the given language with robust fallbacks.
    1. Requested language
    2. Telugu ('te')
    3. English ('en')
    4. First available
    """
    translations = list(article.translations.all())
    if not translations:
        return None
        
    # 1. Try requested
    tr = next((t for t in translations if t.language == lang), None)
    if tr: return tr
    
    # 2. Try Telugu
    tr = next((t for t in translations if t.language == "te"), None)
    if tr: return tr
    
    # 3. Try English
    tr = next((t for t in translations if t.language == "en"), None)
    if tr: return tr
    
    # 4. Fallback to first
    return translations[0]

def summary_from_content(html_text, max_len=140):
    """
    Extracts a plain text summary from HTML content if a summary isn't provided.
    """
    if not html_text:
        return ""
    plain = strip_tags(html_text)
    plain = " ".join(plain.split())
    return plain[:max_len].strip()



def prepare_article_card(article, lang="te"):
    """
    Prepares a standardized article card dictionary for public listings.
    Internalizes media resolution.
    Uses prefetched data to avoid N+1 queries.
    """
    from apps.media.utils import get_media_url
    tr = get_article_translation(article, lang)
    if not tr:
        return None

    card = {
        "id": article.id,
        "slug": article.slug,
        "section": article.section,
        "title": tr.title,
        "summary": tr.summary or summary_from_content(tr.content),
        "meta_title": article.meta_title,
        "meta_description": article.meta_description,
        "is_top_story": article.is_top_story,
        "youtube_url": article.youtube_url,
        "og_title": article.og_title,
        "og_description": article.og_description,
        "og_image_url": article.og_image_url,
        "published_at": article.published_at,
        "created_at": article.created_at,
        "views_count": article.views_count,
        "categories": [
            {
                "id": ac.category.id,
                "name": ac.category.name,
                "slug": ac.category.slug,
                "section": ac.category.section.slug if ac.category.section else None
            }
            for ac in article.article_categories.all()
        ],
    }

    # Add featured media (first media attachment) - Use prefetched links
    media_links = list(article.media_links.all())
    first_media_link = media_links[0] if media_links else None
    
    if first_media_link and first_media_link.media:
        media = first_media_link.media
        card["featured_media"] = {
            "media_id": media.id,
            "url": get_media_url(media),
            "media_type": media.media_type,
        }
    
    return card
