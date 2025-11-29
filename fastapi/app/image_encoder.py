"""
이미지 인코딩 모듈

이미지를 Base64로 인코딩하고 Claude 한도에 맞게 최적화하는 기능을 제공합니다.
"""

import base64
import io
import os
from typing import Tuple

try:
    from PIL import Image  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "이미지 최적화를 위해 Pillow가 필요합니다. 'pip install Pillow' 실행 후 다시 시도하세요."
    ) from exc


RESAMPLE_FILTER = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

# Claude 이미지 입력 제약 대응 (환경변수로 조정 가능)
MAX_IMAGES_FOR_LLM = int(os.getenv("LLM_IMAGE_MAX_COUNT", "4"))
MAX_LLM_IMAGE_BYTES = int(os.getenv("LLM_IMAGE_MAX_BYTES", str(950_000)))  # 약간의 버퍼
MAX_LLM_IMAGE_DIMENSION = int(os.getenv("LLM_IMAGE_MAX_DIMENSION", "1024"))


def get_mime_type_from_url(url: str, content_type: str | None = None) -> str:
    """
    URL과 Content-Type 헤더로부터 MIME 타입을 결정합니다.
    
    Args:
        url: 이미지 URL
        content_type: HTTP 응답의 Content-Type 헤더 값
    
    Returns:
        MIME 타입 문자열 (예: "image/jpeg", "image/png")
    """
    # Content-Type 헤더가 있고 이미지인 경우 사용
    if content_type and 'image' in content_type:
        return content_type
    
    # 확장자로 판단
    ext = os.path.splitext(url)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    return mime_map.get(ext, 'image/jpeg')


def optimize_image_bytes(
    raw_bytes: bytes,
    mime_type: str,
    max_bytes: int = MAX_LLM_IMAGE_BYTES,
    max_dimension: int = MAX_LLM_IMAGE_DIMENSION,
) -> Tuple[bytes, str, int, int]:
    """
    Claude 한도(1MB) 내로 이미지를 맞추기 위해 리사이즈/재압축합니다.

    Args:
        raw_bytes: 원본 이미지 바이트 데이터
        mime_type: 원본 이미지의 MIME 타입
        max_bytes: 최대 허용 바이트 수 (기본값: MAX_LLM_IMAGE_BYTES)
        max_dimension: 최대 이미지 차원 (픽셀 단위, 기본값: MAX_LLM_IMAGE_DIMENSION)

    Returns:
        (optimized_bytes, optimized_mime_type, original_size, optimized_size) 튜플
    """
    original_size = len(raw_bytes)
    if original_size <= max_bytes:
        return raw_bytes, mime_type, original_size, original_size

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            longest_side = max(img.size)
            if longest_side > max_dimension:
                scale = max_dimension / float(longest_side)
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, RESAMPLE_FILTER)

            buffer = io.BytesIO()
            quality = 85
            optimized_size = original_size

            while quality >= 50:
                buffer.seek(0)
                buffer.truncate(0)
                img.save(buffer, format="JPEG", optimize=True, quality=quality)
                optimized_size = buffer.tell()
                if optimized_size <= max_bytes or quality == 50:
                    break
                quality -= 5

            return buffer.getvalue(), "image/jpeg", original_size, optimized_size
    except Exception:
        # Pillow 처리 실패 시 원본 전달 (최소한 Claude 호출 전에 필터링 가능)
        return raw_bytes, mime_type, original_size, original_size


def encode_image_to_base64(
    image_bytes: bytes,
    mime_type: str,
    max_bytes: int = MAX_LLM_IMAGE_BYTES,
    max_dimension: int = MAX_LLM_IMAGE_DIMENSION,
) -> Tuple[str, str, int, int]:
    """
    이미지 바이트를 Base64 문자열로 인코딩합니다.
    Claude 한도에 맞게 최적화도 함께 수행합니다.

    Args:
        image_bytes: 이미지 바이트 데이터
        mime_type: 이미지의 MIME 타입
        max_bytes: 최대 허용 바이트 수 (기본값: MAX_LLM_IMAGE_BYTES)
        max_dimension: 최대 이미지 차원 (픽셀 단위, 기본값: MAX_LLM_IMAGE_DIMENSION)

    Returns:
        (base64_string, optimized_mime_type, original_size, optimized_size) 튜플
    """
    optimized_bytes, optimized_mime, original_size, optimized_size = optimize_image_bytes(
        image_bytes,
        mime_type,
        max_bytes,
        max_dimension,
    )
    
    base64_string = base64.b64encode(optimized_bytes).decode('utf-8')
    
    return base64_string, optimized_mime, original_size, optimized_size

