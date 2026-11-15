"""Only catalog images are public. Customer artwork and avatars stay private."""
import mimetypes
from pathlib import PurePosixPath
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

_ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}

@require_GET
def public_catalog_image(request, image_path):
    # Never follow .., special path separators or hidden files from user input.
    path = PurePosixPath(image_path)
    if (not image_path or image_path.startswith('/') or '\\' in image_path
        or any(part in ('', '.', '..') or part.startswith('.') for part in image_path.split('/'))
        or path.suffix.lower() not in _ALLOWED):
        raise Http404('Fichier introuvable')
    storage_path = 'catalog/' + str(path)
    try:
        handle = default_storage.open(storage_path, 'rb')
    except (FileNotFoundError, OSError, ValueError):
        raise Http404('Fichier introuvable')
    content_type = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
    response = FileResponse(handle, content_type=content_type)
    response['Cache-Control'] = 'public, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
