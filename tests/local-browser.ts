import {test as base,expect,type Browser,type BrowserContext,type Page} from '@playwright/test';
export async function blockExternal(context:BrowserContext){await context.route('**/*',route=>{const url=new URL(route.request().url());if(['http:','https:'].includes(url.protocol)&&!['127.0.0.1','localhost','[::1]'].includes(url.hostname))return route.abort('blockedbyclient');return route.continue();});}
export async function localContext(browser:Browser){const context=await browser.newContext();await blockExternal(context);return context;}
export const test=base.extend({context:async({context},use)=>{await blockExternal(context);await use(context);}});
export {expect,type Page};
