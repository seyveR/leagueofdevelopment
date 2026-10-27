import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useLocation,Link} from 'react-router-dom';
import {request,onSessionEnded} from '../data/api';
import {defaults,voices,type Settings,type SettingsResponse} from './settings';
import './experience.css';

type Experience={settings:Settings;apply:(s:Settings)=>void;play:(text:string,url?:string)=>Promise<void>;stop:()=>void;speaking:boolean;hint:string};
const Context=createContext<Experience>(null!);
export const useExperience=()=>useContext(Context);
export function ExperienceProvider({userId,childId,children}:{userId?:string;childId?:string;children:ReactNode}){
  const[settings,setSettings]=useState(defaults),[revision,setRevision]=useState(0),[speaking,setSpeaking]=useState(false),[hint,setHint]=useState('');
  const audio=useRef<HTMLAudioElement|null>(null),generation=useRef(0),location=useLocation();
  function stop(){generation.current++;if(audio.current){audio.current.pause();audio.current.removeAttribute('src');audio.current.load();audio.current=null;}setSpeaking(false);}
  useEffect(()=>{stop();setHint('');},[location.pathname]);
  useEffect(()=>onSessionEnded(()=>{stop();setSettings(defaults);}),[]);
  useEffect(()=>{let live=true;stop();setSettings(defaults);if(userId)void request<SettingsResponse>(`/settings${childId?'?child_id='+childId:''}`).then(value=>{if(live)setSettings(value.settings);}).catch(()=>{});return()=>{live=false;stop();};},[userId,childId,revision]);
  useEffect(()=>{stop();},[settings.speech,settings.voice]);
  useEffect(()=>{if(audio.current){audio.current.volume=settings.volume;audio.current.playbackRate=settings.rate;}},[settings.volume,settings.rate]);
  useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');const update=()=>{document.documentElement.classList.toggle('reduce-motion',settings.reduced_motion||media.matches);document.documentElement.dataset.textSize=settings.text_size;};update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[settings.reduced_motion,settings.text_size]);
  async function play(text:string,url?:string){
    stop();setHint('');const ticket=generation.current;
    if(!settings.speech&&!url){setHint('Озвучка выключена. Её можно включить в настройках.');return;}
    try{
      if(!url){const clip=await request<{url:string|null;message:string}>(`/audio/resolve?${new URLSearchParams({text,voice:settings.voice})}`);if(ticket!==generation.current)return;if(!clip.url){setHint(clip.message);return;}url=clip.url;}
      if(ticket!==generation.current)return;
      const player=new Audio(url);audio.current=player;player.volume=settings.volume;player.playbackRate=settings.rate;
      player.onplaying=()=>{if(ticket===generation.current)setSpeaking(true);};player.onpause=()=>{if(ticket===generation.current)setSpeaking(false);};player.onended=()=>{if(ticket===generation.current)setSpeaking(false);};
      player.onerror=()=>{if(ticket===generation.current){setSpeaking(false);setHint('Запись недоступна. Используйте текстовую инструкцию.');}};
      await player.play();
    }catch(e){if(ticket===generation.current){setSpeaking(false);setHint(e instanceof DOMException&&e.name==='NotAllowedError'?'Браузер остановил автозапуск. Нажмите «Озвучить инструкцию».':'Аудио недоступно. Используйте текстовую инструкцию.');}}
  }
  return <Context.Provider value={{settings,apply:(value)=>{setSettings(value);setRevision(n=>n+1);},play,stop,speaking,hint}}>{children}</Context.Provider>;
}

export function Companion({state='waiting'}:{state?:'greeting'|'explaining'|'waiting'|'completed'}){
  const{settings,speaking}=useExperience();if(!settings.character)return null;
  const voice=voices.find(v=>v.id===settings.voice)!;
  const messages={greeting:'Привет! Начнём, когда будешь готов.',explaining:'Инструкцию можно прочитать или прослушать.',waiting:'Можно не спешить.',completed:'Готово. Ответы сохранены.'};
  return <aside className={`companion ${voice.character} ${speaking?'speaking':''}`} aria-label={`Помощник ${voice.character==='lev'?'Лев':'София'}`}><div className="companion-portrait" aria-hidden="true"><img src="/characters/lev-sofia.png" alt=""/></div><div><strong>{voice.character==='lev'?'Лев':'София'}</strong><p>{speaking?'Читаю инструкцию…':messages[state]}</p><span className="speech-indicator" aria-hidden="true"><i/><i/><i/></span></div></aside>;
}
export function SpeechInstruction({text,state='waiting'}:{text:string;state?:'greeting'|'explaining'|'waiting'|'completed'}){
  const{settings,play,stop,speaking,hint}=useExperience();const playRef=useRef(play);playRef.current=play;
  useEffect(()=>{if(settings.speech&&settings.autoplay)void playRef.current(text);return()=>stop();},[text,settings.voice,settings.speech,settings.autoplay]);
  return <div className="speech-instruction"><Companion state={state}/><div className="button-row"><button type="button" className="secondary" onClick={()=>void play(text)} disabled={!settings.speech}>Озвучить инструкцию</button>{speaking&&<button type="button" className="secondary" onClick={stop}>Остановить</button>}<Link className="back" to="/settings">Настройки</Link></div>{hint&&<p role="status" className="micro">{hint}</p>}</div>;
}

export function SettingsScreen({childrenList}:{childrenList:{id:string;name:string}[]}){
  const{apply,play,stop}=useExperience();const[scope,setScope]=useState(''),[form,setForm]=useState<Settings>(),[overridden,setOverridden]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(''),[busy,setBusy]=useState(false),[samples,setSamples]=useState<{voices:{id:string;sample_url:string|null}[]} | null>(null);
  const path='/settings'+(scope?'?child_id='+scope:'');
  useEffect(()=>{let live=true;setForm(undefined);setError('');setSaved('');void request<SettingsResponse>(path).then(data=>{if(live){setForm(data.settings);setOverridden(data.overridden);}}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[scope]);
  useEffect(()=>{void request<typeof samples>('/audio/catalog').then(setSamples).catch(()=>{});return()=>stop();},[]);
  async function save(e:React.FormEvent){e.preventDefault();if(!form)return;setBusy(true);setError('');try{const result=await request<SettingsResponse>(path,'PUT',form);setForm(result.settings);setOverridden(result.overridden);apply(result.settings);setSaved('Настройки сохранены');}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  const toggle=(key:keyof Settings,label:string)=><label className="settings-toggle"><span>{label}</span><input type="checkbox" disabled={key==='autoplay'&&!form?.speech} checked={Boolean(form?.[key])} onChange={e=>{if(!e.target.checked&&key==='speech')stop();setForm({...form!,[key]:e.target.checked,...(key==='speech'&&!e.target.checked?{autoplay:false}:{})});setSaved('');}}/></label>;
  return <><h1 tabIndex={-1}>Настройки</h1><label className="settings-scope">Применять к<select value={scope} onChange={e=>{stop();setScope(e.target.value);}}><option value="">Аккаунту родителя</option>{childrenList.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>{error&&<p className="error" role="alert">{error}</p>}{!form?<p role="status">Загрузка…</p>:<form className="card form-card settings-form" onSubmit={save}>{scope&&<p className="micro">{overridden?'Для ребёнка заданы собственные настройки.':'Пока используются настройки родителя. Сохранение создаст собственные настройки ребёнка.'}</p>}<h2>Голос и помощник</h2>{toggle('speech','Озвучка заданий')}{toggle('autoplay','Автоматическое воспроизведение')}{toggle('character','Персонаж-помощник')}<label>Голос<select value={form.voice} onChange={e=>{stop();setForm({...form,voice:e.target.value as Settings['voice']});}}>{voices.map(v=><option value={v.id} key={v.id}>{v.name}</option>)}</select></label><button type="button" className="secondary" disabled={!samples?.voices.find(v=>v.id===form.voice)?.sample_url} onClick={()=>void play('',samples!.voices.find(v=>v.id===form.voice)!.sample_url!)}>Прослушать образец</button>{!samples?.voices.find(v=>v.id===form.voice)?.sample_url&&<p className="micro">Записи голосов пока не подготовлены. Загрузка моделей отложена; задания доступны с текстом.</p>}<label>Громкость: {Math.round(form.volume*100)}%<input type="range" min={0} max={1} step={.1} value={form.volume} onChange={e=>setForm({...form,volume:Number(e.target.value)})}/></label><label>Скорость: {form.rate.toFixed(1)}×<input type="range" min={.8} max={1.2} step={.1} value={form.rate} onChange={e=>setForm({...form,rate:Number(e.target.value)})}/></label><h2>Отображение</h2>{toggle('reduced_motion','Уменьшить анимацию')}<p className="micro">Системное уменьшение движения учитывается автоматически.</p><label>Размер текста<select value={form.text_size} onChange={e=>setForm({...form,text_size:e.target.value as Settings['text_size']})}><option value="normal">Обычный</option><option value="large">Увеличенный</option></select></label><h2>Внутренние уведомления</h2>{toggle('notify_bookings','Статусы заявок')}{toggle('notify_retest','Повторное прохождение')}{toggle('notify_subscription','Состояние подписки')}<p className="micro">Доступен только центр уведомлений в приложении. Email, SMS и push не подключены.</p>{saved&&<p role="status">{saved}</p>}<button disabled={busy}>Сохранить настройки</button>{scope&&overridden&&<button type="button" className="secondary" disabled={busy} onClick={async()=>{setBusy(true);try{const result=await request<SettingsResponse>(path,'DELETE');setForm(result.settings);setOverridden(false);apply(result.settings);setSaved('Используются настройки родителя');}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>Использовать настройки родителя</button>}</form>}</>;
}
