import {useEffect,useRef,useState} from 'react';
export const date=(value:string)=>new Date(value).toLocaleString('ru-RU');
export const statuses:Record<string,string>={draft:'Черновик',pending:'На проверке',approved:'Одобрено',rejected:'Отклонено',closed:'Закрыто',archived:'В архиве',new:'Новая заявка',accepted:'Принята',completed:'Пробное занятие завершено · запись активна',cancelled:'Отменено',cancellation_requested:'Запрошено прекращение занятий',ended:'Занятия прекращены',published:'Опубликовано',confirmed:'Подтверждено'};
export const status=(value:string)=>statuses[value]??value;
export function useResource<T>(fn:()=>Promise<T>,key=''){
  const[value,setValue]=useState<T>(),[error,setError]=useState(''),[tick,setTick]=useState(0);const loader=useRef(fn);loader.current=fn;
  useEffect(()=>{let live=true;setValue(undefined);setError('');void loader.current().then(v=>{if(live)setValue(v);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[key,tick]);return {value,error,reload:()=>setTick(n=>n+1)};
}
export function useAction(){const[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');const lock=useRef(false);async function run(fn:()=>Promise<void>){if(lock.current)return;lock.current=true;setBusy(true);setError('');setMessage('');try{await fn();}catch(e){setError((e as Error).message);}finally{lock.current=false;setBusy(false);}}return{busy,error,message,setMessage,run};}
export function Feedback({error,message}:{error?:string;message?:string}){return <>{error&&<p className="error" role="alert">{error}</p>}{message&&<p className="notice" role="status">{message}</p>}</>;}
export function Loading({error,reload}:{error:string;reload:()=>void}){return error?<div className="card"><Feedback error={error}/><button onClick={reload}>Повторить загрузку</button></div>:<p role="status">Загрузка…</p>;}
export function downloadJson(data:unknown,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
