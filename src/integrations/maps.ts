/** Link-only adapter. No map SDK, key or background geolocation request. */
export const maps={provider:'Яндекс Карты',addressUrl:(city:string,address:string)=>'https://yandex.ru/maps/?text='+encodeURIComponent(city+' '+address)};
