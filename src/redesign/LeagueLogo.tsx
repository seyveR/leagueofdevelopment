export function LeagueLogo({age}:{age?:number}){
  const color=!age?'#655397':age<8?'#42846c':age<11?'#347db4':age<15?'#8855ac':'#c18a2e';
  return <svg className="league-logo" viewBox="0 0 48 54" aria-label="Логотип Лиги развития" role="img"><path d="M24 2 45 9v21c0 11-12 18-21 22C15 48 3 41 3 30V9Z" fill={color}/><path d="m24 8 2 5 6 .4-4.5 3.6 1.5 5.5-5-3-5 3 1.5-5.5L16 13.4l6-.4Z" fill="#ffe49a"/><path d="M24 28c-4-4-10-4-15-3v15c6-1 11 0 15 4 4-4 9-5 15-4V25c-5-1-11-1-15 3Z" fill="#fffaf0"/><path d="M24 28v16M12 29c4 0 7 1 9 3m6 0c2-2 5-3 9-3" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round"/></svg>;
}
