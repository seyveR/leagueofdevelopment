import{defineConfig}from'@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:['mvp.spec.ts','platform.spec.ts'],workers:1,timeout:90000,reporter:'list',use:{baseURL:'http://127.0.0.1:8081',channel:process.env.PLAYWRIGHT_CHANNEL||(process.platform==='win32'?'msedge':undefined),viewport:{width:390,height:844},headless:true,trace:'retain-on-failure'}});
