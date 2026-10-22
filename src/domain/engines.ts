import type { Answer, AssessmentResult, ChildInput, Program, Session } from './models';
export interface AssessmentEngine {
  evaluate(session: Session, answers: Answer[]): Promise<Omit<AssessmentResult, 'id' | 'schemaVersion' | 'createdAt'>>;
}
export const demoAssessmentEngine: AssessmentEngine = {
  async evaluate(session) {
    return { sessionId: session.id, engineId: 'fixed-example', engineVersion: '1.0.0', mode: 'demo', fixtureVersion: '1.0.0', demoProfile: [
      { title: 'Придумывать и создавать', description: 'Пример направления: рисунки, поделки, собственные истории.', isIllustrative: true },
      { title: 'Исследовать мир', description: 'Пример направления: наблюдения, вопросы и маленькие эксперименты.', isIllustrative: true },
      { title: 'Пробовать вместе', description: 'Пример направления: музыка, движение и совместные проекты.', isIllustrative: true },
    ] };
  },
};
export interface RecommendationEngine { recommend(child: ChildInput, catalog: Program[]): { program: Program; reason: string; rulesVersion: string }[] }
export const recommendationEngine: RecommendationEngine = {
  recommend(child, catalog) {
    return catalog.filter(p => child.ageYears >= p.minAge && child.ageYears <= p.maxAge)
      .map(program => { const matches = program.tags.filter(tag => child.interests.includes(tag)); return { program, matches, reason: matches.length ? `Подходит по возрасту и интересам: ${matches.join(', ').toLowerCase()}.` : 'Подходит по возрасту. Совпадений с выбранными интересами нет.', rulesVersion: 'age-interests-1.0.0' }; })
      .sort((a, b) => b.matches.length - a.matches.length || a.program.id.localeCompare(b.program.id));
  },
};
