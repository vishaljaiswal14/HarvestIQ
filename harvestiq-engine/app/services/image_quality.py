import io
from PIL import Image, ImageStat, ImageFilter

def analyze_image_quality(image_bytes: bytes) -> dict:
    """
    Perform objective visual validation checks using Pillow:
    1. Resolution (min 300x300 pixels)
    2. Brightness (avoid completely white/overexposed images)
    3. Darkness (avoid completely black/underexposed images)
    4. Contrast (avoid extremely low-contrast, plain-colored images)
    5. Blur (variance/mean edge detection check)
    6. Corruption (cannot open the image format)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Ensure lazy load is completed to detect file integrity
        img.verify()
        # verify() closes the file pointer; we need to reopen to query sizes
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
    except Exception as e:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": f"Image file is corrupted or unsupported: {e}"
        }

    # 1. Resolution Check
    if width < 300 or height < 300:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": f"Image resolution is too low ({width}x{height}). Minimum required size is 300x300 pixels."
        }

    # Convert to grayscale for statistics
    gray_img = img.convert("L")
    stat = ImageStat.Stat(gray_img)
    
    mean_val = stat.mean[0]      # Mean pixel intensity (0 to 255)
    stddev_val = stat.stddev[0]  # Standard deviation of intensity (contrast)

    # 2. Brightness / Completely White Check
    if mean_val > 245 and stddev_val < 15:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": "Image is completely white or overexposed. Please capture with even exposure."
        }

    # 3. Darkness / Completely Black Check
    if mean_val < 10 and stddev_val < 10:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": "Image is completely dark or black. Please ensure there is adequate lighting."
        }

    # 4. Contrast Check
    if stddev_val < 12:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": "Image contrast is too low. Please ensure details of the leaves are visible."
        }

    # 5. Blur Check
    # Apply FIND_EDGES filter. A sharp, high-detail image yields high pixel averages.
    # A blurry, smooth, or out-of-focus image has extremely low edge pixel intensities.
    edge_img = gray_img.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edge_img)
    blur_score = edge_stat.mean[0]  # average edge intensity

    # Threshold for blur_score: if average edge intensity is less than 2.0, the image is out of focus.
    if blur_score < 2.0:
        return {
            "valid": False,
            "reason": "LOW_IMAGE_QUALITY",
            "message": f"Image is excessively blurry (blur score: {round(blur_score, 2)}). Please hold your device steady and re-focus."
        }

    return {
        "valid": True,
        "metrics": {
            "resolution": f"{width}x{height}",
            "blur_score": round(blur_score, 2),
            "brightness_score": round(mean_val, 2),
            "contrast_score": round(stddev_val, 2)
        }
    }
