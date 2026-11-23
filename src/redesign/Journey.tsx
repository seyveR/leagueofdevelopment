import {ColorfulText} from './ColorfulText';
import {useRef,useState,type PointerEvent} from 'react';
import {Link,Navigate,useNavigate} from 'react-router-dom';
import {useApp} from '../app/ApiApp';
import {api} from '../data/api';
import {journey,journeyVersion,type JourneyTask,type JourneyPayload,type Stroke,type JourneyScores,type Metric} from '../data/journey';
import {entityId} from '../domain/id';
import type {Session} from '../domain/api-models';
import {useResource,useAction,Loading,Feedback,date} from '../platform/common';
import './journey.css';

const labels:Record<string,string>={logic:'Логические задания',attention:'Поиск деталей',memory:'Зрительная память',spatial:'Маршрут',story:'Последовательность событий',imagination:'Творческий выбор'};
const arrows:Record<string,string>={up:'↑',left:'←',right:'→',down:'↓'};
export function JourneyCatalog(){
  const {data,activeId,refresh}=useApp(),navigate=useNavigate(),action=useAction();
  const child=data.children.find(c=>c.id===activeId);
  const load=useResource(()=>child?journey.catalog(child.id):Promise.resolve(null),child?.id);
  const sessions=data.sessions.filter(s=>s.child_id===child?.id);
  const current=sessions.find(s=>s.task_set_id===load.value?.set_id&&s.status==='in_progress');
  const requestId=useRef(entityId());
  return <><h1>Тесты</h1>{!child?<section className="card"><h2>Начнём с профиля ребёнка</h2><p>Возраст определяет сложность игровых заданий.</p><Link className="button" to="/children/new">Добавить ребёнка</Link></section>:<>
    <p>{child.name} · {child.age} лет</p>
    {load.value===undefined?<Loading {...load}/>:<section className="card journey-intro"><span className="pill">{load.value?.age_group??'4–17'} лет · 10 заданий</span><h2>Путь открытий</h2><p>Собирай идеи, рисуй, запоминай картинки и прокладывай маршрут. После прохождения — результат и подбор занятий по ответам.</p><p>Около 10–15 минут. Можно прерваться после любого сохранённого задания. Озвучка этого набора выключена.</p><div className="journey-age-groups" aria-label="Возрастные варианты">{load.value?.groups.map(g=><span className={g.min<=child.age&&g.max>=child.age?'active':''} key={g.min}>{g.min}–{g.max}</span>)}</div><Feedback {...action}/>{load.value?.available?<button disabled={action.busy} onClick={()=>void action.run(async()=>{const s=current??await journey.start(child.id,requestId.current);await refresh();navigate(`/sessions/${s.id}/${current?'tasks':'intro'}`);})}>{current?`Продолжить · ${current.position} из 10`:'Начать прохождение'}</button>:<p>Этот путь доступен детям от 4 до 17 лет. Старые результаты доступны в истории.</p>}</section>}
    <section className="card"><h2>История прохождений</h2>{sessions.length?sessions.map(s=><p key={s.id}><Link to={`/sessions/${s.id}/${s.status==='completed'?'result':'tasks'}`}>{date(s.created_at)} · {(data.results.find(r=>r.session_id===s.id)?.scores as unknown as {test_name?:string})?.test_name??(s.algorithm_version===journeyVersion?'Путь открытий':'Прежний набор')} · {s.status==='completed'?'Результат':`Продолжить · ${s.position}`}</Link></p>):<p>Здесь появятся сохранённые прохождения ребёнка.</p>}</section>
  </>}</>;
}

export function JourneyRunner({session}:{session:Session}){
  const load=useResource(()=>journey.detail(session.id),session.id);
  const action=useAction(),navigate=useNavigate(),{refresh}=useApp();
  if(!load.value)return <Loading {...load}/>;
  const {session:s,task,total}=load.value;
  if(s.status==='completed')return <Navigate to={`/sessions/${s.id}/result`} replace/>;
  if(!task)return <section className="card"><h1>Все задания сохранены</h1><p>Результат будет рассчитан по вашим ответам.</p><Feedback {...action}/><button disabled={action.busy} onClick={()=>void action.run(async()=>{await api.sessions.complete(s.id);await refresh();navigate(`/sessions/${s.id}/result`);})}>Посмотреть результат</button></section>;
  return <><Link className="back" to="/tests">Выйти и продолжить позже</Link><p>{s.child_snapshot.name} · Задание {s.position+1} из {total}</p><progress value={s.position} max={total} aria-label="Сохранённые задания"/><Activity key={task.id+'-'+s.phase} task={task} session={s} reload={load.reload}/></>;
}

function Activity({task:t,session,reload}:{task:JourneyTask;session:Session;reload:()=>void}){
  const cfg=t.config,choices=cfg.choices??[];
  const [selected,setSelected]=useState<string[]>([]),[buckets,setBuckets]=useState<string[]>(Array(choices.length).fill(''));
  const [item,setItem]=useState(''),[reason,setReason]=useState(''),[pattern,setPattern]=useState<string[]>(['','','']);
  const [strokes,setStrokes]=useState<Stroke[]>([]);
  const action=useAction(),{refresh}=useApp();
  const toggle=(id:string)=>setSelected(v=>v.includes(id)?v.filter(x=>x!==id):v.length<(cfg.max_select??choices.length)?[...v,id]:v);
  const ordered=t.mechanic==='order';
  const memory=t.mechanic==='memory'&&session.phase==='view';
  const route=t.mechanic==='route';
  const start=cfg.start??[2,2];let [x,y]=start;
  if(route)for(const dir of selected){const [dx,dy]={up:[0,-1],down:[0,1],left:[-1,0],right:[1,0]}[dir]!;x+=dx;y+=dy;}
  let payload:JourneyPayload={selected};let ready=true;
  if(t.mechanic==='combine')ready=selected.length>0;
  if(ordered)ready=selected.length===cfg.length;
  if(route)ready=selected.length===cfg.steps!.length;
  if(t.mechanic==='sort'){payload={buckets};ready=buckets.every(Boolean);}
  if(t.mechanic==='odd'){payload={item,reason};ready=!!item&&!!reason;}
  if(t.mechanic==='patterns'){payload={selected:pattern};ready=pattern.every(Boolean);}
  if(t.mechanic==='draw'){payload={choice:item,strokes};ready=!!item&&strokes.length>0;}
  return <section className="card journey-activity"><span className="pill">{labels[t.category]}</span><h1>{t.prompt}</h1>
    {memory?<><div className="memory-material" aria-label="Картинки для запоминания">{cfg.material?.map((s,i)=><span key={i}>{s}</span>)}</div><p>Посмотри на картинки. Когда запомнишь — скрой их.</p><button disabled={action.busy} onClick={()=>void action.run(async()=>{await api.sessions.hide(session.id,t.id);reload();})}>Скрыть и ответить</button></>:<>
      {t.mechanic==='draw'&&<Drawing shape={cfg.shape??'circle'} strokes={strokes} change={setStrokes} disabled={action.busy}/>}
      {t.mechanic==='sort'&&<div className="sort-cards">{choices.map((c,i)=><div className="sort-card" key={c.id}><strong>{c.label}</strong><div className="button-row">{cfg.buckets?.map((label,b)=><button type="button" aria-pressed={buckets[i]===String(b)} className={buckets[i]===String(b)?'chosen':'secondary'} key={b} onClick={()=>setBuckets(v=>v.map((old,j)=>j===i?String(b):old))}>{label}</button>)}</div></div>)}</div>}
      {t.mechanic==='patterns'&&cfg.sequences?.map((part,i)=><fieldset key={i}><legend>Ряд {i+1}</legend><p className="pattern-stimulus"><ColorfulText text={part.text}/></p><div className="activity-options">{part.choices.map(c=><button type="button" className={pattern[i]===c.id?'chosen':'secondary'} aria-pressed={pattern[i]===c.id} key={c.id} onClick={()=>setPattern(v=>v.map((old,j)=>i===j?c.id:old))}><ColorfulText text={c.label}/></button>)}</div></fieldset>)}
      {route&&<><p className="route-instruction">Маршрут: {cfg.steps?.map(s=>arrows[s]).join(' · ')}</p><p>Шаг {Math.min(selected.length+1,cfg.steps!.length)} из {cfg.steps!.length}</p><div className="route-board" style={{gridTemplateColumns:`repeat(${cfg.grid},1fr)`}} aria-label="Поле с роботом">{Array.from({length:(cfg.grid??5)**2},(_,i)=><span key={i}>{i%(cfg.grid??5)===x&&Math.floor(i/cfg.grid!)===y?'🤖':i%(cfg.grid??5)===start[0]&&Math.floor(i/cfg.grid!)===start[1]?'○':''}</span>)}</div><div className="route-controls">{['up','left','down','right'].map(dir=>{const [dx,dy]={up:[0,-1],down:[0,1],left:[-1,0],right:[1,0]}[dir]!;return <button type="button" aria-label={{up:'Вверх',left:'Влево',down:'Вниз',right:'Вправо'}[dir]} disabled={selected.length>=cfg.steps!.length||x+dx<0||x+dx>=cfg.grid!||y+dy<0||y+dy>=cfg.grid!} key={dir} onClick={()=>setSelected(v=>[...v,dir])}>{arrows[dir]}</button>;})}</div><p aria-label="Собранный маршрут">Твой путь: {selected.map(s=>arrows[s]).join(' · ')||'ещё не начат'}</p><button type="button" className="secondary" onClick={()=>setSelected(v=>v.slice(0,-1))} disabled={!selected.length}>Отменить шаг</button></>}
      {ordered&&<><p>Нажимай карточки в нужном порядке. Повторное нажатие убирает карточку.</p><ol className="ordered-slots">{Array.from({length:cfg.length!},(_,i)=><li key={i}>{choices.find(c=>c.id===selected[i])?.label??'Выбери карточку'}</li>)}</ol></>}
      {['combine','draw','odd','memory','targets','order'].includes(t.mechanic)&&<>
        {t.mechanic==='combine'&&<div className="combination-scene" aria-label="Мастерская">📦 → {selected.map(id=>choices.find(c=>c.id===id)?.label).join(' + ')||'Твои идеи'}</div>}
        {t.mechanic==='draw'&&<p>Что получилось на рисунке? Выбери подходящий вариант.</p>}
        {t.mechanic==='targets'&&<p>Можно нажать повторно, чтобы убрать выбор.</p>}
        <div className={'activity-options '+(t.mechanic==='targets'?'target-grid':'')} style={t.mechanic==='targets'?{gridTemplateColumns:`repeat(${cfg.columns},1fr)`}:undefined} aria-label="Элементы задания">{choices.map(c=>{const active=['draw','odd'].includes(t.mechanic)?item===c.id:selected.includes(c.id);return <button type="button" key={c.id} disabled={action.busy} className={active?'chosen':'secondary'} aria-pressed={active} aria-label={t.mechanic==='targets'?`Ячейка ${Number(c.id)+1}: ${c.label}`:undefined} onClick={()=>['draw','odd'].includes(t.mechanic)?setItem(c.id):ordered?setSelected(v=>v.includes(c.id)?v.filter(x=>x!==c.id):v.length<cfg.length!?[...v,c.id]:v):toggle(c.id)}>{ordered&&active?<span className="order-number">{selected.indexOf(c.id)+1}. </span>:null}<ColorfulText text={c.label}/></button>;})}</div>
        {t.mechanic==='odd'&&item&&<fieldset><legend>Почему этот элемент лишний?</legend>{cfg.reasons?.map(c=><button className={reason===c.id?'chosen':'secondary'} type="button" aria-pressed={reason===c.id} key={c.id} onClick={()=>setReason(c.id)}><ColorfulText text={c.label}/></button>)}</fieldset>}
      </>}
      <p className="micro">Сохранится после нажатия кнопки. Можно менять действия до сохранения.</p><button disabled={!ready||action.busy} onClick={()=>void action.run(async()=>{await journey.answer(session.id,t.id,payload);await refresh();reload();})}>{action.busy?'Сохраняем…':'Сохранить и дальше'}</button>
    </>}<Feedback {...action}/></section>;
}

function Drawing({shape,strokes,change,disabled}:{shape:string;strokes:Stroke[];change:(s:Stroke[])=>void;disabled:boolean}){
  const svg=useRef<SVGSVGElement>(null),active=useRef(false),latest=useRef(strokes);latest.current=strokes;
  const point=(e:PointerEvent<SVGSVGElement>):[number,number]=>{const r=e.currentTarget.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];};
  return <><svg ref={svg} className="drawing-board" viewBox="0 0 400 300" role="img" aria-label="Холст: рисуй пальцем или мышью" onPointerDown={e=>{if(disabled||latest.current.length>=80)return;active.current=true;e.currentTarget.setPointerCapture(e.pointerId);const next=[...latest.current,[point(e)]];latest.current=next;change(next);}} onPointerMove={e=>{if(!active.current||disabled)return;const next=latest.current.map(s=>[...s]);if(next[next.length-1].length<300){next[next.length-1].push(point(e));latest.current=next;change(next);}}} onPointerUp={()=>{active.current=false;}} onPointerCancel={()=>{active.current=false;}}>
    {shape==='circle'?<circle cx="200" cy="150" r="65" fill="#fff0c4" stroke="#ec9460" strokeWidth="3"/>:shape==='triangle'?<path d="M200 65L285 220H115Z" fill="#fff0c4" stroke="#ec9460" strokeWidth="3"/>:shape==='square'?<rect x="125" y="75" width="150" height="150" fill="#fff0c4" stroke="#ec9460" strokeWidth="3"/>:<path d="M150 70H250L300 150L250 230H150L100 150Z" fill="#fff0c4" stroke="#ec9460" strokeWidth="3"/>}
    {strokes.map((s,i)=><polyline key={i} points={s.map(([x,y])=>`${x*400},${y*300}`).join(' ')} fill="none" stroke="#655397" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>)}
  </svg><div className="button-row"><button type="button" className="secondary" disabled={disabled||!strokes.length} onClick={()=>change(strokes.slice(0,-1))}>Убрать штрих</button><button type="button" className="secondary" disabled={disabled||!strokes.length} onClick={()=>change([])}>Очистить рисунок</button></div></>;
}

export function JourneyResult({session}:{session:Session}){
  const load=useResource(()=>api.sessions.result(session.id),session.id);
  if(!load.value)return <Loading {...load}/>;
  const s=load.value.scores as unknown as JourneyScores;
  return <><h1>Результат: путь открытий</h1><p>{session.child_snapshot.name} · {session.child_snapshot.age} лет · {date(session.completed_at??session.created_at)}</p><section className="card"><h2>Выполнено {s.completed} из {s.total}</h2></section><section className="card"><h2>Что получилось в заданиях</h2>{Object.keys(labels).filter(k=>k!=='imagination'&&s[k]).map(k=>{const m=s[k] as Metric;return <div className="journey-metric" key={k}><strong>{labels[k]}</strong><span>{m.correct} из {m.total} действий</span><progress max={m.total} value={m.correct} aria-label={labels[k]}/></div>;})}</section><h2>Какие занятия попробовать</h2>{s.directions.slice(0,2).map(d=><section className="card" key={d.code}><h3>{d.name}</h3><p>{d.reason.split('. Это')[0]}</p></section>)}<Link className="button" to={`/sessions/${session.id}/recommendations`}>Подобрать кружки</Link><section className="card"><h2>Подробности прохождения</h2>{s.task_details.map((t,i)=><details key={t.task_id}><summary>{i+1}. {t.prompt}</summary><p>{t.score?`${t.score.correct} из ${t.score.total} проверяемых действий`:'Свободное творческое задание; ответ сохранён без оценки.'}</p></details>)}</section><Link className="back" to="/tests">Вернуться к тестам</Link></>;
}
