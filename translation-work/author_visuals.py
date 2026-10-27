"""Developer-only compiler for reviewed menu art and native visual patches.

Dependencies: Pillow, UnityPy, fonttools, capstone, unicorn. The shipping build
uses only visuals.py and precompiled, hash-guarded objects (standard library).
"""
import io
import argparse
import json
from pathlib import Path
import shutil
import struct
from PIL import Image
import UnityPy
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_RDI, UC_X86_REG_RDX, UC_X86_REG_RBX, UC_X86_REG_RCX
from native import UnityFile, Reader, pack_string, sha
from storage import encoded
from author_fonts import main as fonts
from tmp_atlas import compile_asset

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'translation-work/visuals'
DATA = 'Who the fuck ate grandma_Data/'


def rel(path): return path.relative_to(ROOT).as_posix()


def obj(u, pid): return next(o for o in u.objects if o['id']==pid)


def payload(name, raw):
    p=WORK/'objects'/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    return rel(p)


def patch(u, pid, raw, name):
    o=obj(u,pid)
    return {'id':pid,'type':list(o['type']),'before_sha256':sha(u.raw(o)),
            'after_sha256':sha(raw),'payload':payload(name,raw)}


def image_raw(env, pid, image):
    o=next(o for o in env.objects if o.path_id==pid and o.type.name=='Texture2D')
    tex=o.read(); assert (tex.m_Width,tex.m_Height,tex.m_TextureFormat)==(1417,340,4)
    old=o.get_raw_data()
    tex.set_image(image, target_format=4, mipmap_count=1)
    assert tex.image.convert('RGBA').tobytes()==image.convert('RGBA').tobytes(), 'Texture conversion changed pixels'
    tex.save()
    # get_raw_data() reads the original stream in UnityPy 1.25.4. Serialized
    # edits live in ObjectReader.data until the whole container is saved.
    raw=bytes(o.data)
    assert raw!=old and tex.image_data in raw, 'Localized texture was not serialized'
    return raw


def main(game_root=None):
    fonts()
    WORK.mkdir(exist_ok=True); (WORK/'original').mkdir(exist_ok=True); (WORK/'menu').mkdir(exist_ok=True)
    for name, suffix in [('sharedassets0.assets',DATA+'sharedassets0.assets'),('GameAssembly.dll','GameAssembly.dll')]:
        dest=WORK/'original'/name
        if not dest.exists():
            assert game_root is not None, 'Initial authoring requires --game-root (read-only)'
            shutil.copyfile(Path(game_root)/suffix,dest)
    resource=ROOT/'EN'/DATA/'resources.assets'; shared=WORK/'original/sharedassets0.assets'; level=ROOT/'EN'/DATA/'level0'
    ru=UnityFile(resource.read_bytes()); su=UnityFile(shared.read_bytes()); lu=UnityFile(level.read_bytes())
    re=UnityPy.load(str(resource)); se=UnityPy.load(str(shared))
    profile={'schema':1,'files':{},'inputs':{}}
    def spec(source):return {'kind':'unity','source':rel(source),'source_sha256':sha(source.read_bytes()),'objects':[],'additions':[]}
    rs=profile['files'][DATA+'resources.assets']=spec(resource)
    ss=profile['files'][DATA+'sharedassets0.assets']=spec(shared)
    ls=profile['files'][DATA+'level0']=spec(level)
    for pid in (427,428):
        old=ru.raw(obj(ru,pid));start=old.index(b'OTTO');size=struct.unpack_from('<I',old,start-4)[0]
        end=start+size; old_end=(end+3)//4*4
        data=(WORK/f'fonts/font-{pid}-ptbr.otf').read_bytes()
        changed=old[:start-4]+struct.pack('<I',len(data))+data+bytes(-len(data)%4)+old[old_end:]
        if pid == 427:
            # Keep Unity's cached face metrics consistent with the enlarged
            # accent space. FontSize, tracking, material and texture stay put.
            metrics=json.loads((WORK/'fonts/coverage.json').read_text('utf-8'))[str(pid)]['unity_cached_metrics']
            changed=bytearray(changed)
            name_end=Reader(changed).string()[1][1]
            struct.pack_into('<f',changed,name_end,metrics['line_spacing'])
            tail=(start+len(data)+3)//4*4
            struct.pack_into('<ff',changed,tail,metrics['ascent'],metrics['descent'])
            changed=bytes(changed)
        rs['objects'].append(patch(ru,pid,changed,f'font-{pid}.bin'))
    bake=json.loads((WORK/'tmp/bake.json').read_text('utf-8'))
    bake_proof=json.loads((WORK/'tmp/provenance.json').read_text('utf-8'))
    assert bake_proof['source_font_sha256']==sha((WORK/'fonts/font-427-ptbr.otf').read_bytes()), 'Rebake TMP after source font changes'
    ss['objects'].append(patch(su,458,compile_asset(su.raw(obj(su,458)),bake),'tmp-font-458.bin'))
    # Keep every original atlas pixel at the same coordinates. The right half
    # contains the native SDF bake for characters missing from the static atlas.
    atlas=(WORK/'tmp/atlas-alpha8.bin').read_bytes()
    original_atlas=(WORK/'tmp/original-alpha8.bin').read_bytes()
    assert sha(atlas)==bake_proof['atlas_sha256'] and sha(original_atlas)==bake_proof['original_atlas_sha256']
    assert len(atlas)==2048*1024 and len(original_atlas)==1024*1024
    for row in range(1024):
        assert atlas[row*2048:row*2048+1024]==original_atlas[row*1024:(row+1)*1024]
    reader=next(o for o in se.objects if o.path_id==201)
    tex=reader.read();assert (tex.m_Width,tex.m_Height,tex.m_TextureFormat)==(1024,1024,1)
    tex.m_Width=2048;tex.m_CompleteImageSize=len(atlas);tex.image_data=atlas
    tex.m_StreamData.offset=0;tex.m_StreamData.size=0;tex.m_StreamData.path=''
    tex.save()
    ss['objects'].append(patch(su,201,bytes(reader.data),'tmp-atlas-201.bin'))
    reader=next(o for o in se.objects if o.path_id==2)
    material=reader.read();widths=material.m_SavedProperties.m_Floats
    assert dict(widths)['_TextureWidth']==1024
    material.m_SavedProperties.m_Floats=[(key,2048.0 if key=='_TextureWidth' else value) for key,value in widths]
    material.save()
    ss['objects'].append(patch(su,2,bytes(reader.data),'tmp-material-2.bin'))
    draft_paths=ROOT/'translation-work/.state/button-paths.json'
    paths=(json.loads(draft_paths.read_text('utf-8')) if draft_paths.exists() else
           {key:str(WORK/f'menu/{key}-states.png') for key in ('jogar','carregar','opcoes','sair')})
    art={}
    for label,path in paths.items():
        src=Image.open(path).convert('RGBA'); assert src.getextrema()[3][0]==0, 'Opaque button background'
        if Path(path).resolve() != (WORK/f'menu/{label}-states.png').resolve():
            shutil.copyfile(path, WORK/f'menu/{label}-states.png')
        art[label]=[]
        for state in range(2):
            row=src.crop((0,state*src.height//2,src.width,(state+1)*src.height//2))
            # Sprite import: trim transparent padding/noise and normalize the
            # pivot, so hover scales up without jumping vertically on screen.
            box=row.getchannel('A').point(lambda a:255 if a>32 else 0).getbbox()
            assert box
            box=(max(0,box[0]-12),max(0,box[1]-12),min(row.width,box[2]+12),min(row.height,box[3]+12))
            tile=row.crop(box);tile.thumbnail((1344,273) if state else (1280,260),Image.Resampling.LANCZOS)
            row=Image.new('RGBA',(1417,340),(0,0,0,0))
            row.paste(tile,((1417-tile.width)//2,(340-tile.height)//2))
            assert row.getbbox() and row.getextrema()[3][0]==0 and row.getextrema()[3][1]>=250
            row.save(WORK/f'menu/{label}-{state}.png'); art[label].append(row)
    for label,pids in [('jogar',(189,151)),('carregar',(93,179)),('sair',(134,137))]:
        for state,pid in enumerate(pids):
            ss['objects'].append(patch(su,pid,image_raw(se,pid,art[label][state]),f'{label}-{state}.bin'))
    # The original French images remain untouched. A second instance of the
    # game's own styler provides the fourth (Options) button in both languages.
    next_id=max(o['id'] for o in su.objects)+1
    texture_type=su.types.index(obj(su,189)['type'])
    options=[]
    for state,pid in enumerate((123,19)):
        for translated in (True,False):
            raw=image_raw(re,pid,art['opcoes'][state]) if translated else ru.raw(obj(ru,pid))
            name=f'options-{state}-{translated}.bin'; ident=next_id;next_id+=1
            ss['additions'].append({'id':ident,'type_index':texture_type,'payload':payload(name,raw)})
            options.append(ident)
    # Order: normal PT, normal FR, hover PT, hover FR.
    pt_normal,fr_normal,pt_hover,fr_hover=options
    styler=lu.raw(obj(lu,275)); assert len(styler)==220
    new_id=max(o['id'] for o in lu.objects)+1
    ptr=lambda pid:struct.pack('<iq',2,pid)
    new=styler[:32]+pack_string('Menu depart')+pack_string('Options')
    new+=ptr(pt_normal)+ptr(pt_hover)+ptr(fr_normal)+ptr(fr_hover)
    new+=(pack_string('')+bytes(48))*2
    ls['additions'].append({'id':new_id,'type_index':lu.types.index(obj(lu,275)['type']),
                            'payload':payload('options-styler.bin',new)})
    go=lu.raw(obj(lu,49)); count=struct.unpack_from('<i',go)[0]; assert count==7
    changed=struct.pack('<i',count+1)+go[4:4+12*count]+struct.pack('<iq',0,new_id)+go[4+12*count:]
    ls['objects'].append(patch(lu,49,changed,'menu-gameobject.bin'))
    # Exact IL2CPP UpdateButton method: both selectors must use FR only for
    # language 2, with PT-BR (1) and original/disabled EN (0) using EN artwork.
    binary=WORK/'original/GameAssembly.dll'; raw=binary.read_bytes()
    pe=struct.unpack_from('<I',raw,60)[0]; image_base=struct.unpack_from('<Q',raw,pe+48)[0]
    n=struct.unpack_from('<H',raw,pe+6)[0]; opt=struct.unpack_from('<H',raw,pe+20)[0]; secs=[]
    for i in range(n):
        off=pe+24+opt+40*i;vs,va,sz,pos=struct.unpack_from('<IIII',raw,off+8);secs.append((va,max(vs,sz),pos))
    def offset(address):
        return next(pos+address-image_base-va for va,size,pos in secs if image_base+va<=address<image_base+va+size)
    ranges=[]; proof=[]
    for address,old,new,highlight in [
        (0x1804c4734,'85f6b818000000b9280000000f45c1488b1438','31c083fe020f94c0c1e00483c018488b143890',False),
        (0x1804c475f,'85f6488d8b90000000b830000000ba200000000f45d0488b143a','31d283fe020f94c2c1e20483c220488d8b90000000488b143a90',True)]:
        a=bytes.fromhex(old);b=bytes.fromhex(new);off=offset(address)
        assert len(a)==len(b) and raw[off:off+len(a)]==a,'Unknown menu selector binary'
        cases=[]
        for lang in (-1,0,1,2,3,99):
            uc=Uc(UC_ARCH_X86,UC_MODE_64);uc.mem_map(0x100000,0x1000);uc.mem_write(0x100000,b)
            uc.mem_map(0x200000,0x2000);uc.reg_write(UC_X86_REG_RDI,0x200000);uc.reg_write(UC_X86_REG_RBX,0x201000)
            uc.reg_write(UC_X86_REG_ESI,lang & 0xffffffff)
            en,fr=(0x20,0x30) if highlight else (0x18,0x28)
            uc.mem_write(0x200000+en,struct.pack('<Q',1111));uc.mem_write(0x200000+fr,struct.pack('<Q',2222))
            uc.emu_start(0x100000,0x100000+len(b))
            assert uc.reg_read(UC_X86_REG_RDX)==(2222 if lang==2 else 1111)
            assert uc.reg_read(UC_X86_REG_ESI)==lang & 0xffffffff
            if highlight:assert uc.reg_read(UC_X86_REG_RCX)==0x201090
            cases.append({'language':lang,'uses_french':lang==2})
        ranges.append({'offset':off,'before':old,'after':new})
        proof.append({'address':hex(address),'instructions':[f'{i.mnemonic} {i.op_str}' for i in Cs(CS_ARCH_X86,CS_MODE_64).disasm(b,address)],'emulated_cases':cases})
    profile['files']['GameAssembly.dll']={'kind':'binary','source':rel(binary),'source_sha256':sha(raw),'ranges':ranges}
    (WORK/'selector-proof.json').write_bytes(encoded({'method':'ACLanguageButtonStyler.UpdateButton','source_sha256':sha(raw),'changes':proof}))
    needed={s['source'] for s in profile['files'].values()}
    needed.update(rel(WORK/'tmp'/p) for p in ('bake.json','provenance.json','atlas-alpha8.bin','original-alpha8.bin'))
    for s in profile['files'].values():
        needed.update(p['payload'] for p in s.get('objects',[]));needed.update(p['payload'] for p in s.get('additions',[]))
    profile['inputs']={p:sha((ROOT/p).read_bytes()) for p in sorted(needed)}
    (WORK/'profile.json').write_bytes(encoded(profile))
    print(json.dumps({'files':list(profile['files']),'objects':sum(len(s.get('objects',[])) for s in profile['files'].values()),'selector_emulations':12},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root',type=Path,help='Read-only original installation; initial authoring only')
    main(parser.parse_args().game_root)
