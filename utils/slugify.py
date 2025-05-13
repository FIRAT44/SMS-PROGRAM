import re
import unicodedata

def slugify(value):
    """
    Dosya veya klasör ismi olarak güvenle kullanılabilecek bir slug üretir.
    Türkçe karakterler ve özel karakterler temizlenir.
    """
    # Unicode normalize et ve ascii dışı karakterleri kaldır
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    # Küçük harfe çevir
    value = value.lower()

    # Harf, sayı ve alt çizgi dışındaki karakterleri tireyle değiştir
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')

    return value
