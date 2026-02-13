from django.conf import settings
from apps.media.s3 import get_s3_client

from apps.media.utils import get_media_url

def prepare_material_card(material, lang="te"):
    """Standardized material data preparation for public listings."""
    tr = material.translations.filter(language=lang).first()
    if not tr:
        tr = material.translations.filter(language="te").first()
    
    if not tr: return None

    card = {
        "id": material.id,
        "title": tr.title,
        "summary": tr.summary,
        "content_preview": tr.summary if tr.summary else (tr.content[:140] if tr.content else ""),
        "material_type": material.material_type,
        "external_url": material.external_url,
        "status": material.status,
        "created_at": material.created_at,
    }

    # Add media links
    media_list = []
    for link in material.media_links.all():
        media_list.append({
            "id": link.media.id,
            "url": get_media_url(link.media),
            "usage": link.usage,
            "media_type": link.media.media_type
        })
    card["media"] = media_list
    
    return card

def prepare_subject_card(subject):
    """Standardized subject data preparation with icon resolution."""
    card = {
        "id": subject.id,
        "name": subject.name,
        "rank": subject.rank,
    }

    # Find ICON usage
    icon_link = subject.media_links.filter(usage="ICON").first()
    if icon_link:
        card["icon_url"] = get_media_url(icon_link.media)
    else:
        card["icon_url"] = None

    return card