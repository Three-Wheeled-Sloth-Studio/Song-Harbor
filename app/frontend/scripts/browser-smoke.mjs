import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { chromium } from "playwright";
import {spawn} from "node:child_process";

// Actual Chromium mount check. A successful TS compilation or HTML fetch does
// not mean React mounted or the JavaScript chunk loaded.
const root=resolve("app/frontend/dist");
const mime={".html":"text/html",".js":"text/javascript",".css":"text/css",
  ".svg":"image/svg+xml",".woff2":"font/woff2",".json":"application/json"};
const server=createServer(async(req,res)=>{
  const pathname=decodeURIComponent((req.url||"/").split("?")[0]);
  if(pathname.startsWith("/api/")){
    res.writeHead(200,{"content-type":"application/json"});
    res.end(JSON.stringify(pathname==="/api/health"
      ?{ready:true,separator_ready:false,instance_token:"ci-browser-test",needs_setup:[]}
      :pathname==="/api/library"
      ?{songs:[],collections:[]}
      :pathname==="/api/projects"
      ?{projects:[]}
      :{supported:false,reason:"smoke test"}));
    return;
  }
  const path=resolve(root,"."+pathname+(pathname.endsWith("/")?"index.html":""));
  if(!path.startsWith(root+sep)&&path!==root){res.writeHead(403).end();return;}
  try{
    if(!(await stat(path)).isFile())throw Error("not file");
    const bytes=await readFile(path);
    res.writeHead(200,{"content-type":mime[extname(path)]||"application/octet-stream"});
    res.end(bytes);
  }catch{res.writeHead(404).end("Not found");}
});
await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
const port=server.address().port;
const useBackend=process.argv.includes("--backend");
let backend;
if(useBackend){
  await new Promise(done=>server.close(done));
  backend=spawn(process.env.PYTHON||"python3",["app/backend/server.py"],{
    stdio:["ignore","pipe","pipe"],
    env:{...process.env,SONG_HARBOR_HOME:resolve("qa-runtime-browser"),
      SONG_HARBOR_PORT:String(port),SONG_HARBOR_INSTANCE_TOKEN:"ci-browser-test"}});
  let logs="";
  backend.stdout.on("data",bytes=>logs+=bytes.toString());
  backend.stderr.on("data",bytes=>logs+=bytes.toString());
  let ready=false;
  for(let i=0;i<80;i++){
    if(backend.exitCode!==null)throw Error("Backend exited early:\n"+logs);
    try{
      const response=await fetch("http://127.0.0.1:"+port+"/api/health");
      if(response.ok){ready=true;break;}
    }catch{}
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  if(!ready)throw Error("Backend unavailable:\n"+logs);
}
let browser;
try{
  browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  const page=await browser.newPage();
  const errors=[];
  page.on("pageerror",e=>errors.push("JS: "+e.message));
  page.on("console",m=>{if(m.type()==="error")errors.push("Console: "+m.text());});
  page.on("response",r=>{if(r.url().includes("/assets/")&&r.status()>=400)errors.push("Asset "+r.status()+": "+r.url());});
  await page.goto("http://127.0.0.1:"+port+"/",{waitUntil:"networkidle"});
  await page.getByRole("heading",{name:"Library"}).waitFor({timeout:12000});
  if(errors.length)throw Error("Browser mount errors:\n"+errors.join("\n"));
  console.log("PASS: rendered Library in a real Chromium browser with no JS or asset errors");
  await page.getByRole("button",{name:"Import song"}).first().click();
  await page.getByRole("heading",{name:"Import song"}).waitFor({timeout:5000});
  await page.getByRole("button",{name:"Multiple tracks · already separated"}).click();
  await page.getByText("Choose aligned tracks").waitFor({timeout:5000});
  if(errors.length)throw Error("Import screen errors:\n"+errors.join("\n"));
  console.log("PASS: navigated to multi-track import");
}finally{
  if(browser)await browser.close();
  if(backend){backend.kill();await new Promise(resolve=>backend.once("close",resolve));}
  else await new Promise(resolve=>server.close(resolve));
}
