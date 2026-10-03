export type Observation={dataset:string;indicator:string;geography:string;period:string;value:number;unit:string;frequency:string;source_url:string};
export type Definition={title:string;domain:string;unit:string;source:string;source_url:string;definition?:string;source_organization?:string;publisher_title?:string};
export type Dictionary=Record<string,Definition>;
export type Coverage={observations:number;indicators:number;datasets:number;geographies:number;start:string|null;end:string|null;national_observations:number};
export type WorkspaceResponse={status:string;data:Observation[];metadata:Dictionary;coverage:Coverage};
export const year=(r:Observation)=>Number(r.period.slice(0,4));
export const title=(key:string,metadata:Dictionary)=>metadata[key]?.title??key.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
export function history(rows:Observation[],key:string,geography='Pakistan'){return rows.filter(r=>r.indicator===key&&r.geography===geography).sort((a,b)=>a.period.localeCompare(b.period));}
export function latest(rows:Observation[],key:string,geography='Pakistan'){return history(rows,key,geography).at(-1);}
export function formatValue(value:number|undefined,unit='',compact=true){if(value===undefined||!Number.isFinite(value))return '—';const options:Intl.NumberFormatOptions={maximumFractionDigits:compact?1:2,...(compact&&Math.abs(value)>=10000?{notation:'compact' as const}: {})};const number=new Intl.NumberFormat('en-US',options).format(value);return `${unit.startsWith('current_usd')?'$':''}${number}${unit.startsWith('percent')?'%':''}`;}
export const unitLabel=(unit:string)=>({current_usd:'Current US dollars',current_usd_per_person:'US dollars per person',persons:'People',percent:'Percent',percent_gdp:'% of GDP',tonnes:'Tonnes',kg_per_hectare:'kg per hectare',years:'Years',index_2015_16_100:'Index · 2015–16 = 100',percent_population:'% of population',percent_land_area:'% of land area',pkr_per_usd:'PKR per US dollar'}[unit]??unit.replaceAll('_',' '));
export function points(rows:Observation[],key:string,divisor=1){return history(rows,key).map(r=>({period:r.period,value:r.value/divisor}));}
