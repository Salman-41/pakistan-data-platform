export function transformSeries(rows, mode) {
  const sorted = [...rows].sort((a,b)=>a.period.localeCompare(b.period));
  if(mode === 'index') { const first = sorted.find(x=>x.value !== 0)?.value; return sorted.map(x=>({...x,value:first ? x.value / first * 100 : null})); }
  if(mode === 'change') return sorted.map((x,i)=>({...x,value:i && sorted[i-1].value !== 0 ? (x.value / sorted[i-1].value - 1)*100 : null}));
  if(mode === 'rolling') return sorted.map((x,i)=>({...x,value:i < 2 ? null : sorted.slice(i-2,i+1).reduce((sum,y)=>sum+y.value,0)/3}));
  return sorted;
}
export function csv(rows) { if(!rows.length) return ''; const keys=Object.keys(rows[0]); const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"'; return [keys.map(quote).join(','),...rows.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\n'); }
