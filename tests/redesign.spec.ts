import {test,expect} from './local-browser';
test('регистрация организации после выхода родителя без перезагрузки',async({page})=>{
 await page.goto('/login');await page.getByRole('button',{name:'Создать учётную запись'}).click();
 await page.getByLabel('Email',{exact:true}).fill(`csrf-parent-${crypto.randomUUID()}@example.com`);
 await page.getByLabel('Пароль',{exact:true}).fill('csrf-parent-password');await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();await page.getByRole('button',{name:'Выйти',exact:true}).click();
 await page.getByRole('link',{name:'Регистрация организации',exact:true}).click();
 for(const [label,value] of [['Email',`csrf-org-${crypto.randomUUID()}@example.com`],['Пароль','csrf-partner-password'],['Организация','Проверка регистрации'],['Город','Архангельск'],['Контакт','test@example.com']])await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByRole('checkbox',{name:/Согласен на хранение/}).check();await page.getByRole('button',{name:'Зарегистрировать организацию',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Кабинет организации',exact:true})).toBeVisible();
});
test('пять самостоятельных тестов, восстановление, персонаж и мобильные экраны',async({page})=>{
  await page.goto('/login');await page.getByRole('button',{name:'Создать учётную запись'}).click();
  await page.getByLabel('Email',{exact:true}).fill(`redesign-${crypto.randomUUID()}@example.com`);await page.getByLabel('Пароль',{exact:true}).fill('redesign-parent-password');await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();
  await page.goto('/children/new');await page.getByLabel('Имя',{exact:true}).fill('Саша');await page.getByLabel('Возраст',{exact:true}).fill('8');await page.getByRole('checkbox',{name:'Подтверждаю согласие'}).check();await page.getByRole('button',{name:'Сохранить профиль'}).click();
  await page.goto('/tests');await expect(page.locator('.test-tile')).toHaveCount(5);await page.screenshot({path:'test-results/redesign-tests-390.png',fullPage:true});
  const ids=new Set<string>();
  for(const code of ['attention','memory','logic','spatial','imagination']){
    await page.goto('/tests/'+code);await page.locator('.test-tile button').click();await page.getByRole('link',{name:'Начать прохождение',exact:true}).click();
    ids.add(page.url().split('/')[4]);
    for(let n=1;n<=6;n++){
      await expect(page.getByText(`Задание ${n} из 6`,{exact:true})).toBeVisible();
      if(await page.getByRole('button',{name:'Скрыть и ответить',exact:true}).count())await page.getByRole('button',{name:'Скрыть и ответить',exact:true}).click();
      if(n===2){await page.reload();await expect(page.getByText('Задание 2 из 6',{exact:true})).toBeVisible();}
      await page.getByRole('radio').first().check();await page.getByRole('button',{name:'Сохранить и дальше',exact:true}).click();
    }
    await page.getByRole('button',{name:'Посмотреть результаты'}).click();await expect(page.getByRole('heading',{name:'Выполнено 6 из 6'})).toBeVisible();
    if(code==='imagination')await expect(page.getByText(/талант и воображение не оцениваются/)).toBeVisible();
  }
  expect(ids.size).toBe(5);
  await page.goto('/profile');await page.getByRole('heading',{name:'Саша · 8 лет'}).click();await page.getByRole('link',{name:'Выбрать помощника'}).click();await page.getByRole('button',{name:/Макс/}).click();await page.getByRole('button',{name:'Подтвердить выбор'}).click();await expect(page.getByText('Помощник выбран',{exact:true})).toBeVisible();await page.reload();await expect(page.getByRole('button',{name:/Макс/})).toHaveAttribute('aria-pressed','true');
  for(const path of ['/home','/tests','/analytics','/profile','/programs']){
    await page.goto(path);await expect(page.locator('h1').first()).toBeVisible();
    for(const width of [360,390,430,1280]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),path+' '+width).toBe(true);}
    await page.setViewportSize({width:390,height:844});await page.screenshot({path:`test-results/redesign-${path.slice(1)}-390.png`,fullPage:true});
  }
  await page.goto('/home');await expect(page.locator('.app-navigation a')).toHaveCount(5);await expect(page.getByRole('link',{name:'Настройки',exact:true})).toHaveCount(0);
});
