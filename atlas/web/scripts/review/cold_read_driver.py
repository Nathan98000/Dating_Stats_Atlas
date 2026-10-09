# Persistent Playwright driver: POST JSON commands to http://127.0.0.1:9333/
import asyncio, json, time, sys
from aiohttp import web
from playwright.async_api import async_playwright
STATE={}
async def ensure(ctxname, opts):
    if ctxname in STATE: return STATE[ctxname]
    b=STATE['browser']
    ctx=await b.new_context(**opts)
    pg=await ctx.new_page()
    msgs=[]
    pg.on('console', lambda m: msgs.append(f'{m.type}: {m.text}'))
    pg.on('pageerror', lambda e: msgs.append(f'pageerror: {e}'))
    STATE[ctxname]=(ctx,pg,msgs)
    return STATE[ctxname]
async def handle(req):
    cmds=await req.json()
    if isinstance(cmds,dict): cmds=[cmds]
    out=[]
    for c in cmds:
        t0=time.time()
        try:
            name=c.get('ctx','main')
            if c['a']=='new':
                if name in STATE:
                    await STATE[name][0].close(); del STATE[name]
                await ensure(name, c.get('opts',{}))
                out.append('ok'); continue
            ctx,pg,msgs=STATE[name]
            a=c['a']
            if a=='goto': await pg.goto(c['url'],wait_until=c.get('wait','networkidle')); r=pg.url
            elif a=='click': await pg.locator(c['sel']).first.click(timeout=c.get('timeout',5000)); r='clicked'
            elif a=='tap': await pg.locator(c['sel']).first.tap(timeout=5000); r='tapped'
            elif a=='fill': await pg.locator(c['sel']).first.fill(c['text']); r='filled'
            elif a=='type': await pg.keyboard.type(c['text'],delay=c.get('delay',30)); r='typed'
            elif a=='press': await pg.keyboard.press(c['key']); r='pressed'
            elif a=='select': r=await pg.locator(c['sel']).first.select_option(c['value'])
            elif a=='wait': await pg.wait_for_timeout(c['ms']); r='waited'
            elif a=='waitfor': await pg.locator(c['sel']).first.wait_for(state=c.get('state','visible'),timeout=c.get('timeout',10000)); r='found'
            elif a=='scroll': await pg.evaluate(f"window.scrollTo(0,{c['y']})"); await pg.wait_for_timeout(300); r=await pg.evaluate('window.scrollY')
            elif a=='shot':
                kw={'path':c['path'],'full_page':c.get('full',False)}
                if 'clip' in c: kw['clip']=c['clip']
                if 'sel' in c: await pg.locator(c['sel']).first.screenshot(path=c['path']); r=c['path']
                else: await pg.screenshot(**kw); r=c['path']
            elif a=='eval': r=await pg.evaluate(c['js'])
            elif a=='text': r=await pg.locator(c.get('sel','body')).first.inner_text()
            elif a=='msgs': r=list(msgs); msgs.clear()
            elif a=='url': r=pg.url
            elif a=='focus': r=await pg.evaluate("(()=>{const e=document.activeElement; if(!e) return null; const b=e.getBoundingClientRect(); return {tag:e.tagName, id:e.id, role:e.getAttribute('role'), name:e.getAttribute('aria-label')||e.innerText?.slice(0,60), cls:e.className?.toString().slice(0,80), x:b.x,y:b.y,w:b.width,h:b.height}})()")
            elif a=='mouse': await pg.mouse.click(c['x'],c['y']); r='mouse'
            elif a=='close': await ctx.close(); del STATE[name]; r='closed'
            else: r='unknown'
            out.append({'r':r,'ms':int((time.time()-t0)*1000)})
        except Exception as e:
            out.append({'err':str(e)[:600]})
            if c.get('stop',True): break
    return web.json_response(out)
async def main():
    p=await async_playwright().start()
    STATE['browser']=await p.chromium.launch()
    app=web.Application(client_max_size=10**7); app.router.add_post('/',handle)
    r=web.AppRunner(app); await r.setup(); await web.TCPSite(r,'127.0.0.1',9333).start()
    print('driver ready',flush=True)
    while True: await asyncio.sleep(3600)
asyncio.run(main())
