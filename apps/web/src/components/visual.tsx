'use client';
import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart,BarChart,PieChart,HeatmapChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,VisualMapComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';
echarts.use([LineChart,BarChart,PieChart,HeatmapChart,GridComponent,TooltipComponent,LegendComponent,VisualMapComponent,CanvasRenderer]);
type Series={name:string;rows:{period:string;value:number|null}[]};
type Props={kind?:'line'|'bar'|'donut';series?:Series[];categories?:{name:string;value:number}[];unit?:string;label:string;height?:number;percent?:boolean};
export default function Visual({kind='line',series=[],categories=[],unit='',label,height=290,percent=false}:Props){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!ref.current)return;const chart=echarts.init(ref.current);const paint=()=>{
  const style=getComputedStyle(document.documentElement);const text=style.getPropertyValue('--muted').trim(),line=style.getPropertyValue('--line').trim(),panel=style.getPropertyValue('--panel').trim(),ink=style.getPropertyValue('--ink').trim();
  const colors=['#12a681','#4f83cc','#dfac55','#956fd5','#62b9c1','#d97c72'];
  let dates=[...new Set(series.flatMap(s=>s.rows.map(r=>r.period)))].sort();
  // Keep absent calendar periods as gaps rather than compressing the time axis.
  if(dates.length>1&&dates.every(d=>/^\d{4}-\d{2}-01$/.test(d))){
   const monthly=dates.some(d=>!d.endsWith('-01-01'));const first=new Date(`${dates[0]}T00:00:00Z`),last=new Date(`${dates.at(-1)}T00:00:00Z`);const calendar:string[]=[];
   for(let date=first;date<=last&&calendar.length<2000;date=new Date(Date.UTC(date.getUTCFullYear()+(monthly?0:1),date.getUTCMonth()+(monthly?1:0),1)))calendar.push(date.toISOString().slice(0,10));
   dates=calendar;
  }
  const tooltip={trigger:kind==='donut'?'item':'axis',backgroundColor:panel,borderColor:line,textStyle:{color:ink,fontSize:11},confine:true,valueFormatter:(value:unknown)=>`${Number(value).toLocaleString(undefined,{maximumFractionDigits:2})}${percent?'%':''}${unit?` ${unit}`:''}`};
  const option:echarts.EChartsCoreOption={color:colors,animationDuration:400,tooltip,legend:{bottom:0,icon:'circle',itemWidth:7,itemHeight:7,textStyle:{color:text,fontSize:10}},grid:{top:18,right:20,left:12,bottom:40,containLabel:true}};
  if(kind==='donut')option.series=[{type:'pie',radius:['54%','76%'],center:['50%','44%'],avoidLabelOverlap:true,label:{show:false},emphasis:{label:{show:true,fontSize:15,color:ink,fontWeight:600,formatter:'{b}\n{d}%'}},itemStyle:{borderWidth:4,borderColor:panel,borderRadius:6},data:categories}];
  else if(kind==='bar'){option.xAxis={type:'value',axisLabel:{color:text,fontSize:10},splitLine:{lineStyle:{color:line}},...(percent?{max:100}: {})};option.yAxis={type:'category',inverse:true,data:categories.map(c=>c.name),axisLine:{show:false},axisTick:{show:false},axisLabel:{color:text,fontSize:11,width:145,overflow:'truncate'}};option.legend={show:false};option.series=[{type:'bar',barMaxWidth:18,itemStyle:{borderRadius:[0,5,5,0]},data:categories.map((c,i)=>({value:c.value,itemStyle:{color:colors[i%colors.length]}})),label:{show:true,position:'right',color:text,fontSize:10,formatter:({value}: {value:unknown})=>`${Number(value).toLocaleString(undefined,{maximumFractionDigits:1})}${percent?'%':''}`}}];option.grid={top:15,left:10,right:55,bottom:15,containLabel:true};}
  else {option.xAxis={type:'category',data:dates,boundaryGap:false,axisLine:{show:false},axisTick:{show:false},axisLabel:{color:text,fontSize:10,formatter:(value:string)=>value.slice(0,7).replace('-01','')}};option.yAxis={type:'value',axisLabel:{color:text,fontSize:10},splitLine:{lineStyle:{color:line,type:'dashed'}}};option.series=series.map((s,i)=>{const values=new Map(s.rows.map(r=>[r.period,r.value]));return {name:s.name,type:'line',smooth:false,showSymbol:s.rows.length<15,symbolSize:5,connectNulls:false,lineStyle:{width:2.5},areaStyle:i===0&&series.length===1?{opacity:.08}:undefined,data:dates.map(d=>values.get(d)??null)}});}
  chart.setOption(option,{notMerge:true});
 };paint();const observer=new ResizeObserver(()=>chart.resize());observer.observe(ref.current);const theme=new MutationObserver(paint);theme.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});return()=>{observer.disconnect();theme.disconnect();chart.dispose()};
 },[kind,series,categories,unit,percent]);
 if((kind==='line'&&series.every(s=>!s.rows.length))||(kind!=='line'&&!categories.length))return <div className="visual-empty" style={{height}}><span>No observations in this selection</span><small>Adjust the year or source filters to view available coverage.</small></div>;
 return <div ref={ref} className="bi-visual" style={{height}} role="img" aria-label={label}/>;
}
