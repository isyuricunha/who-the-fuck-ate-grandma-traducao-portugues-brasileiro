"""Independent stdlib inspection of the built visual assets, not a game run."""
import json
from pathlib import Path
import struct
from native import UnityFile, Reader, sha, require
from storage import encoded
from toolkit import Project
from tmp_atlas import parse as parse_tmp

ROOT=Path(__file__).resolve().parent.parent
DATA='Who the fuck ate grandma_Data/'


def font_data(raw):
    start=raw.index(b'OTTO');size=struct.unpack_from('<I',raw,start-4)[0]
    require(start+size<=len(raw),'Truncated embedded font')
    return raw[start:start+size],start,size


def codepoints(data):
    n=struct.unpack_from('>H',data,4)[0]
    tables={}
    for i in range(n):
        tag,checksum,off,size=struct.unpack_from('>4sIII',data,12+16*i)
        require(off+size<=len(data),'Font table outside data');tables[tag]=(off,size)
    base,size=tables[b'cmap'];count=struct.unpack_from('>H',data,base+2)[0];result=set()
    for i in range(count):
        platform,encoding,off=struct.unpack_from('>HHI',data,base+4+8*i)
        if platform not in (0,3):continue
        s=base+off;fmt=struct.unpack_from('>H',data,s)[0]
        if fmt==4:
            segments=struct.unpack_from('>H',data,s+6)[0]//2
            ends=s+14;starts=ends+2*segments+2;deltas=starts+2*segments;ranges=deltas+2*segments
            for j in range(segments):
                lo=struct.unpack_from('>H',data,starts+2*j)[0];hi=struct.unpack_from('>H',data,ends+2*j)[0]
                delta=struct.unpack_from('>h',data,deltas+2*j)[0];ro=struct.unpack_from('>H',data,ranges+2*j)[0]
                for cp in range(lo,min(hi,65534)+1):
                    g=(cp+delta)&65535 if not ro else struct.unpack_from('>H',data,ranges+2*j+ro+2*(cp-lo))[0]
                    if ro and g:g=(g+delta)&65535
                    if g:result.add(cp)
        elif fmt==12:
            for j in range(struct.unpack_from('>I',data,s+12)[0]):
                lo,hi,g=struct.unpack_from('>III',data,s+16+12*j)
                result.update(range(lo if g else lo+1,hi+1))
        else:raise ValueError('Unexpected Unicode cmap format')
    return result


def face_metrics(data):
    tables={struct.unpack_from('>4sIII',data,12+16*i)[0]:struct.unpack_from('>4sIII',data,12+16*i)[2]
            for i in range(struct.unpack_from('>H',data,4)[0])}
    units=struct.unpack_from('>H',data,tables[b'head']+18)[0]
    ascent,descent,gap=struct.unpack_from('>hhh',data,tables[b'hhea']+4)
    return units,ascent,descent,gap


def main():
    p=Project(ROOT);p.integrity();receipt=p.verify_output();_,records,_,_=p.workspace()
    profile=json.loads((ROOT/'translation-work/visuals/profile.json').read_text('utf-8'))
    text=''.join(r['PTBR'] for r in records.values());needed={ord(c) for c in text if ord(c)>32}
    report={'records':len(records),'files':len(receipt['output']),'game_runtime_test':False,
            'installation_written':False,'fonts':{},'native_objects':{},'french_menu_images_preserved':True}
    def get(u,pid):return u.raw(next(o for o in u.objects if o['id']==pid))
    resources=UnityFile((ROOT/'PTBR'/DATA/'resources.assets').read_bytes())
    original_resources=UnityFile((ROOT/'EN'/DATA/'resources.assets').read_bytes())
    for pid in (427,428):
        old=get(original_resources,pid);new=get(resources,pid)
        a,as_,az=font_data(old);b,bs,bz=font_data(new)
        old_prefix=old[:as_-4];new_prefix=bytearray(new[:bs-4])
        old_tail=old[(as_+az+3)//4*4:];new_tail=bytearray(new[(bs+bz+3)//4*4:])
        cached=None
        if pid==427:
            name_end=Reader(old).string()[1][1]
            size=struct.unpack_from('<f',old,name_end+16)[0]
            units,ascent,descent,gap=face_metrics(b);scale=size/units
            expected_metrics=((ascent-descent+gap)*scale,ascent*scale,descent*scale)
            actual_metrics=(struct.unpack_from('<f',new,name_end)[0],*struct.unpack_from('<ff',new_tail))
            require(all(abs(x-y)<0.0001 for x,y in zip(expected_metrics,actual_metrics)),
                    'Unity face cache disagrees with full-size font metrics')
            new_prefix[name_end:name_end+4]=old_prefix[name_end:name_end+4]
            new_tail[:8]=old_tail[:8]
            cached=dict(zip(('line_spacing','ascent','descent'),actual_metrics))
        require(old_prefix==new_prefix and old_tail==new_tail,'Unrelated font object fields changed')
        expected=(ROOT/f'translation-work/visuals/fonts/font-{pid}-ptbr.otf').read_bytes()
        require(b==expected,'Embedded font differs from reviewed OTF')
        have=codepoints(b);missing=needed-have;require(not missing,'Missing translated glyphs')
        report['fonts'][str(pid)]={'unicode_characters':len(have),'missing':[],'embedded_sha256':sha(b),
                                  'unrelated_font_object_fields_preserved':True,'cached_metrics':cached}
    shared=UnityFile((ROOT/'PTBR'/DATA/'sharedassets0.assets').read_bytes())
    old_shared=UnityFile((ROOT/'translation-work/visuals/original/sharedassets0.assets').read_bytes())
    old_tmp=parse_tmp(get(old_shared,458));new_tmp=parse_tmp(get(shared,458))
    old_glyphs={g[0]:g for g in old_tmp['glyphs']};new_glyphs={g[0]:g for g in new_tmp['glyphs']}
    old_chars={c[1]:c for c in old_tmp['characters']};new_chars={c[1]:c for c in new_tmp['characters']}
    require(needed<=set(new_chars),'Subtitle TMP atlas still needs fallback glyphs')
    require(all(new_glyphs.get(i)==g for i,g in old_glyphs.items()),'Original TMP glyph changed')
    require(all(new_chars.get(i)==c for i,c in old_chars.items()),'Original TMP character changed')
    atlas=(ROOT/'translation-work/visuals/tmp/atlas-alpha8.bin').read_bytes()
    original_atlas=(ROOT/'translation-work/visuals/tmp/original-alpha8.bin').read_bytes()
    require(len(atlas)==2048*1024 and len(original_atlas)==1024*1024,'Wrong atlas size')
    require(atlas in get(shared,201),'Built TMP texture does not contain the native bake')
    require(all(atlas[y*2048:y*2048+1024]==original_atlas[y*1024:(y+1)*1024] for y in range(1024)),
            'Original atlas pixels changed')
    material=bytearray(get(shared,2));old_material=get(old_shared,2)
    off=(old_material.index(b'_TextureWidth')+len(b'_TextureWidth')+3)//4*4
    require(struct.unpack_from('<f',material,off)[0]==2048,'TMP material has wrong texture width')
    material[off:off+4]=old_material[off:off+4]
    require(material==old_material,'Unrelated TMP material property changed')
    # The French fallback atlas and font are retained byte-for-byte.
    for pid in (193,200,457):require(get(old_shared,pid)==get(shared,pid),'French TMP asset changed')
    report['subtitle_tmp_atlas']={'path_id':458,'glyphs':len(new_glyphs),'characters':len(new_chars),
        'missing':[],'original_glyphs_preserved':True,'original_atlas_pixels_preserved':True,
        'french_fallback_preserved':True,'size':[2048,1024]}
    for path,spec in profile['files'].items():
        old=(ROOT/spec['source']).read_bytes();new=(ROOT/'PTBR'/path).read_bytes()
        if spec['kind']=='binary':
            allowed=set()
            for patch in spec['ranges']:
                off=patch['offset'];a=bytes.fromhex(patch['before']);b=bytes.fromhex(patch['after'])
                require(old[off:off+len(a)]==a and new[off:off+len(b)]==b,'Selector bytes differ')
                allowed.update(range(off,off+len(a)))
            differences={i for i,(a,b) in enumerate(zip(old,new)) if a!=b}
            require(len(old)==len(new) and differences<=allowed,'Unrelated native code changed')
            report['selector_changed_bytes']=len(differences)
            continue
        a=UnityFile(old);b=UnityFile(new);changed={x['id'] for x in spec['objects']}
        for patch in spec['objects']:
            require(get(b,patch['id'])==(ROOT/patch['payload']).read_bytes(),'Built object mismatch')
        for extra in spec['additions']:
            require(get(b,extra['id'])==(ROOT/extra['payload']).read_bytes(),'Appended object mismatch')
        if path.endswith('resources.assets'):
            # Only these three extra objects belong to the localization stage.
            changed|={a.named('SpeechManager')['id'],*p.shape['language_menu_objects']}
        unchanged=0
        for o in a.objects:
            if o['id'] not in changed:
                require(a.raw(o)==get(b,o['id']),'Unrelated native object changed')
                unchanged+=1
        report['native_objects'][path]={'original':len(a.objects),'built':len(b.objects),'unchanged':unchanged}
        if path.endswith('sharedassets0.assets'):
            for pid in (8,28,114,116,144,173):require(get(a,pid)==get(b,pid),'Original French image changed')
            # Options normal and hover are cloned verbatim for French.
            extras=spec['additions'];require(len(extras)==4,'Options inventory changed')
            require(get(b,extras[1]['id'])==get(original_resources,123),'French options normal changed')
            require(get(b,extras[3]['id'])==get(original_resources,19),'French options hover changed')
    # Verify the extra styler's menu, button and all four texture references.
    ls=profile['files'][DATA+'level0'];ss=profile['files'][DATA+'sharedassets0.assets']
    level=UnityFile((ROOT/'PTBR'/DATA/'level0').read_bytes());extra=get(level,ls['additions'][0]['id'])
    r=Reader(extra,32);require(r.string()[0]=='Menu depart' and r.string()[0]=='Options','Wrong menu binding')
    ids=[x['id'] for x in ss['additions']];expected=[ids[0],ids[2],ids[1],ids[3]]
    for pid in expected:require(struct.unpack('<iq',r.take(12))==(2,pid),'Wrong menu artwork binding')
    for _ in range(2):require(r.string()[0]=='' and not any(r.take(48)),'Unexpected extra styler button')
    require(r.pos==len(extra),'Unexpected styler tail')
    report['options_language_binding_verified']=True
    out=ROOT/'translation-work/reports/visual-verification.json';out.write_bytes(encoded(report))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
