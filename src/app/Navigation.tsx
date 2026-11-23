import {Link,useLocation} from 'react-router-dom';
import type {User} from '../domain/api-models';

type IconName = 'home' | 'tasks' | 'clubs' | 'profile' | 'stats' | 'feedback' | 'password';
const paths:Record<IconName,string> = {
  home:'m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  tasks:'M9 5H5v16h14V5h-4M9 3h6v4H9ZM8 12l2 2 5-4M8 18h8',
  clubs:'M12 12C5 12 3 8 5 5s7-2 7 7Zm0 0c0-7 4-9 7-7s2 7-7 7Zm0 0c7 0 9 4 7 7s-7 2-7-7Zm0 0c0 7-4 9-7 7s-2-7 7-7Z',
  profile:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  stats:'M4 21V11h4v10m2 0V3h4v18m2 0V7h4v14M2 21h20',
  feedback:'M21 11a8 8 0 0 1-8 8H8l-5 3V11a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8ZM7 9h10M7 13h7',
  password:'M6 10V7a6 6 0 0 1 12 0v3M4 10h16v12H4Zm8 5v3',
};
const parentItems = [
  {to:'/home',label:'Главная',icon:'home'},
  
  {to:'/programs',label:'Кружки',icon:'clubs'},
  {to:'/tests',label:'Тесты',icon:'tasks'},
  {to:'/analytics',label:'Аналитика',icon:'stats'},
  {to:'/profile',label:'Профиль',icon:'profile'},
] as const;
const adminItems = [
  {to:'/admin',label:'Статистика',icon:'stats',end:true},
  {to:'/admin/clubs',label:'Кружки',accessible:'Кружки и правила',icon:'clubs'},
  {to:'/admin/feedback',label:'Отзывы',accessible:'Обратная связь',icon:'feedback'},
  {to:'/account/password',label:'Пароль',accessible:'Сменить пароль',icon:'password'},
] as const;
const partnerItems=[{to:'/partner',label:'Организация',icon:'home',end:true},{to:'/partner/programs',label:'Программы',icon:'clubs'},{to:'/partner/bookings',label:'Заявки',icon:'tasks'},{to:'/notifications',label:'Уведомления',icon:'feedback'}] as const;

export function Navigation({role,age}:{role:User['role'];age?:number}){
  const{pathname}=useLocation();
  const items = role==='admin' ? adminItems : role==='partner'?partnerItems:parentItems;
  const active=(to:string)=>to==='/admin'?pathname==='/admin'||pathname.startsWith('/admin/completions')||pathname==='/admin/club-transitions'||pathname.startsWith('/admin/platform'):to==='/partner'?pathname===to:pathname===to||pathname.startsWith(to+'/')||(role==='parent'&&to==='/profile'&&pathname==='/account/password');
  const theme=role!=='parent'||age===undefined?'minimal':age<8?'playful':age<11?'colorful':age<15?'soft':'minimal';
  return <nav className="navigation app-navigation" data-icon-theme={theme} aria-label="Основная навигация">
    {items.map(item=><Link key={item.to} to={item.to} className={active(item.to)?'active':undefined} aria-current={active(item.to)?'page':undefined} aria-label={'accessible' in item?item.accessible:item.label}>
      <span className="nav-icon" aria-hidden="true"><NavigationIcon name={item.icon} theme={theme}/></span>
      <span className="nav-label">{item.label}</span>
    </Link>)}
  </nav>;
}

type Theme='playful'|'colorful'|'soft'|'minimal';
function NavigationIcon({name,theme}:{name:IconName;theme:Theme}){
  if(theme==='minimal')return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]}/><path d={name==='home'?'m3 10 9-7 9 7':name==='tasks'?'m8 12 2 2 5-4':name==='stats'?'M10 21V3h4':name==='profile'?'M8 7a4 4 0 0 1 8 0':'M12 6v12'} stroke="#9b7fb1"/></svg>;
  if(theme==='soft')return <svg viewBox="0 0 24 24" fill="none" stroke="#71618f" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]} fill={name==='home'||name==='profile'?'#eee5f8':name==='clubs'?'#f8dfb8':name==='stats'?'#dfe8fa':'#e4ecdf'}/></svg>;
  const vivid=theme==='playful';
  const coral=vivid?'#f78161':'#eaa190',blue=vivid?'#609cde':'#94b0d9',yellow=vivid?'#f8c849':'#efd394',green=vivid?'#61b99a':'#9bc6b2',purple=vivid?'#a47ad4':'#b3a1ce';
  return <svg viewBox="0 0 32 32" fill="none" stroke="#65547c" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
    {name==='home'?<><path d="M6 15h20v13H6Z" fill={yellow}/><path d="m3 15 13-12 13 12Z" fill={coral}/><path d="M13 20h6v8h-6Z" fill={blue}/><path d="M8 18h3v4H8Zm13 0h3v4h-3Z" fill="#fff9e9"/></>:
     name==='clubs'?<><path d="M15 15C2 18 1 5 8 4c5-1 8 4 7 11Z" fill={coral}/><path d="M17 15C15 2 28 1 29 8c1 5-4 8-12 7Z" fill={yellow}/><path d="M17 17c13-2 14 11 7 12-5 1-8-4-7-12Z" fill={blue}/><path d="M15 17C17 30 4 31 3 24c-1-5 4-8 12-7Z" fill={green}/><circle cx="16" cy="16" r="3" fill={purple}/></>:
     name==='tasks'?<><path d="M7 5h19v24H7Z" fill={blue}/><path d="M4 3h19v24H4Z" fill="#fff8e8"/><path d="M8 3h11v4H8Z" fill={purple}/><path d="m8 14 3 3 7-7" stroke={green} strokeWidth="3"/><path d="M8 22h10" stroke={coral} strokeWidth="2.5"/></>:
     name==='stats'?<><path d="M5 18h6v11H5Z" fill={green}/><path d="M13 10h6v19h-6Z" fill={yellow}/><path d="M21 4h6v25h-6Z" fill={purple}/><path d="M3 29h26"/></>:
     name==='profile'?<><path d="M5 29v-3a11 11 0 0 1 22 0v3" fill={purple}/><circle cx="16" cy="10" r="7" fill="#ffd39e"/><path d="M9 9c0-10 14-10 14 0-5 0-7-2-8-4-1 3-4 4-6 4Z" fill={coral}/><path d="M13 12h.1m5.8 0h.1M14 15q2 2 4 0"/></>:
     <path d={paths[name]} transform="scale(1.25)"/>}
    {vivid&&<path d="m28 1 .7 2.3L31 4l-2.3.7L28 7l-.7-2.3L25 4l2.3-.7Z" fill={yellow} stroke="none"/>}
  </svg>;
}

