"""Developer pixel roundtrip check; requires optional UnityPy and Pillow."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import UnityPy
from native import sha
from storage import encoded
from toolkit import Project

ROOT=Path(__file__).resolve().parent.parent


def main():
    Project(ROOT).verify_output()
    v=ROOT/'translation-work/visuals'
    profile=json.loads((v/'profile.json').read_text('utf-8'))
    added=profile['files']['Who the fuck ate grandma_Data/sharedassets0.assets']['additions']
    rows=[('jogar',189,151),('carregar',93,179),('opcoes',added[0]['id'],added[2]['id']),('sair',134,137)]
    env=UnityPy.load(str(ROOT/'PTBR/Who the fuck ate grandma_Data/sharedassets0.assets'))
    board=Image.new('RGB',(1500,780),'#314535');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(v/'fonts/font-428-ptbr.otf'),23)
    draw.text((30,10),'PRÉVIA TÉCNICA DOS BOTÕES — NORMAL / DESTAQUE',font=font,fill='white')
    report=[]
    for row,(label,normal,hover) in enumerate(rows):
        for state,pid in enumerate((normal,hover)):
            o=next(o for o in env.objects if o.path_id==pid)
            actual=o.read().image.convert('RGBA')
            expected=Image.open(v/f'menu/{label}-{state}.png').convert('RGBA')
            assert actual.size==expected.size==(1417,340)
            assert actual.tobytes()==expected.tobytes(), ('Built artwork differs',label,state)
            report.append({'button':label,'state':state,'path_id':pid,
                           'pixels_match_reviewed_art':True,'rgba_sha256':sha(actual.tobytes())})
            tile=actual.resize((708,170),Image.Resampling.LANCZOS)
            board.paste(tile,(20+state*750,55+row*177),tile)
    board.save(v/'menu-preview.png')
    (ROOT/'translation-work/reports/visual-image-verification.json').write_bytes(encoded(report))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
