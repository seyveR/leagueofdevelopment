// Normalize before React reads the native event; use the native setter so its
// controlled-input value tracker still observes the user's change.
document.addEventListener('input',event=>{
  const input=event.target;
  if(!(input instanceof HTMLInputElement)||input.type!=='number')return;
  const normalized=input.value.replace(/^(-?)0+(?=\d)/,'$1');
  if(normalized!==input.value){
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,normalized);
  }
},true);
