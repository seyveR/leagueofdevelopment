export interface User { id: string; email: string; role: 'parent' | 'admin' }
export interface Child { id:string;name:string;age:number;gender:string;interests:string[];city:string;consent_at:string;consent_version:string }
export interface ChildInput { name:string;age:number;gender:string;interests:string[];city:string;consent:boolean;consent_version?:string }
export interface Session { id:string;child_id:string;task_set_id:string;child_snapshot:Pick<Child,'name'|'age'|'city'>;position:number;phase:'view'|'answer';status:'in_progress'|'completed';created_at:string;completed_at:string|null;algorithm_version:string }
export interface GroupScore {correct:number;total:number;percent:number}
export interface Result {id:string;session_id:string;algorithm_version:string;scores:{completed:number;correct:number;total:number;attention:GroupScore;memory:GroupScore;comment:string}}
export interface State { children:Child[];sessions:Session[];results:Result[] }
export interface Task {id:string;category:'attention'|'memory'|'logic'|'spatial'|'coordination'|'pace';prompt:string;stimulus:string|null;options:{id:string;label:string;mapping?:number[]}[];mechanic?:string;difficulty?:number;left?:string[];right?:string[]}
export interface Detail {session:Session;task:Task|null;answers:{task_id:string;option_id:string}[];total:number}
export interface Club {id:string;name:string;description:string;min_age:number;max_age:number;city:string;address:string;phone:string;price:string;photo_url:string;archived:boolean}
export type ClubInput=Omit<Club,'id'>;
export interface Rule {id:string;club_id:string;metric:'any'|'attention'|'memory';minimum:number;maximum:number;priority:number;explanation:string}
export interface Recommendation {club:Club;explanation:string;rules_version:string}
export interface Feedback {id:string;user_id:string;rating:number;message:string;created_at:string}
export interface AdminCompletion {session:Session;parent:Pick<User,'id'|'email'>;result:Result}
export interface AdminCompletionDetail extends AdminCompletion {task_set_version:string;answers:{task_id:string;category:string;prompt:string;stimulus:string;selected:string|null;correct:string;is_correct:boolean;answered_at:string|null}[]}
export interface Page<T> {items:T[];total:number;offset:number;limit:number}
export interface ClubTransition {club_id:string;name:string;city:string;archived:boolean;count:number;last_opened_at:string}
export interface ClubTransitionPage extends Page<ClubTransition> {total_openings:number}
