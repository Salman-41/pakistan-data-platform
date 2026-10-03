'use client';

import {QueryClient,QueryClientProvider,useQuery} from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import {useEffect,useMemo,useState} from 'react';
import {Activity,ArrowDownToLine,ArrowUpRight,BarChart3,BookOpen,ChevronRight,Database,Globe2,LayoutDashboard,Menu,Moon,RefreshCw,Search,ShieldCheck,Sun,Users,X,Leaf,BriefcaseBusiness,Zap,HeartPulse,GraduationCap,Wifi,Landmark,Layers3,TrendingUp} from 'lucide-react';
import Logo from '../components/logo';
import EvidenceDashboard from '../components/dashboards';
import {Button} from '../components/button';
import DataTable from '../components/table';
import {csv} from '../lib/analytics.mjs';
import {type WorkspaceResponse,type Observation,title,unitLabel,year} from '../lib/data';

const NationalDashboard=dynamic(()=>import('../components/national-dashboard'),{loading:()=> <div className="skeleton tall"/>});
const SectorDashboard=dynamic(()=>import('../components/sector-dashboard'),{loading:()=> <div className="skeleton tall"/>});
const GeographyMap=dynamic(()=>import('../components/map'),{ssr:false});
const client=new QueryClient({defaultOptions:{queries:{retry:1,staleTime:60000}}});
const API=process.env.NEXT_PUBLIC_API_URL??'/backend';
type Row=Record<string,unknown>;
type ApiResponse={status:string;data:Row[];note?:string};
async function request<T>(path:string):Promise<T>{
 const response=await fetch(`${API}/api/v1/${path}`);
 if(!response.ok)throw Error(`The data service returned ${response.status}. Please retry.`);
 return response.json();
}
const subjects=[
 {name:'Economy',icon:Landmark,description:'Growth, investment, income and Pakistan’s macroeconomic history.'},
 {name:'Inflation',icon:TrendingUp,description:'Monthly price indices alongside the published annual inflation history.'},
 {name:'Trade',icon:Globe2,description:'Imports, exports and the scale of Pakistan’s external trade.'},
 {name:'Population',icon:Users,description:'National demographic histories and published district census comparisons.'},
 {name:'Agriculture',icon:Leaf,description:'Agricultural value added, land use, production and cereal yields.'},
 {name:'Labour',icon:BriefcaseBusiness,description:'Employment, participation and unemployment, with modelled estimates labelled.'},
 {name:'Energy',icon:Zap,description:'Electricity access, clean cooking and energy consumption.'},
 {name:'Health',icon:HeartPulse,description:'Life expectancy, health spending, mortality and essential services.'},
 {name:'Education',icon:GraduationCap,description:'Literacy, enrollment and investment in education.'},
 {name:'Environment',icon:Leaf,description:'Forests, freshwater resources and environmental exposure.'},
 {name:'Digital',icon:Wifi,description:'Internet use, connectivity and the infrastructure behind digital access.'},
];
const evidence=[{name:'Data catalog',icon:Database},{name:'Data quality',icon:ShieldCheck},{name:'Models',icon:Layers3}];
function download(rows:Observation[]){const href=URL.createObjectURL(new Blob([csv(rows.map(r=>({...r})))],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=href;a.download='pakistan-observations.csv';a.click();URL.revokeObjectURL(href);}

function Workspace(){
 const [active,setActive]=useState('Dashboard');
 const [dark,setDark]=useState(false);
 const [menu,setMenu]=useState(false);
 const [from,setFrom]=useState(2000);
 const [to,setTo]=useState(new Date().getFullYear());
 const [publisher,setPublisher]=useState('all');
 const [search,setSearch]=useState('');
 const [geography,setGeography]=useState('Pakistan');
 useEffect(()=>{setDark(localStorage.getItem('pdp-theme')==='dark')},[]);
 useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';localStorage.setItem('pdp-theme',dark?'dark':'light')},[dark]);
 const workspace=useQuery({queryKey:['workspace'],queryFn:()=>request<WorkspaceResponse>('workspace')});
 const catalog=useQuery({queryKey:['catalog'],queryFn:()=>request<ApiResponse>('catalog')});
 const models=useQuery({queryKey:['models'],queryFn:()=>request<ApiResponse>('forecast'),enabled:active==='Models'});
 const all=workspace.data?.data??[];
 const metadata=workspace.data?.metadata??{};
 const coverage=workspace.data?.coverage;
 const filtered=useMemo(()=>all.filter(r=>year(r)>=from&&year(r)<=to&&(publisher==='all'||(publisher==='pbs'?r.dataset.startsWith('pbs_'):r.dataset.startsWith('worldbank_')))),[workspace.data,from,to,publisher]);
 const isSubject=subjects.some(s=>s.name===active);
 const activeDomain=active.toLowerCase();
 const exportRows=filtered.filter(r=>active==='Dashboard'?r.geography==='Pakistan':active==='Geographies'?r.geography===geography:metadata[r.indicator]?.domain===activeDomain||(active==='Inflation'&&r.indicator==='inflation_annual'));
 const firstYear=Number(coverage?.start?.slice(0,4)??1960);
 const lastYear=Math.max(new Date().getFullYear(),Number(coverage?.end?.slice(0,4)??0));
 const years=Array.from({length:Math.max(1,lastYear-firstYear+1)},(_,i)=>firstYear+i);
 const geographies=[...new Set(filtered.map(r=>r.geography))].sort();
 function navigate(tab:string){setActive(tab);setMenu(false);setSearch('')}
 function navItem(name:string,Icon:typeof Activity,primary=false){return <button key={name} aria-current={active===name?'page':undefined} className={`nav-item ${primary?'nav-dashboard ':''}${active===name?'selected':''}`} onClick={()=>navigate(name)}><Icon size={primary?19:16}/><span>{name}</span>{active===name&&<ChevronRight size={14}/>}</button>}
 const description=active==='Dashboard'?'A connected view of Pakistan’s economy, people and development.':subjects.find(s=>s.name===active)?.description??(active==='Geographies'?'Explore coverage at each published geographic level.':'Inspect the publications and evidence behind this workspace.');
 const subjectCount=new Set(filtered.map(r=>metadata[r.indicator]?.domain).filter(Boolean)).size;
 const catalogRows=(catalog.data?.data??[]).filter(r=>!search||JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));
 return <div className="shell bi-shell"><a href="#content" className="skip">Skip to content</a>
  {menu&&<button className="sidebar-backdrop" onClick={()=>setMenu(false)} aria-label="Close navigation"/>}
  <aside className={menu?'sidebar open':'sidebar'}>
   <div className="brand"><span className="brand-mark"><Logo/></span><div>Pakistan<span>DATA PLATFORM</span></div><button className="mobile close" onClick={()=>setMenu(false)} aria-label="Close menu"><X size={20}/></button></div>
   <nav className="bi-navigation" aria-label="Main navigation">
    <div className="nav-group">{navItem('Dashboard',LayoutDashboard,true)}</div>
    <div className="nav-group"><div className="nav-label">EXPLORE BY SUBJECT</div>{subjects.map(s=>navItem(s.name,s.icon))}</div>
    <div className="nav-group"><div className="nav-label">GEOGRAPHY</div>{navItem('Geographies',Globe2)}</div>
    <div className="nav-group"><div className="nav-label">SOURCES & EVIDENCE</div>{evidence.map(s=>navItem(s.name,s.icon))}</div>
   </nav>
   <div className="sidebar-foot"><div><span className="status-dot"/>{coverage?`${coverage.observations.toLocaleString()} observations`:'Source-linked analytics'}</div><p>PBS · World Bank</p><a href="https://github.com/Salman-41/pakistan-data-platform" target="_blank" rel="noreferrer">Project repository<ArrowUpRight size={13}/></a></div>
  </aside>
  <div className="workspace"><header className="topbar"><div className="topbar-leading"><button className="mobile" onClick={()=>setMenu(true)} aria-label="Open menu"><Menu size={21}/></button><div className="breadcrumb">Pakistan <ChevronRight size={13}/><span>{active}</span></div></div><div className="topbar-actions"><span className="source-tag"><ShieldCheck size={13}/> PBS + World Bank</span><button onClick={()=>{workspace.refetch();catalog.refetch();if(active==='Models')models.refetch()}} aria-label="Refresh data" disabled={workspace.isFetching}><RefreshCw size={16} className={workspace.isFetching?'refresh-spinning':''}/></button><button onClick={()=>setDark(!dark)} aria-label={dark?'Use light theme':'Use dark theme'}>{dark?<Sun size={17}/>:<Moon size={17}/>}</button></div></header>
   <main id="content"><div className="heading"><div><div className="eyebrow">PAKISTAN / INTELLIGENCE WORKSPACE</div><h1>{active==='Dashboard'?'Pakistan dashboard':active}</h1><p>{description}</p></div><div className="heading-tools">{coverage&&<span className="coverage-pill"><span className="status-dot"/>{coverage.indicators} indicators</span>}<Button className="secondary" onClick={()=>download(exportRows)} disabled={!exportRows.length}><ArrowDownToLine size={15}/>Export data</Button></div></div>
   {workspace.error&&<div className="alert" role="alert"><Activity size={18}/><div><strong>Data service unavailable</strong><p>{(workspace.error as Error).message}</p></div><button onClick={()=>workspace.refetch()}>Retry</button></div>}
   {(active==='Dashboard'||isSubject||active==='Geographies')&&<section className="bi-filter-bar" aria-label="Dashboard filters"><div className="filter-heading"><BarChart3 size={17}/><strong>Report filters</strong></div><label>From<select value={from} onChange={e=>setFrom(Number(e.target.value))}>{years.map(y=><option key={y} disabled={y>to}>{y}</option>)}</select></label><span className="filter-dash">—</span><label>To<select value={to} onChange={e=>setTo(Number(e.target.value))}>{years.map(y=><option key={y} disabled={y<from}>{y}</option>)}</select></label><label>Source<select value={publisher} onChange={e=>setPublisher(e.target.value)}><option value="all">All publishers</option><option value="pbs">Pakistan Bureau of Statistics</option><option value="worldbank">World Bank · WDI</option></select></label><div className="filter-presets"><button className={from===lastYear-10?'selected':''} onClick={()=>{setFrom(Math.max(firstYear,lastYear-10));setTo(lastYear)}}>10Y</button><button className={from===2000?'selected':''} onClick={()=>{setFrom(2000);setTo(lastYear)}}>2000+</button><button className={from===firstYear?'selected':''} onClick={()=>{setFrom(firstYear);setTo(lastYear)}}>All history</button></div><span className="filter-count">{filtered.length.toLocaleString()} observations</span></section>}
   {(active==='Dashboard'||isSubject)&&workspace.isLoading?<div className="bi-loading"><div className="bi-kpi-grid">{Array.from({length:6},(_,i)=><div key={i} className="skeleton" style={{height:155}}/>)}</div><div className="skeleton" style={{height:420}}/></div>:<>
    {active==='Dashboard'&&<NationalDashboard rows={filtered} metadata={metadata} navigate={navigate}/>}
    {isSubject&&<SectorDashboard key={active} active={active} rows={filtered} metadata={metadata}/>}
   </>}
   {active==='Geographies'&&<><div className="metric-grid"><div className="metric"><span>Published geographies</span><strong>{geographies.length}</strong><small>In the selected year and source range</small></div><div className="metric"><span>National observations</span><strong>{filtered.filter(r=>r.geography==='Pakistan').length.toLocaleString()}</strong><small>National estimates and published totals</small></div><div className="metric"><span>District source</span><strong>Census 2023</strong><small>Published PBS district counts</small></div><div className="metric"><span>Geographic integrity</span><strong>Source levels</strong><small>National data is never copied into districts</small></div></div><section className="panel"><div className="panel-title"><div><h2>Geography explorer</h2><p>Select a place to inspect its available measures.</p></div><select className="dashboard-select" aria-label="Published geography" value={geography} onChange={e=>setGeography(e.target.value)}>{geographies.map(g=><option key={g}>{g}</option>)}</select></div>{process.env.NEXT_PUBLIC_BOUNDARY_URL&&<GeographyMap url={process.env.NEXT_PUBLIC_BOUNDARY_URL}/>}<div className="geography-chips">{geographies.map(g=><button key={g} className={g===geography?'selected':''} onClick={()=>setGeography(g)}>{g}<small>{filtered.filter(r=>r.geography===g).length} observations</small></button>)}</div><div className="audit-panel"><h2>{geography}: latest published measures</h2><DataTable rows={[...new Set(filtered.filter(r=>r.geography===geography).map(r=>`${r.dataset}|${r.indicator}`))].map(key=>{const records=filtered.filter(r=>r.geography===geography&&`${r.dataset}|${r.indicator}`===key).sort((a,b)=>a.period.localeCompare(b.period));const r=records.at(-1)!;return {indicator:title(r.indicator,metadata),value:r.value,unit:unitLabel(r.unit),year:r.period.slice(0,4),source_url:r.source_url}})}/></div></section></>}
   {['Data catalog','Data quality','Models'].includes(active)&&<>{active==='Data catalog'&&<div className="catalog-toolbar"><div className="coverage-summary"><strong>{coverage?.datasets??0}</strong> datasets · <strong>{subjectCount}</strong> subjects · <strong>{coverage?.geographies??0}</strong> geographies</div><label className="search"><Search size={15}/><input placeholder="Search source publications" aria-label="Search source publications" value={search} onChange={e=>setSearch(e.target.value)}/></label></div>}{(active==='Models'?models.isLoading:catalog.isLoading)?<div className="skeleton tall"/>:(active==='Models'?models.error:catalog.error)?<div className="alert" role="alert">Could not load this source view. Use Refresh to try again.</div>:<EvidenceDashboard key={active} active={active} rows={active==='Models'?models.data?.data??[]:active==='Data catalog'?catalogRows:catalog.data?.data??[]} catalog={catalog.data?.data??[]} navigate={navigate}/>}</>}
   <footer><span>Pakistan Data Platform</span><span>{coverage?.start?.slice(0,4)??'—'}–{coverage?.end?.slice(0,4)??'—'} published coverage · periods vary by indicator</span><a href={`${API}/docs`} target="_blank" rel="noreferrer"><BookOpen size={13}/>API reference</a></footer>
  </main></div>
 </div>;
}
export default function Home(){return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>}
