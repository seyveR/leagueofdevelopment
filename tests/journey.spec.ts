import {test,expect} from './local-browser';

test('смена детей обновляет название, описание и запуск возрастного набора',async({page})=>{
  const auth=await (await page.request.get('/api/auth/session')).json();
  const registration=await page.request.post('/api/auth/register',{headers:{'X-CSRF-Token':auth.csrf},data:{email:`switch-${crypto.randomUUID()}@example.com`,password:'switch-parent-password'}});
  expect(registration.ok()).toBe(true);const user=await registration.json();const headers={'X-CSRF-Token':user.csrf};
  const order=await (await page.request.post('/api/payments/orders',{headers,data:{plan_id:'premium',request_id:crypto.randomUUID()}})).json();
  expect((await page.request.post('/api/payments/orders/'+order.id+'/simulate-confirm',{headers})).ok()).toBe(true);
  const consent=await (await page.request.get('/api/consent')).json();
  const cases=[{age:5,name:'Олег',title:'Первые открытия',text:'Играй с картинками'}, {age:9,name:'Иван',title:'Мир исследователя',text:'Собирай планы и истории'}, {age:13,name:'Алиса',title:'Лаборатория идей',text:'Решай задачи с фигурами и числами'}, {age:17,name:'Артём',title:'Маршрут возможностей',text:'Ищи закономерности'}];
  const ids:string[]=[];
  for(const c of cases){const response=await page.request.post('/api/children',{headers,data:{name:c.name,age:c.age,city:'Архангельск',gender:'unspecified',interests:[],consent:true,consent_version:consent.version}});expect(response.ok()).toBe(true);ids.push((await response.json()).id);}
  await page.goto('/tests');const setIds=new Set<string>();
  for(let i=0;i<cases.length;i++){
    await page.getByLabel('Активный ребёнок').selectOption(ids[i]);
    await expect(page.locator('.journey-intro h2')).toHaveText(cases[i].title);
    await expect(page.locator('.journey-intro')).toContainText(cases[i].text);
    await page.getByRole('button',{name:'Начать прохождение',exact:true}).click();
    await expect(page).toHaveURL(/\/sessions\/[^/]+\/intro$/);await expect(page.getByRole('heading',{name:cases[i].title,exact:true})).toBeVisible();
    const state=await (await page.request.get('/api/state')).json();const session=state.sessions.find((s:{child_id:string})=>s.child_id===ids[i]);expect(session).toBeTruthy();setIds.add(session.task_set_id);
    await page.goto('/tests');
  }
  expect(setIds.size).toBe(4);
  for(const i of [3,0,2,1,2])await page.getByLabel('Активный ребёнок').selectOption(ids[i]);
  await expect(page.locator('.journey-intro h2')).toHaveText(cases[2].title);
  await expect(page.locator('.journey-intro')).toContainText(cases[2].text);
  await expect(page.getByRole('button',{name:/Продолжить · 0 из 40/})).toBeVisible();
});
