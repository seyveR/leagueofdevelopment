import {request} from './api';
import type {Session} from '../domain/api-models';

export const journeyVersion='discovery-1.0.0';
export type Item={id:string;label:string};
export type Stroke=[number,number][];
export type JourneyTask={id:string;prompt:string;category:string;mechanic:string;config:{
  choices?:Item[];reasons?:Item[];sequences?:{text:string;choices:Item[]}[];
  material?:string[];shape?:string;buckets?:string[];length?:number;
  max_select?:number;columns?:number;steps?:string[];start?:number[];grid?:number;
}};
export type JourneyDetail={session:Session;task:JourneyTask|null;total:number};
export type JourneyCatalog={available:boolean;groups:{min:number;max:number}[];age_group:string|null;set_id:string|null;count:number;version:string};
export type JourneyPayload={selected:string[]}|{buckets:string[]}|{item:string;reason:string}|{choice:string;strokes:Stroke[]};
export type Metric={correct:number;total:number;percent:number};
export type JourneyScores={completed:number;total:number;comment:string;
  task_details:{task_id:string;prompt:string;metric:string;score:Metric|null}[];
  directions:{code:string;name:string;reason:string}[];[key:string]:unknown};
export const journey={
  catalog:(child:string)=>request<JourneyCatalog>('/journey?child_id='+child),
  start:(child:string,id:string)=>request<Session>('/journey/start','POST',{child_id:child,request_id:id}),
  detail:(id:string)=>request<JourneyDetail>('/journey/'+id),
  answer:(id:string,task:string,payload:JourneyPayload)=>request<Session>('/journey/'+id+'/answers','POST',{task_id:task,payload}),
};
