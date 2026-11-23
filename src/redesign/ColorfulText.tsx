const glyphs:Record<string,{color:string;shape:string}>={
  '▲':{color:'#ff8b52',shape:'M16 3 30 28H2Z'},'■':{color:'#6787df',shape:'M3 3h26v26H3Z'},
  '●':{color:'#ef6a91',shape:'M16 2a14 14 0 1 0 0 28 14 14 0 0 0 0-28'},
  '⬡':{color:'#9e6bcb',shape:'M9 3h14l8 13-8 13H9L1 16Z'},
  '★':{color:'#f4b938',shape:'m16 2 4 9 10 1-8 7 3 11-9-6-9 6 3-11-8-7 10-1Z'},
  '☆':{color:'#f4b938',shape:'m16 2 4 9 10 1-8 7 3 11-9-6-9 6 3-11-8-7 10-1Z'},
  '✦':{color:'#6c8fe1',shape:'m16 2 4 10 10 4-10 4-4 10-4-10-10-4 10-4Z'},
  '✧':{color:'#6c8fe1',shape:'m16 2 4 10 10 4-10 4-4 10-4-10-10-4 10-4Z'}
};
export function ColorfulText({text}:{text:string}){return <>{text.split(/([▲■●⬡★☆✦✧])/u).map((s,i)=>{const g=glyphs[s];return g?<span className="colorful-symbol" key={i}><span className="sr-only">{s}</span><svg viewBox="0 0 32 32" aria-hidden="true"><path d={g.shape} fill={s==='☆'||s==='✧'?'#fffaf0':g.color} stroke={g.color} strokeWidth="2" strokeLinejoin="round"/></svg></span>:s;})}</>;}
