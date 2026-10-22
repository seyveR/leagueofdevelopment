import Dexie, { type Table } from 'dexie';
import type { Repositories } from '../domain/repositories';
import type { Answer, Application, AssessmentResult, Child, ChildInput, Session, Settings } from '../domain/models';
import { interests } from '../domain/models';
import { programs, tasks, taskSet } from '../domain/content';
import { demoAssessmentEngine, type AssessmentEngine } from '../domain/engines';
import { entityId } from '../domain/id';

export class DemoDatabase extends Dexie {
  children!: Table<Child>; sessions!: Table<Session>; answers!: Table<Answer>;
  results!: Table<AssessmentResult>; applications!: Table<Application>; settings!: Table<Settings>;
  constructor(name = 'liga-razvitiya-demo') {
    super(name);
    this.version(1).stores({ children: 'id,createdAt', sessions: 'id,childId,[childId+status]', answers: 'id,sessionId,&[sessionId+taskId]', results: 'id,&sessionId', applications: 'id,childId,&idempotencyKey', settings: 'id' });
  }
}
const now = () => new Date().toISOString();
const base = () => ({ id: entityId(), schemaVersion: 1 as const, createdAt: now() });
const cloneChild = (c: ChildInput): ChildInput => ({ displayName: c.displayName, ageYears: c.ageYears, interests: [...c.interests] });
const defaultSettings: Settings = { id: 'demo', entered: false, schemaVersion: 1 };
export function validateChild(input: ChildInput): ChildInput {
  const displayName = input.displayName.trim();
  if (!displayName || displayName.length > 40) throw new Error('Укажите имя или псевдоним: от 1 до 40 символов.');
  if (!Number.isInteger(input.ageYears) || input.ageYears < 5 || input.ageYears > 12) throw new Error('Выберите возраст от 5 до 12 лет.');
  if (input.interests.some(i => !interests.includes(i))) throw new Error('Выберите интересы из списка.');
  return { displayName, ageYears: input.ageYears, interests: [...new Set(input.interests)] };
}
export function createLocalRepositories(db: DemoDatabase, engine: AssessmentEngine = demoAssessmentEngine): Repositories {
  async function child(id: string) { const c = await db.children.get(id); if (!c) throw new Error('Профиль ребёнка не найден. Вернитесь на главную.'); return c; }
  async function session(id: string) { const s = await db.sessions.get(id); if (!s) throw new Error('Прохождение не найдено. Вернитесь к заданиям.'); return s; }
  return {
    demo: {
      async load() {
        return db.transaction('r', db.tables, async () => ({ children: await db.children.orderBy('createdAt').toArray(), sessions: await db.sessions.toArray(), answers: await db.answers.toArray(), results: await db.results.toArray(), applications: await db.applications.toArray(), settings: await db.settings.get('demo') ?? defaultSettings }));
      },
      async enter() { await db.settings.put({ ...(await db.settings.get('demo') ?? defaultSettings), entered: true }); },
      async reset() { await db.transaction('rw', db.tables, async () => { for (const table of db.tables) await table.clear(); }); },
    },
    children: {
      async save(input, id) {
        const valid = validateChild(input);
        return db.transaction('rw', db.children, db.settings, async () => {
          const old = id ? await child(id) : undefined;
          const value: Child = { ...(old ?? base()), ...valid, updatedAt: now() };
          await db.children.put(value);
          await db.settings.put({ ...(await db.settings.get('demo') ?? defaultSettings), entered: true, activeChildId: value.id });
          return value;
        });
      },
      async select(id) { await db.transaction('rw', db.children, db.settings, async () => { await child(id); await db.settings.put({ ...(await db.settings.get('demo') ?? defaultSettings), activeChildId: id }); }); },
    },
    sessions: {
      async start(childId, newAttempt = false) {
        return db.transaction('rw', db.children, db.sessions, async () => {
          const c = await child(childId);
          const active = await db.sessions.where('[childId+status]').equals([childId, 'in_progress']).first();
          if (active) return active;
          if (!newAttempt) { const last = (await db.sessions.where('childId').equals(childId).sortBy('createdAt')).at(-1); if (last) return last; }
          const value: Session = { ...base(), childId, childSnapshot: cloneChild(c), taskSetId: taskSet.id, taskSetVersion: taskSet.version, status: 'in_progress', currentPosition: 0 };
          await db.sessions.add(value); return value;
        });
      },
      async saveAnswer(sessionId, position, optionId) {
        return db.transaction('rw', db.sessions, db.answers, async () => {
          const s = await session(sessionId);
          if (s.taskSetVersion !== taskSet.version) throw new Error('Версия заданий изменилась. Начните новое прохождение.');
          const task = tasks[position];
          if (!task || !task.options.some(o => o.id === optionId)) throw new Error('Выберите один из ответов.');
          const old = await db.answers.where('[sessionId+taskId]').equals([sessionId, task.id]).first();
          // Retries of the same committed operation are safe, including after completion.
          if (position < s.currentPosition && old?.selectedOptionId === optionId) return s;
          if (s.status !== 'in_progress' || position !== s.currentPosition) throw new Error('Шаг уже изменился. Обновите страницу, чтобы продолжить.');
          await db.answers.put({ ...(old ?? base()), sessionId, taskId: task.id, taskVersion: task.version, selectedOptionId: optionId, revision: (old?.revision ?? 0) + 1, answeredAt: now() });
          const updated = { ...s, currentPosition: position + 1 };
          await db.sessions.put(updated); return updated;
        });
      },
      async complete(sessionId) {
        const s = await session(sessionId);
        const existing = await db.results.where('sessionId').equals(sessionId).first();
        if (existing) return existing;
        const answers = await db.answers.where('sessionId').equals(sessionId).toArray();
        if (s.currentPosition !== tasks.length || !tasks.every(t => answers.some(a => a.taskId === t.id && a.taskVersion === t.version && t.options.some(o => o.id === a.selectedOptionId)))) throw new Error('Сначала ответьте на все семь заданий.');
        // Async engines run outside IndexedDB transactions; later this can be an API call.
        const evaluated = await engine.evaluate(s, answers);
        return db.transaction('rw', db.sessions, db.results, async () => {
          const current = await session(sessionId); // Reset in another tab must not resurrect data.
          const previous = await db.results.where('sessionId').equals(sessionId).first();
          if (previous) return previous;
          const result: AssessmentResult = { ...base(), ...evaluated };
          await db.results.add(result);
          await db.sessions.put({ ...current, status: 'completed', completedAt: now() });
          return result;
        });
      },
    },
    applications: {
      async save(childId, programId, sourceSessionId) {
        return db.transaction('rw', db.children, db.sessions, db.applications, async () => {
          const c = await child(childId); const p = programs.find(p => p.id === programId);
          if (!p) throw new Error('Программа не найдена. Выберите другую.');
          if (c.ageYears < p.minAge || c.ageYears > p.maxAge) throw new Error(`Программа доступна для возраста ${p.minAge}–${p.maxAge} лет.`);
          if (sourceSessionId) { const s = await session(sourceSessionId); if (s.childId !== childId || s.status !== 'completed') throw new Error('Результат не относится к выбранному ребёнку.'); }
          // One local application per child/program, also across reloads and tabs.
          const idempotencyKey = `demo:${childId}:${programId}`;
          const old = await db.applications.where('idempotencyKey').equals(idempotencyKey).first(); if (old) return old;
          const a: Application = { ...base(), childId, programId, programVersion: p.version, childSnapshot: cloneChild(c), sourceSessionId, status: 'demo_saved', idempotencyKey };
          await db.applications.add(a); return a;
        });
      },
    },
  };
}

