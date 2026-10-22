import { expect, test, type Page } from '@playwright/test';
async function enter(page: Page) { await page.goto('/'); await expect(page.getByText('Версия 0.1.0',{exact:true})).toBeVisible(); await expect(page.locator('body')).not.toContainText(/демо|демонстраци/i); await page.getByRole('button', {name:'Начать'}).click(); await expect(page.getByRole('heading', {name:'Главная'})).toBeVisible(); }
async function addChild(page: Page, name: string, age: number) { await page.goto('/children/new'); await page.getByRole('textbox',{name:'Имя или псевдоним'}).fill(name); await page.getByRole('combobox',{name:'Возраст',exact:true}).selectOption(String(age)); await page.getByRole('checkbox',{name:'Творчество',exact:true}).check(); await page.getByRole('button', {name:'Сохранить профиль'}).click(); await expect(page.getByRole('heading',{name:'Главная'})).toBeVisible(); }
async function start(page: Page) { await page.getByRole('button', {name:'Начать задания'}).click(); await page.getByRole('link',{name:'Начать прохождение'}).click(); }
async function answer(page: Page) { await page.getByRole('radio').first().check(); await page.getByRole('button',{name:'Сохранить и дальше'}).click(); }
test('основной путь, восстановление, разделение детей, заявки и сброс', async ({page}) => {
  const external: string[] = []; page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:5173')&&!r.url().startsWith('data:'))external.push(r.url());});
  await enter(page); await addChild(page,'Лисёнок',8); await start(page);
  await expect(page.getByRole('button',{name:'Сохранить и дальше'})).toBeDisabled();
  await answer(page); await expect(page.getByText('Задание 2 из 7')).toBeVisible(); const resumeUrl=page.url();
  await page.reload(); await expect(page.getByText('Задание 2 из 7')).toBeVisible();
  await page.goto(resumeUrl.replace('/tasks/1','/result')); await expect(page.getByText('Задание 2 из 7')).toBeVisible();
  await page.getByRole('link',{name:'Выйти и продолжить позже'}).click(); await addChild(page,'Звёздочка',6); await start(page);
  await expect(page.getByText('Задание 1 из 7')).toBeVisible(); await answer(page);
  await page.getByRole('link',{name:'Выйти и продолжить позже'}).click(); await page.getByRole('combobox',{name:'Активный ребёнок'}).selectOption({label:'Лисёнок · 8 лет'});
  await page.getByRole('link',{name:'Продолжить прохождение'}).click(); await expect(page.getByText('Задание 2 из 7')).toBeVisible();
  for(let n=1;n<7;n++) { await expect(page.getByText(`Задание ${n+1} из 7`)).toBeVisible(); await answer(page); }
  await page.getByRole('button',{name:'Посмотреть результаты'}).click(); await expect(page.getByRole('heading',{name:'Выполнено 7 из 7 заданий'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Как может выглядеть профиль'})).toHaveCount(0); await expect(page.locator('body')).not.toContainText(/демо|демонстраци/i); await page.getByText('Сохранённые ответы',{exact:true}).click(); await expect(page.getByText('● Круг',{exact:true})).toBeVisible();
  await page.reload(); await expect(page.getByRole('heading',{name:'Выполнено 7 из 7 заданий'})).toBeVisible();
  await page.getByRole('link',{name:'Посмотреть кружки'}).click(); await expect(page.locator('body')).not.toContainText(/демо|демонстраци/i);
  await page.getByRole('combobox',{name:'Активный ребёнок'}).selectOption({label:'Звёздочка · 6 лет'}); await expect(page.getByText('Для Звёздочка · 6 лет',{exact:true})).toBeVisible();
  await page.getByRole('combobox',{name:'Активный ребёнок'}).selectOption({label:'Лисёнок · 8 лет'}); await expect(page.getByText('Для Лисёнок · 8 лет',{exact:true})).toBeVisible();
  await page.getByRole('link').filter({has:page.getByRole('heading',{name:'Цветная мастерская',exact:true})}).click(); await page.getByRole('link',{name:'Оставить заявку'}).click();
  await page.getByRole('checkbox').check(); await page.getByRole('button',{name:'Сохранить заявку'}).dblclick(); await expect(page.getByRole('heading',{name:'Заявка сохранена',exact:true})).toBeVisible();
  await expect(page.getByText('не отправлена организации',{exact:false})).toBeVisible(); await page.reload(); await expect(page.getByRole('heading',{name:'Заявка сохранена',exact:true})).toBeVisible();
  await page.goto('/applications/new?programId=art'); await expect(page.getByText('Для этого ребёнка заявка на эту программу уже сохранена.')).toBeVisible();
  await page.goto('/profile'); await expect(page.locator('.history-row')).toHaveCount(1); await page.getByRole('combobox',{name:'Заявки ребёнка'}).selectOption({label:'Звёздочка'}); await expect(page.locator('.history-row')).toHaveCount(0);
  await page.getByRole('button',{name:'Сбросить данные'}).click(); await page.getByRole('button',{name:'Отмена',exact:true}).click(); await expect(page.getByRole('heading',{name:'Дети',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Сбросить данные'}).click(); await page.getByRole('button',{name:'Да, удалить все данные'}).click(); await expect(page.getByRole('button',{name:'Начать'})).toBeVisible();
  await page.reload(); await page.getByRole('button',{name:'Начать'}).click(); await expect(page.getByRole('heading',{name:'Нет профилей детей'})).toBeVisible();
  // Host antivirus injects its own script into HTTP pages. This exact host is
  // outside the application; all other external requests still fail the test.
  expect(external.filter(url=>new URL(url).hostname!=='me.kis.v2.scr.kaspersky-labs.com')).toEqual([]);
});
test('ошибка сохранения блокирует переход и разрешает повтор',async ({page})=>{
  await enter(page); await addChild(page,'Проверка',8); await start(page);
  await page.evaluate(()=>{const original=IDBObjectStore.prototype.put; let failed=false; IDBObjectStore.prototype.put=function(...args: Parameters<IDBObjectStore['put']>){if(this.name==='sessions'&&!failed){failed=true;throw new DOMException('Тестовая ошибка','QuotaExceededError');}return original.apply(this,args);};});
  await answer(page); await expect(page.getByRole('alert')).toBeVisible(); await expect(page.getByText('Задание 1 из 7')).toBeVisible(); await expect(page.getByRole('radio').first()).toBeChecked();
  await page.getByRole('button',{name:'Сохранить и дальше'}).click(); await expect(page.getByText('Задание 2 из 7')).toBeVisible(); await page.reload(); await expect(page.getByText('Задание 2 из 7')).toBeVisible();
});
test('ошибка заявки сохраняет форму; повтор не дублирует запись',async ({page})=>{
  await enter(page); await addChild(page,'Проверка',8); await page.goto('/applications/new?programId=art'); await page.getByRole('checkbox').check();
  await page.evaluate(()=>{const original=IDBObjectStore.prototype.add;let failed=false;IDBObjectStore.prototype.add=function(...args:Parameters<IDBObjectStore['add']>){if(this.name==='applications'&&!failed){failed=true;throw new DOMException('Тестовая ошибка','QuotaExceededError');}return original.apply(this,args);};});
  await page.getByRole('button',{name:'Сохранить заявку'}).click(); await expect(page.getByRole('alert')).toBeVisible(); await expect(page.getByRole('checkbox')).toBeChecked();
  await page.getByRole('button',{name:'Сохранить заявку'}).click(); await expect(page.getByRole('heading',{name:'Заявка сохранена',exact:true})).toBeVisible();
  await page.goto('/profile'); await expect(page.locator('.history-row')).toHaveCount(1);
});
test('недоступное хранилище имеет понятный экран и повтор',async ({page})=>{
  await page.addInitScript(()=>{IDBFactory.prototype.open=function(){throw new DOMException('Тестовый запрет','SecurityError');};});
  await page.goto('/'); await expect(page.getByRole('heading',{name:'Хранилище недоступно'})).toBeVisible(); await expect(page.getByRole('button',{name:'Повторить загрузку'})).toBeVisible();
});
test('сбой завершения сохраняет семь ответов; сбой сброса не удаляет часть данных',async ({page})=>{
  await enter(page);await addChild(page,'Лисёнок',8);await start(page);
  for(let n=0;n<7;n++){await expect(page.getByText(`Задание ${n+1} из 7`)).toBeVisible();await answer(page);}
  await page.evaluate(()=>{const original=IDBObjectStore.prototype.add;let failed=false;IDBObjectStore.prototype.add=function(...args:Parameters<IDBObjectStore['add']>){if(this.name==='results'&&!failed){failed=true;throw new DOMException('Сбой завершения','QuotaExceededError');}return original.apply(this,args);};});
  await page.getByRole('button',{name:'Посмотреть результаты'}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('heading',{name:'Задания завершены'})).toBeVisible();
  await page.reload();await expect(page.getByRole('heading',{name:'Задания завершены'})).toBeVisible();await page.getByRole('button',{name:'Посмотреть результаты'}).click();await expect(page.getByRole('heading',{name:'Выполнено 7 из 7 заданий'})).toBeVisible();
  await page.goto('/profile');await page.evaluate(()=>{const original=IDBObjectStore.prototype.clear;let failed=false;IDBObjectStore.prototype.clear=function(){if(this.name==='answers'&&!failed){failed=true;throw new DOMException('Сбой сброса','UnknownError');}return original.call(this);};});
  await page.getByRole('button',{name:'Сбросить данные'}).click();await page.getByRole('button',{name:'Да, удалить все данные'}).click();await expect(page.getByRole('alert')).toBeVisible();
  await page.reload();await expect(page.getByRole('heading',{name:'Лисёнок · 8 лет'})).toBeVisible();await page.getByRole('button',{name:'Сбросить данные'}).click();await page.getByRole('button',{name:'Да, удалить все данные'}).click();await expect(page.getByRole('button',{name:'Начать'})).toBeVisible();
});
test('редактирование, пустой фильтр, неизвестная ссылка, мобильные ширины и компьютер',async ({page})=>{
  await enter(page); await addChild(page,'Очень длинный вымышленный псевдоним',5); await page.getByRole('link',{name:'Редактировать профиль'}).click(); await page.getByLabel('Имя или псевдоним').fill('Лисёнок'); await page.getByRole('button',{name:'Сохранить профиль'}).click();
  await page.goto('/programs'); await page.getByRole('combobox',{name:'Направление кружков'}).selectOption('Истории'); await expect(page.getByRole('heading',{name:'Пока нет подходящих программ'})).toBeVisible(); await page.getByRole('button',{name:'Показать все направления'}).click();
  await page.goto('/applications/new?programId=bots'); await expect(page.getByText('Возраст ребёнка не подходит.',{exact:false})).toBeVisible(); await expect(page.getByRole('button',{name:'Сохранить заявку'})).toBeDisabled();
  for(const path of ['/home','/programs','/profile','/children/new','/programs/art','/applications/new?programId=art'])for(const width of [360,390,430,1280]) { await page.setViewportSize({width,height:844});await page.goto(path); await expect(page.locator('h1')).toBeVisible(); await expect(page.locator('body')).not.toContainText(/демо|демонстраци/i); expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${path} at ${width}`).toBe(true); }
  await page.goto('/unknown'); await expect(page.getByRole('heading',{name:'Страница не найдена'})).toBeVisible(); await page.getByRole('link',{name:'Вернуться на главную'}).click(); await expect(page.getByRole('heading',{name:'Главная'})).toBeVisible();
});
test('визуальные снимки и управление заданиями с клавиатуры',async ({page})=>{
  await page.goto('/'); await expect(page.getByRole('button',{name:'Начать'})).toBeVisible();
  for(const width of [360,390,430]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/visual/welcome-390.png',fullPage:true});
  await page.setViewportSize({width:1280,height:900}); await page.screenshot({path:'test-results/visual/welcome-desktop.png',fullPage:true});
  await page.setViewportSize({width:360,height:800}); await enter(page); await addChild(page,'Лисёнок',8);
  await page.screenshot({path:'test-results/visual/home-360.png',fullPage:true}); await start(page);
  const radio=page.getByRole('radio').first(); await radio.focus(); await page.keyboard.press('Space'); await expect(radio).toBeChecked(); await page.keyboard.press('Tab'); await expect(page.getByRole('button',{name:'Сохранить и дальше'})).toBeFocused();
  await page.screenshot({path:'test-results/visual/task-360.png',fullPage:true});
  for(const width of [360,390,430]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.keyboard.press('Enter'); await expect(page.getByText('Задание 2 из 7')).toBeVisible();
  await page.goto('/programs'); await page.screenshot({path:'test-results/visual/catalog-430.png',fullPage:true});
});


