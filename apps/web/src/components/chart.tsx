'use client';
import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,DataZoomComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';
echarts.use([LineChart,GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,CanvasRenderer]);
export default function Chart({series}:{series:{name:string;rows:{period:string;value:number|null}[]}[]}) {
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!ref.current)return; const chart=echarts.init(ref.current); chart.setOption({color:['#12a681','#d7a34b','#6d8fd1'],tooltip:{trigger:'axis'},legend:{bottom:0,textStyle:{color:'#87958c'}},grid:{left:62,right:25,top:25,bottom:65},xAxis:{type:'category',data:[...new Set(series.flatMap(s=>s.rows.map(r=>r.period)))].sort(),axisLabel:{color:'#87958c'},axisLine:{lineStyle:{color:'#34433b'}}},yAxis:{type:'value',axisLabel:{color:'#87958c'},splitLine:{lineStyle:{color:'#87958c22'}}},dataZoom:[{type:'inside'}],series:series.map(s=>({name:s.name,type:'line',showSymbol:false,connectNulls:false,data:s.rows.map(r=>[r.period,r.value]),lineStyle:{width:3},areaStyle:{opacity:0.08},emphasis:{focus:'series'}}))});const observer=new ResizeObserver(()=>chart.resize());observer.observe(ref.current);return()=>{observer.disconnect();chart.dispose();}},[series]);
 return <div ref={ref} className="chart" role="img" aria-label="Interactive time-series comparison chart"/>;
}
