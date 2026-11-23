import {test,expect,type Page} from './local-browser';

async function setup(page:Page,ages:number[]){
  const csrf=await (await page.request.get('/api/auth/session')).json();
  const registered=await page.request.post('/api/auth/register',{headers:{'X-CSRF-Token':csrf.csrf},data:{email:`balanced-${crypto.randomUUID()}@example.com`,password:'balanced-parent-password'}});
  expect(registered.ok()).toBe(true);const auth=await registered.json();const headers={'X-CSRF-Token':auth.csrf};
  if(ages.length>1){const order=await (await page.request.post('/api/payments/orders',{headers,data:{plan_id:'premium',request_id:crypto.randomUUID()}})).json();expect((await page.request.post('/api/payments/orders/'+order.id+'/simulate-confirm',{headers})).ok()).toBe(true);}
  const consent=await (await page.request.get('/api/consent')).json();const children=[];
  for(const age of ages){const r=await page.request.post('/api/children',{headers,data:{name:'Ребёнок '+age,age,city:'Архангельск',gender:'unspecified',interests:[],consent:true,consent_version:consent.version}});expect(r.ok()).toBe(true);children.push(await r.json());}
  return {children,headers};
}

test('20 заданий: продолжение, основное спортивное направление и согласованные кружки',async({page})=>{
  await setup(page,[5]);await page.goto('/tests');await expect(page.getByText('4–7 лет · 20 заданий',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Начать прохождение',exact:true}).click();await expect(page).toHaveURL(/\/intro$/);await page.getByRole('link',{name:'Начать прохождение',exact:true}).click();await expect(page).toHaveURL(/\/tasks$/);
  const id=page.url().split('/')[4];
  for(let n=0;n<20;n++){
    await expect(page.getByText(`Ребёнок 5 · Задание ${n+1} из 20`,{exact:true})).toBeVisible();
    if(n===13){await page.reload();await expect(page.getByText('Ребёнок 5 · Задание 14 из 20',{exact:true})).toBeVisible();}
    const detail=await (await page.request.get('/api/journey/'+id)).json();const t=detail.task;const sport=t.id.includes('-sport-');
    if(t.mechanic==='order'){
      const ids=t.config.choices.map((c:{id:string})=>c.id).sort((a:string,b:string)=>Number(a)-Number(b));if(!sport)ids.reverse();
      for(const choice of ids)await page.locator(`[data-choice-id="${choice}"]`).click();
    }else await page.locator(`[data-choice-id="${t.mechanic==='preference'?(sport?'0':'2'):(sport?'0':'1')}"]`).click();
    await page.getByRole('button',{name:'Сохранить и дальше',exact:true}).click();
  }
  await page.getByRole('button',{name:'Посмотреть результат',exact:true}).click();await expect(page.getByRole('heading',{name:'Выполнено 20 из 20',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Спорт и движение',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Можно попробовать',exact:true})).toHaveCount(0);
  await page.screenshot({path:'test-results/balanced-sport-result.png',fullPage:true});
  await page.getByRole('link',{name:'Подобрать кружки',exact:true}).click();await expect(page.getByRole('heading',{name:/Лёгкая атлетика/})).toBeVisible();await expect(page.getByRole('heading',{name:/робототехника|Подготовка к школе/i})).toHaveCount(0);
});

test('запись в старшую программу блокирует младшего ребёнка в интерфейсе и API',async({page})=>{
  const {children,headers}=await setup(page,[5,17]);
  const programs=await (await page.request.get('/api/market/programs?age=17')).json();const program=programs.find((p:{name:string})=>p.name==='Биотехнология');expect(program).toBeTruthy();
  await page.goto('/programs/'+program.id);await expect(page.getByRole('heading',{name:'Биотехнология',exact:true})).toBeVisible();
  await expect(page.locator(`select option[value="${children[0].id}"]`).last()).toHaveAttribute('disabled','');
  await page.getByLabel('Ребёнок',{exact:false}).evaluate((element,id)=>{(element as HTMLSelectElement).value=id;element.dispatchEvent(new Event('change',{bubbles:true}));},children[0].id);await page.getByLabel('Время',{exact:false}).selectOption({index:1});await page.getByRole('checkbox',{name:/Разрешаю передать/}).check();await expect(page.getByRole('button',{name:'Оставить заявку',exact:true})).toBeDisabled();
  const detail=await (await page.request.get('/api/market/programs/'+program.id)).json();
  const rejected=await page.request.post('/api/bookings',{headers,data:{child_id:children[0].id,slot_id:detail.slots[0].id,request_id:crypto.randomUUID(),contact:'parent@example.com',consent:true}});expect(rejected.status()).toBe(422);
  await page.getByLabel('Ребёнок',{exact:false}).selectOption(children[1].id);await expect(page.getByRole('button',{name:'Оставить заявку',exact:true})).toBeEnabled();
});
