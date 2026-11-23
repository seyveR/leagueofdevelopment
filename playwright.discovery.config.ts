import {defineConfig} from '@playwright/test';
import base from './playwright.mvp.config';
export default defineConfig({...base,testMatch:['discovery-v2.spec.ts'],timeout:120000,use:{...base.use,actionTimeout:15000}});
