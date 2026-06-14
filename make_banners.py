# -*- coding: utf-8 -*-
"""
make_banners.py — Google Ads banner'larını rates.json'dan DİNAMİK üretir.
Oran değişince çalıştırıldığında banner'lardaki örnek taksit otomatik güncellenir.
Çıktı: ads-output/ klasörüne 9 boyut PNG.
NOT: Üretilen PNG'ler Google Ads hesabına ELLE yüklenir; bu script sadece dosyaları tazeler.
"""
import os, json
from PIL import Image, ImageDraw, ImageFont

# ---- renk + font ----
BLUE="#2563EB"; BLUE2="#1D4ED8"; GREEN="#10B981"; GREEN2="#34D399"
NAVY="#0B1B3F"; INK="#22325E"; WHITE="#FFFFFF"; BG="#F4F8FF"; SOFT="#EAF2FF"; MUTE="#7B8AAC"
HERE=os.path.dirname(os.path.abspath(__file__))
F=os.path.join(HERE,"manrope.ttf")
OUT=os.path.join(HERE,"ads-output")

# ---- oranları oku ----
with open(os.path.join(HERE,"rates.json"),encoding="utf-8") as f:
    RATES=json.load(f)

# Banner'larda gösterilecek ÖRNEK senaryo: ihtiyaç 100.000 TL / 36 ay (vergiler dahil)
EX_AMOUNT=100000; EX_TERM=36
def annuity(P,rate_pct,n,taxed):
    r=(rate_pct/100)*(1.30 if taxed else 1.0)
    return P*r*(1+r)**n/((1+r)**n-1)
EX_PAY=annuity(EX_AMOUNT, RATES["ihtiyac"]["rate"], EX_TERM, True)

def tl(v): return "₺"+f"{v:,.0f}".replace(",",".")
AMOUNT_STR=tl(EX_PAY)                       # ör. ₺5.112
CHIP_STR=f"{EX_AMOUNT:,.0f}".replace(",",".")+" ₺ • "+str(EX_TERM)+" ay"
print(f"Örnek taksit: {AMOUNT_STR}/ay  (ihtiyaç %{RATES['ihtiyac']['rate']}, {EX_AMOUNT} TL, {EX_TERM} ay)")

def font(sz,w="bold"):
    f=ImageFont.truetype(F,sz)
    try:f.set_variation_by_axes([800 if w=="black" else 700 if w=="bold" else 500])
    except:pass
    return f

def hx(c): c=c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def grad(w,h,c1,c2):
    base=Image.new("RGB",(w,h)); px=base.load(); a,b=hx(c1),hx(c2)
    for y in range(h):
        for x in range(w):
            t=((x/w)+(y/h))/2; px[x,y]=lerp(a,b,t)
    return base

def wordmark(d,x,y,sz):
    f=font(sz,"black")
    d.text((x,y),"kredi",font=f,fill=BLUE); w=d.textlength("kredi",font=f)
    d.text((x+w,y),"oran",font=f,fill=GREEN); w2=d.textlength("kredioran",font=f)
    d.text((x+w2,y),".com",font=f,fill=NAVY)

def bolt(d,x,y,s,c=WHITE):
    d.polygon([(x+s*0.55,y),(x+s*0.1,y+s*0.6),(x+s*0.42,y+s*0.6),
               (x+s*0.25,y+s*1.1),(x+s*0.8,y+s*0.42),(x+s*0.46,y+s*0.42)],fill=c)

def speed_chip(d,x,y,sz,txt="SANİYEDE SONUÇ"):
    f=font(sz,"black"); tw=d.textlength(txt,font=f); h=int(sz*2.0); bw=tw+int(sz*2.6)
    d.rounded_rectangle([x,y,x+bw,y+h],radius=h//2,fill=GREEN)
    bolt(d,x+int(sz*0.7),y+int(sz*0.45),sz*1.1)
    d.text((x+int(sz*2.0),y+int(sz*0.5)),txt,font=f,fill=WHITE)
    return bw,h

def result_card(d,x,y,w,h,amount=AMOUNT_STR,sub="ÖRNEK AYLIK TAKSİT",chip=CHIP_STR):
    d.rounded_rectangle([x,y,x+w,y+h],radius=int(h*0.13),fill=WHITE)
    pad=int(w*0.08)
    d.text((x+pad,y+int(h*0.13)),sub,font=font(max(9,int(h*0.095)),"bold"),fill=MUTE)
    bigf=font(int(h*0.40),"black")
    d.text((x+pad-2,y+int(h*0.25)),amount,font=bigf,fill=BLUE)
    aw=d.textlength(amount,font=bigf)
    d.text((x+pad+aw+8,y+int(h*0.49)),"/ay",font=font(int(h*0.15),"bold"),fill=GREEN)
    cf=font(max(8,int(h*0.105)),"bold"); ctw=d.textlength(chip,font=cf); cy=y+int(h*0.73)
    d.rounded_rectangle([x+pad,cy,x+pad+ctw+int(h*0.16),cy+int(h*0.18)],radius=int(h*0.09),fill=SOFT)
    d.text((x+pad+int(h*0.08),cy+int(h*0.035)),chip,font=cf,fill=BLUE2)

def cta(d,x,y,text,sz,w=None,bg=BLUE,fg=WHITE):
    f=font(sz,"black"); tw=d.textlength(text,font=f); padx=int(sz*1.05); pady=int(sz*0.6)
    bw=w or tw+padx*2; bh=int(sz*1.0)+pady*2
    d.rounded_rectangle([x,y,x+bw,y+bh],radius=int(bh*0.3),fill=bg)
    d.text((x+(bw-tw)//2,y+pady),text,font=f,fill=fg)
    return bw,bh

def light_bg(w,h,panel_w):
    img=Image.new("RGB",(w,h),BG)
    if panel_w>0: img.paste(grad(panel_w,h,BLUE,GREEN),(w-panel_w,0))
    return img

def save(img,name): img.save(os.path.join(OUT,f"{name}.png")); print(f"  {name}.png ({img.width}x{img.height})")

def build():
    os.makedirs(OUT,exist_ok=True)

    # LANDSCAPE 1200x628
    img=light_bg(1200,628,520); d=ImageDraw.Draw(img)
    wordmark(d,70,60,52); speed_chip(d,70,150,28)
    d.text((70,255),"Kredi taksitini",font=font(58,"black"),fill=NAVY)
    d.text((70,325),"saniyede hesapla",font=font(58,"black"),fill=BLUE)
    d.text((72,425),"İhtiyaç • Konut • Taşıt",font=font(34,"bold"),fill=INK)
    cta(d,72,495,"Hemen Hesapla →",32)
    result_card(d,740,200,400,250)
    save(img,"landscape_1200x628")

    # SQUARE 1200x1200
    img=Image.new("RGB",(1200,1200),BG); d=ImageDraw.Draw(img)
    img.paste(grad(1200,300,BLUE,GREEN),(0,900)); d=ImageDraw.Draw(img)
    wordmark(d,90,80,72); speed_chip(d,90,195,38)
    d.text((90,310),"Ne kadar taksit",font=font(82,"black"),fill=NAVY)
    d.text((90,405),"ödeyeceksin?",font=font(82,"black"),fill=BLUE)
    d.text((92,530),"Tutarı gir, ödemeni anında gör.",font=font(40,"bold"),fill=INK)
    result_card(d,90,620,640,210)
    d.text((90,965),"Saniyeler içinde, ücretsiz.",font=font(50,"black"),fill=WHITE)
    f=font(40,"black"); t="kredioran.com →"; tw=d.textlength(t,font=f); bw=tw+90
    d.rounded_rectangle([1110-bw,1030,1110,1030+int(40*2.2)],radius=int(40*2.2*0.3),fill=WHITE)
    d.text((1110-bw+(bw-tw)//2,1030+int(40*0.6)),t,font=f,fill=BLUE)
    save(img,"square_1200x1200")

    # PORTRAIT 960x1200
    img=Image.new("RGB",(960,1200),BG); img.paste(grad(960,300,BLUE,GREEN),(0,900)); d=ImageDraw.Draw(img)
    wordmark(d,70,80,56); speed_chip(d,70,190,34)
    d.text((70,300),"Kredi",font=font(110,"black"),fill=NAVY)
    d.text((70,420),"taksitini",font=font(96,"black"),fill=NAVY)
    d.text((70,530),"saniyede gör",font=font(80,"black"),fill=BLUE)
    result_card(d,70,680,560,160)
    d.text((70,960),"Tutarı gir, ödemeni anında gör.",font=font(40,"black"),fill=WHITE)
    f=font(38,"black"); t="Hemen Hesapla →"; tw=d.textlength(t,font=f)
    d.rounded_rectangle([70,1040,630,1040+int(38*2.2)],radius=int(38*2.2*0.3),fill=WHITE)
    d.text((70+(560-tw)//2,1040+int(38*0.6)),t,font=f,fill=BLUE)
    save(img,"portrait_960x1200")

    # 300x250
    img=light_bg(300,250,0); d=ImageDraw.Draw(img)
    img.paste(grad(300,70,BLUE,GREEN),(0,180)); d=ImageDraw.Draw(img)
    wordmark(d,18,18,24); speed_chip(d,18,52,12,"SANİYEDE")
    d.text((18,90),"Taksitin",font=font(30,"black"),fill=NAVY)
    d.text((18,122),"ne kadar?",font=font(30,"black"),fill=BLUE)
    d.text((175,86),"ÖRNEK",font=font(8,"bold"),fill=MUTE)
    d.text((173,96),AMOUNT_STR,font=font(24,"black"),fill=BLUE)
    d.text((18,196),"Hesapla, ücretsiz →",font=font(18,"black"),fill=WHITE)
    save(img,"medrect_300x250")

    # 728x90
    img=light_bg(728,90,240); d=ImageDraw.Draw(img)
    wordmark(d,18,16,28)
    d.text((18,52),"Kredi taksitini saniyede hesapla",font=font(20,"bold"),fill=INK)
    d.text((505,18),"ÖRNEK TAKSİT",font=font(10,"bold"),fill=WHITE)
    d.text((503,32),AMOUNT_STR,font=font(28,"black"),fill=WHITE)
    f=font(20,"black"); t="Hesapla"; tw=d.textlength(t,font=f)
    d.rounded_rectangle([615,26,715,26+int(20*2.2)],radius=14,fill=WHITE)
    d.text((615+(100-tw)//2,26+int(20*0.6)),t,font=f,fill=BLUE)
    save(img,"leaderboard_728x90")

    # 160x600
    img=Image.new("RGB",(160,600),BG); img.paste(grad(160,200,BLUE,GREEN),(0,400)); d=ImageDraw.Draw(img)
    wordmark(d,16,30,17)
    d.text((16,90),"Kredi",font=font(34,"black"),fill=NAVY)
    d.text((16,128),"taksitin",font=font(28,"black"),fill=NAVY)
    d.text((16,162),"ne kadar?",font=font(26,"black"),fill=BLUE)
    result_card(d,16,230,128,92,sub="ÖRNEK",chip=str(EX_TERM)+" ay")
    d.text((16,432),"Saniyede",font=font(22,"black"),fill=WHITE)
    d.text((16,458),"hesapla",font=font(22,"black"),fill=WHITE)
    f=font(17,"black"); t="Hesapla"; tw=d.textlength(t,font=f)
    d.rounded_rectangle([16,520,144,520+int(17*2.2)],radius=12,fill=WHITE)
    d.text((16+(128-tw)//2,520+int(17*0.55)),t,font=f,fill=BLUE)
    save(img,"skyscraper_160x600")

    # 320x100
    img=light_bg(320,100,108); d=ImageDraw.Draw(img)
    wordmark(d,14,18,23)
    d.text((14,52),"Taksitini saniyede hesapla",font=font(14,"bold"),fill=INK)
    d.text((222,16),"ÖRNEK",font=font(8,"bold"),fill=WHITE)
    d.text((220,28),AMOUNT_STR,font=font(20,"black"),fill=WHITE)
    f=font(12,"black"); t="Hesapla"; tw=d.textlength(t,font=f)
    d.rounded_rectangle([228,62,308,62+int(12*2.2)],radius=9,fill=WHITE)
    d.text((228+(80-tw)//2,62+int(12*0.5)),t,font=f,fill=BLUE)
    save(img,"mobile_320x100")

    # LOGO kare 1200x1200
    base=Image.new("RGB",(1200,1200),BG); d=ImageDraw.Draw(base)
    mask=Image.new("L",(420,420),0); md=ImageDraw.Draw(mask); md.rounded_rectangle([0,0,420,420],radius=92,fill=255)
    base.paste(grad(420,420,BLUE,GREEN),(390,300),mask); d=ImageDraw.Draw(base)
    cx,cy=390,300;sw=32;cr=50
    d.ellipse([cx+126-cr,cy+126-cr,cx+126+cr,cy+126+cr],outline=WHITE,width=sw)
    d.ellipse([cx+294-cr,cy+294-cr,cx+294+cr,cy+294+cr],outline=WHITE,width=sw)
    d.line([cx+316,cy+104,cx+104,cy+316],fill=WHITE,width=sw)
    f=font(110,"black"); t="kredioran.com"; tw=d.textlength(t,font=f); wordmark(d,(1200-tw)//2,800,110)
    save(base,"logo_square_1200x1200")

    # LOGO yatay 1200x300
    img=light_bg(1200,300,0); d=ImageDraw.Draw(img)
    mask=Image.new("L",(150,150),0); md=ImageDraw.Draw(mask); md.rounded_rectangle([0,0,150,150],radius=33,fill=255)
    img.paste(grad(150,150,BLUE,GREEN),(420,75),mask); d=ImageDraw.Draw(img)
    cx,cy=420,75;sw=11;cr=18
    d.ellipse([cx+45-cr,cy+45-cr,cx+45+cr,cy+45+cr],outline=WHITE,width=sw)
    d.ellipse([cx+105-cr,cy+105-cr,cx+105+cr,cy+105+cr],outline=WHITE,width=sw)
    d.line([cx+113,cy+37,cx+37,cy+113],fill=WHITE,width=sw)
    wordmark(d,600,118,72)
    save(img,"logo_landscape_1200x300")

    print("Banner'lar ads-output/ klasörüne üretildi.")

if __name__=="__main__":
    build()
