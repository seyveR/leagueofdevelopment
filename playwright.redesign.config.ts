import base from './playwright.mvp.config';
import {defineConfig} from '@playwright/test';
export default defineConfig({...base,testMatch:['redesign.spec.ts','mvp.spec.ts','platform.spec.ts']});

