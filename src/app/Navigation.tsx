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
  {to:'/tests',label:'Задания',icon:'tasks'},
  {to:'/programs',label:'Кружки',icon:'clubs'},
  {to:'/profile',label:'Профиль',icon:'profile'},
] as const;
const adminItems = [
  {to:'/admin',label:'Статистика',icon:'stats',end:true},
  {to:'/admin/clubs',label:'Кружки',accessible:'Кружки и правила',icon:'clubs'},
  {to:'/admin/feedback',label:'Отзывы',accessible:'Обратная связь',icon:'feedback'},
  {to:'/account/password',label:'Пароль',accessible:'Сменить пароль',icon:'password'},
] as const;
const partnerItems=[{to:'/partner',label:'Организация',icon:'home',end:true},{to:'/partner/programs',label:'Программы',icon:'clubs'},{to:'/partner/bookings',label:'Заявки',icon:'tasks'},{to:'/notifications',label:'Уведомления',icon:'feedback'}] as const;

export function Navigation({role}:{role:User['role']}){
  const{pathname}=useLocation();
  const items = role==='admin' ? adminItems : role==='partner'?partnerItems:parentItems;
  const active=(to:string)=>to==='/admin'?pathname==='/admin'||pathname.startsWith('/admin/completions')||pathname==='/admin/club-transitions'||pathname.startsWith('/admin/platform'):to==='/partner'?pathname===to:pathname===to||pathname.startsWith(to+'/')||(role==='parent'&&to==='/profile'&&pathname==='/account/password');
  return <nav className="navigation app-navigation" aria-label="Основная навигация">
    {items.map(item=><Link key={item.to} to={item.to} className={active(item.to)?'active':undefined} aria-current={active(item.to)?'page':undefined} aria-label={'accessible' in item?item.accessible:item.label}>
      <span className="nav-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={paths[item.icon]}/></svg></span>
      <span className="nav-label">{item.label}</span>
    </Link>)}
  </nav>;
}
