from io import BytesIO
from urllib.parse import unquote_plus

import boto3
from PIL import ExifTags, Image

s3 = boto3.client("s3")
EXIF_ORIENTATION = next(k for k, v in ExifTags.TAGS.items() if v == "Orientation")


def resize_image(key, source_bucket, size=(120, 160), dest_bucket=None):
    """Download image from S3, resize, and upload to thumbnails/<key>."""
    if dest_bucket is None:
        dest_bucket = source_bucket

    try:
        # Download original image
        obj = s3.get_object(Bucket=source_bucket, Key=key)
        image = Image.open(obj["Body"])
    except Exception as e:
        print(f"Error: Unable to open image {key}: {e}")
        return None

    # Handle rotation via EXIF
    try:
        exif = dict(image._getexif().items())
        if exif.get(EXIF_ORIENTATION) == 3:
            image = image.rotate(180, expand=True)
        elif exif.get(EXIF_ORIENTATION) == 6:
            image = image.rotate(270, expand=True)
        elif exif.get(EXIF_ORIENTATION) == 8:
            image = image.rotate(90, expand=True)
    except Exception:
        pass  # No exif data

    # Compute resize dimensions
    dest_ratio = size[0] / float(size[1])
    source_ratio = image.size[0] / float(image.size[1])

    if image.size < size:
        new_width, new_height = image.size
    elif dest_ratio > source_ratio:
        new_width = int(image.size[0] * size[1] / float(image.size[1]))
        new_height = size[1]
    else:
        new_width = size[0]
        new_height = int(image.size[1] * size[0] / float(image.size[0]))

    image = image.resize((new_width, new_height), resample=Image.LANCZOS)

    # Center the image in the target size
    final_image = Image.new("RGBA", size)
    topleft = ((size[0] - new_width) // 2, (size[1] - new_height) // 2)
    final_image.paste(image, topleft)

    # Save resized image to memory
    bytes_stream = BytesIO()
    final_image.save(bytes_stream, "PNG")
    bytes_stream.seek(0)

    # Upload to destination
    dest_key = f"thumbnails/{key.split('/')[-1]}".replace(".jpg", ".png")
    s3.put_object(
        Bucket=dest_bucket, Key=dest_key, Body=bytes_stream, ContentType="image/png"
    )

    print(f"Thumbnail saved to s3://{dest_bucket}/{dest_key}")
    return dest_key


def lambda_handler(event, context):
    record = event["Records"][0]["s3"]
    bucket = record["bucket"]["name"]
    key = unquote_plus(record["object"]["key"])

    print(f">> Uploaded Image Details \n Bucket Name: {bucket}, Key: {key}")

    print(">> Resizing Image & Uploding to S3")
    resize_image(key, bucket)

    return None
