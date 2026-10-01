import {test} from 'node:test'; import assert from 'node:assert/strict'; import {transformSeries,csv} from '../src/lib/analytics.mjs';
test('chronological change avoids division by zero',()=>{assert.deepEqual(transformSeries([{period:'2020-02',value:2},{period:'2020-01',value:0}], 'change').map(x=>x.value),[null,null]);});
test('rolling excludes incomplete windows',()=>assert.deepEqual(transformSeries([1,2,3,4].map((value,i)=>({period:String(i),value})),'rolling').map(x=>x.value),[null,null,2,3]));
test('CSV escapes quotes and line breaks',()=>assert.equal(csv([{name:'A,"B',value:2}]),'"name","value"\n"A,""B","2"'));
