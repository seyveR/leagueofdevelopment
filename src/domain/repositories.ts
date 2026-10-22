import type { Answer, Application, AssessmentResult, Child, ChildInput, Session, Settings, Snapshot } from './models';
export interface ChildRepository { save(input: ChildInput, id?: string): Promise<Child>; select(id: string): Promise<void> }
export interface SessionRepository { start(childId: string, newAttempt?: boolean): Promise<Session>; saveAnswer(sessionId: string, position: number, optionId: string): Promise<Session>; complete(sessionId: string): Promise<AssessmentResult> }
export interface ApplicationRepository { save(childId: string, programId: string, sourceSessionId?: string): Promise<Application> }
export interface DemoRepository { load(): Promise<Snapshot>; enter(): Promise<void>; reset(): Promise<void> }
export interface Repositories { children: ChildRepository; sessions: SessionRepository; applications: ApplicationRepository; demo: DemoRepository }
export type { Answer, Application, AssessmentResult, Child, ChildInput, Session, Settings, Snapshot };
