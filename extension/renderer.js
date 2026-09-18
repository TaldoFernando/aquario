(function (root) {
  class Aquarium {
    constructor(canvas, assetURL = p => p) {
      this.canvas=canvas; this.ctx=canvas.getContext('2d'); this.assetURL=assetURL;
      this.items=[]; this.geo=null; this.clock=null; this.realScale=false; this.paused=false; this.disposed=false; this.last=0; this.frame=0;
      this.reduced=typeof matchMedia==='function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
      this.tick=this.tick.bind(this); this.frame=requestAnimationFrame(this.tick);
    }
    set(items, geo) {
      this.geo=geo; this.items=items.filter(i=>i.sprite).map((item,n)=>{
        const image=new Image(); image.src=this.assetURL(item.sprite);
        return {...item,image,x:.15+(n*.23)%.65,y:.3+(n*.19)%.4,direction:n%2 ? -1:1,phase:n*2};
      });
    }
    destroy() {this.disposed=true;cancelAnimationFrame(this.frame);}
    tick(now) {
      if(this.disposed)return;
      this.frame=requestAnimationFrame(this.tick);
      if(now-this.last<1000/30)return;
      const dt=Math.min((now-this.last)/1000,.08); this.last=now;
      if(document.hidden)return;
      const c=this.ctx,w=this.canvas.width,h=this.canvas.height;
      const when=new Date(); if(this.clock){const[hh,mm]=this.clock.split(':').map(Number);if(Number.isFinite(hh))when.setHours(hh,mm||0,0,0);}
      const {light}=root.AquarioSolar.phase(when,this.geo);
      c.imageSmoothingEnabled=false;
      const sky=c.createLinearGradient(0,0,0,h);sky.addColorStop(0,`rgb(${Math.round(12+18*light)},${Math.round(27+64*light)},${Math.round(43+67*light)})`);sky.addColorStop(1,'#102b34');c.fillStyle=sky;c.fillRect(0,0,w,h);
      c.fillStyle=`rgba(174,225,202,${.018+light*.04})`;
      for(let n=0;n<5;n++){c.beginPath();c.moveTo(n*110-70,0);c.lineTo(n*110+14,0);c.lineTo(n*110+150,h);c.lineTo(n*110+95,h);c.fill();}
      c.fillStyle='#253e3b';c.fillRect(0,h-38,w,38);c.fillStyle='#66765d';c.fillRect(0,h-38,w,3);
      for(let n=0;n<70;n++){c.fillStyle=n%2?'#455b49':'#79836a';c.fillRect((n*73)%w,h-31+(n*17)%27,3,2);}
      const ordered=[...this.items].sort((a,b)=>(a.kind==='plant'?0:1)-(b.kind==='plant'?0:1));
      const plants=ordered.filter(a=>a.kind==='plant');
      for (const a of ordered) {
        const plant=a.kind==='plant'||a.kind==='decoration', shrimp=a.kind==='shrimp';
        if(!plant && !this.paused && !this.reduced){a.x+=dt*(shrimp?.009:.025)*(.2+.8*light)*a.direction;if(a.x>.9){a.x=.9;a.direction=-1;}if(a.x<.1){a.x=.1;a.direction=1;}}
        const fictional=plant?136:shrimp?80:104;
        const cm=a.facts&&a.facts.size_cm;
        const size=(this.realScale&&cm)?Math.max(8,Math.min(this.canvas.height*.9,cm*(this.canvas.width/56))):fictional;
        const bob=this.paused||this.reduced?0:Math.sin(now/1400+a.phase)*(plant?0:3);
        let x,y;
        if(plant){
          const q=Math.max(0,plants.indexOf(a))%5;
          x=((q+.5)/5)*w;
          y=(h-12)-size/2;
        }else{
          x=a.x*w;y=shrimp?h-64:a.y*(h-60)+bob;
        }
        c.save();c.translate(Math.round(x),Math.round(y));c.scale(plant?1:a.direction,1);
        if(a.image.complete && a.image.naturalWidth)c.drawImage(a.image,-size/2,-size/2,size,size);
        c.restore();
      }
      c.fillStyle=`rgba(5,12,35,${(1-light)*.45})`;c.fillRect(0,0,w,h);
      c.strokeStyle=`rgba(207,244,227,${light*.12+.03})`;c.lineWidth=1;
      if(!this.reduced)for(let n=0;n<8;n++){const y=this.paused ? n*27 : h-((now/60+n*47)%(h+20));c.strokeRect((n*83+31)%w,y,3,4);}
    }
  }
  root.AquarioRenderer=Aquarium;
})(globalThis);
