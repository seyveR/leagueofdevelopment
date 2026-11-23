import {test,expect} from './local-browser';

test('смена детей обновляет название, описание и запуск возрастного набора',async({page})=>{
  const auth=await (await page.request.get('/api/auth/session')).json();
  const registration=await page.request.post('/api/auth/register',{headers:{'X-CSRF-Token':auth.csrf},data:{email:`switch-${crypto.randomUUID()}@example.com`,password:'switch-parent-password'}});
  expect(registration.ok()).toBe(true);const user=await registration.json();const headers={'X-CSRF-Token':user.csrf};
  const order=await (await page.request.post('/api/payments/orders',{headers,data:{plan_id:'premium',request_id:crypto.randomUUID()}})).json();
  expect((await page.request.post('/api/payments/orders/'+order.id+'/simulate-confirm',{headers})).ok()).toBe(true);
  const consent=await (await page.request.get('/api/consent')).json();
  const cases=[{age:5,name:'Олег',title:'Первые открытия',text:'Рисуй, запоминай картинки'}, {age:9,name:'Иван',title:'Мир исследователя',text:'Собирай модели и истории'}, {age:13,name:'Алиса',title:'Лаборатория идей',text:'Решай задачи с фигурами и числами'}, {age:17,name:'Артём',title:'Маршрут возможностей',text:'Ищи закономерности'}];
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
  await expect(page.getByRole('button',{name:/Продолжить · 0 из 10/})).toBeVisible();
});

test('возрастной путь: все механики, восстановление, ошибка сохранения и заявка',async({page})=>{
  await page.goto('/login');await page.getByRole('button',{name:'Создать учётную запись'}).click();
  await page.getByLabel('Email',{exact:true}).fill(`journey-${crypto.randomUUID()}@example.com`);
  await page.getByLabel('Пароль',{exact:true}).fill('journey-parent-password');await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.goto('/children/new');await page.getByLabel('Имя',{exact:true}).fill('Миша');const age=page.getByLabel('Возраст',{exact:true});await age.fill('0');await age.press('End');await age.pressSequentially('7');await expect(age).toHaveValue('7');await age.pressSequentially('5');await expect(age).toHaveValue('75');await age.press('Backspace');await age.press('Backspace');await expect(age).toHaveValue('0');await age.fill('5');await page.getByRole('checkbox',{name:'Подтверждаю согласие'}).check();await page.getByRole('button',{name:'Сохранить профиль'}).click();await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.goto('/tests');await expect(page.getByText('Версия 0.4.0',{exact:true})).toHaveCount(0);await expect(page.getByRole('img',{name:'Логотип Лиги развития'})).toBeVisible();await expect(page.getByText('4–7 лет · 10 заданий',{exact:true})).toBeVisible();await expect(page.locator('.app-navigation')).toHaveAttribute('data-icon-theme','playful');await expect(page.locator('.app-navigation a.active .nav-icon')).toHaveCSS('background-color','rgba(0, 0, 0, 0)');
  await page.getByRole('button',{name:'Начать прохождение',exact:true}).click();await page.getByRole('link',{name:'Начать прохождение',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Выбери до трёх идей/})).toBeVisible();
  const save=()=>page.getByRole('button',{name:'Сохранить и дальше',exact:true}).click();
  await page.getByRole('button',{name:'🏠 Домик из коробки',exact:true}).click();
  // A failed save must leave the selected action and current step intact.
  await page.route('**/api/journey/*/answers',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Не удалось сохранить ответ. Повторите попытку.'})}),{times:1});
  await save();await expect(page.getByRole('alert')).toContainText('Не удалось сохранить');await expect(page.getByRole('button',{name:'🏠 Домик из коробки',exact:true})).toHaveAttribute('aria-pressed','true');await save();
  await expect(page.getByRole('heading',{name:/Дорисуй фигуру/})).toBeVisible();await page.reload();await expect(page.getByRole('heading',{name:/Дорисуй фигуру/})).toBeVisible();
  const board=page.locator('.drawing-board');const bounds=(await board.boundingBox())!;await page.mouse.move(bounds.x+80,bounds.y+80);await page.mouse.down();await page.mouse.move(bounds.x+140,bounds.y+130,{steps:8});await page.mouse.up();
  await page.getByRole('button',{name:'🎨 Украшение или картина',exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Идёт дождь/})).toBeVisible();
  for(let i=0;i<4;i++)await page.locator('.sort-card').nth(i).getByRole('button').nth(i%2).click();await save();
  await expect(page.getByRole('heading',{name:/Как достать мяч/})).toBeVisible();await page.getByRole('button',{name:/Взять длинную щётку/}).click();await page.getByRole('button',{name:/Осторожно выкатить мяч/}).click();await save();
  await expect(page.getByRole('heading',{name:/Что здесь лишнее/})).toBeVisible();await page.getByRole('button',{name:'🚗 Машина',exact:true}).click();await page.getByRole('button',{name:'Три предмета — фрукты',exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Что будет дальше/})).toBeVisible();for(let i=0;i<3;i++)await page.locator('fieldset').nth(i).getByRole('button').first().click();await save();
  await expect(page.locator('.memory-material')).toBeVisible();await page.getByRole('button',{name:'Скрыть и ответить'}).click();await expect(page.getByRole('heading',{name:'Выбери картинки, которые ты запомнил.',exact:true})).toBeVisible();await page.reload();await expect(page.locator('.memory-material')).toHaveCount(0);await expect(page.getByRole('heading',{name:'Выбери картинки, которые ты запомнил.',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'🍎',exact:true}).click();await page.getByRole('button',{name:'🚲',exact:true}).click();await page.getByRole('button',{name:'🌳',exact:true}).click();await save();
  await expect(page.locator('.target-grid')).toBeVisible();await expect(page.locator('.journey-activity h1 svg path')).toHaveAttribute('fill','#f4b938');await expect(page.locator('.target-grid button').filter({hasText:'★'}).first().locator('svg path')).toHaveAttribute('fill','#f4b938');for(const b of await page.locator('.target-grid button').all())if((await b.textContent())==='★')await b.click();await page.screenshot({path:'test-results/journey-attention-390.png',fullPage:true});await save();
  await expect(page.locator('.route-board')).toBeVisible();for(const dir of ['Вправо','Вверх','Вправо'])await page.getByRole('button',{name:dir,exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Что было сначала/})).toBeVisible();for(const text of ['🌱 Посадили семечко','💧 Полили землю','🌿 Появился росток','🌻 Распустился цветок'])await page.getByRole('button',{name:text,exact:true}).click();await save();
  await page.getByRole('button',{name:'Посмотреть результат',exact:true}).click();await expect(page.getByRole('heading',{name:'Выполнено 10 из 10',exact:true})).toBeVisible();
  for(const width of [360,430,1280]){await page.setViewportSize({width,height:932});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.setViewportSize({width:430,height:932});await page.screenshot({path:'test-results/journey-result-430.png',fullPage:true});
  await expect(page.getByRole('heading',{name:'Какие занятия попробовать'})).toBeVisible();await expect(page.locator('.main').getByText(/не вывод|не оценка|Это повод/)).toHaveCount(0);await page.goto('/programs');await expect(page.getByRole('heading',{name:'Кружки',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Кружки',exact:true})).toHaveCSS('outline-style','none');expect(await page.locator('input:not([type=checkbox]):not([type=radio]),select,textarea').evaluateAll(nodes=>nodes.every(n=>parseFloat(getComputedStyle(n).fontSize)>=16))).toBe(true);await page.goBack();await page.getByRole('link',{name:'Подобрать кружки',exact:true}).click();await expect(page.getByRole('heading',{name:'Рекомендации кружков'})).toBeVisible();await page.getByRole('button',{name:'Связаться с кружком',exact:true}).first().click();
  await expect(page.getByRole('heading',{name:'Запись на пробное занятие'})).toBeVisible();
  await page.getByLabel('Время',{exact:false}).selectOption({index:1});await page.getByRole('checkbox',{name:/Разрешаю передать/}).check();await page.getByRole('button',{name:'Оставить заявку',exact:true}).click();await expect(page.getByText('Заявка отправлена организации. Статус доступен в разделе «Мои заявки».',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:/Мои заявки и занятия/}).click();await expect(page.getByText('Новая заявка',{exact:true})).toBeVisible();await page.reload();await expect(page.getByText('Новая заявка',{exact:true})).toBeVisible();
  await expect(page.locator('.booking-contacts').getByText('Адрес кружка',{exact:true})).toBeVisible();await expect(page.locator('.booking-contacts a[href^="tel:"]')).toBeVisible();await expect(page.getByRole('link',{name:'Открыть адрес на карте ↗',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.querySelectorAll('audio').length)).toBe(0);const state=await (await page.request.get('/api/state')).json();for(const [age,theme] of [[8,'colorful'],[11,'soft'],[15,'minimal']] as const){await page.goto('/children/'+state.children[0].id+'/edit');await page.getByLabel('Возраст',{exact:true}).fill(String(age));await page.getByRole('button',{name:'Сохранить профиль'}).click();await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();await expect(page.locator('.app-navigation')).toHaveAttribute('data-icon-theme',theme);await expect(page.locator('.app-navigation a.active .nav-icon')).toHaveCSS('background-color','rgba(0, 0, 0, 0)');await page.screenshot({path:'test-results/nav-'+theme+'.png',fullPage:true});}
});
