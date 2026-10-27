// Checks the actual generated files through the running Nginx/API, without an account.
import {chromium} from '@playwright/test';
import {readFileSync} from 'node:fs';
const manifest=JSON.parse(readFileSync('audio-cache/manifest.json','utf8'));
const samples=Object.entries(manifest.clips).filter(([,text])=>text.startsWith('Привет! Сейчас'));
if(samples.length!==2)throw new Error('Expected two real voice samples');
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
  const context=await browser.newContext();
  await context.route('**/*',route=>{const u=new URL(route.request().url());return ['127.0.0.1','localhost'].includes(u.hostname)?route.continue():route.abort();});
  const page=await context.newPage();await page.goto('http://127.0.0.1:8080/login');
  for(const [key] of samples){
    const url=`/api/audio/files/${key}.wav`;
    const decoded=await page.evaluate(async url=>{
      const response=await fetch(url);if(!response.ok)throw new Error('Audio HTTP '+response.status);
      const ctx=new AudioContext();const data=await ctx.decodeAudioData(await response.arrayBuffer());
      const pcm=data.getChannelData(0);let energy=0;for(const x of pcm)energy+=x*x;
      const result={duration:data.duration,sampleRate:data.sampleRate,rms:Math.sqrt(energy/pcm.length)};await ctx.close();return result;
    },url);
    if(decoded.duration<2||decoded.rms<0.001)throw new Error('Empty or silent speech file');
    await page.evaluate(url=>{
      window.voiceProbe=new Audio(url);const button=document.createElement('button');button.id='voice-probe';button.textContent='Проверить запись';button.onclick=()=>window.voiceProbe.play();document.body.append(button);
    },url);
    await page.locator('#voice-probe').click();await page.waitForFunction(()=>window.voiceProbe.currentTime>0.5&&!window.voiceProbe.paused);
    const time=await page.evaluate(()=>{const p=window.voiceProbe;const t=p.currentTime;p.pause();document.querySelector('#voice-probe').remove();return t;});
    console.log(JSON.stringify({url,...decoded,playedSeconds:time}));
  }
}finally{await browser.close();}
