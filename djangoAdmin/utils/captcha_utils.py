from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
import string


def generate_captcha():
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    image = Image.new('RGB', (120, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 28)

    draw.text((10, 5), captcha_text, font=font, fill=(0, 0, 0))

    # 添加干扰线
    for _ in range(5):
        start = (random.randint(0, 120), random.randint(0, 40))
        end = (random.randint(0, 120), random.randint(0, 40))
        draw.line([start, end], fill=(0, 0, 0), width=1)

    # 将图片保存到内存中
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)

    return captcha_text, buffer
