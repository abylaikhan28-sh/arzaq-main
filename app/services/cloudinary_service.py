# app/services/cloudinary_service.py
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
import io
from PIL import Image

from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


class CloudinaryService:
    """Service for handling image uploads to Cloudinary"""

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    @staticmethod
    def validate_image(file: UploadFile) -> None:
        """Validate image file"""
        # Check file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        extension = file.filename.split('.')[-1].lower()
        if extension not in CloudinaryService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(CloudinaryService.ALLOWED_EXTENSIONS)}"
            )

    @staticmethod
    async def upload_image(file: UploadFile, folder: str = "arzaq") -> dict:
        """
        Upload image to Cloudinary

        Args:
            file: Upload file from FastAPI
            folder: Cloudinary folder name

        Returns:
            dict with url, public_id, width, height
        """
        try:
            # Validate image
            CloudinaryService.validate_image(file)

            # Read file content
            content = await file.read()

            # Check file size
            if len(content) > CloudinaryService.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is 5MB"
                )

            # Optimize image before upload
            image = Image.open(io.BytesIO(content))

            # Convert RGBA to RGB if necessary
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background

            # Resize if too large (max 1920px width)
            max_width = 1920
            if image.width > max_width:
                ratio = max_width / image.width
                new_size = (max_width, int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Save optimized image to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)

            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                output,
                folder=folder,
                resource_type="image",
                transformation=[
                    {'quality': 'auto'},
                    {'fetch_format': 'auto'}
                ]
            )

            return {
                "url": result['secure_url'],
                "public_id": result['public_id'],
                "width": result['width'],
                "height": result['height']
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {str(e)}"
            )

    @staticmethod
    def delete_image(public_id: str) -> bool:
        """Delete image from Cloudinary"""
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            print(f"Failed to delete image: {str(e)}")
            return False


# Create singleton instance
cloudinary_service = CloudinaryService()
