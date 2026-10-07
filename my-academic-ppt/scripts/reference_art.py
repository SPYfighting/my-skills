"""Original, synthetic scientific graphics for the optional layout reference library."""
from html import escape
import math

NAVY='#15344E'; BLUE='#365F85'; RED='#A63237'; TEAL='#537F78'; MUTED='#657B8B'; GRID='#CCD7DF'; PALE='#EFF4F8'; GOLD='#A47C3D'
class Page:
    def __init__(self,number,title,subtitle='',tag=''):
        self.number=number;self.title=title;self.subtitle=subtitle;self.tag=tag
        self.parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">','<rect width="1280" height="720" fill="white"/>','<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC",sans-serif}line,path,rect,circle,ellipse,polyline{vector-effect:non-scaling-stroke}</style>']
        self.rect(0,0,1280,6,BLUE)
        if title:self.text(50,63,title,34,NAVY,True)
        if subtitle:self.text(52,100,subtitle,19,MUTED)
        self.line(50,116,1230,116,GRID,1.4)
    def text(self,x,y,s,size=21,color=NAVY,bold=False,anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def lines(self,x,y,items,size=20,step=31,color=NAVY,bold=False,anchor='start'):
        for i,s in enumerate(items):self.text(x,y+i*step,s,size,color,bold,anchor)
    def rect(self,x,y,w,h,fill='none',stroke=None,sw=1,dash=None):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def line(self,x1,y1,x2,y2,color=GRID,sw=2,dash=None):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def path(self,d,fill='none',stroke=BLUE,sw=2):self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def circle(self,x,y,r,fill=BLUE,stroke=None,sw=1):self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+'/>')
    def ellipse(self,x,y,rx,ry,fill=PALE,stroke=BLUE,sw=1):self.parts.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def arrow(self,x1,y1,x2,y2,color=BLUE,width=9,head=16):
        dx=x2-x1;dy=y2-y1;l=math.hypot(dx,dy)
        if l==0:return
        head=min(head,l*.6);ux=dx/l;uy=dy/l;px=-uy;py=ux;bx=x2-head*ux;by=y2-head*uy
        pts=[(x1+px*width/2,y1+py*width/2),(bx+px*width/2,by+py*width/2),(bx+px*head*.62,by+py*head*.62),(x2,y2),(bx-px*head*.62,by-py*head*.62),(bx-px*width/2,by-py*width/2),(x1-px*width/2,y1-py*width/2)]
        self.parts.append('<polygon points="'+' '.join(f'{a:.2f},{b:.2f}' for a,b in pts)+f'" fill="{color}"/>')
    def header(self,x,y,w,label,color=BLUE,h=34):
        self.rect(x,y,w,h,color);self.text(x+w/2,y+h*.72,label,21,'white',True,'middle')
    def panel(self,x,y,w,h,label=None):
        self.rect(x,y,w,h,'white',GRID,1.4,'6 4')
        if label:self.header(x,y,w,label)
    def takeaway(self,s,y=665):
        self.text(640,y,s,27,RED,True,'middle')
    def footer(self):
        self.text(1230,704,f'{self.number:02}',15,MUTED,False,'end')
    def svg(self):return '\n'.join(self.parts+['</svg>'])
    def finish(self):self.footer();return self.svg()

def mesh(p,x,y,w,h,mode=0):
    p.rect(x,y,w,h,'#F4F6F6')
    cols=10;rows=6;dx=w/cols;dy=h/rows
    for j in range(rows+1):
        for i in range(cols+1):
            xx=x+i*dx; yy=y+j*dy
            if i<cols:p.line(xx,yy,xx+dx,yy,'#91A6AE',.8)
            if j<rows:p.line(xx,yy,xx,yy+dy,'#91A6AE',.8)
            if i<cols and j<rows:p.line(xx,yy,xx+dx,yy+dy,'#91A6AE',.65)
    for j in range(2,rows,2):
        for i in range(1,cols,2):
            r=(min(dx,dy)*.54)*(1+.14*math.sin(i+j+mode));p.ellipse(x+i*dx,y+j*dy,r,r*.8,'white',BLUE,1.5)
    p.path(f'M{x+8},{y+h*.48} C{x+w*.3},{y+h*.2} {x+w*.65},{y+h*.85} {x+w-8},{y+h*.45}',stroke=RED,sw=3)

def layers(p,x,y,w,h):
    for i,c in enumerate(['#DCE6EB','#8DAAB9','#C5D5DC','#476F8A']):
        yy=y+i*h*.19;p.path(f'M{x},{yy+15} L{x+w*.78},{yy} L{x+w},{yy+24} L{x+w*.22},{yy+39} Z',c,'white',1)
    for j in range(6):p.arrow(x+w*.15+j*w*.12,y+h*.83,x+w*.15+j*w*.12,y+h*.98,RED,3,8)

def heatmap(p,x,y,w,h,rows=8,cols=14):
    colors=['#456B8F','#7694AF','#ADC0D0','#DFE6EB','#F2EBE4','#D9B19A','#B96356','#934141']
    cw=w/cols;ch=h/rows
    for j in range(rows):
        for i in range(cols):
            value=(math.sin(i*.72+j*.31)+math.cos(j*.65-i*.15)+2)/4
            k=min(7,int(value*8));p.rect(x+i*cw,y+j*ch,cw-1,ch-1,colors[k])
    for i in [0,cols//2,cols-1]:p.text(x+(i+.5)*cw,y+h+19,str(i+1),13,MUTED,False,'middle')
    for j in [0,rows-1]:p.text(x-7,y+(j+.67)*ch,str(j+1),13,MUTED,False,'end')

def curve(p,x,y,w,h,kind='decay',labels=True):
    legend_y=y+11
    if labels:
        p.text(x,y-10,'相对响应',14,MUTED)
        y+=24;h-=24
    p.line(x,y+h,x+w,y+h,MUTED,1.3);p.line(x,y,x,y+h,MUTED,1.3)
    for j in range(1,4):p.line(x,y+h*j/4,x+w,y+h*j/4,GRID,.7)
    for k,c in enumerate([BLUE,RED,TEAL]):
        pts=[]
        for i in range(31):
            t=i/30
            if kind=='decay':v=.18+.65*math.exp(-(1+k*.5)*t*2)
            elif kind=='peak':v=.13+.65*math.exp(-((t-(.38+k*.1))/.2)**2)
            elif kind=='increase':v=.12+(.5+k*.11)*(1-math.exp(-t*4))
            else:v=.15+(.5+k*.08)*t+.055*math.sin(t*15+k)
            pts.append((x+t*w,y+(1-v)*h))
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a,b in pts),stroke=c,sw=2.6)
        for i in range(0,31,6):p.circle(*pts[i],2.8,c)
    if labels:
        p.text(x+w/2,y+h+25,'归一化条件',14,MUTED,False,'middle')
        for k,c in enumerate([BLUE,RED,TEAL]):
            xx=x+6+k*w/3;p.line(xx,legend_y-4,xx+18,legend_y-4,c,3);p.text(xx+24,legend_y,chr(65+k),13,MUTED)

def scatter(p,x,y,w,h):
    p.line(x,y+h,x+w,y+h,MUTED,1.2);p.line(x,y,x,y+h,MUTED,1.2);p.line(x,y+h,x+w,y,GRID,1.3,'5 4')
    for i in range(45):
        a=(i*.6180339887)%1;b=max(.03,min(.97,a+.11*math.sin(i*1.77)))
        p.circle(x+a*w,y+(1-b)*h,3.2,BLUE if i%4 else RED)
    p.text(x+w/2,y+h+23,'测量值',14,MUTED,False,'middle');p.text(x,y-10,'预测值',14,MUTED)

def bars(p,x,y,w,h):
    p.line(x,y+h,x+w,y+h,MUTED,1.2);p.line(x,y,x,y+h,MUTED,1.2)
    vals=[.38,.71,.62,.85];cw=w/4
    for i,v in enumerate(vals):
        p.rect(x+cw*(i+.21),y+h*(1-v),cw*.5,h*v,[BLUE,TEAL,GOLD,RED][i]);xx=x+cw*(i+.46);yy=y+h*(1-v)
        p.line(xx,yy-8,xx,yy+8,NAVY,1.4);p.line(xx-6,yy-8,xx+6,yy-8,NAVY,1.4);p.text(x+cw*(i+.46),y+h+22,chr(65+i),14,MUTED,False,'middle')
    p.text(x,y-10,'相对指标',14,MUTED)

def spectrum(p,x,y,w,h):
    p.line(x,y+h,x+w,y+h,MUTED,1.3)
    for k,c in enumerate([BLUE,RED,TEAL]):
        pts=[]
        for i in range(151):
            t=i/150;v=.12+k*.16
            for mu,amp,sig in [(.2,.25,.014),(.45,.37,.023),(.71,.21,.01),(.87,.15,.018)]:v+=amp*math.exp(-((t-mu-k*.008)/sig)**2)
            pts.append((x+t*w,y+h*(1-v)))
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a,b in pts),stroke=c,sw=2)
    p.text(x+w/2,y+h+20,'频率 / 归一化坐标',14,MUTED,False,'middle')

def micrograph(p,x,y,w,h):
    p.rect(x,y,w,h,'#202C33')
    for i in range(38):
        a=(i*.61803399)%1;b=(i*.41421356)%1;rr=3+(i%5)*1.6
        p.ellipse(x+12+a*(w-24),y+10+b*(h-20),rr*1.5,rr,'#7EAC9C','#A0C8B7',.6)
    p.line(x+w-66,y+h-17,x+w-16,y+h-17,'white',3);p.text(x+8,y+18,'形貌示意',12,'white')

def network(p,x,y,w,h):
    nodes=[]
    for i in range(18):
        g=i//6;ang=i*2.4;cx=x+w*(.22+.29*g);cy=y+h*(.43+(.15 if g==1 else 0));nodes.append((cx+math.cos(ang)*w*.13,cy+math.sin(ang)*h*.28))
    for i,(a,b) in enumerate(nodes):
        for j in [i+1,i+3]:
            if j<len(nodes):p.line(a,b,*nodes[j],GRID,1)
    for i,(a,b) in enumerate(nodes):p.circle(a,b,5.5,[BLUE,TEAL,RED][i//6])

def plate(p,x,y,w,h):
    p.rect(x,y,w,h,PALE,GRID,1.5)
    for j in range(8):
        for i in range(12):
            v=(math.sin(i*.8+j*.6)+1)/2;c=['#C6D8DF','#96B8C5','#6590A6','#416983'][min(3,int(v*4))]
            p.circle(x+(i+1)*w/13,y+(j+1)*h/9,min(w/28,h/22),c)

def apparatus(p,x,y,w,h,kind=0):
    if kind==0:
        p.rect(x+w*.15,y+h*.1,w*.7,h*.78,'#E2E9ED',MUTED,1.4);p.rect(x+w*.23,y+h*.2,w*.45,h*.18,BLUE);p.lines(x+w*.45,y+h*.3,['28.0'],18,24,'white',True,'middle');p.rect(x+w*.23,y+h*.46,w*.48,h*.27,'white',GRID);p.line(x+w*.3,y+h*.77,x+w*.62,y+h*.77,MUTED,5)
    elif kind==1:
        p.rect(x+w*.12,y+h*.82,w*.74,h*.08,BLUE);p.path(f'M{x+w*.68},{y+h*.82} C{x+w*.8},{y+h*.39} {x+w*.6},{y+h*.16} {x+w*.34},{y+h*.31}',stroke=BLUE,sw=13);p.path(f'M{x+w*.35},{y+h*.22} L{x+w*.5},{y+h*.36} L{x+w*.39},{y+h*.49} L{x+w*.24},{y+h*.35} Z','#9BB0BD',BLUE,2);p.line(x+w*.24,y+h*.6,x+w*.65,y+h*.6,BLUE,7);p.rect(x+w*.32,y+h*.56,w*.16,h*.025,RED)
    else:
        p.rect(x+w*.13,y+h*.14,w*.73,h*.63,'#E9EFF2',MUTED,1.6);p.rect(x+w*.22,y+h*.23,w*.43,h*.34,'white',BLUE,2);curve(p,x+w*.27,y+h*.29,w*.33,h*.21,labels=False);p.circle(x+w*.74,y+h*.39,w*.04,TEAL);p.line(x+w*.22,y+h*.85,x+w*.75,y+h*.85,BLUE,8)

def molecules(p,x,y,w,h):
    for k,c in enumerate([BLUE,TEAL]):
        pts=[]
        for i in range(100):
            t=i/99*math.pi*5;xx=x+w*(.12+.76*i/99);yy=y+h*(.5+.25*math.sin(t+k*1.5)*math.cos(t*.32));pts.append((xx,yy))
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a,b in pts),stroke=c,sw=5)
    for i in range(7):p.circle(x+w*(.2+i*.1),y+h*(.5+.12*math.sin(i)),3,RED)

def figure(p,kind,x,y,w,h):
    funcs={'mesh':mesh,'layers':layers,'heatmap':heatmap,'curve':curve,'scatter':scatter,'bars':bars,'spectrum':spectrum,'micrograph':micrograph,'network':network,'plate':plate,'apparatus':apparatus,'molecules':molecules}
    funcs[kind](p,x,y,w,h)

def module(p,x,y,w,h,title,kind,body,conclusion=''):
    p.panel(x,y,w,h,title);figure(p,kind,x+24,y+57,w-48,h*.34);p.lines(x+20,y+h*.64,body,19,28)
    if conclusion:p.text(x+w/2,y+h-20,conclusion,20,RED,True,'middle')

def bracket(p,x1,x2,y):
    mid=(x1+x2)/2;p.path(f'M{x1},{y} V{y+14} H{mid-12} L{mid},{y+27} L{mid+12},{y+14} H{x2} V{y}',stroke=BLUE,sw=5)
