import { afterEach, expect, it, vi } from 'vitest';
import { entityId } from './id';
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
it('создаёт UUID v4 при отсутствии randomUUID на сетевом HTTP-адресе',()=>{
  vi.stubGlobal('crypto',{getRandomValues:crypto.getRandomValues.bind(crypto)});
  const a=entityId(),b=entityId();expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);expect(a).not.toBe(b);
});
