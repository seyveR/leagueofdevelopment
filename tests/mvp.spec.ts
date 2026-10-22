import{expect,test,type Page}from'@playwright/test';
test('15 неверных входов: минута паузы, правильный пароль сразу разрешён',async({page})=>{
  await register(page);await page.goto('/profile');const email=await page.locator('.lead').textContent();
  await page.getByRole('button',{name:'Выйти',exact:true}).click();await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();
  await page.getByLabel('Email',{exact:true}).fill(email!);await page.getByLabel('Пароль',{exact:true}).fill('incorrect-password');
  for(let index=1;index<=15;index++){
    const response=page.waitForResponse(r=>r.url().endsWith('/api/auth/login')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Войти',exact:true}).click();expect((await response).status()).toBe(index===15?429:401);
  }
  await expect(page.getByRole('alert')).toContainText('Повторите через минуту');
  await page.getByLabel('Пароль',{exact:true}).fill(password);await page.getByRole('button',{name:'Войти',exact:true}).click();await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();
});
test.describe('мобильная компоновка',()=>{
  test.use({viewport:{width:430,height:932},deviceScaleFactor:3,isMobile:true,hasTouch:true});
  for(const role of ['parent','admin'] as const)test(`${role}: навигация и размеры экрана`,async({page})=>{
    test.skip(role==='admin'&&!process.env.BROWSER_ADMIN_PASSWORD,'Test admin required');
    if(role==='parent'){await register(page);await child(page);}else{await login(page,'browser-admin@example.com',process.env.BROWSER_ADMIN_PASSWORD!);await expect(page.getByRole('heading',{name:'Администрирование',exact:true})).toBeVisible();}
    const nav=page.getByRole('navigation',{name:'Основная навигация'});
    await expect(nav.getByRole('link')).toHaveCount(4);await expect(nav.locator('svg')).toHaveCount(4);
    const routes=role==='admin'?['/admin','/admin/clubs','/admin/feedback','/account/password']:['/home','/tests','/programs','/profile'];
    for(const path of routes){
      await nav.locator(`a[href="${path}"]`).click();await expect(page.locator('h1')).toBeVisible();await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
      for(const width of [360,390,430,768,1280]){
        await page.setViewportSize({width,height:932});
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${role} ${path} ${width}`).toBe(true);
        if(width<=430){
          const bounds=await nav.boundingBox();expect(bounds!.height).toBeLessThanOrEqual(80);
          for(const link of await nav.getByRole('link').all()){const rect=await link.boundingBox();expect(rect!.height).toBeGreaterThanOrEqual(44);expect(rect!.width).toBeGreaterThanOrEqual(44);}
          if(path==='/admin')expect(await page.locator('h1').evaluate(el=>el.getBoundingClientRect().height/parseFloat(getComputedStyle(el).lineHeight))).toBeLessThan(1.1);
        }
      }
      await page.setViewportSize({width:430,height:932});
    }
    await page.goto(routes[0]);await expect(page.locator('h1')).toBeVisible();
    await page.screenshot({path:`test-results/mobile-${role}-430.png`,fullPage:false});
    await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
    const footer=await page.locator('footer').boundingBox(),bar=await nav.boundingBox();expect(footer!.y+footer!.height).toBeLessThanOrEqual(bar!.y);
  });
});
async function login(page:Page,email:string,password:string){await page.goto('/login');await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Пароль',{exact:true}).fill(password);await page.getByRole('button',{name:'Войти',exact:true}).click();}
for(const role of ['parent','admin'] as const)test(`${role}: смена пароля и отзыв другой сессии`,async({page,browser})=>{
  test.skip(role==='admin'&&!process.env.BROWSER_ADMIN_PASSWORD,'Test admin required');
  const email=role==='admin'?'password-admin@example.com':`password-${crypto.randomUUID()}@example.com`;
  const old=role==='admin'?process.env.BROWSER_ADMIN_PASSWORD!:'parent-old-password';const next=`new-${crypto.randomUUID()}`;
  if(role==='parent'){
    await page.goto('/login');await page.getByRole('button',{name:'Создать учётную запись'}).click();await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Пароль',{exact:true}).fill(old);await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();
  }else await login(page,email,old);
  await expect(page.getByRole('heading',{name:role==='admin'?'Администрирование':'Главная',exact:true})).toBeVisible();
  const otherContext=await browser.newContext();const other=await otherContext.newPage();
  try{
    await login(other,email,old);await expect(other.getByRole('button',{name:'Выйти',exact:true})).toBeVisible();
    if(role==='parent')await page.getByRole('link',{name:'Профиль',exact:true}).click();
    await page.getByRole('link',{name:'Сменить пароль',exact:true}).click();
    await page.getByLabel('Текущий пароль',{exact:true}).fill('incorrect-password');await page.getByLabel('Новый пароль',{exact:true}).fill(next);await page.getByLabel('Повторите новый пароль',{exact:true}).fill(next+'x');await page.getByRole('button',{name:'Изменить пароль',exact:true}).click();
    await expect(page.getByRole('alert')).toHaveText('Новые пароли не совпадают');
    await page.getByLabel('Повторите новый пароль',{exact:true}).fill(next);await page.getByRole('button',{name:'Изменить пароль',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Текущий пароль указан неверно');await expect(page.getByRole('button',{name:'Выйти',exact:true})).toBeVisible();
    await page.getByLabel('Текущий пароль',{exact:true}).fill(old);await page.getByRole('button',{name:'Изменить пароль',exact:true}).click();await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();await expect(page.getByRole('status')).toContainText('Пароль изменён');
    await other.getByRole('link',{name:role==='admin'?'Кружки и правила':'Кружки',exact:true}).click();await expect(other.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();await expect(other.getByRole('button',{name:'Выйти',exact:true})).toHaveCount(0);
    await login(page,email,old);await expect(page.getByRole('alert')).toBeVisible();await page.getByLabel('Пароль',{exact:true}).fill(next);await page.getByRole('button',{name:'Войти',exact:true}).click();await expect(page.getByRole('heading',{name:role==='admin'?'Администрирование':'Главная',exact:true})).toBeVisible();
    await page.reload();await expect(page.getByRole('button',{name:'Выйти',exact:true})).toBeVisible();await page.getByRole('button',{name:'Выйти',exact:true}).click();await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();
  }finally{await otherContext.close();}
});

test('выход с уже отозванной сессией и проверка при возврате к вкладке',async({page})=>{
  await register(page);
  // A separate client changes the password without notifying the open page.
  await page.goto('/profile');const account=await page.locator('.lead').textContent();expect(account).toBeTruthy();
  const other=await page.context().browser()!.newContext();
  try{
    const session=await other.request.get('http://127.0.0.1:8081/api/auth/session');const csrf=(await session.json()).csrf;
    const auth=await other.request.post('http://127.0.0.1:8081/api/auth/login',{headers:{'X-CSRF-Token':csrf},data:{email:account,password}});expect(auth.ok()).toBe(true);
    const result=await other.request.post('http://127.0.0.1:8081/api/auth/password',{headers:{'X-CSRF-Token':(await auth.json()).csrf},data:{current_password:password,new_password:'changed-parent-password',confirmation:'changed-parent-password'}});expect(result.ok()).toBe(true);
    await page.getByRole('button',{name:'Выйти',exact:true}).click();await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();
    await login(page,account!,'changed-parent-password');await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();
    const auth2=await other.request.get('http://127.0.0.1:8081/api/auth/session');const login2=await other.request.post('http://127.0.0.1:8081/api/auth/login',{headers:{'X-CSRF-Token':(await auth2.json()).csrf},data:{email:account,password:'changed-parent-password'}});expect(login2.ok()).toBe(true);
    expect((await other.request.post('http://127.0.0.1:8081/api/auth/password',{headers:{'X-CSRF-Token':(await login2.json()).csrf},data:{current_password:'changed-parent-password',new_password:'changed-again-password',confirmation:'changed-again-password'}})).ok()).toBe(true);
    await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();
  }finally{await other.close();}
});
const password='browser-parent-password';
async function register(page:Page){await page.goto('/');await page.getByRole('button',{name:'Создать учётную запись'}).click();await page.getByLabel('Email',{exact:true}).fill(`browser-${crypto.randomUUID()}@example.com`);await page.getByLabel('Пароль',{exact:true}).fill(password);await page.getByRole('button',{name:'Зарегистрироваться',exact:true}).click();await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();}
async function child(page:Page,name='Лисёнок',age='8'){await page.goto('/children/new');await page.getByLabel('Имя',{exact:true}).fill(name);await page.getByLabel('Возраст',{exact:true}).fill(age);await page.getByRole('checkbox',{name:'Подтверждаю согласие'}).check();await page.getByRole('button',{name:'Сохранить профиль'}).click();await expect(page.getByRole('heading',{name:'Главная',exact:true})).toBeVisible();}
test('родитель: регистрация, согласие, 12 заданий, память, результат, контакты, отзыв, выход',async({page})=>{
  await register(page);await child(page);await page.reload();await expect(page.getByText('Лисёнок · 8 лет · Архангельск',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Начать задания',exact:true}).click();await expect(page.getByRole('heading',{name:'Инструкция',exact:true})).toBeVisible();await page.getByRole('link',{name:'Начать прохождение'}).click();
  for(let n=1;n<=12;n++){
    await expect(page.getByText(`Задание ${n} из 12`,{exact:true})).toBeVisible();
    if(n===3){await page.reload();await expect(page.getByText('Задание 3 из 12',{exact:true})).toBeVisible();}
    if(n>=7){await expect(page.getByRole('radio')).toHaveCount(0);await expect(page.getByLabel('Материал задания')).toBeVisible();await page.getByRole('button',{name:'Скрыть и ответить'}).click();await expect(page.getByLabel('Материал задания')).toHaveCount(0);if(n===7){await page.reload();await expect(page.getByLabel('Материал задания')).toHaveCount(0);}}
    await expect(page.getByRole('button',{name:'Сохранить и дальше'})).toBeDisabled();await page.getByRole('radio').first().check();await page.getByRole('button',{name:'Сохранить и дальше'}).click();
  }
  await page.getByRole('button',{name:'Посмотреть результаты'}).click();await expect(page.getByRole('heading',{name:'Выполнено 12 из 12 заданий'})).toBeVisible();await expect(page.getByText('Результат ознакомительный, не является диагнозом и не заменяет консультацию специалиста',{exact:true})).toBeVisible();await page.reload();await expect(page.getByRole('heading',{name:'Результаты',exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Рекомендации кружков'}).click();const buttons=page.getByRole('button',{name:'Связаться с кружком'});await expect(buttons.first()).toBeVisible();expect(await buttons.count()).toBeGreaterThanOrEqual(3);expect(await buttons.count()).toBeLessThanOrEqual(5);await buttons.first().click();await expect(page.locator('a[href^="tel:"]')).toBeVisible();await expect(page.getByText('Адрес',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Оставить обратную связь'}).click();await page.getByRole('combobox',{name:'Оценка приложения'}).selectOption('5');await page.getByRole('textbox',{name:'Предложение'}).fill('Сценарий работает');await page.getByRole('button',{name:'Сохранить отзыв'}).dblclick();await expect(page.getByRole('heading',{name:'Обратная связь сохранена'})).toBeVisible();
  await page.getByRole('button',{name:'Выйти',exact:true}).click();await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();await page.goto('/profile');await expect(page.getByRole('heading',{name:'Вход',exact:true})).toBeVisible();
});
test('два ребёнка, недопустимый возраст, ошибка ответа и мобильные маршруты',async({page})=>{
  await register(page);await child(page);await page.getByRole('button',{name:'Начать задания',exact:true}).click();await page.getByRole('link',{name:'Начать прохождение'}).click();
  await page.route('**/api/sessions/*/answers',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Не удалось сохранить данные. Повторите действие.'})}));
  await page.getByRole('radio').first().check();await page.getByRole('button',{name:'Сохранить и дальше'}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('radio').first()).toBeChecked();await expect(page.getByText('Задание 1 из 12',{exact:true})).toBeVisible();await page.unroute('**/api/sessions/*/answers');await page.getByRole('button',{name:'Сохранить и дальше'}).click();await expect(page.getByText('Задание 2 из 12',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Выйти и продолжить позже'}).click();await child(page,'Второй','6');await expect(page.getByRole('button',{name:'Начать задания',exact:true})).toBeDisabled();await page.getByRole('combobox',{name:'Активный ребёнок'}).selectOption({label:'Лисёнок · 8 лет'});await page.getByRole('link',{name:'Продолжить · 1 из 12'}).click();await expect(page.getByText('Задание 2 из 12',{exact:true})).toBeVisible();
  for(const path of ['/home','/profile','/programs','/feedback','/children/new'])for(const width of[360,390,430,1280]){await page.setViewportSize({width,height:844});await page.goto(path);await expect(page.locator('h1')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${path} ${width}`).toBe(true);}
  await page.goto('/programs');await page.getByRole('textbox',{name:'Город',exact:true}).fill('Нет такого города');await page.getByRole('button',{name:'Показать',exact:true}).click();await expect(page.getByRole('heading',{name:'Кружки не найдены'})).toBeVisible();await page.goto('/admin');await expect(page.getByRole('heading',{name:'Доступ запрещён'})).toBeVisible();
  await page.setViewportSize({width:390,height:844});await page.goto('/home');await page.screenshot({path:'test-results/mvp-home-390.png',fullPage:true});
});
test('администратор: статистика, кружки, правила, архив и обратная связь',async({page})=>{
  test.skip(!process.env.BROWSER_ADMIN_PASSWORD,'Run tests/prepare_browser.py in the isolated database first');
  await page.goto('/');await page.getByLabel('Email',{exact:true}).fill('browser-admin@example.com');await page.getByLabel('Пароль',{exact:true}).fill(process.env.BROWSER_ADMIN_PASSWORD!);await page.getByRole('button',{name:'Войти',exact:true}).click();await expect(page.getByRole('heading',{name:'Администрирование'})).toBeVisible();await expect(page.getByRole('heading',{name:'Завершённые прохождения'})).toBeVisible();
  await page.getByRole('link',{name:/Прохождения и результаты/}).click();await expect(page.getByRole('heading',{name:'Завершённые прохождения',exact:true})).toBeVisible();await page.locator('.report-link').first().click();await expect(page.getByRole('heading',{name:'Результат прохождения',exact:true})).toBeVisible();await expect(page.locator('.report-answer')).toHaveCount(12);await page.locator('.report-answer summary').first().click();await expect(page.locator('.report-answer').first().getByText('Ответ ребёнка:',{exact:true})).toBeVisible();
  for(const width of[360,390,430,1280]){await page.setViewportSize({width,height:932});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await expect(page.getByRole('navigation',{name:'Основная навигация'}).locator('[aria-current="page"]')).toHaveCount(1);}
  await page.setViewportSize({width:430,height:932});await page.screenshot({path:'test-results/admin-completion-430.png',fullPage:true});const reportUrl=page.url();await page.reload();await expect(page.getByRole('heading',{name:'Результат прохождения',exact:true})).toBeVisible();expect(page.url()).toBe(reportUrl);
  await page.getByRole('link',{name:'Все прохождения',exact:false}).click();await expect(page.locator('.report-link')).toHaveCount(1);await page.getByRole('link',{name:'Статистика',exact:true}).click();await page.getByRole('link',{name:/Статистика по кружкам/}).click();await expect(page.getByText('Всего переходов: 1',{exact:true})).toBeVisible();await page.screenshot({path:'test-results/admin-transitions-430.png',fullPage:true});
  await page.getByRole('link',{name:'Кружки и правила'}).click();await page.getByRole('button',{name:'Добавить кружок',exact:true}).click();const name=`Кружок ${Date.now()}`;for(const[label,value]of[['Название',name],['Описание','Описание программы'],['Адрес','Учебный адрес'],['Телефон','+7 (000) 000-00-00'],['Цена','1000 ₽']])await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByRole('combobox',{name:'Показатель',exact:true}).selectOption('attention');await page.getByLabel('Объяснение для родителя',{exact:true}).fill('Упражнения с деталями.');await page.getByRole('button',{name:'Сохранить кружок и правило'}).click();const row=page.locator('.history-row').filter({has:page.getByRole('heading',{name,exact:true})});await expect(row).toBeVisible();await row.getByRole('button',{name:'Редактировать',exact:true}).click();await page.getByLabel('Архивировать кружок',{exact:true}).check();await page.getByRole('button',{name:'Сохранить кружок и правило'}).click();await expect(page.locator('.history-row').filter({has:page.getByRole('heading',{name,exact:true})})).toContainText('Архив');await page.getByRole('link',{name:'Обратная связь',exact:true}).click();await expect(page.getByText('Сценарий работает',{exact:true})).toBeVisible();
});

