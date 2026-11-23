import {test,expect} from './local-browser';

test('возрастной путь: все механики, восстановление, ошибка сохранения и заявка',async({page})=>{
  await page.goto('/login');await page.getByRole('button',{name:'Создать учётную запись'}).click();
  await page.getByLabel('Email',{exact:true}).fill(`journey-${crypto.randomUUID()}@example.com`);
  await page.getByLabel('Пароль',{exact:true}).fill('journey-parent-password');await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();
  await page.goto('/children/new');await page.getByLabel('Имя',{exact:true}).fill('Миша');await page.getByLabel('Возраст',{exact:true}).fill('5');await page.getByRole('checkbox',{name:'Подтверждаю согласие'}).check();await page.getByRole('button',{name:'Сохранить профиль'}).click();
  await page.goto('/tests');await expect(page.getByText('4–7 лет · 10 заданий',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Начать прохождение',exact:true}).click();await page.getByRole('link',{name:'Начать прохождение',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Коробка превращается/})).toBeVisible();
  const save=()=>page.getByRole('button',{name:'Сохранить и дальше',exact:true}).click();
  await page.getByRole('button',{name:'🏠 Домик из коробки',exact:true}).click();
  // A failed save must leave the selected action and current step intact.
  await page.route('**/api/journey/*/answers',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Не удалось сохранить ответ. Повторите попытку.'})}),{times:1});
  await save();await expect(page.getByRole('alert')).toContainText('Не удалось сохранить');await expect(page.getByRole('button',{name:'🏠 Домик из коробки',exact:true})).toHaveAttribute('aria-pressed','true');await save();
  await expect(page.getByRole('heading',{name:/Преврати круг/})).toBeVisible();await page.reload();await expect(page.getByRole('heading',{name:/Преврати круг/})).toBeVisible();
  const board=page.locator('.drawing-board');const bounds=(await board.boundingBox())!;await page.mouse.move(bounds.x+80,bounds.y+80);await page.mouse.down();await page.mouse.move(bounds.x+140,bounds.y+130,{steps:8});await page.mouse.up();
  await page.getByRole('button',{name:'🎨 Украшение или картина',exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Пошёл дождь/})).toBeVisible();
  for(let i=0;i<4;i++)await page.locator('.sort-card').nth(i).getByRole('button').nth(i%2).click();await save();
  await expect(page.getByRole('heading',{name:/Мяч под диваном/})).toBeVisible();await page.getByRole('button',{name:/Взять длинную щётку/}).click();await page.getByRole('button',{name:/Осторожно выкатить мяч/}).click();await save();
  await expect(page.getByRole('heading',{name:/Найди лишний/})).toBeVisible();await page.getByRole('button',{name:'🚗 Машина',exact:true}).click();await page.getByRole('button',{name:'Три предмета — фрукты',exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Заполни три/})).toBeVisible();for(let i=0;i<3;i++)await page.locator('fieldset').nth(i).getByRole('button').first().click();await save();
  await expect(page.locator('.memory-material')).toBeVisible();await page.getByRole('button',{name:'Скрыть и ответить'}).click();await page.reload();await expect(page.locator('.memory-material')).toHaveCount(0);
  await page.getByRole('button',{name:'🍎',exact:true}).click();await page.getByRole('button',{name:'🚲',exact:true}).click();await page.getByRole('button',{name:'🌳',exact:true}).click();await save();
  await expect(page.locator('.target-grid')).toBeVisible();for(const b of await page.locator('.target-grid button').all())if((await b.textContent())==='★')await b.click();await page.screenshot({path:'test-results/journey-attention-390.png',fullPage:true});await save();
  await expect(page.locator('.route-board')).toBeVisible();for(const dir of ['Вправо','Вверх','Вправо'])await page.getByRole('button',{name:dir,exact:true}).click();await save();
  await expect(page.getByRole('heading',{name:/Собери события/})).toBeVisible();for(const text of ['🌱 Посадили семечко','💧 Полили землю','🌿 Появился росток','🌻 Распустился цветок'])await page.getByRole('button',{name:text,exact:true}).click();await save();
  await page.getByRole('button',{name:'Посмотреть результат',exact:true}).click();await expect(page.getByRole('heading',{name:'Выполнено 10 из 10',exact:true})).toBeVisible();
  for(const width of [360,430,1280]){await page.setViewportSize({width,height:932});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.setViewportSize({width:430,height:932});await page.screenshot({path:'test-results/journey-result-430.png',fullPage:true});
  await page.getByRole('link',{name:'Подобрать кружки',exact:true}).click();await expect(page.getByRole('heading',{name:'Рекомендации кружков'})).toBeVisible();await page.getByRole('button',{name:'Связаться с кружком',exact:true}).first().click();
  await expect(page.getByRole('heading',{name:'Запись на пробное занятие'})).toBeVisible();
  await page.getByLabel('Время',{exact:false}).selectOption({index:1});await page.getByRole('checkbox',{name:/Разрешаю передать/}).check();await page.getByRole('button',{name:'Оставить заявку',exact:true}).click();
  await page.getByRole('link',{name:/Мои заявки и занятия/}).click();await expect(page.getByText('Новая заявка',{exact:true})).toBeVisible();await page.reload();await expect(page.getByText('Новая заявка',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.querySelectorAll('audio').length)).toBe(0);
});
