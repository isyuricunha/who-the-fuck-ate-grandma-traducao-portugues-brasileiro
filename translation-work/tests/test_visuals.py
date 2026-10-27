import json
import struct
from pathlib import Path
from test_toolkit import Sandbox
from fixtures import fixture
from native import UnityFile, sha
from storage import encoded
from visuals import append_objects, apply, PROFILE


class VisualTests(Sandbox):
    def test_append_keeps_all_existing_payloads_and_rejects_id_collision(self):
        data=fixture(self.shape); before=UnityFile(data)
        ident=max(o['id'] for o in before.objects)+1
        added={'id':ident,'type_index':0,'raw':b'new profiled payload'}
        changed=append_objects(data,[added]); after=UnityFile(changed)
        self.assertEqual(len(after.objects),len(before.objects)+1)
        for old in before.objects:
            new=next(o for o in after.objects if o['id']==old['id'])
            self.assertEqual(before.raw(old),after.raw(new))
        self.assertEqual(after.raw(next(o for o in after.objects if o['id']==ident)),added['raw'])
        with self.assertRaisesRegex(ValueError,'collision'):append_objects(changed,[added])

    def binary_profile(self):
        folder=self.root/'translation-work/visuals';folder.mkdir()
        raw=b'headerABCDfooter';source=folder/'original.bin';source.write_bytes(raw)
        path=source.relative_to(self.root).as_posix()
        p={'schema':1,'inputs':{path:sha(raw)},'files':{'GameAssembly.dll':{
            'kind':'binary','source':path,'source_sha256':sha(raw),
            'ranges':[{'offset':6,'before':b'ABCD'.hex(),'after':b'WXYZ'.hex()}]}}}
        (self.root/PROFILE).write_bytes(encoded(p))
        return p,source

    def test_binary_patch_is_exact_and_fails_closed_on_version_or_signature(self):
        p,source=self.binary_profile()
        outputs=apply(self.root,{'unrelated':b'keep'})
        self.assertEqual(outputs,{'unrelated':b'keep','GameAssembly.dll':b'headerWXYZfooter'})
        source.write_bytes(b'headerZZZZfooter')
        with self.assertRaisesRegex(ValueError,'Visual input changed'):apply(self.root,{})
        path=next(iter(p['inputs']));p['inputs'][path]=sha(source.read_bytes())
        p['files']['GameAssembly.dll']['source_sha256']=sha(source.read_bytes())
        (self.root/PROFILE).write_bytes(encoded(p))
        with self.assertRaisesRegex(ValueError,'signature changed'):apply(self.root,{})

    def test_unprofiled_visuals_are_noop_and_escape_is_rejected(self):
        self.assertEqual(apply(self.root,{'x':b'y'}),{'x':b'y'})
        p,_=self.binary_profile();p['inputs']={'../outside.bin':'0'*64}
        (self.root/PROFILE).write_bytes(encoded(p))
        with self.assertRaises(ValueError):apply(self.root,{})

    def test_new_visual_inventory_makes_old_package_invalid(self):
        self.init();self.complete();self.p.build();self.p.verify_output()
        self.binary_profile()
        with self.assertRaisesRegex(ValueError,'inventory/hash mismatch'):self.p.verify_output()
