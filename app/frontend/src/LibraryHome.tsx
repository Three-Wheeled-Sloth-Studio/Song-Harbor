import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, EditableTitle, IconButton, Menu } from "@tws-ui/core/react";

type Song = {id: string; legacy_job_id: string; title: string; imported_filename: string;
  created_at: number; version_count: number; variant_count: number; removed?: boolean; fingerprint?: string;
  variants: {id:string;legacy_job_id:string;filename:string;created_at:number;removed:boolean}[]};
type Collection = {id: string; parent_id: string | null; title: string;
  sort_order: number; song_count: number};
type LibraryIndex = {songs: Song[]; collections: Collection[]};
const ROOT = "/api/library";

export function LibraryHome({onOpenSong, onImport}: {
  onOpenSong: (legacyId: string) => void;
  onImport: () => void;
}) {
  const [songs, setSongs] = useState<Song[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [newCollection, setNewCollection] = useState(false);
  const [showTrash, setShowTrash] = useState(false);
  const [removedSong, setRemovedSong] = useState<Song | null>(null);
  const [helpSong, setHelpSong] = useState<Song | null>(null);
  const [collectionSong, setCollectionSong] = useState<Song | null>(null);
  const [combineSong, setCombineSong] = useState<Song | null>(null);
  const [chosenCollection, setChosenCollection] = useState("");
  const [chosenParent, setChosenParent] = useState("");
  const [context, setContext] = useState<{song:Song;x:number;y:number} | null>(null);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  async function refresh(trash = showTrash) {
    const response = await fetch(trash ? ROOT + "/trash" : ROOT);
    if (!response.ok) throw new Error("Library is unavailable. Reopen Song Harbor to reconnect.");
    const result = await response.json() as LibraryIndex;
    setSongs(result.songs);
    setCollections(result.collections);
  }

  useEffect(() => {
    if (!context) return;
    const close = () => setContext(null);
    const escape = (event: KeyboardEvent) => {if(event.key==="Escape")close();};
    window.addEventListener("pointerdown",close);
    window.addEventListener("keydown",escape);
    return () => {window.removeEventListener("pointerdown",close);window.removeEventListener("keydown",escape);};
  }, [context]);

  useEffect(() => {
    let cancelled = false;
    const retry = async () => {
      for (let i=0;i<4;i++) {
        try {
          await refresh(false);
          if (!cancelled) {setLoading(false);setError("");}
          return;
        } catch {
          if (i<3) await new Promise<void>(resolve => setTimeout(resolve, 350*(i+1)));
        }
      }
      if (!cancelled) {setLoading(false);setError("Library isn't ready yet. Try Refresh.");}
    };
    void retry();
    return () => {cancelled=true;};
  }, []);

  const visible = useMemo(() => songs.filter(song => {
    const text = (song.title + " " + song.imported_filename).toLowerCase();
    return text.includes(search.trim().toLowerCase()) || song.variants.some(v => v.filename.toLowerCase().includes(search.trim().toLowerCase()));
  }), [songs, search]);
  const [members, setMembers] = useState<string[]>([]);
  useEffect(() => {
    if (!collection) {setMembers([]);return;}
    let active = true;
    void fetch(ROOT + "?collection_id=" + encodeURIComponent(collection))
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: LibraryIndex) => {if(active)setMembers(data.songs.map(x => x.id));})
      .catch(() => {if(active)setMembers([]);});
    return () => {active=false;};
  }, [collection, songs]);
  const displayed = collection ? visible.filter(song => members.includes(song.id)) : visible;

  async function toggleTrash() {
    const next = !showTrash;
    setShowTrash(next); setCollection(null); setRemovedSong(null);
    try { await refresh(next); } catch(e) { setError(String(e)); }
  }

  async function changeAvailability(song: Song, restore = false) {
    setBusy(true); setError("");
    try {
      const action = restore ? "restore" : "remove";
      const response = await fetch(ROOT + "/songs/" + song.id + "/" + action, {method:"POST"});
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as {detail?:string};
        throw new Error(body.detail || "Could not " + action + " this song (HTTP " + response.status + ")");
      }
      setRemovedSong(restore ? null : song);
      await refresh(showTrash);
    } catch(e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  async function combine() {
    if (!combineSong || !chosenParent) return;
    setBusy(true);setError("");
    try {
      const response = await fetch(ROOT + "/songs/" + combineSong.id + "/combine",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({parent_song_id:chosenParent}),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({})) as {detail?:string};
        throw new Error(data.detail || "Could not combine takes");
      }
      setCombineSong(null);setChosenParent("");
      await refresh();
    } catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }

  function openContext(event: React.MouseEvent, song:Song) {
    event.preventDefault();
    setSelected(song.id);
    setContext({song,x:Math.min(event.clientX,window.innerWidth-195),
      y:Math.min(event.clientY,window.innerHeight-190)});
  }

  function toggleVariants(id: string) {
    setExpanded(previous => previous.includes(id) ? previous.filter(x=>x!==id) : [...previous,id]);
  }

  async function rename(id: string, title: string) {
    setBusy(true); setError("");
    try {
      const response = await fetch(ROOT + "/songs/" + id, {
        method: "PATCH", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({title}),
      });
      if (!response.ok) {
        const result = await response.json() as {detail?: string};
        throw new Error(result.detail || "Rename failed");
      }
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  async function createCollection() {
    if (!newName.trim()) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(ROOT + "/collections", {
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({title:newName.trim(),parent_id:collection}),
      });
      if (!response.ok) throw new Error("Unable to create collection");
      setNewCollection(false); setNewName("");
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  async function assign(id: string, collectionId: string) {
    setBusy(true);setError("");
    try {
      const response = await fetch(ROOT + "/collections/" + collectionId + "/songs", {
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({song_id:id}),
      });
      if (!response.ok) throw new Error("Could not add song to collection");
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  function childrenOf(parent: string | null, depth = 0): React.ReactNode {
    return collections.filter(c => c.parent_id === parent).map(c =>
      <div key={c.id}>
        <button className={"lib-folder" + (collection === c.id ? " active" : "")}
          style={{paddingLeft: 9 + depth * 13}} title={c.title} onClick={() => setCollection(c.id)}>
          <span aria-hidden="true">▸</span><span>{c.title}</span>
          <small>{c.song_count}</small>
        </button>
        {depth < 5 && childrenOf(c.id, depth + 1)}
      </div>);
  }

  return <main className="library-home">
    <aside className="lib-sidebar" aria-label="Collections">
      <div className="lib-section-head">
        <span>COLLECTIONS</span>
        <IconButton icon="+" label="New collection" onClick={() => setNewCollection(v => !v)} />
      </div>
      <button className={"lib-folder" + (!collection ? " active" : "")}
        onClick={() => setCollection(null)}><span aria-hidden="true">♫</span>
        <span>All songs</span><small>{songs.length}</small></button>
      {childrenOf(null)}
      <button className={"lib-folder" + (showTrash ? " active" : "")}
        onClick={() => {void toggleTrash();}} title="Toggle removed songs">
        <span aria-hidden="true">♻</span><span>{showTrash ? "Back to Library" : "Removed"}</span>
      </button>
      {newCollection && <form className="lib-new-folder" onSubmit={e => {e.preventDefault();void createCollection();}}>
        <input autoFocus value={newName} aria-label="New collection name" maxLength={120}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => {if(e.key==="Escape"){setNewCollection(false);setNewName("");}}}/>
        <IconButton icon="✓" label="Create collection" disabled={busy} onClick={() => {void createCollection();}}/>
      </form>}
    </aside>
    <section className="lib-content">
      <div className="lib-topline">
        <h1>{showTrash ? "Removed" : "Library"}</h1>
        <div className="lib-actions">
          <input type="search" aria-label="Search songs" placeholder="Search songs"
            value={search} onChange={e => setSearch(e.target.value)}/>
          <IconButton icon="＋" label="Import song" onClick={onImport}/>
        </div>
      </div>
      <div className="lib-table-head"><span>SONG</span><span>VERSIONS</span><span>ACTIONS</span></div>
      <div className="lib-rows" role="list">
        {displayed.map(song =>
          <div className="lib-song-group" key={song.id}><div role="listitem" className={"lib-song" + (selected === song.id?" selected":"")}
            onClick={() => setSelected(song.id)}
            onContextMenu={e => openContext(e,song)}
            onKeyDown={e => {if(e.key==="ContextMenu" || e.shiftKey && e.key==="F10"){
              e.preventDefault();const rect=e.currentTarget.getBoundingClientRect();
              setContext({song,x:Math.min(rect.left+35,window.innerWidth-195),
                y:Math.min(rect.bottom,window.innerHeight-190)});
            }}}
            tabIndex={0}
            onDoubleClick={() => onOpenSong(song.legacy_job_id)}>
            <div className="lib-song-main">
              <EditableTitle value={song.title} label={"Rename " + song.title}
                disabled={busy || showTrash} onCommit={title => {void rename(song.id,title);}}/>
              <small title={song.imported_filename + (song.fingerprint ? " · SHA-256 " + song.fingerprint : "")}>{song.imported_filename}</small>
            </div>
            <span className="lib-song-count">{song.variant_count > 1 ? song.variant_count + " takes" : song.version_count}</span>
            <div className="lib-song-actions">
              {song.variant_count > 1 && <IconButton
                icon={expanded.includes(song.id) ? "▾" : "▸"}
                label={expanded.includes(song.id) ? "Collapse takes" : "Show takes"}
                onClick={e => {e.stopPropagation();toggleVariants(song.id);}}/>}
              {!showTrash && <IconButton icon="▶" label={"Open " + song.title}
                onClick={e => {e.stopPropagation();onOpenSong(song.legacy_job_id);}}/>}
              <Menu label={"Actions for " + song.title} trigger={<button className="lib-kebab"
                aria-label={"Options for " + song.title} title="More actions">⋯</button>}
                items={[
                  ...(!showTrash ? [{id:"open",label:"Open",onSelect:()=>onOpenSong(song.legacy_job_id)}] : []),
                  ...(!showTrash ? [
                    {id:"collection",label:"Add to collection…",onSelect:()=>{setCollectionSong(song);setChosenCollection("");}},
                    {id:"combine",label:"Combine as takes…",onSelect:()=>{setCombineSong(song);setChosenParent("");}},
                  ] : []),
                  {id:showTrash ? "restore" : "remove",
                   label:showTrash ? "Restore to Library" : "Remove from Library · keep files",
                   onSelect:()=>{void changeAvailability(song,showTrash);}},
                  {id:"help",label:"Help",onSelect:()=>setHelpSong(song)},
                ]}/>
            </div>
          </div>
          {expanded.includes(song.id) && <div className="lib-variants">
            {song.variants.map((take,index) => <div className="lib-variant" key={take.id}>
              <span title={take.filename}>↳ Take {index+1} · {take.filename}</span>
              {!showTrash && <IconButton label={"Open take " + (index+1)} icon="▶"
                onClick={()=>onOpenSong(take.legacy_job_id)} />}
            </div>)}
          </div>}
          </div>)}
      </div>
      {displayed.length === 0 && <div className="lib-empty">
        {songs.length ? "No matching songs." : "Your library is empty."}
        {!songs.length && <Button variant="primary" onClick={onImport}>Import song</Button>}
      </div>}
      {removedSong && !showTrash && <div className="lib-undo" role="status">
        Removed from Library; files preserved.
        <Button size="compact" variant="subtle" onClick={() => {
          void changeAvailability(removedSong,true);
        }}>Undo</Button>
      </div>}
      {loading && <p role="status" className="lib-muted-notice">Loading Library…</p>}
      {error && <div className="lib-undo" role="alert">{error}
        <IconButton icon="↻" label="Retry Library loading" onClick={() => {
          setError(""); setLoading(true);
          void refresh().then(()=>setLoading(false)).catch(e=>{setLoading(false);setError(String(e));});
        }}/>
      </div>}
    </section>
    {context && <div role="menu" className="lib-context-menu" style={{left:context.x,top:context.y}}
      onPointerDown={e=>e.stopPropagation()}>
      {!showTrash && <button role="menuitem" onClick={()=>{onOpenSong(context.song.legacy_job_id);setContext(null);}}>Open</button>}
      {!showTrash && <button role="menuitem" onClick={()=>{setCollectionSong(context.song);setContext(null);}}>Add to collection…</button>}
      {!showTrash && <button role="menuitem" onClick={()=>{setCombineSong(context.song);setContext(null);}}>Combine as takes…</button>}
      <button role="menuitem" onClick={()=>{void changeAvailability(context.song,showTrash);setContext(null);}}>
        {showTrash ? "Restore" : "Remove from Library"}</button>
      <button role="menuitem" onClick={()=>{setHelpSong(context.song);setContext(null);}}>Help</button>
    </div>}
    {collectionSong && <Dialog open onOpenChange={v=>{if(!v)setCollectionSong(null);}}
      title="Add to collection" description={collectionSong.title}>
      <div className="lib-picker">
        <input type="search" aria-label="Filter collections" placeholder="Search collections"
          value={chosenCollection} onChange={e=>setChosenCollection(e.target.value)}/>
        <div className="lib-picker-items">
          {collections.filter(item=>item.title.toLowerCase().includes(chosenCollection.toLowerCase())).map(item=>
            <button key={item.id} onClick={()=>{void assign(collectionSong.id,item.id).then(()=>setCollectionSong(null));}}>
              ♧ {item.title}</button>)}
        </div>
      </div>
    </Dialog>}
    {combineSong && <Dialog open onOpenChange={v=>{if(!v)setCombineSong(null);}}
      title="Combine as takes" description={"Keep both recordings; group " + combineSong.title + " with:"}>
      <div className="lib-picker">
        <select aria-label="Parent song" value={chosenParent} onChange={e=>setChosenParent(e.target.value)}>
          <option value="">Choose song…</option>
          {songs.filter(s=>s.id!==combineSong.id).map(s=>
            <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        <Button variant="primary" disabled={!chosenParent||busy} onClick={()=>{void combine();}}>Combine</Button>
      </div>
    </Dialog>}
    {helpSong && <Dialog open onOpenChange={open => {if(!open)setHelpSong(null);}}
      title="Song Library help" description={helpSong.title}>
      <div className="library-help">
        <p>Double-click a song or use ▶ to open its stem workspace.</p>
        <p>Use the pencil beside its name to rename the song without changing the original WAV/MP3 filename.</p>
        <p>Identical source recordings appear as takes under one song. Expand them to open a specific separation.</p>
        <p>Use ⋯ to place songs into collections or remove them from the Library. Removing a song keeps its media files and can be undone from Removed.</p>
        <a href="https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/blob/main/docs/library-first-architecture.md"
          target="_blank" rel="noreferrer">Detailed reference ↗</a>
      </div>
    </Dialog>}
  </main>;
}
