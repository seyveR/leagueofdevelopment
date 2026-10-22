import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLocalRepositories, DemoDatabase } from './local';
import type { Repositories } from '../domain/repositories';
import { demoAssessmentEngine, recommendationEngine } from '../domain/engines';
import { programs, tasks } from '../domain/content';
let db: DemoDatabase; let repo: Repositories;
const input = { displayName: 'Лисёнок', ageYears: 8, interests: ['Творчество'] as const };
const childInput = () => ({ ...input, interests: [...input.interests] });
beforeEach(() => { db = new DemoDatabase(`test-${crypto.randomUUID()}`); repo = createLocalRepositories(db); });
afterEach(async () => { vi.restoreAllMocks(); await db.delete(); });
async function finish(id: string) { for (let n=0;n<tasks.length;n++) await repo.sessions.saveAnswer(id, n, tasks[n].options[0].id); return repo.sessions.complete(id); }
describe('локальные репозитории', () => {
  it('разделяют детей, восстанавливают шаг и сохраняют снимок прошлого профиля', async () => {
    const a = await repo.children.save(childInput()); const b = await repo.children.save({ ...childInput(), displayName:'Звёздочка', ageYears:6 });
    const sa = await repo.sessions.start(a.id); const sb = await repo.sessions.start(b.id);
    await repo.sessions.saveAnswer(sa.id, 0, tasks[0].options[1].id);
    await repo.children.save({ ...childInput(), displayName:'Новое имя', ageYears:9 }, a.id);
    const restored = createLocalRepositories(db); const snap = await restored.demo.load();
    expect(snap.sessions.find(s => s.id === sa.id)?.currentPosition).toBe(1);
    expect(snap.sessions.find(s => s.id === sb.id)?.currentPosition).toBe(0);
    expect(snap.sessions.find(s => s.id === sa.id)?.childSnapshot.ageYears).toBe(8);
    expect(snap.answers).toHaveLength(1); expect(snap.answers[0].sessionId).toBe(sa.id);
    expect(snap.answers[0].selectedOptionId).toBe(tasks[0].options[1].id);
    await restored.children.select(b.id); expect((await restored.demo.load()).settings.activeChildId).toBe(b.id);
  });
  it('не пропускают обязательный вопрос и не дублируют старт или ответ', async () => {
    const c = await repo.children.save(childInput()); const [a,b] = await Promise.all([repo.sessions.start(c.id),repo.sessions.start(c.id)]); expect(a.id).toBe(b.id);
    await expect(repo.sessions.saveAnswer(a.id,0,'')).rejects.toThrow();
    await expect(repo.sessions.saveAnswer(a.id,1,tasks[1].options[0].id)).rejects.toThrow();
    await expect(repo.sessions.complete(a.id)).rejects.toThrow('семь');
    await Promise.all([repo.sessions.saveAnswer(a.id,0,tasks[0].options[0].id),repo.sessions.saveAnswer(a.id,0,tasks[0].options[0].id)]);
    const snap = await repo.demo.load(); expect(snap.answers).toHaveLength(1); expect(snap.sessions[0].currentPosition).toBe(1);
  });
  it('откатывают ответ и шаг при ошибке записи, затем допускают повтор', async () => {
    const c = await repo.children.save(childInput()); const s = await repo.sessions.start(c.id);
    vi.spyOn(db.sessions, 'put').mockRejectedValueOnce(new DOMException('No space','QuotaExceededError'));
    await expect(repo.sessions.saveAnswer(s.id,0,tasks[0].options[0].id)).rejects.toThrow();
    let snap = await repo.demo.load(); expect(snap.answers).toHaveLength(0); expect(snap.sessions[0].currentPosition).toBe(0);
    await repo.sessions.saveAnswer(s.id,0,tasks[0].options[0].id); snap = await repo.demo.load(); expect(snap.answers).toHaveLength(1); expect(snap.sessions[0].currentPosition).toBe(1);
  });
  it('сохраняют все исходные ответы при сбое завершения и один результат при повторе', async () => {
    const c = await repo.children.save(childInput()); const s = await repo.sessions.start(c.id);
    for (let n=0;n<7;n++) await repo.sessions.saveAnswer(s.id,n,tasks[n].options[0].id);
    vi.spyOn(db.sessions,'put').mockRejectedValueOnce(new Error('Ошибка завершения'));
    await expect(repo.sessions.complete(s.id)).rejects.toThrow();
    let snap = await repo.demo.load(); expect(snap.answers).toHaveLength(7); expect(snap.results).toHaveLength(0); expect(snap.sessions[0].status).toBe('in_progress');
    const [a,b] = await Promise.all([repo.sessions.complete(s.id),repo.sessions.complete(s.id)]); expect(a.id).toBe(b.id);
    snap = await repo.demo.load(); expect(snap.results).toHaveLength(1); expect(snap.sessions[0].status).toBe('completed');
    const again = await repo.sessions.complete(s.id); expect(again).toEqual(a);
    const next = await repo.sessions.start(c.id,true); expect(next.id).not.toBe(s.id); expect((await repo.demo.load()).sessions).toHaveLength(2);
  });
  it('имеют заменяемый асинхронный engine; фиксированный пример не зависит от ответов', async () => {
    const c = await repo.children.save(childInput()); const s = await repo.sessions.start(c.id);
    const first = await demoAssessmentEngine.evaluate(s,[]); const second = await demoAssessmentEngine.evaluate(s,[{ id:'a', schemaVersion:1, createdAt:'', answeredAt:'', taskId:'x', taskVersion:'1', sessionId:s.id, selectedOptionId:'other', revision:1 }]); expect(first).toEqual(second);
    const engine = { evaluate: vi.fn(demoAssessmentEngine.evaluate) }; const injected = createLocalRepositories(db,engine);
    for(let n=0;n<7;n++) await injected.sessions.saveAnswer(s.id,n,tasks[n].options[0].id);
    await injected.sessions.complete(s.id); expect(engine.evaluate).toHaveBeenCalledOnce(); expect(engine.evaluate.mock.calls[0][1]).toHaveLength(7);
  });
  it('не создают дубль заявки при одновременных запросах и после перезагрузки', async () => {
    const a = await repo.children.save(childInput()); const b = await repo.children.save({...childInput(),displayName:'Другой'});
    const [x,y] = await Promise.all([repo.applications.save(a.id,'art'),repo.applications.save(a.id,'art')]); expect(x.id).toBe(y.id);
    expect((await createLocalRepositories(db).applications.save(a.id,'art')).id).toBe(x.id);
    await repo.applications.save(b.id,'art'); expect((await repo.demo.load()).applications).toHaveLength(2);
    await expect(repo.applications.save('missing','art')).rejects.toThrow(); await expect(repo.applications.save(a.id,'missing')).rejects.toThrow();
    const young = await repo.children.save({...childInput(),ageYears:5}); await expect(repo.applications.save(young.id,'bots')).rejects.toThrow('возраста');
    const s = await repo.sessions.start(a.id); await finish(s.id); await expect(repo.applications.save(b.id,'bots',s.id)).rejects.toThrow('ребёнку');
  });
  it('повторяют заявку после ошибки и атомарно сбрасывают все пользовательские таблицы', async () => {
    const c = await repo.children.save(childInput()); const s = await repo.sessions.start(c.id); await finish(s.id); await repo.demo.enter();
    vi.spyOn(db.applications,'add').mockRejectedValueOnce(new Error('Ошибка записи'));
    await expect(repo.applications.save(c.id,'art')).rejects.toThrow(); expect((await repo.demo.load()).applications).toHaveLength(0);
    await repo.applications.save(c.id,'art');
    vi.spyOn(db.tables.find(t=>t.name==='answers')!,'clear').mockRejectedValueOnce(new Error('Ошибка очистки'));
    await expect(repo.demo.reset()).rejects.toThrow(); expect((await repo.demo.load()).children).toHaveLength(1);
    await repo.demo.reset(); const snap = await repo.demo.load();
    expect(snap).toMatchObject({ children:[], sessions:[], answers:[], results:[], applications:[], settings:{entered:false} }); expect(programs).toHaveLength(8);
  });
  it('не воскрешают удалённые данные, пока асинхронный engine ожидал', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof demoAssessmentEngine.evaluate>>) => void;
    const slow = createLocalRepositories(db,{ evaluate: () => new Promise(r => {resolve=r;}) });
    const c = await repo.children.save(childInput()); const s = await repo.sessions.start(c.id);
    for(let n=0;n<7;n++) await repo.sessions.saveAnswer(s.id,n,tasks[n].options[0].id);
    const pending = slow.sessions.complete(s.id); while(!resolve) await new Promise(r=>setTimeout(r,0));
    await repo.demo.reset(); resolve(await demoAssessmentEngine.evaluate(s,[])); await expect(pending).rejects.toThrow(); expect((await repo.demo.load()).results).toHaveLength(0);
  });
  it('валидация не допускает некорректные профили', async () => {
    await expect(repo.children.save({...childInput(),displayName:'  '})).rejects.toThrow();
    await expect(repo.children.save({...childInput(),ageYears:4})).rejects.toThrow();
    await expect(repo.children.save({...childInput(),ageYears:8.5})).rejects.toThrow();
    await expect(repo.children.save(childInput(),'missing')).rejects.toThrow();
  });
});
describe('правила подбора', () => {
  it('учитывают возрастные границы, сортируют совпадения и объясняют возрастные варианты', () => {
    const list = recommendationEngine.recommend(childInput(),programs); expect(list[0].program.id).toBe('art');
    expect(list.find(r=>r.program.id==='music')?.reason).toContain('Совпадений');
    expect(recommendationEngine.recommend({...childInput(),ageYears:5},programs).some(r=>r.program.id==='bots')).toBe(false);
    expect(recommendationEngine.recommend({...childInput(),ageYears:7},programs).some(r=>r.program.id==='bots')).toBe(true);
    expect(recommendationEngine.recommend({...childInput(),ageYears:12},programs).some(r=>r.program.id==='art')).toBe(true);
    expect(recommendationEngine.recommend({...childInput(),ageYears:13},programs)).toEqual([]);
    expect(recommendationEngine.recommend({...childInput(),interests:[]},programs).map(r=>r.program.id)).toEqual(programs.filter(p=>p.minAge<=8&&p.maxAge>=8).map(p=>p.id).sort());
  });
});
