"""
Upload Utilities Module.

Provides helper functions for handling file uploads:
- File extension validation
- Secure file saving with unique filenames
- Subfolder organization (avatars, banners, posts)
"""
from __future__ import annotations

import os
import uuid
from werkzeug.utils import secure_filename

# Allowed file extensions
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def allowed_file(filename: str, allow_video: bool = False) -> bool:
    """Check if a filename has an allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = ALL_MEDIA_EXTENSIONS if allow_video else IMAGE_EXTENSIONS
    return ext in allowed


def save_upload(file, subfolder: str, upload_folder: str, allow_video: bool = False) -> str | None:
    """
    Save an uploaded file to disk and return its URL path.

    Args:
        file: The uploaded file object from request.files
        subfolder: Subdirectory name (e.g., 'avatars', 'banners', 'posts')
        upload_folder: Base upload directory path
        allow_video: Whether to allow video file extensions

    Returns:
        URL path to the saved file (e.g., '/static/uploads/posts/abc123.jpg'),
        or None if the file is invalid.
    """
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename, allow_video=allow_video):
        return None

    # Generate unique filename to avoid collisions
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # Ensure subfolder exists
    dest_dir = os.path.join(upload_folder, subfolder)
    os.makedirs(dest_dir, exist_ok=True)

    # Save file
    filepath = os.path.join(dest_dir, unique_name)
    file.save(filepath)

    # Return URL path relative to static
    return f"/static/uploads/{subfolder}/{unique_name}"
