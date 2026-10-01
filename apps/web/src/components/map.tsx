'use client';
import {useEffect,useRef,useState} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
export default function GeographyMap({url}:{url:string}){ const ref=useRef<HTMLDivElement>(null);const [error,setError]=useState('');
 useEffect(()=>{if(!ref.current||!url)return;const map=new maplibregl.Map({container:ref.current,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#14251d'}}]},center:[69.3,30.4],zoom:4});map.addControl(new maplibregl.NavigationControl());map.on('load',async()=>{try{const r=await fetch(url);if(!r.ok)throw Error('Boundary file could not be loaded');const geo=await r.json();map.addSource('districts',{type:'geojson',data:geo});map.addLayer({id:'district-fill',type:'fill',source:'districts',paint:{'fill-color':'#29966e','fill-opacity':.25}});map.addLayer({id:'district-line',type:'line',source:'districts',paint:{'line-color':'#84c6a7','line-width':1}});map.on('click','district-fill',e=>{const props=e.features?.[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setText(String(props?.name??props?.district??'Boundary feature')).addTo(map)});}catch(e){setError(String(e));}});return()=>map.remove();},[url]);return <>{error&&<p role="alert">{error}</p>}<div className="map" ref={ref}/></>;
}
