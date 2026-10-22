export type Interest = 'Творчество' | 'Техника' | 'Музыка' | 'Движение' | 'Природа' | 'Истории';
export const interests: Interest[] = ['Творчество', 'Техника', 'Музыка', 'Движение', 'Природа', 'Истории'];
export interface Entity { id: string; schemaVersion: 1; createdAt: string }
export interface Child extends Entity { displayName: string; ageYears: number; interests: Interest[]; updatedAt: string }
export type ChildInput = Pick<Child, 'displayName' | 'ageYears' | 'interests'>;
export interface Session extends Entity {
  childId: string; childSnapshot: ChildInput; taskSetId: string; taskSetVersion: string;
  status: 'in_progress' | 'completed'; currentPosition: number; completedAt?: string;
}
export interface Answer extends Entity { sessionId: string; taskId: string; taskVersion: string; selectedOptionId: string; revision: number; answeredAt: string }
export interface AssessmentResult extends Entity {
  sessionId: string; engineId: string; engineVersion: string; mode: 'demo'; fixtureVersion: string;
  demoProfile: { title: string; description: string; isIllustrative: true }[];
}
export interface Program { id: string; version: string; title: string; organization: string; minAge: number; maxAge: number; tags: Interest[]; format: string; schedule: string; price: string; description: string; icon: string; color: string; isDemo: true }
export interface Application extends Entity { childId: string; programId: string; programVersion: string; sourceSessionId?: string; childSnapshot: ChildInput; status: 'demo_saved'; idempotencyKey: string }
export interface Settings { id: 'demo'; entered: boolean; activeChildId?: string; schemaVersion: 1 }
export interface Snapshot { children: Child[]; sessions: Session[]; answers: Answer[]; results: AssessmentResult[]; applications: Application[]; settings: Settings }
export interface Task { id: string; version: string; title: string; prompt: string; scene: string; options: { id: string; label: string }[]; sampleCategory: string }
