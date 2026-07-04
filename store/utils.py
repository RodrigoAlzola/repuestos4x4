import requests

DEFAULT_PRODUCT_IMAGE = "https://parts.terraintamer.com/images/DEFAULTPARTIMG.JPG"


def verify_image_url(url, default_url=DEFAULT_PRODUCT_IMAGE):
    """Verifica si la URL de la imagen es válida, si no retorna la por defecto"""
    if not url or str(url).strip() == "":
        return default_url

    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            return url
        return default_url
    except requests.exceptions.RequestException:
        return default_url
