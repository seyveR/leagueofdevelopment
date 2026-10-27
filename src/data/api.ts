import type {User,Child,ChildInput,Session,State,Detail,Result,Club,ClubInput,Rule,Recommendation,Feedback,AdminCompletion,AdminCompletionDetail,Page,ClubTransitionPage} from '../domain/api-models';
let csrf='';
export type SessionEndReason='expired'|'logout'|'password_changed';
const sessionListeners=new Set<(reason:SessionEndReason)=>void>();
let sessionGeneration=0;
let currentUserId:string|null=null;
export function onSessionEnded(listener:(reason:SessionEndReason)=>void){sessionListeners.add(listener);return()=>{sessionListeners.delete(listener);};}
function endSession(reason:SessionEndReason){sessionGeneration++;currentUserId=null;csrf='';for(const listener of sessionListeners)listener(reason);}
export class ApiError extends Error { constructor(public status:number,message:string){super(message);} }
export async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const generation=sessionGeneration;
  let response:Response;
  try {response=await fetch(`/api${path}`,{method,credentials:'same-origin',headers:{'Content-Type':'application/json',...(method==='GET'?{}:{'X-CSRF-Token':csrf})},...(body===undefined?{}:{body:JSON.stringify(body)})});}
  catch {throw new Error('Нет связи с сервером. Проверьте подключение и повторите сохранение.');}
  const value=await response.json().catch(()=>null);
  if(!response.ok){if(response.status===401&&path!=='/auth/login'&&path!=='/auth/register'&&generation===sessionGeneration)endSession('expired');const message=typeof value?.detail==='string'?value.detail:response.status===422?'Проверьте введённые данные.':'Не удалось выполнить действие. Повторите попытку.';throw new ApiError(response.status,message);}
  return value as T;
}
async function auth(path:string,body?:unknown){const generation=sessionGeneration;const value=await request<{user:User|null;csrf:string}>(path,body?'POST':'GET',body);if(generation!==sessionGeneration)throw new ApiError(401,'Сессия изменилась. Войдите заново.');if(!value.user&&currentUserId)endSession('expired');if(body)sessionGeneration++;currentUserId=value.user?.id??null;csrf=value.csrf;return value.user;}
async function credentials(path:string,email:string,password:string){if(!csrf)await auth('/auth/session');return auth(path,{email,password});}
// Screens depend on these API repositories, never on IndexedDB or SQLAlchemy.
export const api={
  auth:{session:()=>auth('/auth/session'),register:(email:string,password:string)=>credentials('/auth/register',email,password),login:(email:string,password:string)=>credentials('/auth/login',email,password),logout:async()=>{await auth('/auth/session');await request('/auth/logout','POST');endSession('logout');},changePassword:async(current_password:string,new_password:string,confirmation:string)=>{await request('/auth/password','POST',{current_password,new_password,confirmation});endSession('password_changed');}},
  consent:()=>request<{version:string;text:string}>('/consent'),
  state:()=>request<State>('/state'),
  children:{save:(input:ChildInput,id?:string,requestId?:string)=>request<Child>(id?`/children/${id}`:'/children',id?'PUT':'POST',{...input,request_id:requestId})},
  sessions:{start:(child_id:string,request_id:string,scenario='legacy')=>request<Session>('/sessions','POST',{child_id,request_id,scenario}),get:(id:string)=>request<Detail>(`/sessions/${id}`),hide:(id:string,task_id:string)=>request<Session>(`/sessions/${id}/hide`,'POST',{task_id}),answer:(id:string,task_id:string,option_id:string)=>request<Session>(`/sessions/${id}/answers`,'POST',{task_id,option_id}),complete:(id:string)=>request<Result>(`/sessions/${id}/complete`,'POST'),result:(id:string)=>request<Result>(`/sessions/${id}/result`),recommend:(id:string)=>request<Recommendation[]>(`/sessions/${id}/recommendations`),open:(id:string,club_id:string,request_id:string)=>request(`/sessions/${id}/club-open`,'POST',{club_id,request_id})},
  clubs:{list:(age?:number,city?:string)=>request<Club[]>(`/clubs?${new URLSearchParams({...(age?{age:String(age)}:{}),...(city?{city}:{})})}`),get:(id:string)=>request<Club>(`/clubs/${id}`)},
  feedback:(rating:number,message:string,request_id:string)=>request<Feedback>('/feedback','POST',{rating,message,request_id}),
  admin:{completions:(offset=0)=>request<Page<AdminCompletion>>(`/admin/completions?offset=${offset}`),completion:(id:string)=>request<AdminCompletionDetail>(`/admin/completions/${id}`),transitions:(offset=0)=>request<ClubTransitionPage>(`/admin/club-transitions?offset=${offset}`),clubs:()=>request<Club[]>('/admin/clubs'),saveClub:(body:ClubInput,id?:string,requestId?:string)=>request<Club>(id?`/admin/clubs/${id}`:'/admin/clubs',id?'PUT':'POST',{...body,request_id:requestId}),rules:()=>request<Rule[]>('/admin/rules'),saveRule:(id:string,body:Omit<Rule,'id'|'club_id'>)=>request<Rule>(`/admin/clubs/${id}/rule`,'PUT',body),stats:()=>request<{completed:number;club_open:number}>('/admin/stats'),feedback:()=>request<Feedback[]>('/admin/feedback')}
};

