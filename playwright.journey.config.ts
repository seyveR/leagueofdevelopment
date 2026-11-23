import {defineConfig} from '@playwright/test';
import base from './playwright.mvp.config';
export default defineConfig({...base,testMatch:['journey.spec.ts'],timeout:120000,use:{...base.use,actionTimeout:15000}});
