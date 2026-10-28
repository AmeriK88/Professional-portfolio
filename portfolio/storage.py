from pathlib import Path, PurePosixPath

import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage


class PortfolioMediaStorage(MediaCloudinaryStorage):
    """
    Almacenamiento de imágenes y vídeos en Cloudinary.

    Conserva la extensión de los archivos nuevos en la
    referencia de Django para generar las URL correctas.
    """

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".webm",
        ".mov",
        ".avi",
        ".mkv",
    }

    def _get_resource_type(self, name):
        extension = PurePosixPath(name).suffix.lower()

        if extension in self.VIDEO_EXTENSIONS:
            return "video"

        return "image"

    def _save(self, name, content):
        name = self._normalise_name(name)
        name = self._prepend_prefix(name)

        resource_type = self._get_resource_type(name)

        # Conservamos el comportamiento de subida original.
        from django.core.files.uploadedfile import UploadedFile

        content = UploadedFile(content, name)
        response = self._upload(name, content)

        public_id = response["public_id"]

        # Los vídeos necesitan conservar su formato en Django.
        if resource_type == "video":
            file_format = response.get("format")

            if file_format:
                return f"{public_id}.{file_format}"

        return public_id

    def delete(self, name):
        resource_type = self._get_resource_type(name)
        public_id = name

        if resource_type == "video":
            public_id = str(PurePosixPath(name).with_suffix(""))

        response = cloudinary.uploader.destroy(
            public_id,
            invalidate=True,
            resource_type=resource_type,
        )

        return response.get("result") == "ok"