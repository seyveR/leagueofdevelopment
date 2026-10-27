import type {Club,Child,User,GroupScore} from '../domain/api-models';
export interface Organization {id:string;name:string;description:string;city:string;contact:string;status:string;reason:string;document_id:string|null}
export interface ProgramInfo {club_id:string;organization_id:string|null;format:'online'|'offline'|'hybrid';price_rub:number;tags:string[];photos:string[];schedule:string;promotion:string;status:string;reason:string}
export interface Program extends Club {details:ProgramInfo|null}
export interface Slot {id:string;starts_at:string;capacity:number;enabled?:boolean}
export interface ProgramDetail extends Program {slots:Slot[];reviews:{id:string;rating:number;message:string;created_at:string}[];rating:number|null;favorite:boolean;organization:{id:string;name:string}|null}
export interface Booking {id:string;child_id:string;club_id:string;slot_id:string;status:string;contact:string;snapshot:{name:string;age:number};note:string;created_at:string;program_name:string;starts_at:string;history:{id:string;status:string;note:string;created_at:string}[]}
export interface Plan {id:string;name:string;price_rub:number;child_limit:number;duration_days:number;features:string[];active?:boolean}
export interface Entitlement {plan_id:string;name:string;child_limit:number;features:string[];expires_at:string|null;status:string;cancelled:boolean;payment_mode:string}
export interface Plans {items:Plan[];entitlement:Entitlement;mode:string;message:string}
export interface Specialist {id:string;name:string;description:string;contact:string;slots:string[];is_test:boolean;active?:boolean}
export interface Consultation {id:string;specialist_id:string;starts_at:string;status:string;contact:string;name:string;is_test:boolean}
export interface Notice {id:string;kind:string;message:string;url:string;read:boolean;created_at:string}
export interface Account {email:string;email_verified:boolean;consent:boolean;consent_version:string;delivery_mode:string;payment_mode:string}
export interface ManagedUser extends User {blocked:boolean;created_at:string}
export interface Review {id:string;club_id:string;rating:number;message:string;status:string;reason:string}
export interface Audit {id:string;actor_id:string|null;action:string;entity_id:string;detail:string;created_at:string}
export interface Comparison {groups:{session_id:string;date:string;scores:Record<string,GroupScore>}[][];message:string}
export type {Child,User};
