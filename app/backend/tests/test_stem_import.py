import asyncio
import json
import io
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import Request, UploadFile
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import projects
import stem_import
import library
import server
import section_import
import track_routing
import track_lifecycle


class ImportTracksTests(unittest.TestCase):
    def test_suggests_shared_filename_prefix(self):
        files=["Salt in the Circuit - Vocals.wav","Salt in the Circuit - Drums.mp3",
               "Salt in the Circuit - Bass.flac","Salt in the Circuit - Guitar.wav"]
        self.assertEqual(stem_import.guess_song_title(files),"Salt in the Circuit")
        self.assertEqual(stem_import.guess_song_title(["vocals.wav","drums.wav"]),"Imported song")
        self.assertEqual(stem_import.guess_song_title(["Some Piece - Vocals.wav","Different Piece - Drums.wav"]),"Imported song")

    def test_assigns_standard_and_extra_stems_without_collisions(self):
        stems=stem_import.assign_tracks(["demo vocals.wav","demo drums.wav","strings.wav",
                                         "synth.wav","chorus vocals.wav"])
        self.assertEqual([x["stem_alias"] for x in stems],
                         ["Vocals","Drums","Track01","Track02","Track03"])

    def test_recognizes_demucs_parenthesized_stems(self):
        names=["Song_(Vocals)_htdemucs_6s.wav","Song_(Drums)_htdemucs_6s.wav",
               "Song_(Guitar)_htdemucs_6s.wav","Song Guitarist Strings.wav"]
        self.assertEqual([item["stem_alias"] for item in stem_import.assign_tracks(names)],
                         ["Vocals","Drums","Guitar","Track01"])

    def test_import_endpoint_preserves_title_override_and_converts_tracks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            uploads=[UploadFile(filename="A Song - Vocals.mp3",file=io.BytesIO(b"VOCAL")),
                     UploadFile(filename="A Song - Drums.wav",file=io.BytesIO(b"DRUMS"))]
            request=Request({"type":"http","headers":[]})
            with patch.object(server,"DATA_ROOT",root),patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),patch.object(server,"run_track_import",lambda *args:None):
                job=asyncio.run(server.import_tracks(request,uploads,title="My override"))
            self.assertEqual(job["filename"],"My override.wav")
            self.assertEqual(job["status"],"queued")
            folder=root/"jobs"/job["id"]
            self.assertEqual((folder/"originals"/"A Song - Vocals.mp3").read_bytes(),b"VOCAL")
            self.assertEqual((folder/"originals"/"A Song - Drums.wav").read_bytes(),b"DRUMS")
            real_job=server.jobs.pop(job["id"])
            def fake_convert(command,**kwargs):
                Path(command[-1]).write_bytes(b"converted audio"*8)
                return SimpleNamespace(returncode=0,stderr="")
            with patch.object(server,"DATA_ROOT",root),patch.object(server,"probe_duration",return_value=12.5),patch.object(server,"dependency_tool",return_value="ffmpeg"),patch.object(server.subprocess,"run",side_effect=fake_convert):
                server.run_track_import(real_job,["A Song - Vocals.mp3","A Song - Drums.wav"],"My override")
            self.assertEqual(real_job["status"],"complete")
            record=projects.read_project(root,job["id"])
            self.assertEqual(record["title"],"My override")
            self.assertEqual(record["source_duration_seconds"],12.5)
            self.assertEqual(record["files"],["01 (Vocals).wav","02 (Drums).wav"])
            self.assertTrue((folder/"stems"/"02 (Drums).wav").is_file())

    def test_channel_manifest_reconstructs_six_parent_stems_and_active_children(self):
        names=["Vocals","Drums","Bass","Guitar","Piano","Other"]
        tracks=[]
        uploads=[]
        for i,role in enumerate(names,1):
            for side in ("left","right"):
                file=f"{i:02d} - {role} - {side.capitalize()}.wav"
                tracks.append({"source":f"Song_({role})_htdemucs_6s.wav",
                               "stem":role,"file":file,"channel":side})
                uploads.append(UploadFile(filename=file,file=io.BytesIO(b"source audio")))
        manifest={"format":stem_import.MANIFEST_FORMAT,"version":1,
                  "track_count":12,"source_project_id":"another-project","tracks":tracks}
        data=json.dumps(manifest).encode()
        groups=stem_import.channel_groups(data,[x.filename for x in uploads])
        self.assertEqual(len(groups),6)
        self.assertEqual(groups[0]["left"],"01 - Vocals - Left.wav")
        uploads.append(UploadFile(filename="manifest.json",file=io.BytesIO(data)))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            request=Request({"type":"http","headers":[]})
            with patch.object(server,"DATA_ROOT",root),patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),patch.object(server,"run_track_import",lambda *args:None):
                job=asyncio.run(server.import_tracks(request,uploads,title="Reimported"))
            actual=server.jobs.pop(job["id"])
            def fake_convert(command,**kwargs):
                Path(command[-1]).write_bytes(b"working WAV"*8)
                return SimpleNamespace(returncode=0,stderr="")
            with patch.object(server,"DATA_ROOT",root),patch.object(server,"probe_duration",return_value=13.0),patch.object(server,"dependency_tool",return_value="ffmpeg"),patch.object(server.subprocess,"run",side_effect=fake_convert):
                server.run_track_import(actual,[x["file"] for x in tracks],"Reimported",data)
            self.assertEqual(actual["status"],"complete",actual["message"])
            record=projects.read_project(root,job["id"])
            self.assertEqual(len(record["files"]),6)
            self.assertEqual(record["files"][0],"01 (Vocals).wav")
            routing=track_routing.valid_children(root,record)
            self.assertEqual(len(routing),6)
            self.assertTrue(all(x["active"] for x in routing.values()))
            self.assertEqual(routing["01 (Vocals).wav"]["tracks"]["left"]["file"],
                             "01 - Vocals - Left.wav")
            self.assertEqual(projects.stem_name(record["files"][-1]),"Other")

    def test_manifest_rejects_bad_pairs_and_foreign_paths(self):
        pairs=[{"source":"original.wav","file":"left.wav","channel":"left"},
               {"source":"original.wav","file":"right.wav","channel":"right"}]
        def check(tracks,uploaded):
            payload={"format":stem_import.MANIFEST_FORMAT,"version":1,
                     "track_count":len(tracks),"tracks":tracks}
            return stem_import.channel_groups(json.dumps(payload).encode(),uploaded)
        self.assertEqual(len(check(pairs,["left.wav","right.wav"])),1)
        with self.assertRaises(ValueError):check(pairs[:1],["left.wav"])
        with self.assertRaises(ValueError):check([dict(pairs[0],file="../left.wav"),pairs[1]],["../left.wav","right.wav"])
        with self.assertRaises(ValueError):check(pairs,["left.wav","wrong.wav"])

    def test_many_named_tracks_accept_independent_section_effects(self):
        names=["Song - Vocals.wav"]+[f"Song - Synth {n:02d}.wav" for n in range(1,33)]
        tracks=stem_import.identity_tracks(names)
        self.assertEqual(len({t["stem_alias"].lower() for t in tracks}),33)
        self.assertEqual(len({t["track_id"] for t in tracks}),33)
        files=[f"{i:02d} ({t['stem_alias']}).wav" for i,t in enumerate(tracks,1)]
        alias=tracks[-1]["stem_alias"]
        block=f"{{{alias}.pan:right.60@2s:smooth {alias}.eq1:320,1.2,-2@2s:smooth}}"
        result=section_import.apply({"files":files,"sections":[]},
               "[Verse 0:00-0:10]\n"+block+"\n","replace",10)
        self.assertEqual(len(result["section_pan_automation"]),1)
        self.assertEqual(result["section_pan_automation"][0]["source_key"],files[-1])
        self.assertEqual(result["section_eq_automation"][0]["source_key"],files[-1])

    def test_add_stem_to_existing_song_is_non_destructive_and_persistent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ident="abcdef123456"
            folder=root/"jobs"/ident
            (folder/"stems").mkdir(parents=True)
            files=["01 (Vocals).wav","02 (Drums).wav"]
            for name in files:(folder/"stems"/name).write_bytes(b"existing WAV")
            original={"version":projects.PROJECT_VERSION,"id":ident,
                      "filename":"Song.wav","title":"Song",
                      "source_filename":"Song.wav","files":files,
                      "stems":projects.default_settings(files),"source_duration_seconds":10}
            projects.write_project(root,original)
            job={"id":ident,"status":"complete","files":list(files),"message":"ready"}
            upload=UploadFile(filename="solo cello.wav",file=io.BytesIO(b"new source"))
            request=Request({"type":"http","headers":[]})
            def convert(command,**_):
                Path(command[-1]).write_bytes(b"working 48k WAV"*6)
                return SimpleNamespace(returncode=0,stderr="")
            with (patch.object(server,"DATA_ROOT",root),
                  patch.object(server,"jobs",{ident:job}),
                  patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),
                  patch.object(server,"probe_duration",return_value=8.5),
                  patch.object(server,"dependency_tool",return_value="ffmpeg"),
                  patch.object(server.subprocess,"run",side_effect=convert)):
                result=asyncio.run(server.add_project_track(
                    ident,request,upload,stem_alias="Cello_Accent",display_name="Cello Accent"))
            saved=projects.read_project(root,ident)
            self.assertEqual(len(saved["files"]),3)
            self.assertEqual(saved["files"][:2],files)
            self.assertEqual([x["gain"] for x in saved["stems"]],[1,1,1])
            self.assertFalse(saved.get("replacement_masks"),"Layer/default imports must not mute original stems")
            self.assertEqual(len(saved.get("replacement_masks",[])),0)
            self.assertEqual(saved["source_tracks"][-1]["stem_alias"],"Cello_Accent")
            self.assertTrue(saved["source_tracks"][-1]["track_id"].startswith("trk_"))
            self.assertEqual(result["job"]["status"],"complete")
            self.assertTrue((folder/"stems"/saved["files"][-1]).is_file())
            self.assertTrue((folder/"stems"/files[0]).read_bytes()==b"existing WAV")

    def test_original_gain_percentage_is_bounded_and_requires_source(self):
        request=Request({"type":"http","headers":[]})
        for level in (-1,101,float("nan"),float("inf")):
            upload=UploadFile(filename="valid.wav",file=io.BytesIO(b"audio"))
            with self.subTest(level=level),self.assertRaises(Exception) as problem:
                asyncio.run(server.add_project_track(
                    "abcdef123456",request,upload,stem_alias="NewStem",
                    display_name="New stem",original_gain_percent=level))
            self.assertIn("Original stem gain",str(problem.exception))
        upload=UploadFile(filename="valid.wav",file=io.BytesIO(b"audio"))
        with self.assertRaises(Exception) as problem:
            asyncio.run(server.add_project_track(
                "abcdef123456",request,upload,stem_alias="NewStem",
                display_name="New stem",original_gain_percent=15))
        self.assertIn("Select an original source stem",str(problem.exception))

    def test_replace_acceptance_adds_mask_and_remove_restores_unmodified_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ident="abcdef123456"
            folder=root/"jobs"/ident
            (folder/"stems").mkdir(parents=True)
            sources=["01 (Bass).wav","02 (Drums).wav"]
            for name in sources:(folder/"stems"/name).write_bytes(b"original-source")
            original={"version":projects.PROJECT_VERSION,"id":ident,
                      "filename":"Song.wav","title":"Song","source_filename":"Song.wav",
                      "files":sources,"stems":projects.default_settings(sources),
                      "source_duration_seconds":12}
            projects.write_project(root,original)
            identities=track_lifecycle.ensure_identities(original)
            # Persist the initially assigned IDs; a legacy manifest without
            # source_tracks generates fresh IDs on each read.
            original["source_tracks"]=identities
            project_bass=next(x for x in identities if x["stem_alias"]=="Bass")
            projects.write_project(root,original)
            job={"id":ident,"status":"complete","files":list(sources),"message":"ready"}
            upload=UploadFile(filename="cello.wav",file=io.BytesIO(b"generated-cello"))
            request=Request({"type":"http","headers":[]})
            def convert(command,**_):
                self.assertTrue(any("volume=-4.0dB" in str(arg) for arg in command))
                Path(command[-1]).write_bytes(b"working WAV"*8)
                return SimpleNamespace(returncode=0,stderr="")
            with (patch.object(server,"DATA_ROOT",root),
                  patch.object(server,"jobs",{ident:job}),
                  patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),
                  patch.object(server,"probe_duration",return_value=3.5),
                  patch.object(server,"dependency_tool",return_value="ffmpeg"),
                  patch.object(server.subprocess,"run",side_effect=convert)):
                added=asyncio.run(server.add_project_track(
                    ident,request,upload,stem_alias="CelloTake",display_name="Cello",
                    start_seconds=4,preview_trim_db=-4.0,original_gain_percent=10,
                    replace_source_track_id=project_bass["track_id"]))
                saved=projects.read_project(root,ident)
                mask=saved["replacement_masks"][0]
                imported=saved["source_tracks"][-1]
                self.assertEqual(mask["replacement_track_id"],imported["track_id"])
                self.assertEqual(mask["source_track_id"],project_bass["track_id"])
                self.assertEqual(mask["source_filename"],sources[0])
                self.assertEqual(mask["original_gain"],0.1)
                self.assertEqual((mask["start_seconds"],mask["end_seconds"]),(4,7.5))
                self.assertEqual(imported["import_trim_db"],-4)
                self.assertEqual((folder/"stems"/sources[0]).read_bytes(),b"original-source")
                removed=server.remove_project_track(
                    ident,imported["track_id"],request,
                    server.RemoveTrack(expected_alias="CelloTake"))
                restored=projects.read_project(root,ident)
                self.assertEqual(restored.get("replacement_masks"),[])
                self.assertEqual(restored["files"],sources)
                self.assertEqual((folder/"stems"/sources[0]).read_bytes(),b"original-source")

    def test_add_stem_conversion_error_does_not_modify_existing_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ident="abcdef123456"
            folder=root/"jobs"/ident
            (folder/"stems").mkdir(parents=True)
            names=["01 (Vocals).wav","02 (Drums).wav"]
            for name in names:(folder/"stems"/name).write_bytes(b"existing")
            project={"version":projects.PROJECT_VERSION,"id":ident,
                     "filename":"Song.wav","title":"Song","source_filename":"Song.wav",
                     "files":names,"stems":projects.default_settings(names),
                     "source_duration_seconds":10}
            projects.write_project(root,project)
            job={"id":ident,"status":"complete","files":list(names),"message":"ready"}
            upload=UploadFile(filename="cello.wav",file=io.BytesIO(b"audio"))
            request=Request({"type":"http","headers":[]})
            with (patch.object(server,"DATA_ROOT",root),
                  patch.object(server,"jobs",{ident:job}),
                  patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),
                  patch.object(server,"probe_duration",return_value=8.5),
                  patch.object(server,"dependency_tool",return_value="ffmpeg"),
                  patch.object(server.subprocess,"run",return_value=SimpleNamespace(returncode=1,stderr="bad audio"))):
                with self.assertRaises(Exception):
                    asyncio.run(server.add_project_track(ident,request,upload,
                        stem_alias="Cello",display_name="Cello"))
            self.assertEqual(projects.read_project(root,ident),project)
            self.assertEqual(job["status"],"complete")
            self.assertEqual(job["files"],names)
            self.assertEqual(list((folder/"stems").glob("*.wav")),[
                folder/"stems"/names[0],folder/"stems"/names[1]])
    
    def test_imported_project_is_discoverable_and_daw_exportable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ident="abcdef123456"
            folder=root/"jobs"/ident
            (folder/"stems").mkdir(parents=True)
            (folder/"originals").mkdir()
            original=folder/"originals"/"Song Vocals.wav"
            original.write_bytes(b"original unchanged")
            files=["01 (Vocals).wav","02 (Track01).wav"]
            for name in files:(folder/"stems"/name).write_bytes(b"mock wav")
            record={"version":projects.PROJECT_VERSION,"id":ident,"filename":"Song.wav",
                    "title":"Song","source_filename":original.name,"created_at":123,
                    "model":"imported tracks","imported_tracks":True,"files":files,
                    "source_tracks":[{"original_filename":"Song Vocals.wav","working_filename":files[0],"stem_alias":"Vocals"},
                                     {"original_filename":"Strings.wav","working_filename":files[1],"stem_alias":"Track01"}],
                    "stems":projects.default_settings(files),"source_duration_seconds":15}
            projects.write_project(root,record)
            self.assertEqual([p["id"] for p in projects.list_projects(root)],[ident])
            self.assertEqual([p.name for p in projects.validated_stems(record,folder)],files)
            bundle=projects.export_daw(root,record,"waveform")
            self.assertTrue((bundle/"01 - Vocals.wav").is_file())
            self.assertTrue((bundle/"02 - Track01.wav").is_file())
            self.assertIn('"track_count": 2',(bundle/"manifest.json").read_text())
            library.adopt_jobs(root)
            self.assertEqual(len(library.list_songs(root)),1)


if __name__=="__main__":
    unittest.main()
