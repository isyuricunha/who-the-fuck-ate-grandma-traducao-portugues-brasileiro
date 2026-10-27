
let done=false;
const start=Date.now();
const poll=setInterval(()=>{try {
 if(Date.now()-start<1500)return;
 const mod=Process.findModuleByName('GameAssembly.dll');if(!mod)return;
 const api=(n,r,a)=>new NativeFunction(mod.getExportByName('il2cpp_'+n),r,a);
 const domain=api('domain_get','pointer',[])();if(domain.isNull())return;
 api('thread_attach','pointer',['pointer'])(domain);
 const count=Memory.alloc(8);const arr=api('domain_get_assemblies','pointer',['pointer','pointer'])(domain,count);
 const images={};const getimage=api('assembly_get_image','pointer',['pointer']);const getname=api('image_get_name','pointer',['pointer']);
 for(let i=0;i<count.readU64().toNumber();i++){const im=getimage(arr.add(i*8).readPointer());images[getname(im).readUtf8String()]=im;}
 if(!images['AC.dll'])return;
 clearInterval(poll);
 api('thread_attach','pointer',['pointer'])(domain);
 const klass=api('class_from_name','pointer',['pointer','pointer','pointer']);
 const cls=(im,ns,name)=>klass(images[im],Memory.allocUtf8String(ns),Memory.allocUtf8String(name));
 const method=api('class_get_method_from_name','pointer',['pointer','pointer','int']);
 const met=(c,n,a)=>method(c,Memory.allocUtf8String(n),a);
 const state=cls('AC.dll','AC','StateHandler');const update=met(state,'Update',0);
 const Font=cls('UnityEngine.TextRenderingModule.dll','UnityEngine','Font');
 const gm=api('class_get_methods','pointer',['pointer','pointer']);const mn=api('method_get_name','pointer',['pointer']);
 const invoke=api('runtime_invoke','pointer',['pointer','pointer','pointer','pointer']);
 const unbox=api('object_unbox','pointer',['pointer']);
 const exc=Memory.alloc(8);
 function call(m,obj,args){const p=Memory.alloc(Math.max(8,args.length*8));args.forEach((v,i)=>p.add(i*8).writePointer(v));exc.writePointer(ptr(0));const r=invoke(m,obj,p,exc);if(!exc.readPointer().isNull())throw Error('exception '+exc.readPointer());return r;}
 function str(p){if(p.isNull())return null;return p.add(20).readUtf16String(p.add(16).readU32());}



 Interceptor.attach(update.readPointer(),{onEnter(){if(done)return;done=true;try{
 const res=cls('UnityEngine.CoreModule.dll','UnityEngine','Resources'),Obj=cls('UnityEngine.CoreModule.dll','UnityEngine','Object'),FA=cls('Unity.TextMeshPro.dll','TMPro','TMP_FontAsset'),Tex=cls('UnityEngine.CoreModule.dll','UnityEngine','Texture2D');
 const arrayNew=api('array_new','pointer',['pointer','uint64']);
 const find=(c)=>{const type=api('type_get_object','pointer',['pointer'])(api('class_get_type','pointer',['pointer'])(c));const a=call(met(res,'FindObjectsOfTypeAll',1),ptr(0),[type]);let r=[];for(let i=0;i<a.add(24).readU64().toNumber();i++)r.push(a.add(32+i*8).readPointer());return r;};
 const name=f=>str(call(met(Obj,'get_name',0),f,[]));
 const asset=find(FA).find(f=>name(f)==='lucasarts-scumm-solid');const source=find(Font).find(f=>name(f)==='lucasarts-scumm-solid');if(!asset||!source)throw Error('Expected font references');
 call(met(FA,'ReadFontAssetDefinition',0),asset,[]);
 const val=n=>{const p=Memory.alloc(4);p.writeS32(n);return p;};
 const texture=api('object_new','pointer',['pointer'])(Tex);call(met(Tex,'.ctor',4),texture,[val(2048),val(1024),val(1),val(0)]);
 const writable=unbox(call(met(Tex,'GetWritableImageData',1),texture,[val(0)])).readPointer();
 const original=File.readAllBytes('__INPUT__/original-alpha8.bin');const mem=Memory.alloc(original.byteLength);mem.writeByteArray(original);for(let y=0;y<1024;y++)Memory.copy(writable.add(y*2048),mem.add(y*1024),1024);
 asset.add(256).writePointer(source);asset.add(272).writeS32(1);asset.add(320).writePointer(texture);asset.add(328).readPointer().add(32).writePointer(texture);asset.add(344).writeS32(2048);asset.add(340).writeU8(0);
 const rectClass=cls('UnityEngine.TextCoreFontEngineModule.dll','UnityEngine.TextCore','GlyphRect');const free=asset.add(368).readPointer();const rects=arrayNew(rectClass,1);for(const [i,v] of [1024,0,1023,1023].entries())rects.add(32+i*4).writeS32(v);free.add(16).writePointer(rects);free.add(24).writeS32(1);
 let add=ptr(0),it=Memory.alloc(8);it.writePointer(ptr(0));let m;while(!(m=gm(FA,it)).isNull())if(mn(m).readUtf8String()==='TryAddCharacters'&&api('method_get_param_count','uint',['pointer'])(m)===3&&api('type_get_name','pointer',['pointer'])(api('method_get_param','pointer',['pointer','uint'])(m,0)).readUtf8String()==='System.String')add=m;
 const needed=File.readAllText('__INPUT__/needed.txt');const text=api('string_new','pointer',['pointer'])(Memory.allocUtf8String(needed));const missing=Memory.alloc(8);missing.writePointer(ptr(0));const ok=unbox(call(add,asset,[text,missing,val(0)])).readU8()!==0;
 function list(p,stride,objects){const a=p.add(16).readPointer(),n=p.add(24).readS32();let r=[];for(let i=0;i<n;i++)r.push(objects?a.add(32+i*8).readPointer():a.add(32+i*stride));return r;}
 const glyphs=list(asset.add(288).readPointer(),0,true).map(g=>({index:g.add(16).readU32(),metrics:Array.from(new Float32Array(g.add(20).readByteArray(20))),rect:Array.from(new Int32Array(g.add(40).readByteArray(16))),scale:g.add(56).readFloat(),atlas:g.add(60).readS32(),class:g.add(64).readS32()}));
 // TMP_TextElement stores element type, Unicode and glyph index in its base.
 const fields=api('class_get_fields','pointer',['pointer','pointer']),fn=api('field_get_name','pointer',['pointer']),fo=api('field_get_offset','uint',['pointer']);let c=cls('Unity.TextMeshPro.dll','TMPro','TMP_TextElement'),fs={};it.writePointer(ptr(0));while(!(m=fields(c,it)).isNull())fs[fn(m).readUtf8String()]=fo(m);
 const characters=list(asset.add(304).readPointer(),0,true).map(c=>({type:c.add(fs.m_ElementType).readS32(),unicode:c.add(fs.m_Unicode).readU32(),glyph:c.add(fs.m_GlyphIndex).readU32(),scale:c.add(fs.m_Scale).readFloat()}));
 const used=list(asset.add(360).readPointer(),16,false).map(p=>Array.from(new Int32Array(p.readByteArray(16))));const freeRects=list(free,16,false).map(p=>Array.from(new Int32Array(p.readByteArray(16))));
 send({stage:'result',ok,missing:str(missing.readPointer()),glyphs,characters,used,free:freeRects},writable.readByteArray(2048*1024));
 }catch(e){send({stage:'error',error:e.stack});}}});
}catch(e){send({stage:'setup-error',error:e.stack});clearInterval(poll);}},100);
