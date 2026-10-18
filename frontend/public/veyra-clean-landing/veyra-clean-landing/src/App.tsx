import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, Network, Search, Globe2, Link2, FileText, ShieldAlert, Menu, X } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';

function NetworkGlobe({ mouse }: { mouse: {x:number;y:number} }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef(mouse);
  useEffect(()=>{mouseRef.current=mouse},[mouse]);
  useEffect(()=>{
    const canvas=canvasRef.current;if(!canvas)return;const ctx=canvas.getContext('2d');if(!ctx)return;
    let w=0,h=0,raf=0,t=0,dpr=1;
    const resize=()=>{const r=canvas.getBoundingClientRect();w=r.width;h=r.height;dpr=Math.min(devicePixelRatio||1,1.6);canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0)};
    const points:{x:number;y:number;z:number;r:number;phase:number}[]=[];
    // Sphere made from latitude/longitude points, with a dotted globe and sparse graph links.
    for(let lat=-1.32;lat<=1.33;lat+=.16){const count=Math.max(7,Math.round(29*Math.cos(lat)));for(let j=0;j<count;j++){const lon=j/count*Math.PI*2;points.push({x:Math.cos(lat)*Math.cos(lon),y:Math.sin(lat),z:Math.cos(lat)*Math.sin(lon),r:.65+Math.random()*.65,phase:Math.random()*6.28})}}
    const draw=()=>{t+=.0035;ctx.clearRect(0,0,w,h);const m=mouseRef.current;const cx=w*.52+m.x*12,cy=h*.49+m.y*9,rad=Math.min(w,h)*.39,rot=t+m.x*.14;
      const projected=points.map(p=>{const x=p.x*Math.cos(rot)-p.z*Math.sin(rot),z=p.x*Math.sin(rot)+p.z*Math.cos(rot);return {x:cx+x*rad,y:cy+(p.y*.91+z*.12)*rad,z,r:p.r,phase:p.phase}});
      // Thin longitude and latitude curves are approximated by short links.
      projected.forEach((p,i)=>{for(let j=i+1;j<Math.min(i+4,projected.length);j++){const q=projected[j];const d=Math.hypot(p.x-q.x,p.y-q.y);if(d<rad*.13 && (i+j)%3===0){const alpha=(.06+Math.max(0,p.z)*.09);ctx.strokeStyle=`rgba(116,202,245,${alpha})`;ctx.lineWidth=.55;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke()}}});
      const glow=ctx.createRadialGradient(cx,cy,rad*.25,cx,cy,rad*1.08);glow.addColorStop(0,'rgba(17,70,100,.10)');glow.addColorStop(.78,'rgba(16,63,92,.04)');glow.addColorStop(1,'rgba(9,20,29,0)');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(cx,cy,rad*1.08,0,Math.PI*2);ctx.fill();
      projected.forEach((p,i)=>{const alpha=.28+Math.max(0,p.z)*.65;ctx.fillStyle=`rgba(205,236,250,${alpha})`;ctx.beginPath();ctx.arc(p.x,p.y,p.r+(p.z>.65?0.6:0),0,Math.PI*2);ctx.fill();if(p.z>.84&&(i%9===0)){ctx.fillStyle='rgba(104,202,255,.14)';ctx.beginPath();ctx.arc(p.x,p.y,5,0,Math.PI*2);ctx.fill()}});
      // Three highlighted investigation paths, kept restrained.
      const hot=[Math.floor(projected.length*.19),Math.floor(projected.length*.47),Math.floor(projected.length*.73)];
      hot.forEach((idx,k)=>{const p=projected[idx];if(!p)return;ctx.strokeStyle=k===1?'rgba(126,213,255,.8)':'rgba(126,213,255,.5)';ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,4.5+Math.sin(t*2+k)*1.4,0,Math.PI*2);ctx.stroke();ctx.fillStyle='rgba(140,220,255,.85)';ctx.beginPath();ctx.arc(p.x,p.y,1.5,0,Math.PI*2);ctx.fill()});
      raf=requestAnimationFrame(draw)};
    resize();draw();const obs=new ResizeObserver(resize);obs.observe(canvas);return()=>{cancelAnimationFrame(raf);obs.disconnect()};
  },[]);
  return <canvas ref={canvasRef} className="globe-canvas" aria-label="Animated connected evidence globe"/>;
}
function App(){
 const [mouse,setMouse]=useState({x:0,y:0});const [menu,setMenu]=useState(false);const [showEntry,setShowEntry]=useState(false);const reduce=useReducedMotion();
 useEffect(()=>{const fn=(e:MouseEvent)=>setMouse({x:(e.clientX/innerWidth-.5)*2,y:(e.clientY/innerHeight-.5)*2});window.addEventListener('mousemove',fn,{passive:true});return()=>window.removeEventListener('mousemove',fn)},[]);
 const start=()=>{setShowEntry(true);document.getElementById('investigate')?.scrollIntoView({behavior:reduce?'auto':'smooth'})};
 return <main className="page">
  <header className="header">
   <a href="#home" className="logo">VEYRA<span>·</span></a>
   <div className="brand-line"><Network size={15}/><span>Powered by <b>FalkorDB</b></span></div>
   <nav className={menu?'nav open':'nav'}><a href="#about" onClick={()=>setMenu(false)}>About</a><button className="nav-button" onClick={start}>Start Investigation <ArrowUpRight size={15}/></button></nav>
   <button className="mobile-menu" onClick={()=>setMenu(!menu)} aria-label="Toggle menu">{menu?<X/>:<Menu/>}</button>
  </header>
  <section className="hero" id="home">
   <div className="hero-copy">
    <motion.div className="kicker" initial={reduce?false:{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:.6}}>DIGITAL INVESTIGATION PLATFORM</motion.div>
    <motion.h1 initial={reduce?false:{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{duration:.8,delay:.08}}>See what<br/><em>connects.</em></motion.h1>
    <motion.p initial={reduce?false:{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:.6,delay:.2}}>Investigate suspicious digital activity.<br/>Follow the evidence. Reveal the hidden connections.</motion.p>
    <motion.div className="actions" initial={reduce?false:{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:.6,delay:.3}}>
     <button className="primary" onClick={start}>Start Investigation <ArrowRight size={16}/></button><a className="secondary" href="#about"><span className="play">↓</span> Discover Veyra</a>
    </motion.div>
    <div className="micro-note"><span/> CONNECTED DATA. CLEARER CONTEXT.</div>
   </div>
   <div className="visual" style={{transform:`translate(${mouse.x*(reduce?0:-4)}px,${mouse.y*(reduce?0:-3)}px)`}}>
    <div className="globe-wrap"><NetworkGlobe mouse={mouse}/></div>
    <motion.div className="detective" style={{transform:`translate(${mouse.x*(reduce?0:7)}px,${mouse.y*(reduce?0:5)}px)`}} animate={reduce?{}:{y:[0,-5,0]}} transition={{duration:6,repeat:Infinity,ease:'easeInOut'}}><img src="/detective-concept.png" alt="Detective silhouette in a connected digital evidence scene"/></motion.div>
    <div className="entity entity-a"><span className="entity-icon"><Search size={15}/></span><span><small>ENTITY / 001</small><b>Account cluster</b><i>Connected identities</i></span></div>
    <div className="entity entity-b"><span className="entity-icon"><Globe2 size={15}/></span><span><small>INFRASTRUCTURE</small><b>Domain connection</b><i>Shared destination</i></span></div>
    <div className="entity entity-c"><span className="entity-icon"><ShieldAlert size={15}/></span><span><small>INVESTIGATION SIGNAL</small><b>Needs review</b><i>Evidence required</i></span></div>
    <div className="entity entity-d"><span className="entity-icon"><Link2 size={15}/></span><span><small>URL / REDIRECT</small><b>Link relationship</b><i>Trace the path</i></span></div>
    <div className="visual-caption">FIG. 01 <span>CONNECTED EVIDENCE MODEL</span></div>
   </div>
   <a href="#about" className="scroll-cue">SCROLL TO EXPLORE <span>↓</span></a>
  </section>
  <section className="about" id="about">
   <div className="about-block"><div className="section-index">01 / ABOUT VEYRA</div><h2>Every connection<br/>tells <em>a story.</em></h2><p>Veyra helps investigators explore relationships across digital identities, websites, and reported activity. Follow connected evidence to understand the bigger picture.</p><div className="steps"><div><small>01</small><span>Search</span></div><div><small>02</small><span>Connect</span></div><div><small>03</small><span>Investigate</span></div><div><small>04</small><span>Understand</span></div></div></div>
   <div className="graph-art"><div className="graph-orbit go1"/><div className="graph-orbit go2"/><div className="graph-orbit go3"/><div className="graph-core"><Network size={25}/></div><div className="graph-point gp1"><Search/></div><div className="graph-point gp2"><Globe2/></div><div className="graph-point gp3"><FileText/></div><div className="graph-point gp4"><Link2/></div><div className="graph-point gp5"><ShieldAlert/></div><span className="graph-label gl1">ACCOUNT</span><span className="graph-label gl2">DOMAIN</span><span className="graph-label gl3">REPORT</span></div>
   <div className="about-block falkor"><div className="section-index">02 / CONNECTED INTELLIGENCE</div><h2>Powered by<br/><em>relationships.</em></h2><p>FalkorDB is a graph database built for connected data. Veyra uses graph relationships to trace paths between entities and support evidence-based investigation.</p><a className="learn" href="https://www.falkordb.com/" target="_blank" rel="noreferrer">Discover FalkorDB <ArrowUpRight size={14}/></a><div className="falkor-brand"><Network size={25}/><div><b>FalkorDB</b><small>The graph layer behind connected data.</small></div></div></div>
  </section>
  <section className="closing" id="investigate"><div className="closing-line"/><div className="section-index">TAKE THE NEXT STEP</div><h2>Ready to follow<br/><em>the evidence?</em></h2><p>Start with a signal. Discover the connections around it.</p><button className="primary" onClick={()=>setShowEntry(true)}>Start Investigation <ArrowRight size={16}/></button><small className="closing-note">{showEntry?'INVESTIGATION ENTRY READY — CONNECT YOUR BACKEND NEXT':'A CLEARER VIEW STARTS WITH A CONNECTION'}</small></section>
  <footer><a href="#home" className="logo">VEYRA<span>·</span></a><span>CONNECTED DATA. EVIDENCE-LED INVESTIGATION.</span><span>GRAPH LAYER · FALKORDB</span></footer>
 </main>
}
export default App;
