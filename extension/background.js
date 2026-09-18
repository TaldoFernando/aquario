chrome.runtime.onInstalled.addListener(async()=>{
  const saved=await chrome.storage.local.get('config');
  if(!saved.config)await chrome.storage.local.set({config:{version:1,ids:[],geo:null,paused:false,clock:null,realScale:false}});
});
