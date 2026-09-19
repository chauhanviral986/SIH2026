from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, random

OUT="samples"
os.makedirs(OUT,exist_ok=True)
W,H=1200,760

def font(size,bold=False):
    paths=[
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in paths:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def base():
    im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im)
    d.rectangle((8,8,W-8,H-8),outline=(40,60,90),width=5)
    d.text((45,28),"SYNTHETIC TEST DOCUMENT",font=font(36,True),fill=(150,0,0))
    d.text((45,75),"NOT A REAL PASSPORT • HACKATHON DEMO ONLY",font=font(23,True),fill=(150,0,0))
    d.rectangle((50,145,300,455),outline=(80,90,110),width=3)
    # Simple non-photographic portrait placeholder.
    d.ellipse((115,190,235,310),fill=(210,190,170),outline=(50,50,50),width=3)
    d.rectangle((95,305,255,425),fill=(90,100,130),outline=(50,50,50),width=3)
    fields=[
        ("TYPE","P"),("COUNTRY CODE","DMD"),("DOCUMENT NO","TEST12345"),
        ("SURNAME","DEMO"),("GIVEN NAMES","ARJUN TEST"),
        ("NATIONALITY","DEMO CITIZEN"),("DATE OF BIRTH","14 MAY 1998"),
        ("SEX","M"),("DATE OF ISSUE","01 JAN 2026"),("DATE OF EXPIRY","31 DEC 2030")
    ]
    y=160
    for k,v in fields:
        d.text((340,y),k,font=font(18,True),fill=(70,70,70))
        d.text((340,y+24),v,font=font(25),fill=(15,15,15))
        y+=54
    d.text((50,485),"Synthetic MRZ-like test area",font=font(18,True),fill=(80,80,80))
    d.rectangle((45,520,W-45,690),outline=(120,120,120),width=2)
    d.text((65,545),"P<DMDDEMO<<ARJUN<TEST<<<<<<<<<<<<<<<<<<<<",font=font(30),fill=(10,10,10))
    d.text((65,600),"TEST12345<0DMD9805141M3012315<<<<<<<<<<00",font=font(30),fill=(10,10,10))
    d.text((65,660),"ALL DATA IS FICTIONAL",font=font(18,True),fill=(150,0,0))
    return im

im=base()
im.save(os.path.join(OUT,"clean_synthetic_test.png"))
im.filter(ImageFilter.GaussianBlur(8)).save(os.path.join(OUT,"blurry_synthetic_test.png"))

tam=base()
d=ImageDraw.Draw(tam)
d.rectangle((650,265,1040,340),fill=(255,240,80))
d.text((665,280),"ALTERED TEST FIELD",font=font(25,True),fill=(120,0,0))
tam.save(os.path.join(OUT,"tampered_synthetic_test.png"))

# Clearly unrelated test cases.
card=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(card)
d.rectangle((10,10,W-10,H-10),outline=(30,30,30),width=4)
d.text((80,90),"DEMO TECH SOLUTIONS",font=font(50,True),fill=(20,20,20))
d.text((80,180),"HACKATHON TEST VISITING CARD",font=font(32),fill=(70,70,70))
d.text((80,300),"This is intentionally NOT an identity document.",font=font(30),fill=(150,0,0))
card.save(os.path.join(OUT,"unsupported_visiting_card.png"))

land=Image.new("RGB",(W,H),(120,170,210)); d=ImageDraw.Draw(land)
d.rectangle((0,480,W,H),fill=(70,140,70)); d.ellipse((850,70,1080,300),fill=(245,220,80))
d.text((60,60),"RANDOM PHOTO TEST",font=font(40,True),fill=(255,255,255))
land.save(os.path.join(OUT,"unsupported_random_photo.png"))
print("Created synthetic samples in samples/")
